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


def flower_target(
    N: int = 192,
    petals: int = 6,
    petal_len: float = 0.86,
    petal_wid: float = 0.30,
    center_r: float = 0.20,
    blur_sigma: float = 2.0,
) -> np.ndarray:
    """A flower silhouette from overlapping elliptical petals (radius 1 field).

    Drawn parametrically rather than with a font so it works anywhere and the
    petal count/size is a knob: more petals means finer features, which the
    wave field has to resolve, so it is a direct difficulty control.
    """
    x = (np.arange(N)[None, :] + 0.5) / N * 2.0 - 1.0  # columns, -1..1
    y = 1.0 - (np.arange(N)[:, None] + 0.5) / N * 2.0  # rows, -1..1
    m = np.zeros((N, N), dtype=np.float64)
    d = petal_len / 2.0  # petal centre distance from the middle
    for k in range(petals):
        th = 2.0 * np.pi * k / petals
        u = x * np.cos(th) + y * np.sin(th)  # along the petal axis
        v = -x * np.sin(th) + y * np.cos(th)  # across it
        ell = ((u - d) / (petal_len / 2.0)) ** 2 + (v / (petal_wid / 2.0)) ** 2 <= 1.0
        m = np.maximum(m, ell.astype(np.float64))
    m = np.maximum(m, (np.hypot(x, y) <= center_r).astype(np.float64))

    from PIL import Image, ImageFilter

    img = Image.fromarray((m * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(blur_sigma))
    out = np.asarray(img, dtype=np.float64) / 255.0
    m2 = out.max()
    return out / m2 if m2 > 0 else out


def flower_outline_target(N: int = 192, petals: int = 6, **kw) -> np.ndarray:
    """Edge map of `flower_target` — bright petal outlines, which is the shape
    family caustics produce most readily (folds are lines)."""
    blur = kw.pop("blur_sigma", 2.0)
    t = flower_target(N=N, petals=petals, blur_sigma=max(1.0, blur * 0.6), **kw)
    return outline_from_bitmap(t, sigma_px=blur)


def target_from_spec(spec: str, N: int = 192, mode: str = "ink", blur_sigma: float = 2.5) -> np.ndarray:
    """Resolve a target from a short spec string.

    "flower" / "flower8"  -> parametric flower with 8 petals (outline by default)
    anything else         -> glyph rendered from text, as in `glyph_target`
    """
    if spec.startswith("flower"):
        petals = int(spec[6:]) if len(spec) > 6 else 6
        if mode == "outline":
            return flower_outline_target(N=N, petals=petals, blur_sigma=blur_sigma + 1.0)
        return flower_target(N=N, petals=petals, blur_sigma=blur_sigma)
    return glyph_target(spec, N=N, mode=mode, blur_sigma=blur_sigma)
