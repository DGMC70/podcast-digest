#!/usr/bin/env python3
"""
Podcast Daily Digest - HTML Email Builder
Generates the dark-theme HTML email from AI analysis output.
"""

import html as html_mod
from datetime import datetime, timezone

def esc(text):
    """HTML-escape text."""
    return html_mod.escape(str(text)) if text else ""

def color_for_topic(idx, color_hint=""):
    """Return border color for trending topic."""
    colors = {"red": "#ff6b6b", "orange": "#f4a261", "blue": "#74b9ff", "green": "#95d5b2"}
    if color_hint in colors:
        return colors[color_hint]
    defaults = ["#ff6b6b", "#f4a261", "#74b9ff", "#95d5b2"]
    return defaults[idx % len(defaults)]

def build_category_badges(categories):
    """Build HTML for category tag badges."""
    cat_colors = {
        "AI": ("#2a1a3a", "#c9a0dc"),
        "Crypto": ("#2a2a1a", "#e8c87a"),
        "加密": ("#2a2a1a", "#e8c87a"),
        "VC": ("#3b2a1a", "#f4a261"),
        "宏观": ("#1b4332", "#95d5b2"),
        "地缘": ("#1b4332", "#95d5b2"),
        "科技": ("#1a2a3b", "#74b9ff"),
        "新公司": ("#3b2a1a", "#f4a261"),
        "创始人": ("#2a1a3a", "#c9a0dc"),
        "投资": ("#3b2a1a", "#f4a261"),
        "方法论": ("#1a2a3b", "#74b9ff"),
        "趋势": ("#1b4332", "#95d5b2"),
    }
    badges = []
    for cat in (categories or []):
        bg, fg = cat_colors.get(cat, ("#1a1a2e", "#aaa"))
        badges.append(
            f'<span style="font-size:10px;background:{bg};color:{fg};'
            f'padding:2px 8px;border-radius:10px;">{esc(cat)}</span>'
        )
    return " ".join(badges)

