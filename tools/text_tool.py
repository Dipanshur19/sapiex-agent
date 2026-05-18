"""
tools/text_tool.py — Read plain text files (.txt, .md, .json, etc.)
"""
import os

MAX_CHARS = 20_000  # Protect context window


def read_text_file(path: str) -> str:
    """Read any plain-text file and return its contents."""
    path = os.path.expanduser(path)

    if not os.path.exists(path):
        return f"ERROR: File not found: '{path}'"

    try:
        with open(path, "r", encoding="utf-8", errors="replace") as f:
            content = f.read()

        if len(content) > MAX_CHARS:
            content = content[:MAX_CHARS]
            return (
                f"=== {os.path.basename(path)} (first {MAX_CHARS} chars) ===\n"
                + content
                + f"\n\n[File truncated — {len(content)} chars shown of total]"
            )

        return f"=== {os.path.basename(path)} ===\n{content}"

    except Exception as e:
        return f"ERROR reading '{path}': {type(e).__name__}: {e}"
