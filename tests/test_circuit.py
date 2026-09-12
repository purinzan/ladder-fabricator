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


def requested_value(expr, state, previous=None):
    """Evaluate the user's input directly, without product normalization."""
    previous = previous or {}
    if isinstance(expr, str):
        return state[expr]
    if "device" in expr:
        role = expr.get("contact", "a")
        if role == "rising":
            return state[expr["device"]] and not previous.get(expr["device"], False)
        return state[expr["device"]] != (role == "b")
    if "not" in expr:
        return not requested_value(expr["not"], state, previous)
    if "inv" in expr:
        return not requested_value(expr["inv"], state, previous)
    if "and" in expr:
        return all(requested_value(x, state, previous) for x in expr["and"])
    if "or" in expr:
        return any(requested_value(x, state, previous) for x in expr["or"])
    raise AssertionError(expr)


def graph_value(rung, state, previous=None):
    """Evaluate connectivity only: joins are OR, contacts gate incoming flow."""
    previous = previous or {}
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
                if node["contact"] == "rising":
                    contact = state[node["device"]] and not previous.get(node["device"], False)
                else:
                    contact = state[node["device"]] != (node["contact"] == "b")
                power = power and contact
            elif node["kind"] == "inverter":
                power = not power
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
                half = {"contact": 17, "coil": 22, "instruction": 115,
                        "inverter": 24}.get(node["kind"], 0)
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

    def test_set_rst_rising_and_inv_are_preserved_and_rendered(self):
        doc = {
            "schema_version": 1,
            "comments": {"X0": "起動パルス", "X1": "解除条件", "Y0": "保持出力"},
            "rungs": [
                {"id": "set_on_rise", "logic": {"device": "X0", "contact": "rising"},
                 "output": {"type": "set", "device": "Y0"}},
                {"id": "reset", "logic": "X1", "output": {"type": "rst", "device": "C0"}},
                {"id": "pulse", "logic": "X0", "output": {"type": "pls", "device": "M1"}},
                {"id": "inverted", "logic": {"inv": {"and": ["X0", "X1"]}},
                 "output": {"device": "M0"}},
            ],
        }
        circuit = parse_circuit(doc)
        self.assertEqual([rung.output_type for rung in circuit.rungs], ["set", "rst", "pls", "coil"])
        bundle = build_bundle(circuit)
        self.assertEqual([rung["output_condition"]["action"] for rung in bundle["rungs"]],
                         ["SET", "RST", "PLS", "OUT"])
        self.assertEqual(bundle["rungs"][0]["output_condition"]["logic"]["contact"], "rising")
        self.assertEqual([rung["output_condition"]["target"] for rung in bundle["rungs"]],
                         ["Y0", "C0", "M1", "M0"])
        self.assertEqual(bundle["rungs"][3]["output_condition"]["logic"]["op"], "inv")
        self.assertTrue(any(node["kind"] == "instruction" and node["opcode"] == "SET"
                            for node in bundle["rungs"][0]["nodes"]))
        self.assertEqual(next(node for node in bundle["rungs"][1]["nodes"]
                              if node["kind"] == "instruction")["operands"], ["C0"])
        self.assertTrue(any(node["kind"] == "inverter"
                            for node in bundle["rungs"][3]["nodes"]))

        states = [False, False, True, True, False, True]
        previous = False
        observed = []
        for current in states:
            observed.append(graph_value(bundle["rungs"][0], {"X0": current}, {"X0": previous}))
            previous = current
        self.assertEqual(observed, [False, False, True, False, False, True])
        for x0, x1 in itertools.product([False, True], repeat=2):
            state = {"X0": x0, "X1": x1}
            self.assertEqual(graph_value(bundle["rungs"][3], state), not (x0 and x1))

        svg = render_svg(bundle)
        ET.fromstring(svg)
        self.assertIn(">SET</text>", svg)
        self.assertIn(">RST</text>", svg)
        self.assertIn(">PLS</text>", svg)
        self.assertIn(">Y0</text>", svg)
        self.assertIn(">C0</text>", svg)
        self.assertIn(">M1</text>", svg)
        self.assertIn(">INV</text>", svg)
        self.assertIn('class="opcode-cell"', svg)
        self.assertIn('class="box-separator"', svg)
        for rung in bundle["rungs"]:
            self.check_geometry(rung)

    def test_unknown_and_unsupported_inputs_fail(self):
        invalid = [
            {}, {"device": "X0", "typo": 1}, {"and": []}, {"or": ["X0"]},
            {"and": ["X0", "X1"], "or": ["X2", "X3"]},
            {"xor": ["X0", "X1"]}, {"device": "X0", "contact": "falling"},
            {"and": ["X0", {"inv": "X1"}]}, {"not": {"device": "X0", "contact": "rising"}},
            "D0", "T0", "Unknown1", "M1Z2", "D0.1", "X-1", "X+1", 1, True,
        ]
        for expr in invalid:
            with self.subTest(expr=expr), self.assertRaises(ValidationError):
                parse_circuit(document(expr))
        for kind in ["reset", "timer", "mov", "call"]:
            doc = document()
            doc["rungs"][0]["output"]["type"] = kind
            with self.assertRaisesRegex(ValidationError, "output.type"):
                parse_circuit(doc)
        doc = document()
        doc["rungs"][0]["output"]["device"] = "X0"
        with self.assertRaises(ValidationError):
            parse_circuit(doc)

    def test_rst_accepts_gx_works_direct_reset_targets(self):
        reset_targets = [
            "X0", "Y0", "M0", "L0", "SM0", "F0", "B0", "SB0", "S0",
            "T0", "ST0", "C0", "D0", "W0", "SD0", "SW0", "R0", "Z0", "LC0", "LZ0",
        ]
        for target in reset_targets:
            with self.subTest(target=target):
                doc = document()
                doc["rungs"][0]["output"] = {"type": "rst", "device": target}
                parsed = parse_circuit(doc)
                self.assertEqual(parsed.rungs[0].output, target)
        for output_type in ["coil", "set", "pls"]:
            with self.subTest(output_type=output_type):
                doc = document()
                doc["rungs"][0]["output"] = {"type": output_type, "device": "C0"}
                with self.assertRaisesRegex(ValidationError, "unsupported device type C"):
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
        for name, rung_count in [("basic.json", 1), ("instructions.json", 4)]:
            with self.subTest(name=name):
                data = json.loads((ROOT / "examples" / name).read_text(encoding="utf-8"))
                bundle = build_bundle(parse_circuit(data))
                self.assertEqual(len(bundle["rungs"]), rung_count)
                ET.fromstring(render_svg(bundle))


if __name__ == "__main__":
    unittest.main()
