"""SVG primitives adapted from gx3-cli-mcp; render explicit paths only."""
from __future__ import annotations

import html
from .layout import CELL_H, CELL_W, CONTACT_HALF, COIL_HALF, INSTRUCTION_HALF, INVERTER_HALF


# GX Works3 ladder-canvas reference profile. Stroke widths are CSS pixels and
# vector-effect keeps them stable if callers scale the SVG.
INK = "#202020"
GRID = "#c6c6c7"
COMMENT = "#2f8a48"
STATEMENT_FILL = "#a2dfdf"
STATEMENT_BORDER = "#4c925e"
WIRE_PX = 1
GRID_PX = 0.6
BOX_PX = 1

GX_THEME = {
    "ink": INK, "grid": GRID, "comment": COMMENT,
    "statement_fill": STATEMENT_FILL, "statement_border": STATEMENT_BORDER,
    "font": '"MS Gothic","Yu Gothic UI",Meiryo,Arial,sans-serif',
    "opcode_fill": "url(#gx3-opcode)",
}
KEYENCE_THEME = {
    "ink": "#1e2732", "grid": "#cbd2da", "comment": "#26754d",
    "statement_fill": "#e7edf3", "statement_border": "#8998a8",
    "font": '"Yu Gothic UI",Meiryo,"MS Gothic",Arial,sans-serif',
    "opcode_fill": "#e4e8ed",
}

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
    target = bundle.get("target", {"id": "melsec-iq-f"})
    keyence = target.get("id") == "keyence-kv-x"
    theme = KEYENCE_THEME if keyence else GX_THEME
    lines = [
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{bundle["width"]}" height="{bundle["height"]}" viewBox="0 0 {bundle["width"]} {bundle["height"]}" role="img" data-target="{esc(target.get("id", "melsec-iq-f"))}">',
        f'<title>{esc(bundle["title"] or "Ladder circuit")}</title>',
        '<defs><linearGradient id="gx3-opcode" x1="0" y1="0" x2="0" y2="1">'
        '<stop offset="0%" stop-color="#f4f3f3"/><stop offset="50%" stop-color="#d3d3d3"/>'
        '<stop offset="100%" stop-color="#969796"/></linearGradient></defs>',
        f'<style>.wire,.rail,.symbol,.mark{{fill:none;stroke:{theme["ink"]};stroke-width:{WIRE_PX};'
        'stroke-linecap:square;stroke-linejoin:miter;vector-effect:non-scaling-stroke;shape-rendering:crispEdges}'
        f'.grid{{stroke:{theme["grid"]};stroke-width:{GRID_PX};stroke-dasharray:1 2;vector-effect:non-scaling-stroke}}'
        f'.statement{{fill:{theme["statement_fill"]};stroke:{theme["statement_border"]};stroke-width:{BOX_PX};vector-effect:non-scaling-stroke;shape-rendering:crispEdges}}'
        f'.label,.heading,.comment{{font-family:{theme["font"]}}}'
        f'.label{{font-size:13px;text-anchor:middle;fill:{theme["ink"]}}}.heading{{font-size:12px;fill:{theme["ink"]}}}'
        f'.comment{{font-size:10px;text-anchor:middle;fill:{theme["comment"]}}}'
        f'.opcode{{font-family:{theme["font"]};font-size:13px;fill:{theme["ink"]};text-anchor:middle}}'
        f'.instruction-body{{fill:white}}.instruction-box{{fill:none;stroke:{theme["ink"]};stroke-width:{BOX_PX};vector-effect:non-scaling-stroke;shape-rendering:crispEdges}}'
        f'.opcode-cell{{fill:{theme["opcode_fill"]}}}.box-separator{{stroke:{theme["grid"]};stroke-width:{BOX_PX};vector-effect:non-scaling-stroke}}'
        f'.operand{{font-family:{theme["font"]};font-size:12px;fill:{theme["ink"]};text-anchor:middle}}</style>',
        f'<rect width="{bundle["width"]}" height="{bundle["height"]}" fill="white"/>',
    ]
    for rung in bundle["rungs"]:
        layout = rung["layout"]
        # Integer geometry plus a half-pixel translation puts 1 px strokes on
        # device-pixel centers instead of blending them over two pixel rows.
        lines.append(f'<g id="{esc(rung["id"])}" transform="translate(0.5 0.5)">')
        grid = layout["grid"]
        lines.append(f'<rect class="statement" x="{grid["x"]}" y="{grid["y"] - 30}" width="{grid["width"]}" height="22"/>')
        lines.append(f'<text class="heading" x="{grid["x"] + 4}" y="{layout["title_y"]}">{esc(short(rung["title"] or rung["id"], max(1, (bundle["width"] - 28) // 14)))}</text>')
        for column in range(grid["columns"] + 1):
            grid_x = grid["x"] + column * CELL_W
            lines.append(f'<line class="grid" x1="{grid_x}" x2="{grid_x}" y1="{grid["y"]}" y2="{grid["y"] + grid["height"]}"/>')
        for row in range(grid["rows"] + 1):
            grid_y = grid["y"] + row * CELL_H
            lines.append(f'<line class="grid" x1="{grid["x"]}" x2="{grid["x"] + grid["width"]}" y1="{grid_y}" y2="{grid_y}"/>')
        for rail in layout["rails"]:
            lines.append(f'<line class="rail" data-node="{esc(rail["node"])}" x1="{rail["x"]}" x2="{rail["x"]}" y1="{rail["y1"]}" y2="{rail["y2"]}"/>')
        for edge in layout["connections"]:
            points = " ".join(f"{x},{y}" for x, y in edge["points"])
            lines.append(f'<polyline class="wire" data-connection="{esc(edge["connection"])}" points="{points}"/>')
        for node in rung["nodes"]:
            if node["kind"] not in ("contact", "coil", "instruction", "predicate", "inverter"):
                continue
            position = layout["nodes"][node["id"]]
            x, y = position["x"], position["y"]
            if node["kind"] == "inverter":
                lines.append(f'<g data-node="{esc(node["id"])}"><title>{esc(node["opcode"])}</title>')
                lines.append(f'<rect class="symbol" x="{x - INVERTER_HALF}" y="{y - 18}" width="{INVERTER_HALF * 2}" height="36"/>')
                lines.append(f'<text class="opcode" x="{x}" y="{y + 5}">{esc(node["opcode"])}</text>')
                lines.append('</g>')
                continue
            # OUT is circular. SET/RST are instruction boxes so their retained
            # action is not mistaken for an ordinary output coil.
            instruction_text = (f'{node["opcode"]} {" ".join(node["operands"])}'
                                if node["kind"] in ("instruction", "predicate") else node["device"])
            lines.append(f'<g data-node="{esc(node["id"])}"><title>{esc(instruction_text)} {esc(node["comment"])}</title>')
            if node["kind"] == "contact":
                for contact_x in (x - CONTACT_HALF, x + CONTACT_HALF):
                    lines.append(f'<line class="symbol" x1="{contact_x}" y1="{y - 13}" x2="{contact_x}" y2="{y + 13}"/>')
                if node["contact"] == "b":
                    lines.append(f'<line class="mark" x1="{x - 12}" y1="{y + 11}" x2="{x + 12}" y2="{y - 11}"/>')
                elif node["contact"] == "rising":
                    lines.append(f'<line class="mark" x1="{x}" y1="{y + 10}" x2="{x}" y2="{y - 9}"/>')
                    lines.append(f'<polyline class="mark" points="{x - 5},{y - 3} {x},{y - 9} {x + 5},{y - 3}"/>')
                elif node["contact"] == "falling":
                    lines.append(f'<line class="mark" x1="{x}" y1="{y - 10}" x2="{x}" y2="{y + 9}"/>')
                    lines.append(f'<polyline class="mark" points="{x - 5},{y + 3} {x},{y + 9} {x + 5},{y + 3}"/>')
            elif node["kind"] == "coil":
                if keyence:
                    lines.append(f'<path class="symbol" d="M {x - 3} {y - COIL_HALF} Q {x - COIL_HALF} {y} {x - 3} {y + COIL_HALF}"/>')
                    lines.append(f'<path class="symbol" d="M {x + 3} {y - COIL_HALF} Q {x + COIL_HALF} {y} {x + 3} {y + COIL_HALF}"/>')
                else:
                    lines.append(f'<circle class="symbol" cx="{x}" cy="{y}" r="{COIL_HALF}"/>')
            else:
                box_left = x - INSTRUCTION_HALF
                operand_lines = [" ".join(node["operands"])]
                box_height = 58
                if len(node["operands"]) > 2:
                    operand_lines = [" ".join(node["operands"][:2]), " ".join(node["operands"][2:])]
                    box_height = 76
                box_top = y - box_height / 2
                box_width = INSTRUCTION_HALF * 2
                opcode_width = CELL_W - 10
                operand_x = box_left + opcode_width + (box_width - opcode_width) / 2
                lines.append(f'<rect class="instruction-body" x="{box_left}" y="{box_top}" width="{box_width}" height="{box_height}"/>')
                lines.append(f'<rect class="opcode-cell" x="{box_left}" y="{box_top}" width="{opcode_width}" height="{box_height}"/>')
                lines.append(f'<rect class="instruction-box" x="{box_left}" y="{box_top}" width="{box_width}" height="{box_height}"/>')
                lines.append(f'<line class="box-separator" x1="{box_left + opcode_width}" y1="{box_top}" x2="{box_left + opcode_width}" y2="{box_top + box_height}"/>')
                lines.append(f'<text class="opcode" x="{box_left + opcode_width / 2}" y="{y + 5}">{esc(node["opcode"])}</text>')
                for index, value in enumerate(operand_lines):
                    lines.append(f'<text class="operand" x="{operand_x}" y="{box_top + 16 + index * 14}">{esc(value)}</text>')
                comment_y = box_top + (52 if len(operand_lines) > 1 else 37)
                for index, value in enumerate(comment_lines(node["comment"])):
                    if value:
                        lines.append(f'<text class="comment" x="{operand_x}" y="{comment_y + index * 13}">{esc(value)}</text>')
            label_offset = 30 if node["kind"] in ("coil", "instruction", "predicate") else 24
            comment_offset = 40 if node["kind"] in ("coil", "instruction", "predicate") else 30
            if node["kind"] not in ("instruction", "predicate"):
                lines.append(f'<text class="label" x="{x}" y="{y - label_offset}">{esc(short(node["device"], 14))}</text>')
                for index, value in enumerate(comment_lines(node["comment"])):
                    if value:
                        lines.append(f'<text class="comment" x="{x}" y="{y + comment_offset + index * 16}">{esc(value)}</text>')
            lines.append('</g>')
        lines.append('</g>')
    return "\n".join([*lines, "</svg>"])
