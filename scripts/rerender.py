"""Re-render the reveal timeline / GIF / metrics from saved launch parameters.

Optimization is the expensive part; once `results/<tag>/launch_params.pt`
exists you can re-render at different display scales, sampling, or blur
without re-optimizing. Used to keep the committed result set small.

Run:  .venv/bin/python scripts/rerender.py --tag outline --upscale 1
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
from ripple.inverse import correlation_curve
from ripple.launch import PistonArrayLaunch, VelocityArrayLaunch
from ripple.optics import caustic_strength, render_caustic
from ripple.targets import target_from_spec
from ripple.waves import WaterDomain


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--tag", required=True)
    p.add_argument("--out", default="results")
    p.add_argument("--frames", type=int, default=None)
    p.add_argument("--upscale", type=int, default=1)
    p.add_argument("--gif-upscale", type=int, default=1, help="1 keeps the committed GIF small; 2 for a larger preview")
    p.add_argument("--gif-out", default=None, help="write the GIF here instead of <out>/reveal.gif (use for post-sized exports)")
    p.add_argument("--display-dev", type=float, default=None)
    a = p.parse_args()

    out = pathlib.Path(a.out) / a.tag
    saved = torch.load(out / "launch_params.pt", weights_only=False)
    cfg = saved["params"]
    dev = a.display_dev if a.display_dev is not None else cfg.get("display_dev", 0.25)
    frames_n = a.frames or cfg.get("frames", 27)

    dom = WaterDomain(N=cfg["N"], L=cfg["L"], depth=cfg["depth"])
    cls = PistonArrayLaunch if saved["kind"] == "eta" else VelocityArrayLaunch
    launch = cls(dom, n_coarse=cfg["n_coarse"], amp_max=cfg["amp_max"])
    with torch.no_grad():
        launch.A.copy_(saved["A"].to(launch.A.dtype))

    target_np = target_from_spec(cfg["symbol"], N=cfg["N"], mode=cfg["mode"])
    target = torch.from_numpy(target_np)
    rays = cfg.get("rays_per_cell", 2)
    blur = cfg.get("blur", 1.2)

    def render(eta: torch.Tensor):
        return render_caustic(
            eta, L=dom.L, depth=dom.depth, gap=cfg["gap"], blur_px=blur,
            screen_scale=1.0, rays_per_cell=rays, area_average=True,
        )

    t_star = cfg["t_star"]
    t_lo = max(0.02, t_star - cfg["t_window"] * 0.55)
    times = np.unique(np.round(np.concatenate([np.linspace(t_lo, t_star + cfg["t_window"], frames_n), [t_star]]), 5))

    with torch.no_grad():
        curve = correlation_curve(dom, launch, target, times, dict(gap=cfg["gap"], rays_per_cell=rays, blur_px=blur, area_average=True))
        frames = [render(launch.surface_at(float(t))).numpy() for t in times]
        i_star = int(np.argmin(np.abs(times - t_star)))

    disp = [viz.relative(f, dev) for f in frames]
    gif_path = a.gif_out or str(out / "reveal.gif")
    viz.save_gif(disp, gif_path, fps=12, upscale=a.gif_upscale, vmin=0.0, vmax=1.0)
    viz.save_grid(
        disp, str(out / "reveal_timeline.png"), ncols=7, upscale=a.upscale,
        labels=[f"t={t:.2f}s" for t in times], vmin=0.0, vmax=1.0,
    )
    viz.save_gray(disp[i_star], str(out / "reveal_frame_tstar.png"), upscale=3, vmin=0.0, vmax=1.0)
    viz.save_metric_plot({"best launch": curve}, list(times), str(out / "correlation_curve.png"), t_star=t_star)
    print(f"[{a.tag}] re-rendered {len(times)} frames at S={rays}, display +/-{dev:.0%}, "
          f"corr@t* = {curve[int(np.argmin(np.abs(times - t_star)))]:+.3f}")

    mp = out / "metrics.json"
    if mp.exists():
        m = json.loads(mp.read_text())
        m["display_window_fraction"] = dev
        with torch.no_grad():
            m["chi_at_tstar"] = caustic_strength(launch.surface_at(t_star), dom.L, dom.depth, cfg["gap"])
        mp.write_text(json.dumps(m, indent=2))
        print(f"[{a.tag}] metrics.json refreshed")


if __name__ == "__main__":
    main()
