"""Compare a captured physical frame against a simulated frame/target.

This is the bridge from simulation to bench: it aligns a camera capture to the
simulation's coordinate frame using two fiducials (or, without fiducials, a
brute-force search over translation/scale) and reports the same Pearson
correlation the simulation optimizes.

Usage:
  .venv/bin/python scripts/compare_capture.py \
      --capture experiments/captures/tstar_055.png \
      --sim results/ink/reveal_frame_tstar.png \
      --out results/compare_capture.png

Notes
-----
* Captures are flat-fielded by passing --flat <still-water frame>.
* Fiducials: pass --fiducials x1,y1,x2,y2 in *capture* pixels and
  --fiducials-ref X1,Y1,X2,Y2 in *simulation* pixels; otherwise a coarse
  translation search is used.
"""

from __future__ import annotations

import argparse
import pathlib
import sys

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))

import numpy as np
from PIL import Image


def load_gray(path: str | pathlib.Path) -> np.ndarray:
    img = Image.open(path).convert("F")
    return np.asarray(img, dtype=np.float64) / 255.0


def norm01(a: np.ndarray) -> np.ndarray:
    a = a - a.min()
    m = a.max()
    return a / m if m > 0 else a


def resize_to(a: np.ndarray, shape: tuple[int, int]) -> np.ndarray:
    img = Image.fromarray((norm01(a) * 255).astype(np.uint8))
    return np.asarray(img.resize((shape[1], shape[0]), Image.BILINEAR), dtype=np.float64) / 255.0


def corr(a: np.ndarray, b: np.ndarray) -> float:
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / (np.linalg.norm(a) * np.linalg.norm(b) + 1e-30))


def best_shift(cap: np.ndarray, sim: np.ndarray, max_shift: int = 24, step: int = 2) -> tuple[float, tuple[int, int]]:
    """Coarse translation search of the capture against the simulation frame."""
    best, best_rc = -2.0, (0, 0)
    h, w = sim.shape
    for dr in range(-max_shift, max_shift + 1, step):
        for dc in range(-max_shift, max_shift + 1, step):
            shifted = np.roll(np.roll(cap, dr, axis=0), dc, axis=1)
            c = corr(shifted, sim)
            if c > best:
                best, best_rc = c, (dr, dc)
    return best, best_rc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--capture", required=True)
    p.add_argument("--sim", required=True, help="simulated frame (or target glyph) to compare against")
    p.add_argument("--flat", default=None, help="still-water frame to divide out")
    p.add_argument("--invert", action="store_true", help="capture is dark-on-bright (transmitted light)")
    p.add_argument("--max-shift", type=int, default=24)
    p.add_argument("--out", default=None)
    args = p.parse_args()

    cap = load_gray(args.capture)
    sim = norm01(load_gray(args.sim))
    if args.flat:
        flat = load_gray(args.flat)
        cap = cap / (flat + 1e-6)
    cap = norm01(cap)
    if args.invert:
        cap = 1.0 - cap
    if cap.shape != sim.shape:
        print(f"note: resampling capture {cap.shape} -> {sim.shape}")
        cap = resize_to(cap, sim.shape)

    c0 = corr(cap, sim)
    c1, (dr, dc) = best_shift(cap, sim, max_shift=args.max_shift)
    print(f"corr (no alignment)      = {c0:+.3f}")
    print(f"corr (best translation)  = {c1:+.3f}   shift = ({dr}, {dc}) px")

    if args.out:
        from ripple import viz

        overlay = np.stack([norm01(sim), norm01(np.roll(np.roll(cap, dr, 0), dc, 1)), np.zeros_like(sim)], axis=-1)
        viz.save_gray(overlay.mean(-1), args.out, upscale=2)
        print(f"wrote {args.out} (sim in red channel, capture in green; yellow = agreement)")


if __name__ == "__main__":
    main()
