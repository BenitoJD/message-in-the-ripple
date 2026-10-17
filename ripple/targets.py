"""Target glyphs for the caustic reveal.

A target is an N x N array in [0, 1]: 1 where the screen should be bright.
Two modes:

* "ink"     — the glyph's strokes themselves (works for text and symbols)
* "outline" — edges of the filled glyph (bright closed curves; matches the
              physics of caustics, which like to form *lines* at fold
              singularities)

Glyphs are rasterized with matplotlib's bundled DejaVu font, so arbitrary
text/symbols work without system fonts. Everything degrades gracefully: if
matplotlib cannot render a glyph, use `heart_target` (pure numpy).
"""

from __future__ import annotations

import numpy as np


def bitmap_from_text(s: str, N: int = 192, fontsize: float = 260) -> np.ndarray:
    """Rasterize a string/symbol to an N x N ink bitmap in [0, 1]."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig = plt.figure(figsize=(4, 4), dpi=110)
    fig.patch.set_facecolor("white")
    fig.text(0.5, 0.5, s, ha="center", va="center", fontsize=fontsize, color="black")
    fig.canvas.draw()
    buf = np.asarray(fig.canvas.buffer_rgba())[..., :3].mean(axis=-1)
    plt.close(fig)

    ink = buf < 200  # True where drawn
    if not ink.any():
        raise ValueError(f"nothing rendered for {s!r} (font lacks this glyph?)")
    ys, xs = np.where(ink)
    y0, y1 = ys.min(), ys.max() + 1
    x0, x1 = xs.min(), xs.max() + 1
    crop = buf[y0:y1, x0:x1]
    # pad to square
    h, w = crop.shape
    m = max(h, w)
    canvas = np.full((m, m), 255.0)
    canvas[(m - h) // 2 : (m - h) // 2 + h, (m - w) // 2 : (m - w) // 2 + w] = crop
    # resize with PIL (box filter keeps strokes soft but legible)
    from PIL import Image

    small = Image.fromarray(canvas.astype(np.uint8)).resize((N, N), Image.BILINEAR)
    t = 1.0 - np.asarray(small, dtype=np.float64) / 255.0
    return np.clip(t, 0.0, 1.0)


def outline_from_bitmap(t: np.ndarray, sigma_px: float = 2.0) -> np.ndarray:
    """Edge map of a bitmap, normalized to [0, 1]."""
    from PIL import Image, ImageFilter

    img = Image.fromarray((t * 255).astype(np.uint8))
    e = img.filter(ImageFilter.FIND_EDGES).filter(ImageFilter.GaussianBlur(sigma_px))
    e = np.asarray(e, dtype=np.float64) / 255.0
    m = e.max()
    return e / m if m > 0 else e


def heart_target(N: int = 192) -> np.ndarray:
    """Filled heart outline (parametric), pure numpy fallback."""
    u = np.linspace(0.0, 2 * np.pi, 2048)
    hx = 16 * np.sin(u) ** 3
    hy = 13 * np.cos(u) - 5 * np.cos(2 * u) - 2 * np.cos(3 * u) - np.cos(4 * u)
    x = (np.arange(N)[:, None] + 0.5) / N * 36 - 18  # columns
    y = 18 - (np.arange(N)[:, None] + 0.5) / N * 36  # rows
    px = np.interp(hx, (hx.min(), hx.max()), (-16, 16))
    py = np.interp(hy, (hy.min(), hy.max()), (-16, 16))
    pts = np.stack([px, py], -1)
    dmin = np.full((N, N), 1e9)
    for k in range(len(pts)):  # distance to each polygon vertex (cheap enough)
        d = np.hypot(x - pts[k, 0], y - pts[k, 1])
        dmin = np.minimum(dmin, d)
    t = np.exp(-(dmin**2) / (2 * 0.45**2))
    return t / t.max()


def glyph_target(symbol: str = "♥", N: int = 192, mode: str = "ink", blur_sigma: float = 2.5) -> np.ndarray:
    """Target screen pattern for a symbol, lightly blurred (a tolerance the
    physics can actually hit; razor-sharp targets are unreachable optically)."""
    try:
        t = bitmap_from_text(symbol, N=N)
    except Exception:
        t = heart_target(N)
    if mode == "outline":
        t = outline_from_bitmap(t)
    from PIL import Image, ImageFilter

    img = Image.fromarray((t * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur_sigma))
    out = np.asarray(img, dtype=np.float64) / 255.0
    out -= out.min()
    m = out.max()
    return out / m if m > 0 else out
