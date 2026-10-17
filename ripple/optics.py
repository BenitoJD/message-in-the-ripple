"""Differentiable caustic renderer: Snell's law ray trace from a wavy water
surface to a screen below the tray.

Geometry (all lengths in metres):

    z = eta(x,y)      wavy air/water interface (mean level z = 0)
    z = -depth        flat tray bottom (glass; modelled as a plane interface)
    z = -depth - gap  screen (matte white)

Light arrives from above, collimated and pointing straight down. Each surface
cell launches one ray of flux dx^2. The ray refracts at the wavy top surface
(air -> water), crosses the water, refracts at the flat bottom (water -> air)
and lands on the screen. Screen intensity is the flux density of the landing
points — a histogram built with bilinear splatting, so the whole map

    surface elevation  ->  screen intensity

is one differentiable torch program. That is the object the inverse design
optimizes through.

Everything is vectorized over the N x N grid; no loops over rays.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F


# --------------------------------------------------------------------- kernels
def _gauss_kernel(sigma: float, device, dtype) -> torch.Tensor:
    radius = max(1, int(3 * sigma))
    x = torch.arange(-radius, radius + 1, device=device, dtype=dtype)
    k = torch.exp(-(x**2) / (2 * sigma**2))
    return k / k.sum()


def gaussian_blur2d(img: torch.Tensor, sigma: float) -> torch.Tensor:
    """Separable Gaussian blur with a fixed (non-trainable) kernel."""
    if sigma <= 0:
        return img
    k = _gauss_kernel(sigma, img.device, img.dtype)[None, None, None, :]
    r = k.shape[-1] // 2
    x = img[None, None]
    x = F.conv2d(F.pad(x, (r, r, 0, 0), mode="replicate"), k)
    x = F.conv2d(F.pad(x, (0, 0, r, r), mode="replicate"), k.transpose(-1, -2))
    return x[0, 0]


def refract(d: torch.Tensor, n: torch.Tensor, ratio: float) -> tuple[torch.Tensor, torch.Tensor]:
    """Vector Snell refraction.

    d : incident unit directions, pointing *toward* the interface
    n : interface unit normals, pointing *against* d (cos_i = -d.n > 0)
    ratio : n_incident / n_transmitted
    Returns (transmitted unit direction, valid_mask). Rays beyond the total
    internal reflection angle (ratio > 1) come back invalid.
    """
    cos_i = (-d * n).sum(-1, keepdim=True).clamp(1e-9, 1.0)
    sin2_t = ratio * ratio * (1.0 - cos_i * cos_i)
    ok = sin2_t <= 1.0
    cos_t = torch.sqrt(torch.clamp(1.0 - sin2_t, min=0.0))
    t = ratio * d + (ratio * cos_i - cos_t) * n
    return t / t.norm(dim=-1, keepdim=True), ok.squeeze(-1)


# ----------------------------------------------------------------- renderer
def render_caustic(
    eta: torch.Tensor,
    L: float,
    depth: float,
    gap: float,
    n_water: float = 1.331,
    screen_scale: float = 1.0,
    blur_px: float = 1.0,
    rays_per_cell: int = 1,
    area_average: bool = True,
    return_diagnostics: bool = False,
):
    """Render the caustic pattern on the screen below the tray.

    Parameters
    ----------
    eta       : (N, N) surface elevation tensor (requires_grad is honoured).
    L         : side length of the tray (m).
    depth     : water depth below mean level (m).
    gap       : air gap between tray bottom and screen (m).
    n_water   : refractive index of water.
    screen_scale : screen extent relative to the tray. 1.0 aligns the screen
                pixel grid with the tray cell grid — a flat surface then maps
                to an *exactly* uniform screen (no resampling aliasing).
    blur_px   : blur standing in for the finite angular size of the light
                source (a truly collimated point source would give
                infinitely sharp caustic folds).
    rays_per_cell : S x S rays launched per surface cell. S=1 with
                area_average=False is the cheapest setting and gives an exactly
                uniform image for flat water, but it converts *sub-pixel* ray
                displacements into pixel-level texture (a beat between the ray
                lattice and the pixel lattice) which can exaggerate weak
                caustics. For physically meaningful contrast use S >= 3 with
                area_average=True.
    area_average : a screen pixel integrates intensity over its area. With
                S > 1 this averages each S x S block of the fine ray grid into
                one pixel, i.e. it performs that integral and removes the
                lattice beat. S=1 makes this a no-op.

    Returns the (N, N) screen intensity (same grid count as the tray), or
    (intensity, diagnostics) if return_diagnostics.
    """
    N = eta.shape[-1]
    S = max(1, int(rays_per_cell))
    M = N * S
    dxf = L / M
    device, dtype = eta.device, eta.dtype
    n_air = 1.0

    idx = torch.arange(M, device=device, dtype=dtype)
    x = (idx[None, :] + 0.5) * dxf - L / 2  # fine cell centres, x along axis 1
    y = (idx[:, None] + 0.5) * dxf - L / 2  # y along axis 0

    # --- surface slope on the coarse grid, interpolated to the fine grid ----
    etax = (torch.roll(eta, -1, dims=1) - torch.roll(eta, 1, dims=1)) / (2 * (L / N))
    etay = (torch.roll(eta, -1, dims=0) - torch.roll(eta, 1, dims=0)) / (2 * (L / N))

    def up(f: torch.Tensor) -> torch.Tensor:
        return F.interpolate(f[None, None], size=(M, M), mode="bicubic", align_corners=True)[0, 0]

    etax, etay = up(etax), up(etay)
    inv_norm = torch.rsqrt(1.0 + etax**2 + etay**2)
    nrm = torch.stack([-etax * inv_norm, -etay * inv_norm, inv_norm.expand(M, M)], dim=-1)

    # --- air -> water at the wavy top surface -------------------------------
    eta_f = up(eta)  # surface height at the ray positions
    d_in = torch.zeros_like(nrm)
    d_in[..., 2] = -1.0
    t_dir, ok1 = refract(d_in, nrm, n_air / n_water)

    # travel to the flat bottom at z = -depth
    tz = t_dir[..., 2].clamp(max=-1e-9)
    s1 = (eta_f + depth) / (-tz)
    xw = x + s1 * t_dir[..., 0]
    yw = y + s1 * t_dir[..., 1]

    # --- water -> air at the flat bottom ------------------------------------
    nb = torch.zeros_like(nrm)
    nb[..., 2] = 1.0
    u_dir, ok2 = refract(t_dir, nb, n_water / n_air)
    uz = u_dir[..., 2].clamp(max=-1e-9)
    s2 = gap / (-uz)
    xs = xw + s2 * u_dir[..., 0]
    ys = yw + s2 * u_dir[..., 1]

    # --- splat equal flux per fine-grid ray ----------------------------------
    flux = torch.full_like(xs, dxf * dxf)
    if area_average and S > 1:
        # A screen pixel integrates the intensity over its area. Splatting into
        # the fine grid and then averaging each S x S block *is* that integral,
        # and it removes the lattice beat that a 1-ray-per-pixel histogram
        # would otherwise imprint on sub-pixel structures.
        fine = splat(xs, ys, flux, ok1 & ok2, M, L * screen_scale)
        img = fine.view(N, S, N, S).mean(dim=(1, 3))
    else:
        img = splat(xs, ys, flux, ok1 & ok2, N, L * screen_scale)
    img = gaussian_blur2d(img, blur_px)

    if return_diagnostics:
        slope = torch.sqrt(etax**2 + etay**2)
        diag = {
            "slope_max": float(slope.max()),
            "eta_rms": float(eta.pow(2).mean().sqrt()),
            "lost_fraction": float((~(ok1 & ok2)).float().mean()),
            "concentration": float(img.max() / (img.mean() + 1e-30)),
        }
        return img, diag
    return img


def caustic_strength(eta: torch.Tensor, L: float, depth: float, gap: float, n_water: float = 1.331) -> float:
    """chi = (n-1) * L_eff * rms(laplacian(eta)) — the honest measure of the
    focusing regime, and the thing a contrast-blind loss will happily ignore.

    Empirically (see results/*/metrics.json): screen contrast tracks chi while
    chi <~ 1 (chi = 0.005 gave 0.5% contrast, chi = 0.12 gave 12%), and far
    beyond that the folds turn into speckle that the source blur then averages
    back down. Order 0.1-1 is the sweet spot for a legible, visible image.

    L_eff = gap + depth * (1 - 1/n) / (n - 1) is the effective throw: the air
    gap counts fully, the water column only at ~75%.
    """
    N = eta.shape[-1]
    dx = L / N
    lap = (
        torch.roll(eta, -1, 1) + torch.roll(eta, 1, 1) + torch.roll(eta, -1, 0) + torch.roll(eta, 1, 0) - 4 * eta
    ) / dx**2
    l_eff = gap + depth * (1 - 1 / n_water) / (n_water - 1)
    return float((n_water - 1) * l_eff * lap.pow(2).mean().sqrt())


def splat(xs: torch.Tensor, ys: torch.Tensor, values: torch.Tensor, mask: torch.Tensor, N: int, extent: float) -> torch.Tensor:
    """Bilinear deposition of ray values onto an N x N screen of side `extent`.

    Fully differentiable with respect to `values` *and* to the landing
    positions (the bilinear weights depend smoothly on xs/ys), so gradients
    flow from the screen image back to the surface that deflected the rays.
    """
    u = (xs + extent / 2) / extent * N - 0.5
    v = (ys + extent / 2) / extent * N - 0.5
    inside = mask & (u > -1) & (u < N) & (v > -1) & (v < N)
    u = u.clamp(0.0, N - 1.0001)
    v = v.clamp(0.0, N - 1.0001)
    i0 = u.floor()
    j0 = v.floor()
    fu = u - i0
    fv = v - j0
    flat = torch.zeros(N * N, dtype=values.dtype, device=values.device)
    ii0 = i0.long()
    jj0 = j0.long()
    for di, dj, w in (
        (0, 0, (1 - fu) * (1 - fv)),
        (1, 0, fu * (1 - fv)),
        (0, 1, (1 - fu) * fv),
        (1, 1, fu * fv),
    ):
        idx = ((ii0 + di).clamp(0, N - 1)) * N + ((jj0 + dj).clamp(0, N - 1))
        flat = flat.index_add(0, idx[inside], (values * w)[inside])
    return flat.view(N, N)
