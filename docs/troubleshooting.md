# Troubleshooting

## `morning-brief: command not found`

You installed with `pip install -e .` but the entry point isn't on your PATH.
Run:

```bash
which morning-brief
python -m morning_brief.cli --help    # works even if entry point isn't linked
```

If you're in a virtualenv, make sure you activated it. If you used
`pip install --user`, ensure `~/.local/bin` is on your PATH.

## `Missing required environment variables`

The CLI couldn't find `ANTHROPIC_API_KEY` or your SMTP credentials. Check:

```bash
morning-brief where               # confirms which config.yaml is loaded
ls -la <config-dir>/.env          # confirms .env exists in the same directory
cat <config-dir>/.env             # confirms it has values, not placeholders
```

## Gmail: `(535, '5.7.8 Username and Password not accepted')`

You're using your normal Google password instead of an App Password.
Generate one at <https://myaccount.google.com/apppasswords> and paste it
into `EMAIL_APP_PASSWORD`. 2-Step Verification must be enabled first.

## Email "sent" successfully but never arrives

1. **Check Spam** — Gmail filters mail-to-self aggressively, especially on
   the first send.
2. **Check tabs** — Primary, Promotions, Updates, Social.
3. **Run `morning-brief test-email`** — confirms SMTP isolation from the
   Claude pipeline.

## Claude Code backend: `claude: command not found`

Install:

```bash
npm install -g @anthropic-ai/claude-code
claude login
```

If running under launchd or cron, the minimal PATH won't include Claude Code.
Either set `backend: api` in config.yaml (recommended for automation), or
ensure your scheduling script exports a complete PATH.

## API backend: `RateLimitError`

You're hitting Anthropic's rate limits. Either upgrade your account tier or
reduce the cadence — `morning-brief` is normally a once-a-day workload.

## `Claude returned an empty digest`

Usually means the web search returned nothing relevant — the topic
description may be too narrow, or `recency_days` may be too short.
Run `morning-brief preview` to see what Claude returns without sending.

## Laptop is asleep at scheduled time

`launchd` and `cron` cannot wake a sleeping Mac. Either:

- Run on a desktop / always-on machine
- Use `pmset` to schedule a wake (macOS): `sudo pmset repeat wakeorpoweron MTWRFSU 08:55:00`
- Move to a small VPS for guaranteed delivery
