import copy
import json
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
MODULE_DIR = ROOT / "prototypes" / "v2_editing"
sys.path.insert(0, str(MODULE_DIR))

from build_prototype import (
    EDITED_FILENAME,
    build_filter_graph,
    load_timeline,
    parse_ass_time,
    rebase_ass,
    render_assets,
    validate_timeline,
)


TIMELINE = MODULE_DIR / "timeline.json"


class TimelineValidationTests(unittest.TestCase):
    def setUp(self):
        self.data = load_timeline(TIMELINE)

    def test_repository_timeline_is_valid(self):
        validate_timeline(self.data)

    def test_repository_timeline_contains_no_machine_specific_home_path(self):
        raw = json.loads(TIMELINE.read_text(encoding="utf-8"))
        for key in ("source", "reference", "subtitles", "output_dir"):
            self.assertTrue(raw[key].startswith("${AUTOMOTIVE_RAG_DELIVERY}/"))

    def test_timeline_expands_delivery_environment_variable(self):
        with patch.dict("os.environ", {"AUTOMOTIVE_RAG_DELIVERY": "/tmp/delivery"}):
            data = load_timeline(TIMELINE)
        self.assertEqual(data["source"], "/tmp/delivery/驭远智擎_发动机与电动汽车专属RAG对比_最终版.mp4")
        self.assertEqual(data["output_dir"], "/tmp/delivery/v2_prototype")

    def test_clip_is_exactly_28_seconds(self):
        clip = self.data["clip"]
        self.assertAlmostEqual(clip["end"] - clip["start"], 28.0)

    def test_rejects_zoom_over_limit(self):
        data = copy.deepcopy(self.data)
        data["zoom_segments"][0]["zoom_end"] = 1.09
        with self.assertRaisesRegex(ValueError, "zoom"):
            validate_timeline(data)

    def test_rejects_overlapping_zoom_segments(self):
        data = copy.deepcopy(self.data)
        data["zoom_segments"][1]["start"] = 15.0
        with self.assertRaisesRegex(ValueError, "overlap"):
            validate_timeline(data)

    def test_rejects_callout_in_subtitle_band(self):
        data = copy.deepcopy(self.data)
        data["callouts"][0]["y"] = 821
        with self.assertRaisesRegex(ValueError, "subtitle safe"):
            validate_timeline(data)


class SubtitleRebaseTests(unittest.TestCase):
    def test_parse_ass_time(self):
        self.assertAlmostEqual(parse_ass_time("0:01:03.25"), 63.25)

    def test_rebase_keeps_only_overlapping_events(self):
        source_text = """[Script Info]
PlayResX: 1920
[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:30.00,0:00:35.00,Default,,0,0,0,,before
Dialogue: 0,0:00:38.00,0:00:42.50,Default,,0,0,0,,inside
Dialogue: 0,0:01:04.00,0:01:06.00,Default,,0,0,0,,after
"""
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.ass"
            destination = Path(directory) / "rebased.ass"
            source.write_text(source_text, encoding="utf-8")
            retained = rebase_ass(source, destination, 36.0, 64.0)
            result = destination.read_text(encoding="utf-8")

        self.assertEqual(retained, 1)
        self.assertIn("Dialogue: 0,0:00:02.00,0:00:06.50", result)
        self.assertIn("inside", result)
        self.assertNotIn("before", result)
        self.assertNotIn("after", result)

    def test_render_assets_stay_inside_declared_bounds(self):
        data = load_timeline(TIMELINE)
        with tempfile.TemporaryDirectory() as directory:
            assets = render_assets(data, Path(directory))
            self.assertEqual(set(assets), {"chapter", "callout_0", "callout_1", "callout_2", "callout_3"})
            for path in assets.values():
                self.assertTrue(path.is_file())


class FilterGraphTests(unittest.TestCase):
    def test_smooth_build_uses_a_new_delivery_filename(self):
        self.assertEqual(EDITED_FILENAME, "V2精剪样片_平滑推进版_36-64s.mp4")

    def test_zoom_uses_four_x_prescale_to_avoid_integer_pixel_jitter(self):
        data = load_timeline(TIMELINE)
        assets = {
            "chapter": Path("chapter.png"),
            "callout_0": Path("callout_0.png"),
            "callout_1": Path("callout_1.png"),
            "callout_2": Path("callout_2.png"),
            "callout_3": Path("callout_3.png"),
        }
        graph = build_filter_graph(data, assets, Path("rebased.ass"))
        self.assertIn("scale=7680:4320:flags=lanczos,zoompan", graph)

    def test_filter_graph_contains_all_visual_events_and_subtitles(self):
        data = load_timeline(TIMELINE)
        assets = {
            "chapter": Path("chapter.png"),
            "callout_0": Path("callout_0.png"),
            "callout_1": Path("callout_1.png"),
            "callout_2": Path("callout_2.png"),
            "callout_3": Path("callout_3.png"),
        }
        graph = build_filter_graph(data, assets, Path("rebased.ass"))
        self.assertIn("zoompan", graph)
        self.assertIn("gte(on,192)*lt(on,384)", graph)
        self.assertIn("gte(on,504)*lt(on,672)", graph)
        self.assertNotIn("in_time", graph)
        self.assertEqual(graph.count("overlay="), 5)
        self.assertIn("between(t,16.000,16.800)", graph)
        self.assertIn("between(t,23.000,26.500)", graph)
        self.assertIn("subtitles='rebased.ass'", graph)

    def test_declared_visual_labels_stay_above_subtitle_band(self):
        data = load_timeline(TIMELINE)
        self.assertLess(data["chapter"]["y"] + 100, 820)
        for callout in data["callouts"]:
            self.assertLessEqual(callout["y"] + 80, 820)

if __name__ == "__main__":
    unittest.main()
