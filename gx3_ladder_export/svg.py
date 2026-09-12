"""SVG primitives adapted from gx3-cli-mcp; render explicit paths only."""
from __future__ import annotations

import html
from .layout import CONTACT_HALF, COIL_HALF, INSTRUCTION_HALF, INVERTER_HALF

def esc(value: object) -> str:
    return html.escape(str(value), quote=True)


def short(value: str, maximum: int) -> str:
    value = " ".join(value.split())
    return value if len(value) <= maximum else value[:maximum - 1] + "…"


def comment_lines(value: str) -> list[str]:
    # Full text is kept in JSON and <title>. Make truncation visible.
    value = " ".join(value.split())
    width = 7
    return [value[:width], short(value[width:], width)] if len(value) > width else [value]


def render_svg(bundle: dict) -> str:
    """Render a bundle produced by build_bundle, not arbitrary unvalidated JSON."""
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{bundle["width"]}" height="{bundle["height"]}" viewBox="0 0 {bundle["width"]} {bundle["height"]}" role="img">',
        f'<title>{esc(bundle["title"] or "Ladder circuit")}</title>',
        '<style>.wire,.rail,.symbol,.mark{fill:none;stroke:#202832;stroke-width:2.4}'
        '.label,.heading,.comment{font-family:Meiryo,Arial,sans-serif;fill:#16242f}'
        '.label{font-size:14px;text-anchor:middle}.heading{font-size:14px}'
        '.comment{font-size:12px;text-anchor:middle;fill:#14734a}'
        '.opcode{font-family:Consolas,monospace;font-size:14px;font-weight:bold;fill:#16242f;text-anchor:middle}</style>',
        f'<rect width="{bundle["width"]}" height="{bundle["height"]}" fill="white"/>',
    ]
    for rung in bundle["rungs"]:
        layout = rung["layout"]
        lines.append(f'<g id="{esc(rung["id"])}">')
        lines.append(f'<text class="heading" x="14" y="{layout["title_y"]}">{esc(short(rung["title"] or rung["id"], max(1, (bundle["width"] - 28) // 14)))}</text>')
        for rail in layout["rails"]:
            lines.append(f'<line class="rail" data-node="{esc(rail["node"])}" x1="{rail["x"]}" x2="{rail["x"]}" y1="{rail["y1"]}" y2="{rail["y2"]}"/>')
        for edge in layout["connections"]:
            points = " ".join(f"{x},{y}" for x, y in edge["points"])
            lines.append(f'<polyline class="wire" data-connection="{esc(edge["connection"])}" points="{points}"/>')
        for node in rung["nodes"]:
            if node["kind"] not in ("contact", "coil", "instruction", "inverter"):
                continue
            position = layout["nodes"][node["id"]]
            x, y = position["x"], position["y"]
            if node["kind"] == "inverter":
                lines.append(f'<g data-node="{esc(node["id"])}"><title>INV</title>')
                lines.append(f'<rect class="symbol" x="{x - INVERTER_HALF}" y="{y - 18}" width="{INVERTER_HALF * 2}" height="36"/>')
                lines.append(f'<text class="opcode" x="{x}" y="{y + 5}">INV</text>')
                lines.append('</g>')
                continue
            # OUT is circular. SET/RST are instruction boxes so their retained
            # action is not mistaken for an ordinary output coil.
            lines.append(f'<g data-node="{esc(node["id"])}"><title>{esc(node["device"])} {esc(node["comment"])}</title>')
            if node["kind"] == "contact":
                for contact_x in (x - CONTACT_HALF, x + CONTACT_HALF):
                    lines.append(f'<line class="symbol" x1="{contact_x}" y1="{y - 13}" x2="{contact_x}" y2="{y + 13}"/>')
                if node["contact"] == "b":
                    lines.append(f'<line class="mark" x1="{x - 12}" y1="{y + 11}" x2="{x + 12}" y2="{y - 11}"/>')
                elif node["contact"] == "rising":
                    lines.append(f'<line class="mark" x1="{x}" y1="{y + 10}" x2="{x}" y2="{y - 9}"/>')
                    lines.append(f'<polyline class="mark" points="{x - 5},{y - 3} {x},{y - 9} {x + 5},{y - 3}"/>')
            elif node["kind"] == "coil":
                lines.append(f'<circle class="symbol" cx="{x}" cy="{y}" r="{COIL_HALF}"/>')
            else:
                lines.append(f'<rect class="symbol" x="{x - INSTRUCTION_HALF}" y="{y - 19}" width="{INSTRUCTION_HALF * 2}" height="38"/>')
                lines.append(f'<text class="opcode" x="{x}" y="{y + 5}">{esc(node["opcode"])}</text>')
            label_offset = 30 if node["kind"] in ("coil", "instruction") else 24
            comment_offset = 40 if node["kind"] in ("coil", "instruction") else 30
            lines.append(f'<text class="label" x="{x}" y="{y - label_offset}">{esc(short(node["device"], 14))}</text>')
            for index, value in enumerate(comment_lines(node["comment"])):
                if value:
                    lines.append(f'<text class="comment" x="{x}" y="{y + comment_offset + index * 16}">{esc(value)}</text>')
            lines.append('</g>')
        lines.append('</g>')
    return "\n".join([*lines, "</svg>"])
