import copy
import itertools
import json
from pathlib import Path
import random
import subprocess
import sys
import tempfile
import unittest
from xml.etree import ElementTree as ET

from gx3_ladder_export import ValidationError, parse_circuit, build_bundle, render_svg
from gx3_ladder_export.model import MAX_DEPTH, MAX_NODES, MAX_RUNGS

ROOT = Path(__file__).resolve().parents[1]


def document(logic="X0", **extra):
    return {"schema_version": 1, "rungs": [
        {"id": "r1", "logic": logic, "output": {"type": "coil", "device": "Y0"}}
    ], **extra}


def requested_value(expr, state):
    """Evaluate the user's input directly, without product normalization."""
    if isinstance(expr, str):
        return state[expr]
    if "device" in expr:
        return state[expr["device"]] != (expr.get("contact", "a") == "b")
    if "not" in expr:
        return not requested_value(expr["not"], state)
    if "and" in expr:
        return all(requested_value(x, state) for x in expr["and"])
    if "or" in expr:
        return any(requested_value(x, state) for x in expr["or"])
    raise AssertionError(expr)


def graph_value(rung, state):
    """Evaluate connectivity only: joins are OR, contacts gate incoming flow."""
    incoming = {node["id"]: [] for node in rung["nodes"]}
    for edge in rung["connections"]:
        incoming[edge["to"]["node"]].append(edge["from"]["node"])
    pending = {node["id"]: node for node in rung["nodes"]}
    values = {}
    while pending:
        progressed = False
        for key, node in list(pending.items()):
            if any(source not in values for source in incoming[key]):
                continue
            power = node["kind"] == "left_rail" or any(values[source] for source in incoming[key])
            if node["kind"] == "contact":
                power = power and (state[node["device"]] != (node["contact"] == "b"))
            values[key] = power
            del pending[key]
            progressed = True
        if not progressed:
            raise AssertionError("cycle or missing source")
    return values[rung["output_condition"]["output"]]


