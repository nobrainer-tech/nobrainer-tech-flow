import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[1] / "skills/nobrainer-ultra/scripts/decision_config.py"
spec = importlib.util.spec_from_file_location("decision_config", SCRIPT)
config = importlib.util.module_from_spec(spec)
spec.loader.exec_module(config)


class DecisionConfigTests(unittest.TestCase):
    def test_setup_is_idempotent_and_never_reopens_saved_choice(self):
        import subprocess
        import sys
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "flow.json"
            command = [sys.executable, str(SCRIPT), "--config", str(path), "setup", "--non-interactive"]
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertTrue(config.read(path)["configured"])
            config.configure(path, "jev", "shadow", "jev-latest", 10, 2)
            before = path.read_bytes()
            self.assertEqual(subprocess.run(command, capture_output=True).returncode, 0)
            self.assertEqual(path.read_bytes(), before)

    def test_missing_config_does_not_write_or_enable_provider(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "flow.json"
            self.assertFalse(config.read(path)["configured"])
            self.assertEqual(config.read(path)["config"]["mode"], "off")
            self.assertFalse(path.exists())

    def test_decline_is_remembered_and_explicit_change_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "flow.json"
            config.configure(path, "core", "off", None, 10, 0)
            self.assertTrue(config.read(path)["configured"])
            config.configure(path, "laya", "shadow", config.MODELS["laya"], 10, 3)
            self.assertEqual(config.read(path)["config"]["provider"], "laya")

    def test_invalid_input_preserves_previous_bytes(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "flow.json"
            config.configure(path, "core", "off", None, 10, 0)
            before = path.read_bytes()
            with self.assertRaises(ValueError):
                config.configure(path, "jev", "shadow", "jev-latest", 10, 0)
            self.assertEqual(path.read_bytes(), before)

    def test_corrupt_config_falls_back_without_reprompt_or_overwrite(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "flow.json"
            path.write_text('{"api_key":"synthetic-secret"}')
            result = config.read(path)
            self.assertTrue(result["configured"])
            self.assertEqual(result["config"], config.DEFAULT)
            self.assertNotIn("synthetic-secret", str(result))


if __name__ == "__main__":
    unittest.main()
