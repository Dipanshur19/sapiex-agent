"""
main.py — CLI entry point for the Sapiex Agent.

Usage:
    python main.py                   # default session
    python main.py ./my-data-folder  # session tied to a specific folder
    python main.py --session my_task # named session (for restart)

Commands:
    /quit  /new  /history  /sessions  /clear  /session <id>
"""

import os
import argparse
import time

from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.rule import Rule

from runtime import run_turn, set_working_dir
from state import load_history, delete_session, list_sessions

console = Console()


def session_id_from_folder(folder: str) -> str:
    abs_path = os.path.abspath(folder)
    safe = abs_path.replace(os.sep, "_").replace(":", "").replace(" ", "_")
    return safe.strip("_")[:80]


def new_session_id() -> str:
    return f"session_{int(time.time())}"


def on_tool_call(tool_name: str, args: dict) -> None:
    args_str = ", ".join(f"{k}={repr(v)}" for k, v in args.items())
    console.print(f"  [dim cyan]⚙ {tool_name}({args_str})[/dim cyan]")


def cmd_history(session_id: str) -> None:
    history = load_history(session_id)
    if not history:
        console.print("[dim]No history for this session yet.[/dim]")
        return
    console.print(f"\n[bold]Session:[/bold] {session_id} | {len(history)} messages\n")
    for msg in history:
        role = msg["role"]
        content = msg["content"]
        label = "[bold blue]You:[/bold blue]" if role == "user" else "[bold green]Agent:[/bold green]"
        console.print(f"{label} {content[:200]}")
        console.print()


def cmd_sessions() -> None:
    sessions = list_sessions()
    if not sessions:
        console.print("[dim]No saved sessions found.[/dim]")
        return
    console.print(f"\n[bold]Saved sessions ({len(sessions)}):[/bold]")
    for s in sessions:
        console.print(f"  • {s}")
    console.print()


def cmd_clear(session_id: str) -> None:
    if delete_session(session_id):
        console.print(f"[yellow]Session '{session_id}' cleared.[/yellow]")
    else:
        console.print("[dim]Nothing to clear.[/dim]")


def main() -> None:
    parser = argparse.ArgumentParser(description="Sapiex Agent Runtime")
    parser.add_argument("folder", nargs="?", default=None)
    parser.add_argument("--session", "-s", default=None)
    args = parser.parse_args()

    abs_folder = None
    if args.folder and os.path.isdir(args.folder):
        abs_folder = os.path.abspath(args.folder)
        # KEY FIX: change Python's working directory to the data folder.
        # Now the agent can always use "." as the path — no spaces,
        # no backslashes, no escaping issues on Windows.
        os.chdir(abs_folder)
        set_working_dir(".")

    if args.session:
        session_id = args.session
    elif abs_folder:
        session_id = session_id_from_folder(abs_folder)
    else:
        session_id = "default"

    console.print()
    console.print(Panel.fit(
        "[bold blue]Sapiex Agent Runtime[/bold blue]\n"
        "[dim]Groq · Llama 3.3 70B · PDF · Excel · CSV · Skills[/dim]",
        border_style="blue"
    ))
    console.print(f"[dim]Session ID:[/dim] [cyan]{session_id}[/cyan]")

    history = load_history(session_id)
    if history:
        console.print(f"[dim]Resuming session with [bold]{len(history)}[/bold] previous messages.[/dim]")
    else:
        console.print("[dim]New session started.[/dim]")

    if abs_folder:
        console.print(f"[dim]Working folder:[/dim] [cyan]{abs_folder}[/cyan]")

    console.print("[dim]Commands: /quit  /new  /history  /sessions  /clear  /session <id>[/dim]")
    console.print()

    while True:
        try:
            user_input = input("You: ").strip()
        except (EOFError, KeyboardInterrupt):
            console.print("\n[yellow]Goodbye![/yellow]")
            break

        if not user_input:
            continue

        if user_input == "/quit":
            console.print("[yellow]Goodbye![/yellow]")
            break
        if user_input == "/new":
            session_id = new_session_id()
            console.print(f"[green]New session started:[/green] {session_id}\n")
            continue
        if user_input == "/history":
            cmd_history(session_id)
            continue
        if user_input == "/sessions":
            cmd_sessions()
            continue
        if user_input == "/clear":
            cmd_clear(session_id)
            continue
        if user_input.startswith("/session "):
            new_id = user_input.split(" ", 1)[1].strip()
            if new_id:
                session_id = new_id
                h = load_history(session_id)
                console.print(f"[green]Switched to session:[/green] {session_id} ({len(h)} messages)\n")
            continue

        console.print("[dim]Thinking...[/dim]")
        console.print()

        try:
            response = run_turn(
                session_id=session_id,
                user_message=user_input,
                on_tool_call=on_tool_call,
            )
            console.print(Rule(style="dim"))
            console.print("[bold green]Agent:[/bold green]")
            console.print(Markdown(response))
            console.print()

        except Exception as e:
            console.print(f"[red bold]Error:[/red bold] {type(e).__name__}: {e}")
            console.print("[dim]Try rephrasing, or check your API key and file paths.[/dim]")
            console.print()


if __name__ == "__main__":
    main()
