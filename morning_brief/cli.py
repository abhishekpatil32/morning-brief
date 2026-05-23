"""Command-line interface for morning-brief.

Commands:
    morning-brief init        Interactive setup wizard
    morning-brief run         Generate + send today's digest
    morning-brief preview     Generate digest but print to stdout (no email)
    morning-brief test-email  Send a smoke-test email to verify SMTP
    morning-brief seen        Inspect the dedup list
"""
from __future__ import annotations

import shutil
import sys
from importlib.resources import as_file, files
from pathlib import Path

import click
from rich.console import Console
from rich.panel import Panel

from . import __version__
from .config import CONFIG_SEARCH_PATHS, Config, load_config
from .core import generate_digest, parse_digest, urls_in
from .dedup import load_seen, record
from .doctor import run_doctor
from .email_sender import send

console = Console()

def _copy_package_data_file(resource_name: str, target: Path) -> None:
    """Copy a packaged template/config file to a user-visible path."""
    resource = files("morning_brief").joinpath("data", resource_name)
    with as_file(resource) as src:
        shutil.copy(src, target)

def _load(config_path: Path | None, require_email: bool = True) -> Config:
    try:
        return load_config(config_path, require_email=require_email)
    except (FileNotFoundError, ValueError) as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@click.group()
@click.version_option(__version__, prog_name="morning-brief")
def main():
    """A local-first AI research/news briefing tool from topics you define."""


@main.command()
@click.option("--target", type=click.Path(path_type=Path), default=None,
              help="Where to install config (default: ./config.yaml).")
def init(target: Path | None) -> None:
    """Copy config.example.yaml and .env.example into place for editing."""
    target_config = target or Path.cwd() / "config.yaml"
    target_env = target_config.parent / ".env"

    pkg_root = Path(__file__).parent.parent
    src_config = pkg_root / "config.example.yaml"
    src_env = pkg_root / ".env.example"

    if not src_config.exists() or not src_env.exists():
        console.print("[red]Error:[/red] template files not found. Reinstall the package.")
        sys.exit(1)

    if target_config.exists():
        console.print(f"[yellow]Skipping[/yellow] {target_config} (already exists).")
    else:
        _copy_package_data_file("config.example.yaml", target_config)
        console.print(f"[green]Created[/green] {target_config}")

    if target_env.exists():
        console.print(f"[yellow]Skipping[/yellow] {target_env} (already exists).")
    else:
        _copy_package_data_file("env.example", target_env)
        target_env.chmod(0o600)
        console.print(f"[green]Created[/green] {target_env} (mode 600)")

    console.print(Panel.fit(
        "[bold]Next steps:[/bold]\n"
        f"  1. Edit [cyan]{target_env}[/cyan] -- fill in your API key and Gmail app password\n"
        f"  2. Edit [cyan]{target_config}[/cyan] -- customize the topic and sources\n"
        f"  3. Run [cyan]morning-brief test-email[/cyan] to verify SMTP works\n"
        f"  4. Run [cyan]morning-brief run[/cyan] to send your first digest",
        title="morning-brief: setup", border_style="green",
    ))


@main.command()
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path),
              help="Path to config.yaml.")
@click.option("--dry-run", is_flag=True, help="Generate digest but don't send or record.")
def run(config_path: Path | None, dry_run: bool) -> None:
    """Generate today's digest and email it."""
    cfg = _load(config_path)
    console.print(f"[dim]Using config:[/dim] {cfg.config_path}")
    console.print(f"[dim]Backend:[/dim] {cfg.backend}  [dim]Model:[/dim] {cfg.model}")

    console.print("[bold]Generating digest...[/bold] (this can take a few minutes)")
    digest = generate_digest(cfg)
    if not digest.strip():
        console.print("[red]Error:[/red] Claude returned an empty digest.")
        sys.exit(1)

    entries = parse_digest(digest)
    console.print(f"[green]Parsed {len(entries)} entries.[/green]")

    if dry_run:
        console.print("[yellow]--dry-run set, not sending email or recording dedup.[/yellow]")
        console.print(digest)
        return

    console.print("[bold]Sending email...[/bold]")
    try:
        send(cfg, digest, entries)
    except Exception as e:
        console.print(f"[red]Send failed:[/red] {e}")
        sys.exit(1)
    console.print(f"[green]Sent to {cfg.env.email_recipient}.[/green]")

    new_count = record(cfg.seen_path(), urls_in(digest))
    console.print(f"[dim]Recorded {new_count} new URLs in {cfg.seen_path()}[/dim]")


@main.command()
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path))
def preview(config_path: Path | None) -> None:
    """Generate the digest and print it to stdout (no email, no dedup recording)."""
    cfg = _load(config_path)
    digest = generate_digest(cfg)
    click.echo(digest)


@main.command("test-email")
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path))
def test_email(config_path: Path | None) -> None:
    """Send a small SMTP test message to confirm email credentials work."""
    cfg = _load(config_path)
    fake_digest = (
        "============================================================\n"
        f"{cfg.topic.name.upper()} DIGEST -- TEST\n"
        "============================================================\n\n"
        "1. Test Entry: morning-brief SMTP smoke test\n"
        "   https://github.com/abhishekpatil32/morning-brief\n"
        "   If you can read this in your inbox, your SMTP credentials work correctly.\n"
        "   The HTML version of this message demonstrates the rendered layout.\n"
    )
    entries = parse_digest(fake_digest)
    try:
        send(cfg, fake_digest, entries)
    except Exception as e:
        console.print(f"[red]Send failed:[/red] {e}")
        sys.exit(1)
    console.print(f"[green]Test email sent to {cfg.env.email_recipient}.[/green]")


@main.command()
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path))
@click.option("--limit", type=int, default=20, help="How many recent URLs to show.")
def seen(config_path: Path | None, limit: int) -> None:
    """List the URLs in seen.txt (most recent last)."""
    cfg = _load(config_path)
    urls = load_seen(cfg.seen_path())
    if not urls:
        console.print(f"[dim]{cfg.seen_path()} is empty.[/dim]")
        return
    console.print(f"[bold]{len(urls)}[/bold] URLs total in [cyan]{cfg.seen_path()}[/cyan]:")
    for u in urls[-limit:]:
        console.print(f"  {u}")


@main.command()
def where() -> None:
    """Show where morning-brief will look for config files."""
    console.print("[bold]Config search paths (first match wins):[/bold]")
    for p in CONFIG_SEARCH_PATHS:
        marker = "[green]exists[/green]" if p.exists() else "[dim]not found[/dim]"
        console.print(f"  {p}  {marker}")



@main.command()
@click.option("--config", "config_path", type=click.Path(exists=True, path_type=Path))
def doctor(config_path: Path | None) -> None:
    """Check config, credentials, backend, and local setup."""
    raise SystemExit(run_doctor(config_path))


if __name__ == "__main__":
    main()
