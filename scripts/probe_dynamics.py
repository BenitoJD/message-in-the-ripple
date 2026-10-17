"""Probe the wave dynamics of a given launch: how fast does structure
decorrelate, and what surface curvature (which is what focuses light) is
available at each instant?

Run:  .venv/bin/python scripts/probe_dynamics.py
"""

from __future__ import annotations

import argparse
import os
import pathlib
import sys
import tempfile

sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1]))
os.environ.setdefault("MPLCONFIGDIR", os.path.join(tempfile.gettempdir(), "ripple-mpl"))

import torch

from ripple.launch import PistonArrayLaunch, VelocityArrayLaunch
from ripple.waves import WaterDomain


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("--N", type=int, default=192)
    p.add_argument("--L", type=float, default=0.4)
    p.add_argument("--depth", type=float, default=0.008)
    p.add_argument("--n-coarse", type=int, default=32)
    p.add_argument("--amp-max", type=float, default=1.2e-3)
    p.add_argument("--launch", default="eta", choices=["eta", "velocity"])
    p.add_argument("--seed", type=int, default=0)
    p.add_argument("--tmax", type=float, default=1.2)
    p.add_argument("--steps", type=int, default=13)
    a = p.parse_args()

    torch.manual_seed(a.seed)
    dom = WaterDomain(N=a.N, L=a.L, depth=a.depth)
    cls = PistonArrayLaunch if a.launch == "eta" else VelocityArrayLaunch
    launch = cls(dom, n_coarse=a.n_coarse, amp_max=a.amp_max)
    with torch.no_grad():
        launch.A.normal_(0, 1.0)  # a "full-on" random actuation, worst case

    with torch.no_grad():
        eta0, v0 = launch.initial_state()
        print(f"imprint: {a.launch}, rms(imprint) = {float(eta0.pow(2).mean().sqrt() + v0.pow(2).mean().sqrt()):.3e}")
        print(f"{'t (s)':>7} {'eta_rms (mm)':>13} {'slope_rms':>10} {'slope_max':>10} {'lap_rms (1/m)':>14} {'corr(eta0,eta_t)':>18}")
        for t in torch.linspace(0.0, a.tmax, a.steps):
            eta = launch.surface_at(float(t))
            etax = (torch.roll(eta, -1, 1) - torch.roll(eta, 1, 1)) / (2 * dom.dx)
            etay = (torch.roll(eta, -1, 0) - torch.roll(eta, 1, 0)) / (2 * dom.dx)
            lap = (torch.roll(eta, -1, 1) + torch.roll(eta, 1, 1) + torch.roll(eta, -1, 0) + torch.roll(eta, 1, 0) - 4 * eta) / dom.dx**2
            c = float(
                ((eta - eta.mean()) * (launch.surface_at(0.0) - launch.surface_at(0.0).mean())).sum()
                / (eta.norm() * launch.surface_at(0.0).norm() + 1e-30)
            )
            print(
                f"{float(t):7.2f} {1e3 * float(eta.pow(2).mean().sqrt()):13.3f} "
                f"{float((etax**2 + etay**2).mean().sqrt()):10.4f} {float((etax**2 + etay**2).max().sqrt()):10.3f} "
                f"{float(lap.pow(2).mean().sqrt()):14.1f} {c:18.3f}"
            )
        print("\ncaustic focusing needs  (n-1) * L_eff * laplacian ~ 1, with")
        print("  L_eff = gap + depth*(1-1/n)/(n-1)  (water path counts less than air):")
        for gap in (0.06, 0.12, 0.20):
            l_eff = gap + a.depth * (1 - 1 / 1.331) / (1.331 - 1)
            print(f"  gap {gap * 100:4.0f} cm -> L_eff {l_eff * 100:5.1f} cm -> need lap ~ {1 / ((1.331 - 1) * l_eff):6.1f} /m")


if __name__ == "__main__":
    main()
