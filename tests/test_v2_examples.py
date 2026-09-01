import json
import re
import unittest
from pathlib import Path

from explainer_video_v2.manifest import validate_manifest


ROOT = Path(__file__).resolve().parents[1]
CREATE_MINIMAL = ROOT / "examples" / "create_minimal" / "project.json"
ENHANCE_MINIMAL = ROOT / "examples" / "enhance_minimal" / "project.json"


class ExampleTests(unittest.TestCase):
    def test_create_example_is_card_only_and_valid(self):
        data = json.loads(CREATE_MINIMAL.read_text(encoding="utf-8"))
        validate_manifest(data)
        self.assertEqual(data["mode"], "create")
        self.assertTrue(all(item["kind"] == "card" for item in data["visuals"]))

    def test_repository_examples_share_the_research_theme(self):
        enhance = json.loads(ENHANCE_MINIMAL.read_text(encoding="utf-8"))
        create = json.loads(CREATE_MINIMAL.read_text(encoding="utf-8"))
        validate_manifest(enhance)
        self.assertEqual(enhance["mode"], "enhance")
        self.assertEqual(enhance["theme"], "research_ppt")
        self.assertEqual(create["theme"], "research_ppt")

    def test_repository_contains_only_neutral_example_directories(self):
        directories = {
            path.name
            for path in (ROOT / "examples").iterdir()
            if path.is_dir() and (path / "project.json").is_file()
        }
        self.assertEqual(directories, {"create_minimal", "enhance_minimal"})

    def test_create_example_has_no_external_sources(self):
        data = json.loads(CREATE_MINIMAL.read_text(encoding="utf-8"))
        self.assertTrue(all("source" not in visual for visual in data["visuals"]))

    def test_release_excludes_internal_prototypes_and_plans(self):
        self.assertEqual(list((ROOT / "prototypes").rglob("*.py")), [])
        self.assertEqual(list((ROOT / "docs" / "superpowers").rglob("*.md")), [])

    def test_repository_docs_contain_no_machine_specific_home_path(self):
        offenders = []
        machine_home = re.compile(r"/home/[^/\s]+/")
        for path in (ROOT / "docs").rglob("*.md"):
            if machine_home.search(path.read_text(encoding="utf-8")):
                offenders.append(str(path.relative_to(ROOT)))
        self.assertEqual(offenders, [])


if __name__ == "__main__":
    unittest.main()
