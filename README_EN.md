# Ladder Fabricator

Ladder Fabricator is an open-source JSON AST-to-ladder-diagram renderer for
Mitsubishi MELSEC iQ-F / GX Works3 and KEYENCE KV-X / KV STUDIO. It generates
SVG, high-resolution PNG, readable rung text, and explicit connection JSON from
one validated circuit definition.

It gives people and AI agents a deterministic boundary between circuit intent
and visual layout. Authors describe logic, devices, and outputs in JSON. Ladder
Fabricator validates that source and derives coordinates, branches, wires,
labels, and output formats.

## Quick start

Python 3.10 or newer is required.

```bash
python -m pip install .
ladder-fabricator examples/basic.json --validate-only
ladder-fabricator rung-text examples/basic.json --comments
ladder-fabricator examples/basic.json -o outputs/basic.svg
```

PNG support is optional:

```bash
python -m pip install ".[png]"
ladder-fabricator examples/basic.json -o outputs/basic.png
```

## Minimal source AST

```json
{
  "schema_version": 2,
  "target": {"vendor": "melsec", "series": "iq-f"},
  "title": "Run permissive",
  "comments": {"X0": "Start", "X1": "A", "X2": "B", "X3": "Stop", "Y0": "Run"},
  "rungs": [{
    "id": "run_output",
    "logic": {"and": ["X0", {"or": ["X1", "X2"]}, {"not": "X3"}]},
    "output": {"type": "coil", "device": "Y0"}
  }]
}
```

The reusable source is the circuit AST. SVG and derived connection JSON are
outputs and must not be hand-authored or fed back as source.

## Supported scope

| Area | Supported |
|---|---|
| Contacts | normally open, normally closed, rising edge, falling edge |
| Logic | nested AND, OR, NOT, outermost INV |
| Comparison | word-device `=`, `<>`, `<`, `<=`, `>`, `>=` |
| Outputs | coil, SET, RST/RES, PLS/DIFU, PLF/DIFD, PID, MOV |
| Targets | MELSEC iQ-F and KEYENCE KV-X |
| Formats | SVG, PNG, rung text, explicit connection JSON |

Timers that accumulate time, counters that increment, constant comparisons,
arithmetic other than MOV, labels, and GX3/KV STUDIO project import are not
currently supported. Unsupported inputs fail explicitly instead of being
silently approximated.

For the complete authoring contract, device tables, limits, and AI workflow,
read the [authoritative README](README.md). The machine-readable schema is at
[`schema/ladder-ast.schema.json`](schema/ladder-ast.schema.json).

## Safety boundary

Successful validation means the JSON satisfies Ladder Fabricator's structural
contract. It does not prove PLC runtime behavior, CPU-specific device ranges,
electrical wiring, sensor polarity, functional safety, or machine safety.

## License

[MIT License](LICENSE.txt).
