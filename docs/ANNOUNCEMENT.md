# Announcement copy (X / Twitter)

Copy for posting this project. Written for X Premium long posts; the single
posts and thread are kept for quote posts and replies. No em dashes anywhere,
on request. Lengths are raw characters (X counts a link as 23, so the real
count is a little lower than shown).

## Posting plan

| slot | media | why |
|---|---|---|
| main post | `results/flower8/reveal.gif` | one moving image tells the whole story, and it loops twice, so "same splash, same image" reads without explanation |
| reply, second image | `results/contrast_trap.png` | the honest science beat: the same frame stretched, honest, and zoomed to the real 0.6% ripple |
| optional | `results/outline/reveal_timeline.png` | the 28 frame story in one glance |
| optional | `results/flower_targets.png` | shows the target is a knob (5, 6, 8 petals) |

Export a post sized GIF (768 px, gitignored, does not touch the committed one):

```bash
.venv/bin/python scripts/rerender.py --tag flower8 --gif-upscale 4 \
    --gif-out results/tmp/flower8_reveal_768.gif
```

**Alt text**

* `flower8/reveal.gif`: Animation of 28 simulated caustic frames. Chaotic networks of light assemble into a crisp 8-petal flower shape at one instant, then dissolve back into chaos. The sequence repeats once.
* `contrast_trap.png`: Three panels of the same simulated caustic frame. Left, min-max stretched, showing an apparent image. Middle, on a fixed plus or minus 25 percent brightness window, appears completely flat gray. Right, zoomed to plus or minus 0.6 percent, reveals the faint heart-shaped structure that is really there.
* `outline/reveal_timeline.png`: Contact sheet of 28 caustic frames. One frame at 0.55 seconds shows a bright heart outline; the surrounding frames show unrelated caustic networks.
* `flower_targets.png`: Four panels of target shapes: 5, 6 and 8 petal flower outlines, and a filled 6 petal flower.

---

# LONG POST (recommended, 5577 chars)

```
So I've been trying to make water draw a flower.

Here's the setup. Shallow tray of water, clear bottom, lamp above, white screen underneath. Every ripple is a little lens, so the screen shows that wobbling net of light you see on the bottom of a swimming pool.

Normally it's just noise. But if you poke the water once, in exactly the right way, and then leave it completely alone, then half a second later the ripples happen to line up so that the light draws a flower on the screen. It lasts about 11 milliseconds, then it's gone.

I simulated it. Nobody has built it. And I got fooled by my own pretty picture along the way, which is honestly the best part of the story.

THE PART THAT MATTERS

The flower is not in the poke. I checked.

The splash's own light pattern scores 0.06 against the target. The water at 0.55 seconds scores 0.83. A random poke scores 0.00.

So the picture really does come from the water moving on its own. That's the whole idea, and it's the thing I most expected to be wrong.

WHY IT'S HARD

Two reasons.

Water disperses. Long ripples travel faster than short ones, so any pattern you write into the water smears itself out within a few hundred milliseconds. The flower is legible for about 11 ms. Blink and you miss it. A strobe light won't.

And you can't tell water "draw a flower". There's no formula for it. So I did two things.

First, I ran the wave equation backwards. Ignore viscosity and the equation is reversible, so I took the flower shape I wanted, put it on the water at t = 0.55 s, and propagated it back to the start. That gives a splash that would evolve into the flower. Round trip error: 1.2e-16. Viscosity is what breaks this, which is exactly what you would expect. The arrow of time, showing up in a tray of water.

Second, I made that ideal splash buildable. On its own it isn't, so I fit it onto a 32x32 grid of little actuators (0.74 to 0.96 shape match, depending on the target), then let a computer tune the grid.

The tuning is the part I like. The gradient of "does this look like the flower" flows backwards through the wave simulation and through the light bending, into every actuator. The computer isn't guessing. It's following the physics backwards.

Technically: the wave propagator is closed form, two FFTs per instant, and the ray tracing is differentiable. The whole thing runs on a laptop CPU in a few minutes.

WHAT I MEASURED

8 petal flower: 0.83 correlation, 12.8% brightness modulation, visible for 11 ms
6 petal flower: 0.82
Heart outline: 0.87 with a longer throw, 0.81 with a short one
Filled heart: 0.41

That last pair is the interesting one. Caustics are made of bright lines, so they love outlines and hate solid shapes. A flower outline is easy for physics like this. A solid heart is not.

Hardware: 64 actuators is not enough. 256 works. 1024 gets the numbers above.

And it repeats. Two runs of the same splash are identical, bit for bit. That matters, because the whole point is that the image comes back at the same moment every time.

HOW I FOOLED MYSELF

The first version of this thing reported 0.79 correlation and produced a genuinely beautiful heart. I was quite pleased with myself.

Then I measured how bright it actually was. 0.5%. And the focusing number: 0.005, which is basically nothing. The "image" was a shimmer you could not see. My own display code had been stretching every frame to full black and white, so a 0.5% ripple looked like a photograph.

The figure below is that exact frame. Stretched, it looks like a picture. On an honest fixed window it's flat gray. Zoom in to plus or minus 0.6% and you can see the heart really is there, just far too faint to matter.

What went wrong: I was scoring with correlation, and correlation does not care about brightness at all. It only asks whether the shape matches. So the optimizer happily found shapes no eye could see, and I happily showed them off.

Fixed it by adding a brightness requirement to the score, reporting brightness and focusing next to every correlation, and showing every image on a fixed window. The numbers got worse and real. The check that caught it is still in the repo.

WHAT I DON'T KNOW

It's all simulation. Linear waves, a box with no walls, an idealised splash with no crater and no droplets, simple ray optics, no camera. The designs sit comfortably in the linear regime (surface slopes around 0.09), but that's the model talking, not a measurement.

Prior art: static caustic design is a whole field, you can 3D print a lens that makes an image. Time reversal of water waves is real, Bacot et al in Nature Physics 2016, but they refocus waves back onto a source rather than drawing a picture. Water displays drive the water continuously, not once. I could not find anyone doing all four at once: one splash, free propagation, a real image, solved backwards. If you know of work like this, please tell me. I would rather find out now.

WHY I THINK IT'S WORTH BUILDING

It's cheap. Tray, LED panel, matte screen, phone camera, microcontroller. Somewhere between 150 and 500 dollars. The reveal is a 13% brightness change, which a phone camera can easily see. The design runs on a CPU.

And the next step is not the actuators. It's one droplet and a camera. Measure how ripples actually move in a real tray. If the dispersion matches what I assumed, the rest is engineering. If it doesn't, the idea dies cheaply, which is the best way for an idea to die.

Everything is here, including the negative results:

github.com/BenitoJD/message-in-the-ripple

Corrections and collaborators welcome.
```

