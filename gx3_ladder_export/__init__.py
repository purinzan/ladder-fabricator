"""Circuit JSON -> validated relay structure -> explicit connections and SVG."""
from .model import Circuit, ValidationError, parse_circuit
from .rung_text import render_rung_text, rung_text_records
from .layout import build_bundle
from .png import render_png
from .svg import render_svg


def render_circuit(circuit: Circuit) -> str:
    """Render an in-memory circuit AST directly to SVG."""
    return render_svg(build_bundle(circuit))


__all__ = [
    "Circuit", "ValidationError", "parse_circuit", "render_rung_text",
    "rung_text_records", "build_bundle", "render_svg", "render_circuit",
    "render_png",
]
