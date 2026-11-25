import tempfile
import unittest
from pathlib import Path

from harness.corpus_style import profile_paths, profile_text


class CorpusStyleTests(unittest.TestCase):
    def test_profile_counts_dialogue_and_shapes(self):
        text = (
            "“十二点以后这里不能过夜。”\n\n"
            "“烘完就走。”她没抬头。\n\n"
            "机器还在转。她把篮子挪到腿边，挡住风衣下摆。外面有人推车经过。"
        )
        report = profile_text(text)
        self.assertGreater(report["dialogue_ratio"], 0.15)
        self.assertGreater(report["median_sentence"], 0)
        self.assertGreater(report["median_paragraph"], 0)
        self.assertGreaterEqual(report["one_sentence_paragraph_ratio"], 0.3)

    def test_profile_paths_is_compact_and_skips_short_files(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / "good.txt").write_text(
                "这是第一句话。这里还有第二句话。\n\n“你来了。”他说。\n\n"
                "她没回答，把门关上。门外有人走过，" * 100,
                encoding="utf-8",
            )
            (root / "short.txt").write_text("太短。", encoding="utf-8")
            report = profile_paths([tmp], limit=10)
            self.assertEqual(report["sample_count"], 1)
            self.assertIn("median", report["dialogue_ratio"])

    def test_empty_text(self):
        self.assertEqual(profile_text(""), {"cjk_chars": 0})


if __name__ == "__main__":
    unittest.main()
