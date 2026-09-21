"""
Generates an animated Neofetch-style terminal info card SVG and a static fallback.
Displays user identity, education, focus, skills, achievements, links, and terminal palette.
"""

import sys
import argparse
from pathlib import Path


def generate_info_card_svg(
    output_path: Path,
    animated: bool = True,
    width: int = 540,
    height: int = 626,
):
    """Generate a sleek, dark-terminal Neofetch SVG card."""
    # Data fields
    fields = [
        ("Identity", "samrit@github", "#58a6ff"),
        ("Separator", "--------------------------------------", "#30363d"),
        ("Education", "B.Tech CSE (AI & ML)", "#e6edf3"),
        ("Institute", "Meghnad Saha Inst. of Technology", "#8b949e"),
        ("Focus", "AI/ML, Full-Stack, Agentic AI", "#39d353"),
        ("Languages", "Python, TypeScript, JavaScript, C/C++, Java", "#e6edf3"),
        ("Frameworks", "Next.js, Flask, React, HTML5/CSS3", "#e6edf3"),
        ("AI & Data", "LangChain, LangGraph, Hugging Face, Gemini", "#d2a8ff"),
        ("Libraries", "NumPy, Pandas, FAISS", "#8b949e"),
        ("Cloud & Ops", "Docker, AWS, Vercel, Firebase, MongoDB", "#79c0ff"),
        ("Achievements", "11 Hackathon Wins", "#ffbd2e"),
        ("Global Rank", "Top 106: Google Solution Challenge 2026", "#e3b341"),
        ("Portfolio", "https://samrit.dev/", "#58a6ff"),
        ("LinkedIn", "in/samrit-mukherjee", "#58a6ff"),
    ]

    # Logo ASCII art (Cyber / Terminal Brain emblem)
    emblem_lines = [
        "      .---.      ",
        "     /     \\     ",
        "    | () () |    ",
        "     \\  ^  /     ",
        "      |||||      ",
        "      '---'      ",
        "   [AI ENGINEER] ",
    ]

    # Staggered animations
    content_elements = []
    base_delay = 0.2
    step_delay = 0.12

    # Prompt line
    prompt_anim = ""
    if animated:
        prompt_anim = (
            f'<animate attributeName="opacity" from="0" to="1" dur="0.2s" begin="{base_delay}s" fill="freeze"/>'
        )
    content_elements.append(
        f'    <text x="28" y="70" class="prompt" opacity="{"0" if animated else "1"}">'
        f'<tspan fill="#39d353">samrit@github</tspan><tspan fill="#8b949e">:</tspan>'
        f'<tspan fill="#58a6ff">~</tspan><tspan fill="#8b949e">$ </tspan>'
        f'<tspan fill="#e6edf3">neofetch --profile</tspan>{prompt_anim}</text>'
    )

    curr_delay = base_delay + 0.25

    # Emblem on the left
    emblem_start_y = 112
    for idx, eline in enumerate(emblem_lines):
        line_y = emblem_start_y + idx * 18
        anim_frag = ""
        if animated:
            anim_frag = (
                f'<animate attributeName="opacity" from="0" to="1" dur="0.2s" begin="{curr_delay:.2f}s" fill="freeze"/>'
            )
        color = "#39d353" if "AI" in eline else "#58a6ff"
        content_elements.append(
            f'    <text x="28" y="{line_y}" class="emblem" fill="{color}" opacity="{"0" if animated else "1"}">'
            f'{eline}{anim_frag}</text>'
        )
        curr_delay += 0.05

    # Details on the right side
    details_x = 188
    details_start_y = 108

    def xml_esc(s: str) -> str:
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', "&quot;")

    for idx, (label, val, val_color) in enumerate(fields):
        y_pos = details_start_y + idx * 24
        curr_delay += step_delay

        anim_frag = ""
        if animated:
            anim_frag = (
                f'<animate attributeName="opacity" from="0" to="1" dur="0.2s" begin="{curr_delay:.2f}s" fill="freeze"/>'
                f'<animate attributeName="transform" type="translate" values="5,0; 0,0" dur="0.2s" begin="{curr_delay:.2f}s" fill="freeze"/>'
            )

        safe_val = xml_esc(val)
        safe_label = xml_esc(label)

        if label == "Identity":
            line_str = (
                f'    <text x="{details_x}" y="{y_pos}" class="val" opacity="{"0" if animated else "1"}">'
                f'<tspan fill="#39d353" font-weight="700">samrit</tspan>'
                f'<tspan fill="#8b949e">@</tspan>'
                f'<tspan fill="#58a6ff" font-weight="700">github</tspan>{anim_frag}</text>'
            )
        elif label == "Separator":
            line_str = (
                f'    <text x="{details_x}" y="{y_pos}" class="sep" fill="#30363d" opacity="{"0" if animated else "1"}">'
                f'{safe_val}{anim_frag}</text>'
            )
        else:
            line_str = (
                f'    <text x="{details_x}" y="{y_pos}" class="meta" opacity="{"0" if animated else "1"}">'
                f'<tspan fill="#79c0ff" font-weight="600">{safe_label:12s}</tspan>'
                f'<tspan fill="#6e7681">: </tspan>'
                f'<tspan fill="{val_color}">{safe_val}</tspan>{anim_frag}</text>'
            )
        content_elements.append(line_str)


    # Palette blocks
    palette_y = height - 96
    curr_delay += 0.3
    pal_anim = ""
    if animated:
        pal_anim = (
            f'<animate attributeName="opacity" from="0" to="1" dur="0.3s" begin="{curr_delay:.2f}s" fill="freeze"/>'
        )

    dark_colors = ["#0d1117", "#f85149", "#3fb950", "#d29922", "#58a6ff", "#bc8cff", "#39c5cf", "#b1bac4"]
    bright_colors = ["#484f58", "#ff7b72", "#56d364", "#e3b341", "#79c0ff", "#d2a8ff", "#56d4dd", "#ffffff"]

    palette_rects = []
    sq_size = 20
    sq_gap = 6
    pal_start_x = 28

    for i, (c_dark, c_bright) in enumerate(zip(dark_colors, bright_colors)):
        x = pal_start_x + i * (sq_size + sq_gap)
        palette_rects.append(f'      <rect x="{x}" y="{palette_y}" width="{sq_size}" height="{sq_size}" rx="4" fill="{c_dark}"/>')
        palette_rects.append(f'      <rect x="{x}" y="{palette_y + sq_size + 4}" width="{sq_size}" height="{sq_size}" rx="4" fill="{c_bright}"/>')

    palette_block = (
        f'    <!-- Terminal Palette Blocks -->\n'
        f'    <g id="palette-blocks" opacity="{"0" if animated else "1"}">\n'
        + "\n".join(palette_rects)
        + f'\n      {pal_anim}\n    </g>'
    )
    content_elements.append(palette_block)

    # Footer prompt line with blinking cursor
    footer_y = height - 28
    cursor_svg = ""
    if animated:
        cursor_svg = (
            f'<rect x="206" y="{footer_y - 12}" width="8" height="15" fill="#39d353">'
            f'<animate attributeName="opacity" values="1;0;1" dur="1s" repeatCount="indefinite" begin="{curr_delay:.2f}s"/>'
            f'</rect>'
        )
    else:
        cursor_svg = f'<rect x="206" y="{footer_y - 12}" width="8" height="15" fill="#39d353"/>'

    footer_str = (
        f'    <text x="28" y="{footer_y}" class="prompt">'
        f'<tspan fill="#39d353">samrit@github</tspan><tspan fill="#8b949e">:</tspan>'
        f'<tspan fill="#58a6ff">~</tspan><tspan fill="#8b949e">$ </tspan>'
        f'<tspan fill="#8b949e">status: </tspan><tspan fill="#39d353">online</tspan>'
        f'</text>\n    {cursor_svg}'
    )
    content_elements.append(footer_str)

    body_svg = "\n".join(content_elements)

    svg_content = f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width} {height}" width="{width}" height="{height}">
  <defs>
    <filter id="windowGlow" x="-5%" y="-5%" width="110%" height="110%">
      <feDropShadow dx="0" dy="8" stdDeviation="12" flood-color="#000000" flood-opacity="0.5"/>
    </filter>
  </defs>

  <style>
    .window-bg {{ fill: #0d1117; stroke: #30363d; stroke-width: 1px; rx: 10px; }}
    .title-bar {{ fill: #161b22; stroke: #30363d; stroke-width: 1px; }}
    .title-text {{ fill: #8b949e; font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; font-weight: 600; }}
    .prompt {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 12px; font-weight: 500; }}
    .emblem {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; font-weight: 700; }}
    .meta {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; }}
    .val {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 13px; }}
    .sep {{ font-family: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, monospace; font-size: 11px; }}
  </style>

  <!-- Terminal Window Background -->
  <rect x="1" y="1" width="{width - 2}" height="{height - 2}" class="window-bg" filter="url(#windowGlow)" />

  <!-- Terminal Window Header -->
  <path d="M 1 10 Q 1 1 10 1 L {width - 10} 1 Q {width - 1} 1 {width - 1} 10 L {width - 1} 36 L 1 36 Z" class="title-bar" />

  <!-- Window Controls -->
  <circle cx="20" cy="18" r="5" fill="#ff5f56" />
  <circle cx="36" cy="18" r="5" fill="#ffbd2e" />
  <circle cx="52" cy="18" r="5" fill="#27c93f" />

  <!-- Window Title -->
  <text x="{width // 2}" y="22" text-anchor="middle" class="title-text">samrit@github: ~/neofetch</text>

  <!-- Terminal Body Content -->
{body_svg}
</svg>"""

    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(svg_content)
    print(f"Info card generated: {output_path} ({'animated' if animated else 'static'})")


def main():
    parser = argparse.ArgumentParser(description="Generate Neofetch terminal info card SVG")
    parser.add_argument("--static", action="store_true", help="Generate static SVG without animations")
    parser.add_argument("--both", action="store_true", help="Generate both animated and static SVGs")
    args = parser.parse_args()

    root = Path(__file__).resolve().parent.parent
    anim_out = root / "assets" / "info-card.svg"
    static_out = root / "assets" / "info-card-static.svg"

    if args.both:
        generate_info_card_svg(anim_out, animated=True)
        generate_info_card_svg(static_out, animated=False)
    elif args.static:
        generate_info_card_svg(static_out, animated=False)
    else:
        generate_info_card_svg(anim_out, animated=True)


if __name__ == "__main__":
    main()
