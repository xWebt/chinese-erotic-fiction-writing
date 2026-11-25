import unittest

from harness.text_encoding import decode_bytes


class TextEncodingTests(unittest.TestCase):
    def test_decodes_gb18030_chinese(self):
        source = "第一章 夜色很深。他推开门，问她：“你怎么还没走？”\n" * 30
        raw = source.encode("gb18030")
        text, encoding, _score = decode_bytes(raw)
        self.assertEqual(encoding, "gb18030")
        self.assertIn("夜色很深", text)

    def test_prefers_utf8(self):
        source = "她坐在窗边，杯子里的水还在晃。" * 30
        raw = source.encode("utf-8")
        text, encoding, _score = decode_bytes(raw)
        self.assertEqual(encoding, "utf-8-sig")
        self.assertIn("杯子里的水", text)

    def test_replacement_fallback(self):
        text, encoding, _score = decode_bytes(b"\xff\xff\xff")
        self.assertIsInstance(encoding, str)
        self.assertIsInstance(text, str)


if __name__ == "__main__":
    unittest.main()
