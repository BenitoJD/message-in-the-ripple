"""Inverse design: find a finite launch whose *freely evolved* wave field
renders the target caustic at a chosen instant t*.

Three stages, in increasing physical honesty:

A. optimize_static   — free-parameter surface at t* (computational-caustics
                       sanity check of the optics; not a wave yet).
B. time_reverse      — take the stage-A surface (with v=0) and reverse the
                       undamped wave equation to learn what launch state at
                       t=0 would have evolved into it. An *ideal*, possibly
                       unrealizable launch.
C. optimize_launch   — optimize a constrained launcher (piston array /
                       droplet barrage) end-to-end through wave propagation
                       and caustic rendering. This is the actual research
                       question: can a *realizable* launch still do it?

All optimization is Adam through the differentiable chain
launch -> (FFT propagate) -> (Snell ray trace) -> (bilinear splat).
"""

from __future__ import annotations

import torch

from .optics import render_caustic
from .waves import WaterDomain


def corr(a: torch.Tensor, b: torch.Tensor) -> float:
    """Pearson correlation between two images (as a python float)."""
    a = a - a.mean()
    b = b - b.mean()
    return float((a * b).sum() / (a.norm() * b.norm() + 1e-30))


def corr_loss(img: torch.Tensor, target: torch.Tensor) -> torch.Tensor:
    """Differentiable negative Pearson correlation (scale/offset invariant:
    caustics have no meaningful absolute brightness, only structure).

    NOTE: being contrast-blind, this alone is a *dangerous* objective — a
    0.5%-contrast ripple that happens to match the target scores as well as a
    brilliant one. Pair it with `shape_loss` (or at least report contrast and
    chi alongside); see scripts/probe_sampling.py.
    """
    a = img - img.mean()
    b = target - target.mean()
    return -(a * b).sum() / (a.norm() * b.norm() + 1e-30)


def contrast(img: torch.Tensor) -> torch.Tensor:
    """std/mean — the visible strength of the caustic pattern (0 = flat)."""
    return img.std() / (img.mean().abs() + 1e-30)


def shape_loss(img: torch.Tensor, target: torch.Tensor, c_min: float = 0.0, w_c: float = 0.0) -> torch.Tensor:
    """Correlation plus a penalty for invisibly weak caustics.

    `c_min` is the minimum acceptable contrast (std/mean). Reaching it requires
    real focusing — chi = (n-1) * L_eff * rms(lap eta) ~ 1 — which is what
    makes the image visible on a physical screen instead of a numerical ripple
    that only a contrast-stretching display can show.
    """
    loss = corr_loss(img, target)
    if c_min > 0 and w_c > 0:
        deficit = torch.relu(c_min - contrast(img))
        loss = loss + w_c * deficit**2
    return loss


def render_of(eta: torch.Tensor, domain: WaterDomain, optics: dict, diagnostics: bool = False):
    return render_caustic(
        eta,
        L=domain.L,
        depth=optics.get("depth", domain.depth),
        gap=optics["gap"],
        n_water=optics.get("n_water", 1.331),
        screen_scale=optics.get("screen_scale", 1.0),
        blur_px=optics.get("blur_px", 1.0),
        rays_per_cell=optics.get("rays_per_cell", 3),
        area_average=optics.get("area_average", True),
        return_diagnostics=diagnostics,
    )


# ------------------------------------------------------------------ stage A
def optimize_static(
    domain: WaterDomain,
    target: torch.Tensor,
    optics: dict,
    iters: int = 350,
    lr: float = 0.03,
    amp_max: float = 2.0e-3,
    prior_w: float = 5.0e-5,
    slope_max: float = 0.35,
    c_min: float = 0.15,
    w_c: float = 20.0,
    seed: int = 0,
    verbose: bool = True,
) -> tuple[torch.Tensor, list[float]]:
    """Optimize the surface elevation *directly* (no wave constraint) so its
    caustic matches the target. Returns (eta, history of correlations)."""
    g = torch.Generator().manual_seed(seed)
    q = (1e-3 * torch.randn((domain.N, domain.N), generator=g, dtype=domain.dtype, device=domain.device) + target.to(domain.dtype) * 0.3).requires_grad_(True)
    opt = torch.optim.Adam([q], lr=lr)
    hist: list[float] = []
    for it in range(iters):
        opt.zero_grad()
        eta = amp_max * torch.tanh(q)
        img = render_of(eta, domain, optics)
        loss = shape_loss(img, target, c_min=c_min, w_c=w_c)
        # keep the design physically gentle: smooth spectrum, bounded slopes
        prior = domain.spectrum_prior(eta, power=8)
        etax = (torch.roll(eta, -1, 1) - torch.roll(eta, 1, 1)) / (2 * domain.dx)
        etay = (torch.roll(eta, -1, 0) - torch.roll(eta, 1, 0)) / (2 * domain.dx)
        over = torch.relu(etax**2 + etay**2 - slope_max**2).mean()
        (loss + prior_w * prior + 1e4 * over).backward()
        opt.step()
        hist.append(corr(img.detach(), target))
        if verbose and (it % 50 == 0 or it == iters - 1):
            print(f"  [static {it:4d}] corr={hist[-1]:+.3f} contrast={float(contrast(img.detach())):.3f}")
    with torch.no_grad():
        eta = amp_max * torch.tanh(q)
        img = render_of(eta, domain, optics)
    return eta, hist


