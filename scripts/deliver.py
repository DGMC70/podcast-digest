#!/usr/bin/env python3
"""
Deliver an HTML digest file via configured channel(s).

Usage:
  python deliver.py digest.html                       # Deliver via config
  python deliver.py digest.html --method file          # Override method
  python deliver.py digest.html --subject "Custom subject"
"""

import json
import os
import sys
import smtplib
import urllib.request
import urllib.error
import re as re_mod
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config.json"


def load_config():
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            return json.load(f)
    return {}


def send_smtp(delivery, subject, html):
    smtp_host = delivery.get("smtp_host", "")
    smtp_port = delivery.get("smtp_port", 587)
    smtp_user = delivery.get("smtp_user", "")
    smtp_pass = os.environ.get("SMTP_PASSWORD", "")
    from_email = delivery.get("email_from", smtp_user)
    to_email = delivery.get("email_to", "")

    if not all([smtp_host, smtp_user, smtp_pass, to_email]):
        print("[WARN] SMTP not fully configured.", file=sys.stderr)
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
        print(f"[OK] Email sent to {to_email}", file=sys.stderr)
        return True
    except Exception as e:
        print(f"[ERROR] SMTP: {e}", file=sys.stderr)
        return False


def send_telegram(delivery, subject, html):
    bot_token = os.environ.get("TELEGRAM_BOT_TOKEN", "")
    chat_id = delivery.get("telegram_chat_id", "")

    if not bot_token or not chat_id:
        print("[WARN] Telegram not configured.", file=sys.stderr)
        return False

    text = re_mod.sub(r'<[^>]+>', '', html)[:4000]
    text = f"*{subject}*\n\n{text}"

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
    payload = json.dumps({"chat_id": chat_id, "text": text, "parse_mode": "Markdown"}).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("ok"):
                print(f"[OK] Telegram sent to {chat_id}", file=sys.stderr)
                return True
    except Exception as e:
        print(f"[ERROR] Telegram: {e}", file=sys.stderr)
    return False


def send_webhook(delivery, subject, html):
    webhook_url = delivery.get("webhook_url", "")
    if not webhook_url:
        return False
    text = re_mod.sub(r'<[^>]+>', '', html)[:4000]
    payload = json.dumps({"text": f"{subject}\n\n{text}"}).encode("utf-8")
    try:
        req = urllib.request.Request(webhook_url, data=payload,
                                     headers={"Content-Type": "application/json"}, method="POST")
        with urllib.request.urlopen(req, timeout=30) as resp:
            if 200 <= resp.status < 300:
                print(f"[OK] Webhook delivered", file=sys.stderr)
                return True
    except Exception as e:
        print(f"[ERROR] Webhook: {e}", file=sys.stderr)
    return False


def main():
    if len(sys.argv) < 2:
        print("Usage: python deliver.py <digest.html> [--method METHOD] [--subject SUBJECT]", file=sys.stderr)
        sys.exit(1)

    html_path = sys.argv[1]
    with open(html_path, encoding="utf-8") as f:
        html = f.read()

    config = load_config()
    delivery = config.get("delivery", {"method": "file"})

    method_override = None
    subject = None
    for i, arg in enumerate(sys.argv):
        if arg == "--method" and i + 1 < len(sys.argv):
            method_override = sys.argv[i + 1]
        if arg == "--subject" and i + 1 < len(sys.argv):
            subject = sys.argv[i + 1]

    method = method_override or delivery.get("method", "file")
    date_str = datetime.now().strftime("%Y-%m-%d")
    if not subject:
        subject = f"\U0001f399 Podcast Daily Digest | {date_str}"

    if method in ("file", "both", "all"):
        out = SKILL_DIR / f"digest-{date_str}.html"
        with open(out, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"[OK] Saved to {out}", file=sys.stderr)

    if method in ("email", "both", "all"):
        send_smtp(delivery, subject, html)

    if method in ("telegram", "all"):
        send_telegram(delivery, subject, html)

    if method in ("webhook", "all"):
        send_webhook(delivery, subject, html)

    print("Delivery complete.", file=sys.stderr)


if __name__ == "__main__":
    main()
