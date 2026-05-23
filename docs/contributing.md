# Contributing to morning-brief

Thanks for considering a contribution. This is a small personal-utility project
maintained on weekends — keep PRs focused and small and they'll get merged
quickly.

## Setup

```bash
git clone https://github.com/abhishekpatil32/morning-brief.git
cd morning-brief
python -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
```

## What's welcome

- **Email backends**: a new module like `morning_brief/email_backends/sendgrid.py`
  exposing a `send(cfg, plain, entries)` function, plus a config switch.
- **Source-specific search**: direct arXiv API and PubMed E-utilities clients
  that the prompt can use as authoritative sources rather than relying on
  generic WebSearch.
- **Example configs**: well-commented `examples/config.*.yaml` for new domains.
- **Tests**: this project has none. The most valuable additions would be
  unit tests for `dedup.py`, `core.parse_digest`, and `email_sender.render_html`.
- **Documentation fixes**: typos, broken instructions, missing platforms.

## What's out of scope

- A web UI / SaaS frontend (different project)
- Storing user secrets in any cloud service
- Adding more LLM providers (this is a Claude-specific project)

## Style

- Run `ruff format .` and `ruff check .` before committing.
- Keep functions small and named after what they do.
- Comments explain *why*, not *what*.
- New dependencies require justification in the PR description.

## Reporting bugs

Include:
1. Your OS and Python version
2. The CLI command that failed
3. The full error output
4. A redacted `config.yaml` (remove the topic description if it's private)
