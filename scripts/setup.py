#!/usr/bin/env python3
"""
Podcast Digest - Interactive Setup Wizard
Generates config.json with podcast list, delivery, and schedule preferences.

Usage:
  python setup.py              # Interactive setup
  python setup.py --defaults   # Quick: 51 default podcasts, file delivery
"""

import json
import os
import sys
import re
import urllib.request
import urllib.parse
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config.json"
DEFAULT_PODCASTS_PATH = SKILL_DIR / "references" / "default-podcasts.json"


def load_default_podcasts():
    with open(DEFAULT_PODCASTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def search_itunes(query):
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&media=podcast&limit=5"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PodcastDigest/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [
            {"name": r.get("collectionName", ""), "rss": r["feedUrl"], "artist": r.get("artistName", "")}
            for r in data.get("results", []) if r.get("feedUrl")
        ]
    except Exception:
        return []


def slug(name):
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')[:40]


def setup_podcasts():
    podcasts = []
    defaults = load_default_podcasts()

    print("\n=== Podcast Selection ===\n")
    print("  1) Use default list (51 podcasts: AI, Crypto, VC, Macro, Tech)")
    print("  2) Start with defaults and customize (add/remove)")
    print("  3) Build your own list from scratch")
    choice = input("\nChoose [1/2/3]: ").strip()

    if choice == "1":
        podcasts = defaults
        print(f"\nLoaded {len(podcasts)} default podcasts.")
    elif choice == "2":
        podcasts = list(defaults)
        print(f"\nLoaded {len(podcasts)} defaults. You can now add/remove.")
        while True:
            action = input("\n[a]dd / [r]emove / [l]ist / [d]one: ").strip().lower()
            if action == "d":
                break
            elif action == "l":
                for i, p in enumerate(podcasts):
                    print(f"  {i+1}. [{p['group']}] {p['name']}")
            elif action == "r":
                idx = input("Remove # (or name substring): ").strip()
                if idx.isdigit():
                    i = int(idx) - 1
                    if 0 <= i < len(podcasts):
                        print(f"  Removed: {podcasts.pop(i)['name']}")
                else:
                    for m in [p for p in podcasts if idx.lower() in p['name'].lower()]:
                        podcasts.remove(m)
                        print(f"  Removed: {m['name']}")
            elif action == "a":
                name = input("Podcast name to search: ").strip()
                if not name:
                    continue
                results = search_itunes(name)
                if not results:
                    rss = input("  No results. RSS URL (or skip): ").strip()
                    if rss:
                        podcasts.append({"id": slug(name), "name": name, "rss": rss, "group": "custom"})
                else:
                    for i, r in enumerate(results):
                        print(f"  {i+1}. {r['name']} ({r['artist']})")
                    pick = input("  Choose # (or 0 to skip): ").strip()
                    if pick.isdigit() and 0 < int(pick) <= len(results):
                        r = results[int(pick) - 1]
                        group = input("  Group [core/important/supplement]: ").strip() or "supplement"
                        podcasts.append({"id": slug(r['name']), "name": r['name'], "rss": r['rss'], "group": group})
    elif choice == "3":
        print("\nSearch by name or paste RSS URLs. Type 'done' to finish.")
        while True:
            name = input("\nPodcast name (or 'done'): ").strip()
            if name.lower() == "done":
                break
            if name.startswith("http"):
                podcasts.append({"id": slug(name.split("/")[-1]), "name": name, "rss": name, "group": "custom"})
                continue
            results = search_itunes(name)
            if not results:
                rss = input("  No results. RSS URL (or skip): ").strip()
                if rss:
                    podcasts.append({"id": slug(name), "name": name, "rss": rss, "group": "custom"})
            else:
                for i, r in enumerate(results):
                    print(f"  {i+1}. {r['name']} ({r['artist']})")
                pick = input("  Choose # (or 0 to skip): ").strip()
                if pick.isdigit() and 0 < int(pick) <= len(results):
                    r = results[int(pick) - 1]
                    podcasts.append({"id": slug(r['name']), "name": r['name'], "rss": r['rss'], "group": "custom"})

    print(f"\nFinal: {len(podcasts)} podcasts")
    return podcasts


def setup_delivery():
    print("\n=== Delivery Setup ===\n")
    print("  1) Save to file only (default, no extra setup)")
    print("  2) Email (SMTP)")
    print("  3) Telegram Bot")
    print("  4) Webhook (Slack, Discord, etc.)")
    print("  5) All channels")
    choice = input("\nChoose [1/2/3/4/5]: ").strip()

    delivery = {"method": "file"}

    if choice == "2":
        delivery["method"] = "email"
    elif choice == "3":
        delivery["method"] = "telegram"
    elif choice == "4":
        delivery["method"] = "webhook"
    elif choice == "5":
        delivery["method"] = "all"

    if choice in ("2", "5"):
        print("\nCommon SMTP: Gmail smtp.gmail.com:587, QQ smtp.qq.com:465, 163 smtp.163.com:465")
        delivery["smtp_host"] = input("SMTP host: ").strip()
        delivery["smtp_port"] = int(input("SMTP port [587]: ").strip() or "587")
        delivery["smtp_user"] = input("SMTP user (email): ").strip()
        delivery["email_from"] = delivery["smtp_user"]
        delivery["email_to"] = input("Recipient email: ").strip()
        print("  -> Set SMTP_PASSWORD env var before running.")

    if choice in ("3", "5"):
        print("\nCreate bot via @BotFather, get chat ID from @userinfobot")
        delivery["telegram_chat_id"] = input("Chat ID: ").strip()
        print("  -> Set TELEGRAM_BOT_TOKEN env var before running.")

    if choice in ("4", "5"):
        delivery["webhook_url"] = input("Webhook URL: ").strip()

    return delivery


def setup_schedule():
    print("\n=== Schedule ===")
    time_str = input("Run time (24h) [08:00]: ").strip() or "08:00"
    tz = input("Timezone [Asia/Shanghai]: ").strip() or "Asia/Shanghai"
    lookback = input("Lookback hours [24]: ").strip() or "24"
    return {"time": time_str, "timezone": tz, "lookback_hours": int(lookback)}


def run_setup():
    print("=" * 50)
    print("  Podcast Daily Digest - Setup")
    print("=" * 50)

    if "--defaults" in sys.argv:
        config = {
            "delivery": {"method": "file"},
            "schedule": {"time": "08:00", "timezone": "Asia/Shanghai", "lookback_hours": 24},
            "max_deep_dives": 4,
            "podcasts": load_default_podcasts(),
        }
    else:
        config = {
            "delivery": setup_delivery(),
            "schedule": setup_schedule(),
            "max_deep_dives": 4,
            "podcasts": setup_podcasts(),
        }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\nSaved to {CONFIG_PATH}")
    print(f"  {len(config['podcasts'])} podcasts | delivery: {config['delivery']['method']}")
    print("\nSetup complete! Ask your agent to run the podcast digest.")


if __name__ == "__main__":
    run_setup()
