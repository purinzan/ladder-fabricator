"""Validated, immutable circuit input. Connections are structural, not coordinates.

The device/contact and and/or/not vocabulary comes from gx3-cli-mcp's
generate_rung/to_nnf. Unlike that generator, we never expand to DNF.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .device import format_device, parse_device_name

MAX_RUNGS = 64
MAX_NODES = 512  # total expression nodes per document, before normalization
MAX_DEPTH = 24
# v1 supports relay logic only. Timer/counter instructions and word operands
# require their own semantics, even though some share contact syntax.
CONTACT_TYPES = frozenset({"X", "Y", "M", "L", "B"})
OUTPUT_TYPES = frozenset({"Y", "M", "L", "B"})
ID_RE = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,47}\Z")


class ValidationError(ValueError):
    def __init__(self, path: str, message: str):
        super().__init__(f"{path}: {message}")


def fields(value: Any, allowed: set[str], required: set[str], path: str) -> dict:
    if not isinstance(value, dict):
        raise ValidationError(path, "expected an object")
    if any(not isinstance(key, str) for key in value):
        raise ValidationError(path, "object keys must be strings")
    extra = value.keys() - allowed
    missing = required - value.keys()
    if extra:
        raise ValidationError(path, f"unknown fields: {', '.join(sorted(extra))}")
    if missing:
        raise ValidationError(path, f"missing fields: {', '.join(sorted(missing))}")
    return value


def text(value: Any, path: str, maximum: int = 2048) -> str:
    if not isinstance(value, str) or len(value) > maximum:
        raise ValidationError(path, f"expected text of at most {maximum} characters")
    if any(not (c in "\t\n\r" or 0x20 <= ord(c) <= 0xD7FF
                or 0xE000 <= ord(c) <= 0xFFFD or 0x10000 <= ord(c) <= 0x10FFFF) for c in value):
        raise ValidationError(path, "text contains characters invalid in XML")
    return value


def device(value: Any, path: str, *, output: bool = False) -> str:
    name = text(value, path, 32)
    # The reused parser is intentionally permissive; v1's authoring boundary
    # rejects unknown types, signs, indirect addresses and non-ASCII spelling.
    if not re.fullmatch(r"[A-Za-z]+[0-9A-Fa-f]+", name):
        raise ValidationError(path, "expected a direct bit device such as X0 or M10")
    try:
        kind, number = parse_device_name(name)
    except ValueError as exc:
        raise ValidationError(path, str(exc)) from exc
    allowed = OUTPUT_TYPES if output else CONTACT_TYPES
    if kind not in allowed:
        raise ValidationError(path, f"unsupported device type {kind}; supported: {', '.join(sorted(allowed))}")
    return format_device(kind, number)


@dataclass(frozen=True)
class Expr:
    id: str
    op: str
    args: tuple[Expr, ...] = ()
    device: str = ""
    contact: str = "a"


@dataclass(frozen=True)
class Rung:
    id: str
    title: str
    logic: Expr
    output: str
    output_type: str


@dataclass(frozen=True)
class Circuit:
    title: str
    rungs: tuple[Rung, ...]
    comments: tuple[tuple[str, str], ...]


def parse_circuit(payload: Any) -> Circuit:
    """Reject unsupported or excessive input; never return a partial circuit."""
    doc = fields(payload, {"schema_version", "title", "comments", "rungs"},
                 {"schema_version", "rungs"}, "$")
    if type(doc["schema_version"]) is not int or doc["schema_version"] != 1:
        raise ValidationError("$.schema_version", "expected version 1")
    title = text(doc.get("title", ""), "$.title", 160)
    raw_comments = doc.get("comments", {})
    if not isinstance(raw_comments, dict) or len(raw_comments) > MAX_NODES:
        raise ValidationError("$.comments", f"expected a device/text map with at most {MAX_NODES} entries")
    comments = {}
    for key, value in raw_comments.items():
        canonical = device(key, "$.comments")
        if canonical in comments:
            raise ValidationError("$.comments", f"duplicate normalized device {canonical}")
        comments[canonical] = text(value, f"$.comments.{key}")
    raw_rungs = doc["rungs"]
    if not isinstance(raw_rungs, list) or not 1 <= len(raw_rungs) <= MAX_RUNGS:
        raise ValidationError("$.rungs", f"expected 1..{MAX_RUNGS} rungs")

    count = 0

    def expression(raw: Any, path: str, identifier: str, depth: int = 0,
                   negate: bool = False, allow_inv: bool = True) -> Expr:
        nonlocal count
        count += 1
        if count > MAX_NODES:
            raise ValidationError(path, f"expression node limit exceeded ({MAX_NODES})")
        if depth > MAX_DEPTH:
            raise ValidationError(path, f"expression depth limit exceeded ({MAX_DEPTH})")
        if isinstance(raw, str):
            raw = {"device": raw}
        if not isinstance(raw, dict):
            raise ValidationError(path, "expected a logic object or device string")
        if "device" in raw:
            leaf = fields(raw, {"device", "contact"}, {"device"}, path)
            role = leaf.get("contact", "a")
            if role not in ("a", "b", "rising"):
                raise ValidationError(path + ".contact", "expected a, b, or rising")
            if negate:
                if role == "rising":
                    raise ValidationError(path + ".contact", "rising contacts cannot be negated")
                role = "b" if role == "a" else "a"
            return Expr(identifier, "contact", device=device(leaf["device"], path + ".device"), contact=role)
        fields(raw, {"and", "or", "not", "inv"}, set(), path)
        if len(raw) != 1:
            raise ValidationError(path, "expected exactly one of and/or/not/inv")
        op = next(iter(raw))
        if op == "not":
            return expression(raw[op], path + ".not", identifier + "-n", depth + 1,
                              not negate, False)
        if op == "inv":
            if not allow_inv or negate:
                raise ValidationError(path + ".inv", "INV is supported only as the outermost logic operation")
            child = expression(raw[op], path + ".inv", identifier + "-source", depth + 1,
                               False, False)
            return Expr(identifier, "inv", (child,))
        children = raw[op]
        if not isinstance(children, list) or not 2 <= len(children) <= MAX_NODES:
            raise ValidationError(path + "." + op, f"expected 2..{MAX_NODES} operands")
        # De Morgan normalization preserves tree size; no Cartesian expansion.
        normalized = ("or" if op == "and" else "and") if negate else op
        return Expr(identifier, normalized, tuple(
            expression(child, f"{path}.{op}[{index}]", f"{identifier}-{index}",
                       depth + 1, negate, False)
            for index, child in enumerate(children)
        ))

    rungs = []
    seen = set()
    for index, value in enumerate(raw_rungs):
        path = f"$.rungs[{index}]"
        raw = fields(value, {"id", "title", "logic", "output"}, {"id", "logic", "output"}, path)
        identifier = text(raw["id"], path + ".id", 48)
        if not ID_RE.fullmatch(identifier) or identifier in seen:
            raise ValidationError(path + ".id", "expected a unique identifier starting with a letter (letters/digits/_/-)")
        seen.add(identifier)
        output = fields(raw["output"], {"type", "device"}, {"device"}, path + ".output")
        output_type = output.get("type", "coil")
        if output_type not in ("coil", "set", "rst", "pls"):
            raise ValidationError(path + ".output.type", "expected coil (OUT), set, rst, or pls")
        rungs.append(Rung(
            identifier, text(raw.get("title", ""), path + ".title", 160),
            expression(raw["logic"], path + ".logic", identifier + ":logic"),
            device(output["device"], path + ".output.device", output=True),
            output_type,
        ))
    return Circuit(title, tuple(rungs), tuple(comments.items()))


def condition(expr: Expr) -> dict:
    if expr.op == "contact":
        return {"op": "contact", "node": expr.id, "device": expr.device, "contact": expr.contact}
    if expr.op == "inv":
        return {"op": "inv", "node": expr.id, "args": [condition(expr.args[0])]}
    return {"op": expr.op, "args": [condition(child) for child in expr.args]}
