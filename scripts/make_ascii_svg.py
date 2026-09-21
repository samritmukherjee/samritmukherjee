"""
Generates an animated dense technical ASCII portrait SVG and a static fallback.
Maps pixel luminance to high-contrast ASCII characters and grayscale colors.
"""

import sys
import argparse
from pathlib import Path
from PIL import Image, ImageEnhance
import numpy as np


# Technical ASCII ramp: sparse/dark to dense/bright
RAMP = " .:-=+*#%@"
COLOR_RAMP = [
    "#21262d",  # darkest
    "#30363d",
    "#484f58",
    "#656d76",
    "#8b949e",
    "#a4abb6",
    "#c0c7d0",
    "#d0d7de",
    "#e6edf3",
    "#ffffff",  # brightest
]


def image_to_ascii_grid(img: Image.Image, cols: int = 68, rows: int = 50):
    """Resample image and produce an ASCII grid with character and color info."""
    img_resized = img.resize((cols, rows), Image.Resampling.LANCZOS)
    arr = np.array(img_resized)

    grid = []
    ramp_len = len(RAMP)

    for r in range(rows):
        row_cells = []
        for c in range(cols):
            r_val, g_val, b_val, a_val = arr[r, c]
            if a_val < 45:
                row_cells.append({"char": " ", "color": "#0d1117"})
            else:
                # Perceptual luminance
                lum = 0.299 * r_val + 0.587 * g_val + 0.114 * b_val
                # Normalized 0..1
                norm = min(max(lum / 255.0, 0.0), 1.0)
                # Boost midtones for facial recognizability
                norm = pow(norm, 0.9)
                idx = int(norm * (ramp_len - 1))
                char = RAMP[idx]
                color = COLOR_RAMP[idx]
                row_cells.append({"char": char, "color": color})
        grid.append(row_cells)

    return grid