# ------------------------------------------------------------------ stage B
def time_reverse(domain: WaterDomain, eta_star: torch.Tensor, t_star: float) -> tuple[torch.Tensor, torch.Tensor]:
    """State at t=0 that evolves into (eta*, v*=0) at t=t*, undamped system.

    v* = 0 is a deliberate, elegant choice: at the reveal instant the wave
    field is instantaneously at rest, passing *through* its designed shape.
    """
    v_star = torch.zeros_like(eta_star)
    return domain.reverse(eta_star, v_star, t_star)


def regress_launch(
    domain: WaterDomain,
    target_field: torch.Tensor,
    launch,
    iters: int = 150,
    lr: float = 0.05,
    verbose: bool = False,
) -> float:
    """Project a desired initial field onto the constrained launcher
    (in-place warm start of the actuator amplitudes). Returns final cosine
    similarity — the fraction of the ideal imprint the hardware can express."""
    opt = torch.optim.Adam([launch.A], lr=lr)
    cos = 0.0
    for it in range(iters):
        opt.zero_grad()
        imp = launch.imprint()
        cos_t = torch.nn.functional.cosine_similarity(imp.flatten(), target_field.flatten(), dim=0)
        mse = (imp - target_field).pow(2).mean() / (target_field.pow(2).mean() + 1e-30)
        loss = (1.0 - cos_t) + 0.1 * mse
        loss.backward()
        opt.step()
        cos = float(cos_t)
        if verbose and it % 50 == 0:
            print(f"  [regress {it}] cos={cos:.3f} loss={float(loss):.4f}")
    return cos


# backwards-compatible alias
regress_piston = regress_launch


# ------------------------------------------------------------------ stage C
def optimize_launch(
    domain: WaterDomain,
    launch,
    target: torch.Tensor,
    t_star: float,
    optics: dict,
    iters: int = 450,
    lr: float = 0.04,
    prior_w: float = 5.0e-5,
    slope_max: float = 0.35,
    c_min: float = 0.15,
    w_c: float = 20.0,
    verbose: bool = True,
) -> list[float]:
    """End-to-end: launcher parameters -> free propagation to t* -> caustic.

    The only supervision is the caustic at t*. Nothing rewards legibility at
    other times, so whatever comes out is genuinely *produced by the free
    motion*, not by the imprint.
    """
    opt = torch.optim.Adam([launch.A], lr=lr)
    sched = torch.optim.lr_scheduler.CosineAnnealingLR(opt, T_max=max(1, iters), eta_min=lr * 0.05)
    hist: list[float] = []
    for it in range(iters):
        opt.zero_grad()
        eta_star = launch.surface_at(t_star)
        img = render_of(eta_star, domain, optics)
        loss = shape_loss(img, target, c_min=c_min, w_c=w_c)
        prior = domain.spectrum_prior(eta_star, power=8)
        etax = (torch.roll(eta_star, -1, 1) - torch.roll(eta_star, 1, 1)) / (2 * domain.dx)
        etay = (torch.roll(eta_star, -1, 0) - torch.roll(eta_star, 1, 0)) / (2 * domain.dx)
        over = torch.relu(etax**2 + etay**2 - slope_max**2).mean()
        (loss + prior_w * prior + 1e4 * over).backward()
        opt.step()
        sched.step()
        hist.append(corr(img.detach(), target))
        if verbose and (it % 50 == 0 or it == iters - 1):
            print(f"  [launch {it:4d}] corr@t*={hist[-1]:+.3f} contrast={float(contrast(img.detach())):.3f}")
    return hist


@torch.no_grad()
def correlation_curve(domain: WaterDomain, launch, target: torch.Tensor, times, optics: dict) -> list[float]:
    """corr(target, caustic(t)) — the legibility timeline of the reveal."""
    out = []
    for t in times:
        eta = launch.surface_at(float(t))
        img = render_of(eta, domain, optics)
        out.append(corr(img, target))
    return out
