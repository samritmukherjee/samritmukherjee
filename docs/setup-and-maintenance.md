# Setup and Maintenance Guide

This document explains the architecture, local generator workflows, and automated maintenance for Samrit Mukherjee's animated GitHub profile README.

---

## 1. Architecture Overview

The profile README uses self-contained, lightweight vector graphics (SVG) with dark terminal aesthetics, custom SMIL progressive animations, and zero external tracking widgets.

```
samritmukherjee/
├── README.md                           # Main profile README
├── .gitignore                          # Protects raw images & temp caches
├── data/
│   └── contributions.json              # Cached verified GitHub contribution stats
├── assets/
│   ├── ascii-portrait.svg              # Animated dense technical ASCII portrait
│   ├── ascii-portrait-static.svg       # Static fallback ASCII portrait
│   ├── info-card.svg                   # Animated Neofetch terminal card
│   ├── info-card-static.svg            # Static fallback Neofetch card
│   ├── contribution-heatmap.svg        # Animated GitHub green contribution heatmap
│   └── contribution-heatmap-static.svg # Static fallback contribution heatmap
├── scripts/
│   ├── requirements.txt                # Minimal Python dependencies (Pillow, requests)
│   ├── prep_photo.py                   # Portrait normalization, crop, contrast & sharpness
│   ├── make_ascii_svg.py               # ASCII luminance mapper & SVG generator
│   ├── make_info_card.py               # Terminal Neofetch card generator
│   ├── fetch_contributions.py          # Public GitHub contribution calendar scraper
│   └── render_heatmap_svg.py           # Heatmap SVG renderer
├── docs/
│   └── setup-and-maintenance.md        # Architecture & maintenance guide (this file)
└── .github/
    └── workflows/
        └── update-profile-art.yml      # Scheduled daily update workflow
```

---

## 2. Local Setup & Execution

### Prerequisites
- Python 3.10+
- Virtual environment (recommended)

### Install Dependencies
```bash
pip install -r scripts/requirements.txt
```

### Running Individual Generators

#### 1. Preprocess Portrait
Crops transparent padding, centers on bust, and optimizes contrast and sharpness:
```bash
python scripts/prep_photo.py
```

#### 2. Generate ASCII Portrait SVG
Generates both animated and static versions:
```bash
python scripts/make_ascii_svg.py --both
```
*Options:*
- `--static`: Generate only static SVG
- `--cols 68`: Adjust ASCII character columns (default: 68)
- `--rows 52`: Adjust ASCII character rows (default: 52)

#### 3. Generate Neofetch Terminal Info Card
Generates both animated and static versions:
```bash
python scripts/make_info_card.py --both
```
*Options:*
- `--static`: Generate only static SVG

#### 4. Fetch Contributions
Fetches public GitHub contribution data from `https://github.com/users/samritmukherjee/contributions`, calculates streaks and active days, and saves to `data/contributions.json`:
```bash
python scripts/fetch_contributions.py
```

#### 5. Render Contribution Heatmap SVG
Renders the contribution heatmap from `data/contributions.json`:
```bash
python scripts/render_heatmap_svg.py --both
```

---

## 3. GitHub Actions Automated Updates

### Workflow: `.github/workflows/update-profile-art.yml`
- **Schedule**: Automatically runs daily at 00:00 UTC.
- **Manual Trigger**: Supports `workflow_dispatch` button under the GitHub Actions tab.
- **Recursion Prevention**: Commits using `[skip ci]` to avoid re-triggering workflows.
- **Commit Guard**: Only commits when `data/contributions.json` or generated SVGs have changed.

### Required Repository Settings
To allow the GitHub Actions bot to commit updated SVGs and contribution data:
1. Go to your GitHub repository: `https://github.com/samritmukherjee/samritmukherjee`
2. Navigate to **Settings** > **Actions** > **General**.
3. Scroll down to **Workflow permissions**.
4. Select **"Read and write permissions"**.
5. Click **Save**.

---

## 4. Static Fallbacks & Resilience

- **SMIL Fallbacks**: For clients or markdown previewers that do not evaluate SVG SMIL animations, the static versions (`*-static.svg`) display all content at full opacity without animation delays.
- **Offline / Failure Resilience**: If GitHub rate limits or network requests fail, `scripts/fetch_contributions.py` falls back to the existing cached `data/contributions.json` without breaking the build or fabricating contribution counts.
- **Privacy**: The raw source image `assets/source-photo.png` is included in `.gitignore` so personal high-resolution uncompressed files are not committed to git history unnecessarily.
