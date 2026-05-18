"""
skills_loader.py — Load user-defined skills from the skills/ directory.

Design choices:
- A "skill" is just a Markdown file in the skills/ folder.
- Every .md file found is read and injected into the system prompt.
- The agent sees ALL skills at the start of every turn (small enough set
  that this is fine; if skills grew large we'd switch to on-demand retrieval).
- Users add expertise by dropping a new .md file — zero code changes needed.
- Skill files are re-read on every agent turn, so edits take effect immediately
  without restarting the agent.
"""
import os
from config import SKILLS_DIR


def load_skills() -> str:
    """
    Read all .md files from the skills directory and return them
    as a formatted string ready to be injected into the system prompt.
    Returns an empty string if no skills are found.
    """
    if not os.path.isdir(SKILLS_DIR):
        return ""

    skill_blocks: list[str] = []

    for filename in sorted(os.listdir(SKILLS_DIR)):
        if not filename.endswith(".md"):
            continue
        filepath = os.path.join(SKILLS_DIR, filename)
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read().strip()
            if content:
                # Use the filename (without extension) as the skill title
                title = filename[:-3].replace("_", " ").replace("-", " ").title()
                skill_blocks.append(f"### Skill: {title}\n{content}")
        except IOError:
            continue  # skip unreadable files silently

    if not skill_blocks:
        return ""

    header = (
        "## Loaded Skills\n"
        "The following expert skills are available to guide your analysis:\n"
    )
    return header + "\n\n---\n\n".join(skill_blocks)
