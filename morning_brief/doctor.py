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
    provider = raw.get("provider") or ("claude-code" if backend == "claude-code" else "anthropic")
    model = raw.get("model", "(not set)")
    topic = (raw.get("topic") or {}).get("name", "(not set)")

    console.print("\n[bold]Config[/bold]")
    console.print(f"  backend:  {backend}")
    console.print(f"  provider: {provider}")
    console.print(f"  model:    {model}")
    console.print(f"  topic:    {topic}")

    env_path = resolved.parent / ".env"
    if env_path.exists():
        _ok(".env found:", str(env_path))
        load_env_file(env_path)
    else:
        _warn(".env not found:", str(env_path))

    console.print("\n[bold]Provider credentials[/bold]")

    problems = 0

    if backend == "api" and provider == "anthropic":
        value = os.environ.get("ANTHROPIC_API_KEY", "")
        if value:
            _ok("ANTHROPIC_API_KEY set:", _mask(value))
        else:
            _fail("ANTHROPIC_API_KEY missing")
            problems += 1

    elif backend == "api" and provider == "openai-compatible":
        value = os.environ.get("OPENAI_API_KEY", "")
        if value:
            _ok("OPENAI_API_KEY set:", _mask(value))
        else:
            _fail("OPENAI_API_KEY missing")
            problems += 1

        _ok("OPENAI_BASE_URL:", os.environ.get("OPENAI_BASE_URL", "https://api.openai.com/v1"))

    elif backend == "api" and provider == "ollama":
        _ok("OLLAMA_BASE_URL:", os.environ.get("OLLAMA_BASE_URL", "http://localhost:11434"))
        if shutil.which("ollama"):
            _ok("Ollama CLI found")
        else:
            _warn("Ollama CLI not found on PATH")

    elif backend == "claude-code":
        if shutil.which("claude"):
            _ok("Claude Code CLI found")
        else:
            _fail("Claude Code CLI not found on PATH")
            problems += 1

    else:
        _fail("Unknown backend/provider:", f"{backend}/{provider}")
        problems += 1

    console.print("\n[bold]Email credentials[/bold]")

    for key in ["EMAIL_SENDER", "EMAIL_APP_PASSWORD", "EMAIL_RECIPIENT"]:
        value = os.environ.get(key, "")
        if value:
            _ok(f"{key} set:", _mask(value))
        else:
            _fail(f"{key} missing")
            problems += 1

    _ok("SMTP_SERVER:", os.environ.get("SMTP_SERVER", "smtp.gmail.com"))
    _ok("SMTP_PORT:", os.environ.get("SMTP_PORT", "587"))

    console.print("")
    if problems:
        _fail(f"Doctor found {problems} problem(s).")
        return 1

    _ok("Doctor found no blocking problems.")
    return 0
