from pathlib import Path
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
            "keyence-kv-x", "--validate-only", "rung-text",
        )
        for text in required:
            with self.subTest(authoring_form=text):
                self.assertIn(text, readme)


if __name__ == "__main__":
    unittest.main()

