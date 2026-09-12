from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import ValidationError, parse_circuit, build_bundle, render_svg

MAX_INPUT_BYTES = 1_048_576


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("$", f"duplicate JSON key {key}")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Validated ladder circuit JSON to SVG or structured connections.")
    parser.add_argument("input", type=Path, help="version 1 or 2 circuit JSON")
    parser.add_argument("--format", choices=("svg", "json"), default="svg")
    parser.add_argument("--target", choices=("melsec-iq-f", "keyence-kv-x"),
                        help="override the target stored in the circuit JSON")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--validate-only", action="store_true", help="validate supported relay structure without rendering")
    args = parser.parse_args(argv)
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        if args.output and args.input.resolve() == args.output.resolve():
            raise ValidationError("--output", "must not overwrite the input circuit")
        if args.validate_only and args.output:
            raise ValidationError("--output", "cannot be used with --validate-only")
        with args.input.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValidationError("$", f"input exceeds {MAX_INPUT_BYTES} bytes")
        circuit = parse_circuit(json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object),
                                target_override=args.target)
        if args.validate_only:
            print(f"valid: {len(circuit.rungs)} rung(s); structural relay checks only")
            return 0
        bundle = build_bundle(circuit)
        content = json.dumps(bundle, ensure_ascii=False, indent=2) if args.format == "json" else render_svg(bundle)
        if args.output:
            args.output.parent.mkdir(parents=True, exist_ok=True)
            args.output.write_text(content + "\n", encoding="utf-8")
            print(f"written: {args.output}")
        else:
            print(content)
    except (ValueError, OSError, RecursionError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    return 0
