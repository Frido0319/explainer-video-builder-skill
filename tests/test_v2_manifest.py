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
        "card": {
            "template": "hero",
            "kicker": "测试栏目",
            "title_lines": [{"text": "测试标题"}],
        },
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

    def test_visual_and_narration_ids_must_be_safe_filenames(self):
        for field, unsafe_id in (("visual", "../../escape"), ("narration", "..\\escape")):
            data = copy.deepcopy(minimal_manifest())
            if field == "visual":
                data["visuals"][0]["id"] = unsafe_id
            else:
                data["narration"][0]["id"] = unsafe_id
            with self.subTest(field=field), self.assertRaisesRegex(ValueError, "safe identifier"):
                validate_manifest(data)

    def test_card_templates_require_fields_used_by_renderers(self):
        cases = {
            "hero": (
                {"template": "hero", "kicker": "栏目", "title_lines": [{"text": "标题"}]},
                "kicker",
            ),
            "process": (
                {
                    "template": "process",
                    "title": "流程",
                    "steps": [
                        {"number": "01", "text": "输入"},
                        {"number": "02", "text": "输出"},
                    ],
                    "takeaway": {"lead": "结论", "detail": "流程稳定"},
                },
                "title",
            ),
            "metric_compare": (
                {
                    "template": "metric_compare",
                    "title": "指标",
                    "before": "50%",
                    "after": "90%",
                    "takeaway": {"lead": "结论", "detail": "明显提升"},
                },
                "before",
            ),
            "chapter": (
                {
                    "template": "chapter",
                    "title": "章节",
                    "items": [
                        {"title": "一", "detail": "说明"},
                        {"title": "二", "detail": "说明"},
                    ],
                    "takeaway": {"lead": "结论", "detail": "结构清晰"},
                },
                "items",
            ),
            "metric_grid": (
                {
                    "template": "metric_grid",
                    "title": "数据",
                    "metrics": [
                        {"value": "10", "label": "指标一"},
                        {"value": "20", "label": "指标二"},
                    ],
                    "takeaway": {"lead": "结论", "detail": "结果可靠"},
                },
                "metrics",
            ),
            "ending": (
                {
                    "template": "ending",
                    "brand": "品牌",
                    "headline": "标题",
                    "subline": "副标题",
                    "badge": "完成",
                },
                "badge",
            ),
        }
        for template, (spec, missing_field) in cases.items():
            data = copy.deepcopy(minimal_manifest())
            del spec[missing_field]
            data["visuals"][0]["card"] = spec
            with self.subTest(template=template), self.assertRaisesRegex(
                ValueError, "missing fields"
            ):
                validate_manifest(data)

    def test_card_templates_validate_nested_required_fields(self):
        data = copy.deepcopy(minimal_manifest())
        data["visuals"][0]["card"] = {
            "template": "process",
            "title": "流程",
            "steps": [
                {"number": "01", "text": "输入"},
                {"number": "02"},
            ],
            "takeaway": {"lead": "结论", "detail": "流程稳定"},
        }
        with self.assertRaisesRegex(ValueError, "missing fields"):
            validate_manifest(data)

    def test_hero_stat_style_must_be_supported(self):
        data = copy.deepcopy(minimal_manifest())
        data["visuals"][0]["card"]["stats"] = [
            {"text": "指标", "style": "unknown"}
        ]
        with self.assertRaisesRegex(ValueError, "stat style"):
            validate_manifest(data)

    def test_verification_requires_at_least_one_frame_time(self):
        data = copy.deepcopy(minimal_manifest())
        data["verification"]["frame_times"] = []
        with self.assertRaisesRegex(ValueError, "at least one frame time"):
            validate_manifest(data)


if __name__ == "__main__":
    unittest.main()
