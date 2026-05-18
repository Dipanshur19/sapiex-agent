"""
runtime.py — Agent loop using manual JSON tool dispatch.

Instead of relying on the provider's native function-calling API (which is
unreliable on open-source models), we describe tools in the system prompt
and ask the model to emit a JSON action block when it wants to call one.
We parse that JSON ourselves and feed results back. This works with ANY model.

Loop per turn:
  1. Build messages with tool descriptions in system prompt.
  2. Send to model.
  3. If response contains {"action": ...} JSON → execute tool, loop back.
  4. If response is plain text → done.
"""

import json
import re
from groq import Groq

from config import GROQ_API_KEY, MODEL_NAME, MAX_ITERATIONS
from state import load_history, append_and_save
from skills_loader import load_skills
from tools.pdf_tool import read_pdf
from tools.spreadsheet_tool import read_spreadsheet
from tools.file_tool import list_files
from tools.text_tool import read_text_file

_client = Groq(api_key=GROQ_API_KEY)
_working_dir: str = "."


def set_working_dir(path: str) -> None:
    global _working_dir
    _working_dir = path


# ── Tool registry ─────────────────────────────────────────────────────────────

TOOL_REGISTRY = {
    "list_files": {
        "fn": list_files,
        "description": 'List all files in a directory.',
        "args": {"directory": 'Path to folder. Use "." for the current folder.'},
    },
    "read_pdf": {
        "fn": read_pdf,
        "description": "Extract all text and tables from a PDF file.",
        "args": {"path": "Filename of the PDF, e.g. annual_report.pdf"},
    },
    "read_spreadsheet": {
        "fn": read_spreadsheet,
        "description": "Read an Excel (.xlsx) or CSV file. Returns column names and data.",
        "args": {"path": "Filename of the spreadsheet, e.g. revenue.xlsx"},
    },
    "read_text_file": {
        "fn": read_text_file,
        "description": "Read a plain text file (.txt, .md, .json).",
        "args": {"path": "Filename of the text file"},
    },
}


def _build_tool_descriptions() -> str:
    lines = []
    for name, info in TOOL_REGISTRY.items():
        args_desc = ", ".join(f'"{k}": "{v}"' for k, v in info["args"].items())
        lines.append(f'- {name}: {info["description"]} Args: {{{args_desc}}}')
    return "\n".join(lines)


def _build_system_prompt() -> str:
    tools_text = _build_tool_descriptions()
    skills = load_skills()
    skills_section = ("\n\n" + skills) if skills else ""

    return f"""You are a precise, analytical file-reading agent.

## Available Tools
{tools_text}

## How to use a tool
When you need to call a tool, output ONLY a JSON block like this — nothing else:
```json
{{"action": "tool_name", "args": {{"arg_name": "arg_value"}}}}
```

## Rules
- ALWAYS start with list_files using directory="." to see what files exist.
- After listing, use the exact filenames shown (e.g. "revenue.xlsx").
- Never output both a tool call AND text in the same response.
- Once you have all the information you need, write your final answer in clear Markdown.
- Never invent file contents — only report what tools return.{skills_section}"""


def _extract_action(text: str) -> dict | None:
    """
    Find and parse the first ```json ... ``` block that contains an 'action' key.
    Returns the parsed dict or None if not found.
    """
    # Match ```json ... ``` fenced blocks
    pattern = r"```(?:json)?\s*(\{.*?\})\s*```"
    matches = re.findall(pattern, text, re.DOTALL)
    for raw in matches:
        try:
            data = json.loads(raw)
            if "action" in data:
                return data
        except json.JSONDecodeError:
            continue

    # Fallback: look for a bare JSON object with "action" anywhere in text
    pattern2 = r'\{[^{}]*"action"\s*:[^{}]*\}'
    matches2 = re.findall(pattern2, text, re.DOTALL)
    for raw in matches2:
        try:
            data = json.loads(raw)
            if "action" in data:
                return data
        except json.JSONDecodeError:
            continue

    return None


def _run_tool(name: str, args: dict) -> str:
    if name not in TOOL_REGISTRY:
        return f"ERROR: Unknown tool '{name}'. Available: {list(TOOL_REGISTRY.keys())}"
    fn = TOOL_REGISTRY[name]["fn"]
    try:
        return str(fn(**args))
    except TypeError as e:
        return f"ERROR: Bad arguments for '{name}': {e}"
    except Exception as e:
        return f"ERROR: '{name}' failed — {type(e).__name__}: {e}"


def _to_message_history(stored: list[dict]) -> list[dict]:
    result = []
    for msg in stored:
        role = "assistant" if msg["role"] == "model" else msg["role"]
        result.append({"role": role, "content": msg["content"]})
    return result


def run_turn(session_id: str, user_message: str, on_tool_call=None) -> str:
    stored = load_history(session_id)
    messages = _to_message_history(stored)
    messages = [{"role": "system", "content": _build_system_prompt()}] + messages
    messages.append({"role": "user", "content": user_message})

    final_text = ""

    for _iteration in range(MAX_ITERATIONS):
        response = _client.chat.completions.create(
            model=MODEL_NAME,
            messages=messages,
            max_tokens=4096,
            temperature=0,
        )

        reply = (response.choices[0].message.content or "").strip()
        messages.append({"role": "assistant", "content": reply})

        action = _extract_action(reply)

        if action is None:
            # No tool call — this is the final answer
            final_text = reply
            break

        # Execute the tool
        tool_name = action.get("action", "")
        tool_args = action.get("args", {})

        if on_tool_call:
            on_tool_call(tool_name, tool_args)

        result = _run_tool(tool_name, tool_args)

        # Feed result back as a user message (tool result)
        messages.append({
            "role": "user",
            "content": f"Tool result for {tool_name}:\n{result}"
        })

    else:
        final_text = "[Agent hit iteration limit. Try a simpler question.]"

    if not final_text:
        final_text = "[No response generated. Try rephrasing.]"

    append_and_save(session_id, "user", user_message)
    append_and_save(session_id, "model", final_text)
    return final_text
