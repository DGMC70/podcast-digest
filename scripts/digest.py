#!/usr/bin/env python3
"""
Podcast Daily Digest - Main Pipeline
Fetches RSS feeds, analyzes with AI, generates HTML email, delivers via configured channel.

Usage:
  python digest.py              # Normal run
  python digest.py --dry-run    # Save HTML to file, no delivery
  python digest.py --force      # Bypass dedup (reprocess all recent episodes)
"""

import json
import os
import sys
import time
import subprocess
import hashlib
import re as re_mod
import smtplib
import urllib.request
import urllib.error
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime, timedelta, timezone
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

try:
    import feedparser
except ImportError:
    print("[SETUP] Installing feedparser...")
    subprocess.check_call([sys.executable, "-m", "pip", "install", "-q", "feedparser"])
    import feedparser

DRY_RUN = "--dry-run" in sys.argv
FORCE = "--force" in sys.argv

SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config.json"
STATE_PATH = SKILL_DIR / "state.json"

# Default OpenAI-compatible API (user should configure their own)
DEFAULT_API_BASE = "https://api.openai.com/v1"


def load_config():
    if not CONFIG_PATH.exists():
        print("[ERROR] config.json not found. Run setup.py first.")
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


def save_state(state):
    cutoff = (datetime.now(timezone.utc) - timedelta(days=14)).isoformat()
    pruned = {k: v for k, v in state["sent_ids"].items() if v > cutoff}
    state["sent_ids"] = pruned
    state["last_run"] = datetime.now(timezone.utc).isoformat()
    with open(STATE_PATH, "w", encoding="utf-8") as f:
        json.dump(state, f, indent=2, ensure_ascii=False)


def episode_id(podcast_id, entry):
    guid = entry.get("id", "") or entry.get("link", "") or entry.get("title", "")
    return hashlib.md5(f"{podcast_id}:{guid}".encode()).hexdigest()


# === RSS Fetching ===

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
        print(f"  [ERROR] {pid}: {e}")
    return episodes


def fetch_all_feeds(config, cutoff_time):
    all_episodes = []
    podcasts = config["podcasts"]
    print(f"Fetching {len(podcasts)} RSS feeds...")
    with ThreadPoolExecutor(max_workers=10) as executor:
        futures = {executor.submit(fetch_single_feed, p, cutoff_time): p["id"] for p in podcasts}
        for future in as_completed(futures):
            pid = futures[future]
            try:
                eps = future.result()
                if eps:
                    print(f"  [OK] {pid}: {len(eps)} new episode(s)")
                    all_episodes.extend(eps)
            except Exception as e:
                print(f"  [ERROR] {pid}: {e}")
    return all_episodes


def deduplicate(episodes, state):
    new_eps = []
    for ep in episodes:
        eid = episode_id(ep["podcast_id"], {"id": ep["link"], "title": ep["title"]})
        if eid not in state["sent_ids"]:
            ep["_eid"] = eid
            new_eps.append(ep)
    return new_eps


# === AI Analysis (OpenAI-compatible API) ===

MAX_RETRIES = 2
RETRY_DELAYS = [3, 10]


