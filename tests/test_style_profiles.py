from pathlib import Path
import unittest

try:
    import yaml
except ImportError:
    yaml = None


class StyleProfileTests(unittest.TestCase):
    def test_required_profiles_load(self):
        if yaml is None:
            self.skipTest("PyYAML is not installed in this runtime")
        root = Path(__file__).resolve().parents[1] / "styles"
        profiles = {
            path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in root.glob("*.yaml")
            if not path.name.startswith("_") and path.name != "index.yaml"
        }
        self.assertGreaterEqual(len(profiles), 5)
        for name, profile in profiles.items():
            with self.subTest(profile=name):
                for key in ("id", "role", "source", "voice", "sentence", "dialogue", "scene"):
                    self.assertIn(key, profile)
                self.assertNotIn("sample_text", profile)
                self.assertGreater(profile["source"]["scenes_read"], 0)

    def test_required_playbooks_load(self):
        if yaml is None:
            self.skipTest("PyYAML is not installed in this runtime")
        root = Path(__file__).resolve().parents[1] / "playbooks"
        profiles = {
            path.stem: yaml.safe_load(path.read_text(encoding="utf-8"))
            for path in root.glob("*.yaml")
            if path.name != "index.yaml"
        }
        self.assertGreaterEqual(len(profiles), 12)
        for name, profile in profiles.items():
            with self.subTest(playbook=name):
                for key in ("id", "label", "progression", "turn", "avoid"):
                    self.assertIn(key, profile)

    def test_plain_modern_is_primary(self):
        if yaml is None:
            self.skipTest("PyYAML is not installed in this runtime")
        path = Path(__file__).resolve().parents[1] / "styles" / "plain-modern.yaml"
        profile = yaml.safe_load(path.read_text(encoding="utf-8"))
        self.assertEqual(profile["role"], "primary")
        self.assertEqual(profile["thresholds"]["max_short_narrative_run"], 2)


if __name__ == "__main__":
    unittest.main()
