import contextlib
from concurrent.futures import ThreadPoolExecutor
import importlib.util
import io
import json
import os
from pathlib import Path
import plistlib
import subprocess
import tempfile
import threading
import time
import unittest
from unittest.mock import patch

spec = importlib.util.spec_from_file_location("tern_bg", Path(__file__).parents[1] / "tern_bg.py")
bg = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bg)


class Durations(unittest.TestCase):
    def test_units_whitespace_and_exact_fractional_units(self):
        for value, expected in {
            "2s": 2, "15m": 900, "1h": 3600, " 2 M ": 120,
            "0.5m": 30, ".5m": 30, "1.5h": 5400,
            "2147483647s": 2147483647,
        }.items():
            with self.subTest(value=value):
                self.assertEqual(bg.parse_duration(value), expected)

    def test_invalid_and_subsecond_intervals_are_rejected(self):
        for value in (
            "", "2", "0s", "-2m", "1d", "1ms", "0.5s", "1e2m",
            "nanm", "infh", "2s extra", "2147483648s",
            "0.999999999999999999999999999999s",
        ):
            with self.subTest(value=value), self.assertRaises(ValueError):
                bg.parse_duration(value)


class WallpaperFixture(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)
        self.source = self.directory / "source"
        (self.source / "wallpapers").mkdir(parents=True)
        (self.source / "tern/plugin").mkdir(parents=True)
        for name in bg.WALLPAPERS:
            (self.source / "wallpapers" / f"{name}.webp").write_bytes(f"image for {name}".encode())
        (self.source / "tern/plugin/plugin.toml").write_text(f'id = "{bg.PLUGIN_ID}"\n')
        (self.source / "tern/plugin/window.luau").write_text('tern.css("wallpaper", "background")\n')
        self.runtime = bg._Runtime(self.directory / "config/plugins", "/fixture/tern")
        self.runtime.plugin_dir.mkdir(parents=True)
        self.patches = (
            patch.object(bg, "ROOT", self.source),
            patch.object(bg, "_runtime", return_value=self.runtime),
            # The tests exercise filesystem/state behavior, never the real Tern.
            patch.object(bg, "_reload_plugin"),
        )
        for replacement in self.patches:
            replacement.start()
            self.addCleanup(replacement.stop)

    def seed(self, name):
        self.runtime.image_path.write_bytes((self.source / "wallpapers" / f"{name}.webp").read_bytes())

    def state(self, value):
        self.runtime.state_dir.mkdir(parents=True, exist_ok=True)
        self.runtime.state_path.write_text(json.dumps(value))

    def command_output(self, *args):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            bg.main(list(args))
        return output.getvalue()