def build_html_email(analysis, config):
    """Build the full HTML email from analysis data."""
    date_str = analysis.get("date", datetime.now(timezone.utc).strftime("%Y-%m-%d"))
    total_eps = analysis.get("total_episodes", 0)
    trends = analysis.get("trending_topics", [])
    deep_dives = analysis.get("deep_dives", [])
    standard_eps = analysis.get("standard_episodes", [])
    discoveries = analysis.get("discoveries", {})

    # Day of week
    weekdays_zh = ["周一", "周二", "周三", "周四", "周五", "周六", "周日"]
    try:
        d = datetime.strptime(date_str, "%Y-%m-%d")
        weekday = weekdays_zh[d.weekday()]
    except ValueError:
        weekday = ""

    num_podcasts = len(config.get("podcasts", []))

    parts = []

    # === Document start ===
    parts.append(f"""<!DOCTYPE html>
<html>
<head><meta charset="UTF-8"></head>
<body style="margin:0;padding:0;background:#0d1117;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI','PingFang SC','Microsoft YaHei',sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#0d1117;padding:20px 0;">
<tr><td align="center">
<table width="640" cellpadding="0" cellspacing="0" style="background:#161b22;border-radius:12px;overflow:hidden;border:1px solid #30363d;">

<!-- Header -->
<tr><td style="background:linear-gradient(135deg,#1a2744,#0d1117);padding:24px 28px;border-bottom:2px solid #2a4a7a;">
  <div style="font-size:22px;color:#fff;font-weight:700;">&#127908; Podcast Daily Digest</div>
  <div style="font-size:13px;color:#7eb8ff;margin-top:4px;">{esc(date_str)} {esc(weekday)} | 监控 {num_podcasts} 个播客</div>
  <div style="font-size:12px;color:#666;margin-top:6px;">&#128202; 今日更新 {total_eps} 期 &nbsp;|&nbsp; &#128293; {len(trends)} 个跨播客热点 &nbsp;|&nbsp; &#11088; {len(deep_dives)} 期深度推荐</div>
</td></tr>""")

    # === Trending Topics ===
    if trends:
        parts.append("""
<!-- Trending Topics -->
<tr><td style="padding:24px 28px 8px;">
  <div style="font-size:15px;color:#f4a261;font-weight:700;margin-bottom:16px;">&#128293; 跨播客热点趋势</div>""")

        for i, topic in enumerate(trends):
            border_color = color_for_topic(i, topic.get("color", ""))
            podcasts_str = " &bull; ".join(esc(p) for p in topic.get("podcasts", []))
            parts.append(f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:14px;">
  <tr><td style="background:#1a1a2e;border-left:3px solid {border_color};border-radius:6px;padding:14px 16px;">
    <div style="font-size:14px;color:#fff;font-weight:600;">{i+1}. {esc(topic.get('title', ''))}</div>
    <div style="font-size:11px;color:#7eb8ff;margin:4px 0;">&#128205; {podcasts_str}</div>
    <div style="font-size:13px;color:#aaa;line-height:1.5;">{esc(topic.get('summary', ''))}</div>
  </td></tr></table>""")

        parts.append("</td></tr>")

    # === Deep Dives ===
    if deep_dives:
        parts.append("""
<!-- Deep Dives -->
<tr><td style="padding:8px 28px;">
  <div style="font-size:15px;color:#95d5b2;font-weight:700;margin-bottom:16px;padding-top:8px;border-top:1px solid #30363d;">&#11088; 深度推荐</div>""")

        for dd in deep_dives:
            badges = build_category_badges(dd.get("categories", []))
            badges += ' <span style="font-size:10px;background:#3b1a1a;color:#ff6b6b;padding:2px 8px;border-radius:10px;">&#11088; 深度</span>'

            link = esc(dd.get("link", "#"))
            title = esc(dd.get("title", ""))
            hosts = esc(dd.get("hosts_guests", ""))
            duration = esc(dd.get("duration", ""))
            overview = esc(dd.get("overview", ""))

            parts.append(f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:18px;">
  <tr><td style="background:rgba(255,255,255,0.03);border-radius:8px;padding:18px;border:1px solid #2a3a4a;">
    <div style="margin-bottom:6px;">{badges}</div>
    <div style="font-size:15px;color:#fff;font-weight:700;">
      <a href="{link}" style="color:#fff;text-decoration:none;">{esc(dd.get('podcast_name',''))}: {title} &#8599;</a>
    </div>
    <div style="font-size:12px;color:#666;margin-top:4px;">{hosts} &nbsp;|&nbsp; {duration}</div>
    <div style="font-size:13px;color:#ccc;line-height:1.7;margin-top:12px;">{overview}</div>""")

            # Insights
            insights = dd.get("insights", [])
            if insights:
                parts.append("""
    <div style="margin-top:12px;padding:12px 14px;background:rgba(255,255,255,0.03);border-radius:6px;">
      <div style="font-size:12px;color:#f4a261;font-weight:600;margin-bottom:8px;">&#128161; 关键非共识观点 / 独特洞察：</div>
      <table cellpadding="0" cellspacing="0" style="font-size:12.5px;color:#ccc;line-height:1.7;">""")
                for ins in insights:
                    parts.append(f"""
        <tr><td style="vertical-align:top;padding:0 8px 6px 0;color:#666;">&#9679;</td>
        <td style="padding-bottom:6px;"><strong style="color:#fff;">{esc(ins.get('title',''))}</strong> {esc(ins.get('detail',''))}</td></tr>""")
                parts.append("</table></div>")

            # Quote
            quote = dd.get("quote")
            if quote and quote.get("text"):
                parts.append(f"""
    <div style="font-size:12px;color:#95d5b2;font-style:italic;margin-top:10px;padding-left:12px;border-left:2px solid #2d6a4f;">
      &#128172; "{esc(quote['text'])}" &mdash; {esc(quote.get('speaker',''))} {esc(quote.get('context',''))}
    </div>""")

            parts.append("</td></tr></table>")

        parts.append("</td></tr>")

    # === Standard Episodes ===
    if standard_eps:
        # Group by rough category
        parts.append("""
<!-- Standard Episodes -->
<tr><td style="padding:8px 28px;">
  <div style="font-size:14px;color:#8b949e;font-weight:600;margin-bottom:14px;padding-top:8px;border-top:1px solid #30363d;">&#128196; 其他更新</div>""")

        for ep in standard_eps:
            link = esc(ep.get("link", "#"))
            title = esc(ep.get("title", ""))
            podcast_name = esc(ep.get("podcast_name", ""))
            summary = esc(ep.get("summary", ""))
            badges = build_category_badges(ep.get("categories", []))

            parts.append(f"""
  <table width="100%" cellpadding="0" cellspacing="0" style="margin-bottom:10px;">
  <tr><td style="padding:10px 0;border-bottom:1px solid #1e1e2e;">
    <div style="margin-bottom:3px;">{badges}</div>
    <div style="font-size:13px;color:#fff;font-weight:600;">
      <a href="{link}" style="color:#fff;text-decoration:none;">{podcast_name}: {title} &#8599;</a>
    </div>
    <div style="font-size:12px;color:#999;line-height:1.5;margin-top:4px;">{summary}</div>
  </td></tr></table>""")

        parts.append("</td></tr>")

    # === Discoveries ===
    disco_items = []
    for item in discoveries.get("new_companies", []):
        disco_items.append(f"&#127970; <strong>新公司：</strong>{esc(item)}")
    for item in discoveries.get("key_data", []):
        disco_items.append(f"&#128202; <strong>关键数据：</strong>{esc(item)}")
    for item in discoveries.get("trend_signals", []):
        disco_items.append(f"&#128200; <strong>趋势信号：</strong>{esc(item)}")
    for item in discoveries.get("watch_items", []):
        disco_items.append(f"&#128064; <strong>值得关注：</strong>{esc(item)}")
    for item in discoveries.get("risk_alerts", []):
        disco_items.append(f"&#9888;&#65039; <strong>风险提示：</strong>{esc(item)}")
    for item in discoveries.get("frameworks", []):
        disco_items.append(f"&#128161; <strong>方法论：</strong>{esc(item)}")

    if disco_items:
        disco_html = "<br>\n      ".join(disco_items)
        parts.append(f"""
<!-- Discoveries -->
<tr><td style="padding:16px 28px;">
  <div style="background:#1a2744;border-radius:8px;padding:16px;border:1px solid #2a4a7a;">
    <div style="font-size:14px;color:#7eb8ff;font-weight:700;margin-bottom:10px;">&#127381; 今日发现</div>
    <div style="font-size:12px;color:#ccc;line-height:1.8;">
      {disco_html}
    </div>
  </div>
</td></tr>""")

    # === Footer ===
    parts.append(f"""
<!-- Footer -->
<tr><td style="padding:16px 28px 24px;border-top:1px solid #30363d;">
  <div style="font-size:11px;color:#555;text-align:center;">
    &#128236; Podcast Digest Bot 自动生成 &nbsp;|&nbsp; &#128225; 监控 {num_podcasts} 个播客<br>
    涵盖 AI / Crypto / VC / 宏观 / 政经<br>
    <span style="color:#444;">&#11088; 深度推荐 = AI 筛选出的高信息密度、非共识观点节目</span>
  </div>
</td></tr>

</table>
</td></tr></table>
</body>
</html>""")

    return "\n".join(parts)
