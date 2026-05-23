# morning-brief

> A local-first AI research/news briefing tool from topics you define.

`morning-brief` reads a YAML config describing what you care about, asks Claude
to search the web for the most significant recent articles on that topic, and
emails you a beautifully formatted digest. It remembers what it has already
sent you so you never see the same paper twice.

Originally built for tracking the **AI × Neuroscience** intersection, but
configurable for any topic — crypto, climate, biotech, foreign policy, your
city's local news, whatever you read every morning anyway.

```
┌────────────────────────────────────────────────┐
│  Daily Research Brief                          │
│  AI × Neuroscience                             │
│  Friday, May 22, 2026                          │
├────────────────────────────────────────────────┤
│  #1  Equilibrium Reasoners: Learning Attract…  │
│      arxiv.org/abs/2605.21488                  │
│      Benhao Huang et al. propose that gener…   │
├────────────────────────────────────────────────┤
│  #2  Cross-Subject Intracranial EEG Reconst…   │
│      ...                                       │
└────────────────────────────────────────────────┘
```

## Why

If you're a researcher, you should be skimming new arXiv preprints and recent
PubMed entries in your field most mornings — but you don't. `morning-brief`
delegates that to Claude and drops the result in your inbox while you make
coffee.

## Features

- **Topic-agnostic** — write a YAML config, get a daily digest on anything
- **Two backends** — talk to Claude via the [Anthropic API](https://docs.claude.com) or the [Claude Code CLI](https://docs.claude.com/en/docs/claude-code/overview)
- **Persistent dedup** — papers you've already seen are never resent
- **Clean HTML email** — proper typography, clickable links, mobile-friendly
- **Plain text fallback** — for terminal-based mail clients
- **MIT licensed** — fork, modify, ship

## Quick start

`morning-brief` works with your existing Claude Code subscription — no 
Anthropic API credits required.

```bash
# 1. Install Claude Code (free, only needed once)
npm install -g @anthropic-ai/claude-code
claude login

# 2. Install morning-brief
git clone https://github.com/abhishekpatil32/morning-brief.git
cd morning-brief
python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# 3. Set up config
morning-brief init
$EDITOR .env          # add your Gmail address + app password (no API key 
needed)
$EDITOR config.yaml   # customize the topic if you want

# 4. Send your first digest
morning-brief test-email    # confirm SMTP works
morning-brief run           # the real thing
```

## Configuration

A minimal `config.yaml`:

```yaml
backend: api                          # or "claude-code"
model: claude-sonnet-4-6

topic:
  name: "AI x Neuroscience"
  description: |
    Articles at the intersection of AI/ML and neuroscience.
  include_areas:
    - "Deep learning for EEG and fMRI"
    - "Brain-computer interfaces"
    - "LLMs as models of language processing"
  sources: |
    arXiv, PubMed, bioRxiv, Nature Neuroscience.

output:
  num_articles: 5
  recency_days: 14
  summary_sentences: "3-4"
```

See [`config.example.yaml`](config.example.yaml) for the full schema and
[`examples/`](examples/) for ready-made configs (crypto, climate, etc.).

## Credentials

`morning-brief` reads two kinds of secrets from a `.env` file next to your
`config.yaml`:

```env
# Required if backend = "api"
ANTHROPIC_API_KEY=sk-ant-...

# Required for email delivery (Gmail shown; other providers in .env.example)
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
EMAIL_SENDER=you@gmail.com
EMAIL_APP_PASSWORD=xxxx xxxx xxxx xxxx
EMAIL_RECIPIENT=you@gmail.com
```

For Gmail, you must use an **App Password** (not your normal password):
1. Enable [2-Step Verification](https://myaccount.google.com/security)
2. Generate an [App Password](https://myaccount.google.com/apppasswords)
3. Paste the 16-character code into `EMAIL_APP_PASSWORD`

For Anthropic API access, get a key from
[console.anthropic.com](https://console.anthropic.com/settings/keys).

## Scheduling

`morning-brief` does not include a scheduler — use whatever your OS provides.

### macOS (launchd)

Create `~/Library/LaunchAgents/com.morning-brief.daily.plist`:

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0"><dict>
  <key>Label</key><string>com.morning-brief.daily</string>
  <key>ProgramArguments</key>
  <array>
    <string>/usr/local/bin/morning-brief</string>
    <string>run</string>
    <string>--config</string>
    <string>/Users/YOU/.config/morning-brief/config.yaml</string>
  </array>
  <key>StartCalendarInterval</key>
  <dict><key>Hour</key><integer>9</integer><key>Minute</key><integer>0</integer></dict>
  <key>StandardOutPath</key><string>/tmp/morning-brief.out</string>
  <key>StandardErrorPath</key><string>/tmp/morning-brief.err</string>
</dict></plist>
```

Then:

```bash
launchctl load ~/Library/LaunchAgents/com.morning-brief.daily.plist
```

If your laptop sleeps with the lid closed, also run:
```bash
sudo pmset repeat wakeorpoweron MTWRFSU 08:55:00
```

### Linux (cron)

```cron
0 9 * * * /usr/local/bin/morning-brief run --config /home/you/.config/morning-brief/config.yaml
```

### Truly always-on

For guaranteed delivery regardless of your laptop's state, run on a small
VPS ($5/month on Hetzner, DigitalOcean, etc.) or a free-tier cloud instance.
The CLI works the same way — just `morning-brief run` from a cron job.

## CLI reference

```
morning-brief init           Copy config.example.yaml and .env.example into place
morning-brief run            Generate + email today's digest
morning-brief preview        Generate digest, print to stdout, don't email
morning-brief test-email     Send a smoke-test message to verify SMTP
morning-brief seen           Show URLs in seen.txt
morning-brief where          Show where the CLI looks for config files
morning-brief --help         Full help
```

All commands accept `--config PATH` to override the default config location.

## How it works

1. **Build prompt** — `config.yaml` is composed into a single prompt that tells
   Claude the topic, the areas to focus on, preferred sources, output format,
   and the list of URLs already sent (so Claude picks different ones).
2. **Run Claude** — either via the `anthropic` Python SDK with the
   `web_search` server-tool enabled, or by shelling out to the local `claude`
   CLI in headless mode with `WebSearch` and `WebFetch` allowed.
3. **Parse** — the plain-text response is parsed into structured entries
   (title, URL, summary).
4. **Render + send** — the entries are rendered into an HTML email via a
   Jinja2 template and sent through SMTP. The plain-text version is included
   as an alternative MIME part.
5. **Record** — every URL in the digest is appended to `seen.txt` so it's
   excluded from future runs.


## Safety and privacy

- Your `.env`, `config.yaml`, and `seen.txt` stay local.
- Your topic description and recent seen URLs may be sent to the selected LLM provider.
- Do not paste API keys, Gmail app passwords, or `.env` contents into public issues.
- For unattended scheduled use, prefer `backend: api`.
- Claude Code support is experimental.

## Limitations

- v0.1 depends on LLM-based search, so results may miss relevant articles.
- Publication dates and article relevance should be manually verified for critical work.
- Deduplication is currently URL-based, with basic arXiv version normalization.
- This is a discovery assistant, not a replacement for systematic literature review.

## Roadmap

- [ ] Direct arXiv source mode
- [ ] Direct PubMed source mode
- [ ] SQLite digest history
- [ ] Markdown export
- [ ] Notion export
- [ ] Gemini/OpenAI/Ollama provider abstraction
- [ ] Better DOI/title-based deduplication


## Contributing

PRs welcome — see [`docs/contributing.md`](docs/contributing.md). Particularly
useful contributions:

- New email backends (SendGrid, AWS SES, Mailgun, Postmark)
- New scheduling docs for Windows Task Scheduler
- More example configs for different domains
- A simple test suite (this project has none yet)

## License

MIT. See [LICENSE](LICENSE).

## Acknowledgements

Built on [Claude](https://claude.com) by Anthropic. Originally inspired by the
endless drift of unread arXiv preprints in my browser tabs.
