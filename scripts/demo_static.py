"""Stage A — free-surface caustic design.

Optimize a *static* water surface so that the light refracted through it lands
on the screen as the target glyph. This is the computational-caustics sanity
check: it validates the optics (Snell trace + differentiable splatting)
before any wave dynamics enter the picture. It also produces the "ideal"
surface that stage B time-reverses.

Run:  .venv/bin/python scripts/demo_static.py --symbol "♥" --iters 300
"""

from __future__ import annotations

import argparse
import json
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "ripple-mpl"))

import numpy as np
import torch

from ripple import viz
from ripple.inverse import optimize_static, render_of
from ripple.optics import caustic_strength
from ripple.targets import target_from_spec
from ripple.waves import WaterDomain


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="♥", help="any glyph matplotlib's font can draw")
    p.add_argument("--mode", default="ink", choices=["ink", "outline"])
    p.add_argument("--flower", type=int, default=0, help="parametric flower with this many petals instead of --symbol")
    p.add_argument("--N", type=int, default=192)
    p.add_argument("--L", type=float, default=0.4)
    p.add_argument("--depth", type=float, default=0.008)
    p.add_argument("--gap", type=float, default=0.12, help="air gap between tray bottom and screen (m)")
    p.add_argument("--amp-max", type=float, default=1.2e-3)
    p.add_argument("--iters", type=int, default=300)
    p.add_argument("--lr", type=float, default=0.03)
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--rays-per-cell", type=int, default=2)
    p.add_argument("--c-min", type=float, default=0.15)
    p.add_argument("--w-contrast", type=float, default=20.0)
    p.add_argument("--display-dev", type=float, default=0.25)
    p.add_argument("--blur", type=float, default=1.2)
    p.add_argument("--out", default="results")
    p.add_argument("--tag", default="")
    a = p.parse_args()

    torch.manual_seed(a.seed)
    out = pathlib.Path(a.out) / a.tag if a.tag else pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)

    dom = WaterDomain(N=a.N, L=a.L, depth=a.depth)
    if a.flower:
        a.symbol = f"flower{a.flower}"
    target_np = target_from_spec(a.symbol, N=a.N, mode=a.mode)
    target = torch.from_numpy(target_np)
    optics = dict(gap=a.gap, n_water=1.331, blur_px=a.blur, screen_scale=1.0,
                  rays_per_cell=a.rays_per_cell, area_average=True)

    print(f"stage A: static caustic design for {a.symbol!r} ({a.mode}), N={a.N}, gap={a.gap * 100:.0f} cm")
    eta, hist = optimize_static(dom, target, optics, iters=a.iters, lr=a.lr, amp_max=a.amp_max,
                                seed=a.seed, c_min=a.c_min, w_c=a.w_contrast)

    with torch.no_grad():
        img, diag = render_of(eta, dom, optics, diagnostics=True)
        stats = dom.slope_stats(eta)
        con = float(img.std() / (img.mean() + 1e-30))
        chi = caustic_strength(eta, dom.L, dom.depth, a.gap)
    print(f"  final corr = {hist[-1]:+.3f} | contrast = {con:.3f} | chi = {chi:.3f} | slope_max = {stats['slope_max']:.3f}")

    viz.save_gray(target_np, str(out / "target.png"), upscale=3)
    viz.save_gray(eta.numpy(), str(out / "static_surface.png"), upscale=3)
    viz.save_gray(viz.relative(img.numpy(), a.display_dev), str(out / "static_caustic.png"),
                  upscale=3, vmin=0.0, vmax=1.0)
    viz.save_grid(
        [target_np, eta.numpy(), img.numpy()],
        str(out / "static_design.png"),
        ncols=3,
        upscale=3,
        labels=["target glyph", "designed surface", "rendered caustic"],
    )
    metrics = {
        "stage": "A_static",
        "symbol": a.symbol,
        "mode": a.mode,
        "corr": hist[-1],
        "corr_history": hist[:: max(1, len(hist) // 40)],
        "slope_max": stats["slope_max"],
        "eta_rms_mm": 1e3 * stats["eta_rms"],
        "concentration": diag["concentration"],
        "contrast": con,
        "chi": chi,
        "display_window_fraction": a.display_dev,
        "params": vars(a),
    }
    (out / "static_metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"  wrote {out}/static_design.png, static_metrics.json")


if __name__ == "__main__":
    main()
