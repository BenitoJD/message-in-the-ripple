# Announcement copy (X / Twitter)

Drafts for posting this project. All lengths verified against X's rules (a link
counts as 23 characters; media does not count). X Premium allows long posts, so
the long-form drafts below are written for that; the single posts and thread are
kept for quote-posts and replies.

## Posting plan

| slot | media | why |
|---|---|---|
| main post | `results/flower8/reveal.gif` | one moving image tells the whole story; it loops twice, so "same splash, same image" reads without explanation |
| reply / second image | `results/contrast_trap.png` | the honest-science beat: the same frame stretched, honest, and zoomed to the real 0.6 % ripple |
| optional | `results/outline/reveal_timeline.png` | the 28-frame story in one glance |
| optional | `results/flower_targets.png` | shows the target is a knob (5, 6, 8 petals) |

**Alt text**

* `flower8/reveal.gif` — Animation of 28 simulated caustic frames. Chaotic networks of light assemble into a crisp 8-petal flower shape at one instant, then dissolve back into chaos; the sequence repeats once.
* `contrast_trap.png` — Three panels of the same simulated caustic frame. Left, min-max stretched, showing an apparent image. Middle, shown on a fixed plus/minus 25 percent brightness window, appears completely flat uniform gray. Right, zoomed to plus/minus 0.6 percent, reveals the faint heart-shaped structure that is really there.
* `outline/reveal_timeline.png` — Contact sheet of 28 caustic frames; one frame at 0.55 seconds shows a bright heart outline, the surrounding frames show unrelated caustic networks.
* `flower_targets.png` — Four panels of target shapes: 5, 6 and 8-petal flower outlines and a filled 6-petal flower.

---

# LONG-FORM POST A — recommended (4826 chars)

```
One splash of water. Then you walk away.

Half a second later the ripples bend the light into an 8-petal flower on the screen below. It holds for 11 milliseconds. Then the water forgets.

We simulated it. Nobody has built it. And it fooled us once, badly.

THE SETUP

A shallow tray of water with a clear bottom, a lamp above it, a matte screen below. Every ripple acts like a tiny lens, so the screen shows caustics — the same moving net of light you see on the bottom of a swimming pool.

Normally that net is noise. The idea here: poke the water once, in one carefully chosen pattern, and then never touch it again. If the poke is right, the freely evolving wave field is shaped — at one instant — like the picture you want, and the light does the drawing.

Measured, for the flower: the poke by itself scores 0.06 against the target. The freely evolved water at t* = 0.55 s scores 0.83.

The image is not in the poke. It is assembled by the water's own motion.

WHY THIS IS HARD

You cannot tell water "draw a flower". Thousands of coupled ripples, all dispersing: different wavelengths travel at different speeds, so any pattern smears itself out. The predicted legible window is 11 ms — one frame at 90 fps, if you are lucky.

Two tricks make it tractable:

1. Run time backwards. Ignoring viscosity, the wave equation is reversible, so we propagate the target picture backwards from t* to t = 0 and obtain an ideal splash. Round-trip check: error 1.2e-16.

2. Project, then optimize. That ideal splash is not something hardware can produce, so we fit it onto a 32x32 actuator grid (74-96% shape fidelity), then optimize the actuators end to end.

"End to end" is the interesting part: the gradient of "how much does this look like the flower" flows backwards through the wave propagation and through the refraction, into every single actuator. The propagator is closed-form — two FFTs per instant — and the optics is a differentiable ray trace. The entire chain is one autodiff program.

WHAT WE MEASURED (all in simulation)

• 8-petal flower: correlation 0.83, screen brightness modulation 12.8%, visible for 11 ms
• 6-petal flower: 0.82 and 12.6%
• heart outline: 0.81 (0.87 with a longer throw)
• solid filled heart: 0.41

Caustics love lines and hate filled shapes. Outlines of flowers and hearts come out crisp; a solid shape comes out mushy.

Hardware floor: 64 actuators fail, 256 work, 1024 give the numbers above.

And it is deterministic — two evaluations of the same splash are bit-identical. That matters, because the entire conceit is "repeat the splash and the image returns at the same moment."

HOW IT FOOLED US

The first version of this pipeline reported correlation 0.79 and rendered a gorgeous heart.

Then we checked the actual brightness modulation: 0.5%. And the focusing parameter: 0.005, meaning no focusing whatsoever.

The "image" was an invisible shimmer. Our display code had been min-max normalizing each frame, which stretches a 0.5% ripple into full black-and-white. The figure below is that exact frame: stretched it looks like a picture, on an honest fixed window it is flat gray, and only at ±0.6% does the real structure appear.

Root cause: Pearson correlation is contrast-blind. It scores shape, not visibility — so the optimizer happily converged on structure no eye could see.

Fixes: a minimum-contrast term in the loss; contrast and focusing reported next to every correlation; and every committed image shown on a fixed ±25% window. The numbers went down and became real. The diagnostic that caught it is still in the repo as a tripwire.

STILL UNKNOWN

Simulation only. Linear waves, a periodic box instead of walls, an idealized launcher with no splash or crater physics, geometric optics, no camera. The wave-constrained designs are comfortably linear (surface slopes ~0.09), but that is a model result, not a measurement.

Prior art: static computational caustics is a mature field. Water-wave time reversal is real — Bacot et al., Nature Physics 2016 — but it refocuses waves onto a source rather than drawing an image. Water displays drive the water continuously rather than once. The combination — one finite launch, free propagation, a structured image, solved inversely — I could not find. If you know of it, please tell me.

WHY BUILD IT

The rig is cheap: tray, LED panel, matte screen, phone camera, microcontroller — roughly $150-500. The reveal is a visible ~13% brightness modulation, and the design pipeline runs on a CPU in minutes.

Repo: theory, the focusing scaling law, the bill of materials, the bench protocol, and the negative results.

github.com/BenitoJD/message-in-the-ripple

The next step is not the actuators. It is one droplet and a camera: measure the dispersion of the actual tray, and find out whether the predicted 0.55 s timeline is real.
```

