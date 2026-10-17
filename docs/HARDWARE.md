# Physical rig: what to build, and what it would take

This is a plan, not a build log. Nothing here has been constructed or measured;
the numbers are the ones the simulation says to aim for, with the reasoning in
`docs/THEORY.md`.

---

## 1. Geometry

```
            LED panel (diffused, ~5000 K)          <- collimated-ish light from above
                 |
                 v
   ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~ ~         <- water surface eta(x,y,t), h = 8 mm mean depth
  +------------------------------------------+
  |  tray, clear flat bottom (glass/acrylic)  |     <- 40 x 40 cm inner, walls with absorbing beaches
  +------------------------------------------+
                 |  air gap  gap = 12 cm
                 v
        matte screen (paper / ground acrylic)      <- the reveal is viewed here
                 |
                 v
        camera (below, or via 45 deg mirror)       <- 60-240 fps, fixed focus, manual exposure
```

Everything above the surface should be matte black except the light path; stray
light is the main enemy of a low-contrast caustic image.

## 2. Design numbers (from the simulation)

| parameter | value | why |
|---|---|---|
| tray inner size | 35-45 cm square | fits the glyph (~25 cm) plus margin so wall reflections arrive late |
| water depth `h` | 8 mm +/- 0.5 mm | sets dispersion; must be uniform |
| screen gap | 12 cm | sets caustic strength `chi = (n-1) * L_eff * lap(eta)`; 12 cm -> need `lap(eta) ~ 24 /m` |
| surface amplitudes | 0.2-1.2 mm | gives `lap(eta)` in the focusing band while staying linear |
| dominant wavelengths | 10-40 mm | the band that both focuses light and is actuatable |
| reveal time `t*` | 0.3-0.7 s after launch | before wall reflections return (~1.4 s round trip) and before dispersion erases cm structure |
| legibility window | 10-60 ms (measured: 11 ms for the outline target, 51 ms for the filled one) | the "fleeting" part; a 120 fps camera may catch one frame, a strobe will not miss it |
| actuator grid | **>= 16x16 (256)**, prefer 32x32 | measured floor: 8x8 (64) could not express the required curvature — it produced either an invisible 0.6 %-contrast ripple or a visible but shapeless 15 % pattern (see `results/coarse8*`) |
| throw | 12-20 cm | measured: 20 cm reached `corr 0.866` vs `0.812` at 12 cm, at equal contrast; the throw buys shape fidelity, not brightness |

Useful rules of thumb:

* **Focusing**: `lap(eta) ~ 1/((n-1) * L_eff)`, with `L_eff = gap + 0.75 * depth`.
  Halve the gap and you need twice the curvature.
* **Too large a gap** (`chi >> 1`) breaks the image into speckle, not a sharper
  image.
* **Decimetre-scale waves cannot paint a sharp image** at this throw; they tilt
  it. The image is carried by centimetre ripples and their interference.

## 3. Bill of materials (rough, USD)

| item | example | cost | notes |
|---|---|---|---|
| tray | 40 cm square acrylic tray, 10 mm clear bottom, or a glass photo tray | $25-60 | flatness matters more than optical quality; avoid moulded ribs in the light path |
| screen | matte drafting film / ground acrylic / fine paper | $5-15 | must be removable so the camera can look straight through at the surface for calibration |
| light | 5000 K high-CRI LED panel, dimmable, with diffuser | $25-80 | diffuse: a point source makes noisy caustics. Must be uniform and flicker-free if you strobe |
| strobe driver | MOSFET + driver on the LED, or a separate high-power LED + pulsed driver | $15-40 | lets you freeze the reveal with a long camera exposure (see section 5) |
| camera | phone (240 fps slow-mo) or USB/Basler-class camera | $0-400 | fixed, manual exposure and focus; a phone is genuinely enough for a first look |
| mirror | 45 deg first-surface or plain mirror, >= 30 cm | $10-30 | so the camera can be off-axis under the tray |
| controller | ESP32 / Teensy / Arduino | $10-30 | fires the launcher, syncs the strobe/trigger |
| absorbing beaches | open-cell foam / horsehair rope around the walls | $10 | without them, reflections return at ~1.4 s and destroy later frames |
| depth gauge | dial indicator on a bridge, or a calibrated dipstick | $20-60 | depth uniformity is the biggest systematic error |
| launcher | see section 4 | $40-600 | the hard part |

## 4. Launchers, in increasing difficulty

The simulation's default launcher is a 32x32 grid of bounded actuators
imprinting either surface displacement (`eta`) or downward velocity
(`velocity`), 12.5 mm pitch, 0.35 cell smoothing, max amplitude 1.2 mm.
The sensitivity study (`results/coarse*/`) says how much this can be coarsened
before legibility dies — check those numbers before committing to hardware.

