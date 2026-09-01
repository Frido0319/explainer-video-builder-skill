import ast
import tempfile
import unittest
from pathlib import Path

from PIL import Image

from explainer_video_v2.cards import card_content_bottom, render_card
from explainer_video_v2.themes import get_theme


def card_specs():
    takeaway = {"lead": "结论：", "detail": "结构清晰、证据完整"}
    return [
        {
            "template": "hero",
            "kicker": "技术方案演示",
            "subtitle": "项目成果与真实验证",
            "title_lines": [
                {"text": "回答更准确", "color": "text"},
                {"text": "证据可追溯", "color": "red"},
            ],
            "stats": [
                {"text": "核心素材", "style": "blue"},
                {"text": "结构化知识", "style": "light"},
            ],
            "footer": "技术材料 × 实测证据",
        },
        {
            "template": "process",
            "kicker": "技术流程",
            "title": "系统如何工作",
            "subtitle": "从问题到证据",
            "steps": [
                {"number": "01", "text": "问题理解"},
                {"number": "02", "text": "候选检索"},
                {"number": "03", "text": "重新排序", "accent": "red"},
                {"number": "04", "text": "证据注入"},
            ],
            "badge": "保留最相关信息",
            "takeaway": takeaway,
        },
        {
            "template": "metric_compare",
            "kicker": "真实验证",
            "title": "结果更可靠",
            "subtitle": "对比前后表现",
            "before": "60%",
            "after": "89%",
            "badges": ["样本 A", "样本 B", "引用完整"],
            "takeaway": takeaway,
        },
        {
            "template": "chapter",
            "kicker": "泛化测试",
            "title": "换一种表达仍能理解",
            "subtitle": "同一问题的三种问法",
            "items": [
                {"title": "直问", "detail": "标准提问"},
                {"title": "口语化", "detail": "自然表达"},
                {"title": "设问", "detail": "换角度追问"},
            ],
            "takeaway": takeaway,
        },
        {
            "template": "metric_grid",
            "kicker": "量化结果",
            "title": "结果可以核验",
            "subtitle": "三项核心指标",
            "metrics": [
                {"value": "60% → 89%", "label": "平均命中率", "accent": "red"},
                {"value": "83 → 29", "label": "波动范围"},
                {"value": "9 / 9", "label": "引用可溯源"},
            ],
            "takeaway": takeaway,
        },
        {
            "template": "ending",
            "brand": "技术方案",
            "headline": "让专业结论更可靠",
            "subline": "让每个结论都有依据",
            "badge": "准确 · 稳定 · 可溯源",
        },
    ]


class CardTests(unittest.TestCase):
    def test_research_ppt_theme_is_immutable_and_has_safe_boundary(self):
        theme = get_theme("research_ppt")
        self.assertEqual(theme.blue, (52, 88, 165))
        self.assertEqual(theme.red, (205, 10, 18))
        self.assertEqual(theme.subtitle_safe_y, 875)
        self.assertTrue(theme.font_regular.is_file())
        self.assertTrue(theme.font_bold.is_file())
        with self.assertRaises(Exception):
            theme.blue = (0, 0, 0)

    def test_all_templates_render_1080p_and_keep_subtitle_band_clear(self):
        theme = get_theme("research_ppt")
        with tempfile.TemporaryDirectory() as directory:
            for spec in card_specs():
                output = Path(directory) / f"{spec['template']}.png"
                render_card(spec, theme, output)
                image = Image.open(output).convert("RGB")
                self.assertEqual(image.size, (1920, 1080))
                self.assertGreater(min(image.getpixel((960, 970))), 235)
                bottom_after_zoom = 540 + (card_content_bottom(spec) - 540) * 1.025
                self.assertLessEqual(bottom_after_zoom, theme.subtitle_safe_y)

    def test_renderer_contains_no_hard_coded_chinese_copy(self):
        module_path = Path(__file__).parents[1] / "explainer_video_v2" / "cards.py"
        tree = ast.parse(module_path.read_text(encoding="utf-8"))
        chinese_literals = [
            node.value
            for node in ast.walk(tree)
            if isinstance(node, ast.Constant)
            and isinstance(node.value, str)
            and any("\u4e00" <= char <= "\u9fff" for char in node.value)
        ]
        self.assertEqual(chinese_literals, [])


if __name__ == "__main__":
    unittest.main()
