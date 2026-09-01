import copy
import tempfile
import unittest
from pathlib import Path

from explainer_video_v2.provenance import (
    assert_build_fingerprint,
    manifest_fingerprint,
    write_build_fingerprint,
)

from tests.test_v2_manifest import clip_segment, minimal_manifest


class ProvenanceTests(unittest.TestCase):
    def test_manifest_fingerprint_is_stable_and_ignores_runtime_metadata(self):
        data = minimal_manifest()
        same = copy.deepcopy(data)
        same["_manifest_path"] = "/another/machine/project.json"
        self.assertEqual(manifest_fingerprint(data), manifest_fingerprint(same))

    def test_manifest_fingerprint_changes_with_build_inputs(self):
        data = minimal_manifest()
        changed = copy.deepcopy(data)
        changed["narration"][0]["text"] = "不同的旁白"
        self.assertNotEqual(manifest_fingerprint(data), manifest_fingerprint(changed))

    def test_assert_build_fingerprint_rejects_missing_and_stale_builds(self):
        data = minimal_manifest()
        with tempfile.TemporaryDirectory() as directory:
            work_dir = Path(directory)
            output = work_dir / "final.mp4"
            output.write_bytes(b"video")
            with self.assertRaisesRegex(RuntimeError, "fingerprint missing"):
                assert_build_fingerprint(data, work_dir, output)
            write_build_fingerprint(data, work_dir, output)
            changed = copy.deepcopy(data)
            changed["duration"] = 11.0
            with self.assertRaisesRegex(RuntimeError, "does not match"):
                assert_build_fingerprint(changed, work_dir, output)

    def test_written_fingerprint_accepts_current_manifest(self):
        data = minimal_manifest()
        with tempfile.TemporaryDirectory() as directory:
            work_dir = Path(directory)
            output = work_dir / "final.mp4"
            output.write_bytes(b"video")
            write_build_fingerprint(data, work_dir, output)
            assert_build_fingerprint(data, work_dir, output)

    def test_fingerprint_rejects_changed_source_or_output_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            source = root / "source.mp4"
            source.write_bytes(b"source-v1")
            output = root / "final.mp4"
            output.write_bytes(b"output-v1")
            data = minimal_manifest(mode="enhance", visuals=[clip_segment()])
            data["visuals"][0]["source"] = str(source)
            work_dir = root / "work"
            write_build_fingerprint(data, work_dir, output)

            source.write_bytes(b"source-v2")
            with self.assertRaisesRegex(RuntimeError, "source fingerprint"):
                assert_build_fingerprint(data, work_dir, output)

            source.write_bytes(b"source-v1")
            output.write_bytes(b"output-v2")
            with self.assertRaisesRegex(RuntimeError, "output fingerprint"):
                assert_build_fingerprint(data, work_dir, output)


if __name__ == "__main__":
    unittest.main()