1. **Droplet barrage from a fixed nozzle plate (velocity imprint).**
   Gravity-fed manifold with solenoid valves, or a row of nozzles on a
   traversing gantry if you accept one launch per pass. Cheapest path to a
   first "does anything appear" experiment: even a *uniform* grid of drops
   produces a rich caustic network, and you can start by tilting the plate or
   varying nozzle heights to break symmetry. Timing spread must be << the
   ~50 ms reveal window, so use a common rail, not individual pumps.

2. **Plunger bed (displacement imprint).**
   A lattice of vertical pins/plungers resting on the water, each lifted by a
   cam bar or a solenoid, then dropped together. Mechanically the most direct
   match to the model: the surface *is* the actuator pattern at `t = 0`.
   Cost and part count explode past ~8x8 with off-the-shelf solenoids; the
   coarse-grid results tell you whether 64 actuators is enough.

3. **Drop-on-demand inkjet-style head.**
   A piezo nozzle plate gives fine spatial and temporal control (kHz), at the
   cost of integrating a printhead, its driver, and water-compatible inks
   (i.e. water). This is the "right" long-term actuator if the project grows,
   and it makes staggered launch times (a DOF this repo does not yet exploit)
   available.

4. **Single shaped impactor / membrane.**
   One machined profile or a loudspeaker-driven membrane imprinting a designed
   static pattern. Attractive because it is one part; it is also the most
   constrained, and the time-reversal step in the pipeline will tell you
   immediately how much fidelity you lose (that is the `cos_projection` number).

**Recommendation for a first rig:** 16x16 is the measured minimum and 32x32 is
the comfortable choice; the outline target is markedly easier (corr 0.81-0.87)
than the filled one (0.40-0.41), because caustics form bright *lines* far more
readily than smooth filled regions — so build for the outline first. Start at
(1) or (2) with the coarsest grid the sensitivity study says still works, and
accept a wobblier reveal. The
goal of the first experiment is not the glyph; it is measuring whether a
designed launch produces a repeatable, designed-looking caustic at a predicted
instant.

## 5. Timing, sync, and how to actually see a 50 ms event

* Fire the launcher and, in the same instant, start a timer.
* **Option A (cheap):** open the camera shutter with the room darkened, then
  fire a short, bright LED pulse at `t* + delay`; vary `delay` in 10 ms steps
  across repeated identical launches to build a "frame sequence" from single
  shots. This is time-resolved photography with a $20 strobe.
* **Option B (direct):** 120-240 fps camera with continuous light; you get the
  whole dissolve in one launch, with a few hundred microseconds of motion blur
  at 240 fps.
* Repeatability is the core requirement: the reveal is only "a message" if the
  same launch returns the same image at the same moment. Measure it before
  trusting any single frame — 20 repeats, per-pixel std of the t* frame.

## 6. Calibration checklist

1. **Flat field.** Still water, no launch: the screen must be uniform (this is
   the simulation's `test_flat_surface_gives_uniform_screen`). Any pattern here
   is tray warp, screen texture, or lamp non-uniformity — record it and divide
   it out.
2. **Depth.** Measure `h` in a grid over the tray; target +/- 0.5 mm. Depth
   errors change the dispersion and therefore `t*`.
3. **Dispersion check.** Drop a single droplet, film the surface at a known
   distance (or use a laser sheet / photometric stereo), track the ring radius
   vs time, and fit `c(k)`. This validates the model and calibrates `h` and
   surface tension in situ. Do this *before* the designed launch.
4. **Gap and index.** Measure the tray-bottom-to-screen distance and confirm
   `n = 1.33` (temperature matters slightly).
5. **Latency.** Measure launcher trigger to first surface motion (microphone or
   high-speed clip); this shifts the effective `t*` and must be fed back into
   the simulation.

## 7. Safety and sanity

* Mains-powered lighting above an open tray of water: use a GFCI/RCD, keep all
  electronics on a raised, drip-shielded shelf, and never put the LED driver
  under the water line.
* Camera and mirror under the tray should be covered with a clear shield; a
  spill will find them.
* Keep the water clean and still: dust films change surface tension and make
  the reveal irreproducible. A drop of surfactant *ruins* the capillary
  dispersion; do not add soap to "settle" the water.
* Ground loops and LED flicker show up as horizontal banding in the captured
  image; power the light from a battery or a linear supply when measuring.

## 8. What success looks like on the bench

1. Still water flat field: uniform within a few percent.
2. Single-drop dispersion measurement matching `omega^2 = (gk + sigma k^3/rho)
   tanh(kh)` within measurement error.
3. A tuned launch producing a bright, structured caustic that peaks at a
   *predicted* instant (within ~20 ms) and is absent 100 ms later.
4. Correlation between the captured frame at `t*` and the simulated target
   above ~0.5 after alignment (the simulation itself reaches 0.79-0.93 against
   its own target, so 0.5 from a real rig would be a strong result).
5. Repeat launch -> same image at the same moment, with per-pixel std well
   below the image contrast.
