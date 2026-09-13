from pathlib import Path
import json
import unittest


ROOT = Path(__file__).resolve().parents[1]


class DocumentationContractTests(unittest.TestCase):
    def test_ai_entry_points_route_to_the_authoritative_readme(self):
        entry_points = {
            "AGENTS.md": ("README.md", "AST・命令リファレンス"),
            "CLAUDE.md": ("AGENTS.md", "README.md"),
            "GEMINI.md": ("AGENTS.md", "README.md"),
            "AI_INSTRUCTIONS.md": ("AGENTS.md", "README.md"),
            ".github/copilot-instructions.md": ("AGENTS.md", "README.md"),
            ".cursor/rules/ladder-fabricator.mdc": ("alwaysApply: true", "README.md"),
            ".cursorrules": ("AGENTS.md", "README.md"),
            ".windsurfrules": ("AGENTS.md", "README.md"),
            ".clinerules": ("AGENTS.md", "README.md"),
            ".aider.conf.yml": ("AGENTS.md", "README.md"),
            "llms.txt": ("AGENTS.md", "README.md"),
        }
        for relative, required_text in entry_points.items():
            with self.subTest(entry_point=relative):
                content = (ROOT / relative).read_text(encoding="utf-8")
                for text in required_text:
                    self.assertIn(text, content)

    def test_readme_names_every_supported_authoring_form(self):
        readme = (ROOT / "README.md").read_text(encoding="utf-8")
        required = (
            '"contact":"a"', '"contact":"b"', '"contact":"rising"',
            '"contact":"falling"', '"and"', '"or"', '"not"', '"inv"',
            '"compare"', '"type":"coil"', '"type":"set"',
            '"type":"rst"', '"type":"pls"', '"type":"plf"',
            '"type": "pid"', '"type":"mov"', "melsec-iq-f",
            "keyence-kv-x", "--validate-only", "rung-text", "--format png",
            "--png-scale", '".[png]"',
        )
        for text in required:
            with self.subTest(authoring_form=text):
                self.assertIn(text, readme)

    def test_open_source_and_discovery_assets_are_consistent(self):
        license_text = (ROOT / "LICENSE.txt").read_text(encoding="utf-8")
        pyproject = (ROOT / "pyproject.toml").read_text(encoding="utf-8")
        website = (ROOT / "docs" / "index.html").read_text(encoding="utf-8")
        chinese = (ROOT / "README_ZH-CN.md").read_text(encoding="utf-8")
        self.assertTrue(license_text.startswith("MIT License"))
        self.assertIn('license = "MIT"', pyproject)
        self.assertIn('"@type": "SoftwareSourceCode"', website)
        self.assertIn("OAI-SearchBot", (ROOT / "docs" / "robots.txt").read_text(encoding="utf-8"))
        self.assertIn("Ladder Fabricator", chinese)
        schema = json.loads((ROOT / "schema" / "ladder-ast.schema.json").read_text(encoding="utf-8"))
        self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")

    def test_public_site_does_not_reference_missing_local_files(self):
        required = (
            "docs/assets/basic.svg",
            "docs/assets/basic.png",
            "docs/styles.css",
            "docs/llms.txt",
            "docs/sitemap.xml",
            "docs/zh-cn/index.html",
        )
        for relative in required:
            with self.subTest(path=relative):
                self.assertTrue((ROOT / relative).is_file())


if __name__ == "__main__":
    unittest.main()
