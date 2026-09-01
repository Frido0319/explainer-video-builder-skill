import json
import unittest
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


class VersionSelectionContractTests(unittest.TestCase):
    def test_skill_and_readme_publish_the_same_visible_menu(self):
        markers = (
            "请选择视频制作方向：",
            "V1｜保真增强",
            "V2 create｜重新制作",
            "V2 enhance｜精剪重构",
            "展示完整三项菜单并等待用户选择",
            "1 / 2 / 3",
        )
        for name in ("SKILL.md", "README.md"):
            content = (ROOT / name).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, content, f"{name} missing {marker}")
            self.assertNotIn("未明确选择版本时，默认使用 V1", content)

    def test_skill_handles_partial_and_explicit_version_selection(self):
        skill = (ROOT / "SKILL.md").read_text(encoding="utf-8")
        for marker in (
            "只说 V2",
            "列出两个 V2 子方向并等待选择",
            "已明确选择 V1、V2 create 或 V2 enhance",
            "不重复展示菜单",
        ):
            self.assertIn(marker, skill)

    def test_v2_submenu_preserves_global_numbers(self):
        markers = (
            "编号是版本选择协议，不是局部菜单的装饰序号",
            "V2 子菜单固定模板（必须原样使用序号）",
            "2. V2 create｜重新制作",
            "3. V2 enhance｜精剪重构",
            "请回复 2 / 3",
            "不得在 V2 子菜单中重新编号为 1 / 2",
        )
        for name in ("SKILL.md", "README.md"):
            content = (ROOT / name).read_text(encoding="utf-8")
            for marker in markers:
                self.assertIn(marker, content, f"{name} missing {marker}")

        data = json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))
        v2_eval = next(item for item in data["evals"] if item["name"] == "menu-v2-submode")
        self.assertIn("2=V2 create", v2_eval["expected_output"])
        self.assertIn("3=V2 enhance", v2_eval["expected_output"])
        self.assertIn("不得重新编号为 1/2", v2_eval["expected_output"])

    def test_both_implementations_remain_present(self):
        for relative in (
            "scripts/make_tts.py",
            "scripts/make_subs.py",
            "scripts/mix_audio.py",
            "scripts/verify_video.py",
            "explainer_video_v2/cli.py",
            "explainer_video_v2/manifest.py",
        ):
            self.assertTrue((ROOT / relative).is_file(), relative)

    def test_evals_cover_interactive_version_selection(self):
        data = json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))
        names = {item["name"] for item in data["evals"]}
        required = {
            "menu-no-version",
            "menu-v2-submode",
            "numeric-version-selection",
            "explicit-version-no-repeat",
        }
        self.assertTrue(required.issubset(names))
        self.assertNotIn("default-v1-fallback", names)

    def test_unversioned_complete_video_eval_waits_for_selection(self):
        data = json.loads((ROOT / "evals/evals.json").read_text(encoding="utf-8"))
        item = next(entry for entry in data["evals"] if entry["name"] == "complete-demo-video")
        self.assertIn("展示完整三项菜单", item["expected_output"])
        self.assertIn("等待用户选择", item["expected_output"])
        self.assertNotIn("生成 1080p MP4", item["expected_output"])


if __name__ == "__main__":
    unittest.main()
