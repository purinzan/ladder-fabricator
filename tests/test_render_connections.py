"""Source AST -> real renderer, with independent terminal/segment checks."""
import copy
import json
from pathlib import Path
import random
import unittest
from xml.etree import ElementTree as ET

from gx3_ladder_export import build_bundle, parse_circuit, render_rung_text, render_svg
from gx3_ladder_export.svg import comment_lines

ROOT = Path(__file__).resolve().parents[1]
NS = {"s": "http://www.w3.org/2000/svg"}


def drawing(payload):
    circuit = parse_circuit(payload)
    # The reading pass precedes rendering, as required by the authoring contract.
    render_rung_text(circuit, comments=True)
    bundle = build_bundle(circuit)
    return bundle, ET.fromstring(render_svg(bundle))


def example():
    return json.loads((ROOT / "examples/operand-comments.json").read_text())


def net_signature(segments, ports, links=()):
    """Union actual intersecting axis-aligned segments, not declared edge IDs."""
    points = list(ports.values())
    edges = list(segments) + [(point, point) for point in points]
    roots = list(range(len(edges)))
    def root(i):
        while roots[i] != i:
            roots[i] = roots[roots[i]]
            i = roots[i]
        return i
    def join(a, b):
        roots[root(a)] = root(b)
    for i, ((ax, ay), (bx, by)) in enumerate(edges):
        for j in range(i):
            (cx, cy), (dx, dy) = edges[j]
            if (max(min(ax, bx), min(cx, dx)) <= min(max(ax, bx), max(cx, dx))
                    and max(min(ay, by), min(cy, dy)) <= min(max(ay, by), max(cy, dy))):
                join(i, j)
    indices = {point: i for i, (point, other) in enumerate(edges) if point == other}
    for a, b in links:
        join(indices[ports[a]], indices[ports[b]])
    groups = {}
    for name, point in ports.items():
        groups.setdefault(root(indices[point]), []).append(name)
    return sorted(tuple(sorted(names)) for names in groups.values())


def declared_nets(rung):
    # Unique synthetic coordinates avoid using the product's placement as the oracle.
    ports = {(node["id"], side): (i * 2 + j, 0)
             for i, node in enumerate(rung["nodes"]) for j, side in enumerate(("in", "out"))}
    links = [((e["from"]["node"], e["from"]["port"]), (e["to"]["node"], e["to"]["port"]))
             for e in rung["connections"]]
    links += [((n["id"], "in"), (n["id"], "out")) for n in rung["nodes"]
              if n["kind"] in ("junction", "left_rail", "right_rail")]
    return net_signature([], ports, links)


def rendered_nets(rung, group):
    segments, ports = [], {}
    for line in group.findall("s:polyline[@class='wire']", NS):
        points = [tuple(map(float, value.split(","))) for value in line.get("points").split()]
        segments.extend(zip(points, points[1:]))
    for node in rung["nodes"]:
        identifier, kind = node["id"], node["kind"]
        if kind == "junction":
            pos = rung["layout"]["nodes"][identifier]
            a = b = (pos["x"], pos["y"])
        elif kind.endswith("rail"):
            line = group.find(f"s:line[@data-node='{identifier}']", NS)
            x, y1, y2 = [float(line.get(key)) for key in ("x1", "y1", "y2")]
            segments.append(((x, y1), (x, y2)))
            a = b = (x, rung["layout"]["nodes"][identifier]["y"])
        else:
            symbol = group.find(f"s:g[@data-node='{identifier}']", NS)
            if kind == "contact":
                bars = symbol.findall("s:line[@class='symbol']", NS)
                ends = sorted((float(bar.get("x1")), (float(bar.get("y1")) + float(bar.get("y2"))) / 2) for bar in bars)
                a, b = ends
            elif kind == "coil" and symbol.find("s:circle", NS) is not None:
                circle = symbol.find("s:circle", NS)
                x, y, r = [float(circle.get(key)) for key in ("cx", "cy", "r")]
                a, b = (x-r, y), (x+r, y)
            elif kind == "coil":
                # A quadratic parenthesis touches its wire at t=0.5, not at its control point.
                ends = []
                for curve in symbol.findall("s:path", NS):
                    values = curve.get("d").replace("M", "").replace("Q", "").split()
                    x0, y0, x1, y1, x2, y2 = map(float, values)
                    ends.append(((x0 + 2*x1 + x2)/4, (y0 + 2*y1 + y2)/4))
                a, b = sorted(ends)
            else:
                rect = symbol.find("s:rect[@class='instruction-box']", NS)
                if rect is None:
                    rect = symbol.find("s:rect[@class='symbol']", NS)
                x, y, w, h = [float(rect.get(key)) for key in ("x", "y", "width", "height")]
                a, b = (x, y+h/2), (x+w, y+h/2)
        ports[identifier, "in"], ports[identifier, "out"] = a, b
    return net_signature(segments, ports)


