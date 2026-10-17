"""The contrast trap, as a reproducible figure.

Renders one saved launch's reveal frame three ways:

  1. min-max stretched to full range  <- what fooled us: an invisible ripple
                                          displayed as a brilliant image
  2. fixed +/- 25 % of mean window    <- what a real screen would show
  3. fixed +/- 1 % of mean window     <- the structure is really there, but
                                          only a camera with ~1 % noise floor
                                          would see it

The script prints the measured contrast (std/mean) and the focusing parameter
chi for the frame, so the figure carries its own numbers.

Run:  .venv/bin/python scripts/contrast_trap_figure.py            # = results/coarse8
      .venv/bin/python scripts/contrast_trap_figure.py --tag outline
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
from ripple.launch import PistonArrayLaunch, VelocityArrayLaunch
from ripple.optics import caustic_strength, render_caustic
from ripple.waves import WaterDomain


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", default="coarse8", help="which saved run to illustrate")
    p.add_argument("--out", default="results/contrast_trap.png")
    a = p.parse_args()

    run = pathlib.Path("results") / a.tag
    saved = torch.load(run / "launch_params.pt", weights_only=False)
    cfg = saved["params"]
    dom = WaterDomain(N=cfg["N"], L=cfg["L"], depth=cfg["depth"])
    cls = PistonArrayLaunch if saved["kind"] == "eta" else VelocityArrayLaunch
    launch = cls(dom, n_coarse=cfg["n_coarse"], amp_max=cfg["amp_max"])
    with torch.no_grad():
        launch.A.copy_(saved["A"].to(launch.A.dtype))
        eta = launch.surface_at(cfg["t_star"])
        img = render_caustic(
            eta, L=dom.L, depth=dom.depth, gap=cfg["gap"], blur_px=cfg.get("blur", 1.2),
            screen_scale=1.0, rays_per_cell=cfg.get("rays_per_cell", 2), area_average=True,
        ).numpy()
        chi = caustic_strength(eta, dom.L, dom.depth, cfg["gap"])

    con = float(img.std() / (img.mean() + 1e-30))
    stretched = viz.to_u8(img) / 255.0          # min-max, the dishonest view
    honest = viz.relative(img, 0.25)            # what a screen shows
    zoom = viz.relative(img, max(1e-4, con))    # zoomed to the real structure

    viz.save_grid(
        [stretched, honest, zoom],
        a.out,
        ncols=3,
        upscale=3,
        vmin=0.0,
        vmax=1.0,
        labels=[
            f"min-max stretched (lies)",
            f"fixed +/-25% window (a screen)",
            f"fixed +/-{max(1e-4, con):.1%} window (the real ripple)",
        ],
    )
    print(f"[{a.tag}] contrast = {con:.3f} (std/mean), chi = {chi:.4f}")
    print(f"  the middle panel is what an eye or camera would see; wrote {a.out}")


if __name__ == "__main__":
    main()
