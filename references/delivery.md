# Delivery Channel Reference

## File (Default)

Saves HTML digest to `{skill_dir}/digest-{date}.html`. No external dependencies.

## Email (SMTP)

Standard SMTP email delivery. Works with any email provider.

### Common SMTP Servers

| Provider | Host | Port | Notes |
|----------|------|------|-------|
| Gmail | `smtp.gmail.com` | 587 | Requires [App Password](https://support.google.com/accounts/answer/185833) |
| Outlook/365 | `smtp.office365.com` | 587 | |
| QQ Mail | `smtp.qq.com` | 465 (SSL) | Requires authorization code |
| 163 Mail | `smtp.163.com` | 465 (SSL) | Requires authorization code |
| Custom | Your server | 587/465 | |

### Config

```json
{
  "delivery": {
    "method": "email",
    "smtp_host": "smtp.gmail.com",
    "smtp_port": 587,
    "smtp_user": "you@gmail.com",
    "email_from": "you@gmail.com",
    "email_to": "recipient@example.com"
  }
}
```

### Environment Variable

```bash
export SMTP_PASSWORD="your-app-password"
```

## Telegram

Sends a text summary via Telegram Bot.

### Setup Steps

1. Message [@BotFather](https://t.me/BotFather) on Telegram → create a new bot → get your bot token
2. Get your Chat ID: message [@userinfobot](https://t.me/userinfobot) or [@RawDataBot](https://t.me/RawDataBot)
3. Add your bot to the target chat/group

### Config

```json
{
  "delivery": {
    "method": "telegram",
    "telegram_chat_id": "123456789"
  }
}
```

### Environment Variable

```bash
export TELEGRAM_BOT_TOKEN="123456:ABC-DEF..."
```

## Webhook

Generic webhook for Slack, Discord, or custom endpoints.

### Config

```json
{
  "delivery": {
    "method": "webhook",
    "webhook_url": "https://hooks.slack.com/services/..."
  }
}
```

## All Channels

Use `"method": "all"` to send via every configured channel simultaneously.

```json
{
  "delivery": {
    "method": "all",
    "smtp_host": "...",
    "email_to": "...",
    "telegram_chat_id": "...",
    "webhook_url": "..."
  }
}
```

## Security Notes

- **Never store passwords/tokens in config.json.** Use environment variables.
- The setup wizard reminds you which env vars to set.
- For Gmail, use [App Passwords](https://support.google.com/accounts/answer/185833), not your account password.
