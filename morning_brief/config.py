"""Config + environment loading.

Resolves config.yaml from (in order):
  1. Path passed on the CLI with --config
  2. ./config.yaml in the current working directory
  3. ~/.config/morning-brief/config.yaml

.env is loaded from the directory containing the chosen config.yaml.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from pathlib import Path

import yaml

CONFIG_SEARCH_PATHS = [
    Path.cwd() / "config.yaml",
    Path.home() / ".config" / "morning-brief" / "config.yaml",
]


@dataclass
class TopicConfig:
    name: str
    description: str
    include_areas: list[str] = field(default_factory=list)
    sources: str = ""


@dataclass
class OutputConfig:
    num_articles: int = 5
    recency_days: int = 14
    summary_sentences: str = "3-4"


@dataclass
class FiltersConfig:
    exclude_blogs: bool = True
    prefer_peer_reviewed: bool = False
    language: str = "English"


@dataclass
class StateConfig:
    seen_file: str = "seen.txt"
    inject_recent: int = 500


@dataclass
class EmailConfig:
    subject: str = "{topic_name} Digest -- {date}"
    tagline: str = "Daily Research Brief"
    footer: str = "Curated by Claude · Powered by morning-brief"


@dataclass
class EnvConfig:
    """Values pulled from .env (or the surrounding environment)."""
    anthropic_api_key: str | None = None
    smtp_server: str = ""
    smtp_port: int = 587
    email_sender: str = ""
    email_app_password: str = ""
    email_recipient: str = ""


@dataclass
class Config:
    backend: str
    model: str
    topic: TopicConfig
    output: OutputConfig
    filters: FiltersConfig
    state: StateConfig
    email: EmailConfig
    env: EnvConfig
    config_path: Path
    config_dir: Path

    def seen_path(self) -> Path:
        p = Path(self.state.seen_file)
        return p if p.is_absolute() else (self.config_dir / p)


def resolve_config_path(explicit: Path | None) -> Path:
    if explicit:
        if not explicit.exists():
            raise FileNotFoundError(f"Config file not found: {explicit}")
        return explicit.resolve()
    for candidate in CONFIG_SEARCH_PATHS:
        if candidate.exists():
            return candidate.resolve()
    raise FileNotFoundError(
        "No config.yaml found. Run `morning-brief init` or pass --config PATH.\n"
        f"Searched: {', '.join(str(p) for p in CONFIG_SEARCH_PATHS)}"
    )


def load_env_file(env_path: Path) -> None:
    """Parse a .env file and merge into os.environ (without overwriting existing values)."""
    if not env_path.exists():
        return
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        k, v = line.split("=", 1)
        os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))


def load_config(explicit: Path | None = None, require_email: bool = True) -> Config:
    config_path = resolve_config_path(explicit)
    config_dir = config_path.parent
    load_env_file(config_dir / ".env")

    with open(config_path) as f:
        raw = yaml.safe_load(f) or {}

    backend = raw.get("backend", "api")
    if backend not in ("api", "claude-code"):
        raise ValueError(f"backend must be 'api' or 'claude-code', got: {backend}")

    topic_raw = raw.get("topic", {})
    if not topic_raw.get("name") or not topic_raw.get("description"):
        raise ValueError("config.yaml must define topic.name and topic.description")

    cfg = Config(
        backend=backend,
        model=raw.get("model", "claude-sonnet-4-6"),
        topic=TopicConfig(
            name=topic_raw["name"],
            description=topic_raw["description"],
            include_areas=topic_raw.get("include_areas", []),
            sources=topic_raw.get("sources", ""),
        ),
        output=OutputConfig(**(raw.get("output") or {})),
        filters=FiltersConfig(**(raw.get("filters") or {})),
        state=StateConfig(**(raw.get("state") or {})),
        email=EmailConfig(**(raw.get("email") or {})),
        env=EnvConfig(
            anthropic_api_key=os.environ.get("ANTHROPIC_API_KEY"),
            smtp_server=os.environ.get("SMTP_SERVER", "smtp.gmail.com"),
            smtp_port=int(os.environ.get("SMTP_PORT", "587")),
            email_sender=os.environ.get("EMAIL_SENDER", ""),
            email_app_password=os.environ.get("EMAIL_APP_PASSWORD", ""),
            email_recipient=os.environ.get("EMAIL_RECIPIENT", ""),
        ),
        config_path=config_path,
        config_dir=config_dir,
    )

    # Validate the relevant env vars are present
    missing = []
    if cfg.backend == "api" and not cfg.env.anthropic_api_key:
        missing.append("ANTHROPIC_API_KEY (required because backend=api)")
    if require_email:
        for key, val in [
            ("EMAIL_SENDER", cfg.env.email_sender),
            ("EMAIL_APP_PASSWORD", cfg.env.email_app_password),
            ("EMAIL_RECIPIENT", cfg.env.email_recipient),
        ]:
            if not val:
                missing.append(key)
    if missing:
        raise ValueError(
            "Missing required environment variables:\n  - "
            + "\n  - ".join(missing)
            + f"\n\nAdd them to {config_dir / '.env'} (copy from .env.example)."
        )
    return cfg
