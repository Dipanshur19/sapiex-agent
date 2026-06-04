# ⚡ Sapiex Agent Runtime

> A minimal AI agent built from scratch — no LangChain, no frameworks. Drop in files, ask questions, get answers.

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=flat&logo=python&logoColor=white)
![Groq](https://img.shields.io/badge/Groq-Llama_3.3_70B-F55036?style=flat)
![License](https://img.shields.io/badge/License-MIT-green?style=flat)
![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=flat)

---

## What it does

Sapiex reads your files — PDFs, Excel spreadsheets, CSVs — and lets you ask questions across all of them at once. It automatically flags discrepancies, compares data sources, and summarizes findings in clean Markdown.

```
You: Compare the spreadsheet and the PDF. Flag any discrepancies.

  ⚙ list_files(directory='.')
  ⚙ read_pdf(path='annual_report_2023.pdf')
  ⚙ read_spreadsheet(path='revenue_2023.xlsx')

Agent:
## Discrepancy Report

| Month    | PDF ($)   | Spreadsheet ($) | Match? |
|----------|-----------|-----------------|--------|
| January  | 1,200,000 | 1,200,000       | ✅     |
| February | 1,100,000 | 1,050,000       | ❌     |
| March    | 1,350,000 | 1,350,000       | ✅     |
| ...      | ...       | ...             | ✅     |

⚠️ Discrepancy found in February — $50,000 gap (4.5%).
   PDF claims $1,100,000. Spreadsheet shows $1,050,000.
   All other months match exactly.
```

---

## Quick Start

```bash
# 1. Clone
git clone https://github.com/Dipanshur19/sapiex-agent.git
cd sapiex-agent

# 2. Create virtual environment
python -m venv venv
venv\Scripts\activate      # Windows
source venv/bin/activate   # Mac/Linux

# 3. Install dependencies
pip install -r requirements.txt

# 4. Get a FREE Groq API key — no credit card needed
#    https://console.groq.com/keys

# 5. Set up .env
cp .env.example .env
# Paste your key: GROQ_API_KEY=gsk_...

# 6. Run
python main.py ./your-data-folder
```

---

## Features

- **Multi-file reasoning** — reads PDFs, Excel (.xlsx), CSV, and plain text; reasons across all of them simultaneously
- **Automatic discrepancy detection** — compares data sources row by row and flags mismatches
- **Skills system** — drop a `.md` file into `skills/` to change agent behavior, no restart needed
- **Session persistence** — conversation history saved per session, survives restarts
- **Works with any model** — manual JSON tool dispatch instead of native function-calling API (works with Groq, OpenAI, Anthropic)
- **Web frontend** — deployed React app, anyone can use it in the browser

---

## Usage

```bash
# Default session
python main.py

# Session tied to a data folder
python main.py ./data

# Named session (resumable across restarts)
python main.py --session my_project
```

**Built-in commands:**
```
/history     Show conversation history
/sessions    List all saved sessions
/new         Start a fresh session
/clear       Delete current session
/session <id>  Switch to a different session
/quit        Exit
```

---

## Project Structure

```
sapiex-agent/
├── main.py              # CLI entry point (REPL)
├── runtime.py           # Agent loop — manual JSON tool dispatch
├── state.py             # Session history persistence (JSON)
├── skills_loader.py     # Dynamic skill loading from skills/
├── config.py            # Environment variable loader
├── tools/
│   ├── pdf_tool.py          # pdfplumber — text + table extraction
│   ├── spreadsheet_tool.py  # pandas — Excel + CSV with summaries
│   ├── file_tool.py         # Directory listing
│   └── text_tool.py         # Plain text / JSON / Markdown
├── skills/              # Drop .md files here — active on next turn
│   ├── financial_analyst.md
│   ├── data_comparator.md
│   └── summarizer.md
├── test_data/           # Sample files for demo
├── .agent_state/        # Auto-created session storage
├── .env.example
└── requirements.txt
```

---

## How it works

### The Agent Loop
Instead of using the provider's native tool-calling API (which generates malformed output with open-source models), tools are described in the system prompt. The model emits a plain JSON block when it wants to call a tool:

```json
{"action": "read_pdf", "args": {"path": "annual_report.pdf"}}
```

The runtime parses this, executes the tool, feeds the result back as a message, and loops until no more tool calls are needed.

```
User message
     │
     ▼
  LLM call ──► JSON action found? ──► Execute tool ──► Feed result back
                      │                                        │
                      │ No                                     │
                      ▼                                        ▼
               Final text answer ◄────────────────────────── Loop
```

### Skills
Skills are `.md` files in the `skills/` folder. They're injected into the system prompt on every turn. Drop a new file — it's active immediately, no restart needed.

### State
Conversation history is stored as `JSON` in `.agent_state/<session_id>.json`. Only final user + agent messages are stored (not intermediate tool calls), keeping history clean for replay. Pruned at 60 messages.

---

## Adding a New Tool

1. Write a Python function in `tools/` — takes string args, returns a string
2. Add it to `TOOL_REGISTRY` in `runtime.py` with a name and description
3. Done — the model discovers and uses it automatically

## Adding a New Skill

1. Create `skills/my_skill.md`
2. Write instructions in plain Markdown
3. Active on the next agent turn — no restart needed

---

## Why No Framework?

LangChain, LlamaIndex, and similar frameworks abstract away the loop, tool dispatch, and history management. Building those from scratch means:

- Full control over how tool failures are handled
- No dependency on framework-specific APIs that change constantly
- The agent works with any LLM provider by changing one line in `.env`
- The code is small enough to read in 15 minutes

---

## Tech Stack

| Layer | Tech |
|---|---|
| LLM | Groq API — Llama 3.3 70B (free tier) |
| PDF parsing | pdfplumber |
| Spreadsheet parsing | pandas + openpyxl |
| CLI rendering | Rich |
| Web frontend | React + Vite + Netlify |
| Session storage | JSON (flat files) |

---

## Free Tier Limits (Groq)

| Limit | Value |
|---|---|
| Requests per minute | 30 |
| Requests per day | 14,400 |
| Context window | 128k tokens |

No credit card required.

---

## Live Demo

Try the web version (no Python needed):
**[sapiex-agent.netlify.app](https://sapiex-agent.netlify.app)**

Enter your free Groq API key, upload a file, and ask anything.

---

## License

MIT — free to use, modify, and distribute.

---

<p align="center">Built by <a href="https://github.com/Dipanshur19">Dipanshu Raj</a> · IIT Kanpur</p>
