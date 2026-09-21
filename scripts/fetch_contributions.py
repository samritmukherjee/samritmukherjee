"""
Fetches public GitHub contribution data for samritmukherjee.
Parses the contribution calendar, computes statistics, and saves data/contributions.json.
Gracefully falls back to existing cached data if offline or network fails.
"""

import sys
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from html.parser import HTMLParser
import requests


USERNAME = "samritmukherjee"
CONTRIBUTIONS_URL = f"https://github.com/users/{USERNAME}/contributions"


class ContributionParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.days = []
        self.tooltips = {}
        self.current_tooltip_for = None
        self.raw_total_text = ""
        self.in_h2 = False

    def handle_starttag(self, tag, attrs):
        attrs_dict = dict(attrs)
        if tag == "h2" and "js-contribution-activity-description" in attrs_dict.get("id", ""):
            self.in_h2 = True
        elif tag == "td" and "data-date" in attrs_dict:
            date = attrs_dict.get("data-date")
            level = int(attrs_dict.get("data-level", 0))
            cell_id = attrs_dict.get("id")
            self.days.append({
                "date": date,
                "level": level,
                "id": cell_id,
                "count": 0,
            })
        elif tag == "tool-tip" and "for" in attrs_dict:
            self.current_tooltip_for = attrs_dict["for"]

    def handle_data(self, data):
        if self.in_h2:
            self.raw_total_text += " " + data.strip()
        elif self.current_tooltip_for:
            self.tooltips[self.current_tooltip_for] = data.strip()

    def handle_endtag(self, tag):
        if tag == "h2" and self.in_h2:
            self.in_h2 = False
        elif tag == "tool-tip" and self.current_tooltip_for:
            self.current_tooltip_for = None


def compute_streaks(sorted_days):
    """Compute current streak and longest streak in days."""
    longest_streak = 0
    curr_streak = 0

    for day in sorted_days:
        if day["count"] > 0:
            curr_streak += 1
            if curr_streak > longest_streak:
                longest_streak = curr_streak
        else:
            curr_streak = 0

    # Current streak looking backwards from the last day
    current_streak = 0
    # Walk backwards from the end
    for day in reversed(sorted_days):
        if day["count"] > 0:
            current_streak += 1
        elif current_streak > 0:
            break

    return current_streak, longest_streak


def fetch_and_parse_contributions(output_path: Path):
    """Fetch GitHub contributions calendar, parse, and save JSON."""
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9",
    }

    try:
        print(f"Fetching contribution calendar from {CONTRIBUTIONS_URL}...")
        resp = requests.get(CONTRIBUTIONS_URL, headers=headers, timeout=15)
        resp.raise_for_status()
        html_content = resp.text
    except Exception as e:
        print(f"Warning: Failed to fetch online contributions: {e}", file=sys.stderr)
        if output_path.exists():
            print(f"Using existing cached data at: {output_path}")
            return True
        else:
            print("No cached data found. Generating fallback data.", file=sys.stderr)
            save_fallback_data(output_path)
            return False

    parser = ContributionParser()
    parser.feed(html_content)

    if not parser.days:
        print("Warning: No contribution days parsed from response.", file=sys.stderr)
        if output_path.exists():
            return True
        save_fallback_data(output_path)
        return False

    # Extract total contributions in the last year
    total_contributions = 0
    match_total = re.search(r'([\d,]+)\s+contributions', parser.raw_total_text)
    if match_total:
        total_contributions = int(match_total.group(1).replace(",", ""))

    # Populate exact counts from tooltips
    active_days = 0
    summed_counts = 0
    for day in parser.days:
        tip = parser.tooltips.get(day.get("id", ""), "")
        day["tooltip"] = tip
        count_match = re.search(r'(\d+)\s+contribution', tip)
        if count_match:
            cnt = int(count_match.group(1))
            day["count"] = cnt
            summed_counts += cnt
        elif "No contributions" in tip:
            day["count"] = 0
        else:
            day["count"] = 1 if day["level"] > 0 else 0

        if day["count"] > 0:
            active_days += 1

    if total_contributions == 0 and summed_counts > 0:
        total_contributions = summed_counts

    # Sort days chronologically
    sorted_days = sorted(parser.days, key=lambda x: x["date"])
    curr_streak, longest_streak = compute_streaks(sorted_days)

    # Group into weeks (52-53 columns)
    # Determine day-of-week for each date (Monday=0..Sunday=6, but GitHub uses Sunday=0)
    weeks = []
    current_week = []

    for day in sorted_days:
        dt = datetime.strptime(day["date"], "%Y-%m-%d")
        gh_weekday = (dt.weekday() + 1) % 7  # 0=Sun, 1=Mon, ..., 6=Sat
        day["weekday"] = gh_weekday
        day["month"] = dt.strftime("%b")

        if gh_weekday == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(day)

    if current_week:
        weeks.append(current_week)

    data = {
        "username": USERNAME,
        "source": CONTRIBUTIONS_URL,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_contributions": total_contributions,
        "total_days": len(sorted_days),
        "active_days": active_days,
        "current_streak": curr_streak,
        "longest_streak": longest_streak,
        "weeks_count": len(weeks),
        "days": sorted_days,
        "weeks": weeks,
    }

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)

    print(f"Successfully saved contributions to {output_path}")
    print(f"Summary: {total_contributions} contributions | {active_days} active days | Longest streak: {longest_streak} days")
    return True


def save_fallback_data(output_path: Path):
    """Save an empty or fallback JSON schema if initial fetch fails."""
    data = {
        "username": USERNAME,
        "source": CONTRIBUTIONS_URL,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "status": "offline_fallback",
        "total_contributions": 0,
        "total_days": 0,
        "active_days": 0,
        "current_streak": 0,
        "longest_streak": 0,
        "weeks_count": 0,
        "days": [],
        "weeks": [],
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)


def main():
    root = Path(__file__).resolve().parent.parent
    data_file = root / "data" / "contributions.json"
    success = fetch_and_parse_contributions(data_file)
    if not success and not data_file.exists():
        sys.exit(1)


if __name__ == "__main__":
    main()
