#!/usr/bin/env python3
"""Change Tern's local wallpaper, with optional macOS LaunchAgent rotation."""

import argparse
from contextlib import contextmanager
from decimal import Decimal, InvalidOperation, localcontext
import fcntl
import hashlib
import json
import os
from pathlib import Path
import plistlib
import re
import shutil
import subprocess
import sys
import tempfile
import uuid
from xml.parsers.expat import ExpatError

SOURCE = Path(__file__).resolve()
ROOT = SOURCE.parent
WALLPAPERS = (
    "replicant", "dunes", "grid", "tron-ares", "altered-carbon",
    "cyberpunk", "ghost-shell", "deus-ex", "retro-future",
)
PLUGIN_ID = "omp-tern-config-wallpaper"
AGENT_LABEL = "io.github.arakiss.omp-tern-config.wallpaper"
MAX_INTERVAL = 2_147_483_647


class _Runtime:
    def __init__(self, plugins_dir, tern):
        self.plugins_dir = Path(plugins_dir)
        self.tern = Path(tern)
        self.plugin_dir = self.plugins_dir / PLUGIN_ID
        self.state_dir = self.plugins_dir.parent / PLUGIN_ID
        self.state_path = self.state_dir / "state.json"
        self.lock_path = self.state_dir / "wallpaper.lock"
        self.image_path = self.plugin_dir / "wallpaper.webp"


def _command(*args):
    result = subprocess.run(args, capture_output=True, text=True, timeout=30)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise RuntimeError(f"{' '.join(map(str, args))}: {detail}")
    return result.stdout.strip()


def _runtime():
    binary = shutil.which("tern")
    if not binary:
        raise RuntimeError("Install Tern and put tern on PATH first.")
    tern = Path(binary).resolve()
    directory = _command(str(tern), "plugin", "dir")
    if not directory:
        raise RuntimeError("tern plugin dir returned no directory.")
    return _Runtime(Path(directory).expanduser().resolve(), tern)


def _check_plugin(runtime):
    if runtime.plugin_dir.is_symlink():
        raise RuntimeError(f"Refusing to replace a linked plugin: {runtime.plugin_dir}")
    for name in ("plugin.toml", "window.luau", "wallpaper.webp"):
        path = runtime.plugin_dir / name
        if path.is_symlink():
            raise RuntimeError(f"Refusing to replace a linked plugin file: {path}")


@contextmanager
def _file_lock(path):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.parent.is_symlink():
        raise RuntimeError(f"Refusing to use a linked state directory: {path.parent}")
    descriptor = os.open(path, os.O_CREAT | os.O_RDWR | os.O_NOFOLLOW, 0o600)
    try:
        fcntl.flock(descriptor, fcntl.LOCK_EX)
        yield
    finally:
        os.close(descriptor)


