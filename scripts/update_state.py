#!/usr/bin/env python3
"""
Mark episodes as sent in state.json (dedup tracking).

Usage:
  python update_state.py episodes.json    # Mark all episodes in file as sent
"""

import json
import sys
import hashlib
from datetime import datetime, timedelta, timezone
from pathlib import Path

SKILL_DIR = Path(__file__).parent.resolve().parent
STATE_PATH = SKILL_DIR / "state.json"


def load_state():
    if STATE_PATH.exists():
        try:
            with open(STATE_PATH, encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError):
            pass
    return {"sent_ids": {}, "last_run": None}


def save_state(state):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    pruned = {k: v for k, v in state["sent_ids"].items() if v > cutoff}
    state["sent_ids"] = pruned
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def episode_id(podcast_id, link, title):
    guid = link or title or ""
    return hashlib.md5(f"{podcast_id}:{guid}".encode()).hexdigest()


def main():
    if len(sys.argv) < 2:
        print("Usage: python update_state.py <episodes.json>", file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1], encoding="utf-8") as f:
        episodes = json.load(f)

    state = load_state()
    now = datetime.now(timezone.utc).isoformat()

    for ep in episodes:
        eid = ep.get("_eid") or episode_id(ep["podcast_id"], ep.get("link", ""), ep.get("title", ""))
        state["sent_ids"][eid] = now

    save_state(state)
    print(f"Marked {len(episodes)} episodes as sent.", file=sys.stderr)


if __name__ == "__main__":
    main()