def call_ai_api(api_base, api_key, model_name, prompt_text, max_tokens=8000):
    """Call an OpenAI-compatible chat completions API."""
    url = f"{api_base.rstrip('/')}/chat/completions"
    payload = json.dumps({
        "model": model_name,
        "messages": [{"role": "user", "content": prompt_text}],
        "max_tokens": max_tokens,
        "temperature": 0.3,
    }, ensure_ascii=True).encode("utf-8")
    print(f"  Payload: {len(payload)/1024:.1f}KB -> {model_name} @ {api_base}")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    for attempt in range(MAX_RETRIES):
        if attempt > 0:
            delay = RETRY_DELAYS[min(attempt - 1, len(RETRY_DELAYS) - 1)]
            print(f"  Retry {attempt}/{MAX_RETRIES} after {delay}s...")
            time.sleep(delay)
        try:
            req = urllib.request.Request(url, data=payload, headers=headers, method="POST")
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = resp.read().decode("utf-8")
                status = resp.status
        except urllib.error.HTTPError as e:
            print(f"  [HTTP {e.code}] attempt {attempt+1}")
            continue
        except urllib.error.URLError as e:
            print(f"  [NETWORK ERROR] attempt {attempt+1}: {e.reason}")
            continue
        except Exception as e:
            print(f"  [TIMEOUT/ERROR] attempt {attempt+1}: {e}")
            continue

        if status == 200:
            try:
                resp_data = json.loads(body)
                content = resp_data["choices"][0]["message"]["content"]
                return content, body
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                print(f"  [PARSE ERROR] attempt {attempt+1}: {e}")
                continue
        else:
            print(f"  [HTTP {status}] attempt {attempt+1}")

    return None, f"All {MAX_RETRIES} retries failed for {model_name}"


def parse_ai_json(content):
    content = content.strip()
    if content.startswith("```"):
        nl = content.find("\n")
        content = content[nl+1:] if nl > 0 else content[3:]
    if content.endswith("```"):
        content = content[:-3].strip()
    try:
        return json.loads(content)
    except json.JSONDecodeError:
        pass
    match = re_mod.search(r'\{[\s\S]*\}', content)
    if match:
        try:
            return json.loads(match.group())
        except json.JSONDecodeError:
            fixed = re_mod.sub(r',(\s*[}\]])', r'\1', match.group())
            try:
                return json.loads(fixed)
            except json.JSONDecodeError:
                pass
    fixed = re_mod.sub(r',(\s*[}\]])', r'\1', content)
    try:
        return json.loads(fixed)
    except json.JSONDecodeError:
        pass
    return None


def build_prompt(episodes, max_deep, today_str):
    ep_lines = []
    for i, ep in enumerate(episodes):
        desc = (ep.get('description', '') or '')[:300]
        desc = ''.join(c for c in desc if ord(c) < 128)
        title = ''.join(c for c in ep.get('title', '') if ord(c) < 128)
        line = f"[{i+1}] {ep['podcast_name']}: {title}"
        if ep.get('link'):
            line += f"\nLink: {ep['link']}"
        if desc:
            line += f"\nDesc: {desc}"
        ep_lines.append(line)
    ep_text = "\n\n".join(ep_lines)
    prompt = (
        "You are a podcast digest analyst for an investor. "
        "Analyze these episodes and return ONLY valid JSON.\n\n"
        "REQUIREMENTS:\n"
        "1. trending_topics: topics appearing in 2+ podcasts, with perspectives from each\n"
        f"2. deep_dives: pick up to {max_deep} highest-value episodes "
        "(non-consensus views, unique insights, important data, novel frameworks). "
        "Each needs: overview paragraph, 2-3 specific insight bullets, one notable quote.\n"
        "3. standard_episodes: 2-3 sentence summaries for remaining episodes\n"
        "4. discoveries: new companies, key data, trend signals, risk alerts\n\n"
        "LANGUAGE: Mixed Chinese-English. English for names/companies/quotes/terms. "
        "Chinese for insights/analysis/summaries.\n\n"
        f"EPISODES ({len(episodes)}):\n{ep_text}\n\n"
        "Return valid JSON (NO markdown code fences):\n"
        '{"date":"' + today_str + '","total_episodes":' + str(len(episodes)) + ','
        '"trending_topics":[{"title":"str","podcasts":["str"],"summary":"str","color":"red|orange|blue|green"}],'
        '"deep_dives":[{"podcast_name":"str","title":"str","link":"str","duration":"str","categories":["str"],'
        '"hosts_guests":"str","overview":"str","insights":[{"title":"str","detail":"str"}],'
        '"quote":{"text":"str","speaker":"str","context":"str"}}],'
        '"standard_episodes":[{"podcast_name":"str","title":"str","link":"str","categories":["str"],"summary":"str"}],'
        '"discoveries":{"new_companies":[],"key_data":[],"trend_signals":[],"watch_items":[],"risk_alerts":[],"frameworks":[]}}'
    )
    return prompt


