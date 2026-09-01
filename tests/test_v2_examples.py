import json
import re
import unittest
from pathlib import Path

from explainer_video_v2.manifest import validate_manifest


ROOT = Path(__file__).resolve().parents[1]
AUTOMOTIVE = ROOT / "examples" / "automotive_rag" / "project.json"
CREATE_MINIMAL = ROOT / "examples" / "create_minimal" / "project.json"


class ExampleTests(unittest.TestCase):
    def test_create_example_is_card_only_and_valid(self):
        data = json.loads(CREATE_MINIMAL.read_text(encoding="utf-8"))
        validate_manifest(data)
        self.assertEqual(data["mode"], "create")
        self.assertTrue(all(item["kind"] == "card" for item in data["visuals"]))

    def test_repository_examples_share_the_research_theme(self):
        automotive = json.loads(AUTOMOTIVE.read_text(encoding="utf-8"))
        create = json.loads(CREATE_MINIMAL.read_text(encoding="utf-8"))
        self.assertEqual(automotive["theme"], "research_ppt")
        self.assertEqual(create["theme"], "research_ppt")

    def test_neutral_example_contains_no_automotive_copy(self):
        content = CREATE_MINIMAL.read_text(encoding="utf-8")
        for forbidden in ("RAG", "E5", "K1", "发动机", "电动汽车"):
            self.assertNotIn(forbidden, content)

    def test_user_6g_assets_are_not_committed_as_example_assets(self):
        self.assertFalse((ROOT / "examples" / "6g_fountain_code").exists())

    def test_repository_docs_contain_no_machine_specific_home_path(self):
        offenders = []
        machine_home = re.compile(r"/home/[^/\s]+/")
        for path in (ROOT / "docs").rglob("*.md"):
            if machine_home.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
