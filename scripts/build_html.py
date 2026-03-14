#!/usr/bin/env python3
"""
Build dark-themed HTML digest from analysis JSON.

Usage:
  python build_html.py analysis.json                  # Output HTML to stdout
  python build_html.py analysis.json --output FILE    # Write to file
"""

import json
import sys
from pathlib import Path

SCRIPT_DIR = Path(__file__).parent.resolve()
SKILL_DIR = SCRIPT_DIR.parent
CONFIG_PATH = SKILL_DIR / "config.json"

sys.path.insert(0, str(SCRIPT_DIR))
from emailer import build_html_email


def main():
    if len(sys.argv) < 2:
        print("Usage: python build_html.py <analysis.json> [--output FILE]", file=sys.stderr)
        sys.exit(1)

    analysis_path = sys.argv[1]
    with open(analysis_path, encoding="utf-8") as f:
        analysis = json.load(f)

    config = {}
    if CONFIG_PATH.exists():
        with open(CONFIG_PATH, encoding="utf-8") as f:
            config = json.load(f)

    html = build_html_email(analysis, config)

    output_file = None
    for i, arg in enumerate(sys.argv):
        if arg == "--output" and i + 1 < len(sys.argv):
            output_file = sys.argv[i + 1]

    if output_file:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(html)
        print(f"HTML written to {output_file}", file=sys.stderr)
    else:
        print(html)


if __name__ == "__main__":
    main()