class WallpaperTransitions(WallpaperFixture):
    def test_existing_installer_image_seeds_current_and_neighbors(self):
        self.seed("cyberpunk")
        self.assertFalse(self.runtime.state_path.exists())
        self.assertEqual(self.command_output("current"), "cyberpunk\n")
        self.assertIn("* cyberpunk\n", self.command_output("list"))
        self.assertEqual(bg.next_wallpaper(), "ghost-shell")
        self.assertEqual(bg.previous_wallpaper(), "cyberpunk")
        self.assertEqual(json.loads(self.runtime.state_path.read_text())["current"], "cyberpunk")

    def test_order_and_both_wraparound_edges(self):
        self.seed("retro-future")
        self.assertEqual(bg.next_wallpaper(), "replicant")
        self.assertEqual(bg.previous_wallpaper(), "retro-future")
        self.assertEqual(self.command_output("list").splitlines(), [
            "  replicant", "  dunes", "  grid", "  tron-ares",
            "  altered-carbon", "  cyberpunk", "  ghost-shell", "  deus-ex", "* retro-future",
        ])

    def test_installed_image_wins_over_stale_and_unknown_saved_names(self):
        for saved in ("dunes", "removed-wallpaper", ["invalid-name-type"]):
            with self.subTest(saved=saved):
                self.seed("ghost-shell")
                self.state({"version": 1, "current": saved})
                self.assertEqual(bg.current_wallpaper(), "ghost-shell")
                self.assertEqual(bg.next_wallpaper(), "deus-ex")

    def test_unknown_image_is_not_silently_replaced_by_next(self):
        self.runtime.image_path.write_bytes(b"a custom wallpaper")
        self.state({"version": 1, "current": "cyberpunk"})
        before = self.runtime.state_path.read_bytes()
        self.assertEqual(self.command_output("current"), "unknown\n")
        with self.assertRaisesRegex(RuntimeError, "not in the catalogue"):
            bg.next_wallpaper()
        self.assertEqual(self.runtime.image_path.read_bytes(), b"a custom wallpaper")
        self.assertEqual(self.runtime.state_path.read_bytes(), before)
        self.assertEqual(bg.apply_wallpaper("ghost-shell"), "ghost-shell")
        self.assertEqual((self.runtime.state_dir / "original-wallpaper.webp").read_bytes(), b"a custom wallpaper")

    def test_missing_image_uses_first_or_last_edge_not_stale_state(self):
        self.state({"version": 1, "current": "cyberpunk"})
        self.assertEqual(self.command_output("current"), "none\n")
        self.assertEqual(bg.next_wallpaper(), "replicant")
        self.runtime.image_path.unlink()
        self.assertEqual(bg.previous_wallpaper(), "retro-future")

    def test_unknown_name_does_not_change_existing_image_or_state(self):
        self.seed("ghost-shell")
        bg.apply_wallpaper("ghost-shell")
        before_image = self.runtime.image_path.read_bytes()
        before_state = self.runtime.state_path.read_bytes()
        with self.assertRaisesRegex(ValueError, "Unknown wallpaper"):
            bg.apply_wallpaper("../outside")
        self.assertEqual(self.runtime.image_path.read_bytes(), before_image)
        self.assertEqual(self.runtime.state_path.read_bytes(), before_state)

    def test_only_owned_plugin_changes_and_backup_is_bounded(self):
        self.seed("ghost-shell")
        original = self.runtime.image_path.read_bytes()
        protected = {
            self.runtime.plugins_dir.parent / "settings.json": b'{"shell":"/bin/zsh"}\n',
            self.directory / "omp/config.yaml": b"model: private/custom\n",
            self.directory / "omp/mcp.json": b'{"mcpServers":{"existing":{}}}\n',
            self.directory / "omp/skills/existing/SKILL.md": b"Keep this user's skill.\n",
            self.runtime.plugins_dir / "unrelated/plugin.toml": b'id = "unrelated"\n',
            self.runtime.plugin_dir / "custom-note.txt": b"Keep extra plugin files.\n",
        }
        for path, content in protected.items():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(content)
        for name in ("deus-ex", "replicant", "cyberpunk"):
            bg.apply_wallpaper(name)
        for path, content in protected.items():
            self.assertEqual(path.read_bytes(), content)
        self.assertEqual((self.runtime.state_dir / "original-wallpaper.webp").read_bytes(), original)
        self.assertEqual(sorted(path.name for path in self.runtime.state_dir.iterdir()), [
            "original-wallpaper.webp", "state.json", "wallpaper.lock",
        ])

    def test_overlapping_steps_each_advance_once(self):
        self.seed("cyberpunk")
        barrier = threading.Barrier(5)

        def advance():
            barrier.wait(timeout=10)
            return bg.next_wallpaper()

        with patch.object(bg, "_reload_plugin", side_effect=lambda runtime: time.sleep(0.01)):
            with ThreadPoolExecutor(max_workers=5) as executor:
                names = list(executor.map(lambda _: advance(), range(5)))
        self.assertCountEqual(names, ["ghost-shell", "deus-ex", "retro-future", "replicant", "dunes"])
        self.assertEqual(bg.current_wallpaper(), "dunes")
        self.assertEqual(json.loads(self.runtime.state_path.read_text())["current"], "dunes")

    def test_source_and_cli_do_not_depend_on_working_directory(self):
        self.seed("ghost-shell")
        previous = Path.cwd()
        try:
            os.chdir(self.directory)
            self.assertEqual(self.command_output("current"), "ghost-shell\n")
            self.assertEqual(self.command_output("next"), "deus-ex\n")
        finally:
            os.chdir(previous)


