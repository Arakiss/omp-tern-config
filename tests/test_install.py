import importlib.util
import json
from pathlib import Path
import tempfile
import unittest

spec = importlib.util.spec_from_file_location("deck_install", Path(__file__).parents[1] / "install.py")
installer = importlib.util.module_from_spec(spec)
spec.loader.exec_module(installer)


class SettingsPreservation(unittest.TestCase):
    def test_nested_preferences_and_inputs_are_preserved(self):
        original = {"paste": {"confirm": True, "quote_urls_at_prompt": False}, "shell": "/bin/zsh"}
        patch = {"paste": {"confirm": False}}
        result = installer.merge(original, patch)
        self.assertEqual(result, {"paste": {"confirm": False, "quote_urls_at_prompt": False}, "shell": "/bin/zsh"})
        result["paste"]["confirm"] = True
        self.assertEqual(patch, {"paste": {"confirm": False}})
        self.assertEqual(original["paste"], {"confirm": True, "quote_urls_at_prompt": False})

    def test_custom_model_roles_survive_the_preset(self):
        roles = {"default": "custom/model", "review": "custom/reviewer"}
        updated = installer.merge(roles, {"default": "anthropic/claude-opus-5-5"})
        self.assertEqual(updated["review"], "custom/reviewer")
        self.assertEqual(updated["default"], "anthropic/claude-opus-5-5")
        self.assertEqual(roles["default"], "custom/model")

    def test_failed_serialization_does_not_destroy_existing_settings(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text('{"shell": "/bin/zsh"}\n')
            with self.assertRaises(TypeError):
                installer.atomic_json(path, {"unsupported": object()})
            self.assertEqual(json.loads(path.read_text()), {"shell": "/bin/zsh"})
            self.assertEqual(sorted(p.name for p in Path(directory).iterdir()), ["settings.json"])

    def test_existing_private_file_mode_is_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "settings.json"
            path.write_text("{}\n")
            path.chmod(0o600)
            installer.atomic_json(path, {"theme": "Dark"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text()), {"theme": "Dark"})


if __name__ == "__main__":
    unittest.main()
