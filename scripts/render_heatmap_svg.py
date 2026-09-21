"""
Renders an animated GitHub contribution heatmap SVG and static fallback using verified real data.
Features classic GitHub green palette, month headers, stats summary, and legend.
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime

# GitHub dark mode green palette
PALETTE = {
    0: "#161b22",  # No contributions
    1: "#0e4429",  # Low
    2: "#006d32",  # Medium-low
    3: "#26a641",  # Medium-high
    4: "#39d353",  # High
}

PALETTE_STROKE = {
    0: "#21262d",
    1: "#0e4429",
    2: "#006d32",
    3: "#26a641",
    4: "#39d353",
}


def render_heatmap(
    data: dict,
    output_path: Path,
    animated: bool = True,
    width: int = 860,
    height: int = 210,
):
    """Render heatmap SVG from parsed contribution data."""
    weeks = data.get("weeks", [])
    total_contributions = data.get("total_contributions", 0)
    active_days = data.get("active_days", 0)
    longest_streak = data.get("longest_streak", 0)
    updated_at = data.get("updated_at", datetime.utcnow().strftime("%Y-%m-%d"))

    # Grid layout constants
    start_x = 44
    start_y = 66
    cell_size = 11
    cell_gap = 3.5
    step_x = cell_size + cell_gap
    step_y = cell_size + cell_gap

    # Build Day of Week labels (Mon=1, Wed=3, Fri=5)
    day_labels = [
        ("Mon", start_y + 1 * step_y + cell_size - 2),
        ("Wed", start_y + 3 * step_y + cell_size - 2),
        ("Fri", start_y + 5 * step_y + cell_size - 2),
    ]

    day_labels_svg = []
    for lbl, y in day_labels:
        day_labels_svg.append(
            f'    <text x="{start_x - 8}" y="{y}" class="axis-label" text-anchor="end">{lbl}</text>'
        )

    # Build Month labels and cells
    month_labels_svg = []
    cells_svg = []
    last_month = None

    col_delay = 0.02
    base_delay = 0.2

    for col_idx, week in enumerate(weeks):
        x = start_x + col_idx * step_x

        # Check if month changed in this week
        first_day_of_week = week[0] if week else None
        if first_day_of_week:
            m = first_day_of_week.get("month", "")
            if m != last_month and col_idx < len(weeks) - 2:
                month_labels_svg.append(
                    f'    <text x="{x}" y="{start_y - 8}" class="axis-label">{m}</text>'
                )
                last_month = m

        col_anim_delay = base_delay + col_idx * col_delay

        for day in week:
            weekday = day.get("weekday", 0)
            y = start_y + weekday * step_y
            level = day.get("level", 0)
            count = day.get("count", 0)
            date_str = day.get("date", "")
            color = PALETTE.get(level, PALETTE[0])
            stroke_color = PALETTE_STROKE.get(level, PALETTE_STROKE[0])

            tip_text = f"{count} contributions on {date_str}" if count > 0 else f"No contributions on {date_str}"

            anim_tag = ""
            if animated:
                anim_tag = (
                    f'<animate attributeName="opacity" from="0" to="1" dur="0.15s" '
                    f'begin="{col_anim_delay:.2f}s" fill="freeze"/>'
                )

            rect = (
                f'    <rect x="{x:.1f}" y="{y:.1f}" width="{cell_size}" height="{cell_size}" '
                f'rx="2.5" fill="{color}" stroke="{stroke_color}" stroke-width="0.5" '
                f'opacity="{"0" if animated else "1"}">\n'
                f'      <title>{tip_text}</title>\n'
                f'      {anim_tag}\n'
                f'    </rect>'
            )
            cells_svg.append(rect)

    # Legend at bottom right
    legend_x = width - 180
    legend_y = height - 22
    legend_rects = []
    for lvl in range(5):
        lx = legend_x + 36 + lvl * (cell_size + 3)
        legend_rects.append(
            f'<rect x="{lx}" y="{legend_y - 9}" width="{cell_size}" height="{cell_size}" rx="2" fill="{PALETTE[lvl]}" stroke="{PALETTE_STROKE[lvl]}" stroke-width="0.5"/>'
        )

    legend_svg = (
        f'    <g id="legend">\n'
        f'      <text x="{legend_x}" y="{legend_y}" class="meta-label">Less</text>\n'
        f'      {" ".join(legend_rects)}\n'
        f'      <text x="{legend_x + 36 + 5 * (cell_size + 3) + 4}" y="{legend_y}" class="meta-label">More</text>\n'
        f'    </g>'
    )

    # Header stats
    header_title = f"samrit@github ~ $ git log --contributions --last-year"
    stats_summary = f"{total_contributions:,} Total Contributions  •  {active_days} Active Days  •  Longest Streak: {longest_streak}d"

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <filter id="cardGlow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="6" stdDeviation="10" flood-color="#000000" flood-opacity="0.4"/>
    </filter>
  </defs>

  <style>
    .card-bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
    .header-bar {{ fill: #161b22; stroke: #30363d; stroke-width: 1px; }}
    .term-title {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; font-weight: 600; }}
    .stats-title {{ fill: #39d353; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; font-weight: 700; }}
    .axis-label {{ fill: #7d8590; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 9px; }}
    .meta-label {{ fill: #7d8590; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 10px; }}
    .brand-link {{ fill: #58a6ff; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 10px; }}
  </style>

  <!-- Background Frame -->
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" class="card-bg" filter="url(#cardGlow)" />

  <!-- Header -->
  <path d="M 1 10 Q 1 1 10 1 L {width - 10} 1 Q {width - 1} 1 {width - 1} 10 L {width - 1} 36 L 1 36 Z" class="header-bar" />
  <circle cx="20" cy="18" r="5" fill="#ff5f56" />
  <circle cx="36" cy="18" r="5" fill="#ffbd2e" />
  <circle cx="52" cy="18" r="5" fill="#27c93f" />

  <text x="72" y="22" class="term-title">{header_title}</text>
  <text x="{width - 24}" y="22" text-anchor="end" class="stats-title">{stats_summary}</text>

  <!-- Month Labels -->
{chr(10).join(month_labels_svg)}

  <!-- Day Labels -->
{chr(10).join(day_labels_svg)}

  <!-- Grid Cells -->
  <g id="heatmap-cells">
{chr(10).join(cells_svg)}
  </g>

  <!-- Footer Metadata & Legend -->
  <text x="{start_x}" y="{height - 22}" class="meta-label">
    Data synced from <tspan class="brand-link">github.com/samritmukherjee</tspan> (Updated {updated_at})
  </text>
{legend_svg}
</svg>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Heatmap SVG generated: {output_path} ({'animated' if animated else 'static'})")


def main():
    parser = argparse.ArgumentParser(description="Render GitHub contribution heatmap SVG")
    parser.add_argument("--static", action="store_true", help="Generate static SVG without animations")
    parser.add_argument("--both", action="store_true", help="Generate both animated and static SVGs")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    data_file = root / "data" / "contributions.json"

    if not data_file.exists():
        print(f"Data file {data_file} not found. Running fetch_contributions.py first...")
        from fetch_contributions import fetch_and_parse_contributions
        fetch_and_parse_contributions(data_file)

    with open(data_file, "r", encoding="utf-8") as f:
        data = json.load(f)

    anim_out = root / "assets" / "contribution-heatmap.svg"
    static_out = root / "assets" / "contribution-heatmap-static.svg"

    if args.both:
        render_heatmap(data, anim_out, animated=True)
        render_heatmap(data, static_out, animated=False)
    elif args.static:
        render_heatmap(data, static_out, animated=False)
    else:
        render_heatmap(data, anim_out, animated=True)


if __name__ == "__main__":
    main()
