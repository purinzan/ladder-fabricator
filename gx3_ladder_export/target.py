"""Vendor profiles for validating authoring JSON and emitting mnemonics."""
from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Any

from .device import format_device, parse_device_name


@dataclass(frozen=True)
class TargetProfile:
    id: str
    vendor: str
    series: str
    contact_types: frozenset[str]
    bit_output_types: frozenset[str]
    reset_types: frozenset[str]
    output_opcodes: dict[str, str]
    inverter_opcode: str

    @property
    def comment_types(self) -> frozenset[str]:
        return self.contact_types | self.bit_output_types | self.reset_types


MELSEC_IQ_F = TargetProfile(
    id="melsec-iq-f", vendor="melsec", series="iq-f",
    contact_types=frozenset({"X", "Y", "M", "L", "B"}),
    bit_output_types=frozenset({"Y", "M", "L", "B"}),
    reset_types=frozenset({
        "X", "Y", "M", "L", "SM", "F", "B", "SB", "S",
        "T", "ST", "C", "D", "W", "SD", "SW", "R", "Z", "LC", "LZ",
    }),
    output_opcodes={"coil": "OUT", "set": "SET", "rst": "RST", "pls": "PLS", "plf": "PLF"},
    inverter_opcode="INV",
)

KEYENCE_KV_X = TargetProfile(
    id="keyence-kv-x", vendor="keyence", series="kv-x",
    contact_types=frozenset({"R", "B", "MR", "LR", "CR", "T", "C"}),
    bit_output_types=frozenset({"R", "B", "MR", "LR"}),
    reset_types=frozenset({"R", "B", "MR", "LR", "T", "C", "DM", "EM", "FM", "ZF", "W", "TM"}),
    output_opcodes={"coil": "OUT", "set": "SET", "rst": "RES", "pls": "DIFU", "plf": "DIFD"},
    inverter_opcode="CON",
)

PROFILES = {profile.id: profile for profile in (MELSEC_IQ_F, KEYENCE_KV_X)}
_KV_TYPES = tuple(sorted(KEYENCE_KV_X.comment_types | {"CM", "Z"}, key=len, reverse=True))
_KV_LOCAL_TYPES = frozenset({"R", "MR", "LR", "T", "C", "DM", "EM", "FM", "TM"})
_KV_HEX_TYPES = frozenset({"B", "W"})
_KV_MIN_WIDTH = {"R": 3, "MR": 3, "LR": 3, "CR": 4, "B": 4, "W": 4, "CM": 4}


def profile_from_target(raw: Any, path: str = "$.target") -> TargetProfile:
    if not isinstance(raw, dict) or set(raw) != {"vendor", "series"}:
        raise ValueError(f"{path}: expected vendor and series")
    vendor = raw["vendor"]
    series = raw["series"]
    if not isinstance(vendor, str) or not isinstance(series, str):
        raise ValueError(f"{path}: vendor and series must be text")
    key = f"{vendor.lower()}-{series.lower()}"
    if key not in PROFILES:
        raise ValueError(f"{path}: unsupported target {vendor}/{series}")
    return PROFILES[key]


def profile_from_id(identifier: str) -> TargetProfile:
    try:
        return PROFILES[identifier]
    except KeyError as exc:
        raise ValueError(f"unsupported target profile {identifier}") from exc


def target_json(profile: TargetProfile) -> dict[str, str]:
    return {"id": profile.id, "vendor": profile.vendor, "series": profile.series}


def canonical_device(value: str, profile: TargetProfile) -> tuple[str, str]:
    """Return canonical spelling and device type for one target."""
    if profile is MELSEC_IQ_F:
        if not re.fullmatch(r"[A-Za-z]+[0-9A-Fa-f]+", value):
            raise ValueError("expected a direct device such as X0, M10, or C0")
        kind, number = parse_device_name(value)
        return format_device(kind, number), kind
    return _canonical_keyence_device(value)


def _canonical_keyence_device(value: str) -> tuple[str, str]:
    spelling = value.strip().upper()
    local = spelling.startswith("@")
    if local:
        spelling = spelling[1:]
    for kind in _KV_TYPES:
        if not spelling.startswith(kind):
            continue
        digits = spelling[len(kind):]
        if not digits:
            continue
        radix = 16 if kind in _KV_HEX_TYPES else 10
        if radix == 10 and not digits.isdigit():
            continue
        try:
            number = int(digits, radix)
        except ValueError:
            continue
        if local and kind not in _KV_LOCAL_TYPES:
            raise ValueError(f"{kind} cannot be a KV-X local device")
        if kind in {"R", "MR", "LR"}:
            padded = f"{number:03d}"
            if int(padded[-2:]) > 15:
                raise ValueError(f"invalid KV-X relay bit number: {value}")
            digits = padded
        elif kind in _KV_HEX_TYPES:
            digits = f"{number:0{_KV_MIN_WIDTH[kind]}X}"
        elif kind in _KV_MIN_WIDTH:
            digits = f"{number:0{_KV_MIN_WIDTH[kind]}d}"
        else:
            digits = str(number)
        return ("@" if local else "") + kind + digits, kind
    if not re.fullmatch(r"@?[A-Z]+[0-9A-F]+", value.strip().upper()):
        raise ValueError(f"invalid device: {value}")
    raise ValueError(f"unsupported KV-X device: {value}")
