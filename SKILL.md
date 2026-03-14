---
name: podcast-digest
description: >
  Automated daily podcast digest. Monitors RSS feeds, analyzes new episodes,
  and delivers a curated HTML digest via email, Telegram, webhook, or file.
  Use when the user wants to run a podcast digest, set up podcast monitoring,
  configure podcast lists or delivery channels, or generate a podcast summary.
  Supports 51 built-in podcasts (AI, Crypto, VC, Macro, Tech).
---

# Podcast Daily Digest

Fetches podcast RSS feeds, analyzes new episodes, and delivers a dark-themed HTML digest with cross-podcast trends, deep dives, and discoveries.

## First-Time Setup

If `config.json` does not exist in the skill root, run the setup wizard:

```bash
python scripts/setup.py              # Interactive
python scripts/setup.py --defaults   # Quick: 51 default podcasts, file delivery
```

This creates `config.json` with podcast list, delivery method, and schedule.

## Workflow — Running the Digest

Follow these steps in order:

### Step 1: Fetch episodes

```bash
python scripts/fetch.py --output episodes.json
```

This fetches all configured RSS feeds, deduplicates against previous runs, and writes new episodes to `episodes.json`. Add `--force` to bypass dedup.

If the file is empty (`[]`), tell the user there are no new episodes and stop.

### Step 2: Analyze episodes (you do this)

Read `episodes.json`. Analyze the episodes and produce a JSON object following the schema and prompt below. Save the result as `analysis.json` in the skill root.

#### Analysis Prompt

You are a podcast digest analyst for an investor. Analyze the episodes and produce JSON with:

1. **trending_topics**: Topics appearing in 2+ podcasts. Each has: title, list of podcast names discussing it, summary of different perspectives, color hint (red/orange/blue/green).
2. **deep_dives**: Pick up to 4 highest-value episodes (non-consensus views, unique insights, important data, novel frameworks). Each needs: podcast_name, title, link, duration, categories, hosts_guests, overview paragraph, 2-3 insight bullets (title + detail), one notable quote (text, speaker, context).
3. **standard_episodes**: 2-3 sentence summaries for remaining episodes. Each: podcast_name, title, link, categories, summary.
4. **discoveries**: Organized as: new_companies, key_data, trend_signals, watch_items, risk_alerts, frameworks (each an array of strings).

**Language**: Mixed Chinese-English. English for names, companies, quotes, technical terms. Chinese for insights, analysis, summaries.

#### Analysis JSON Schema

```json
{
  "date": "YYYY-MM-DD",
  "total_episodes": <number>,
  "trending_topics": [
    {"title": "str", "podcasts": ["str"], "summary": "str", "color": "red|orange|blue|green"}
  ],
  "deep_dives": [
    {
      "podcast_name": "str", "title": "str", "link": "str", "duration": "str",
      "categories": ["str"], "hosts_guests": "str", "overview": "str",
      "insights": [{"title": "str", "detail": "str"}],
      "quote": {"text": "str", "speaker": "str", "context": "str"}
    }
  ],
  "standard_episodes": [
    {"podcast_name": "str", "title": "str", "link": "str", "categories": ["str"], "summary": "str"}
  ],
  "discoveries": {
    "new_companies": [], "key_data": [], "trend_signals": [],
    "watch_items": [], "risk_alerts": [], "frameworks": []
  }
}
```

### Step 3: Build HTML

```bash
python scripts/build_html.py analysis.json --output digest.html
```

### Step 4: Deliver

```bash
python scripts/deliver.py digest.html
```

Delivers via the method configured in `config.json` (file, email, telegram, webhook, or all).

### Step 5: Update state

```bash
python scripts/update_state.py episodes.json
```

Marks episodes as sent so they won't appear in the next run.

### Step 6: Report to user

Summarize: how many episodes processed, key trending topics, which episodes got deep-dive treatment.

## Modifying Podcast List

To add/remove podcasts, either:
- Edit `config.json` directly (the `podcasts` array)
- Re-run `python scripts/setup.py`

Default list: see `references/default-podcasts.json` (51 podcasts across AI, Crypto, VC, Macro, Tech, Politics).

## Delivery Channels

See `references/delivery.md` for setup details on each channel (SMTP email, Telegram, webhook).
