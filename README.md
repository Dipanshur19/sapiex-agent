# Sapiex Agent Runtime

A minimal agent runtime built from scratch in Python, using the Gemini API (free tier).

---

## Quick Start

```bash
# 1. Clone / download this folder

# 2. Install dependencies
pip install -r requirements.txt

# 3. Get a FREE Gemini API key
#    → https://aistudio.google.com/app/apikey

# 4. Set up your .env file
cp .env.example .env
# Open .env and paste your key: GEMINI_API_KEY=AIza...

# 5. Run the agent
python main.py                        # default session
python main.py ./path/to/data/folder  # session tied to a folder
python main.py --session my_task      # named session (resumable)
```

---

## What it can do

```
You: Here's a folder. It has a spreadsheet of monthly revenue and a PDF of
     last year's annual report. Tell me whether the trajectory in the 
     spreadsheet matches what the PDF claims happened, and flag anything 
     that looks off.

Agent: ⚙ list_files(directory='./data')
       ⚙ read_spreadsheet(path='./data/revenue_2023.xlsx')
       ⚙ read_pdf(path='./data/annual_report_2023.pdf')

       **Comparison: Spreadsheet vs Annual Report**

       | Month | Spreadsheet | PDF Claim | Match? |
       |-------|-------------|-----------|--------|
       | Jan   | $1.20M      | $1.20M    | ✅     |
       | Feb   | $1.05M      | $1.10M    | ❌     |
       ...

       **Discrepancy found**: February shows $50K gap. PDF states $1.10M;
       spreadsheet shows $1.05M. All other months match exactly.
```

---

## Folder structure

```
sapiex-agent/
├── main.py              ← CLI entry point (REPL)
├── runtime.py           ← The agent loop — tool dispatch, history, loop control
├── state.py             ← Persist / load conversation history (JSON files)
├── skills_loader.py     ← Load .md skill files from skills/ dynamically
├── config.py            ← Reads .env variables
├── tools/
│   ├── pdf_tool.py      ← pdfplumber: text + table extraction
│   ├── spreadsheet_tool.py  ← pandas: Excel + CSV with numeric summaries
│   ├── file_tool.py     ← Directory tree listing
│   └── text_tool.py     ← Plain text / JSON / Markdown files
├── skills/              ← Drop .md files here to add new skills
│   ├── financial_analyst.md
│   └── data_comparator.md
├── .agent_state/        ← Auto-created: one JSON file per session
├── requirements.txt
├── .env.example
└── README.md
```

---

## Design decisions

### The loop

The loop runs inside `run_turn()` in `runtime.py`. Each iteration:

1. Check the model's response for `function_call` parts.
2. If present: execute each tool, collect results, send them back as `FunctionResponse` parts.
3. If absent: the model produced text — we're done.

**Termination**: The loop exits when the model returns no function calls, or after `MAX_ITERATIONS` (default: 10). The iteration cap is a hard safety rail — if the model keeps calling tools without settling, we return whatever text exists. In practice, Gemini Flash settles in 1-3 tool rounds for file-analysis tasks.

**Malformed output**: If a tool is called with wrong arguments, `_execute_tool()` catches the `TypeError` and returns an error string to the model. The model then either retries with corrected args or explains the error to the user. We never crash — errors become tool results.

---

### Tools

A tool is a Python function + a `FunctionDeclaration` that describes it to Gemini. The `TOOL_REGISTRY` dict in `runtime.py` pairs each declaration with its implementation.

**Shape**: Each tool takes simple string arguments and returns a string. Strings are the universal interface — no complex types to serialise.

**Surfacing to the LLM**: All tools are sent in every request as part of the `tools=` parameter. Gemini picks which ones to call based on the descriptions. Descriptions are the primary documentation — they're written to guide the model's choice (e.g., "call list_files FIRST to see what's available").

**Results**: Tool outputs flow back as `FunctionResponse` parts in the next chat message. Gemini sees the result inline in the conversation, which is why it can reason about multiple files at once.

**Failure**: Exceptions are caught inside `_execute_tool()` and returned as `"ERROR: ..."` strings. The model reads the error and either retries or tells the user something went wrong.