def generate_ascii_svg(
    grid,
    output_path: Path,
    animated: bool = True,
    title: str = "samrit@github: ~/ascii-portrait",
):
    """Render the ASCII grid into a high-fidelity terminal SVG."""
    rows = len(grid)
    cols = len(grid[0]) if rows > 0 else 0

    char_width = 7.2
    line_height = 10.5
    padding_x = 24
    padding_top = 56
    padding_bottom = 24

    svg_width = int(padding_x * 2 + cols * char_width)
    svg_height = int(padding_top + padding_bottom + rows * line_height)

    lines_svg = []
    total_reveal_time = 1.8  # seconds for full reveal
    line_delay = total_reveal_time / max(rows, 1)

    for r_idx, row in enumerate(grid):
        y_pos = padding_top + r_idx * line_height

        # Group adjacent characters with the same color into tspans
        spans = []
        curr_color = None
        curr_chars = []

        def flush():
            nonlocal curr_color, curr_chars
            if curr_chars and curr_color:
                text_content = "".join(curr_chars).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")
                spans.append(f'<tspan fill="{curr_color}">{text_content}</tspan>')
                curr_chars = []

        for cell in row:
            char = cell["char"]
            color = cell["color"]
            if color != curr_color:
                flush()
                curr_color = color
            curr_chars.append(char)
        flush()

        inner_content = "".join(spans)
        row_anim = ""
        initial_opacity = "1"

        if animated:
            initial_opacity = "0"
            delay = round(r_idx * line_delay, 3)
            row_anim = (
                f'<animate attributeName="opacity" from="0" to="1" dur="0.12s" '
                f'begin="{delay}s" fill="freeze" />'
                f'<animate attributeName="transform" type="translate" values="0,3; 0,0" '
                f'dur="0.12s" begin="{delay}s" fill="freeze" />'
            )

        line_element = (
            f'    <text x="{padding_x}" y="{y_pos:.1f}" font-family="ui-monospace, SFMono-Regular, \'SF Mono\', Menlo, Consolas, \'Liberation Mono\', monospace" '
            f'font-size="9px" xml:space="preserve" opacity="{initial_opacity}">'
            f'{inner_content}{row_anim}</text>'
        )
        lines_svg.append(line_element)

    lines_body = "\n".join(lines_svg)

    # Scanline animation element
    scanline_svg = ""
    if animated:
        scanline_svg = f"""
    <!-- Subtle Scanline reveal beam -->
    <rect x="{padding_x}" y="{padding_top}" width="{cols * char_width:.1f}" height="4" fill="url(#scanlineGrad)" opacity="0.7">
      <animate attributeName="y" from="{padding_top}" to="{padding_top + rows * line_height}" dur="{total_reveal_time}s" fill="freeze" />
      <animate attributeName="opacity" values="0.7;0.8;0" keyTimes="0;0.95;1" dur="{total_reveal_time}s" fill="freeze" />
    </rect>"""

    svg_template = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {svg_width} {svg_height}" width="{svg_width}" height="{svg_height}">
  <defs>
    <linearGradient id="scanlineGrad" x1="0" y1="0" x2="1" y2="0">
      <stop offset="0%" stop-color="#58a6ff" stop-opacity="0"/>
      <stop offset="50%" stop-color="#39d353" stop-opacity="0.9"/>
      <stop offset="100%" stop-color="#58a6ff" stop-opacity="0"/>
    </linearGradient>
    <filter id="cardGlow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.5"/>
    </filter>
  </defs>

  <style>
    .window-bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
    .title-bar {{ fill: #161b22; stroke: #30363d; stroke-width: 1px; }}
    .title-text {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; font-weight: 600; }}
    .status-dot {{ fill: #39d353; }}
  </style>

  <!-- Terminal Window -->
  <rect x="1" y="1" width="{svg_width - 2}" height="{svg_height - 2}" class="window-bg" filter="url(#cardGlow)" />

  <!-- Terminal Window Header -->
  <path d="M 1 10 Q 1 1 10 1 L {svg_width - 10} 1 Q {svg_width - 1} 1 {svg_width - 1} 10 L {svg_width - 1} 36 L 1 36 Z" class="title-bar" />

  <!-- macOS / Linux Window Controls -->
  <circle cx="20" cy="18" r="5" fill="#ff5f56" />
  <circle cx="36" cy="18" r="5" fill="#ffbd2e" />
  <circle cx="52" cy="18" r="5" fill="#27c93f" />

  <!-- Header Title -->
  <text x="{svg_width // 2}" y="22" text-anchor="middle" class="title-text">{title}</text>

  <!-- Online indicator -->
  <circle cx="{svg_width - 24}" cy="18" r="3.5" class="status-dot">
    {'<animate attributeName="opacity" values="1;0.4;1" dur="2s" repeatCount="indefinite"/>' if animated else ''}
  </circle>

  <!-- ASCII Lines Container -->
  <g id="ascii-lines">
{lines_body}
  </g>
{scanline_svg}
</svg>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_template)
    print(f"ASCII SVG generated: {output_path} ({'animated' if animated else 'static'})")


def main():
    parser = argparse.ArgumentParser(description="Generate ASCII portrait SVG")
    parser.add_argument("--cols", type=int, default=68, help="Number of ASCII columns")
    parser.add_argument("--rows", type=int, default=52, help="Number of ASCII rows")
    parser.add_argument("--static", action="store_true", help="Generate static SVG without animations")
    parser.add_argument("--both", action="store_true", help="Generate both animated and static SVGs")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    source_photo = root / "assets" / "source-photo.png"
    prepped_photo = root / "assets" / "prepped-photo.png"

    # Use prepped photo if exists, else preprocess
    if prepped_photo.exists():
        img = Image.open(prepped_photo).convert("RGBA")
    elif source_photo.exists():
        from prep_photo import preprocess_portrait
        img = preprocess_portrait(source_photo, prepped_photo)
    else:
        print(f"Error: {source_photo} not found.", file=sys.stderr)
        sys.exit(1)

    grid = image_to_ascii_grid(img, cols=args.cols, rows=args.rows)

    anim_out = root / "assets" / "ascii-portrait.svg"
    static_out = root / "assets" / "ascii-portrait-static.svg"

    if args.both:
        generate_ascii_svg(grid, anim_out, animated=True)
        generate_ascii_svg(grid, static_out, animated=False)
    elif args.static:
        generate_ascii_svg(grid, static_out, animated=False)
    else:
        generate_ascii_svg(grid, anim_out, animated=True)


if __name__ == "__main__":
    main()
