#!/usr/bin/env python3
"""
Podcast Digest - Interactive Setup Wizard
Generates config.json by guiding the user through podcast selection and delivery options.

Usage:
  python setup.py                    # Interactive setup
  python setup.py --defaults         # Use all defaults (51 VC/AI/Crypto podcasts)
  python setup.py --import list.txt  # Import podcast names from file
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
    """Load the built-in default podcast list."""
    with open(DEFAULT_PODCASTS_PATH, encoding="utf-8") as f:
        return json.load(f)


def search_itunes(query):
    """Search iTunes API for a podcast RSS feed."""
    url = f"https://itunes.apple.com/search?term={urllib.parse.quote(query)}&media=podcast&limit=5"
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "PodcastDigest/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        results = []
        for r in data.get("results", []):
            if r.get("feedUrl"):
                results.append({
                    "name": r.get("collectionName", ""),
                    "rss": r["feedUrl"],
                    "artist": r.get("artistName", ""),
                })
        return results
    except Exception:
        return []


def slug(name):
    """Generate a URL-safe slug from a podcast name."""
    s = name.lower().strip()
    s = re.sub(r'[^a-z0-9]+', '-', s)
    return s.strip('-')[:40]


def setup_podcasts_interactive():
    """Interactive podcast selection."""
    podcasts = []
    defaults = load_default_podcasts()

    print("\n=== Podcast Selection ===\n")
    print("Options:")
    print("  1) Use default list (51 podcasts: AI, Crypto, VC, Macro, Tech)")
    print("  2) Start with defaults and customize (add/remove)")
    print("  3) Build your own list from scratch")
    print()

    choice = input("Choose [1/2/3]: ").strip()

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
                        removed = podcasts.pop(i)
                        print(f"  Removed: {removed['name']}")
                else:
                    matches = [p for p in podcasts if idx.lower() in p['name'].lower()]
                    for m in matches:
                        podcasts.remove(m)
                        print(f"  Removed: {m['name']}")
            elif action == "a":
                name = input("Podcast name to search: ").strip()
                if not name:
                    continue
                print(f"  Searching '{name}'...")
                results = search_itunes(name)
                if not results:
                    print("  No results found.")
                    rss = input("  Enter RSS URL manually (or skip): ").strip()
                    if rss:
                        podcasts.append({
                            "id": slug(name), "name": name,
                            "rss": rss, "group": "custom"
                        })
                        print(f"  Added: {name}")
                else:
                    for i, r in enumerate(results):
                        print(f"  {i+1}. {r['name']} ({r['artist']})")
                    pick = input("  Choose # (or 0 to skip): ").strip()
                    if pick.isdigit() and 0 < int(pick) <= len(results):
                        r = results[int(pick) - 1]
                        group = input("  Group [core/important/supplement]: ").strip() or "supplement"
                        podcasts.append({
                            "id": slug(r['name']), "name": r['name'],
                            "rss": r['rss'], "group": group
                        })
                        print(f"  Added: {r['name']}")
    elif choice == "3":
        print("\nBuild your list. Search by name or paste RSS URLs.")
        while True:
            name = input("\nPodcast name (or 'done'): ").strip()
            if name.lower() == "done":
                break
            if name.startswith("http"):
                podcasts.append({
                    "id": slug(name.split("/")[-1]),
                    "name": name, "rss": name, "group": "custom"
                })
                print(f"  Added RSS: {name}")
                continue
            print(f"  Searching '{name}'...")
            results = search_itunes(name)
            if not results:
                print("  No results. Enter RSS URL manually?")
                rss = input("  RSS URL (or skip): ").strip()
                if rss:
                    podcasts.append({
                        "id": slug(name), "name": name,
                        "rss": rss, "group": "custom"
                    })
            else:
                for i, r in enumerate(results):
                    print(f"  {i+1}. {r['name']} ({r['artist']})")
                pick = input("  Choose # (or 0 to skip): ").strip()
                if pick.isdigit() and 0 < int(pick) <= len(results):
                    r = results[int(pick) - 1]
                    podcasts.append({
                        "id": slug(r['name']), "name": r['name'],
                        "rss": r['rss'], "group": "custom"
                    })
                    print(f"  Added: {r['name']}")

    print(f"\nFinal podcast list: {len(podcasts)} podcasts")
    return podcasts


def setup_delivery():
    """Configure delivery method."""
    print("\n=== Delivery Setup ===\n")
    print("How should the digest be delivered?")
    print("  1) Save to file only (HTML) — no extra setup needed")
    print("  2) Email (SMTP — works with Gmail, Outlook, etc.)")
    print("  3) Telegram Bot")
    print("  4) Webhook (Slack, Discord, custom)")
    print("  5) All channels")
    print()

    choice = input("Choose [1/2/3/4/5]: ").strip()

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
        print("\n--- Email (SMTP) Setup ---")
        print("Common SMTP servers:")
        print("  Gmail:   smtp.gmail.com  (port 587, use App Password)")
        print("  Outlook: smtp.office365.com (port 587)")
        print("  QQ Mail: smtp.qq.com (port 465, use authorization code)")
        print("  163 Mail: smtp.163.com (port 465)")
        print()
        delivery["smtp_host"] = input("SMTP host: ").strip()
        port_str = input("SMTP port [587]: ").strip() or "587"
        delivery["smtp_port"] = int(port_str)
        delivery["smtp_user"] = input("SMTP username (your email): ").strip()
        delivery["email_from"] = delivery["smtp_user"]
        delivery["email_to"] = input("Recipient email: ").strip()
        print("\n  Note: Set SMTP_PASSWORD environment variable with your password/app-password.")
        print("  Do NOT store passwords in config.json.\n")

    if choice in ("3", "5"):
        print("\n--- Telegram Bot Setup ---")
        print("1. Message @BotFather on Telegram to create a bot")
        print("2. Get your chat ID from @userinfobot or @RawDataBot")
        print()
        delivery["telegram_chat_id"] = input("Telegram Chat ID: ").strip()
        print("\n  Note: Set TELEGRAM_BOT_TOKEN environment variable with your bot token.")
        print("  Do NOT store tokens in config.json.\n")

    if choice in ("4", "5"):
        print("\n--- Webhook Setup ---")
        delivery["webhook_url"] = input("Webhook URL: ").strip()

    return delivery


def setup_ai():
    """Configure AI model and API preferences."""
    print("\n=== AI Setup ===\n")
    print("This skill uses an OpenAI-compatible API to analyze podcast episodes.")
    print("You can use OpenAI, Anthropic (via proxy), OpenRouter, or any compatible provider.\n")

    print("Common API base URLs:")
    print("  OpenAI:      https://api.openai.com/v1")
    print("  OpenRouter:  https://openrouter.ai/api/v1")
    print("  Together:    https://api.together.xyz/v1")
    print("  Local:       http://localhost:11434/v1  (Ollama)")
    print()

    api_base = input("API base URL [https://api.openai.com/v1]: ").strip()
    if not api_base:
        api_base = "https://api.openai.com/v1"

    print("\nModel cascade (tries each in order, falls back on failure).")
    print("Default: gpt-4.1, gpt-4.1-mini")
    use_default = input("Use default models? [Y/n]: ").strip().lower()

    models = None
    if use_default == "n":
        print("Enter model IDs in priority order (one per line, empty to finish):")
        models = []
        while True:
            m = input("  Model: ").strip()
            if not m:
                break
            models.append(m)

    print("\n  Note: Set AI_API_KEY environment variable with your API key.")
    print("  Do NOT store API keys in config.json.\n")

    return {
        "api_base": api_base,
        "models": models if models else ["gpt-4.1", "gpt-4.1-mini"],
    }


def setup_schedule():
    """Configure schedule."""
    print("\n=== Schedule ===\n")
    print("When should the digest run? (24h format, in your timezone)")
    time_str = input("Time [default: 08:00]: ").strip() or "08:00"
    tz = input("Timezone [default: Asia/Shanghai]: ").strip() or "Asia/Shanghai"
    lookback = input("Lookback hours [default: 24]: ").strip() or "24"
    return {
        "time": time_str,
        "timezone": tz,
        "lookback_hours": int(lookback),
    }


def run_setup():
    """Run the full interactive setup wizard."""
    print("=" * 50)
    print("  Podcast Daily Digest - Setup Wizard")
    print("=" * 50)

    if "--defaults" in sys.argv:
        podcasts = load_default_podcasts()
        delivery = {"method": "file"}
        ai = {"api_base": "https://api.openai.com/v1", "models": ["gpt-4.1", "gpt-4.1-mini"]}
        schedule = {"time": "08:00", "timezone": "Asia/Shanghai", "lookback_hours": 24}
        print(f"\nQuick setup: {len(podcasts)} podcasts, file delivery, OpenAI API.")
        print("Edit config.json to customize, or re-run without --defaults.\n")
    else:
        podcasts = setup_podcasts_interactive()
        delivery = setup_delivery()
        ai = setup_ai()
        schedule = setup_schedule()

    config = {
        "delivery": delivery,
        "schedule": schedule,
        "max_deep_dives": 4,
        "ai": ai,
        "podcasts": podcasts,
    }

    with open(CONFIG_PATH, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2, ensure_ascii=False)

    print(f"\nConfig saved to {CONFIG_PATH}")
    print(f"  Podcasts: {len(podcasts)}")
    print(f"  Delivery: {delivery.get('method', 'file')}")
    print(f"  AI API:   {ai['api_base']}")
    print(f"  Models:   {', '.join(ai['models'])}")
    print(f"  Schedule: {schedule['time']} ({schedule['timezone']})")
    print("\n--- Environment variables to set before running digest.py ---")
    print("  AI_API_KEY=<your-api-key>")
    if delivery.get("method") in ("email", "all"):
        print("  SMTP_PASSWORD=<your-smtp-password>")
    if delivery.get("method") in ("telegram", "all"):
        print("  TELEGRAM_BOT_TOKEN=<your-bot-token>")
    print("\nSetup complete! Run: python scripts/digest.py")
    return config


if __name__ == "__main__":
    run_setup()
