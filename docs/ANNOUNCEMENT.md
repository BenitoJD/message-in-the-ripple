# Announcement copy (X / Twitter)

Drafts for posting this project. Lengths follow X's rules (any link counts as
23 characters; media does not count at all).

**Attach:** `results/flower8/reveal.gif` (loops twice, ~1.3 MB) — or, for a
static post, `results/flower8/reveal_timeline.png`.

**Alt text:**

> A grid of 28 simulated caustic frames. Most are chaotic networks of bright and dark cells; one frame shows a crisp 8-petal flower drawn in light, with the frames either side fading into and out of the shape.

---

## Single post — option A (numbers-forward, 235 chars)

```
Splash a tray of water once, then walk away.

0.55 s later the ripples bend light into an 8-petal flower on the screen below — for 11 milliseconds — then dispersion erases it.

Simulated, not built. Code + plan: github.com/BenitoJD/message-in-the-ripple
```

## Single post — option B (punchier, 202 chars)

```
One splash. No moving parts.

Half a second later the water draws an 8-petal flower in light — and 11 ms after that, it's gone.

Nobody has built this yet. We only simulated it.

github.com/BenitoJD/message-in-the-ripple
```

---

## Thread (6 posts, each under 280)

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

**6/6** — 245 chars

```
Honest status: simulation only. Linear waves, periodic box, no wall reflections, idealized launcher. No tray built.

Repo has the theory, the scaling law, the BOM and the bench protocol — plus prior art I could not find:

github.com/BenitoJD/message-in-the-ripple
```

---

## Notes

* **Lead with the GIF.** One image stops the scroll; the 28-frame timeline is
  the whole story in one glance. The GIF loops twice, so the repeatability
  claim ("same splash, same image, same instant") reads without explanation.
* **The hook is the mismatch** between effort and effect: one splash, eleven
  milliseconds, then nothing.
* **Keep the simulation-only line.** It is honest *and* it is the more
  interesting claim: "here is the plan, nobody has built it" invites
  collaborators and prior art; overclaiming invites a correction.
* **The best technical reply-post is the failure case**: with 64 actuators the
  optimizer either produces an invisible shimmer (corr 0.71 at 0.6 % contrast)
  or a bright shapeless blob (15 % contrast, corr 0.10) — a clean illustration
  of why correlation alone is a trap.
* If someone replies with prior art, that is a win. `docs/RESEARCH_GAP.md`
  asks for exactly that.
* Hashtags are optional on X; if used, `#physics #optics` is enough. Do not
  stuff them.
