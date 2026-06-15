#!/usr/bin/env python3
"""Generate favicon PNG/ICO assets for QubitLogic.

Requires: Pillow  (pip install Pillow)
Output:   static/favicon*.png, static/favicon.ico, static/apple-touch-icon.png
Run:      python scripts/generate_favicons.py
"""

from __future__ import annotations
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"

ACCENT = (0, 232, 122)
BG = (18, 18, 22)
STROKE = (228, 228, 236)


def draw_logo(size: int) -> Image.Image:
    img = Image.new("RGBA", (size, size), (*BG, 255))
    draw = ImageDraw.Draw(img)
    cx, cy = size // 2, size // 2
    rx = int(size * 0.42)
    ry = int(size * 0.15)
    stroke = max(1, size // 24)

    for angle in (-30, 30):
        bbox = [cx - rx, cy - ry, cx + rx, cy + ry]
        draw.ellipse(bbox, outline=(*STROKE, 255), width=stroke)

    nucleus_r = max(2, size // 14)
    draw.ellipse(
        [cx - nucleus_r, cy - nucleus_r, cx + nucleus_r, cy + nucleus_r],
        fill=(*ACCENT, 255),
    )

    node_r = max(2, size // 20)
    for nx, ny in ((cx - rx + node_r, cy - int(size * 0.08)), (cx + rx - node_r, cy + int(size * 0.08))):
        draw.ellipse(
            [nx - node_r, ny - node_r, nx + node_r, ny + node_r],
            fill=(*ACCENT, 255),
        )
    return img


def save_png(img: Image.Image, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    img.save(path, "PNG", optimize=True)


def save_ico(sizes: list[int]) -> None:
    images = [draw_logo(s) for s in sizes]
    out = STATIC / "favicon.ico"
    images[0].save(
        out,
        format="ICO",
        sizes=[(s, s) for s in sizes],
        append_images=images[1:],
    )


def main() -> None:
    save_png(draw_logo(512), STATIC / "favicon.png")
    save_png(draw_logo(32), STATIC / "favicon-32x32.png")
    save_png(draw_logo(16), STATIC / "favicon-16x16.png")
    save_png(draw_logo(180), STATIC / "apple-touch-icon.png")
    save_ico([16, 32, 48])
    print("Generated favicons → static/favicon*")


if __name__ == "__main__":
    main()
