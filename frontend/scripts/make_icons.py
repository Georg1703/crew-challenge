#!/usr/bin/env python3
"""Generate the app icons in public/icons/ (three circles = a crew).

Edit ACCENT/FOREGROUND or the drawing below and run
    python3 scripts/make_icons.py
Needs Pillow (pip install pillow). Keep ACCENT in sync with --palette-clay-500 in tokens.css.
"""

from pathlib import Path

from PIL import Image, ImageDraw

ACCENT = (194, 81, 55)  # --palette-clay-500 (#c25137)
FOREGROUND = (255, 255, 255)
OUT = Path(__file__).resolve().parent.parent / "public" / "icons"


def draw(size: int, *, padding: float, rounded: bool) -> Image.Image:
    scale = 4  # draw large, then downsample for smooth edges
    big = size * scale
    image = Image.new("RGBA", (big, big), (0, 0, 0, 0))
    pen = ImageDraw.Draw(image)
    if rounded:
        pen.rounded_rectangle((0, 0, big - 1, big - 1), radius=int(big * 0.22), fill=ACCENT)
    else:
        pen.rectangle((0, 0, big, big), fill=ACCENT)
    inner = big * (1 - 2 * padding)
    radius = inner * 0.19
    cx, cy = big / 2, big / 2 + inner * 0.03
    spread = inner * 0.24
    for dx, dy in ((0, -spread), (-spread * 0.95, spread * 0.6), (spread * 0.95, spread * 0.6)):
        x, y = cx + dx, cy + dy
        pen.ellipse((x - radius, y - radius, x + radius, y + radius), fill=FOREGROUND)
    return image.resize((size, size), Image.LANCZOS)


def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    draw(192, padding=0.14, rounded=False).save(OUT / "icon-192.png")
    draw(512, padding=0.14, rounded=False).save(OUT / "icon-512.png")
    # Maskable: content inside the central 80% safe zone; the OS applies its own mask.
    draw(512, padding=0.22, rounded=False).save(OUT / "icon-maskable-512.png")
    # iOS adds its own rounded corners; no transparency allowed.
    draw(180, padding=0.14, rounded=False).convert("RGB").save(OUT / "apple-touch-icon.png")
    draw(64, padding=0.08, rounded=True).save(OUT / "favicon-64.png")
    print(f"Wrote icons to {OUT}")


if __name__ == "__main__":
    main()
