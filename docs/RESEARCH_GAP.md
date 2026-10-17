# Where this sits: prior art and the gap

*Written 2026-10. This is a first-pass survey by the authors of this repository,
not an exhaustive literature review. It is deliberately conservative: every
claim of "no precedent" below is a claim about what we could find, and
corrections are welcome as issues or pull requests.*

---

## 1. Static caustic design (the closest engineering lineage)

Designing a *static* refracting surface so that it paints a prescribed image is
a solved, active field:

* **Schwartzburg, Testuz, Tagliasacchi, Pauly — "High-contrast computational
  caustics", ACM TOG 33(4), 2014.** The canonical formulation: optimize a
  height field so the light it refracts forms a target image, using a
  continuous, differentiable caustic model. Direct ancestor of stage A in this
  repo.
* **Yue, Iwasaki, Chen, Dobashi, Nishita — "Poisson-based continuous surface
  generation for goal-based caustics", ACM TOG 33(3), 2014.** Produces smooth,
  fabricable surfaces (mirrors/lenses) that reproduce an image.
* **Zhou, Sun, Deng, Zhang — "Computational Caustic Design for Surface Light
  Source", IEEE TVCG, 2025** ([arXiv:2511.09361](https://arxiv.org/abs/2511.09361),
  doi:10.1109/TVCG.2025.3633081). Current state of the art, closing the gap
  between idealized point/parallel sources and real extended sources.

**All of this is static.** The surface is designed once, fabricated, and the
image is whatever that fixed surface always produces. In our problem the
surface is a *moving* water wave: there is no artefact to fabricate, the
"surface design" must be reachable by free propagation from a single launch,
and the image exists for a moment.

## 2. Water-wave time reversal (why this is not obviously impossible)

The reversibility of lossless wave equations is a classical tool:

* **Bacot, Labousse, Eddi, Fink, Fort — "Revisiting time reversal and
  holography with spacetime transformations", Nature Physics 12, 972 (2016)**
  ([arXiv:1510.01277](https://arxiv.org/abs/1510.01277),
  doi:10.1038/nphys3810). *Experiments on water waves*: a sudden change of
  effective gravity creates a "time mirror" and the waves refocus at the
  original source.
* **Ducrozet, Fink, Chabchoub — "Time-Reversal of Nonlinear Waves —
  Applicability and Limitations", Phys. Rev. Fluids 1, 054302 (2016)**
  ([arXiv:1603.05831](https://arxiv.org/abs/1603.05831),
  doi:10.1103/PhysRevFluids.1.054302). Numerical high-order spectral study of
  hydrodynamic time reversal, quantifying where nonlinearity and dispersion
  break it.
* The broader **time-reversal mirror** programme in acoustics and optics (Fink
  and successors; e.g. Mounaix et al., Nat. Commun. 11, 5615 (2020)) established
  the principle that a complex medium can be made to deliver a chosen
  spatiotemporal focus.

These prove the *mechanism* — free water-wave propagation really can be made to
concentrate energy at a chosen place and time — but the demonstrated target is a
**point-like refocus at the source**, not a spatially structured image, and the
implementations use a *time boundary* or a *reversed recording* rather than a
designed finite launch.

## 3. Water as an optical and display element

* Caustics from a wavy water surface (pool floors, "caustic art") are textbook
  geometric optics, and are the phenomenon this project deliberately exploits.
* Active water **displays** exist commercially and in research — water screens
  and wave fountains (e.g. large-scale fountain shows), ultrasonic/flow-based
  water displays, and wave machines in tanks. These either project light *onto*
  water or drive the water continuously to sculpt a shape; they do not use a
  single finite launch whose *free* evolution produces a caustic image.
* Programmed **deterministic focusing** of wave energy in physical tanks is
  standard ocean engineering (design-wave / "NewWave" theory, Tromans et al.
  1991, and the ensuing focused-wave-group literature): tanks are routinely
  driven so that wave components superpose at a chosen point and time. The
  target is an extreme wave event, not an image.

## 4. The gap, stated narrowly

> **Transient inverse design of a caustic image under a finite mechanical
> launch.**

Specifically, all four of the following together:

1. the actuation is a **single, finite launch** (imprint, then hands off — no
   continuous per-pixel control);
2. the shaping mechanism is **free wave propagation** (the image is assembled by
   dispersion and interference, then dissolves);
3. the target is a **spatially structured image** (a glyph), not a point focus
   or an energy maximum;
4. the design is **inverse and validated forward** (we solve for the launch, not
   merely observe an interesting pattern).

We found no work that does all four. The nearest neighbours are static caustic
design (1 missing, 2 missing), time-reversal refocusing (3 missing), and
active water displays (1 missing, 2 missing).

## 5. What would count as prior art we missed

Things that would move the needle if they exist:

* a water-wave time-reversal experiment whose target is a *pattern* rather than
  a focus (e.g. acoustic holography transplanted to a tank);
* caustic-based water displays driven by a one-shot actuator pulse;
* transient/aperiodic computational caustics where the optic evolves in time
  (optics literature rather than graphics);
* "inverse dispersion" or "dispersion engineering" work that shapes a wave
  packet's spatial profile at a chosen time rather than compressing it in space
  or time.

Please open an issue with a citation if you know of one — the honest status of
this project is *unproven and possibly already done*.

## 6. What this repository actually establishes

Not that the physical experiment works. Only:

* that the forward physics (linear gravity-capillary waves + Snell refraction)
  can be posed as one differentiable program and optimized end-to-end;
* that in that model a *constrained finite launch* can produce a legible,
  transient caustic image (numbers in the README), with controls showing the
  imprint alone does not contain the image;
* that the ideal (time-reversed) launch is expressible by a modest actuator grid
  to within a measured cosine similarity — the key feasibility number for
  hardware;
* what the physical rig would have to look like, and which measurements would
  falsify the idea (`docs/HARDWARE.md`, `experiments/PROTOCOL.md`).
