import copy
import json
import tempfile
import unittest
from pathlib import Path

from explainer_video_v2.manifest import load_manifest, validate_manifest


def card_segment(start=0.0, end=10.0, segment_id="card"):
    return {
        "id": segment_id,
        "kind": "card",
        "start": start,
        "end": end,
        "card": {"template": "hero", "title": "测试"},
    }


def clip_segment(start=0.0, end=10.0):
    return {
        "id": "clip",
        "kind": "clip",
        "start": start,
        "end": end,
        "source": "/tmp/source.mp4",
        "source_start": 0.0,
        "source_duration": 10.0,
    }


def minimal_manifest(mode="create", visuals=None):
    return {
        "version": 2,
        "mode": mode,
        "theme": "research_ppt",
        "duration": 10.0,
        "fps": 24,
        "width": 1920,
        "height": 1080,
        "output_dir": "/tmp/v2-output",
        "output_name": "test.mp4",
        "visuals": visuals or [card_segment()],
        "narration": [
            {"id": "n1", "start": 0.0, "end_limit": 10.0, "text": "测试旁白"}
        ],
        "verification": {"frame_times": [5.0], "duration_tolerance": 0.1},
    }


class ManifestTests(unittest.TestCase):
    def test_load_manifest_returns_valid_json(self):
        data = minimal_manifest()
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            loaded = load_manifest(path)
        self.assertEqual(loaded, data)

    def test_enhance_requires_clip(self):
        data = minimal_manifest(mode="enhance", visuals=[card_segment()])
        with self.assertRaisesRegex(ValueError, "enhance requires at least one clip"):
            validate_manifest(data)

    def test_enhance_accepts_clip(self):
        validate_manifest(minimal_manifest(mode="enhance", visuals=[clip_segment()]))

    def test_visuals_must_be_contiguous(self):
        data = minimal_manifest(
            visuals=[card_segment(0.0, 4.0), card_segment(5.0, 10.0, "card-2")]
        )
        with self.assertRaisesRegex(ValueError, "contiguous"):
            validate_manifest(data)

    def test_visuals_must_cover_duration(self):
        data = minimal_manifest(visuals=[card_segment(0.0, 9.0)])
        with self.assertRaisesRegex(ValueError, "cover the full duration"):
            validate_manifest(data)

    def test_rejects_unsupported_theme(self):
        data = minimal_manifest()
        data["theme"] = "unknown"
        with self.assertRaisesRegex(ValueError, "unsupported theme"):
            validate_manifest(data)

    def test_narration_must_stay_inside_timeline(self):
        data = copy.deepcopy(minimal_manifest())
        data["narration"][0]["end_limit"] = 11.0
        with self.assertRaisesRegex(ValueError, "narration outside timeline"):
            validate_manifest(data)

    def test_rejects_geometry_other_than_1080p_24fps(self):
        for field, value in (("width", 1280), ("height", 720), ("fps", 30)):
            data = copy.deepcopy(minimal_manifest())
            data[field] = value
            with self.subTest(field=field), self.assertRaisesRegex(
                ValueError, "1920x1080 at 24 fps"
            ):
                validate_manifest(data)

    def test_output_name_cannot_escape_output_directory(self):
        for output_name in ("../source.mp4", "/tmp/source.mp4", "..\\source.mp4"):
            data = copy.deepcopy(minimal_manifest())
            data["output_name"] = output_name
            with self.subTest(output_name=output_name), self.assertRaisesRegex(
                ValueError, "output_name"
            ):
                validate_manifest(data)

    def test_verification_requires_at_least_one_frame_time(self):
        data = copy.deepcopy(minimal_manifest())
        data["verification"]["frame_times"] = []
        with self.assertRaisesRegex(ValueError, "at least one frame time"):
            validate_manifest(data)


if __name__ == "__main__":
    unittest.main()
