import unittest

from explainer_video_v2.pronunciation import rewrite_narration, rewrite_text


class PronunciationTests(unittest.TestCase):
    def test_default_rewrites_are_applied(self):
        self.assertEqual(
            rewrite_text("重排、重传、多运营商"),
            "重新排序、重新传输、多家运营商",
        )

    def test_project_rewrites_cannot_override_locked_reordering_rule(self):
        self.assertEqual(
            rewrite_text("RAG完成重排", {"RAG": "检索增强生成", "重排": "再次排序"}),
            "检索增强生成完成重新排序",
        )

    def test_long_project_rule_cannot_consume_locked_reordering_term(self):
        self.assertEqual(
            rewrite_text("完成交叉重排", {"交叉重排": "再次排序"}),
            "完成交叉重新排序",
        )

    def test_narration_rewrite_is_non_mutating(self):
        original = {
            "pronunciations": {"TOP": "托普"},
            "narration": [{"id": "n1", "text": "TOP执行重排"}],
        }
        rewritten = rewrite_narration(original)
        self.assertEqual(rewritten["narration"][0]["text"], "托普执行重新排序")
        self.assertEqual(original["narration"][0]["text"], "TOP执行重排")


if __name__ == "__main__":
    unittest.main()
