import json
import unittest

from harness.style_audit import audit_text


class StyleAuditTests(unittest.TestCase):
    def test_flags_generic_ai_phrases(self):
        text = (
            "空气仿佛凝固了。她的心像被投入一颗石子，涟漪一圈圈荡开。"
            "他的目光像一簇暗火，烧得她无所遁形。时间仿佛静止。"
            "那一刻她终于明白，某种说不清的情绪正在心里某处悄然改变。"
            "从这一刻起，一切都不一样了。"
        )
        report = audit_text(text)
        self.assertIn("空气凝固/静止", report["generic_patterns"])
        self.assertIn("时间静止", report["generic_patterns"])
        self.assertIn("终于明白", report["generic_patterns"])
        self.assertLess(report["summary"]["risk_score"], 85)
        self.assertTrue(any(w["code"] == "generic_atmosphere" for w in report["warnings"]))

    def test_plain_scene_has_low_or_moderate_risk(self):
        text = (
            "他把门带上。锁舌响了一声，她原本想说的话就忘了。\n\n"
            "他站在两步外，没有过来，只问：“现在还来得及。你确定？”\n\n"
            "她听见自己咽了一下，点头。手指先碰到他的袖口，布料被雨打湿，凉得她一缩。"
            "他低头看了一眼那只手，没有躲，也没有握回去。\n\n"
            "窗外有人按喇叭。她去拉窗帘，手停在半空，最终只拉上了一半。"
        )
        report = audit_text(text)
        self.assertNotEqual(report["summary"]["risk_level"], "high")
        self.assertNotIn("空气凝固/静止", report["generic_patterns"])

    def test_flags_consecutive_fake_beat_paragraphs(self):
        text = (
            "她把档位推高一格。\n\n震动变得清楚了。\n\n"
            "门外传来轮子压过地砖的声音。\n\n男人隔着玻璃敲了两下。"
        )
        report = audit_text(text)
        codes = {warning["code"] for warning in report["warnings"]}
        self.assertIn("fake_beat_paragraphs", codes)

    def test_flags_prop_exposition_and_action_chains(self):
        text = (
            "沈妍顺着他指的方向看过去，上面写着“十二点关门”。"
            "她点头，拿起洗衣篮，指了一下机器，推门，转身，停下。"
        )
        report = audit_text(text)
        codes = {warning["code"] for warning in report["warnings"]}
        self.assertIn("prop_exposition", codes)
        self.assertIn("action_tag_chain", codes)

    def test_report_is_json_serializable(self):
        report = audit_text("她坐下来。杯子里的水还在晃。")
        json.dumps(report, ensure_ascii=False)

    def test_flags_ai_elevation_and_purple_prose(self):
        text = (
            "命运的齿轮开始转动，她美得惊心动魄，带着不可方物的气质。"
            "她不只是漂亮，更是某种破碎感与疏离感的化身。"
            "她看着他，仿佛在宣告一段宿命的开始。从此一切都不一样了。"
        )
        report = audit_text(text)
        self.assertTrue(report["ai_elevation_patterns"])
        self.assertGreaterEqual(report["style_markers"]["purple_prose_count"], 2)
        codes = {warning["code"] for warning in report["warnings"]}
        self.assertIn("ai_elevation", codes)
        self.assertIn("purple_prose", codes)

    def test_dialogue_ratio_detects_quoted_text(self):
        report = audit_text("“你迟到了。”他把伞收起来。“路上堵车。”她没看他。")
        self.assertGreater(report["summary"]["dialogue_ratio"], 0.3)


if __name__ == "__main__":
    unittest.main()
