"""Sensitive-file detection and user confirmation."""

from __future__ import annotations

from pathlib import Path

import pathspec

from codectx.config.defaults import SENSITIVE_PATTERNS


def build_sensitive_spec() -> pathspec.PathSpec:
    """Build a pathspec for detecting sensitive files."""
    return pathspec.PathSpec.from_lines("gitignore", SENSITIVE_PATTERNS)


def find_sensitive_files(
    files: list[Path],
    root: Path,
) -> list[Path]:
    """Return files that match sensitive-file patterns.

    Args:
        files: List of absolute file paths to check.
        root: Repository root for relative path computation.

    Returns:
        List of sensitive files found.
    """
    spec = build_sensitive_spec()
    sensitive: list[Path] = []
    for f in files:
        try:
            rel = f.relative_to(root)
        except ValueError:
            continue
        if spec.match_file(rel.as_posix()):
            sensitive.append(f)
    return sensitive


def confirm_sensitive_files(sensitive: list[Path], root: Path) -> bool:
    """Prompt user to confirm inclusion of sensitive files.

    Args:
        sensitive: List of sensitive file paths.
        root: Repository root for display.

    Returns:
        True if user confirms, False otherwise.
    """
    if not sensitive:
        return True

    from rich.console import Console
    from rich.panel import Panel

    console = Console(stderr=True)
    file_list = "\n".join(f"  • {f.relative_to(root)}" for f in sensitive)
    console.print(
        Panel(
            f"[bold yellow]⚠ Potentially sensitive files detected:[/]\n\n{file_list}",
            title="Security Warning",
            border_style="yellow",
        )
    )
    response = console.input("[bold]Include these files? [y/N]: [/]").strip().lower()
    return response in ("y", "yes")