class CircuitTests(unittest.TestCase):
    def test_shared_contacts_are_not_duplicated(self):
        logic = {"and": ["X0", {"or": ["X1", "X2"]}]}
        rung = build_bundle(parse_circuit(document(logic)))["rungs"][0]
        contacts = [node["device"] for node in rung["nodes"] if node["kind"] == "contact"]
        self.assertEqual(contacts, ["X0", "X1", "X2"])
        self.assertEqual(build_bundle(parse_circuit(document(logic)))["rungs"][0], rung)

    def test_seven_pairs_do_not_explode_into_128_branches(self):
        logic = {"and": [{"or": [f"M{i*2}", f"M{i*2+1}"]} for i in range(7)]}
        rung = build_bundle(parse_circuit(document(logic)))["rungs"][0]
        self.assertEqual(sum(node["kind"] == "contact" for node in rung["nodes"]), 14)
        self.assertLess(len(rung["connections"]), 50)

    def test_truth_tables_against_generated_connections(self):
        rng = random.Random(20260912)
        def make(depth):
            if depth == 0 or rng.random() < 0.35:
                return {"device": f"X{rng.randrange(4)}", "contact": rng.choice(["a", "b"])}
            op = rng.choice(["and", "or", "not"])
            return {op: make(depth - 1) if op == "not" else [make(depth - 1), make(depth - 1)]}
        cases = ["X0", {"not": "X0"}, {"and": ["X0", {"or": ["X1", "X2"]}]},
                 {"not": {"or": ["X0", {"and": ["X1", "X2"]}]}}]
        cases += [make(4) for _ in range(80)]
        for expr in cases:
            rung = build_bundle(parse_circuit(document(expr)))["rungs"][0]
            for bits in itertools.product([False, True], repeat=4):
                state = dict(zip(["X0", "X1", "X2", "X3"], bits))
                self.assertEqual(requested_value(expr, state), graph_value(rung, state), (expr, state))
            self.check_geometry(rung)

    def check_geometry(self, rung):
        nodes = {node["id"]: node for node in rung["nodes"]}
        positions = rung["layout"]["nodes"]
        edges = {edge["id"]: edge for edge in rung["connections"]}
        paths = rung["layout"]["connections"]
        self.assertEqual(len(edges), len(rung["connections"]))
        self.assertEqual(set(edges), {path["connection"] for path in paths})
        for path in paths:
            edge = edges[path["connection"]]
            for end, name in [(0, "from"), (-1, "to")]:
                node = nodes[edge[name]["node"]]
                pos = positions[node["id"]]
                half = {"contact": 17, "coil": 22}.get(node["kind"], 0)
                self.assertEqual(path["points"][end], [pos["x"] + (half if end == 0 else -half), pos["y"]])
            for a, b in zip(path["points"], path["points"][1:]):
                self.assertTrue(a[0] == b[0] or a[1] == b[1])
        # A rail must span every branch center, not just the last row's top.
        last_branch = max(pos["y"] for pos in positions.values())
        for rail in rung["layout"]["rails"]:
            self.assertGreater(rail["y2"], last_branch)

    def test_svg_uses_exactly_explicit_connections_and_escapes_text(self):
        doc = document({"or": ["X0", {"not": "X1"}]},
                       comments={"X0": '<script>alert("x")</script>\n日本語', "Y0": "出力"})
        bundle = build_bundle(parse_circuit(doc))
        svg = render_svg(bundle)
        root = ET.fromstring(svg)
        paths = [element for element in root.iter() if "data-connection" in element.attrib]
        self.assertEqual({e.attrib["data-connection"] for e in paths},
                         {e["id"] for rung in bundle["rungs"] for e in rung["connections"]})
        self.assertNotIn("<script>", svg)
        self.assertIn("&lt;script&gt;", svg)
        self.assertEqual(sum(e.attrib.get("class") == "mark" for e in root.iter()), 1)
        self.check_geometry(bundle["rungs"][0])

    def test_unknown_and_unsupported_inputs_fail(self):
        invalid = [
            {}, {"device": "X0", "typo": 1}, {"and": []}, {"or": ["X0"]},
            {"and": ["X0", "X1"], "or": ["X2", "X3"]},
            {"xor": ["X0", "X1"]}, {"device": "X0", "contact": "rising"},
            "D0", "T0", "Unknown1", "M1Z2", "D0.1", "X-1", "X+1", 1, True,
        ]
        for expr in invalid:
            with self.subTest(expr=expr), self.assertRaises(ValidationError):
                parse_circuit(document(expr))
        for kind in ["set", "rst", "pls", "timer", "mov", "call"]:
            doc = document()
            doc["rungs"][0]["output"]["type"] = kind
            with self.assertRaisesRegex(ValidationError, "output.type"):
                parse_circuit(doc)
        doc = document()
        doc["rungs"][0]["output"]["device"] = "X0"
        with self.assertRaises(ValidationError):
            parse_circuit(doc)

    def test_document_metadata_and_normalization(self):
        parsed = parse_circuit(document("x01a", comments={"X01A": "開始"}))
        self.assertEqual(parsed.rungs[0].logic.device, "X1A")
        self.assertEqual(dict(parsed.comments), {"X1A": "開始"})
        for version in [True, 1.0, "1", 2]:
            doc = document()
            doc["schema_version"] = version
            with self.assertRaises(ValidationError):
                parse_circuit(doc)
        for extra in [{"comments": {"X1A": "a", "x01a": "b"}},
                      {"comments": {"X0": "\u0000"}}, {"typo": 1}]:
            with self.assertRaises(ValidationError):
                parse_circuit(document(**extra))
        doc = document()
        doc["rungs"].append(copy.deepcopy(doc["rungs"][0]))
        with self.assertRaises(ValidationError):
            parse_circuit(doc)

    def test_depth_and_size_boundaries(self):
        for depth in [MAX_DEPTH - 1, MAX_DEPTH, MAX_DEPTH + 1]:
            expr = "X0"
            for _ in range(depth):
                expr = {"not": expr}
            if depth <= MAX_DEPTH:
                parse_circuit(document(expr))
            else:
                with self.assertRaisesRegex(ValidationError, "depth"):
                    parse_circuit(document(expr))
        for count in [MAX_NODES - 1, MAX_NODES, MAX_NODES + 1]:
            expr = {"and": ["X0"] * (count - 1)}
            if count <= MAX_NODES:
                parse_circuit(document(expr))
            else:
                with self.assertRaisesRegex(ValidationError, "node limit"):
                    parse_circuit(document(expr))
        for count in [0, MAX_RUNGS - 1, MAX_RUNGS, MAX_RUNGS + 1]:
            doc = document()
            doc["rungs"] = [{"id": f"r{i}", "logic": "X0", "output": {"device": "Y0"}} for i in range(count)]
            if 1 <= count <= MAX_RUNGS:
                bundle = build_bundle(parse_circuit(doc))
                self.assertEqual(len(bundle["rungs"]), count)
            else:
                with self.assertRaises(ValidationError):
                    parse_circuit(doc)

    def test_cli_and_saved_json_to_svg_work_without_gx3(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "回路.json"
            source.write_text(json.dumps(document({"and": ["X0", {"not": "X1"}]})), encoding="utf-8")
            command = [sys.executable, "-m", "gx3_ladder_export", str(source)]
            for fmt in ["svg", "json"]:
                dest = root / "出力" / f"result.{fmt}"
                result = subprocess.run([*command, "--format", fmt, "-o", str(dest)],
                                        cwd=ROOT, capture_output=True, text=True, encoding="utf-8")
                self.assertEqual(result.returncode, 0, result.stderr)
                if fmt == "svg":
                    ET.parse(dest)
                else:
                    self.assertEqual(json.loads(dest.read_text(encoding="utf-8"))["schema_version"], 1)
            # Invalid input must not create an output or overwrite an existing one.
            old = root / "untouched.svg"
            old.write_text("keep", encoding="utf-8")
            source.write_text('{"schema_version":1,"schema_version":2,"rungs":[]}', encoding="utf-8")
            result = subprocess.run([*command, "-o", str(old)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)
            self.assertEqual(old.read_text(), "keep")
            self.assertIn(b"duplicate JSON key", result.stderr)
            result = subprocess.run([*command, "-o", str(source)], cwd=ROOT, capture_output=True)
            self.assertEqual(result.returncode, 2)

    def test_example_is_valid(self):
        data = json.loads((ROOT / "examples/basic.json").read_text(encoding="utf-8"))
        bundle = build_bundle(parse_circuit(data))
        self.assertEqual(len(bundle["rungs"]), 1)
        ET.fromstring(render_svg(bundle))


if __name__ == "__main__":
    unittest.main()