---

# SINGLE POST

**Numbers forward (262 chars)**

```
Splash a tray of water once, then walk away.

0.55 s later the ripples bend light into an 8-petal flower on the screen below, and 11 milliseconds after that it's gone.

I simulated it. Nobody has built it. Code and plan: github.com/BenitoJD/message-in-the-ripple
```

**Punchier (214 chars)**

```
One splash. No moving parts.

Half a second later the water draws an 8-petal flower in light. 11 ms after that, it's gone.

Nobody has built this yet. I only simulated it.

github.com/BenitoJD/message-in-the-ripple
```

---

# THREAD (6 posts)

**1/6** (220 chars)

```
One splash. Then nothing.

0.55 s later, the ripples in a tray of water bend light into an 8-petal flower on the screen below. It lasts 11 milliseconds.

Then dispersion erases it.

I simulated it. Nobody has built it. 🧵
```

**2/6** (235 chars)

```
Why this is strange: the picture is not in the splash.

The splash alone scores 0.06 against the flower. The freely evolving water at t=0.55 s scores 0.83.

The image is assembled by the water's own motion. I only chose how to poke it.
```

**3/6** (229 chars)

```
You can't tell water "draw a flower".

So I ran the wave equation backwards for an ideal splash, then optimized a 32x32 actuator grid until the forward simulation produced the flower.

Waves and light, one differentiable program.
```

**4/6** (164 chars)

```
It's also fast. Ripples of different sizes travel at different speeds, so the pattern smears itself out.

Measured legible window: 11 ms. About one frame at 90 fps.
```

**5/6** (257 chars)

```
How much hardware does it need? I tested:

• 64 actuators: fails. Either an invisible shimmer, or a bright blob with no shape
• 256: works, corr 0.40
• 1024: corr 0.83 at 12.8% contrast

Caustics love lines and hate filled shapes. Flowers beat solid hearts.
```

**6/6** (266 chars)

```
Honest status: simulation only. Linear waves, periodic box, no wall reflections, idealized launcher. No tray built.

The repo has the theory, the scaling law, the BOM and the bench protocol, plus prior art I could not find:

github.com/BenitoJD/message-in-the-ripple
```

---

## Notes

* The first 280 characters are the entire pitch, because that is all X shows
  before "Show more". The long post opens with the splash, the 11
  milliseconds, and the admission that it is unbuilt.
* Keep "nobody has built it". It is true, and it is the more interesting
  claim. An unbuilt idea with a shopping list and a test protocol invites
  collaborators. An overclaim invites a correction.
* The section where the project fools itself is the most quotable part. Anyone
  who has tuned an optimizer against the wrong metric has lived it, and here
  there is a picture of it.
* The best technical reply post is the failure case: 64 actuators give either
  corr 0.71 at 0.6% contrast (invisible) or 14.8% contrast at corr 0.10
  (shapeless). A clean actuator floor.
* If someone replies with prior art, that is a win. `docs/RESEARCH_GAP.md`
  asks for it directly.