def _atomic_write(path, content, mode=0o600):
    path.parent.mkdir(parents=True, mode=0o700, exist_ok=True)
    if path.exists():
        mode = path.stat().st_mode & 0o777
    with tempfile.NamedTemporaryFile(dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            handle.write(content)
            handle.flush()
            os.fsync(handle.fileno())
            temporary.chmod(mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def _atomic_json(path, value):
    content = (json.dumps(value, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    _atomic_write(path, content)


def _atomic_copy(source, destination):
    destination.parent.mkdir(parents=True, exist_ok=True)
    mode = destination.stat().st_mode & 0o777 if destination.exists() else 0o644
    with tempfile.NamedTemporaryFile(dir=destination.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            with source.open("rb") as original:
                shutil.copyfileobj(original, handle)
            handle.flush()
            os.fsync(handle.fileno())
            temporary.chmod(mode)
            os.replace(temporary, destination)
        finally:
            temporary.unlink(missing_ok=True)


def _read_state(runtime):
    if runtime.state_path.is_symlink():
        raise RuntimeError(f"Refusing to read linked wallpaper state: {runtime.state_path}")
    if not runtime.state_path.exists():
        return {}
    try:
        state = json.loads(runtime.state_path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, UnicodeError) as error:
        raise RuntimeError(f"Invalid wallpaper state in {runtime.state_path}: {error}") from error
    if not isinstance(state, dict):
        raise RuntimeError(f"Expected a JSON object in {runtime.state_path}")
    return state


def _digest(path):
    result = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            result.update(chunk)
    return result.digest()


def _current_locked(runtime, state):
    if not runtime.image_path.exists():
        return None
    installed = _digest(runtime.image_path)
    # State is only a search hint: the installed bytes win after an older
    # installer, a source-image edit, or a stale/unknown saved selection.
    hint = state.get("current")
    candidates = list(WALLPAPERS)
    if hint in WALLPAPERS:
        candidates.remove(hint)
        candidates.insert(0, hint)
    for name in candidates:
        source = ROOT / "wallpapers" / f"{name}.webp"
        if source.is_file() and _digest(source) == installed:
            return name
    return None


def current_wallpaper():
    """Return the installed catalogue name, or None for no/unknown wallpaper."""
    runtime = _runtime()
    _check_plugin(runtime)
    with _file_lock(runtime.lock_path):
        return _current_locked(runtime, _read_state(runtime))


def _validate_wallpaper(name):
    if name not in WALLPAPERS:
        raise ValueError(f"Unknown wallpaper {name!r}; choose: {', '.join(WALLPAPERS)}")
    image = ROOT / "wallpapers" / f"{name}.webp"
    if not image.is_file():
        raise ValueError(f"Missing wallpaper image: {image}")
    for filename in ("plugin.toml", "window.luau"):
        source = ROOT / "tern/plugin" / filename
        if not source.is_file():
            raise ValueError(f"Missing wallpaper plugin source: {source}")
    return image


def _reload_plugin(runtime):
    raw = _command(str(runtime.tern), "plugin", "reload", "--json")
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as error:
        raise RuntimeError(f"Tern returned invalid plugin reload JSON: {raw}") from error
    plugins = result.get("plugins", []) if isinstance(result, dict) else []
    if not isinstance(plugins, list):
        raise RuntimeError(f"Tern returned an invalid plugin list: {raw}")
    own = next((plugin for plugin in plugins if isinstance(plugin, dict) and plugin.get("id") == PLUGIN_ID), None)
    if not own or own.get("status") != "ready":
        raise RuntimeError(f"Wallpaper plugin did not load: {raw}")


def _apply_locked(runtime, name, state):
    image = _validate_wallpaper(name)
    backup = runtime.state_dir / "original-wallpaper.webp"
    if runtime.image_path.exists() and not backup.exists():
        _atomic_copy(runtime.image_path, backup)
        backup.chmod(0o600)
    runtime.plugin_dir.mkdir(parents=True, exist_ok=True)
    for filename in ("plugin.toml", "window.luau"):
        _atomic_copy(ROOT / "tern/plugin" / filename, runtime.plugin_dir / filename)
    _atomic_copy(image, runtime.image_path)
    state.update(version=1, current=name)
    _atomic_json(runtime.state_path, state)
    try:
        _reload_plugin(runtime)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        raise RuntimeError(f"Saved {name}, but Tern could not reload its wallpaper: {error}") from error
    return name


def apply_wallpaper(name):
    """Apply only this project's wallpaper plugin; never change preferences."""
    _validate_wallpaper(name)
    runtime = _runtime()
    _check_plugin(runtime)
    with _file_lock(runtime.lock_path):
        return _apply_locked(runtime, name, _read_state(runtime))


def _step_locked(runtime, state, direction):
    current = _current_locked(runtime, state)
    if current is None:
        if runtime.image_path.exists():
            raise RuntimeError("Installed wallpaper is not in the catalogue; use tern-bg set NAME first.")
        name = WALLPAPERS[0 if direction > 0 else -1]
    else:
        name = WALLPAPERS[(WALLPAPERS.index(current) + direction) % len(WALLPAPERS)]
    return _apply_locked(runtime, name, state)


def _step(direction):
    runtime = _runtime()
    _check_plugin(runtime)
    with _file_lock(runtime.lock_path):
        return _step_locked(runtime, _read_state(runtime), direction)


def next_wallpaper():
    return _step(1)


def previous_wallpaper():
    return _step(-1)


def install_cli(bin_dir=None):
    """Install an absolute source symlink, refusing any unrelated existing file."""
    directory = Path(bin_dir) if bin_dir is not None else Path.home() / ".local/bin"
    target = directory / "tern-bg"
    if target.is_symlink():
        if target.resolve() == SOURCE:
            return target
        raise RuntimeError(f"Refusing to overwrite an unrelated command: {target}")
    if target.exists():
        raise RuntimeError(f"Refusing to overwrite an unrelated command: {target}")
    directory.mkdir(parents=True, exist_ok=True)
    # symlink() cannot overwrite a file created by somebody else in the gap.
    target.symlink_to(SOURCE)
    return target


def parse_duration(value):
    """Parse s/m/h to positive whole launchd seconds without rounding."""
    match = re.fullmatch(r"(\d+(?:\.\d+)?|\.\d+)\s*([smh])", value.strip(), re.IGNORECASE)
    message = "Interval must be a positive whole number of seconds using s, m or h (for example 15m)."
    if not match:
        raise ValueError(message)
    try:
        with localcontext() as context:
            context.prec = max(28, len(match[1]) + 4)
            seconds = Decimal(match[1]) * {"s": 1, "m": 60, "h": 3600}[match[2].lower()]
            if not seconds.is_finite() or seconds <= 0 or seconds > MAX_INTERVAL or seconds != seconds.to_integral_value():
                raise ValueError(message)
            return int(seconds)
    except InvalidOperation as error:
        raise ValueError(message) from error


def _require_macos():
    if sys.platform != "darwin":
        raise RuntimeError("Wallpaper rotation requires macOS launchd.")


def _schedule_path():
    return Path.home() / "Library/LaunchAgents" / f"{AGENT_LABEL}.plist"


def _schedule_lock_path():
    return Path.home() / "Library/Application Support" / PLUGIN_ID / "rotation.lock"


def _read_schedule():
    path = _schedule_path()
    if path.is_symlink():
        raise RuntimeError(f"Refusing to use a linked LaunchAgent: {path}")
    if not path.exists():
        return None
    try:
        schedule = plistlib.loads(path.read_bytes())
    except (plistlib.InvalidFileException, ValueError, TypeError, ExpatError) as error:
        raise RuntimeError(f"Invalid wallpaper LaunchAgent in {path}: {error}") from error
    args = schedule.get("ProgramArguments", []) if isinstance(schedule, dict) else []
    environment = schedule.get("EnvironmentVariables", {}) if isinstance(schedule, dict) else {}
    interval = schedule.get("StartInterval") if isinstance(schedule, dict) else None
    if not (
        isinstance(schedule, dict) and schedule.get("Label") == AGENT_LABEL
        and isinstance(args, list) and len(args) == 5 and all(isinstance(arg, str) for arg in args)
        and Path(args[1]).name == SOURCE.name and args[2:4] == ["_tick", "--generation"]
        and re.fullmatch(r"[0-9a-f]{32}", args[4])
        and isinstance(environment, dict) and isinstance(environment.get("TERN_CONFIG_DIR"), str)
        and type(interval) is int and 0 < interval <= MAX_INTERVAL
    ):
        raise RuntimeError(f"Refusing to replace an unrelated or invalid LaunchAgent: {path}")
    return schedule


def _launchctl(*args):
    return subprocess.run(("/bin/launchctl", *args), capture_output=True, text=True, timeout=30)


def _domain():
    return f"gui/{os.getuid()}"


def _agent_loaded():
    return _launchctl("print", f"{_domain()}/{AGENT_LABEL}").returncode == 0


def _launchctl_checked(*args):
    result = _launchctl(*args)
    if result.returncode:
        detail = result.stderr.strip() or result.stdout.strip() or f"exit {result.returncode}"
        raise RuntimeError(f"launchctl {' '.join(args)}: {detail}")


def _unload():
    _launchctl_checked("bootout", f"{_domain()}/{AGENT_LABEL}")


def rotate_wallpapers(interval):
    seconds = parse_duration(interval)
    _require_macos()
    runtime = _runtime()
    _check_plugin(runtime)
    with _file_lock(_schedule_lock_path()):
        previous = _read_schedule()
        was_loaded = _agent_loaded()
        if was_loaded and previous is None:
            raise RuntimeError("Wallpaper rotation is loaded without its plist; run tern-bg stop before configuring it.")
        with _file_lock(runtime.lock_path):
            state = _read_state(runtime)
            if _current_locked(runtime, state) is None and runtime.image_path.exists():
                raise RuntimeError("Installed wallpaper is not in the catalogue; use tern-bg set NAME first.")
        # Capture this configuration and native binary's PATH for launchd, which
        # does not inherit the interactive shell environment.
        paths = [str(runtime.tern.parent), *os.environ.get("PATH", os.defpath).split(os.pathsep)]
        schedule = {
            "Label": AGENT_LABEL,
            "ProgramArguments": [str(Path(sys.executable).resolve()), str(SOURCE), "_tick", "--generation", uuid.uuid4().hex],
            "EnvironmentVariables": {
                "TERN_CONFIG_DIR": str(runtime.plugins_dir.parent),
                "PATH": os.pathsep.join(dict.fromkeys(path for path in paths if path)),
            },
            "StartInterval": seconds,
            "RunAtLoad": False,
            "ProcessType": "Background",
        }
        path = _schedule_path()
        previous_bytes = path.read_bytes() if previous else None
        if was_loaded:
            _unload()
        try:
            _atomic_write(path, plistlib.dumps(schedule))
            _launchctl_checked("bootstrap", _domain(), str(path))
            if not _agent_loaded():
                raise RuntimeError("Wallpaper LaunchAgent was configured but did not load.")
        except (OSError, RuntimeError, subprocess.TimeoutExpired) as error:
            try:
                if _agent_loaded():
                    _unload()
                if previous_bytes is None:
                    path.unlink(missing_ok=True)
                else:
                    _atomic_write(path, previous_bytes)
                    if was_loaded:
                        _launchctl_checked("bootstrap", _domain(), str(path))
            except (OSError, RuntimeError, subprocess.TimeoutExpired) as rollback_error:
                raise RuntimeError(f"Rotation setup failed: {error}; restoring previous schedule also failed: {rollback_error}") from error
            raise RuntimeError(f"Rotation setup failed; previous schedule restored: {error}") from error
    return seconds


def stop_rotation():
    _require_macos()
    with _file_lock(_schedule_lock_path()):
        schedule = _read_schedule()
        loaded = _agent_loaded()
        if loaded:
            _unload()
        if schedule:
            _schedule_path().unlink()
    return bool(schedule or loaded)


def rotation_status():
    _require_macos()
    with _file_lock(_schedule_lock_path()):
        schedule = _read_schedule()
        return {
            "configured": schedule is not None,
            "loaded": _agent_loaded(),
            "every": schedule["StartInterval"] if schedule else None,
            "config_dir": schedule["EnvironmentVariables"]["TERN_CONFIG_DIR"] if schedule else None,
            "plist": str(_schedule_path()),
        }


def _tick(generation):
    # A queued invocation from a stopped or replaced schedule must not advance
    # anything. Lock order is always schedule first, selection second.
    with _file_lock(_schedule_lock_path()):
        schedule = _read_schedule()
        if schedule is None or schedule["ProgramArguments"][4] != generation:
            return None
        runtime = _runtime()
        if runtime.plugins_dir.parent != Path(schedule["EnvironmentVariables"]["TERN_CONFIG_DIR"]):
            raise RuntimeError("Scheduled Tern configuration differs from the active configuration.")
        _check_plugin(runtime)
        with _file_lock(runtime.lock_path):
            return _step_locked(runtime, _read_state(runtime), 1)


def main(argv=None):
    argv = sys.argv[1:] if argv is None else argv
    parser = argparse.ArgumentParser(description=__doc__)
    if argv and argv[0] == "_tick":
        parser.add_argument("_tick")
        parser.add_argument("--generation", required=True)
        args = parser.parse_args(argv)
        try:
            _tick(args.generation)
        except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
            parser.exit(1, f"tern-bg: {error}\n")
        return 0
    commands = parser.add_subparsers(dest="command", required=True)
    commands.add_parser("list", help="List wallpapers, marking the current selection")
    commands.add_parser("current", help="Print the installed wallpaper name")
    setter = commands.add_parser("set", help="Apply a wallpaper without changing preferences")
    setter.add_argument("name", choices=WALLPAPERS)
    commands.add_parser("next", help="Apply the next wallpaper, wrapping around")
    commands.add_parser("prev", help="Apply the previous wallpaper, wrapping around")
    rotation = commands.add_parser("rotate", help="Enable periodic macOS LaunchAgent rotation")
    rotation.add_argument("--every", required=True, metavar="INTERVAL", help="Positive duration using s, m or h, e.g. 15m")
    commands.add_parser("stop", help="Unload and remove only this project's rotation schedule")
    commands.add_parser("status", help="Show whether rotation is configured and loaded")
    args = parser.parse_args(argv)
    try:
        if args.command == "list":
            current = current_wallpaper()
            for name in WALLPAPERS:
                print(f"{'*' if name == current else ' '} {name}")
        elif args.command == "current":
            runtime = _runtime()
            _check_plugin(runtime)
            with _file_lock(runtime.lock_path):
                current = _current_locked(runtime, _read_state(runtime))
                print(current or ("unknown" if runtime.image_path.exists() else "none"))
        elif args.command == "set":
            print(apply_wallpaper(args.name))
        elif args.command == "next":
            print(next_wallpaper())
        elif args.command == "prev":
            print(previous_wallpaper())
        elif args.command == "rotate":
            seconds = rotate_wallpapers(args.every)
            print(f"Rotation configured every {seconds}s (loaded).")
        elif args.command == "stop":
            stop_rotation()
            print("Rotation stopped; LaunchAgent removed.")
        elif args.command == "status":
            status = rotation_status()
            print(f"Configured: {'yes' if status['configured'] else 'no'}")
            print(f"Loaded: {'yes' if status['loaded'] else 'no'}")
            if status["configured"]:
                print(f"Interval: {status['every']}s")
                print(f"Tern configuration: {status['config_dir']}")
            print(f"LaunchAgent: {status['plist']}")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"tern-bg: {error}\n")
    return 0


if __name__ == "__main__":
    sys.exit(main())
