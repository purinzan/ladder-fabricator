import json
from pathlib import Path
import sqlite3
import tempfile
import unittest

from tools.build_keyence_reference_db import build_database


ROOT = Path(__file__).resolve().parents[1]


class KeyenceReferenceTests(unittest.TestCase):
    def test_reference_json_builds_searchable_database(self):
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "kv.sqlite3"
            counts = build_database(ROOT / "data" / "keyence_kv", output)
            self.assertGreaterEqual(counts["sources"], 10)
            self.assertGreaterEqual(counts["families"], 17)
            self.assertGreaterEqual(counts["mappings"], 30)
            self.assertGreaterEqual(counts["devices"], 15)
            connection = sqlite3.connect(output)
            try:
                reset = connection.execute(
                    "SELECT gx3_json, kv_json, confidence FROM instruction_mappings WHERE id='reset'"
                ).fetchone()
                self.assertEqual(json.loads(reset[0]), ["RST"])
                self.assertEqual(json.loads(reset[1]), ["RES"])
                self.assertEqual(reset[2], "verified")
                self.assertEqual(connection.execute(
                    "SELECT COUNT(*) FROM instruction_sources"
                ).fetchone()[0], sum(len(row["sources"]) for row in json.loads(
                    (ROOT / "data" / "keyence_kv" / "instruction_differences.json").read_text()
                )["mappings"]))
                self.assertEqual(connection.execute(
                    "SELECT status FROM instruction_families WHERE id='timer-counter'"
                ).fetchone()[0], "core-mapped")
            finally:
                connection.close()


if __name__ == "__main__":
    unittest.main()
