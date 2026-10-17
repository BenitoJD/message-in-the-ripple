"""Output helpers: image grids, GIFs, metric plots. Pure PIL + matplotlib,
no optional dependencies."""

from __future__ import annotations

import numpy as np
from PIL import Image


def relative(img: np.ndarray, dev: float = 0.25) -> np.ndarray:
    """Display transform for caustic images: show the deviation from the mean
    intensity inside a *fixed* +/- dev window, centred on 0.5.

    Use this instead of per-frame min-max normalization. Min-max stretching is
    how a 0.5% ripple comes to look like a brilliant image — it hides the very
    quantity (contrast) that decides whether a screen would show anything at
    all. Pass vmin=0.0, vmax=1.0 to the save helpers so the result is not
    re-stretched.
    """
    a = np.asarray(img, dtype=np.float64)
    m = a.mean()
    if abs(m) < 1e-30:
        return np.full_like(a, 0.5)
    return (a / m - 1.0) / (2.0 * dev) + 0.5


def to_u8(arr: np.ndarray, vmin=None, vmax=None) -> np.ndarray:
    a = np.asarray(arr, dtype=np.float64)
    if vmin is None:
        vmin = a.min()
    if vmax is None:
        vmax = a.max()
    if vmax - vmin < 1e-30:
        vmax = vmin + 1e-30
    return np.clip((a - vmin) / (vmax - vmin) * 255.0, 0, 255).astype(np.uint8)


def save_gray(arr: np.ndarray, path: str, upscale: int = 2, vmin=None, vmax=None) -> None:
    u = to_u8(arr, vmin, vmax)
    if upscale > 1:
        u = np.asarray(Image.fromarray(u).resize((u.shape[1] * upscale, u.shape[0] * upscale), Image.LANCZOS))
    Image.fromarray(u).save(path)


def tint(arr: np.ndarray, rgb=(255, 226, 160), upscale: int = 2, vmin=None, vmax=None) -> np.ndarray:
    u = to_u8(arr, vmin, vmax)
    rgbarr = np.asarray(rgb, dtype=np.float64) / 255.0
    img = (u[..., None] / 255.0 * rgbarr[None, None, :] * 255.0).astype(np.uint8)
    if upscale > 1:
        img = np.asarray(
            Image.fromarray(img).resize((img.shape[1] * upscale, img.shape[0] * upscale), Image.LANCZOS)
        )
    return img


def save_grid(
    items,
    path: str,
    ncols: int = 6,
    upscale: int = 2,
    labels=None,
    rgb=(255, 226, 160),
    pad: int = 4,
    vmin=None,
    vmax=None,
):
    """items: list of 2-D arrays (same shape). Saves an annotated contact sheet.

    Pass vmin/vmax to share one intensity scale across panels (needed when the
    point is to compare brightness between frames, e.g. a dissolve).
    """
    from PIL import ImageDraw

    n = len(items)
    nrows = (n + ncols - 1) // ncols
    h, w = items[0].shape
    cell_w, cell_h = w * upscale, h * upscale
    label_h = 18 if labels is not None else 0
    sheet = np.full((nrows * (cell_h + label_h + pad) + pad, ncols * (cell_w + pad) + pad, 3), 18, dtype=np.uint8)
    for i, arr in enumerate(items):
        r, c = divmod(i, ncols)
        img = tint(arr, rgb=rgb, upscale=upscale, vmin=vmin, vmax=vmax)
        y = pad + r * (cell_h + label_h + pad)
        x = pad + c * (cell_w + pad)
        sheet[y : y + cell_h, x : x + cell_w] = img
    pil = Image.fromarray(sheet)
    if labels is not None:
        d = ImageDraw.Draw(pil)
        for i, lab in enumerate(labels):
            r, c = divmod(i, ncols)
            y = pad + r * (cell_h + label_h + pad) + cell_h + 1
            x = pad + c * (cell_w + pad) + 4
            d.text((x, y), str(lab), fill=(205, 205, 205))
    pil.save(path)


def save_gif(
    frames,
    path: str,
    fps: float = 14,
    upscale: int = 2,
    rgb=(255, 226, 160),
    loop_extra_pass=True,
    vmin=None,
    vmax=None,
    colors: int = 64,
):
    """frames: list of 2-D arrays (screen intensities). Shared vmin/vmax keeps
    the dissolve honest — garbage frames must not be brightened into shape.

    loop_extra_pass: play the whole sequence twice so the *repeatability*
    claim (same launch -> same image at the same moment) is visible in one
    loop of the file.
    """
    seq = list(frames) + list(frames) if loop_extra_pass else list(frames)
    ims = [Image.fromarray(tint(f, rgb=rgb, upscale=upscale, vmin=vmin, vmax=vmax)) for f in seq]
    if colors and colors < 256:
        # the images are monochrome-tinted; a small palette keeps the GIF small
        ims = [im.convert("P", palette=Image.ADAPTIVE, colors=colors) for im in ims]
    ims[0].save(path, save_all=True, append_images=ims[1:], duration=int(1000 / fps), loop=0, optimize=True)


def save_metric_plot(curves: dict[str, list[float]], times: list[float], path: str, t_star: float | None = None):
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6.4, 3.6))
    for name, c in curves.items():
        ax.plot(times, c, label=name)
    if t_star is not None:
        ax.axvline(t_star, color="k", ls="--", lw=1, alpha=0.7)
        ax.annotate("t*", (t_star, ax.get_ylim()[1] * 0.92), ha="center")
    ax.set_xlabel("time after launch (s)")
    ax.set_ylabel("corr(target, caustic)")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=140)
    plt.close(fig)
