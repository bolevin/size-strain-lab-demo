"""Draw the application icon: a Williamson-Hall plot on an accent tile.

    python tools/make_icon.py

Writes ``icon.png`` (256 px) and a multi-size ``icon.ico`` into the package data.
"""

from __future__ import annotations

from pathlib import Path

from PIL import Image, ImageDraw

OUT = Path(__file__).resolve().parents[1] / "src" / "sizeout_demo" / "data"
SIZE = 1024  # drawn large, downsampled for smooth edges
TOP, BOTTOM = (0, 138, 160), (0, 78, 112)  # accent gradient
WHITE = (255, 255, 255, 255)


def main() -> None:
    tile = Image.new("RGBA", (SIZE, SIZE))
    for y in range(SIZE):
        t = y / (SIZE - 1)
        colour = tuple(round(a + (b - a) * t) for a, b in zip(TOP, BOTTOM, strict=True))
        ImageDraw.Draw(tile).line([(0, y), (SIZE, y)], fill=(*colour, 255))
    mask = Image.new("L", (SIZE, SIZE), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, SIZE - 1, SIZE - 1], radius=220, fill=255)
    icon = Image.new("RGBA", (SIZE, SIZE), (0, 0, 0, 0))
    icon.paste(tile, (0, 0), mask)

    draw = ImageDraw.Draw(icon)
    left, right, bottom, top = 170, SIZE - 150, 830, 190
    draw.line(
        [(left, top), (left, bottom), (right, bottom)],
        fill=(255, 255, 255, 140),
        width=24,
        joint="curve",
    )

    def line_y(x: float) -> float:  # the fitted line: intercept and slope
        return 640 - 0.52 * (x - left)

    draw.line([(left, line_y(left)), (right, line_y(right))], fill=WHITE, width=34)
    for x, dy in ((285, 34), (425, -40), (560, 26), (700, -30), (830, 18)):
        y = line_y(x) + dy
        draw.ellipse([x - 50, y - 50, x + 50, y + 50], fill=WHITE)

    OUT.mkdir(parents=True, exist_ok=True)
    icon.resize((256, 256), Image.LANCZOS).save(OUT / "icon.png")
    icon.save(OUT / "icon.ico", sizes=[(s, s) for s in (16, 24, 32, 48, 64, 128, 256)])
    print(f"wrote {OUT / 'icon.png'} and icon.ico")


if __name__ == "__main__":
    main()