def analyze_episodes(episodes, config):
    api_key = os.environ.get("AI_API_KEY", "")
    if not api_key:
        print("[ERROR] AI_API_KEY environment variable not set.")
        print("        Set it to your OpenAI / Anthropic / compatible API key.")
        return None

    ai_config = config.get("ai", {})
    api_base = ai_config.get("api_base", DEFAULT_API_BASE)
    models = ai_config.get("models", ["gpt-4.1", "gpt-4.1-mini"])
    max_deep = config.get("max_deep_dives", 4)

    today_str = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    prompt = build_prompt(episodes, max_deep, today_str)
    print(f"  Prompt: {len(prompt)} chars ({len(prompt)/1024:.1f}KB)")

    for model_name in models:
        print(f"\nTrying model: {model_name}")
        content, raw = call_ai_api(api_base, api_key, model_name, prompt)
        if content is None:
            print(f"  [FAIL] {model_name}: {raw}")
            continue
        print(f"  AI response: {len(content)} chars")
        analysis = parse_ai_json(content)
        if analysis is None:
            print(f"  [ERROR] Could not parse JSON from {model_name}")
            continue
        analysis["_model_used"] = model_name
        print(f"  [OK] via {model_name}: {len(analysis.get('deep_dives',[]))} deep dives, "
              f"{len(analysis.get('standard_episodes',[]))} standard, "
              f"{len(analysis.get('trending_topics',[]))} trends")
        return analysis
    print("[ERROR] All AI models failed after retries")
    return None


# === Delivery ===

