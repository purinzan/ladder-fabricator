"""Optional SVG-to-PNG raster output."""
from __future__ import annotations

import math

from .layout import build_bundle
from .model import Circuit
from .svg import render_svg


DEFAULT_PNG_SCALE = 2.0
MAX_PNG_SCALE = 4.0
MAX_PNG_PIXELS = 80_000_000


def render_png(circuit: Circuit, *, scale: float = DEFAULT_PNG_SCALE) -> bytes:
    """Render a validated circuit to PNG bytes using the optional CairoSVG dependency."""
    if not isinstance(scale, (int, float)) or isinstance(scale, bool) or not math.isfinite(scale):
        raise ValueError("PNG scale must be a finite number")
    if not 0.25 <= scale <= MAX_PNG_SCALE:
        raise ValueError(f"PNG scale must be between 0.25 and {MAX_PNG_SCALE:g}")

    bundle = build_bundle(circuit)
    pixels = math.ceil(bundle["width"] * scale) * math.ceil(bundle["height"] * scale)
    if pixels > MAX_PNG_PIXELS:
        raise ValueError(
            f"PNG output would exceed {MAX_PNG_PIXELS:,} pixels; reduce --png-scale"
        )
    try:
        import cairosvg
    except ImportError as exc:
        raise ValueError(
            "PNG output requires the optional dependency; "
            "install with: python -m pip install 'gx3-ladder-export[png]'"
        ) from exc
    return cairosvg.svg2png(
        bytestring=render_svg(bundle).encode("utf-8"),
        scale=float(scale),
    )

