# Sapiex Agent Runtime

A minimal agent runtime built from scratch in Python, using the Groq API (free tier) with Llama 3.3 70B.

---

## Quick Start

```bash
# 1. Clone the repo
git clone <your-repo-url>
cd sapiex-agent

# 2. Create and activate virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Get a FREE Groq API key (no credit card)
#    → https://console.groq.com/keys

# 5. Set up your .env file
cp .env.example .env
# Open .env and paste your key: GROQ_API_KEY=gsk_...

# 6. Run the agent
python main.py                        # default session
python main.py ./path/to/data/folder  # session tied to a folder
python main.py --session my_task      # named session (resumable)
```

---

## Demo

```
You: What files are in this folder?
  ⚙ list_files(directory='.')

Agent:
The folder contains:
- annual_report_2023.pdf
- revenue_2023.xlsx
- revenue_summary.csv

You: Compare the spreadsheet and the PDF month by month. Flag any discrepancies.
  ⚙ read_pdf(path='annual_report_2023.pdf')
  ⚙ read_spreadsheet(path='revenue_2023.xlsx')

Agent:
## Month-by-Month Comparison

| Month     | PDF ($)   | Spreadsheet ($) | Match? |
|-----------|-----------|-----------------|--------|
| January   | 1,200,000 | 1,200,000       | ✅     |
| February  | 1,100,000 | 1,050,000       | ❌     |
| ...       | ...       | ...             | ✅     |

⚠️ Discrepancy found: February — PDF claims $1,100,000 but spreadsheet shows
$1,050,000. Gap of $50,000 (4.5%). All other months match exactly.
```

---

## Folder Structure

```
sapiex-agent/
├── main.py              ← CLI entry point (REPL)
├── runtime.py           ← Agent loop — manual JSON tool dispatch
├── state.py             ← Persist / load conversation history (JSON)
├── skills_loader.py     ← Load .md skill files dynamically
├── config.py            ← Reads .env variables
├── tools/
│   ├── pdf_tool.py      ← pdfplumber: text + table extraction
│   ├── spreadsheet_tool.py  ← pandas: Excel + CSV with summaries
│   ├── file_tool.py     ← Directory listing
│   └── text_tool.py     ← Plain text / JSON / Markdown
├── skills/              ← Drop .md files here to add new skills
│   ├── financial_analyst.md
│   ├── data_comparator.md
│   └── summarizer.md
├── test_data/           ← Sample files for demo
│   ├── annual_report_2023.pdf
│   ├── revenue_2023.xlsx
│   └── revenue_summary.csv
├── .agent_state/        ← Auto-created: one JSON file per session
├── requirements.txt
├── .env.example
└── README.md
```

---

## Design Decisions

### The Loop

The loop runs inside `run_turn()` in `runtime.py`. Instead of using the provider's
native function-calling API (which is unreliable on open-source models and caused
400 errors with malformed `<function=...>` output), tools are described in plain
English in the system prompt. The model emits a JSON action block when it wants
to call a tool:

```json
{"action": "list_files", "args": {"directory": "."}}
```

We parse that JSON ourselves and feed results back. Each iteration:
1. Send messages to model
2. If response contains a `{"action": ...}` JSON block → execute tool, append result, loop
3. If response is plain text → done

**Termination:** Loop exits when the model returns no JSON action block, or after
`MAX_ITERATIONS` (default 10). The cap is a hard safety rail.

**Malformed output:** `_extract_action()` tries two regex patterns before giving up.
If it can't find a valid action, it treats the response as a final answer. Tools
wrap all exceptions and return `"ERROR: ..."` strings — the model reads these and
either retries or explains the problem. We never crash.

**Why not native tool calling?** Groq's `llama-3.3-70b-versatile` generates its own
`<function=...>` format which the API then rejects with a 400 error. Manual JSON
dispatch works with any model from any provider, with zero API-specific code.

---

### Tools

A tool is a Python function in `tools/` that takes string arguments and returns a
string. The `TOOL_REGISTRY` dict in `runtime.py` pairs each name with its function
and a plain-English description that goes into the system prompt.

**Shape:** Every tool takes simple string arguments and returns a string. Strings
are the universal interface — no complex types to serialise or deserialise.

**Surfacing to the LLM:** Tool descriptions are embedded in the system prompt on
every request. The model picks which ones to call based on the descriptions.
Descriptions are written to guide the model's choice, e.g. "always call list_files
first with directory='.'" 

