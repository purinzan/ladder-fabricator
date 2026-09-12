"""Compact, comment-aware reading form derived directly from the circuit AST."""
from __future__ import annotations

import json

from .model import Circuit, Expr
from .target import profile_from_id


def _condition_text(expr: Expr, parent_precedence: int = 0) -> str:
    if expr.op == "contact":
        if expr.contact == "a":
            return expr.device
        if expr.contact == "b":
            return "/" + expr.device
        if expr.contact == "rising":
            return f"RISING({expr.device})"
        return f"FALLING({expr.device})"
    if expr.op == "inv":
        return f"INV({_condition_text(expr.args[0])})"
    precedence = 2 if expr.op == "and" else 1
    text = f" {expr.op.upper()} ".join(_condition_text(child, precedence) for child in expr.args)
    return f"({text})" if precedence < parent_precedence else text


def _referenced_devices(expr: Expr) -> list[str]:
    if expr.op == "contact":
        return [expr.device]
    devices: list[str] = []
    for child in expr.args:
        for device in _referenced_devices(child):
            if device not in devices:
                devices.append(device)
    return devices


def rung_text_records(circuit: Circuit, *, comments: bool = False) -> list[dict]:
    """Build one readable record per output directly from the in-memory AST."""
    profile = profile_from_id(circuit.target)
    comment_map = dict(circuit.comments)
    records = []
    for rung in circuit.rungs:
        devices = [*_referenced_devices(rung.logic), rung.output]
        visible_comments = {
            device: comment_map[device]
            for device in dict.fromkeys(devices)
            if device in comment_map
        }
        record = {
            "id": rung.id,
            "title": rung.title,
            "condition": _condition_text(rung.logic),
            "opcode": profile.output_opcodes[rung.output_type],
            "device": rung.output,
        }
        if comments:
            record["comments"] = visible_comments
        records.append(record)
    return records


def render_rung_text(circuit: Circuit, *, comments: bool = False) -> str:
    """Render the optional condition-to-output view for people and AI."""
    lines: list[str] = []
    for record in rung_text_records(circuit, comments=comments):
        if record["title"]:
            lines.extend(([f"# {record['title']}"] if not lines else ["", f"# {record['title']}"]))
        output = record["device"]
        if record["opcode"] != "OUT":
            output = f"{record['opcode']} {output}"
        line = f"{record['id']}  {record['condition']} -> {output}"
        if comments and record["comments"]:
            rendered = ", ".join(
                f"{device}={json.dumps(text, ensure_ascii=False)}"
                for device, text in record["comments"].items()
            )
            line += "  # " + rendered
        lines.append(line)
    return "\n".join(lines)
