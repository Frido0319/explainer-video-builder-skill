import json
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from explainer_video_v2.audio import build_ass
from explainer_video_v2.builder import final_ffmpeg_command, prepare_project
from explainer_video_v2.media import (
    card_video_filter,
    clip_setpts_factor,
    clip_video_filter,
    image_video_filter,
)

from tests.test_v2_manifest import clip_segment, minimal_manifest


class PipelineTests(unittest.TestCase):
    def test_card_filter_uses_four_x_lanczos_prescale(self):
        value = card_video_filter(duration=5.0, fps=24, width=1920, height=1080)
        self.assertIn("scale=7680:4320:flags=lanczos,zoompan", value)
        self.assertIn("s=1920x1080:fps=24", value)

    def test_clip_setpts_factor_compresses_source_to_output(self):
        visual = {"start": 10.0, "end": 14.0, "source_duration": 8.0}
        self.assertEqual(clip_setpts_factor(visual), 0.5)

    def test_clip_filter_contains_without_stretching(self):
        value = clip_video_filter(0.5, fps=24, width=1920, height=1080)
        self.assertIn("force_original_aspect_ratio=decrease", value)
        self.assertIn("pad=1920:1080", value)

    def test_image_filter_contains_without_cropping_and_reserves_subtitle_band(self):
        value = image_video_filter(1920, 1080, subtitle_safe_y=875)
        self.assertIn("force_original_aspect_ratio=decrease", value)
        self.assertIn("scale=1920:875", value)
        self.assertIn("pad=1920:1080", value)
        self.assertIn(":0:color=white", value)

    def test_ass_uses_rewritten_narration_and_safe_play_resolution(self):
        data = {
            "narration": [
                {"id": "n1", "start": 0.0, "end_limit": 3.0, "text": "完成重新排序。"}
            ]
        }
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "subs.ass"
            build_ass(data, {"n1": 2.0}, output, 1920, 1080)
            content = output.read_text(encoding="utf-8")
        self.assertIn("PlayResX: 1920", content)
        self.assertIn("PlayResY: 1080", content)
        self.assertIn("完成重新排序", content)
        self.assertNotIn("完成重新排序。", content)

    def test_prepare_project_rewrites_narration_and_resolves_relative_paths(self):
        data = minimal_manifest()
        data["narration"][0]["text"] = "执行重排"
        data["output_dir"] = "output"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            path.write_text(__import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")
            prepared = prepare_project(path)
        self.assertEqual(prepared["narration"][0]["text"], "执行重新排序")
        self.assertTrue(Path(prepared["output_dir"]).is_absolute())

    def test_prepare_project_expands_environment_paths(self):
        data = minimal_manifest()
        data["output_dir"] = "${V2_TEST_ROOT}/output"
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "project.json"
            path.write_text(__import__("json").dumps(data, ensure_ascii=False), encoding="utf-8")
            with patch.dict("os.environ", {"V2_TEST_ROOT": directory}):
                prepared = prepare_project(path)
        self.assertEqual(Path(prepared["output_dir"]), Path(directory) / "output")

    def test_prepare_project_rejects_output_that_overwrites_source(self):
        data = minimal_manifest(mode="enhance", visuals=[clip_segment()])
        with tempfile.TemporaryDirectory() as directory:
            source = Path(directory) / "source.mp4"
            source.touch()
            data["visuals"][0]["source"] = str(source)
            data["output_dir"] = directory
            data["output_name"] = source.name
            path = Path(directory) / "project.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overwrite source"):
                prepare_project(path)

    def test_prepare_project_rejects_source_inside_output_directory(self):
        data = minimal_manifest(mode="enhance", visuals=[clip_segment()])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            source = output_dir / "work" / "video_only.mp4"
            source.parent.mkdir(parents=True)
            source.touch()
            data["visuals"][0]["source"] = str(source)
            data["output_dir"] = str(output_dir)
            path = root / "project.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "outside output_dir"):
                prepare_project(path)

    def test_prepare_project_rejects_symlinks_inside_output_directory(self):
        data = minimal_manifest()
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            output_dir = root / "output"
            work_dir = output_dir / "work"
            work_dir.mkdir(parents=True)
            external = root / "external.mp4"
            external.touch()
            (work_dir / "video_only.mp4").symlink_to(external)
            data["output_dir"] = str(output_dir)
            path = root / "project.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "symbolic link"):
                prepare_project(path)

    def test_prepare_project_rejects_symlink_output_aliasing_source(self):
        data = minimal_manifest(mode="enhance", visuals=[clip_segment()])
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.touch()
            output_dir = root / "output"
            output_dir.mkdir()
            (output_dir / "final.mp4").symlink_to(source)
            data["visuals"][0]["source"] = str(source)
            data["output_dir"] = str(output_dir)
            data["output_name"] = "final.mp4"
            path = root / "project.json"
            path.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "overwrite source"):
                prepare_project(path)

    def test_final_command_uses_delivery_codecs_and_faststart(self):
        command = final_ffmpeg_command(
            Path("video.mp4"),
            Path("audio.wav"),
            Path("subs.ass"),
            Path("final.mp4"),
            duration=12.0,
        )
        joined = " ".join(str(item) for item in command)
        self.assertIn("-c:v libx264", joined)
        self.assertIn("-c:a aac", joined)
        self.assertIn("-movflags +faststart", joined)
        self.assertIn("-t 12.000", joined)


if __name__ == "__main__":
    unittest.main()
