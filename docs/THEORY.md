# Theory

This document states exactly what is being simulated, the approximations used,
and the scaling law that tells you whether a given tray/throw/amplitude
combination can produce a caustic image at all. Everything here is implemented
in `ripple/` and checked by `tests/test_sanity.py`.

---

## 0. The chain

```
finite mechanical launch  ->  initial state (eta_0, v_0)
        |                                   |
        |  free linear wave propagation     |  (no further actuation)
        v                                   v
   surface at time t*  eta(x, y, t*)  ->  refraction at the air/water
        |                                   interface, then at the flat
        |                                   tray bottom
        v
   screen intensity I(x, y)  =  density of refracted rays
```

The claim under test is the middle arrow: **the image is produced by free
motion**, not by the launch imprinting the glyph. The controls in
`scripts/demo_array.py` measure this directly (`corr` at `t = 0` must be low).

---

## 1. Water waves

### 1.1 Dispersion relation

For a layer of quiescent depth `h` with gravity `g` and surface tension
`sigma`, linear modes `exp(i(k.x - omega t))` obey

```
omega(k)^2 = ( g k + (sigma/rho) k^3 ) * tanh(k h),      k = |k|
```

with `sigma/rho = 7.28e-5 m^3/s^2` for clean water at 20 C. We keep the
capillary term: over a 40 cm tray at 2 mm resolution the Nyquist wavelength is
~4 mm, and capillarity dominates below ~17 mm — the same band that focuses
light (section 2.3), so dropping it would change the answer.

### 1.2 Closed-form propagation (and why that matters)

The linearized problem is a pair of first-order equations in time,

```
d/dt [eta]   [ 0      1 ] [eta]
     [v  ] = [ -L     0 ] [v  ],        L = omega^2  (in Fourier space)
```

so each Fourier mode is a rotation:

```
eta_hat(k, t) = eta_hat_0 cos(w t) + v_hat_0 sin(w t)/w
v_hat(k, t)   = -w eta_hat_0 sin(w t) + v_hat_0 cos(w t)
```

This is exact for the linear model at *any* `t` — no time stepping, no CFL
condition. One forward evaluation of the entire wave simulation at `t*` costs
two FFTs. That is what makes end-to-end differentiable inverse design practical
(`ripple/waves.py::WaterDomain.forward`).

### 1.3 Damping, and the arrow of time

Viscosity enters as a per-mode decay

```
gamma(k) = 2 nu k^2,        nu = 1e-6 m^2/s (kinematic)
```

so `eta_hat(t) -> eta_hat(t) * exp(-gamma t)`. Damping is the one piece of the
model that is *not* time-reversal symmetric: high wavenumbers decay fastest,
which is precisely the information you would need to reconstruct the launch
state. `WaterDomain.reverse` therefore inverts the **undamped** propagator and
is exact only in the inviscid limit:

* `tests/test_sanity.py::test_time_reversal_roundtrip` — inviscid round trip,
  error `1.2e-16`.
* `tests/test_sanity.py::test_viscosity_is_the_arrow_of_time` — with
  `nu = 1e-6`, reversal of a 0.5 s evolution is inexact (relative error ~0.4),
  as it must be.

In practice this bounds how far back a reveal can be designed: for a
`t* = 0.55 s` reveal, modes with `gamma t* ~ 1` (wavelengths below ~1 mm) have
already lost their information. The design pipeline never relies on reversal
alone — stage C optimizes the constrained launch directly through the *damped*
forward model.

### 1.4 Numbers for the default rig

The design pipeline uses a 2D wave field whose curvature structure determines the
optics. `scripts/probe_dynamics.py` prints the relevant budgets; with the
default configuration (`h = 8 mm`):

| quantity | value |
|---|---|
| shallow-water speed `sqrt(g h)` | 0.28 m/s |
| phase speed at 20 mm wavelength | ~0.24 m/s |
| minimum phase speed (gravity-capillary) | ~0.18 m/s at ~17 mm |
| tray crossing time | ~1.4 s |
| reveal instant `t*` used in results | 0.55 s |

Because `c(k)` varies by tens of percent across the centimetre band, structure
decorrelates in a few hundred milliseconds — that is the physical origin of the
*fleeting* reveal (measured window in the results: ~150 ms).

---

## 2. Optics: how a surface becomes an image

### 2.1 The refraction chain

Light arrives collimated from above. At the wavy interface the ray refracts
(air -> water), crosses the water column, refracts again at the flat tray
bottom (water -> air), and lands on a screen `gap` below the bottom. Each
surface cell carries flux `dx^2`; the screen intensity is the density of
landing points, i.e. `I ∝ 1/|det J|` where `J` maps surface position to screen
position. Bright caustic lines are folds of that map, where `det J -> 0`.

