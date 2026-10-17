"""Message in the Ripple — transient caustic glyphs from a finite water-wave launch.

Core idea: a finite mechanical launch imprints an initial state on a water
surface; free linear wave propagation carries it toward a designed instant
t*, at which the refracted light (caustics) on a screen briefly assembles
into a chosen glyph, then disperses.
"""

__version__ = "0.1.0"

from .waves import WaterDomain
from .optics import render_caustic
from .targets import glyph_target
from .launch import PistonArrayLaunch, VelocityArrayLaunch

__all__ = [
    "WaterDomain",
    "render_caustic",
    "glyph_target",
    "PistonArrayLaunch",
    "VelocityArrayLaunch",
]
