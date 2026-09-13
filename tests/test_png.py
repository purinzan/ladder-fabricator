import importlib.util
import json
from pathlib import Path
import struct
import subprocess
import sys
import tempfile
import unittest

from gx3_ladder_export import build_bundle, parse_circuit, render_png


ROOT = Path(__file__).resolve().parents[1]
HAS_CAIROSVG = importlib.util.find_spec("cairosvg") is not None


def document():
    return {
        "schema_version": 1,
        "title": "PNG出力試験",
        "comments": {"X0": "開始条件", "Y0": "運転出力"},
        "rungs": [{
            "id": "run",
            "logic": "X0",
            "output": {"type": "coil", "device": "Y0"},
        }],
    }


def png_size(data: bytes) -> tuple[int, int]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise AssertionError("not a PNG")
    return struct.unpack(">II", data[16:24])


class PngOutputTests(unittest.TestCase):
    def test_invalid_scale_is_rejected_without_optional_dependency(self):
        circuit = parse_circuit(document())
        for scale in (0, 0.1, 5, float("inf"), float("nan"), True):
            with self.subTest(scale=scale), self.assertRaises(ValueError):
                render_png(circuit, scale=scale)

    @unittest.skipUnless(HAS_CAIROSVG, "requires gx3-ladder-export[png]")
    def test_render_png_uses_svg_layout_and_default_double_scale(self):
        circuit = parse_circuit(document())
        bundle = build_bundle(circuit)
        data = render_png(circuit)
        self.assertEqual(png_size(data), (bundle["width"] * 2, bundle["height"] * 2))

    @unittest.skipUnless(HAS_CAIROSVG, "requires gx3-ladder-export[png]")
    def test_cli_infers_png_from_output_extension(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            source = root / "回路.json"
            output = root / "出力" / "ラダー.PNG"
            source.write_text(json.dumps(document(), ensure_ascii=False), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "gx3_ladder_export", str(source),
                 "--png-scale", "1", "-o", str(output)],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 0, result.stderr)
            bundle = build_bundle(parse_circuit(document()))
            self.assertEqual(png_size(output.read_bytes()),
                             (bundle["width"], bundle["height"]))

    def test_png_scale_is_rejected_for_non_png_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / "circuit.json"
            source.write_text(json.dumps(document()), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "gx3_ladder_export", str(source),
                 "--format", "svg", "--png-scale", "2"],
                cwd=ROOT, capture_output=True, text=True, encoding="utf-8",
            )
            self.assertEqual(result.returncode, 2)
            self.assertIn("requires PNG output", result.stderr)


if __name__ == "__main__":
    unittest.main()

