#!/usr/bin/env python3
"""Update all AI coding tools in parallel."""

from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import Optional

from rich.console import Console
from rich.live import Live
from rich.panel import Panel
from rich.table import Table

console = Console()


@dataclass
class Tool:
    name: str
    command: list[str]
    cwd: Optional[str] = None
    shell: bool = False


TOOLS = [
    Tool(name="codex", command=["npm", "update", "-g", "@openai/codex"]),
    Tool(name="gemini", command=["npm", "update", "-g", "@google/gemini-cli"]),
    Tool(name="crush", command=["brew", "upgrade", "crush"]),
    Tool(
        name="claude",
        command=["npm", "update"],
        cwd=os.path.expanduser("~/.claude/local"),
    ),
]


@dataclass
class UpdateResult:
    tool: Tool
    success: bool
    stdout: str
    stderr: str
    returncode: int


async def update_tool(tool: Tool, results: dict[str, UpdateResult | None]) -> UpdateResult:
    """Run update command for a single tool."""
    try:
        proc = await asyncio.create_subprocess_exec(
            *tool.command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
            cwd=tool.cwd,
        )
        stdout, stderr = await proc.communicate()
        result = UpdateResult(
            tool=tool,
            success=proc.returncode == 0,
            stdout=stdout.decode(),
            stderr=stderr.decode(),
            returncode=proc.returncode or 0,
        )
    except Exception as e:
        result = UpdateResult(
            tool=tool,
            success=False,
            stdout="",
            stderr=str(e),
            returncode=1,
        )
    results[tool.name] = result
    return result


def make_status_table(results: dict[str, UpdateResult | None]) -> Table:
    """Create a status table showing current progress."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Tool", style="bold")
    table.add_column("Status")

    for tool in TOOLS:
        result = results.get(tool.name)
        if result is None:
            status = "[yellow]updating...[/yellow]"
        elif result.success:
            status = "[green]done[/green]"
        else:
            status = "[red]failed[/red]"
        table.add_row(tool.name, status)

    return table


async def run_updates() -> list[UpdateResult]:
    """Run all updates in parallel with live status display."""
    results: dict[str, UpdateResult | None] = {tool.name: None for tool in TOOLS}

    with Live(make_status_table(results), console=console, refresh_per_second=4) as live:
        tasks = [update_tool(tool, results) for tool in TOOLS]

        async def update_display():
            while any(r is None for r in results.values()):
                live.update(make_status_table(results))
                await asyncio.sleep(0.25)
            live.update(make_status_table(results))

        display_task = asyncio.create_task(update_display())
        completed = await asyncio.gather(*tasks)
        await display_task

    return completed


def show_failures(results: list[UpdateResult]) -> None:
    """Show verbose output for failed updates."""
    failures = [r for r in results if not r.success]
    if not failures:
        return

    console.print()
    for result in failures:
        output = ""
        if result.stdout.strip():
            output += result.stdout
        if result.stderr.strip():
            if output:
                output += "\n"
            output += result.stderr

        console.print(
            Panel(
                output or f"Exit code: {result.returncode}",
                title=f"[red]{result.tool.name} failed[/red]",
                border_style="red",
            )
        )


def main() -> None:
    """Main entry point."""
    console.print("[bold]Updating AI tools...[/bold]\n")

    results = asyncio.run(run_updates())

    # Summary
    success_count = sum(1 for r in results if r.success)
    fail_count = len(results) - success_count

    console.print()
    if fail_count == 0:
        console.print(f"[green]All {success_count} tools updated successfully.[/green]")
    else:
        console.print(
            f"[yellow]{success_count} succeeded, {fail_count} failed.[/yellow]"
        )
        show_failures(results)


if __name__ == "__main__":
    main()
