#!/usr/bin/env python3
"""Update all AI coding tools in parallel."""

from __future__ import annotations

import asyncio
import os
import re
from dataclasses import dataclass, field
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
    version_command: Optional[list[str]] = None
    version_regex: str = r"(\d+\.\d+\.\d+)"


TOOLS = [
    Tool(
        name="codex",
        command=["npm", "update", "-g", "@openai/codex"],
        version_command=["codex", "--version"],
    ),
    Tool(
        name="gemini",
        command=["npm", "update", "-g", "@google/gemini-cli"],
        version_command=["gemini", "--version"],
    ),
    Tool(
        name="crush",
        command=["brew", "upgrade", "crush"],
        version_command=["crush", "--version"],
    ),
    Tool(
        name="claude",
        command=["npm", "update"],
        cwd=os.path.expanduser("~/.claude/local"),
        version_command=[os.path.expanduser("~/.claude/local/claude"), "--version"],
    ),
]


@dataclass
class UpdateResult:
    tool: Tool
    success: bool
    stdout: str
    stderr: str
    returncode: int
    old_version: Optional[str] = None
    new_version: Optional[str] = None


async def get_version(tool: Tool, timeout: float = 5.0) -> Optional[str]:
    """Get the current version of a tool."""
    if not tool.version_command:
        return None

    try:
        proc = await asyncio.create_subprocess_exec(
            *tool.version_command,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        try:
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=timeout)
        except asyncio.TimeoutError:
            proc.kill()
            return None

        if proc.returncode != 0:
            return None

        output = stdout.decode().strip()
        match = re.search(tool.version_regex, output)
        if match:
            return match.group(1)
        return None
    except Exception:
        return None


async def get_all_versions(tools: list[Tool]) -> dict[str, Optional[str]]:
    """Get versions of all tools in parallel."""

    async def get_one(tool: Tool) -> tuple[str, Optional[str]]:
        version = await get_version(tool)
        return tool.name, version

    results = await asyncio.gather(*[get_one(t) for t in tools])
    return dict(results)


def format_version_change(old: Optional[str], new: Optional[str]) -> str:
    """Format version change for display."""
    if old is None and new is None:
        return "[dim]unknown[/dim]"
    if old is None:
        return f"[dim]?[/dim] -> [green]{new}[/green]"
    if new is None:
        return f"{old} -> [dim]?[/dim]"
    if old == new:
        return f"[dim]{old}[/dim]"
    return f"{old} -> [green]{new}[/green]"


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


def make_status_table(
    results: dict[str, UpdateResult | None], show_versions: bool = False
) -> Table:
    """Create a status table showing current progress."""
    table = Table(show_header=False, box=None, padding=(0, 1))
    table.add_column("Tool", style="bold")
    table.add_column("Status")
    if show_versions:
        table.add_column("Version")

    for tool in TOOLS:
        result = results.get(tool.name)
        if result is None:
            status = "[yellow]updating...[/yellow]"
            row = [tool.name, status]
        elif result.success:
            status = "[green]done[/green]"
            row = [tool.name, status]
            if show_versions:
                row.append(format_version_change(result.old_version, result.new_version))
        else:
            status = "[red]failed[/red]"
            row = [tool.name, status]
            if show_versions:
                row.append(f"[dim]{result.old_version or '?'}[/dim]")

        if show_versions and len(row) == 2:
            row.append("")
        table.add_row(*row)

    return table


async def run_updates() -> list[UpdateResult]:
    """Run all updates in parallel with live status display."""
    # Phase 1: Get old versions
    console.print("[dim]Checking current versions...[/dim]")
    old_versions = await get_all_versions(TOOLS)

    # Phase 2: Run updates with live display
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

    # Phase 3: Get new versions
    console.print("[dim]Checking new versions...[/dim]")
    new_versions = await get_all_versions(TOOLS)

    # Attach versions to results
    for result in completed:
        result.old_version = old_versions.get(result.tool.name)
        result.new_version = new_versions.get(result.tool.name)

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

    # Final table with versions
    console.print()
    final_results = {r.tool.name: r for r in results}
    console.print(make_status_table(final_results, show_versions=True))

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
