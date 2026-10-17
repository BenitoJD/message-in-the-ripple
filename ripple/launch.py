"""Launch parameterizations: how a finite mechanical actuation enters the
water. Each one maps a small vector of *physical* parameters to the initial
conditions (eta_0, v_0) — or directly to the surface at any time t — of the
linear wave model. Different realism/DOF trade-offs:

PistonArrayLaunch   A coarse n x n grid of plungers deforms the surface at
                    t = 0 and releases it (eta imprint, v0 = 0).
                    ~24x24 = 576 dof. Realizable with a plunger bed or a
                    synchronously fired drop-on-demand nozzle plate.

VelocityArrayLaunch The same grid imprints a downward *velocity* field
                    (v0 imprint, eta_0 = 0) — the linearized model of a
                    simultaneous droplet barrage hitting the surface.

Both are torch modules: parameters are trainable, and the whole launch ->
wave -> caustic chain is differentiable end to end.
"""

from __future__ import annotations

import torch
import torch.nn.functional as F

from .waves import WaterDomain


class _ArrayLaunch:
    def __init__(self, domain: WaterDomain, n_coarse: int = 32, amp_max: float = 1.2e-3, smooth_sigma_cells: float = 0.35) -> None:
        self.domain = domain
        self.n_coarse = n_coarse
        self.amp_max = amp_max
        self.sigma = smooth_sigma_cells * (domain.N / n_coarse)
        self.A = torch.zeros((n_coarse, n_coarse), dtype=domain.dtype, device=domain.device, requires_grad=True)
        # small bias so tanh(0)=0 start does not sit exactly at a saddle
        with torch.no_grad():
            self.A.normal_(0, 0.05)

    def amplitude_field(self) -> torch.Tensor:
        """Bounded actuator amplitudes upsampled to the sim grid (smooth)."""
        a = self.amp_max * torch.tanh(self.A)
        up = F.interpolate(a[None, None], size=(self.domain.N, self.domain.N), mode="bicubic", align_corners=True)[0, 0]
        if self.sigma > 0:
            from .optics import gaussian_blur2d

            up = gaussian_blur2d(up, self.sigma)
        return up


class PistonArrayLaunch(_ArrayLaunch):
    """Surface displacement imprint at t = 0 (plungers)."""

    kind = "eta"

    def initial_state(self) -> tuple[torch.Tensor, torch.Tensor]:
        return self.amplitude_field(), torch.zeros((self.domain.N, self.domain.N), dtype=self.domain.dtype, device=self.domain.device)

    def imprint(self) -> torch.Tensor:
        return self.initial_state()[0]

    def surface_at(self, t: torch.Tensor | float) -> torch.Tensor:
        eta0, v0 = self.initial_state()
        return self.domain.forward(eta0, v0, t)


class VelocityArrayLaunch(_ArrayLaunch):
    """Downward-velocity imprint at t = 0 (droplet barrage)."""

    kind = "velocity"

    def initial_state(self) -> tuple[torch.Tensor, torch.Tensor]:
        return torch.zeros((self.domain.N, self.domain.N), dtype=self.domain.dtype, device=self.domain.device), self.amplitude_field()

    def imprint(self) -> torch.Tensor:
        return self.initial_state()[1]

    def surface_at(self, t: torch.Tensor | float) -> torch.Tensor:
        eta0, v0 = self.initial_state()
        return self.domain.forward(eta0, v0, t)
