"""
Fetches GitHub contribution data for samritmukherjee.

Strategy:
  1. If GITHUB_TOKEN (or GH_TOKEN) is set: use the GitHub GraphQL API.
     This is the authoritative, rate-limit-friendly, authenticated route.
  2. Otherwise: fall back to scraping the public contributions calendar page.
     Useful for local development without a token.

Output: data/contributions.json (same schema in both cases).
"""

import os
import sys
import json
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path
from html.parser import HTMLParser

import requests

USERNAME = "samritmukherjee"
GRAPHQL_URL = "https://api.github.com/graphql"
CONTRIBUTIONS_URL = f"https://github.com/users/{USERNAME}/contributions"

LEVEL_MAP = {
    "NONE": 0,
    "FIRST_QUARTILE": 1,
    "SECOND_QUARTILE": 2,
    "THIRD_QUARTILE": 3,
    "FOURTH_QUARTILE": 4,
}

GRAPHQL_QUERY = """
query($login: String!, $from: DateTime!, $to: DateTime!) {
  user(login: $login) {
    contributionsCollection(from: $from, to: $to) {
      contributionCalendar {
        totalContributions
        weeks {
          contributionDays {
            date
            contributionCount
            contributionLevel
            weekday
          }
        }
      }
    }
  }
}
"""


# ---------------------------------------------------------------------------
# Shared utilities
# ---------------------------------------------------------------------------

def compute_streaks(sorted_days: list) -> tuple[int, int]:
    """Return (current_streak, longest_streak) from a chronologically sorted list."""
    longest_streak = 0
    run = 0
    for day in sorted_days:
        if day["count"] > 0:
            run += 1
            longest_streak = max(longest_streak, run)
        else:
            run = 0

    # Walk backwards from the most recent day to find the current streak
    current_streak = 0
    for day in reversed(sorted_days):
        if day["count"] > 0:
            current_streak += 1
        elif current_streak > 0:
            break

    return current_streak, longest_streak


def build_output(
    days: list,
    weeks: list,
    total_contributions: int,
    active_days: int,
    source: str,
) -> dict:
    """Assemble the canonical output dict."""
    current_streak, longest_streak = compute_streaks(days)
    return {
        "username": USERNAME,
        "source": source,
        "updated_at": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "total_contributions": total_contributions,
        "total_days": len(days),
        "active_days": active_days,
        "current_streak": current_streak,
        "longest_streak": longest_streak,
        "weeks_count": len(weeks),
        "days": days,
        "weeks": weeks,
    }


def save_json(data: dict, output_path: Path) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2)
    d = data
    print(
        f"Saved contributions to {output_path}\n"
        f"  {d['total_contributions']:,} contributions | "
        f"{d['active_days']} active days | "
        f"Current streak: {d['current_streak']}d | "
        f"Longest streak: {d['longest_streak']}d"
    )


# ---------------------------------------------------------------------------
# Strategy 1: GitHub GraphQL API (authenticated, preferred)
# ---------------------------------------------------------------------------

def fetch_via_graphql(token: str, output_path: Path) -> bool:
    """Fetch contributions via the GitHub GraphQL API using GITHUB_TOKEN."""
    now = datetime.now(timezone.utc)
    one_year_ago = now - timedelta(days=365)
    variables = {
        "login": USERNAME,
        "from": one_year_ago.strftime("%Y-%m-%dT%H:%M:%SZ"),
        "to": now.strftime("%Y-%m-%dT%H:%M:%SZ"),
    }
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json",
        "User-Agent": f"github-profile-readme-updater/{USERNAME}",
    }

    try:
        print("Fetching contributions via GitHub GraphQL API...")
        resp = requests.post(
            GRAPHQL_URL,
            json={"query": GRAPHQL_QUERY, "variables": variables},
            headers=headers,
            timeout=30,
        )
        resp.raise_for_status()
        result = resp.json()
    except Exception as exc:
        print(f"  GraphQL request failed: {exc}", file=sys.stderr)
        return False

    if "errors" in result:
        print(f"  GraphQL errors: {result['errors']}", file=sys.stderr)
        return False

    try:
        calendar = (
            result["data"]["user"]["contributionsCollection"]["contributionCalendar"]
        )
    except (KeyError, TypeError) as exc:
        print(f"  Unexpected GraphQL response structure: {exc}", file=sys.stderr)
        return False

    total_contributions = calendar.get("totalContributions", 0)
    gql_weeks = calendar.get("weeks", [])

    if not gql_weeks:
        print("  GraphQL returned no weeks data.", file=sys.stderr)
        return False

    all_days = []
    weeks = []
    active_days = 0

    for gql_week in gql_weeks:
        week_days = []
        for d in gql_week.get("contributionDays", []):
            date_str = d["date"]
            count = int(d["contributionCount"])
            level = LEVEL_MAP.get(d["contributionLevel"], 0)
            weekday = int(d["weekday"])  # 0=Sun ... 6=Sat (matches GitHub convention)
            month = datetime.strptime(date_str, "%Y-%m-%d").strftime("%b")
            day_obj = {
                "date": date_str,
                "level": level,
                "count": count,
                "weekday": weekday,
                "month": month,
            }
            all_days.append(day_obj)
            week_days.append(day_obj)
            if count > 0:
                active_days += 1
        if week_days:
            weeks.append(week_days)

    data = build_output(all_days, weeks, total_contributions, active_days, GRAPHQL_URL)
    save_json(data, output_path)
    return True


