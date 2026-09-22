"""
Renders an animated GitHub contribution heatmap SVG and static fallback.

Geometry: 860 x 155 px compact layout (matches the proto2 design).
Features:
- Individual box-by-box diagonal wave reveal animation
- Classic GitHub dark-mode green palette (5 levels)
- Month and weekday axis labels
- Terminal-style header card
- Less → More legend + timestamp footer
- Zero emojis
"""

import sys
import json
import argparse
from pathlib import Path
from datetime import datetime, timezone

# Classic GitHub dark mode green palette
PALETTE = {
    0: "#161b22",  # Empty
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

# ---------------------------------------------------------------------------
# Layout constants — compact 155px design (proto2)
# ---------------------------------------------------------------------------
SVG_WIDTH = 860
SVG_HEIGHT = 155

# Grid
START_X = 44          # left edge of first column
START_Y = 46          # top edge of row 0 (Sunday)
CELL_SIZE = 9.5       # square cell side length (px)
STEP_X = 14.5         # column pitch (horizontal spacing between cell left edges)
STEP_Y = 11.5         # row pitch (vertical spacing between cell top edges)
CELL_RX = 1.5         # corner radius on cells

# Header bar (terminal card top)
HEADER_H = 28         # header bar bottom y
DOT_CY = 14           # vertical centre of traffic-light dots
DOT_R = 4             # dot radius
DOT_MARGIN = 18       # x of first (red) dot centre
DOT_STEP = 14         # horizontal step between dot centres
TITLE_X = 62          # x of terminal prompt text
TITLE_Y = 18          # baseline y of terminal prompt text

# Month labels (above the grid)
MONTH_Y = START_Y - 7   # = 39

# Day-of-week labels (Mon / Wed / Fri, right-aligned to x=36)
DAY_LABEL_X = START_X - 8   # = 36

# Footer
FOOTER_TEXT_Y = SVG_HEIGHT - 12     # ≈ 143  (text baseline)
LEGEND_RECT_Y = SVG_HEIGHT - CELL_SIZE - 10  # ≈ 135.5  (top of legend squares)
LEGEND_X = SVG_WIDTH - 180          # = 680  (x of "Less" text)
LEGEND_RECT_START = LEGEND_X + 36   # = 716  (x of first legend square)
LEGEND_STEP = CELL_SIZE + 3.5       # ≈ 13   (spacing between legend squares)

# Animation timing
BASE_DELAY = 0.20
COL_STEP = 0.024
ROW_STEP = 0.014


def _day_label_y(weekday: int) -> float:
    """Vertical baseline for a Mon/Wed/Fri label aligned to its cell row."""
    return round(START_Y + weekday * STEP_Y + CELL_SIZE / 2 + 3, 1)


def render_heatmap(
    data: dict,
    output_path: Path,
    animated: bool = True,
):
    """Render the contribution heatmap SVG."""
    weeks = data.get("weeks", [])
    total_contributions = data.get("total_contributions", 0)
    active_days = data.get("active_days", 0)
    current_streak = data.get("current_streak", 0)
    updated_at = data.get(
        "updated_at", datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")
    )

    # ------------------------------------------------------------------
    # Day-of-week axis labels
    # ------------------------------------------------------------------
    day_labels_svg = [
        f'    <text x="{DAY_LABEL_X}" y="{_day_label_y(1)}" class="axis-label" text-anchor="end">Mon</text>',
        f'    <text x="{DAY_LABEL_X}" y="{_day_label_y(3)}" class="axis-label" text-anchor="end">Wed</text>',
        f'    <text x="{DAY_LABEL_X}" y="{_day_label_y(5)}" class="axis-label" text-anchor="end">Fri</text>',
    ]

    # ------------------------------------------------------------------
    # Month labels + animated cells
    # ------------------------------------------------------------------
    month_labels_svg = []
    cells_svg = []
    last_month = None

    for col_idx, week in enumerate(weeks):
        x = round(START_X + col_idx * STEP_X, 1)

        # Month header — show on the first week of each month
        first_day = week[0] if week else None
        if first_day:
            m = first_day.get("month", "")
            if m != last_month and col_idx < len(weeks) - 2:
                month_labels_svg.append(
                    f'    <text x="{x}" y="{MONTH_Y}" class="axis-label">{m}</text>'
                )
                last_month = m

        for day in week:
            weekday = day.get("weekday", 0)
            y = round(START_Y + weekday * STEP_Y, 1)
            level = day.get("level", 0)
            count = day.get("count", 0)
            date_str = day.get("date", "")
            color = PALETTE.get(level, PALETTE[0])
            stroke = PALETTE_STROKE.get(level, PALETTE_STROKE[0])

            tip = (
                f"{count} contributions on {date_str}"
                if count > 0
                else f"No contributions on {date_str}"
            )

            if animated:
                delay = round(BASE_DELAY + col_idx * COL_STEP + weekday * ROW_STEP, 3)
                rect = (
                    f'    <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'rx="{CELL_RX}" fill="{color}" stroke="{stroke}" stroke-width="0.5" '
                    f'class="c-sq c-anim" style="animation-delay: {delay}s;">'
                    f'<title>{tip}</title></rect>'
                )
            else:
                rect = (
                    f'    <rect x="{x}" y="{y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
                    f'rx="{CELL_RX}" fill="{color}" stroke="{stroke}" stroke-width="0.5" '
                    f'class="c-sq"><title>{tip}</title></rect>'
                )
            cells_svg.append(rect)

    # ------------------------------------------------------------------
    # Legend (Less → More)
    # ------------------------------------------------------------------
    legend_rects = []
    for lvl in range(5):
        lx = round(LEGEND_RECT_START + lvl * LEGEND_STEP, 1)
        legend_rects.append(
            f'<rect x="{lx}" y="{LEGEND_RECT_Y}" width="{CELL_SIZE}" height="{CELL_SIZE}" '
            f'rx="{CELL_RX}" fill="{PALETTE[lvl]}" stroke="{PALETTE_STROKE[lvl]}" stroke-width="0.5"/>'
        )
    more_x = round(LEGEND_RECT_START + 5 * LEGEND_STEP, 1)
    legend_svg = (
        f'    <g id="legend">\n'
        f'      <text x="{LEGEND_X}" y="{FOOTER_TEXT_Y}" class="meta-label">Less</text>\n'
        f'      {" ".join(legend_rects)}\n'
        f'      <text x="{more_x}" y="{FOOTER_TEXT_Y}" class="meta-label">More</text>\n'
        f'    </g>'
    )

    # ------------------------------------------------------------------
    # Stats summary in the header
    # ------------------------------------------------------------------
    header_title = "samrit@github ~ $ git log --contributions --last-year"
    stats_summary = (
        f"{total_contributions:,} Contributions  \u2022  "
        f"{active_days} Active Days  \u2022  Streak: {current_streak}d"
    )

    # ------------------------------------------------------------------
    # CSS block
    # ------------------------------------------------------------------
    anim_css = ""
    if animated:
        anim_css = """
    /* Box-by-box diagonal pop-in */
    @keyframes squarePop {
      0%   { opacity: 0; transform: scale(0.2); }
      70%  { opacity: 1; transform: scale(1.15); }
      100% { opacity: 1; transform: scale(1); }
    }
    .c-sq { transform-box: fill-box; transform-origin: center; }
    .c-anim { opacity: 0; animation: squarePop 0.32s cubic-bezier(0.16, 1, 0.3, 1) forwards; }"""
    else:
        anim_css = "\n    .c-sq { }"

    # ------------------------------------------------------------------
    # Assemble SVG
    # ------------------------------------------------------------------
    svg = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {SVG_WIDTH} {SVG_HEIGHT}" width="{SVG_WIDTH}" height="{SVG_HEIGHT}">
  <style>
    .card-bg   {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 8px; }}
    .header-bar {{ fill: #161b22; stroke: #30363d; stroke-width: 1px; }}
    .term-title {{ fill: #8b949e; font-family: ui-monospace, 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 11px; font-weight: 600; }}
    .stats-title {{ fill: #39d353; font-family: ui-monospace, 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 11px; font-weight: 700; }}
    .axis-label {{ fill: #7d8590; font-family: ui-monospace, 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 9px; }}
    .meta-label {{ fill: #7d8590; font-family: ui-monospace, 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 10px; }}
    .brand-link {{ fill: #58a6ff; font-family: ui-monospace, 'SF Mono', Menlo, Monaco, Consolas, monospace; font-size: 10px; }}{anim_css}
  </style>

  <!-- Background Frame -->
  <rect x="1" y="1" width="{SVG_WIDTH - 2}" height="{SVG_HEIGHT - 2}" class="card-bg" />

  <!-- Header -->
  <path d="M 1 8 Q 1 1 8 1 L {SVG_WIDTH - 8} 1 Q {SVG_WIDTH - 1} 1 {SVG_WIDTH - 1} 8 L {SVG_WIDTH - 1} {HEADER_H} L 1 {HEADER_H} Z" class="header-bar" />
  <circle cx="{DOT_MARGIN}" cy="{DOT_CY}" r="{DOT_R}" fill="#ff5f56" />
  <circle cx="{DOT_MARGIN + DOT_STEP}" cy="{DOT_CY}" r="{DOT_R}" fill="#ffbd2e" />
  <circle cx="{DOT_MARGIN + DOT_STEP * 2}" cy="{DOT_CY}" r="{DOT_R}" fill="#27c93f" />
  <text x="{TITLE_X}" y="{TITLE_Y}" class="term-title">{header_title}</text>
  <text x="{SVG_WIDTH - 24}" y="{TITLE_Y}" text-anchor="end" class="stats-title">{stats_summary}</text>

  <!-- Month Labels -->
{chr(10).join(month_labels_svg)}

  <!-- Day Labels -->
{chr(10).join(day_labels_svg)}

  <!-- Heatmap Cells -->
  <g id="heatmap-cells">
{chr(10).join(cells_svg)}
  </g>

  <!-- Footer: timestamp + legend -->
  <text x="{START_X}" y="{FOOTER_TEXT_Y}" class="meta-label">Data synced from <tspan class="brand-link">github.com/samritmukherjee</tspan> (Updated {updated_at})</text>
{legend_svg}
</svg>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8", newline="\n") as f:
        f.write(svg)
    kind = "animated" if animated else "static"
    print(f"Heatmap SVG written: {output_path}  [{kind}, {SVG_WIDTH}x{SVG_HEIGHT}px]")


def main():
    parser = argparse.ArgumentParser(description="Render GitHub contribution heatmap SVG")
    parser.add_argument("--static", action="store_true", help="Generate static SVG (no animation)")
    parser.add_argument("--both", action="store_true", help="Generate both animated and static SVGs")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    data_file = root / "data" / "contributions.json"

    if not data_file.exists():
        print(f"Data file not found at {data_file} — running fetch first...")
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