**Results:** Tool outputs flow back as `user` messages with the label
`Tool result for <name>:`. The model sees the result inline in the conversation
and can reason across multiple file reads.

**Failure:** All exceptions are caught inside `_run_tool()` and returned as
`"ERROR: ..."` strings. The model reads the error and either retries or tells
the user what went wrong.

---

### Skills

A skill is a `.md` file in the `skills/` folder. Skills are loaded by
`skills_loader.py` and injected into the system prompt at the start of every turn.

**When does the LLM see them:** All at once, every turn, appended to the system
prompt. This works well for a small set of skills (< 20). If skills grew to
hundreds, I'd switch to embedding-based retrieval — embed skill descriptions and
fetch the top-k most relevant for each query.

**Authoring format:** Plain Markdown. No YAML, no registration, no code. Drop a
`.md` file in `skills/` and it's active on the next turn — no restart needed.
`skills_loader.py` re-reads the directory on every agent turn.

**New skills without code changes:** Confirmed. Adding or editing a skill file
takes effect immediately on the next user message.

---

### State

Conversation history is stored as a JSON file per session in
`.agent_state/<session_id>.json`. Each entry is `{"role": "user"|"model", "content": "..."}`.

**What's stored:** Only the final user message and the model's final text response.
Tool-call intermediates are not stored. This keeps history clean and avoids
re-sending complex multi-turn tool sequences on restart.

**Restart:** On restart, stored history is rebuilt into the message list and
prepended before the new user message. The model sees the full prior conversation
and continues naturally.

**Pruning:** If history exceeds 60 messages, the oldest are dropped. The 60-message
window keeps context manageable while retaining many full exchanges. A smarter
approach would summarise older turns — a natural next step.

---

### Documents

The agent's understanding of a file depends on what the tool returns:

- **PDF:** `pdfplumber` extracts text per page and tables as pipe-separated rows.
- **Spreadsheet:** `pandas` extracts column names, numeric summary statistics
  (min/max/mean/sum), and the full data as a text table.
- **CSV:** Same pipeline as spreadsheet — pandas handles both.
- **Text:** Raw UTF-8 content, capped at 20,000 characters.

**Whose job is parsing:** The tool's. The runtime knows nothing about file formats.
The model knows nothing about file bytes. Tools are the translation layer.

---

### The Interface

A `readline`-based CLI REPL (`main.py`). Rich is used for Markdown rendering and
coloured output. The agent's responses render headers, tables, and bullet points
in the terminal.

**Key Windows fix:** On startup, `main.py` calls `os.chdir()` into the data folder,
so the agent always uses `"."` as the working path. This avoids backslash
over-escaping issues with Windows paths that contain spaces.

---

### User Control Without Editing Code

Three levers:

1. **Skills** — drop a `.md` file in `skills/` to change the agent's expertise
   and output format. Takes effect immediately, no restart.
2. **`.env`** — change `MODEL_NAME` to swap models, `MAX_ITERATIONS` to adjust
   depth, `SKILLS_DIR` to point at a different skills folder.
3. **Session IDs** — `python main.py --session project_x` gives a named,
   resumable context for different tasks.

---

## Adding a New Tool

1. Write a Python function in `tools/` that takes string args and returns a string.
2. Add it to `TOOL_REGISTRY` in `runtime.py` with a description and arg descriptions.
3. Done — the model discovers and uses it automatically via the system prompt.

## Adding a New Skill

1. Create `skills/my_skill.md`.
2. Write instructions in plain Markdown.
3. Active on the next agent turn — no restart needed.

---

## Free Tier Limits (Groq)

| Limit | Value |
|-------|-------|
| Requests per minute | 30 |
| Requests per day | 14,400 |
| Tokens per minute | 6,000 |

More than enough for development and demo purposes.

---

## AI Session Evidence

This project was built with Claude (claude.ai) as the AI pair-programmer.
The full conversation covering all major design decisions — the tool-calling
architecture, the Windows path fix, the switch from native function calling to
manual JSON dispatch — is included in `session_evidence/claude_session.md`.

Key decisions made during the session:
- Switched from Gemini (quota exhausted) to Groq (free, faster)
- Replaced native Groq tool-calling API with manual JSON dispatch after
  discovering `llama-3.3-70b-versatile` generates malformed `<function=...>`
  output that the API rejects
- Implemented `os.chdir()` fix for Windows path escaping issues
- Chose session-scoped JSON history over a database for simplicity
