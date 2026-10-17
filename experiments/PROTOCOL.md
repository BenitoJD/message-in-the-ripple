# Experiment protocol (physical rig)

Goal: test whether a single finite mechanical launch produces the designed
caustic glyph at the predicted instant, repeatably. Written to be followed by
someone who did not write the simulation.

---

## 0. Prerequisites

* [ ] Rig assembled per `docs/HARDWARE.md`; tray level, depth 8 +/- 0.5 mm.
* [ ] Absorbing beaches in place; walls do not return visible reflections
      before 1.4 s.
* [ ] Light path baffled; room dark enough that the screen image is
      light-limited noise only from the lamp.
* [ ] Launcher repeatable: 20 consecutive dry/bench firings with timing spread
      < 10 ms (measure with a microphone or a contact sensor).
* [ ] A simulation run saved for the exact launch you will fire, including
      `results/<tag>/launch_params.pt` and `metrics.json`.

## 1. Calibration (do once per session, in this order)

| step | procedure | acceptance |
|---|---|---|
| C1 flat field | still water, no launch, 20 frames | uniformity within 5%; save as `flat.tif` and divide it out of everything later |
| C2 depth map | dipstick/dial gauge on a 5x5 grid | each point 8 +/- 0.5 mm |
| C3 dispersion | single droplet from fixed height; film surface from a known angle/distance; track ring radius vs time; fit `c(k)` | fitted `h` and `sigma` within 10% of nominal; if not, fix the model inputs before proceeding |
| C4 latency | trigger launcher, record the first surface disturbance | latency `dt_lat` measured, then re-run the simulation with `t*_physical = t* - dt_lat` |
| C5 gap/index | measure gap; note water temperature | recorded; `n(20 C) = 1.333` |

Calibration outputs go into `experiments/calibration/<date>/`. Never compare a
capture to a simulation that used different `h`, `gap`, or `t*`.

## 2. Capture the reveal

1. Set the launcher to the designed pattern (this is the fixed artefact under
   test — do not retune it between repeats).
2. Set the strobe delay to `t* + dt_lat`.
3. **Repeat 20x**: launch, capture, wait for the surface to settle (>= 30 s, or
   actively skim/flatten), then relaunch.
4. Sweep the delay across `t* - 200 ms ... t* + 400 ms` in 20 ms steps, 5
   repeats per delay, to reconstruct the assemble->reveal->dissolve sequence.
5. Capture a "no-launch" reference at each delay setting to subtract ambient
   light drift.

Do not touch the camera, focus, lamp, or tray between the calibration and the
sweep. Log every change with a timestamp; unexplained changes invalidate the
session.

## 3. Analysis

For each delay:

1. Dark-frame subtract, flat-field divide.
2. Register (align) the frame to the simulation's screen coordinates: the
   simplest robust method is a fixed physical fiducial taped to the screen
   (two dots), and a homography from their known positions.
3. Compute the same metric the simulation reports:
   `.venv/bin/python scripts/compare_capture.py --capture <frame.png> --sim results/ink/reveal_frame_tstar.png`
   which prints the Pearson correlation after alignment and writes an overlay.
4. Plot correlation vs delay against the simulated curve
   (`results/<tag>/correlation_curve.png`) — **the shape of that curve, not a
   single number, is the result**: does a real reveal appear at the predicted
   instant and vanish at the predicted rate?

## 4. Repeatability metric

Per pixel across the 20 repeats at `t*`: mean image, std image, and the ratio
`std / (contrast of the mean image)`. Report as a fraction. This is the honest
measure of whether "the same launch returns the same image".

## 5. Failure modes and their signatures

| symptom | likely cause | check |
|---|---|---|
| nothing but a faint uniform brightening | amplitudes too small / gap too short (`chi << 1`) | C3, C5; increase amplitude or gap |
| caustic network, but no glyph at any delay | launch does not express the designed field; or `h` mismatch shifted `t*` | stage-B fidelity number; re-fit `h` from C3 and re-optimize |
| glyph appears, but at a different delay than predicted | latency not accounted, depth error, or timing jitter | C4, C2 |
| glyph sharp but unstable between repeats | launcher jitter, surface contamination, draughts | repeatability metric; cover the tray |
| speckle instead of an image | `chi >> 1` (gap too large or amplitudes too high) | reduce gap or amplitude |
| horizontal banding | LED flicker / ground loop | battery or linear supply for the lamp |
| image drifts over minutes | evaporation lowering `h`, temperature drift | top up to a marked level; re-run C2 |

## 6. Logging

One JSON per session in `experiments/sessions/<date>.json`:

```json
{
  "date": "2026-10-17",
  "sim_tag": "ink",
  "h_mm": 8.0, "gap_mm": 120.0, "water_temp_C": 21.5,
  "latency_ms": 12.0,
  "launcher": "16x16 plunger bed, pitch 25 mm, amp 1.0 mm",
  "repeats": 20,
  "corr_at_tstar": 0.0,
  "corr_curve": {"0.35": 0.0, "0.55": 0.0, "0.75": 0.0},
  "repeatability_std_over_contrast": 0.0,
  "notes": ""
}
```

## 7. What would falsify the idea

* The correlation-vs-delay curve is flat: no transient reveal exists, only a
  slowly evolving caustic network.
* The reveal appears, but at an instant unrelated to predictions across
  independent calibrations (i.e. the model is not predictive).
* Repeatability is worse than the image contrast (the "message" is noise).

Any of these is a publishable negative result and should be recorded as such
rather than tuned away.
