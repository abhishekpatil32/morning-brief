"""Prompt construction + dispatch to the chosen Claude backend."""
from __future__ import annotations

import os
import re
import subprocess
from dataclasses import dataclass
from datetime import datetime

from .config import Config
from .dedup import extract_urls, recent_for_prompt


@dataclass
class Entry:
    num: str
    title: str
    url: str
    summary: str


def build_prompt(cfg: Config) -> str:
    """Compose the user-facing config into a single prompt for Claude."""
    seen_snippet = recent_for_prompt(cfg.seen_path(), cfg.state.inject_recent)
    areas = "\n".join(f"  - {a}" for a in cfg.topic.include_areas) or "  (no areas listed)"
    today = datetime.now().strftime("%Y-%m-%d")

    filter_lines = []
    if cfg.filters.exclude_blogs:
        filter_lines.append("Skip blog posts, press releases, and aggregator sites.")
    if cfg.filters.prefer_peer_reviewed:
        filter_lines.append("Strongly prefer peer-reviewed work over preprints.")
    if cfg.filters.language:
        filter_lines.append(f"Only include articles available in {cfg.filters.language}.")
    filter_block = "\n".join(filter_lines) or "(no extra filters)"

    return f"""You are preparing a daily research digest on the following topic.

TOPIC: {cfg.topic.name}

DESCRIPTION:
{cfg.topic.description.strip()}

AREAS OF INTEREST:
{areas}

PREFERRED SOURCES:
{cfg.topic.sources.strip() or "Reputable sources for this topic."}

FILTERS:
{filter_block}

TASK:
Find the {cfg.output.num_articles} most significant articles or preprints
published in the past {cfg.output.recency_days} days that fit the topic.

CRITICAL: the URLs listed below have ALREADY been sent in previous digests.
Skip them entirely and find DIFFERENT papers. Treat different version suffixes
of the same arXiv ID as already-seen.

PREVIOUSLY SENT URLS:
{seen_snippet}

OUTPUT FORMAT:
Output ONLY clean plain text in this exact format -- no preamble, no closing remarks:

============================================================
{cfg.topic.name.upper()} DIGEST -- {today}
============================================================

1. <Title>
   <URL>
   <{cfg.output.summary_sentences} sentence summary covering the contribution and why it matters>

2. <Title>
   <URL>
   <summary>

(continue through {cfg.output.num_articles})
"""


def run_claude_api(cfg: Config, prompt: str) -> str:
    """Call the Anthropic API with web search enabled."""
    from anthropic import Anthropic

    client = Anthropic(api_key=cfg.env.anthropic_api_key)

    # Web search is exposed as a server-tool via the API.
    # Reference: https://docs.claude.com/en/docs/build-with-claude/tool-use/web-search-tool
    response = client.messages.create(
        model=cfg.model,
        max_tokens=4096,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 15}],
        messages=[{"role": "user", "content": prompt}],
    )

    # The final message may contain multiple blocks (tool_use, web_search_tool_result, text).
    # We want only the text blocks, joined.
    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)
    return "\n".join(parts).strip()


def run_claude_code(cfg: Config, prompt: str) -> str:
    """Shell out to the local `claude` CLI in headless mode."""
    if not _which("claude"):
        raise RuntimeError(
            "`claude` CLI not found on PATH. Install with:\n"
            "  npm install -g @anthropic-ai/claude-code\n"
            "Then run `claude login` once, or switch backend to 'api' in config.yaml."
        )

    proc = subprocess.run(
        [
            "claude", "-p", prompt,
            "--allowedTools", "WebSearch,WebFetch",
            "--output-format", "text",
            "--model", cfg.model,
        ],
        capture_output=True, text=True, timeout=600,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed (exit {proc.returncode}):\n{proc.stderr}")
    return proc.stdout.strip()


def _which(cmd: str) -> bool:
    """True if `cmd` exists somewhere on PATH."""
    for p in os.environ.get("PATH", "").split(os.pathsep):
        if p and os.access(os.path.join(p, cmd), os.X_OK):
            return True
    return False


def generate_digest(cfg: Config) -> str:
    """Build the prompt, dispatch to the configured backend, return plain-text digest."""
    prompt = build_prompt(cfg)
    if cfg.backend == "api":
        return run_claude_api(cfg, prompt)
    elif cfg.backend == "claude-code":
        return run_claude_code(cfg, prompt)
    else:
        raise ValueError(f"unknown backend: {cfg.backend}")


def parse_digest(text: str) -> list[Entry]:
    """Parse the plain-text digest into structured entries."""
    # Strip the banner
    content = re.sub(r"^=+\s*\n.*?\n=+\s*\n", "", text, count=1, flags=re.S).strip()
    chunks = re.split(r"\n(?=\d+\.\s)", content)
    url_re = re.compile(r"https?://\S+")
    entries: list[Entry] = []
    for chunk in chunks:
        chunk = chunk.strip()
        if not chunk:
            continue
        lines = [ln.rstrip() for ln in chunk.splitlines() if ln.strip()]
        m = re.match(r"^(\d+)\.\s+(.*)$", lines[0])
        if not m:
            continue
        num, title = m.group(1), m.group(2).strip()
        url, summary_lines = "", []
        for ln in lines[1:]:
            u = url_re.search(ln)
            if u and not url:
                url = u.group(0).rstrip(".,;:)]")
            else:
                summary_lines.append(ln.strip())
        entries.append(Entry(num=num, title=title, url=url,
                             summary=" ".join(s for s in summary_lines if s)))
    return entries


def urls_in(digest: str) -> list[str]:
    """Pull URLs out of the digest for dedup recording."""
    return extract_urls(digest)
