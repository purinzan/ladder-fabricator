"""Optional SVG-to-PNG raster output."""
from __future__ import annotations

import math
from xml.etree import ElementTree as ET

from .layout import build_bundle
from .model import Circuit
from .svg import GX_THEME, KEYENCE_THEME, render_svg


DEFAULT_PNG_SCALE = 2.0
MAX_PNG_SCALE = 4.0
MAX_PNG_PIXELS = 80_000_000


def _png_svg(bundle: dict) -> str:
    """Resolve a usable family for CairoSVG's single-family text renderer.

    Keep the portable SVG's fallback list unchanged. Probe the actual visible
    characters through Cairo so a missing first family does not hide Japanese
    even when a later family is installed.
    """
    import cairocffi as cairo

    svg = render_svg(bundle)
    text = "".join(n.text or "" for n in ET.fromstring(svg).iter()
                   if n.tag == "{http://www.w3.org/2000/svg}text")
    sample = "".join(dict.fromkeys(text))
    if not sample:
        return svg
    theme = KEYENCE_THEME if bundle["target"]["id"] == "keyence-kv-x" else GX_THEME
    families = theme["font"]
    best, coverage = "", -1
    for item in families.split(","):
        family = item.strip(' "')
        font = cairo.ScaledFont(cairo.ToyFontFace(family), cairo.Matrix(xx=12, yy=12),
                                cairo.Matrix(), cairo.FontOptions())
        glyphs = font.text_to_glyphs(0, 0, sample, False)
        covered = sum(index != 0 for index, _x, _y in glyphs)
        if covered > coverage:
            best, coverage = family, covered
        if all(index != 0 for index, _x, _y in glyphs):
            break
    return svg.replace(families, f'"{best}"')


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
        bytestring=_png_svg(bundle).encode("utf-8"),
        scale=float(scale),
    )

