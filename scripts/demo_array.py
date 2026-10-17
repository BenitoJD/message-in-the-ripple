"""Stage B + C — the actual research question.

A *finite mechanical launch* imprints the water surface once, then lets the
waves propagate freely. Can the light refracted through the freely evolving
surface assemble into the target glyph at a chosen instant t*, and dissolve
again?

Pipeline
--------
A. optimize_static : design the ideal surface at t* (computational caustics).
B. time_reverse    : reverse the undamped wave equation to learn the ideal
                     launch state at t=0 that would evolve into that surface.
C. optimize_launch : optimize a *constrained* launcher (piston bed / droplet
                     barrage) end-to-end through propagation + optics. The
                     time-reversed field is projected onto the launcher as a
                     warm start ("reverse-and-project").

Controls reported
-----------------
* corr(target, caustic(0))  — the imprint alone must NOT already show the
  glyph, otherwise free motion is doing no work.
* random-launch baseline   — what an untuned launch scores (~0).
* determinism              — relaunching gives a bit-identical frame at t*.

Run:  .venv/bin/python scripts/demo_array.py --symbol "♥" --t-star 0.55
"""

from __future__ import annotations

import argparse
import hashlib
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
from ripple.inverse import (
    correlation_curve,
    corr,
    optimize_launch,
    optimize_static,
    regress_launch,
    render_of,
    time_reverse,
)
from ripple.launch import PistonArrayLaunch, VelocityArrayLaunch
from ripple.optics import caustic_strength
from ripple.targets import target_from_spec
from ripple.waves import WaterDomain


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--symbol", default="♥")
    p.add_argument("--mode", default="ink", choices=["ink", "outline"])
    p.add_argument("--flower", type=int, default=0, help="draw a parametric flower with this many petals instead of --symbol")
    p.add_argument("--N", type=int, default=192)
    p.add_argument("--L", type=float, default=0.4)
    p.add_argument("--depth", type=float, default=0.008)
    p.add_argument("--gap", type=float, default=0.12)
    p.add_argument("--t-star", type=float, default=0.55, help="reveal instant (s after launch)")
    p.add_argument("--n-coarse", type=int, default=32, help="actuator grid (n x n)")
    p.add_argument("--amp-max", type=float, default=1.5e-3, help="max imprint (m or m/s)")
    p.add_argument("--launch", default="eta", choices=["eta", "velocity"])
    p.add_argument("--static-iters", type=int, default=250)
    p.add_argument("--iters", type=int, default=450)
    p.add_argument("--seeds", default="0,1,2")
    p.add_argument("--warm-start", type=int, default=1)
    p.add_argument("--frames", type=int, default=27)
    p.add_argument("--t-window", type=float, default=0.85, help="seconds shown after t*")
    p.add_argument("--rays-per-cell", type=int, default=2, help="S x S rays per cell; S>=2 with area averaging is physical")
    p.add_argument("--c-min", type=float, default=0.15, help="minimum visible caustic contrast (std/mean)")
    p.add_argument("--w-contrast", type=float, default=20.0)
    p.add_argument("--display-dev", type=float, default=0.25, help="display window: +/- this fraction of mean intensity")
    p.add_argument("--blur", type=float, default=1.2, help="source-size blur (px)")
    p.add_argument("--out", default="results")
    p.add_argument("--tag", default="", help="write into results/<tag>/ instead")
    a = p.parse_args()

    out = pathlib.Path(a.out) / a.tag if a.tag else pathlib.Path(a.out)
    out.mkdir(parents=True, exist_ok=True)
    dom = WaterDomain(N=a.N, L=a.L, depth=a.depth)
    if a.flower:  # resolve to a spec that re-rendering can reproduce
        a.symbol = f"flower{a.flower}"
    target_np = target_from_spec(a.symbol, N=a.N, mode=a.mode)
    target = torch.from_numpy(target_np)
    optics = dict(gap=a.gap, n_water=1.331, blur_px=a.blur, screen_scale=1.0,
                  rays_per_cell=a.rays_per_cell, area_average=True)
    cls = PistonArrayLaunch if a.launch == "eta" else VelocityArrayLaunch
    seeds = [int(s) for s in a.seeds.split(",") if s.strip()]

    # ---------------------------------------------------------------- stage A
    print(f"[A] static caustic design ({a.symbol!r}, {a.mode}) ...")
    eta_star, hist_a = optimize_static(
        dom, target, optics, iters=a.static_iters, amp_max=a.amp_max, seed=seeds[0],
        c_min=a.c_min, w_c=a.w_contrast, verbose=True
    )
    corr_static = hist_a[-1]
    viz.save_gray(eta_star.numpy(), str(out / "designed_surface.png"), upscale=3)
    viz.save_gray(viz.relative(render_of(eta_star, dom, optics).numpy(), a.display_dev),
                 str(out / "designed_caustic.png"), upscale=3, vmin=0.0, vmax=1.0)

    # ---------------------------------------------------------------- stage B
    print("[B] time-reversing the designed surface to an ideal launch state ...")
    with torch.no_grad():
        eta0_ideal, v0_ideal = time_reverse(dom, eta_star, a.t_star)
        ideal_field = eta0_ideal if a.launch == "eta" else v0_ideal
        print(
            f"    ideal launch rms = {1e3 * float(ideal_field.pow(2).mean().sqrt()):.3f} "
            f"{'mm' if a.launch == 'eta' else 'mm/s'}"
        )

    # ---------------------------------------------------------------- stage C
    best = None
    best_score = -2.0
    results = []
    for i, seed in enumerate(seeds):
        torch.manual_seed(seed)
        launch = cls(dom, n_coarse=a.n_coarse, amp_max=a.amp_max)
        warm = 0.0
        if a.warm_start and i == 0:
            warm = regress_launch(dom, ideal_field, launch, iters=200)
            print(f"    [seed {seed}] reverse-and-project fidelity cos = {warm:.3f}")
        print(f"[C] optimizing launch, seed {seed} ...")
        hist = optimize_launch(dom, launch, target, a.t_star, optics, iters=a.iters,
                               c_min=a.c_min, w_c=a.w_contrast)
        with torch.no_grad():
            img_star = render_of(launch.surface_at(a.t_star), dom, optics)
            score = corr(img_star, target)
        results.append({"seed": seed, "cos_projection": warm, "corr_at_tstar": score, "history": hist[:: max(1, len(hist) // 25)]})
        print(f"    [seed {seed}] corr@t* = {score:+.3f}")
        if score > best_score:
            best_score, best = score, launch

    # ------------------------------------------------------------- timeline
    print("[C] rendering timeline of the best launch ...")
    t_lo = max(0.02, a.t_star - (a.t_window * 0.55))
    times = np.unique(np.round(np.concatenate([np.linspace(t_lo, a.t_star + a.t_window, a.frames), [a.t_star]]), 5))
    curve = correlation_curve(dom, best, target, times, optics)
    frames, diags = [], []
    with torch.no_grad():
        for t in times:
            img, d = render_of(best.surface_at(float(t)), dom, optics, diagnostics=True)
            frames.append(img.numpy())
            diags.append(d)
    i_star = int(np.argmin(np.abs(times - a.t_star)))
    ref = frames[i_star]
    disp = [viz.relative(f, a.display_dev) for f in frames]
    print(f"        display window = mean +/- {a.display_dev:.0%} of mean intensity (no contrast stretching)")
    viz.save_gif(disp, str(out / "reveal.gif"), fps=12, upscale=2, vmin=0.0, vmax=1.0)
    viz.save_grid(
        disp,
        str(out / "reveal_timeline.png"),
        ncols=7,
        upscale=1,
        labels=[f"t={t:.2f}s" for t in times],
        vmin=0.0,
        vmax=1.0,
    )
    viz.save_gray(target_np, str(out / "target.png"), upscale=3)
    viz.save_gray(best.imprint().detach().numpy(), str(out / "launch_imprint.png"), upscale=3)
    viz.save_gray(disp[i_star], str(out / "reveal_frame_tstar.png"), upscale=3, vmin=0.0, vmax=1.0)
    viz.save_metric_plot({"best launch": curve}, list(times), str(out / "correlation_curve.png"), t_star=a.t_star)
    torch.save({"A": best.A.detach().cpu(), "kind": best.kind, "params": vars(a)}, str(out / "launch_params.pt"))

    # ------------------------------------------------------------ controls
    print("[control] imprint-only and random-launch baselines ...")
    with torch.no_grad():
        corr_t0 = corr(render_of(best.surface_at(0.0), dom, optics), target)
        torch.manual_seed(1234)
        rnd = cls(dom, n_coarse=a.n_coarse, amp_max=a.amp_max)
        corr_rand = corr(render_of(rnd.surface_at(a.t_star), dom, optics), target)
        f1 = render_of(best.surface_at(a.t_star), dom, optics).numpy()
        f2 = render_of(best.surface_at(a.t_star), dom, optics).numpy()
        corr_ts_exact = corr(torch.from_numpy(f1), target)
    det_hash = hashlib.sha256(f1.tobytes()).hexdigest()[:16]
    deterministic = bool(np.array_equal(f1, f2))
    peak_idx = int(np.argmax(curve))
    legible = [float(t) for t, c in zip(times, curve) if c > 0.5 * max(curve)]
    window_ms = 1e3 * (max(legible) - min(legible)) if len(legible) > 1 else 0.0

    print(f"        corr at t=0 (imprint alone) = {corr_t0:+.3f}")
    print(f"        corr at exactly t* = {corr_ts_exact:+.3f}")
    print(f"        random-launch baseline      = {corr_rand:+.3f}")
    print(f"        peak corr = {max(curve):+.3f} at t = {times[peak_idx]:.2f} s")
    print(f"        contrast (std/mean) = {float(f1.std() / (f1.mean() + 1e-30)):.3f}")
    print(f"        caustic strength chi = {caustic_strength(best.surface_at(a.t_star).detach(), dom.L, dom.depth, a.gap):.3f} (order 1 = real focusing)")
    print(f"        legible window (corr > 50% peak) = {window_ms:.0f} ms")
    print(f"        determinism: {'bit-identical' if deterministic else 'MISMATCH'} ({det_hash})")

    metrics = {
        "stage": "C_wave_reveal",
        "symbol": a.symbol,
        "mode": a.mode,
        "t_star_s": a.t_star,
        "corr_static_design": corr_static,
        "corr_peak": max(curve),
        "corr_at_tstar_exact": corr_ts_exact,
        "t_peak_s": float(times[peak_idx]),
        "corr_at_t0_imprint_only": corr_t0,
        "corr_random_launch": corr_rand,
        "corr_curve": {f"{t:.3f}": c for t, c in zip(times, curve)},
        "legible_window_ms": window_ms,
        "determinism": {"bit_identical": deterministic, "sha256_16": det_hash},
        "seeds": results,
        "contrast_at_tstar": float(f1.std() / (f1.mean() + 1e-30)),
        "chi_at_tstar": caustic_strength(best.surface_at(a.t_star).detach(), dom.L, dom.depth, a.gap),
        "display_window_fraction": a.display_dev,
        "final_slope_max": float(diags[i_star]["slope_max"]),
        "final_eta_rms_mm": 1e3 * float(diags[i_star]["eta_rms"]),
        "lost_light_fraction": float(diags[i_star]["lost_fraction"]),
        "params": {k: v for k, v in vars(a).items()},
    }
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(f"        wrote {out}/reveal_timeline.png, reveal.gif, correlation_curve.png, metrics.json")


if __name__ == "__main__":
    main()