---

### Skills

A skill is a `.md` file in the `skills/` folder. Skills are loaded by `skills_loader.py` and injected into the system prompt at the start of every turn.

**When does the LLM see them**: All at once, every turn, prepended to the system prompt under `## Loaded Skills`. This works well for a small set of skills (< 20). If skills grew to hundreds, I'd switch to retrieval — embed skill descriptions and fetch the top-k most relevant ones for the query.

**Authoring format**: Plain Markdown. No YAML front matter, no registration, no code. Drop a `.md` file in `skills/` and it's active on the next turn — no restart needed.

**New skills without code changes**: Confirmed. The loader re-reads the `skills/` directory on every agent turn, so edits and additions take effect immediately.

---

### State

Conversation history is stored as a JSON file in `.agent_state/<session_id>.json`. Each entry is `{"role": "user"|"model", "content": "..."}`.

**What's stored**: Only the final user message and the model's final text response. Tool-call intermediates (function calls and results) are not stored. This keeps history clean and avoids Gemini's strict multi-turn history format requirements when replaying complex tool-call sequences.

**Restart**: On restart, the stored history is converted back to Gemini's chat format and passed to `start_chat(history=...)`. The model sees the full conversation and can continue naturally.

**Pruning**: If history exceeds 60 messages, the oldest messages are dropped (`state.py: MAX_STORED`). The 60-message window keeps the context manageable while retaining several full exchanges. A smarter approach would summarise older turns — that's a bonus feature.

---

### Documents

The agent's understanding of a file depends on what the tool returns:

- **PDF**: `pdfplumber` extracts text per page and tables as pipe-separated rows. The model sees text — it reasons over it like a document.
- **Spreadsheet**: `pandas` extracts column names, numeric summary statistics (min/max/mean/sum per column), and the full data as a text table. Summary stats let the model spot anomalies even before reading individual rows.
- **CSV**: Same as spreadsheet — pandas handles both.
- **Text**: Raw UTF-8 content, capped at 20,000 characters.

**Whose job is parsing**: The tool's. The runtime knows nothing about file formats. The model knows nothing about file bytes. The tools are the translation layer.

---

### The interface

A `readline`-based CLI REPL (`main.py`). The user runs `python main.py` and types questions. Rich is used for Markdown rendering and coloured output — the agent's responses render headers, tables, and bullet points correctly in the terminal.

I chose CLI because it requires zero infrastructure (no server, no browser, no port), works on every OS, and is the fastest path to a working demo. The agent is good enough to not need a fancy UI.

---

### User control without editing code

Three levers:

1. **Skills** — drop a `.md` file in `skills/` to change the agent's expertise and output format.
2. **`.env`** — change `MODEL_NAME` to swap models, `MAX_ITERATIONS` to adjust depth, `SKILLS_DIR` to point at a different skills folder.
3. **Session IDs** — `python main.py --session project_x` gives you a named, resumable context for different tasks.

No config UI, no plugin registry, no class hierarchy. Flat files all the way down.

---

## Adding a new tool

1. Write a Python function in `tools/` that takes string args and returns a string.
2. Add it to `TOOL_REGISTRY` in `runtime.py` with a `FunctionDeclaration`.
3. That's it — the model will discover and use it automatically.

## Adding a new skill

1. Create `skills/my_skill.md`.
2. Write instructions in plain Markdown.
3. The agent picks it up on the next turn — no restart needed.

---

## Free tier limits (Gemini Flash)

| Limit | Value |
|-------|-------|
| Requests per minute | 15 |
| Requests per day | 1,500 |
| Tokens per minute | 1,000,000 |

More than enough for development and demo purposes.

---

## Running in VS Code

1. Open the `sapiex-agent/` folder in VS Code.
2. Open a terminal (`Ctrl+` `` ` ``).
3. Create a virtual environment:
   ```bash
   python -m venv venv
   venv\Scripts\activate      # Windows
   # or
   source venv/bin/activate   # Mac/Linux
   ```
4. Install deps: `pip install -r requirements.txt`
5. Copy `.env.example` to `.env` and add your key.
6. Run: `python main.py`
