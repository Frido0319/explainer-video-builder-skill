import copy
import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from explainer_video_v2.manifest import validate_manifest
from explainer_video_v2.builder import prepare_project
from explainer_video_v2.pptx import render_pptx_slide
from tests.test_v2_manifest import minimal_manifest


def pptx_visual():
    return {
        "id": "slide",
        "kind": "pptx",
        "start": 0.0,
        "end": 10.0,
        "source": "deck.pptx",
        "slide": 2,
    }


class PptxInputTests(unittest.TestCase):
    def test_manifest_accepts_one_based_pptx_slide(self):
        validate_manifest(minimal_manifest(visuals=[pptx_visual()]))

    def test_manifest_rejects_zero_pptx_slide(self):
        visual = copy.deepcopy(pptx_visual())
        visual["slide"] = 0
        with self.assertRaisesRegex(ValueError, "slide must be a positive integer"):
            validate_manifest(minimal_manifest(visuals=[visual]))

    def test_prepare_project_resolves_relative_pptx_source(self):
        data = minimal_manifest(visuals=[pptx_visual()])
        with tempfile.TemporaryDirectory() as directory:
            manifest = Path(directory) / "project.json"
            manifest.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            prepared = prepare_project(manifest)
        self.assertEqual(prepared["visuals"][0]["source"], str(Path(directory) / "deck.pptx"))

    def test_render_slide_uses_read_only_conversion_and_cache(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "deck.pptx"
            source.write_bytes(b"test fixture")
            cache = root / "cache"

            def fake_run(command, **kwargs):
                if "--convert-to" in command:
                    (cache / "deck.pdf").write_bytes(b"pdf")
                else:
                    Path(f"{command[-1]}.png").write_bytes(b"png")
                return None

            with patch("explainer_video_v2.pptx.shutil.which", side_effect=lambda name: f"/usr/bin/{name}"), patch(
                "explainer_video_v2.pptx.subprocess.run", side_effect=fake_run
            ) as run:
                first = render_pptx_slide(source, 2, cache)
                second = render_pptx_slide(source, 2, cache)
                source.write_bytes(b"updated fixture")
                third = render_pptx_slide(source, 2, cache)

        self.assertEqual(first, second)
        self.assertEqual(second, third)
        self.assertEqual(first.name, "slide-2.png")
        self.assertEqual(run.call_count, 4)


if __name__ == "__main__":
    unittest.main()
