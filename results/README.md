# Results

Committed outputs of the runs described in the top-level README. Every number in
a `metrics.json` comes from a run whose launch parameters are saved alongside it
(`launch_params.pt`), so any artifact can be regenerated — including at a
different display scale or ray sampling — without re-optimizing:

```bash
.venv/bin/python scripts/rerender.py --tag outline
```

## Artifact guide

| file | what it is |
|---|---|
| `reveal_timeline.png` | contact sheet of the caustic at successive instants; the reveal is the frame at `t*` |
| `reveal.gif` | the same sequence as a looping GIF (played twice, so the repeatability claim is visible in one loop) |
| `reveal_frame_tstar.png` | the frame at `t*` alone |
| `correlation_curve.png` | `corr(target, caustic(t))` versus time — the legibility timeline |
| `designed_surface.png`, `designed_caustic.png` | stage A: the ideal (wave-free) surface and the image it makes |
| `launch_imprint.png` | the initial state the actuator grid imprints at `t = 0` |
| `target.png` | the target bitmap the optimization was scored against |
| `launch_params.pt` | actuator amplitudes + full configuration (torch.save) |
| `metrics.json` | correlations, contrast, `chi`, controls, per-seed history |

## Display convention (important)

Caustic frames are shown on a **fixed** window of `mean ± 25 %` of the mean
intensity (`ripple.viz.relative`), never per-frame min-max stretched. A frame
whose real contrast is 0.6 % therefore *looks* flat — which is the point: an
earlier version of this pipeline reported `corr = 0.79` for a caustic with
0.5 % contrast that only contrast stretching made visible. Every run now
reports `contrast` (std/mean) and `chi` (the focusing parameter) next to the
correlation, and `scripts/probe_sampling.py` checks that the reported structure
survives finer ray sampling and correct pixel-area integration.

## Runs

| tag | what it varies |
|---|---|
| `static` | stage A only: free surface, no wave dynamics (computational-caustics reference) |
| `outline` | heart outline, 32×32 actuators — the crispest reveal |
| `ink` | filled heart, 32×32 actuators |
| `coarse16` | 16×16 actuators (256) — how little hardware is needed |
| `coarse8` | 8×8 actuators (64) — shows the actuator-count floor |
| `coarse8_strong` | 8×8 with a 10× heavier contrast penalty, to separate "too few actuators" from "penalty too soft" |
| `outline_gap20` | same target with a 20 cm throw instead of 12 cm, testing the `chi` scaling law |

Reproduce any of them (CPU, a few minutes each):

```bash
.venv/bin/python scripts/demo_static.py --iters 250 --tag static
.venv/bin/python scripts/demo_array.py --mode outline --tag outline
.venv/bin/python scripts/demo_array.py --mode ink --n-coarse 16 --iters 400 --seeds 0,1 --tag coarse16
.venv/bin/python scripts/demo_array.py --mode ink --n-coarse 8 --iters 400 --seeds 0,1 --tag coarse8
.venv/bin/python scripts/demo_array.py --mode outline --gap 0.20 --iters 400 --seeds 0,1 --tag outline_gap20
```

Then, after adding or changing runs:

```bash
.venv/bin/python scripts/update_readme_table.py   # refresh the README table
```