---

# LONG-FORM POST B — extended, for a technical audience (7859 chars)

```
One splash of water. Then you walk away.

Half a second later the ripples bend the light into an 8-petal flower on the screen below. It holds for 11 milliseconds. Then the water forgets.

We simulated it. Nobody has built it. Here is the whole story, including the way the project fooled us first.

1. THE IDEA

A shallow tray, clear flat bottom, lamp above, matte screen below. Ripples are lenses, so the screen shows caustics — the light-net on the bottom of a swimming pool.

Now: instead of driving the water continuously (what fountain displays do), poke it once and let go. The disturbance spreads, interferes, disperses — and if the poke was chosen correctly, the surface at one instant is the right shape for the light to draw a picture. Then the picture dissolves on its own.

The research question is uncomfortable: can a finite, buildable poke do this, or does it need more control than hardware can offer?

2. WHY THE PICTURE IS NOT IN THE POKE

We measured it. For the 8-petal flower, the splash's own caustic at t = 0 scores 0.06 against the target. The freely evolved surface at t* = 0.55 s scores 0.83. An untuned random launch scores 0.00.

So the image genuinely comes from the propagation, not from the imprint. This is the control that makes the whole thing interesting rather than a printing trick.

3. WHY IT'S HARD

Water disperses. Modes obey

  w^2 = (g k + (sigma/rho) k^3) tanh(k h)

with gravity and capillarity both mattering at centimetre scales. Different wavelengths travel at different speeds, so a pattern decorrelates in a few hundred milliseconds. Measured legible window for the flower: 11 ms; for the softer filled-heart target, 51 ms.

The second hardness is the inverse problem: you cannot tell water "draw a flower".

4. HOW WE SOLVED THE INVERSE PROBLEM

Three stages, each more physically honest than the last.

A. Static design. Let the surface at t* be arbitrary and optimize it so its caustic is the target. This is classical computational caustics (Schwartzburg et al. 2014 and successors). It validates the optics and gives a reference: corr 0.87 for the flower outline, 0.47 for the filled heart.

B. Time reversal. The undamped wave equation is reversible. Put the designed surface at t* with zero velocity (the field passes through its shape, momentarily at rest), then propagate backwards to t = 0. The result is an ideal splash that would evolve into the picture. Inviscid round-trip error: 1.2e-16. Under viscosity reversal is inexact (~0.3 relative error at 0.5 s), which is the physical arrow of time and the reason we do not rely on reversal alone.

C. Reverse-and-project, then optimize. The ideal splash is not buildable. So we fit it onto a coarse actuator grid (cosine similarity 0.74-0.96 depending on target), then optimize the actuator amplitudes end to end.

End to end means the gradient of image quality at t* flows back through the wave propagation and the ray-traced refraction into every actuator. The propagator is closed-form in time (two FFTs per instant), the optics uses vector Snell refraction with differentiable bilinear splatting, so the entire chain is a single autodiff program. A run is minutes on a laptop CPU.

5. WHAT WE MEASURED

  target                        actuators   corr@t*   contrast   window
  8-petal flower outline        32x32       0.833     12.8%      11 ms
  6-petal flower outline        32x32       0.824     12.6%      11 ms
  heart outline (20 cm throw)   32x32       0.866     12.7%      11 ms
  heart outline (12 cm throw)   32x32       0.812     11.9%      11 ms
  filled heart                  32x32       0.413     11.6%      51 ms
  filled heart                  16x16       0.402     10.2%      51 ms
  filled heart                  8x8         0.705      0.6%     405 ms
  filled heart, 8x8, penalty x10 8x8        0.104     14.8%     557 ms

Patterns worth reading off that table:

• Caustics love lines, hate filled shapes. Outlines of flowers and hearts: 0.81-0.87. Solid hearts: 0.41. Fold lines are what a caustic wants to make anyway.

• There is an actuator floor. 64 actuators cannot express the required surface curvature. Asked for shape alone, that grid reports a flattering 0.705 at 0.6% contrast — invisible. Enforce visibility ten times harder and it produces a bright 14.8% pattern at 0.104 — light, but not the glyph. 256 actuators work; 1024 work better.

• Throw buys fidelity, not brightness. Going from a 12 cm to a 20 cm screen distance raised correlation from 0.812 to 0.866 at the same contrast and the same focusing parameter. The visibility requirement pins the curvature budget; extra throw spends it on shape.

• It is deterministic. Two evaluations of the same launch are bit-identical.

6. HOW IT FOOLED US

The first version reported correlation 0.79 and rendered a beautiful heart.

Then we checked the brightness modulation: 0.5%. And the focusing parameter chi: 0.005 — no focusing at all. The "image" was an invisible shimmer, and our own display code had been min-max stretching every frame, turning a 0.5% ripple into full black-and-white.

The failure mode is general and worth naming: Pearson correlation is contrast-blind. It measures shape agreement, not visibility, so an optimizer scored by correlation will happily design something no eye can see.

What we changed: a minimum-contrast term in the loss, contrast and the focusing parameter reported next to every correlation, and every committed image shown on a fixed ±25% window. The numbers dropped and became real.

We also verified the surviving result is not a rendering artifact: re-rendering the same surface from 1 to 16 rays per cell, with correct pixel-area integration, moves correlation only from 0.809 to 0.800 and contrast from 0.118 to 0.116.

7. THE PHYSICS IN ONE PARAGRAPH

A surface slope s deflects a vertical ray by about (n-1)s in air, giving a lateral displacement (n-1) L_eff s at the screen, where L_eff = gap + 0.75 x depth. Focusing therefore scales with one dimensionless number:

  chi = (n-1) L_eff rms(laplacian of eta)

chi below ~0.01 is an invisible ripple; 0.1 to 1 is a visible image; far above 1 is speckle that blur washes out. With a 12 cm throw, chi ~ 0.1 needs centimetre-scale ripples with fractions of a millimetre of amplitude — exactly the gravity-capillary band, and why decimetre waves cannot paint a sharp image at a table-top throw.

8. WHAT IS STILL UNKNOWN

Simulation only. Linear waves in a periodic box (no wall reflections), an idealized launcher (no splash or crater physics), geometric optics (no diffraction), no camera, no measurement. The wave-constrained designs sit comfortably inside linear theory (surface slopes ~0.09), but that is a model result.

Prior art: static computational caustics is mature; water-wave time reversal is real (Bacot et al., Nature Physics 2016) but refocuses onto a source rather than drawing an image; water displays drive the water continuously. The four-way combination — one finite launch, free propagation, a spatially structured image, designed inversely — I could not find. If you know it exists, please tell me.

9. WHY IT MIGHT BE WORTH BUILDING

The rig is cheap ($150-500): tray, LED, matte screen, phone camera, microcontroller. The reveal is a visible ~13% brightness modulation, an order of magnitude above what a phone camera resolves. The design pipeline is CPU-only and takes minutes.

The next step is not the actuator bed. It is one droplet and a camera: measure the tray's actual dispersion, and see whether the predicted timeline is real. If the dispersion matches, the rest is engineering. If it does not, the idea dies cheaply.

Everything is here — theory, scaling law, bill of materials, bench protocol, negative results, and the figures:

github.com/BenitoJD/message-in-the-ripple

Corrections, prior art, and collaborators all welcome.
```

