#!/usr/bin/env python3
"""
Fetch podcast RSS feeds, deduplicate, and output episodes as JSON.

Usage:
  python fetch.py                   # Output new episodes to stdout (JSON)
  python fetch.py --output FILE     # Write to file instead
  python fetch.py --force           # Bypass dedup
"""

import json
import os
import sys
import subprocess
import hashlib
import re as re_mod
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import feedparser
except ImportError:
    sys.stderr.write("[SETUP] Installing feedparser...\n")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "feedparser"])
    import feedparser

SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config.json"
STATE_PATH = SKILL_DIR / "state.json"

FORCE = "--force" in sys.argv


def load_config():
    if not CONFIG_PATH.exists():
        print("[ERROR] config.json not found. Run setup.py first.", file=sys.stderr)
        sys.exit(1)
    with open(CONFIG_PATH, encoding="utf-8") as f:
        return json.load(f)


def load_state():
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"sent_ids": {}, "last_run": None}


def episode_id(podcast_id, entry):
    guid = entry.get("id", "") or entry.get("link", "") or entry.get("title", "")
    return hashlib.md5(f"{podcast_id}:{guid}".encode()).hexdigest()


def fetch_single_feed(podcast, cutoff_time):
    pid = podcast["id"]
    episodes = []
    try:
        feed = feedparser.parse(podcast["rss"])
        if feed.bozo and not feed.entries:
            return episodes
        for entry in feed.entries[:20]:
            pub_time = entry.get("published_parsed") or entry.get("updated_parsed")
            if not pub_time:
                continue
            from calendar import timegm
            pub_dt = datetime.fromtimestamp(timegm(pub_time), tz=timezone.utc)
            if pub_dt >= cutoff_time:
                desc = entry.get("summary", "")
                if not desc and entry.get("content"):
                    desc = entry["content"][0].get("value", "")
                desc = re_mod.sub(r"<[^>]+>", " ", desc)
                desc = re_mod.sub(r"\s+", " ", desc).strip()[:5000]
                dur = entry.get("itunes_duration", "")
                episodes.append({
                    "podcast_id": pid,
                    "podcast_name": podcast["name"],
                    "podcast_group": podcast.get("group", "custom"),
                    "title": entry.get("title", "Untitled"),
                    "link": entry.get("link", ""),
                    "description": desc,
                    "published": pub_dt.isoformat(),
                    "duration": dur,
                })
    except Exception as e:
        print(f"  [ERROR] {pid}: {e}", file=sys.stderr)
    return episodes


def main():
    config = load_config()
    state = load_state()
    podcasts = config["podcasts"]
    lookback = config.get("schedule", {}).get("lookback_hours", 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback)

    print(f"Fetching {len(podcasts)} RSS feeds (since {cutoff.strftime('%Y-%m-%d %H:%M UTC')})...", file=sys.stderr)

    all_episodes = []
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_feed, p, cutoff): p["id"] for p in podcasts}
        for future in as_completed(futures):
            pid = futures[future]
            try:
                eps = future.result()
                if eps:
                    print(f"  [OK] {pid}: {len(eps)} episode(s)", file=sys.stderr)
                    all_episodes.extend(eps)
            except Exception as e:
                print(f"  [ERROR] {pid}: {e}", file=sys.stderr)

    print(f"Total found: {len(all_episodes)}", file=sys.stderr)

    if FORCE:
        episodes = all_episodes
    else:
        episodes = []
        for ep in all_episodes:
            eid = episode_id(ep["podcast_id"], {"id": ep["link"], "title": ep["title"]})
            if eid not in state.get("sent_ids", {}):
                ep["_eid"] = eid
                episodes.append(ep)
        print(f"After dedup: {len(episodes)} new episodes", file=sys.stderr)

    group_order = {"core": 0, "important": 1, "supplement": 2, "archive": 3, "custom": 2}
    episodes.sort(key=lambda e: (group_order.get(e["podcast_group"], 9), e["published"]))

    output_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]

    result = json.dumps(episodes, indent=2, ensure_ascii=False)
    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(result)
        print(f"Written to {output_file}", file=sys.stderr)
    else:
        print(result)


if __name__ == "__main__":
    main()
