# Podcast Daily Digest

An AI agent skill that monitors 51+ podcast RSS feeds and delivers a curated daily digest with cross-podcast trends, deep dives, and discoveries.

**No API key needed.** Your agent (OpenClaw, Claude Code, Cursor) does the AI analysis — this skill just gives it the workflow and tools.

## Install

Clone into your agent's skill directory:

```bash
# OpenClaw (recommended)
git clone https://github.com/DGMC70/podcast-digest.git ~/.openclaw/skills/podcast-digest

# Claude Code
git clone https://github.com/DGMC70/podcast-digest.git ~/.claude/skills/podcast-digest

# Cursor (personal)
git clone https://github.com/DGMC70/podcast-digest.git ~/.cursor/skills/podcast-digest
```

Or simply tell your agent:

> Install the podcast-digest skill from https://github.com/DGMC70/podcast-digest

## Use

Ask your agent:

> Run my podcast digest

The agent will:
1. **Fetch** — pull RSS feeds for all configured podcasts (parallel, 10 threads)
2. **Analyze** — identify trending topics, pick deep-dive episodes, summarize the rest
3. **Build** — generate a dark-themed HTML digest
4. **Deliver** — save to file, send via email/Telegram/webhook

That's it. The agent reads `SKILL.md` and handles everything.

## Setup

On first run the agent will run the setup wizard automatically. Or run it yourself:

```bash
python scripts/setup.py              # Interactive
python scripts/setup.py --defaults   # Quick: 51 default podcasts, file delivery
```

Configures: podcast list, delivery method, schedule.

## What's in the Digest

- **Trending Topics** — themes appearing across 2+ podcasts
- **Deep Dives** — up to 4 high-value episodes with insights and quotes
- **Standard Summaries** — brief coverage of remaining episodes
- **Discoveries** — new companies, key data, trend signals, risk alerts

Language: Chinese insights, English names/terms/quotes.

## Delivery Channels

| Channel | Extra Setup |
|---------|------------|
| **File** (default) | None |
| **Email** (SMTP) | SMTP server + `SMTP_PASSWORD` env var |
| **Telegram** | Bot token + chat ID |
| **Webhook** | URL (Slack, Discord, etc.) |

Details: [`references/delivery.md`](references/delivery.md)

## Directory Structure

```
podcast-digest/           ← This IS the skill. Clone it into your skills folder.
├── SKILL.md              ← Agent reads this (workflow + analysis prompt)
├── references/
│   ├── default-podcasts.json   (51 curated feeds)
│   └── delivery.md             (channel setup guide)
└── scripts/
    ├── setup.py          ← Config wizard
    ├── fetch.py          ← RSS fetch + dedup → episodes.json
    ├── build_html.py     ← analysis.json → HTML
    ├── deliver.py        ← Send HTML via configured channel
    ├── update_state.py   ← Mark episodes as sent
    └── emailer.py        ← HTML template engine
```

## Built-in Podcasts (51)

**Core**: All-In, 20VC, Bankless, BG2 Pod  
**Important**: Acquired, Invest Like the Best, a16z, No Priors, Hard Fork, Latent Space, Dwarkesh, Lightcone...  
**Supplement**: Lex Fridman, Odd Lots, Founders, Unchained, What Bitcoin Did...  
**Archive**: Rachel Maddow, Tucker Carlson, Kara Swisher...

Full list: [`references/default-podcasts.json`](references/default-podcasts.json)

## Requirements

- Python 3.8+ (only dependency: `feedparser`, auto-installed)
- An AI agent (OpenClaw / Claude Code / Cursor)

## License

MIT
