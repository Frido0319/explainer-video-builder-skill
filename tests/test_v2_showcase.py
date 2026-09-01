import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from PIL import Image

from explainer_video_v2.manifest import validate_manifest
from explainer_video_v2.pronunciation import rewrite_narration


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "prototypes" / "v2_showcase"
sys.path.insert(0, str(MODULE_DIR))

from build_showcase import CARD_FILTER_PREFIX, load_timeline, render_card, render_label, validate_timeline


TIMELINE = MODULE_DIR / "timeline.json"
V2_EXAMPLE = ROOT / "examples" / "automotive_rag" / "project.json"


class ShowcaseTimelineTests(unittest.TestCase):
    def setUp(self):
        self.data = load_timeline(TIMELINE)

    def test_repository_timeline_is_valid(self):
        validate_timeline(self.data)

    def test_repository_timeline_contains_no_machine_specific_home_path(self):
        raw = json.loads(TIMELINE.read_text(encoding="utf-8"))
        for key in ("source_main", "source_generalization", "output_dir"):
            self.assertTrue(raw[key].startswith("${AUTOMOTIVE_RAG_DELIVERY}/"))

    def test_timeline_expands_delivery_environment_variable(self):
        with patch.dict("os.environ", {"AUTOMOTIVE_RAG_DELIVERY": "/tmp/delivery"}):
            data = load_timeline(TIMELINE)
        self.assertEqual(data["source_main"], "/tmp/delivery/驭远智擎_发动机与电动汽车专属RAG对比_最终版.mp4")
        self.assertEqual(data["output_dir"], "/tmp/delivery/v2_showcase")

    def test_automotive_example_migrates_to_generic_v2_manifest(self):
        data = json.loads(V2_EXAMPLE.read_text(encoding="utf-8"))
        validate_manifest(data)
        rewritten = rewrite_narration(data)
        self.assertEqual(data["mode"], "enhance")
        self.assertEqual(data["duration"], 72.0)
        self.assertEqual(len(data["visuals"]), 13)
        self.assertEqual(len(data["narration"]), 11)
        self.assertNotIn("重排", "".join(item["text"] for item in rewritten["narration"]))
        self.assertIn("${AUTOMOTIVE_RAG_DELIVERY}", json.dumps(data, ensure_ascii=False))

    def test_generic_package_contains_no_automotive_copy(self):
        package = ROOT / "explainer_video_v2"
        content = "".join(path.read_text(encoding="utf-8") for path in package.glob("*.py"))
        for forbidden in ("E5", "K1", "发动机", "电动汽车"):
            self.assertNotIn(forbidden, content)

    def test_visuals_are_contiguous_and_total_72_seconds(self):
        visuals = self.data["visuals"]
        self.assertEqual(visuals[0]["start"], 0.0)
        self.assertEqual(visuals[-1]["end"], 72.0)
        for first, second in zip(visuals, visuals[1:]):
            self.assertEqual(first["end"], second["start"])

    def test_metrics_match_authoritative_report(self):
        self.assertEqual(
            self.data["metrics"],
            {
                "index_blocks": 1817,
                "four_before": 85.8,
                "four_after": 96.5,
                "general_before": 60,
                "general_after": 89,
                "variance_before": 83,
                "variance_after": 29,
                "traceable": "9/9",
            },
        )

    def test_narration_stays_inside_video(self):
        for narration in self.data["narration"]:
            self.assertGreaterEqual(narration["start"], 0)
            self.assertLessEqual(narration["end_limit"], 72.0)
            self.assertLess(narration["start"], narration["end_limit"])

    def test_each_generalization_case_has_its_own_narration(self):
        narration_ids = {item["id"] for item in self.data["narration"]}
        self.assertTrue({"n7_k1", "n7_k3", "n7_k4"}.issubset(narration_ids))

    def test_reordering_is_spelled_out_for_chong_pronunciation(self):
        narration_text = "".join(item["text"] for item in self.data["narration"])
        builder_text = (MODULE_DIR / "build_showcase.py").read_text(encoding="utf-8")
        self.assertNotIn("重排", narration_text)
        self.assertIn("重新排序", narration_text)
        self.assertNotIn("交叉重排", builder_text)
        self.assertIn("交叉重新排序", builder_text)

    def test_pipeline_card_uses_reference_ppt_light_palette(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pipeline.png"
            render_card("pipeline", output)
            image = Image.open(output).convert("RGB")
        self.assertGreater(min(image.getpixel((960, 330))), 235)
        bottom_bar = image.getpixel((960, 840))
        self.assertGreater(bottom_bar[2], bottom_bar[0] + 40)
        self.assertGreater(bottom_bar[2], bottom_bar[1] + 10)

    def test_ppt_card_keeps_bottom_subtitle_band_clear(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "pipeline.png"
            render_card("pipeline", output)
            image = Image.open(output).convert("RGB")
        self.assertGreater(min(image.getpixel((960, 970))), 235)

    def test_cards_use_four_x_lanczos_prescale(self):
        self.assertIn("scale=7680:4320:flags=lanczos,zoompan", CARD_FILTER_PREFIX)

    def test_real_footage_label_is_placed_in_top_right_safe_area(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "label.png"
            render_label("E5 · 燃烧过程  43% → 86%", output)
            alpha = Image.open(output).getchannel("A")
            bbox = alpha.getbbox()
        self.assertIsNotNone(bbox)
        self.assertGreaterEqual(bbox[0], 1100)
        self.assertLessEqual(bbox[2], 1860)

    def test_rejects_gap_in_visual_timeline(self):
        data = copy.deepcopy(self.data)
        data["visuals"][2]["start"] = 11.5
        with self.assertRaisesRegex(ValueError, "contiguous"):
            validate_timeline(data)


if __name__ == "__main__":
    unittest.main()
