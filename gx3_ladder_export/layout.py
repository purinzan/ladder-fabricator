"""Build explicit connections and separate geometry from the circuit tree.

No DNF expansion, fixed-width text parsing, or inferred gap-filling wires.
A connection has its own ID and path; drawing does not invent connections.
"""
from __future__ import annotations

from .model import Circuit, Expr, condition

# Adapted from gx3-cli-mcp/gx3_ladder_layout.py, with more room for comments.
CELL_W = 120
CELL_H = 96
RAIL_PAD = 32
HEADER_H = 58
FOOTER_H = 32
CONTACT_HALF = 17
COIL_HALF = 22
# GX Works-style instruction boxes use one cell for the opcode and one per
# operand. Current authoring instructions have one operand, so they span two.
INSTRUCTION_HALF = CELL_W - 5
INVERTER_HALF = 24


def extent(expr: Expr) -> tuple[int, int]:
    if expr.op == "contact":
        return 1, 1
    if expr.op == "inv":
        width, height = extent(expr.args[0])
        return width + 1, height
    sizes = [extent(child) for child in expr.args]
    if expr.op == "and":
        return sum(w for w, _ in sizes), max(h for _, h in sizes)
    return max(w for w, _ in sizes) + 2, sum(h for _, h in sizes)


class Builder:
    def __init__(self, comments: dict[str, str], y_offset: int):
        self.comments = comments
        self.y_offset = y_offset
        self.nodes: dict[str, dict] = {}
        self.positions: dict[str, dict] = {}
        self.connections: list[dict] = []
        self.paths: list[dict] = []

    def add(self, identifier: str, kind: str, x: float, y: float, **details: object) -> str:
        if identifier in self.nodes:
            raise ValueError(f"duplicate generated node {identifier}")
        self.nodes[identifier] = {"id": identifier, "kind": kind, **details}
        self.positions[identifier] = {
            "x": RAIL_PAD + x * CELL_W,
            "y": self.y_offset + HEADER_H + (y + 0.5) * CELL_H,
        }
        return identifier

    def port(self, identifier: str, side: str) -> list[float]:
        node = self.nodes[identifier]
        point = self.positions[identifier]
        half = {
            "contact": CONTACT_HALF,
            "coil": COIL_HALF,
            "instruction": INSTRUCTION_HALF,
            "inverter": INVERTER_HALF,
        }.get(node["kind"], 0)
        return [point["x"] + (half if side == "out" else -half), point["y"]]

    def connect(self, source: str, target: str, via: list[list[float]] | None = None) -> None:
        identifier = source + ">" + target
        points = [self.port(source, "out"), *(via or []), self.port(target, "in")]
        cleaned = [points[0]]
        for point in points[1:]:
            if point != cleaned[-1]:
                cleaned.append(point)
        # Zero-length paths at a shared junction are still explicit connections.
        if len(cleaned) == 1:
            cleaned.append(cleaned[0])
        if any(a[0] != b[0] and a[1] != b[1] for a, b in zip(cleaned, cleaned[1:])):
            raise ValueError(f"non-orthogonal generated connection {identifier}")
        self.connections.append({
            "id": identifier, "from": {"node": source, "port": "out"},
            "to": {"node": target, "port": "in"},
        })
        self.paths.append({"connection": identifier, "points": cleaned})

    def place(self, expr: Expr, x: int, y: int) -> tuple[str, str]:
        if expr.op == "contact":
            identifier = self.add(expr.id, "contact", x + 0.5, y,
                                  device=expr.device, contact=expr.contact,
                                  comment=self.comments.get(expr.device, ""))
            return identifier, identifier
        if expr.op == "inv":
            child = expr.args[0]
            entry, exit_node = self.place(child, x, y)
            width, _ = extent(child)
            inverter = self.add(expr.id, "inverter", x + width + 0.5, y, opcode="INV")
            self.connect(exit_node, inverter)
            return entry, inverter
        if expr.op == "and":
            first = previous = ""
            for child in expr.args:
                entry, exit_node = self.place(child, x, y)
                if previous:
                    self.connect(previous, entry)
                first = first or entry
                previous = exit_node
                x += extent(child)[0]
            return first, previous
        width, _ = extent(expr)
        entry = self.add(expr.id + ":fork", "junction", x, y)
        exit_node = self.add(expr.id + ":join", "junction", x + width, y)
        branch_y = y
        for child in expr.args:
            branch_entry, branch_exit = self.place(child, x + 1, branch_y)
            self.connect(entry, branch_entry, [[self.port(entry, "out")[0], self.port(branch_entry, "in")[1]]])
            self.connect(branch_exit, exit_node, [[self.port(exit_node, "in")[0], self.port(branch_exit, "out")[1]]])
            branch_y += extent(child)[1]
        return entry, exit_node


def build_bundle(circuit: Circuit) -> dict:
    """Derived graph + SVG geometry + conditions; never a second editable truth."""
    rung_widths = [extent(rung.logic)[0] for rung in circuit.rungs]
    has_instruction = any(rung.output_type != "coil" for rung in circuit.rungs)
    columns = max(rung_widths) + (4 if has_instruction else 3)
    offset = 0
    rungs = []
    comments = dict(circuit.comments)
    for rung in circuit.rungs:
        _, height = extent(rung.logic)
        builder = Builder(comments, offset)
        left = builder.add(rung.id + ":left", "left_rail", 0, 0)
        entry, exit_node = builder.place(rung.logic, 1, 0)
        opcode = {"coil": "OUT", "set": "SET", "rst": "RST", "pls": "PLS"}[rung.output_type]
        output_kind = "coil" if rung.output_type == "coil" else "instruction"
        output_x = columns - (1 if output_kind == "instruction" else 0.5)
        coil = builder.add(rung.id + ":output", output_kind, output_x, 0,
                           device=rung.output, opcode=opcode, operands=[rung.output],
                           comment=comments.get(rung.output, ""))
        right = builder.add(rung.id + ":right", "right_rail", columns, 0)
        builder.connect(left, entry)
        builder.connect(exit_node, coil)
        builder.connect(coil, right)
        # Extend to the LAST BRANCH CENTER, not the top edge of its grid row.
        rail_top = offset + HEADER_H + CELL_H * 0.5 - 22
        rail_bottom = offset + HEADER_H + CELL_H * (height - 0.5) + 22
        rungs.append({
            "id": rung.id, "title": rung.title,
            "nodes": list(builder.nodes.values()),
            "connections": builder.connections,
            "output_condition": {
                "output": coil, "action": opcode, "target": rung.output,
                "logic": condition(rung.logic),
            },
            "layout": {
                "nodes": builder.positions, "connections": builder.paths,
                "rails": [{"node": node, "x": builder.positions[node]["x"], "y1": rail_top, "y2": rail_bottom}
                          for node in (left, right)],
                "title_y": offset + 26,
            },
        })
        offset += HEADER_H + height * CELL_H + FOOTER_H
    return {
        "schema": "gx3-ladder-export/render-bundle", "schema_version": 1,
        "title": circuit.title, "width": columns * CELL_W + RAIL_PAD * 2,
        "height": offset, "rungs": rungs,
        "limitations": [
            "Rendering only; no PLC execution or live values.",
            "Rising contacts and PLS require a previous scan result; SET/RST retain PLC device state.",
        ],
    }
