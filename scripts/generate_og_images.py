#!/usr/bin/env python3
"""Generate 1200x630 OG social preview images for every QubitLogic post.

Requires: Pillow  (pip install Pillow)
Output:   static/images/og/<slug>.png
Run:      python scripts/generate_og_images.py
"""

from __future__ import annotations
import re, textwrap
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT    = Path(__file__).resolve().parent.parent
CONTENT = ROOT / "content"
OUTPUT  = ROOT / "static" / "images" / "og"

W, H = 1200, 630

SKIP_FILES = {
    "privacy.md", "affiliate-disclosure.md",
    "newsletter.md", "search.md",
}

HOME_OG = {
    "slug": "home",
    "title": "QubitLogic",
    "description": "Quantum-AI tutorials, Qiskit guides, and Python infrastructure — code-first, benchmarked, self-hosted.",
    "label": "Home",
    "accent": (0, 232, 122),
    "bg": (12, 12, 15),
}

SECTIONS = {
    "infrastructure":    {"accent": (0, 232, 122),   "bg": (10, 14, 16),  "label": "Infrastructure"},
    "quantum-coding":    {"accent": (167, 139, 250),  "bg": (13, 11, 20),  "label": "Quantum Coding"},
    "professional-edge": {"accent": (56, 189, 248),   "bg": (10, 14, 18),  "label": "Professional Edge"},
    "root":              {"accent": (0, 232, 122),    "bg": (12, 12, 15),  "label": "QubitLogic"},
}

FONT_CANDIDATES = [
    ("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf", "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
    ("C:/Windows/Fonts/arialbd.ttf", "C:/Windows/Fonts/arial.ttf"),
]

def parse_front_matter(path: Path) -> dict:
    text = path.read_text(encoding="utf-8", errors="replace")
    m = re.match(r"^---\n(.*?)\n---", text, re.DOTALL)
    if not m:
        return {}
    fm: dict = {}
    for line in m.group(1).splitlines():
        kv = line.split(":", 1)
        if len(kv) == 2:
            fm[kv[0].strip()] = kv[1].strip().strip('"\'')
    return fm

def section_info(path: Path) -> dict:
    parts = path.relative_to(CONTENT).parts
    key = parts[0] if len(parts) > 1 else "root"
    return SECTIONS.get(key, SECTIONS["root"])

def add_radial_glow(img: Image.Image, cx: int, cy: int, radius: int, color: tuple, strength: float = 0.18) -> None:
    """Draw a soft radial glow onto the image (RGBA compositing)."""
    glow = Image.new("RGBA", img.size, (0, 0, 0, 0))
    draw = ImageDraw.Draw(glow)
    for r in range(radius, 0, -4):
        alpha = int(strength * 255 * (1 - r / radius) ** 1.5)
        draw.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(*color, alpha))
    img.alpha_composite(glow)

def output_slug(path: Path) -> str:
    if path.name == "_index.md":
        return path.parent.name
    return path.stem


def load_fonts() -> tuple:
    for bold, normal in FONT_CANDIDATES:
        try:
            return (
                ImageFont.truetype(bold, 28),
                ImageFont.truetype(normal, 26),
                ImageFont.truetype(bold, 68),
                ImageFont.truetype(normal, 32),
            )
        except OSError:
            continue
    default = ImageFont.load_default()
    return default, default, default, default


def render_og(
    *,
    slug: str,
    title: str,
    desc: str,
    label: str,
    accent: tuple[int, int, int],
    bg: tuple[int, int, int],
) -> Path:

    # ── Canvas ────────────────────────────────────────────────────────────────
    img = Image.new("RGBA", (W, H), (*bg, 255))
    draw = ImageDraw.Draw(img)

    # Background gradient: slightly lighter towards bottom-right
    for y in range(H):
        t = y / H
        r = int(bg[0] + t * 8)
        g = int(bg[1] + t * 6)
        b = int(bg[2] + t * 18)
        draw.line([(0, y), (W, y)], fill=(min(r,40), min(g,40), min(b,50), 255))

    # Radial glow top-left
    add_radial_glow(img, W // 4, H // 3, 450, accent, 0.10)

    # ── Left accent bar ────────────────────────────────────────────────────────
    draw = ImageDraw.Draw(img)
    bar_w = 8
    draw.rectangle([0, 0, bar_w, H], fill=(*accent, 255))

    fnt_site, fnt_label, fnt_title, fnt_desc = load_fonts()

    pad_l = 72  # left padding (after accent bar)
    pad_r = 72

    # ── Top row: site name + section label ─────────────────────────────────────
    site_text  = "QubitLogic"
    label_text = f"/ {label}"
    draw.text((pad_l, 54), site_text,  font=fnt_site,  fill=(228, 228, 236, 255))
    site_w = draw.textlength(site_text, font=fnt_site)
    draw.text((pad_l + site_w + 12, 57), label_text, font=fnt_label, fill=(*accent, 220))

    # ── Title (wrapped) ────────────────────────────────────────────────────────
    max_chars = 30 if len(title) > 50 else 36
    lines = textwrap.wrap(title, width=max_chars)[:3]
    title_y = 150
    line_h  = 84
    for i, line in enumerate(lines):
        draw.text((pad_l, title_y + i * line_h), line, font=fnt_title, fill=(240, 240, 248, 255))

    # ── Description (one line, truncated) ──────────────────────────────────────
    if desc:
        max_d = 70
        short_desc = desc[:max_d].rsplit(" ", 1)[0] + "…" if len(desc) > max_d else desc
        desc_y = title_y + len(lines) * line_h + 28
        draw.text((pad_l, desc_y), short_desc, font=fnt_desc, fill=(136, 136, 160, 255))

    # ── Bottom rule + URL ─────────────────────────────────────────────────────
    rule_y = H - 80
    draw.rectangle([pad_l, rule_y, W - pad_r, rule_y + 1], fill=(*accent, 60))
    draw.text((pad_l, rule_y + 16), "qubitlogic.dev", font=fnt_label, fill=(*accent, 200))

    OUTPUT.mkdir(parents=True, exist_ok=True)
    out = OUTPUT / f"{slug}.png"
    img.convert("RGB").save(out, "PNG", optimize=True)
    return out


def generate_og(path: Path) -> Path | None:
    fm = parse_front_matter(path)
    title = fm.get("title", "")
    desc = fm.get("description", "")
    if not title:
        return None

    info = section_info(path)
    return render_og(
        slug=output_slug(path),
        title=title,
        desc=desc,
        label=info["label"],
        accent=info["accent"],
        bg=info["bg"],
    )


def generate_home_og() -> Path:
    return render_og(
        slug=HOME_OG["slug"],
        title=HOME_OG["title"],
        desc=HOME_OG["description"],
        label=HOME_OG["label"],
        accent=HOME_OG["accent"],
        bg=HOME_OG["bg"],
    )


def iter_posts() -> list[Path]:
    paths = [
        p for p in sorted(CONTENT.rglob("*.md"))
        if p.name not in SKIP_FILES
        and parse_front_matter(p).get("title")
    ]
    return paths


def main() -> None:
    generated = []
    home = generate_home_og()
    generated.append(("home", home))
    print("  home")

    for p in iter_posts():
        out = generate_og(p)
        if out:
            generated.append((output_slug(p), out))
            print(f"  {output_slug(p)}")
    print(f"\nGenerated {len(generated)} OG images → static/images/og/")


if __name__ == "__main__":
    main()
