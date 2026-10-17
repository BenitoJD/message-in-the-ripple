"""Physics sanity tests. Run with:  python tests/test_sanity.py
(pytest-compatible; no pytest dependency.)"""

from __future__ import annotations

import os
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import torch

from ripple.optics import render_caustic
from ripple.waves import WaterDomain


def test_flat_surface_gives_uniform_screen():
    dom = WaterDomain(N=96, L=0.4, depth=0.008)
    eta = torch.zeros((96, 96), dtype=dom.dtype)
    img = render_caustic(eta, L=dom.L, depth=dom.depth, gap=0.05, blur_px=0.5)
    # boundary screen pixels catch only half a footprint; judge the interior
    N = img.shape[0]
    c = img[N // 5 : 4 * N // 5, N // 5 : 4 * N // 5]
    rel = float(c.std() / c.mean())
    assert rel < 1e-6, f"flat water must not focus light (rel std {rel:.1e})"
    print("  flat surface -> uniform screen OK")


def test_bump_focuses_light():
    # Caustic strength scales as (1 - 1/n) * throw * laplacian(eta). With a
    # ~0.12 m throw, strong focusing needs laplacian ~ 1/(0.249*0.128) ~ 31 /m,
    # i.e. millimetre-scale sags over centimetre-scale widths.
    dom = WaterDomain(N=192, L=0.4, depth=0.008)
    N, dx = dom.N, dom.dx
    x = (torch.arange(N, dtype=dom.dtype)[None, :] + 0.5) * dx - dom.L / 2
    y = (torch.arange(N, dtype=dom.dtype)[:, None] + 0.5) * dx - dom.L / 2
    R, a = 0.010, 1.5e-3  # 1 cm wide, 1.5 mm tall paraboloid cap
    dome = a * torch.clamp(1 - (x**2 + y**2) / R**2, min=0.0)
    img, diag = render_caustic(dome, L=dom.L, depth=dom.depth, gap=0.12, blur_px=1.0, return_diagnostics=True)
    conc = float(img.max() / img.mean())
    assert conc > 4.0, f"a 1 cm dome should focus light (max/mean = {conc:.1f})"
    print(f"  dome -> focal structure OK (max/mean = {conc:.1f}, slope_max = {diag['slope_max']:.2f})")


def test_time_reversal_roundtrip():
    # reversal is exact for the inviscid (reversible) system
    dom = WaterDomain(N=96, L=0.4, depth=0.008, nu=0.0)
    g = torch.Generator().manual_seed(1)
    eta0 = 1e-3 * torch.randn((96, 96), generator=g, dtype=dom.dtype)
    v0 = 1e-2 * torch.randn((96, 96), generator=g, dtype=dom.dtype)
    t = 0.63
    eta_t = dom.forward(eta0, v0, t)
    v_t = dom.velocity(eta0, v0, t)
    e0r, v0r = dom.reverse(eta_t, v_t, t)
    err = max(float((e0r - eta0).abs().max()), float((v0r - v0).abs().max()))
    assert err < 1e-10, f"roundtrip error {err:.2e}"
    print(f"  time reversal roundtrip OK (err {err:.1e})")


def test_viscosity_is_the_arrow_of_time():
    # with damping, reversal is only approximate — by design. Feed the *true*
    # damped velocity so the residual isolates viscosity alone.
    dom = WaterDomain(N=96, L=0.4, depth=0.008, nu=1.0e-6)
    g = torch.Generator().manual_seed(2)
    eta0 = 1e-3 * torch.randn((96, 96), generator=g, dtype=dom.dtype)
    z = torch.zeros_like(eta0)
    t = 0.5
    eta_t = dom.forward(eta0, z, t)
    v_t = dom.velocity(eta0, z, t)
    e0r, _ = dom.reverse(eta_t, v_t, t)
    err = float((e0r - eta0).abs().max() / eta0.abs().max())
    assert 1e-3 < err < 0.9, f"damped reversal should be inexact but bounded (rel err {err:.2e})"
    print(f"  damped reversal inexact as expected (rel err {err:.2e})")


def test_dispersion_limits():
    # shallow water: omega^2 -> g h k^2  => c -> sqrt(g h)
    dom = WaterDomain(N=64, L=4.0, depth=0.01, use_capillary=False)
    k = dom.kmag[0, 1].item()
    c = (dom.omega[0, 1] / k).item()
    c_theory = (9.81 * 0.01) ** 0.5
    assert abs(c - c_theory) / c_theory < 0.02
    print(f"  shallow-water limit OK (c = {c:.3f} m/s vs sqrt(gh) = {c_theory:.3f})")


def test_targets_rasterize():
    from ripple.targets import bitmap_from_text, glyph_target

    t = bitmap_from_text("R", N=64)
    assert t.max() > 0.5 and t.mean() > 0.01
    heart = glyph_target("♥", N=64)
    assert heart.max() > 0.5
    print("  glyph rasterization OK")


if __name__ == "__main__":
    os.environ.setdefault("MPLCONFIGDIR", tempfile.mkdtemp())
    test_flat_surface_gives_uniform_screen()
    test_bump_focuses_light()
    test_time_reversal_roundtrip()
    test_viscosity_is_the_arrow_of_time()
    test_dispersion_limits()
    test_targets_rasterize()
    print("all sanity tests passed")
