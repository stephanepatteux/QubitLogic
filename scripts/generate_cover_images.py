#!/usr/bin/env python3
"""Generate branded SVG cover images for QubitLogic blog posts.

Reads Markdown front matter from content/ and writes covers to
static/images/covers/ using a consistent dark-theme style per section.

Run before Hugo build:
    python scripts/generate_cover_images.py
"""

from __future__ import annotations

import re
import textwrap
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUTPUT = ROOT / "static" / "images" / "covers"

SKIP_FILES = {
    "about.md",
    "privacy.md",
    "affiliate-disclosure.md",
    "start-here.md",
    "newsletter.md",
    "search.md",
}

SECTIONS = {
    "infrastructure": {
        "label": "Infrastructure",
        "accent": "#00e87a",
        "secondary": "#38bdf8",
        "bg_end": "#131a22",
    },
    "quantum-coding": {
        "label": "Quantum Coding",
        "accent": "#a78bfa",
        "secondary": "#00e87a",
        "bg_end": "#120f1a",
    },
    "professional-edge": {
        "label": "Professional Edge",
        "accent": "#38bdf8",
        "secondary": "#fbbf24",
        "bg_end": "#0f1418",
    },
}

CATEGORY_COLORS = {
    "tutorial": "#00e87a",
    "benchmark": "#38bdf8",
    "review": "#a78bfa",
    "build": "#fbbf24",
}

FRONT_MATTER_RE = re.compile(r"^---\s*\n(.*?)\n---", re.DOTALL)
TITLE_RE = re.compile(r'^title:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE)
CATEGORIES_RE = re.compile(
    r'^categories:\s*\[(.+?)\]|^categories:\s*["\']?(.+?)["\']?\s*$', re.MULTILINE
)


def parse_front_matter(path: Path) -> dict[str, str]:
    text = path.read_text(encoding="utf-8")
    match = FRONT_MATTER_RE.match(text)
    if not match:
        return {}
    fm = match.group(1)
    title = ""
    if m := TITLE_RE.search(fm):
        title = m.group(1).strip()
    category = ""
    if m := CATEGORIES_RE.search(fm):
        raw = (m.group(1) or m.group(2) or "").strip()
        raw = raw.strip("[]")
        category = raw.split(",")[0].strip().strip('"').strip("'")
    return {"title": title, "category": category}


def cover_output_path(md_path: Path) -> Path:
    rel = md_path.relative_to(CONTENT)
    if rel.parent == Path("."):
        return OUTPUT / f"{rel.stem}.svg"
    return OUTPUT / rel.parent / f"{rel.stem}.svg"


def cover_url_path(md_path: Path) -> str:
    rel = md_path.relative_to(CONTENT)
    if rel.parent == Path("."):
        return f"/images/covers/{rel.stem}.svg"
    return f"/images/covers/{rel.parent.as_posix()}/{rel.stem}.svg"


def wrap_title(title: str, width: int = 30, max_lines: int = 4) -> list[str]:
    clean = re.sub(r"\s+", " ", title).strip()
    lines = textwrap.wrap(clean, width=width, break_long_words=False)
    return lines[:max_lines] if lines else [clean[:width]]


def section_key(md_path: Path) -> str:
    rel = md_path.relative_to(CONTENT)
    if rel.parent != Path("."):
        return rel.parts[0]
    return "build" if "build" in rel.stem else "site"


def section_style(key: str) -> dict[str, str]:
    if key in SECTIONS:
        return SECTIONS[key]
    return {
        "label": "QubitLogic",
        "accent": "#00e87a",
        "secondary": "#38bdf8",
        "bg_end": "#131a22",
    }


def motif_svg(key: str, accent: str, secondary: str) -> str:
    if key == "infrastructure":
        return f"""
  <g stroke="{accent}" stroke-opacity="0.22" stroke-width="1" fill="none">
    <rect x="860" y="90" width="280" height="180" rx="10"/>
    <line x1="900" y1="140" x2="1100" y2="140"/>
    <line x1="940" y1="90" x2="940" y2="270"/>
    <line x1="1020" y1="90" x2="1020" y2="270"/>
    <line x1="1100" y1="90" x2="1100" y2="270"/>
    <path d="M900 220 L980 160 L1060 200 L1140 130"/>
  </g>
  <circle cx="980" cy="160" r="5" fill="{accent}" fill-opacity="0.65"/>
  <circle cx="1140" cy="130" r="5" fill="{secondary}" fill-opacity="0.65"/>"""
    if key == "quantum-coding":
        return f"""
  <g stroke="{accent}" stroke-opacity="0.35" stroke-width="1.5" fill="none">
    <ellipse cx="1000" cy="180" rx="95" ry="34" transform="rotate(-28 1000 180)"/>
    <ellipse cx="1000" cy="180" rx="95" ry="34" transform="rotate(28 1000 180)"/>
    <circle cx="1000" cy="180" r="10" fill="{accent}" fill-opacity="0.75"/>
    <circle cx="905" cy="155" r="6" fill="{secondary}" fill-opacity="0.8"/>
    <circle cx="1095" cy="205" r="6" fill="{secondary}" fill-opacity="0.8"/>
  </g>"""
    if key == "professional-edge":
        return f"""
  <g stroke="{secondary}" stroke-opacity="0.28" stroke-width="1" fill="none">
    <rect x="860" y="100" width="280" height="160" rx="10"/>
    <path d="M900 220 L960 150 L1020 190 L1080 120 L1140 220"/>
    <line x1="900" y1="130" x2="1140" y2="130"/>
  </g>
  <circle cx="960" cy="150" r="5" fill="{accent}" fill-opacity="0.7"/>
  <circle cx="1080" cy="120" r="5" fill="{secondary}" fill-opacity="0.7"/>"""
    return f"""
  <g stroke="{accent}" stroke-opacity="0.25" stroke-width="1.5" fill="none">
    <rect x="880" y="110" width="240" height="150" rx="12"/>
    <path d="M920 200 L980 140 L1040 175 L1100 125"/>
    <circle cx="1000" cy="185" r="28"/>
  </g>
  <circle cx="1000" cy="185" r="6" fill="{accent}" fill-opacity="0.8"/>"""


def escape_xml(text: str) -> str:
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )


