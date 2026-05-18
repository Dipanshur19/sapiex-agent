"""
tools/file_tool.py — List files in a directory.

Design: The agent uses this as its first step to understand what documents
are available before deciding which tools to call next.
"""
import os


def list_files(directory: str) -> str:
    """
    Recursively list all files in a directory with sizes.
    Returns a tree-like string representation.
    """
    directory = os.path.expanduser(directory)

    if not os.path.exists(directory):
        return f"ERROR: Directory '{directory}' does not exist."

    if not os.path.isdir(directory):
        # It's a single file — just describe it
        size = os.path.getsize(directory)
        return f"'{directory}' is a file ({size} bytes), not a directory."

    lines: list[str] = [f"Contents of: {os.path.abspath(directory)}\n"]
    file_count = 0

    for root, dirs, files in os.walk(directory):
        # Skip hidden dirs like .git, .agent_state
        dirs[:] = [d for d in sorted(dirs) if not d.startswith(".")]

        depth = root.replace(directory, "").count(os.sep)
        indent = "  " * depth
        folder_name = os.path.basename(root) or directory
        lines.append(f"{indent}📁 {folder_name}/")

        sub_indent = "  " * (depth + 1)
        for fname in sorted(files):
            if fname.startswith("."):
                continue
            fpath = os.path.join(root, fname)
            try:
                size = os.path.getsize(fpath)
                size_str = _human_size(size)
            except OSError:
                size_str = "?"
            # Add a hint about what tool to use
            hint = _file_hint(fname)
            lines.append(f"{sub_indent}📄 {fname}  ({size_str}){hint}")
            file_count += 1

    lines.append(f"\nTotal: {file_count} file(s)")
    return "\n".join(lines)


def _human_size(size: int) -> str:
    for unit in ("B", "KB", "MB", "GB"):
        if size < 1024:
            return f"{size:.1f} {unit}"
        size /= 1024
    return f"{size:.1f} TB"


def _file_hint(filename: str) -> str:
    ext = os.path.splitext(filename)[1].lower()
    hints = {
        ".pdf": "  → use read_pdf",
        ".xlsx": "  → use read_spreadsheet",
        ".xls": "  → use read_spreadsheet",
        ".csv": "  → use read_spreadsheet",
        ".txt": "  → use read_text_file",
        ".md": "  → use read_text_file",
        ".json": "  → use read_text_file",
    }
    return hints.get(ext, "")