Implementation (`ripple/optics.py`): vector Snell's law at both interfaces,
then bilinear **splatting** of equal-flux rays onto the screen grid. Splatting
weights depend smoothly on the landing positions, so `dI/d(eta)` exists and the
whole chain — launch parameters to screen — is one autodiff graph.

### 2.2 The deflection law

For a surface slope `s = |grad eta|` (small-angle regime), the ray leaves the
top interface at `theta_w ~ s/n` relative to the tilted normal, i.e.
`s(1 - 1/n)` relative to vertical. Refraction at the flat bottom undoes the
index factor in angle, so in air the deflection is amplified:

```
alpha ~ (n - 1) * s
```

The lateral displacement at the screen is therefore

```
d(s) = depth * (1 - 1/n) * s  +  gap * (n - 1) * s
     = (n - 1) * L_eff * s,
L_eff = gap + depth * (1 - 1/n) / (n - 1)      [= gap + 0.75 * depth for n = 1.331]
```

Note the asymmetry: the *air* gap counts fully, the water column only at ~75%.
Raising the tray is the cheap way to buy caustic strength.

### 2.3 Caustic strength: when does a ripple focus?

Rays from a region of curvature `lap(eta)` converge when the accumulated
deflection across the feature reaches the feature size. That gives the single
useful design number:

```
chi = (n - 1) * L_eff * lap(eta)        [dimensionless]
chi << 1 : barely any focusing (flat, washed-out image)
chi ~  1 : strong folds, bright lines
chi >> 1 : rays cross well before the screen; multiple images, speckle
```

Measured in this repo: `chi = 0.005` -> 0.5 % intensity contrast (invisible),
`chi ~ 0.12` -> ~12 % contrast (a clearly visible, soft image), and
`chi ~ 10` -> a dense caustic network whose finest folds the source blur then
averages away. So contrast rises roughly with `chi` while `chi <~ 1` and
saturates beyond it; the useful design band is `chi ~ 0.1-1`. Because the
obvious objective (Pearson correlation) is contrast-blind, `chi` and contrast
must be reported next to it — see section 3 and `scripts/probe_sampling.py`.

Equivalently, the required surface curvature is

```
lap(eta) ~ 1 / ((n - 1) * L_eff).
```

With the default `gap = 12 cm`, `L_eff = 0.126 m` and
`lap(eta) ~ 24 /m`. For a ripple `eta = a sin(kx)` this means
`k^2 a ~ 24`:

| wavelength | amplitude needed for strong focusing |
|---|---|
| 10 mm | ~0.06 mm |
| 20 mm | ~0.25 mm |
| 40 mm | ~1.0 mm |
| 80 mm | ~4 mm (beyond the linear regime) |

So the centimetre band is exactly the sweet spot, and this is why the model
keeps capillarity and why the actuator grid pitch (~12 mm) is well matched to
the physics. Big, slow, decimetre-scale waves cannot paint a sharp image at a
12 cm throw no matter how large their amplitude; they mostly just tilt the
image. (An earlier iteration of the dome test in `tests/test_sanity.py` asked a
5 cm-wide bump to focus and failed for exactly this reason.)

### 2.4 Rendering details that matter

* **Grid alignment.** The screen pixel grid is aligned with the tray cell grid
  (`screen_scale = 1.0`) and one ray is cast per cell (`rays_per_cell = 1`).
  Then a flat surface maps every ray exactly onto its own pixel: an exactly
  uniform image with no resampling beat. Supersampling (`rays_per_cell > 1`)
  smooths folds but adds a visible fine grid texture where the sub-pixel ray
  lattice beats against the pixel lattice; results here use `rays_per_cell = 1`.
* **Source size.** `blur_px` stands in for the finite angular size of the light
  source. A perfectly collimated point source would give infinitely sharp (and
  unphysically noisy) folds; a 12 cm throw with a 5 cm LED panel implies a
  blur of order a pixel.
* **Geometric optics only.** Diffraction is neglected. Fine for centimetre
  features: the Fresnel number is enormous (`feature^2/(lambda_light * L_eff)
  ~ 1e8`).
* **The glass bottom is ignored as a slab.** Two parallel interfaces do not
  change ray directions, only shift them laterally by a sub-millimetre amount.

### 2.4 What the throw actually buys (measured)

