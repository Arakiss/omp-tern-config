#!/usr/bin/env python3
"""Toggle the optional retro-future HUD without changing preferences or wallpaper."""
import argparse
import json
from pathlib import Path
import subprocess
import sys

from tern_bg import _atomic_copy, _atomic_write, _command

ROOT = Path(__file__).resolve().parent
PLUGIN_ID = "omp-tern-config-hud"
FILES = ("plugin.toml", "window.luau", "hud.css")


def plugin_dir():
    destination = Path(_command("tern", "plugin", "dir")) / PLUGIN_ID
    if destination.is_symlink():
        raise RuntimeError(f"Refusing to use a linked HUD plugin: {destination}")
    for name in (*FILES, "enabled"):
        if (destination / name).is_symlink():
            raise RuntimeError(f"Refusing to use a linked HUD file: {destination / name}")
    return destination


def install():
    """Install the native plugin disabled by default; preserve an existing mode."""
    target = Path.home() / ".local/bin/tern-ui"
    source = Path(__file__).resolve()
    if target.is_symlink():
        if target.resolve() != source:
            raise RuntimeError(f"Refusing to overwrite an unrelated command: {target}")
    elif target.exists():
        raise RuntimeError(f"Refusing to overwrite an unrelated command: {target}")
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.symlink_to(source)
    destination = plugin_dir()
    destination.mkdir(parents=True, exist_ok=True)
    for name in FILES:
        _atomic_copy(ROOT / "tern/ui" / name, destination / name)
    return target


def mode():
    destination = plugin_dir()
    if not (destination / "plugin.toml").is_file():
        raise RuntimeError("HUD plugin is not installed. Run python3 install.py first.")
    return "on" if (destination / "enabled").is_file() else "off"


def set_mode(enabled):
    mode()  # Require an installed, unlinked plugin before changing it.
    marker = plugin_dir() / "enabled"
    if enabled:
        _atomic_write(marker, b"on\n")
    else:
        marker.unlink(missing_ok=True)
    # The installed native API reloads all plugins. This syncs already-open windows.
    result = json.loads(_command("tern", "plugin", "reload", "--json"))
    own = next((p for p in result.get("plugins", []) if p.get("id") == PLUGIN_ID), None)
    if not own or own.get("status") != "ready":
        raise RuntimeError(f"HUD mode saved, but the plugin did not load: {result}")
    return mode()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("mode", choices=("on", "off", "status"))
    args = parser.parse_args()
    try:
        print(f"HUD: {mode() if args.mode == 'status' else set_mode(args.mode == 'on')}")
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"tern-ui: {error}\n")


if __name__ == "__main__":
    main()
