"""
state.py — Conversation history persistence.

Design choices:
- History is stored as a JSON file per session in STATE_DIR.
- Each entry is {"role": "user"|"model", "content": "..."}.
- Tool-call intermediates are NOT stored — only the user message and the
  final text the model produced. This keeps the stored history clean and
  lets us replay it as a normal chat history on restart.
- Pruning: if history grows beyond MAX_STORED, we drop the oldest messages
  (but always keep the most recent ones so context stays relevant).
"""
import json
import os
from config import STATE_DIR

MAX_STORED = 60  # messages before pruning kicks in


def _session_path(session_id: str) -> str:
    os.makedirs(STATE_DIR, exist_ok=True)
    # Sanitise session_id so it's a safe filename
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in session_id)
    return os.path.join(STATE_DIR, f"{safe}.json")


def load_history(session_id: str) -> list[dict]:
    """Return the stored message list for this session, or [] if none."""
    path = _session_path(session_id)
    if not os.path.exists(path):
        return []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError):
        return []


def save_history(session_id: str, history: list[dict]) -> None:
    """Persist the message list to disk."""
    path = _session_path(session_id)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(history, f, indent=2, ensure_ascii=False)


def append_and_save(session_id: str, role: str, content: str) -> list[dict]:
    """Add one message to history, prune if needed, and save."""
    history = load_history(session_id)
    history.append({"role": role, "content": content})
    # Prune: keep last MAX_STORED messages
    if len(history) > MAX_STORED:
        history = history[-MAX_STORED:]
    save_history(session_id, history)
    return history


def list_sessions() -> list[str]:
    """Return all known session IDs."""
    if not os.path.exists(STATE_DIR):
        return []
    return [
        f.replace(".json", "")
        for f in os.listdir(STATE_DIR)
        if f.endswith(".json")
    ]


def delete_session(session_id: str) -> bool:
    path = _session_path(session_id)
    if os.path.exists(path):
        os.remove(path)
        return True
    return False