# ---------------------------------------------------------------------------
# Strategy 2: HTML calendar scraping (unauthenticated fallback)
# ---------------------------------------------------------------------------

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
            date = attrs_dict.get("data-date", "")
            level = int(attrs_dict.get("data-level", 0))
            cell_id = attrs_dict.get("id", "")
            self.days.append({"date": date, "level": level, "id": cell_id, "count": 0})
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


def fetch_via_html(output_path: Path) -> bool:
    """Scrape GitHub's public contributions calendar page as an unauthenticated fallback."""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml",
    }

    try:
        print(f"Fetching contribution calendar from {CONTRIBUTIONS_URL}...")
        resp = requests.get(CONTRIBUTIONS_URL, headers=headers, timeout=20)
        resp.raise_for_status()
    except Exception as exc:
        print(f"  HTML scrape failed: {exc}", file=sys.stderr)
        if output_path.exists():
            print(f"  Using existing cached data at {output_path}")
            return True
        save_fallback_data(output_path)
        return False

    parser = ContributionParser()
    parser.feed(resp.text)

    if not parser.days:
        print("  No contribution days parsed from HTML response.", file=sys.stderr)
        if output_path.exists():
            return True
        save_fallback_data(output_path)
        return False

    total_contributions = 0
    match_total = re.search(r"([\d,]+)\s+contributions", parser.raw_total_text)
    if match_total:
        total_contributions = int(match_total.group(1).replace(",", ""))

    active_days = 0
    summed_counts = 0
    sorted_days_raw = sorted(parser.days, key=lambda x: x["date"])

    for day in sorted_days_raw:
        tip = parser.tooltips.get(day.get("id", ""), "")
        day["tooltip"] = tip
        cnt_match = re.search(r"(\d+)\s+contribution", tip)
        if cnt_match:
            cnt = int(cnt_match.group(1))
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

    # Attach weekday / month metadata and group into weeks
    weeks = []
    current_week = []
    all_days = []

    for day in sorted_days_raw:
        dt = datetime.strptime(day["date"], "%Y-%m-%d")
        gh_weekday = (dt.weekday() + 1) % 7  # 0=Sun ... 6=Sat
        day["weekday"] = gh_weekday
        day["month"] = dt.strftime("%b")
        all_days.append(day)

        if gh_weekday == 0 and current_week:
            weeks.append(current_week)
            current_week = []
        current_week.append(day)

    if current_week:
        weeks.append(current_week)

    data = build_output(all_days, weeks, total_contributions, active_days, CONTRIBUTIONS_URL)
    save_json(data, output_path)
    return True


def save_fallback_data(output_path: Path) -> None:
    """Write a structurally valid but empty fallback when all fetches fail."""
    data = {
        "username": USERNAME,
        "source": "offline_fallback",
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
    print(f"  Saved offline fallback data to {output_path}", file=sys.stderr)


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------

def fetch_and_parse_contributions(output_path: Path) -> bool:
    """Public entry point: try GraphQL, fall back to HTML scraping."""
    token = os.environ.get("GITHUB_TOKEN") or os.environ.get("GH_TOKEN", "")

    if token:
        success = fetch_via_graphql(token, output_path)
        if not success:
            print("GraphQL fetch failed — falling back to HTML scraping...", file=sys.stderr)
            success = fetch_via_html(output_path)
    else:
        print("No GITHUB_TOKEN found — using HTML scraping (set GITHUB_TOKEN for authenticated API access).")
        success = fetch_via_html(output_path)

    return success


def main():
    root = Path(__file__).resolve().parent.parent
    data_file = root / "data" / "contributions.json"
    success = fetch_and_parse_contributions(data_file)
    if not success and not data_file.exists():
        print("FATAL: Could not fetch contributions and no cached data found.", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