def build_svg(title: str, section: dict[str, str], category: str, section_key_name: str) -> str:
    lines = wrap_title(title)
    cat = category or "article"
    cat_color = CATEGORY_COLORS.get(cat, section["accent"])
    cat_label = cat.replace("-", " ").title()

    title_y_start = 300 - (len(lines) - 1) * 28
    title_lines_svg = "\n".join(
        f'  <text x="72" y="{title_y_start + i * 56}" fill="#e4e4ec" '
        f'font-family="Inter, system-ui, sans-serif" font-size="42" '
        f'font-weight="700">{escape_xml(line)}</text>'
        for i, line in enumerate(lines)
    )

    return f"""<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 1200 630" fill="none" role="img" aria-label="{escape_xml(title)}">
  <defs>
    <linearGradient id="bg" x1="0" y1="0" x2="1200" y2="630" gradientUnits="userSpaceOnUse">
      <stop stop-color="#0c0c0f"/>
      <stop offset="1" stop-color="{section['bg_end']}"/>
    </linearGradient>
    <linearGradient id="glow" x1="0" y1="0" x2="900" y2="630" gradientUnits="userSpaceOnUse">
      <stop stop-color="{section['accent']}" stop-opacity="0.14"/>
      <stop offset="1" stop-color="{section['secondary']}" stop-opacity="0.05"/>
    </linearGradient>
  </defs>
  <rect width="1200" height="630" fill="url(#bg)"/>
  <rect width="1200" height="630" fill="url(#glow)"/>
  <rect x="0" y="0" width="8" height="630" fill="{section['accent']}"/>
{motif_svg(section_key_name, section['accent'], section['secondary'])}
  <rect x="72" y="56" width="{len(section['label']) * 9 + 36}" height="34" rx="17" fill="{section['accent']}" fill-opacity="0.12" stroke="{section['accent']}" stroke-opacity="0.35"/>
  <text x="90" y="78" fill="{section['accent']}" font-family="Inter, system-ui, sans-serif" font-size="14" font-weight="600" letter-spacing="0.04em">{escape_xml(section['label'].upper())}</text>
  <rect x="{1080 - len(cat_label) * 8 - 24}" y="56" width="{len(cat_label) * 8 + 24}" height="34" rx="17" fill="{cat_color}" fill-opacity="0.12" stroke="{cat_color}" stroke-opacity="0.4"/>
  <text x="{1092 - len(cat_label) * 8}" y="78" fill="{cat_color}" font-family="Inter, system-ui, sans-serif" font-size="14" font-weight="600">{escape_xml(cat_label)}</text>
{title_lines_svg}
  <text x="72" y="590" fill="#8888a0" font-family="Inter, system-ui, sans-serif" font-size="16" font-weight="500">qubitlogic.dev</text>
  <circle cx="1128" cy="578" r="5" fill="{section['accent']}" fill-opacity="0.8"/>
  <circle cx="1154" cy="578" r="5" fill="{section['secondary']}" fill-opacity="0.55"/>
</svg>
"""


def iter_posts() -> list[Path]:
    posts: list[Path] = []
    for path in sorted(CONTENT.rglob("*.md")):
        if path.name in SKIP_FILES or path.name == "_index.md":
            continue
        meta = parse_front_matter(path)
        if not meta.get("title"):
            continue
        posts.append(path)
    return posts


def main() -> None:
    posts = iter_posts()
    generated = 0
    for md_path in posts:
        meta = parse_front_matter(md_path)
        key = section_key(md_path)
        style = section_style(key)
        svg = build_svg(meta["title"], style, meta.get("category", ""), key)
        out = cover_output_path(md_path)
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(svg, encoding="utf-8", newline="\n")
        generated += 1
        print(f"  {cover_url_path(md_path)}")
    print(f"\nGenerated {generated} cover images in {OUTPUT.relative_to(ROOT)}/")


if __name__ == "__main__":
    main()
