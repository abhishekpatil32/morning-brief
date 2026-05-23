"""LLM provider adapters for morning-brief."""

from __future__ import annotations

import json
import os
import subprocess
import urllib.error
import urllib.request

from .config import Config


def generate_with_provider(cfg: Config, prompt: str) -> str:
    """Dispatch prompt generation to the configured provider."""
    if cfg.provider == "anthropic":
        return run_anthropic_api(cfg, prompt)

    if cfg.provider == "openai-compatible":
        return run_openai_compatible(cfg, prompt)

    if cfg.provider == "ollama":
        return run_ollama(cfg, prompt)

    if cfg.provider == "claude-code":
        return run_claude_code(cfg, prompt)

    raise ValueError(f"Unknown provider: {cfg.provider}")


def run_anthropic_api(cfg: Config, prompt: str) -> str:
    """Call the Anthropic API with Claude web search enabled."""
    from anthropic import Anthropic

    client = Anthropic(api_key=cfg.env.anthropic_api_key)

    response = client.messages.create(
        model=cfg.model,
        max_tokens=4096,
        tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 15}],
        messages=[{"role": "user", "content": prompt}],
    )

    parts: list[str] = []
    for block in response.content:
        if getattr(block, "type", None) == "text":
            parts.append(block.text)

    return "\n".join(parts).strip()


def run_openai_compatible(cfg: Config, prompt: str) -> str:
    """Call an OpenAI-compatible /v1/chat/completions endpoint."""
    if not cfg.env.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is required when provider=openai-compatible")

    base_url = cfg.env.openai_base_url.rstrip("/")
    url = f"{base_url}/chat/completions"

    payload = {
        "model": cfg.model,
        "messages": [
            {
                "role": "system",
                "content": (
                    "You generate concise research/news digests. "
                    "Follow the requested output format exactly."
                ),
            },
            {"role": "user", "content": prompt},
        ],
        "temperature": 0.2,
        "max_tokens": 4096,
    }

    data = _post_json(
        url=url,
        payload=payload,
        headers={
            "Authorization": f"Bearer {cfg.env.openai_api_key}",
            "Content-Type": "application/json",
        },
        timeout=cfg.runtime_timeout_seconds,
    )

    try:
        return data["choices"][0]["message"]["content"].strip()
    except (KeyError, IndexError, TypeError) as exc:
        raise RuntimeError(f"Unexpected OpenAI-compatible response shape: {data}") from exc


def run_ollama(cfg: Config, prompt: str) -> str:
    """Call a local Ollama model."""
    base_url = cfg.env.ollama_base_url.rstrip("/")
    url = f"{base_url}/api/generate"

    payload = {
        "model": cfg.model,
        "prompt": prompt,
        "stream": False,
        "options": {"temperature": 0.2},
    }

    data = _post_json(
        url=url,
        payload=payload,
        headers={"Content-Type": "application/json"},
        timeout=cfg.runtime_timeout_seconds,
    )

    try:
        return data["response"].strip()
    except (KeyError, TypeError) as exc:
        raise RuntimeError(f"Unexpected Ollama response shape: {data}") from exc


def run_claude_code(cfg: Config, prompt: str) -> str:
    """Shell out to the local Claude Code CLI."""
    if not _which("claude"):
        raise RuntimeError(
            "`claude` CLI not found on PATH. Install Claude Code first, "
            "or switch to backend=api in config.yaml."
        )

    proc = subprocess.run(
        [
            "claude",
            "-p",
            prompt,
            "--allowedTools",
            "WebSearch,WebFetch",
            "--output-format",
            "text",
            "--model",
            cfg.model,
        ],
        capture_output=True,
        text=True,
        timeout=cfg.runtime_timeout_seconds,
        check=False,
    )

    if proc.returncode != 0:
        raise RuntimeError(f"claude CLI failed with exit {proc.returncode}:\n{proc.stderr}")

    return proc.stdout.strip()


def _post_json(
    url: str,
    payload: dict,
    headers: dict[str, str],
    timeout: int,
) -> dict:
    """POST JSON using only the Python standard library."""
    body = json.dumps(payload).encode("utf-8")

    request = urllib.request.Request(
        url,
        data=body,
        headers=headers,
        method="POST",
    )

    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        error_body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {url}:\n{error_body}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Could not connect to {url}: {exc}") from exc

    try:
        return json.loads(raw)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Provider returned non-JSON response:\n{raw[:1000]}") from exc


def _which(cmd: str) -> bool:
    """True if cmd exists somewhere on PATH."""
    for path in os.environ.get("PATH", "").split(os.pathsep):
        if path and os.access(os.path.join(path, cmd), os.X_OK):
            return True
    return False
