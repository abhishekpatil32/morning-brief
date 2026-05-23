# Security Policy

## Reporting a vulnerability

Please open a private security advisory on GitHub or contact the maintainer directly.

Do not post secrets, API keys, Gmail app passwords, `.env` contents, or private digest outputs in public issues.

## Secret handling

`morning-brief` reads credentials from environment variables or a local `.env` file:

- `ANTHROPIC_API_KEY`
- `EMAIL_SENDER`
- `EMAIL_APP_PASSWORD`
- `EMAIL_RECIPIENT`
- `SMTP_SERVER`
- `SMTP_PORT`

The repository intentionally ignores `.env`, `config.yaml`, and `seen.txt`.

## Claude Code backend

The Claude Code backend is experimental. For unattended scheduled use, the API backend is recommended.

The project should not run Claude Code with bypassed permissions by default.

## Prompt injection

Search results, abstracts, article pages, and web pages are treated as untrusted content. Summaries should not follow instructions found inside web pages.