In a design with a required minimum contrast, the contrast requirement — not the
optimizer's preference — sets the curvature budget: every successful run in
`results/` lands at `chi ~ 0.10-0.12` with 10-13 % contrast. The throw then
trades against *required curvature*: doubling `L_eff` halves the curvature
needed for the same `chi`, and the freed dynamic range goes into shape fidelity.
Measured: the same target at 12 cm and 20 cm throws gave `corr = 0.812` and
`0.866` at the same contrast and `chi`, while the free-surface (no-dynamics)
reference reached `0.817` only by using `chi ~ 12` — a hundred times more
curvature, i.e. a lenslet-like surface in the speckle regime.

Conversely, when the hardware cannot produce the required curvature, the design
degrades in one of two ways — both visible in the README table at 8x8
actuators: an invisible but well-correlated ripple (`corr 0.71`, 0.6 %
contrast), or a bright but shapeless pattern (`corr 0.10`, 15 % contrast).

---

## 3. The inverse problem

Three stages, in increasing physical honesty. All use the same differentiable
optics, and Adam on the correlation loss

```
loss = -corr(I(eta), target)  +  w * spectrum_prior(eta)  +  slope_guard(eta)
```

The Pearson correlation is scale- and offset-invariant, which is the right
choice: caustics have no meaningful absolute brightness, only structure.

**Stage A — static design** (`optimize_static`). The surface at `t*` is a free
parameter field; no wave dynamics. This is the classical computational-caustics
problem and serves as an optics sanity check, and as the reference for what the
*ideal* surface can do.

**Stage B — time reversal** (`time_reverse`). Take the stage-A surface with
`v* = 0` (the wave field passes *through* its designed shape, momentarily at
rest) and invert the undamped propagator to get the launch state at `t = 0`
that would evolve into it. This is an existence proof for the wave-constrained
version — but the resulting field is generally not something hardware can
imprint.

**Stage C — constrained launch** (`optimize_launch`), the actual research
question. Parameterize a *finite* launch (a coarse grid of bounded actuators,
imprinting either surface displacement or downward velocity at `t = 0`), then
optimize its parameters end-to-end through propagation and optics. Two things
make this tractable:

1. the propagator is closed-form, so the gradient passes through `t*` exactly;
2. stage B provides a *warm start*: project the time-reversed ideal field onto
   the actuator grid ("reverse-and-project", `regress_launch`), which measures
   how much of the ideal launch the hardware can express (reported as a cosine
   similarity).

Legibility at other times is never rewarded, so the reveal is a consequence of
the free evolution, and the dissolve is not designed — it is dispersion.

---

## 4. What the model deliberately ignores

| effect | status | why it matters / when it breaks |
|---|---|---|
| Nonlinearity (steepness) | ignored | `slope_max ~ 0.35` in results is at the edge of linear theory; real steep ripples steepen, generate harmonics, and break reversibility |
| Viscous damping in reversal | ignored in `reverse` | bounded `t*`, see 1.3 |
| Boundary reflections | periodic domain | a real tray needs absorbing beaches, or a `t*` short enough that the wavefront has not returned |
| Bottom/contact-line physics, meniscus | ignored | the actuator footprint is modelled as a smooth Gaussian-ish imprint |
| Splash, crater collapse, droplet coalescence | ignored | real droplet impacts are violent and nonlinear; the velocity-imprint model is the linear idealization |
| Evaporation, temperature, surface films | ignored | change `sigma`, add drift |
| Partial coherence, polarisation, absorption | ignored | geometric intensity only |
| Camera response, stray light, screen texture | ignored | flat-field with still water before trusting any measurement |
| Diffraction of light | ignored | fine for mm-cm features, wrong for micron features |

## 5. Falsifiable predictions for a physical rig

From the default configuration:

1. With still water, the screen is uniform; the imprint alone scores ~0 (in sim,
   `corr(t = 0) = -0.15`, i.e. no accidental resemblance).
2. A tuned finite launch produces `corr > 0.5` against the target at one
   instant, with a legibility window of ~150 ms, and no legibility at other
   times.
3. Returning the launch to the identical initial state reproduces the frame
   bit-for-bit in simulation; physically, frame-to-frame repeatability is
   limited by launcher jitter and surface contamination, and is the first thing
   to measure (see `experiments/PROTOCOL.md`).
4. Halving the throw (`gap = 6 cm`) roughly halves `chi` and should visibly
   soften the caustic; doubling it should break the image into speckle.

If (2) fails while (1) holds, the fault is in the launcher's ability to express
the reversed field — the fidelity number from stage B tells you how much was
lost, and re-running stage C at a coarser actuator grid quantifies the
sensitivity.
