"""Diagnostic checks for morning-brief setup."""

from __future__ import annotations

import os
import shutil
from pathlib import Path

import yaml
from rich.console import Console

from .config import CONFIG_SEARCH_PATHS, load_env_file, resolve_config_path

console = Console()


def _mask(value: str, keep: int = 4) -> str:
    """Mask secret-like values for display."""
    if not value:
        return ""
    if len(value) <= keep:
        return "***"
    return value[:2] + "***" + value[-keep:]


def _ok(label: str, detail: str = "") -> None:
    console.print(f"[green]✓[/green] {label} {detail}")


def _warn(label: str, detail: str = "") -> None:
    console.print(f"[yellow]![/yellow] {label} {detail}")


def _fail(label: str, detail: str = "") -> None:
    console.print(f"[red]✗[/red] {label} {detail}")


def run_doctor(config_path: Path | None = None) -> int:
    """Run local setup diagnostics. Returns a shell exit code."""
    console.print("[bold]morning-brief doctor[/bold]\n")

    try:
        resolved = resolve_config_path(config_path)
        _ok("Config found:", str(resolved))
    except FileNotFoundError:
        _fail("No config.yaml found.")
        console.print("\nSearched:")
        for path in CONFIG_SEARCH_PATHS:
            console.print(f"  - {path}")
        console.print("\nRun: [cyan]morning-brief init[/cyan]")
        return 1

    try:
        raw = yaml.safe_load(resolved.read_text()) or {}
        _ok("Config YAML parsed")
    except Exception as exc:
        _fail("Config YAML could not be parsed:", str(exc))
        return 1

    backend = raw.get("backend", "api")
    model = raw.get("model", "(not set)")
    topic = (raw.get("topic") or {}).get("name", "(not set)")

    console.print("\n[bold]Config[/bold]")
    console.print(f"  backend: {backend}")
    console.print(f"  model:   {model}")
    console.print(f"  topic:   {topic}")

    env_path = resolved.parent / ".env"
    if env_path.exists():
        _ok(".env found:", str(env_path))
        load_env_file(env_path)
    else:
        _warn(".env not found:", str(env_path))

    console.print("\n[bold]Credentials[/bold]")

    required = []
    if backend == "api":
        required.append("ANTHROPIC_API_KEY")

    required.extend(["EMAIL_SENDER", "EMAIL_APP_PASSWORD", "EMAIL_RECIPIENT"])

    problems = 0
    for key in required:
        value = os.environ.get(key, "")
        if value:
            _ok(f"{key} set:", _mask(value))
        else:
            _fail(f"{key} missing")
            problems += 1

    smtp_server = os.environ.get("SMTP_SERVER", "smtp.gmail.com")
    smtp_port = os.environ.get("SMTP_PORT", "587")
    _ok("SMTP_SERVER:", smtp_server)
    _ok("SMTP_PORT:", smtp_port)

    console.print("\n[bold]Backend checks[/bold]")

    if backend == "claude-code":
        if shutil.which("claude"):
            _ok("Claude Code CLI found")
        else:
            _fail("Claude Code CLI not found on PATH")
            problems += 1
    elif backend == "api":
        _ok("API backend selected")
    else:
        _fail("Unknown backend:", str(backend))
        problems += 1

    console.print("")
    if problems:
        _fail(f"Doctor found {problems} problem(s).")
        return 1

    _ok("Doctor found no blocking problems.")
    return 0
