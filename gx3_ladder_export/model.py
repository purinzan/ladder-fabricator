"""Validated, immutable circuit input. Connections are structural, not coordinates.

The device/contact and and/or/not vocabulary comes from gx3-cli-mcp's
generate_rung/to_nnf. Unlike that generator, we never expand to DNF.
"""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .target import MELSEC_IQ_F, TargetProfile, canonical_device, profile_from_id, profile_from_target

MAX_RUNGS = 64
MAX_NODES = 512  # total expression nodes per document, before normalization
MAX_DEPTH = 24
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


def device(value: Any, path: str, profile: TargetProfile, *, allowed: frozenset[str]) -> str:
    name = text(value, path, 32)
    try:
        canonical, kind = canonical_device(name, profile)
    except ValueError as exc:
        raise ValidationError(path, str(exc)) from exc
    if kind not in allowed:
        raise ValidationError(path, f"unsupported device type {kind}; supported: {', '.join(sorted(allowed))}")
    return canonical


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
    target: str = MELSEC_IQ_F.id


def parse_circuit(payload: Any, target_override: str | None = None) -> Circuit:
    """Reject unsupported or excessive input; never return a partial circuit."""
    doc = fields(payload, {"schema_version", "target", "title", "comments", "rungs"},
                 {"schema_version", "rungs"}, "$")
    version = doc["schema_version"]
    if type(version) is not int or version not in (1, 2):
        raise ValidationError("$.schema_version", "expected version 1 or 2")
    if target_override:
        try:
            profile = profile_from_id(target_override)
        except ValueError as exc:
            raise ValidationError("--target", str(exc)) from exc
    elif "target" in doc:
        try:
            profile = profile_from_target(doc["target"])
        except ValueError as exc:
            message = str(exc)
            raise ValidationError("$.target", message.split(": ", 1)[-1]) from exc
    else:
        profile = MELSEC_IQ_F
    if version == 1 and "target" in doc:
        raise ValidationError("$.target", "requires schema_version 2")
    if version == 2 and "target" not in doc and not target_override:
        raise ValidationError("$.target", "required for schema_version 2")
    title = text(doc.get("title", ""), "$.title", 160)
    raw_comments = doc.get("comments", {})
    if not isinstance(raw_comments, dict) or len(raw_comments) > MAX_NODES:
        raise ValidationError("$.comments", f"expected a device/text map with at most {MAX_NODES} entries")
    comments = {}
    for key, value in raw_comments.items():
        canonical = device(key, "$.comments", profile, allowed=profile.comment_types)
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
            if role not in ("a", "b", "rising", "falling"):
                raise ValidationError(path + ".contact", "expected a, b, rising, or falling")
            if negate:
                if role in ("rising", "falling"):
                    raise ValidationError(path + ".contact", "edge contacts cannot be negated")
                role = "b" if role == "a" else "a"
            return Expr(identifier, "contact", device=device(
                leaf["device"], path + ".device", profile, allowed=profile.contact_types), contact=role)
        fields(raw, {"and", "or", "not", "inv"}, set(), path)
        if len(raw) != 1:
            raise ValidationError(path, "expected exactly one of and/or/not/inv")
        op = next(iter(raw))
        if op == "not":
            # NOT is normalized into contact polarity and De Morgan operators.
            # Keep IDs tied to the resulting semantic position, so an input
            # using NOT and its canonical AST serialize to the same nodes.
            return expression(raw[op], path + ".not", identifier, depth + 1,
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
        if output_type not in ("coil", "set", "rst", "pls", "plf"):
            raise ValidationError(path + ".output.type", "expected coil (OUT), set, rst, pls, or plf")
        rungs.append(Rung(
            identifier, text(raw.get("title", ""), path + ".title", 160),
            expression(raw["logic"], path + ".logic", identifier + ":logic"),
            device(output["device"], path + ".output.device", profile,
                   allowed=(profile.reset_types if output_type == "rst" else profile.bit_output_types)),
            output_type,
        ))
    return Circuit(title, tuple(rungs), tuple(comments.items()), profile.id)


def condition(expr: Expr) -> dict:
    if expr.op == "contact":
        return {"op": "contact", "node": expr.id, "device": expr.device, "contact": expr.contact}
    if expr.op == "inv":
        return {"op": "inv", "node": expr.id, "args": [condition(expr.args[0])]}
    return {"op": expr.op, "args": [condition(child) for child in expr.args]}
