import copy
import tempfile
import unittest
from pathlib import Path

import numpy as np
from PIL import Image

from explainer_video_v2.verify import (
    ass_dialogue_midpoints,
    assert_subtitle_frame_diff,
    assert_verification_report,
)
from tests.test_v2_manifest import minimal_manifest


def valid_report():
    return {
        "duration": 10.024,
        "black_intervals": [],
        "mean_volume_db": -24.0,
        "max_volume_db": -4.0,
        "metadata": {
            "streams": [
                {
                    "codec_name": "h264",
                    "codec_type": "video",
                    "width": 1920,
                    "height": 1080,
                    "r_frame_rate": "24/1",
                },
                {
                    "codec_name": "aac",
                    "codec_type": "audio",
                    "sample_rate": "44100",
                    "channels": 2,
                },
            ]
        },
    }


class VerifyGateTests(unittest.TestCase):
    def test_accepts_delivery_specification(self):
        assert_verification_report(minimal_manifest(), valid_report())

    def test_rejects_wrong_video_codec_and_geometry(self):
        report = copy.deepcopy(valid_report())
        report["metadata"]["streams"][0].update(
            {"codec_name": "hevc", "width": 640, "height": 360}
        )
        with self.assertRaisesRegex(RuntimeError, "video specification"):
            assert_verification_report(minimal_manifest(), report)

    def test_rejects_wrong_audio_codec(self):
        report = copy.deepcopy(valid_report())
        report["metadata"]["streams"][1]["codec_name"] = "mp3"
        with self.assertRaisesRegex(RuntimeError, "audio specification"):
            assert_verification_report(minimal_manifest(), report)

    def test_rejects_black_intervals(self):
        report = valid_report()
        report["black_intervals"] = ["black_start:3 black_end:4"]
        with self.assertRaisesRegex(RuntimeError, "black frames"):
            assert_verification_report(minimal_manifest(), report)

    def test_rejects_clipped_audio(self):
        report = valid_report()
        report["max_volume_db"] = 0.0
        with self.assertRaisesRegex(RuntimeError, "clipping"):
            assert_verification_report(minimal_manifest(), report)

    def test_subtitle_frame_diff_accepts_rendering_inside_safe_band(self):
        reference = np.full((1080, 1920, 3), 255, dtype=np.uint8)
        final = reference.copy()
        final[900:920, 800:850] = 0
        with tempfile.TemporaryDirectory() as directory:
            reference_path = Path(directory) / "reference.png"
            final_path = Path(directory) / "final.png"
            Image.fromarray(reference).save(reference_path)
            Image.fromarray(final).save(final_path)
            result = assert_subtitle_frame_diff(final_path, reference_path, safe_y=875)
        self.assertGreater(result["subtitle_band_pixels"], 300)
        self.assertEqual(result["content_pixels"], 0)

    def test_subtitle_frame_diff_rejects_missing_rendering(self):
        frame = np.full((1080, 1920, 3), 255, dtype=np.uint8)
        with tempfile.TemporaryDirectory() as directory:
            reference_path = Path(directory) / "reference.png"
            final_path = Path(directory) / "final.png"
            Image.fromarray(frame).save(reference_path)
            Image.fromarray(frame).save(final_path)
            with self.assertRaisesRegex(RuntimeError, "subtitle rendering missing"):
                assert_subtitle_frame_diff(final_path, reference_path, safe_y=875)

    def test_subtitle_frame_diff_rejects_changes_above_safe_band(self):
        reference = np.full((1080, 1920, 3), 255, dtype=np.uint8)
        final = reference.copy()
        final[100:170, 100:200] = 0
        final[900:920, 800:850] = 0
        with tempfile.TemporaryDirectory() as directory:
            reference_path = Path(directory) / "reference.png"
            final_path = Path(directory) / "final.png"
            Image.fromarray(reference).save(reference_path)
            Image.fromarray(final).save(final_path)
            with self.assertRaisesRegex(RuntimeError, "outside safe band"):
                assert_subtitle_frame_diff(final_path, reference_path, safe_y=875)

    def test_ass_dialogue_midpoints_sample_first_middle_and_last(self):
        content = "\n".join(
            [
                "Dialogue: 0,0:00:01.00,0:00:02.00,Default,,0,0,0,,第一条",
                "Dialogue: 0,0:00:03.00,0:00:04.00,Default,,0,0,0,,第二条",
                "Dialogue: 0,0:00:05.00,0:00:06.00,Default,,0,0,0,,第三条",
                "Dialogue: 0,0:00:07.00,0:00:08.00,Default,,0,0,0,,第四条",
            ]
        )
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "subtitles.ass"
            path.write_text(content, encoding="utf-8")
            result = ass_dialogue_midpoints(path)
        self.assertEqual(result, [1.5, 5.5, 7.5])


if __name__ == "__main__":
    unittest.main()
