"""Sampling study: how much of a rendered caustic is physics, and how much is
the ray lattice beating against the pixel grid?

Motivation
----------
A ray-traced intensity image is a histogram. With one ray per pixel, a ray
displacement of a fraction of a pixel still moves flux between neighbouring
pixels, so *sub-pixel* surface structure can produce pixel-level texture that
does not exist in the continuum intensity a real screen would show. Because the
optimization loss is a Pearson correlation (invariant to overall contrast) the
design pipeline can be tempted to exploit exactly that.

This script renders one fixed launch with increasing ray sampling and with the
physically correct pixel-area integration, and reports
  * Pearson correlation against the target,
  * image contrast (std/mean),
  * the continuum caustic-strength parameter
        chi = (n - 1) * L_eff * rms(laplacian(eta)),
    which is the honest predictor of whether real focusing happens (chi ~ 1).

Run:  .venv/bin/python scripts/probe_sampling.py --params results/ink/launch_params.pt
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "ripple-mpl"))

import numpy as np
import torch

from ripple import viz
from ripple.inverse import corr
from ripple.launch import PistonArrayLaunch, VelocityArrayLaunch
from ripple.optics import caustic_strength, render_caustic
from ripple.targets import glyph_target
from ripple.waves import WaterDomain


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--params", default="results/ink/launch_params.pt")
    p.add_argument("--t-star", type=float, default=None, help="default: from the saved params")
    p.add_argument("--out", default="results/probe_sampling.png")
    a = p.parse_args()

    saved = torch.load(a.params, weights_only=False)
    cfg = saved["params"]
    t_star = a.t_star if a.t_star is not None else cfg["t_star"]
    dom = WaterDomain(N=cfg["N"], L=cfg["L"], depth=cfg["depth"])
    cls = PistonArrayLaunch if saved["kind"] == "eta" else VelocityArrayLaunch
    launch = cls(dom, n_coarse=cfg["n_coarse"], amp_max=cfg["amp_max"])
    with torch.no_grad():
        launch.A.copy_(saved["A"].to(launch.A.dtype))

    target = torch.from_numpy(glyph_target(cfg["symbol"], N=cfg["N"], mode=cfg["mode"]))
    with torch.no_grad():
        eta = launch.surface_at(t_star)
        chi = caustic_strength(eta, dom.L, dom.depth, cfg["gap"])
        print(f"launch: {saved['kind']} {cfg['n_coarse']}x{cfg['n_coarse']}, t* = {t_star:.2f} s")
        print(f"continuum caustic strength chi = {chi:.3f}   (chi ~ 1 = strong focusing)")
        print(f"{'S':>3} {'area-avg':>9} {'corr':>7} {'contrast':>9} {'concentration':>14}")

        panels, labels = [], []
        rows = [
            (1, False),
            (2, False),
            (4, False),
            (4, True),
            (8, True),
            (16, True),
        ]
        for s, aa in rows:
            img, diag = render_caustic(
                eta,
                L=dom.L,
                depth=cfg["depth"],
                gap=cfg["gap"],
                blur_px=cfg["blur"],
                screen_scale=1.0,
                rays_per_cell=s,
                area_average=aa,
                return_diagnostics=True,
            )
            c = corr(img, target)
            contrast = float(img.std() / (img.mean() + 1e-30))
            print(f"{s:3d} {str(aa):>9} {c:+7.3f} {contrast:9.3f} {diag['concentration']:14.2f}")
            if s in (1, 4) and not aa or (s == 8 and aa):
                panels.append(img.numpy())
                labels.append(f"S={s}, area-avg={aa}\ncorr={c:+.3f}, contrast={contrast:.2f}")

    if panels:
        viz.save_grid(panels, a.out, ncols=len(panels), upscale=3, labels=labels)
        print(f"wrote {a.out}")


if __name__ == "__main__":
    main()