def _send_smtp_email(delivery, subject, html):
    """Send via standard SMTP (Gmail, Outlook, custom server, etc.)."""
    smtp_host = delivery.get("smtp_host", "")
    smtp_port = delivery.get("smtp_port", 587)
    smtp_user = delivery.get("smtp_user", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", delivery.get("smtp_password", ""))
    from_email = delivery.get("email_from", smtp_user)
    to_email = delivery.get("email_to", "")

    if not all([smtp_host, smtp_user, smtp_pass, to_email]):
        print("[WARN] SMTP not fully configured. Need: smtp_host, smtp_user, SMTP_PASSWORD env var, email_to")
        return False

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = from_email
    msg["To"] = to_email
    msg.attach(MIMEText(html, "html", "utf-8"))

    try:
        if smtp_port == 465:
            server = smtplib.SMTP_SSL(smtp_host, smtp_port, timeout=30)
        else:
            server = smtplib.SMTP(smtp_host, smtp_port, timeout=30)
            server.starttls()
        server.login(smtp_user, smtp_pass)
        server.sendmail(from_email, [to_email], msg.as_string())
        server.quit()
        print(f"[OK] Email sent to {to_email} via {smtp_host}")
        return True
    except Exception as e:
        print(f"[ERROR] SMTP failed: {e}")
        return False


def _send_telegram(delivery, subject, html):
    """Send digest via Telegram Bot API."""
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", delivery.get("telegram_bot_token", ""))
    chat_id = delivery.get("telegram_chat_id", "")

    if not bot_token or not chat_id:
        print("[WARN] Telegram not configured. Need: TELEGRAM_BOT_TOKEN env var, telegram_chat_id in config")
        return False

    text = re_mod.sub(r'<[^>]+>', '', html)[:4000]
    text = f"*{subject}*\n\n{text}"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("ok"):
                print(f"[OK] Telegram message sent to chat {chat_id}")
                return True
            else:
                print(f"[WARN] Telegram API: {result.get('description', 'unknown error')}")
                return False
    except Exception as e:
        print(f"[ERROR] Telegram failed: {e}")
        return False


def _send_webhook(delivery, subject, html):
    """Send digest via generic webhook (Slack, Discord, custom)."""
    webhook_url = delivery.get("webhook_url", "")
    if not webhook_url:
        print("[WARN] Webhook URL not configured.")
        return False

    text = re_mod.sub(r'<[^>]+>', '', html)[:4000]
    payload = json.dumps({"text": f"{subject}\n\n{text}"}).encode("utf-8")

    try:
        req = urllib.request.Request(webhook_url, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if 200 <= resp.status < 300:
                print(f"[OK] Webhook delivered to {webhook_url[:50]}...")
                return True
    except Exception as e:
        print(f"[ERROR] Webhook failed: {e}")
    return False


def deliver(html, analysis, config):
    delivery = config.get("delivery", {"method": "file"})
    method = delivery.get("method", "file")
    date_str = analysis.get("date", datetime.now().strftime("%Y-%m-%d"))
    weekdays_zh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = weekdays_zh[d.weekday()]
    except ValueError:
        weekday = ""
    subject = f"\U0001f399 Podcast Daily Digest | {date_str} {weekday}"

    if method in ("file", "both", "all"):
        out_path = SKILL_DIR / f"digest-{date_str}.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] Saved to {out_path}")

    if method in ("email", "both", "all"):
        _send_smtp_email(delivery, subject, html)

    if method in ("telegram", "all"):
        _send_telegram(delivery, subject, html)

    if method in ("webhook", "all"):
        _send_webhook(delivery, subject, html)


# === Main Pipeline ===

def main():
    print("=" * 60)
    mode = f"{'[DRY-RUN] ' if DRY_RUN else ''}{'[FORCE] ' if FORCE else ''}"
    print(f"{mode}Podcast Daily Digest - {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M UTC')}")
    print("=" * 60)

    config = load_config()
    state = load_state()
    num_podcasts = len(config['podcasts'])
    print(f"Loaded {num_podcasts} podcasts from config")

    lookback = config.get("schedule", {}).get("lookback_hours", 24)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=lookback)
    print(f"Looking for episodes since {cutoff.strftime('%Y-%m-%d %H:%M UTC')}")

    all_episodes = fetch_all_feeds(config, cutoff)
    print(f"\nTotal new episodes found: {len(all_episodes)}")

    if FORCE:
        episodes = all_episodes
        for ep in episodes:
            ep["_eid"] = episode_id(ep["podcast_id"], {"id": ep["link"], "title": ep["title"]})
        print(f"Force mode: using all {len(episodes)} episodes")
    else:
        episodes = deduplicate(all_episodes, state)
        print(f"After dedup: {len(episodes)} new episodes")

    if not episodes:
        print("\nNo new episodes. Skipping.")
        save_state(state)
        return

    group_order = {"core": 0, "important": 1, "supplement": 2, "archive": 3, "custom": 2}
    episodes.sort(key=lambda e: (group_order.get(e["podcast_group"], 9), e["published"]))

    analysis = analyze_episodes(episodes, config)
    if not analysis:
        print("[ABORT] AI analysis failed. NO delivery. Will retry next run.")
        return

    from emailer import build_html_email
    html = build_html_email(analysis, config)

    if DRY_RUN:
        out_path = SKILL_DIR / "test_output.html"
        with open(out_path, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"\n[DRY-RUN] HTML saved to {out_path}")
    else:
        deliver(html, analysis, config)

    if not DRY_RUN:
        for ep in episodes:
            eid = ep.get("_eid", episode_id(ep["podcast_id"], {"id": ep["link"], "title": ep["title"]}))
            state["sent_ids"][eid] = datetime.now(timezone.utc).isoformat()
        save_state(state)

    print(f"\nDone! {'[DRY-RUN] ' if DRY_RUN else ''}Digest with {len(episodes)} episodes.")


if __name__ == "__main__":
    main()
