"""Persistent URL dedup so the same paper is never sent twice."""
from __future__ import annotations

import re
from pathlib import Path

URL_RE = re.compile(r"https?://\S+")
TRAILING_PUNCT = ".,;:)]"


def normalize_url(url: str) -> str:
    """Strip trailing punctuation and arxiv version suffixes for dedup purposes."""
    url = url.strip().rstrip(TRAILING_PUNCT)
    # Treat arxiv 2605.12345v1 and 2605.12345v2 as the same paper
    url = re.sub(r"(/abs/\d+\.\d+)v\d+(/?)$", r"\1\2", url)
    return url


def load_seen(seen_path: Path) -> list[str]:
    """Load the full seen list, oldest first."""
    if not seen_path.exists():
        return []
    return [ln.strip() for ln in seen_path.read_text().splitlines() if ln.strip()]


def recent_for_prompt(seen_path: Path, limit: int) -> str:
    """Return the most recent N URLs, formatted as a newline-separated string."""
    urls = load_seen(seen_path)
    if not urls:
        return "(none yet -- this is the first run)"
    return "\n".join(urls[-limit:])


def extract_urls(text: str) -> list[str]:
    """Pull all URLs out of a digest, normalize, and dedup within the result."""
    found = [normalize_url(m.group(0)) for m in URL_RE.finditer(text)]
    out: list[str] = []
    seen: set[str] = set()
    for u in found:
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def record(seen_path: Path, new_urls: list[str]) -> int:
    """Append new URLs to seen.txt (deduplicated). Returns count of *newly* added."""
    seen_path.parent.mkdir(parents=True, exist_ok=True)
    existing = set(load_seen(seen_path))
    additions = [u for u in new_urls if u not in existing]
    if not additions:
        return 0
    with seen_path.open("a") as f:
        for u in additions:
            f.write(u + "\n")
    return len(additions)
