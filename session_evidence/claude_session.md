# Claude AI Session Evidence
## Sapiex Intern Assignment — Agent Runtime

**Tool used:** Claude (claude.ai) — Claude Sonnet 4.6  
**Date:** May 2026  
**Purpose:** Design and build a minimal agent runtime from scratch

---

## Session Summary

This document records the key design decisions, problems encountered, and
solutions found during the build, as discussed with Claude AI.

---

## Decision 1: LLM Provider — Gemini → Groq

**Problem:** Started with Gemini free tier (`gemini-2.0-flash`). Hit quota
exhaustion immediately on first run:
```
ClientError: 429 RESOURCE_EXHAUSTED
Quota exceeded for metric: generate_content_free_tier_requests, limit: 0
```

**Options considered:**
- Wait for daily quota reset (too slow for development)
- Enable billing on Google AI Studio
- Switch provider entirely

**Decision:** Switched to Groq with `llama-3.3-70b-versatile`.  
**Rationale:** Free forever (30 req/min, 14,400/day), no credit card, fastest
inference (300+ tokens/sec), OpenAI-compatible API.

**Changes made:**
- `requirements.txt`: `google-genai` → `groq>=0.9.0`
- `config.py`: `GEMINI_API_KEY` → `GROQ_API_KEY`
- `runtime.py`: rewrote from `google.genai` SDK to Groq SDK

---

## Decision 2: Native Tool Calling → Manual JSON Dispatch

**Problem:** After switching to Groq, used the native `tools=` parameter in the
API call. Got repeated 400 errors:
```
BadRequestError: 400 - tool_use_failed
failed_generation: '<function=list_files {"directory": "."} </function>'
```

The model was ignoring the OpenAI-format tool schema and generating its own
`<function=...>` format, which Groq then rejected as malformed.

Tried model `llama3-groq-70b-8192-tool-use-preview` (fine-tuned for tool use)
but it was decommissioned.

**Root cause:** Open-source models served via Groq don't reliably follow the
OpenAI function-calling format. The model generates Llama's native format
instead, which the proxy layer rejects.

**Decision:** Remove native tool calling entirely. Describe tools in the system
prompt and ask the model to emit a JSON block:
```json
{"action": "tool_name", "args": {"arg": "value"}}
```
Parse this ourselves with regex + `json.loads()`.

**Rationale:** Works with any model, any provider. No API-specific code. The
model is very good at following "emit this exact JSON format" instructions.

**Key insight:** A tool-calling abstraction in the API is convenient but not
required. The loop, dispatch, and result injection are ours to implement —
that's the whole point of the assignment.

---

## Decision 3: Windows Path Fix (os.chdir)

**Problem:** Running `python main.py ./test_data` on Windows produced a path
like `C:\Users\dipan\Downloads\files (3)\sapiex-agent\test_data`. When injected
into the system prompt and passed through JSON to the model, the backslashes and
spaces caused triple-escaping:
```
'failed_generation': '<function=list_files {"directory": 
"C:\\\\\\\\Users\\\\\\\\dipan\\\\\\\\..."}</function>'
```

**Options considered:**
- Convert path to forward slashes before injecting
- Use `pathlib.Path` with `.as_posix()`
- Change Python's working directory to the data folder

**Decision:** `os.chdir(abs_folder)` in `main.py` before starting the REPL.
Then tell the agent to always use `"."` as the directory path.

**Rationale:** One character path, impossible to escape badly, works on every OS.
The model doesn't need to know the absolute path — it just needs to know where
to look, and `"."` is always correct after `chdir`.

---

## Decision 4: State Storage — JSON Files

**Problem:** Where to store conversation history so it survives restarts?

**Options considered:**
- SQLite database (more structured, queryable)
- In-memory only (no persistence)
- JSON file per session (simple, portable)

**Decision:** One JSON file per session in `.agent_state/<session_id>.json`.

**Rationale:** Zero dependencies, readable with any text editor, trivial to
implement. The session ID doubles as the filename. For 60 messages of text
history, a flat JSON file is faster to read/write than any database.

**Tradeoff:** Doesn't scale past ~1,000 sessions (directory listing gets slow).
Acceptable for week-one scope.

---

## Decision 5: Skills as Plain Markdown Files

**Problem:** How to let users customize agent behaviour without editing code?

**Options considered:**
- Python plugin files (requires code, restart)
- YAML config with structured schema (more complex authoring)
- Plain Markdown files re-read every turn (zero friction)

**Decision:** Markdown files in `skills/` folder, re-read on every agent turn
and injected into the system prompt.

**Rationale:** A user can write a skill in a text editor. No YAML syntax to
learn, no registration step, no restart. The agent picks it up on the next
message. Files are sorted alphabetically so load order is deterministic.

**Live test confirmed:** Added `summarizer.md` while agent was running, asked
for a summary immediately — agent applied the new skill format without restart.

---

## What the AI Got Wrong (and How I Fixed It)

1. **Suggested `llama3-groq-70b-8192-tool-use-preview`** — already decommissioned
   by Groq. Caught by testing, reverted to `llama-3.3-70b-versatile`.

2. **Initially injected full Windows absolute path into system prompt** — caused
   escaping issues. Pushed back, AI suggested `os.chdir()` as cleaner solution.

3. **First README draft was too long** — trimmed to focus on design decisions
   the assignment explicitly asks for.

---

## Files Modified During Session

| File | Changes |
|------|---------|
| `config.py` | Gemini → Groq API key and model |
| `runtime.py` | Full rewrite: Gemini SDK → Groq, then native tools → JSON dispatch |
| `main.py` | Added `os.chdir()` fix, `set_working_dir()` call |
| `requirements.txt` | `google-genai` → `groq` |
| `.env.example` | Updated for Groq |
| `README.md` | Full design answers added |