class RenderConnectionsTests(unittest.TestCase):
    def assert_connections(self, payload):
        bundle, svg = drawing(payload)
        for rung in bundle["rungs"]:
            group = svg.find(f"s:g[@id='{rung['id']}']", NS)
            self.assertEqual(declared_nets(rung), rendered_nets(rung, group), rung["id"])
        return bundle, svg

    def test_operand_comments_follow_their_own_cells(self):
        bundle, svg = drawing(example())
        for rung in bundle["rungs"]:
            for node in rung["nodes"]:
                if node["kind"] not in ("instruction", "predicate"):
                    continue
                group = svg.find(f".//s:g[@data-node='{node['id']}']", NS)
                labels = {n.text: float(n.get("x")) for n in group.findall("s:text[@class='operand']", NS)}
                comments = group.findall("s:text[@class='comment']", NS)
                for operand in node["operands"]:
                    self.assertIn(operand, labels)
                    text = example()["comments"].get(operand, "")
                    for part in comment_lines(text):
                        if part:
                            self.assertTrue(any(n.text == part and float(n.get("x")) == labels[operand] for n in comments), operand)
                box = group.find("s:rect[@class='instruction-box']", NS)
                self.assertEqual(float(box.get("width")), 104 * (1 + len(node["operands"])) - 10)

    def test_comment_wrap_uses_display_width_and_marks_truncation(self):
        self.assertEqual(comment_lines("A" * 11), ["A" * 11])
        self.assertEqual(comment_lines("A" * 12), ["A" * 12])
        self.assertEqual(comment_lines("ABCDEFGHIJKLM"), ["ABCDEFGHIJKL", "M"])
        self.assertEqual(comment_lines("あいうえおかき"), ["あいうえおか", "き"])
        self.assertEqual(comment_lines("A" * 24), ["A" * 12, "A" * 12])
        self.assertEqual(comment_lines("A" * 23), ["A" * 12, "A" * 11])
        self.assertTrue(comment_lines("A" * 25)[-1].endswith("…"))
        self.assertEqual(comment_lines(""), [])
        self.assertTrue(comment_lines("A" * 11 + "あ" * 6 + "B")[-1].endswith("…"))
        self.assertEqual(comment_lines("e\u0301" * 12), ["e\u0301" * 12])

    def test_empty_and_repeated_operand_comment_slots_are_preserved(self):
        payload = example()
        payload["comments"] = {"D300": "LastSlot"}
        bundle, svg = drawing(payload)
        pid = next(n for n in bundle["rungs"][1]["nodes"] if n["kind"] == "instruction")
        self.assertEqual([r["comment"] for r in pid["operand_comments"]], ["", "", "", "LastSlot"])
        group = svg.find(f".//s:g[@data-node='{pid['id']}']", NS)
        label = next(n for n in group.findall("s:text[@class='operand']", NS) if n.text == "D300")
        self.assertEqual(group.find("s:text[@class='comment']", NS).get("x"), label.get("x"))
        payload["rungs"] = [{"id": "repeat", "logic": "M0", "output": {"type": "mov", "source": "D300", "destination": "D300"}}]
        bundle, svg = drawing(payload)
        comments = svg.findall(".//s:text[@class='comment']", NS)
        self.assertEqual([n.text for n in comments], ["LastSlot", "LastSlot"])
        self.assertNotEqual(comments[0].get("x"), comments[1].get("x"))

    def test_geometry_checker_detects_a_missing_drawn_wire(self):
        payload = example()
        bundle, svg = drawing(payload)
        rung = bundle["rungs"][0]
        group = copy.deepcopy(svg.find(f"s:g[@id='{rung['id']}']", NS))
        group.remove(group.find("s:polyline[@class='wire']", NS))
        self.assertNotEqual(declared_nets(rung), rendered_nets(rung, group))

    def test_seeded_nested_branches_preserve_geometric_nets(self):
        rng = random.Random(20261103)
        def logic(depth):
            if not depth or rng.random() < .3:
                return f"M{rng.randrange(5)}"
            return {rng.choice(("and", "or")): [logic(depth-1), logic(depth-1)]}
        for _ in range(40):
            self.assert_connections({"schema_version": 1, "rungs": [{"id": "nested", "logic": logic(4), "output": {"device": "Y0"}}]})

    def test_actual_svg_nets_match_declared_connections_for_both_targets(self):
        for target, contact, output in [("melsec", "M0", "Y0"), ("keyence", "MR0", "R0")]:
            for logic in (contact, {"or": [contact, {"and": [contact, {"or": [contact, contact]}]}]},
                          {"and": [{"or": [contact, contact]}, {"or": [contact, contact]}]},
                          {"and": [contact] * 90}):
                self.assert_connections({"schema_version": 2, "target": {"vendor": target, "series": "iq-f" if target == "melsec" else "kv-x"},
                                         "rungs": [{"id": "synthetic", "logic": logic, "output": {"device": output}}]})
        self.assert_connections(example())
        payload = example()
        compare = {"compare": {"operator": ">=", "left": "D101", "right": "D100"}}
        payload["rungs"][1]["logic"] = {"and": ["M0", {"or": [compare, {"and": ["M1", compare]}]}]}
        self.assert_connections(payload)
        self.assert_connections({"schema_version": 2, "target": {"vendor": "keyence", "series": "kv-x"},
                                 "rungs": [{"id": "word", "logic": {"compare": {"operator": "<>", "left": "DM0", "right": "DM10"}},
                                            "output": {"type": "mov", "source": "DM0", "destination": "DM10"}}]})

    def test_long_rung_keeps_all_contacts_and_last_branch_reaches_rails(self):
        payload = {"schema_version": 1, "rungs": [{"id": "wide", "logic": {"and": [f"M{i}" for i in range(90)]}, "output": {"device": "Y0"}},
                   {"id": "branches", "logic": {"or": ["M0", {"or": ["M1", "M2"]}]}, "output": {"device": "Y1"}}]}
        bundle, svg = self.assert_connections(payload)
        self.assertEqual(sum(n["kind"] == "contact" for n in bundle["rungs"][0]["nodes"]), 90)
        self.assertEqual(len(svg.findall(".//s:g[@data-node]/s:line[@class='symbol']", NS)), 186)
        for rung in bundle["rungs"]:
            bottom = max(p["y"] for p in rung["layout"]["nodes"].values())
            self.assertTrue(all(r["y2"] > bottom for r in rung["layout"]["rails"]))


if __name__ == "__main__":
    unittest.main()
