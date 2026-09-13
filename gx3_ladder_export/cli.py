from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

from . import (
    ValidationError, build_bundle, parse_circuit, render_circuit, render_png,
    render_rung_text,
)
from .png import DEFAULT_PNG_SCALE

MAX_INPUT_BYTES = 1_048_576


def unique_object(pairs: list[tuple[str, object]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValidationError("$", f"duplicate JSON key {key}")
        result[key] = value
    return result


def main(argv: list[str] | None = None) -> int:
    argv = list(sys.argv[1:] if argv is None else argv)
    # Keep the original input-first CLI while offering the familiar compact
    # reading command: ladder-fabricator rung-text circuit.json --comments.
    if argv[:1] == ["rung-text"]:
        argv = [*argv[1:], "--format", "rung-text"]
    parser = argparse.ArgumentParser(
        description="Validated ladder AST to rung text, SVG, PNG, or structured connections."
    )
    parser.add_argument("input", type=Path, help="version 1 or 2 circuit JSON")
    parser.add_argument("--format", choices=("svg", "png", "json", "rung-text"),
                        help="default is SVG, or PNG when output ends in .png")
    parser.add_argument("--comments", action="store_true",
                        help="append referenced device comments to rung-text output")
    parser.add_argument("--target", choices=("melsec-iq-f", "keyence-kv-x"),
                        help="override the target stored in the circuit JSON")
    parser.add_argument("-o", "--output", type=Path)
    parser.add_argument("--png-scale", type=float,
                        help=f"PNG raster scale (default: {DEFAULT_PNG_SCALE:g})")
    parser.add_argument("--validate-only", action="store_true", help="validate supported relay structure without rendering")
    args = parser.parse_args(argv)
    output_format = args.format or (
        "png" if args.output and args.output.suffix.lower() == ".png" else "svg"
    )
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8")
    try:
        if args.output and args.input.resolve() == args.output.resolve():
            raise ValidationError("--output", "must not overwrite the input circuit")
        if args.validate_only and args.output:
            raise ValidationError("--output", "cannot be used with --validate-only")
        if args.comments and output_format != "rung-text":
            raise ValidationError("--comments", "requires --format rung-text")
        if args.png_scale is not None and output_format != "png":
            raise ValidationError("--png-scale", "requires PNG output")
        with args.input.open("rb") as stream:
            raw = stream.read(MAX_INPUT_BYTES + 1)
        if len(raw) > MAX_INPUT_BYTES:
            raise ValidationError("$", f"input exceeds {MAX_INPUT_BYTES} bytes")
        circuit = parse_circuit(json.loads(raw.decode("utf-8-sig"), object_pairs_hook=unique_object),
                                target_override=args.target)
        if args.validate_only:
            print(f"valid: {len(circuit.rungs)} rung(s); structural relay checks only")
            return 0
        if output_format == "png":
            binary = render_png(circuit, scale=(
                DEFAULT_PNG_SCALE if args.png_scale is None else args.png_scale
            ))
            if args.output:
                args.output.parent.mkdir(parents=True, exist_ok=True)
                args.output.write_bytes(binary)
                print(f"written: {args.output}")
            else:
                sys.stdout.buffer.write(binary)
            return 0
        if output_format == "rung-text":
            content = render_rung_text(circuit, comments=args.comments)
        else:
            content = (
                json.dumps(build_bundle(circuit), ensure_ascii=False, indent=2)
                if output_format == "json" else render_circuit(circuit)
            )
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