---

# SINGLE POST (if you want a short one instead)

**A, numbers-forward (253 chars)**

```
Splash a tray of water once, then walk away.

0.55 s later the ripples bend light into an 8-petal flower on the screen below — for 11 milliseconds — then dispersion erases it.

Simulated, not built. Code + plan: github.com/BenitoJD/message-in-the-ripple
```

**B, punchier (220 chars)**

```
One splash. No moving parts.

Half a second later the water draws an 8-petal flower in light — and 11 ms after that, it's gone.

Nobody has built this yet. We only simulated it.

github.com/BenitoJD/message-in-the-ripple
```

---

# THREAD (6 posts)

**1/6** — 221 chars

```
One splash. Then nothing.

0.55 s later, the ripples in a tray of water bend light into an 8-petal flower on the screen below. It lasts 11 milliseconds.

Then dispersion erases it.

We simulated it. Nobody has built it. 🧵
```

**2/6** — 236 chars

```
Why this is strange: the picture is NOT in the splash.

The splash alone scores 0.06 against the flower. The freely evolving water at t=0.55 s scores 0.83.

The image is assembled by the water's own motion. We only chose how to poke it.
```

**3/6** — 229 chars

```
You can't tell water "draw a flower".

So we ran the wave equation backwards for an ideal splash, then optimized a 32×32 actuator grid until the forward simulation produced the flower.

Waves + light = one differentiable program.
```