class AtomicFiles(unittest.TestCase):
    def test_failed_serialization_preserves_existing_state_and_leaves_no_temporary(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_bytes(b'{"current":"ghost-shell"}\n')
            with self.assertRaises(TypeError):
                bg._atomic_json(path, {"unsupported": object()})
            self.assertEqual(path.read_bytes(), b'{"current":"ghost-shell"}\n')
            self.assertEqual([entry.name for entry in path.parent.iterdir()], ["state.json"])

    def test_private_state_mode_survives_atomic_replacement(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "state.json"
            path.write_text("{}\n")
            path.chmod(0o600)
            bg._atomic_json(path, {"current": "ghost-shell"})
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertEqual(json.loads(path.read_text()), {"current": "ghost-shell"})


class CommandInstallation(unittest.TestCase):
    def test_owned_absolute_symlink_is_idempotent(self):
        with tempfile.TemporaryDirectory() as directory:
            command = bg.install_cli(Path(directory) / "bin")
            self.assertTrue(command.is_symlink())
            self.assertTrue(Path(os.readlink(command)).is_absolute())
            self.assertEqual(command.resolve(), bg.SOURCE)
            self.assertEqual(bg.install_cli(command.parent), command)

    def test_unrelated_file_or_link_is_never_overwritten(self):
        with tempfile.TemporaryDirectory() as directory:
            command = Path(directory) / "tern-bg"
            command.write_bytes(b"user's command")
            with self.assertRaisesRegex(RuntimeError, "unrelated"):
                bg.install_cli(command.parent)
            self.assertEqual(command.read_bytes(), b"user's command")
            command.unlink()
            command.symlink_to(Path(directory) / "missing-unrelated-command")
            before = os.readlink(command)
            with self.assertRaisesRegex(RuntimeError, "unrelated"):
                bg.install_cli(command.parent)
            self.assertEqual(os.readlink(command), before)


class _LaunchdFixture:
    """A local loaded-job model; no test invokes launchctl or waits for a timer."""
    def __init__(self):
        self.loaded = None
        self.fail_next_bootstrap = False

    def __call__(self, *args):
        if args[0] == "print":
            return subprocess.CompletedProcess(args, 0 if self.loaded else 1, "", "")
        if args[0] == "bootout":
            self.loaded = None
            return subprocess.CompletedProcess(args, 0, "", "")
        if args[0] == "bootstrap":
            if self.fail_next_bootstrap:
                self.fail_next_bootstrap = False
                return subprocess.CompletedProcess(args, 1, "", "fixture load failure")
            self.loaded = plistlib.loads(Path(args[2]).read_bytes())
            return subprocess.CompletedProcess(args, 0, "", "")
        raise AssertionError(f"Unexpected launchctl operation: {args}")


class RotationLifecycle(WallpaperFixture):
    def setUp(self):
        super().setUp()
        self.seed("ghost-shell")
        self.schedule_path = self.directory / "LaunchAgents" / f"{bg.AGENT_LABEL}.plist"
        self.launchd = _LaunchdFixture()
        for replacement in (
            patch.object(bg, "_require_macos"),
            patch.object(bg, "_schedule_path", return_value=self.schedule_path),
            patch.object(bg, "_schedule_lock_path", return_value=self.directory / "schedule/rotation.lock"),
            patch.object(bg, "_launchctl", side_effect=self.launchd),
        ):
            replacement.start()
            self.addCleanup(replacement.stop)

    def test_schedule_ticks_share_manual_state_and_stop_invalidates_queued_ticks(self):
        self.assertEqual(bg.rotate_wallpapers("2s"), 2)
        status = bg.rotation_status()
        self.assertTrue(status["configured"])
        self.assertTrue(status["loaded"])
        self.assertEqual(status["every"], 2)
        self.assertEqual(status["config_dir"], str(self.runtime.plugins_dir.parent))
        self.assertEqual(bg.current_wallpaper(), "ghost-shell")  # no RunAtLoad change
        generation = self.launchd.loaded["ProgramArguments"][4]
        self.assertEqual(bg._tick(generation), "deus-ex")
        self.assertEqual(bg.previous_wallpaper(), "ghost-shell")
        self.assertEqual(bg._tick(generation), "deus-ex")
        self.assertTrue(bg.stop_rotation())
        self.assertFalse(self.schedule_path.exists())
        self.assertFalse(bg.rotation_status()["configured"])
        self.assertFalse(bg.rotation_status()["loaded"])
        self.assertIsNone(bg._tick(generation))
        self.assertEqual(bg.current_wallpaper(), "deus-ex")

    def test_replacement_generation_prevents_old_schedule_from_advancing(self):
        bg.rotate_wallpapers("2s")
        old_generation = self.launchd.loaded["ProgramArguments"][4]
        bg.rotate_wallpapers("15m")
        new_generation = self.launchd.loaded["ProgramArguments"][4]
        self.assertNotEqual(old_generation, new_generation)
        self.assertIsNone(bg._tick(old_generation))
        self.assertEqual(bg.current_wallpaper(), "ghost-shell")
        self.assertEqual(bg._tick(new_generation), "deus-ex")

    def test_configured_and_loaded_are_distinct(self):
        bg.rotate_wallpapers("15m")
        self.launchd.loaded = None
        status = bg.rotation_status()
        self.assertTrue(status["configured"])
        self.assertFalse(status["loaded"])
        self.assertTrue(bg.stop_rotation())
        self.assertFalse(self.schedule_path.exists())

    def test_failed_reconfiguration_restores_previous_schedule(self):
        bg.rotate_wallpapers("15m")
        original = self.schedule_path.read_bytes()
        self.launchd.fail_next_bootstrap = True
        with self.assertRaisesRegex(RuntimeError, "previous schedule restored"):
            bg.rotate_wallpapers("2s")
        self.assertEqual(self.schedule_path.read_bytes(), original)
        self.assertTrue(bg.rotation_status()["loaded"])
        self.assertEqual(bg.rotation_status()["every"], 900)

    def test_bad_interval_does_not_change_image_state_or_existing_schedule(self):
        bg.apply_wallpaper("ghost-shell")
        bg.rotate_wallpapers("15m")
        before = tuple(path.read_bytes() for path in (
            self.runtime.image_path, self.runtime.state_path, self.schedule_path,
        ))
        with self.assertRaises(ValueError):
            bg.rotate_wallpapers("0.5s")
        after = tuple(path.read_bytes() for path in (
            self.runtime.image_path, self.runtime.state_path, self.schedule_path,
        ))
        self.assertEqual(after, before)
        self.assertTrue(bg.rotation_status()["loaded"])


if __name__ == "__main__":
    unittest.main()
