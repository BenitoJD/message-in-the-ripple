"""Linear gravity-capillary water waves, evolved in closed form in Fourier space.

The linearized free-surface problem for a layer of depth h gives each Fourier
mode k the dispersion relation

    omega(k)^2 = (g k + (sigma/rho) k^3) tanh(k h)

with viscous decay ~ exp(-2 nu k^2 t). Because the dynamics are linear, the
state at any time t has an exact closed form from the initial state:

    eta_hat(k, t) = [eta_hat0 cos(w t) + v_hat0 sin(w t)/w] e^{-gamma t}

This makes every forward evaluation a handful of FFTs — fast enough to put
the *entire* wave simulation inside an autodiff graph, which is what the
inverse design (ripple.inverse) exploits.

Conventions
-----------
* eta(x, y, t): surface elevation about mean level z = 0. Positive up.
* v(x, y, t)  : d eta / dt.
* Domain is periodic (a spectral simplification — see docs/THEORY.md for
  what this means physically and where it breaks).
"""

from __future__ import annotations

import torch


class WaterDomain:
    """Spectral propagator on an N x N periodic grid of side length L."""

    def __init__(
        self,
        N: int = 192,
        L: float = 0.40,
        depth: float = 0.008,
        g: float = 9.81,
        sigma_over_rho: float = 7.28e-5,
        nu: float = 1.0e-6,
        use_capillary: bool = True,
        device: str = "cpu",
        dtype: torch.dtype = torch.float64,
    ) -> None:
        self.N, self.L, self.depth = N, L, depth
        self.g, self.nu = g, nu
        dx = L / N
        self.dx = dx
        k = 2.0 * torch.pi * torch.fft.fftfreq(N, d=dx, device=device, dtype=dtype)
        KX = k[:, None].expand(N, N)
        KY = k[None, :].expand(N, N)
        self.kmag = torch.sqrt(KX**2 + KY**2)
        cap = (sigma_over_rho * self.kmag**3) if use_capillary else torch.zeros_like(self.kmag)
        omega2 = (g * self.kmag + cap) * torch.tanh(self.kmag * depth)
        omega2[0, 0] = 0.0
        self.omega = torch.sqrt(omega2)
        self.gamma = 2.0 * nu * self.kmag**2  # Lamb's viscous decay rate
        self.device, self.dtype = device, dtype

    # ---------------------------------------------------------------- helpers
    def _w_safe(self) -> torch.Tensor:
        return torch.where(self.omega > 0, self.omega, torch.ones_like(self.omega))

    # ------------------------------------------------------------------ API
    def velocity(self, eta0: torch.Tensor, v0: torch.Tensor, t: torch.Tensor | float) -> torch.Tensor:
        """d eta/dt at time t from the initial state (eta0, v0).

        Exact time derivative of `forward`, damping included:
            v(t) = e^{-gamma t}[-w eta0 sin(wt) + v0 cos(wt)] - gamma eta(t)
        """
        w = self._w_safe()
        E0 = torch.fft.fft2(eta0)
        V0 = torch.fft.fft2(v0)
        damp = torch.exp(-self.gamma * t)
        c = torch.cos(w * t) * damp
        s = torch.sin(w * t) * damp
        eta_t = torch.fft.ifft2(E0 * c + V0 * s / w).real
        return torch.fft.ifft2(-w * E0 * s + V0 * c).real - self.gamma * eta_t

    def forward(self, eta0: torch.Tensor, v0: torch.Tensor, t: torch.Tensor | float) -> torch.Tensor:
        """Surface elevation eta(x, y, t) from the initial state (eta0, v0)."""
        w = self._w_safe()
        E0 = torch.fft.fft2(eta0)
        V0 = torch.fft.fft2(v0)
        damp = torch.exp(-self.gamma * t)
        c = torch.cos(w * t) * damp
        s = torch.sin(w * t) / w * damp
        return torch.fft.ifft2(E0 * c + V0 * s).real

    def reverse(self, eta_t: torch.Tensor, v_t: torch.Tensor, t: float) -> tuple[torch.Tensor, torch.Tensor]:
        """Exact time reversal of the *undamped* system.

        Given the state (eta, v) at time t, return the state at time 0 that
        evolves into it. Damping is intentionally dropped: it is the one part
        of the model that is not reversible (viscosity turns information into
        heat), so reversal under damping would artificially amplify fine
        scales. See docs/THEORY.md.
        """
        w = self._w_safe()
        E = torch.fft.fft2(eta_t)
        V = torch.fft.fft2(v_t)
        c = torch.cos(w * t)
        s = torch.sin(w * t)
        eta0 = torch.fft.ifft2(E * c - V * s / w).real
        v0 = torch.fft.ifft2(w * E * s + V * c).real
        return eta0, v0

    def spectrum_prior(self, eta: torch.Tensor, power: float = 6.0) -> torch.Tensor:
        """Penalty on high-wavenumber content — keeps designs physically smooth.

        Returns mean over modes of (k/k_nyq)^power * |eta_hat|^2 (Parseval-
        normalized), a differentiable scalar.
        """
        k_nyq = torch.pi / self.dx
        w = (self.kmag / k_nyq) ** power
        Eh = torch.fft.fft2(eta)
        return (w * Eh.abs() ** 2).mean().real

    def slope_stats(self, eta: torch.Tensor) -> dict[str, float]:
        etax = (torch.roll(eta, -1, 1) - torch.roll(eta, 1, 1)) / (2 * self.dx)
        etay = (torch.roll(eta, -1, 0) - torch.roll(eta, 1, 0)) / (2 * self.dx)
        s2 = etax**2 + etay**2
        return {
            "slope_max": float(s2.sqrt().max()),
            "slope_rms": float(s2.mean().sqrt()),
            "eta_rms": float(eta.pow(2).mean().sqrt()),
        }