**4/6** — 165 chars

```
It's also fast. Ripples of different sizes travel at different speeds, so the pattern smears itself out.

Measured legible window: 11 ms — about one frame at 90 fps.
```

**5/6** — 268 chars

```
How much hardware does it need? We tested:

• 64 actuators — fails: either an invisible shimmer, or a bright blob with no shape
• 256 — works, corr 0.40
• 1024 — corr 0.83 at 12.8% contrast

Caustics love lines and hate filled shapes: flowers > letters > solid hearts.
```

**6/6** — 263 chars

```
Honest status: simulation only. Linear waves, periodic box, no wall reflections, idealized launcher. No tray built.

Repo has the theory, the scaling law, the BOM and the bench protocol — plus prior art I could not find:

github.com/BenitoJD/message-in-the-ripple
```

---

## Notes

* **The first ~280 characters are the whole pitch** — that is all X shows before
  "Show more". Both long drafts open with the splash, the 11 milliseconds, and
  the admission that it is unbuilt.
* **Keep "nobody has built it".** It is honest and it is the more interesting
  claim: an unbuilt idea with a shopping list and a test protocol invites
  collaborators; an overclaim invites a correction.
* **The contrast trap is the strongest section** for any audience that builds
  things with optimizers. Correlation is contrast-blind; the repo now reports
  contrast and the focusing parameter next to every correlation, and the
  diagnostic that caught it (`scripts/probe_sampling.py`,
  `scripts/contrast_trap_figure.py`) is part of the codebase.
* **The failure case is the best technical reply-post**: 64 actuators -> either
  corr 0.71 at 0.6 % contrast (invisible) or 14.8 % contrast at corr 0.10
  (shapeless). A clean illustration of an actuator floor.
* If someone replies with prior art, that is a win. `docs/RESEARCH_GAP.md`
  already asks for it.
* Hashtags optional; `#physics #optics` is plenty. No stuffing.
