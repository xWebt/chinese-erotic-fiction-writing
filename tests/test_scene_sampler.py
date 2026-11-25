import unittest

from harness.scene_sampler import select_scenes


class SceneSamplerTests(unittest.TestCase):
    def test_selects_bounded_diverse_scenes(self):
        paragraphs = []
        for index in range(36):
            if index % 3 == 0:
                paragraph = f"“你迟到了。”他说。门口的人抬了抬手，没有进来。第{index}段。"
            elif index % 3 == 1:
                paragraph = f"他推门，转身，拿起杯子，又放下。窗外有人走过。第{index}段。"
            else:
                paragraph = f"雨落在窗台上，屋里的灯没有开。她站着，看了很久。第{index}段。"
            paragraphs.append(paragraph * 5)
        text = "\n\n".join(paragraphs)
        scenes = select_scenes(text, count=6, target_chars=600)
        self.assertEqual(len(scenes), 6)
        self.assertTrue(all(len(scene.text) >= 200 for scene in scenes))
        self.assertEqual(len({scene.position for scene in scenes}), 6)


if __name__ == "__main__":
    unittest.main()
