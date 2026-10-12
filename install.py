#!/usr/bin/env python3
"""Install omp + Tern Config without copying credentials or replacing unrelated settings."""
import argparse
import copy
from datetime import datetime, timezone
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parent
WALLPAPERS = (
    "replicant", "dunes", "grid", "tron-ares", "altered-carbon",
    "cyberpunk", "ghost-shell", "deus-ex",
)


def merge(base, patch):
    result = copy.deepcopy(base)
    for key, value in patch.items():
        if isinstance(value, dict) and isinstance(result.get(key), dict):
            result[key] = merge(result[key], value)
        else:
            result[key] = copy.deepcopy(value)
    return result


def command(*args):
    return subprocess.check_output(args, text=True).strip()


def atomic_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    mode = path.stat().st_mode & 0o777 if path.exists() else 0o600
    with tempfile.NamedTemporaryFile(mode="w", dir=path.parent, delete=False) as handle:
        temporary = Path(handle.name)
        try:
            json.dump(value, handle, indent=2, ensure_ascii=False)
            handle.write("\n")
            handle.flush()
            os.fsync(handle.fileno())
            temporary.chmod(mode)
            os.replace(temporary, path)
        finally:
            temporary.unlink(missing_ok=True)


def install(autonomous=False, dry_run=False, wallpaper="replicant", cua=False, wallpaper_only=False):
    if wallpaper_only and (autonomous or cua):
        raise ValueError("--wallpaper-only cannot change approval policy or configure CUA.")
    for binary in (("omp", "tern", "cua-driver") if cua else ("omp", "tern")):
        if not shutil.which(binary):
            raise RuntimeError(f"Install {binary} and put it on PATH first.")
    image = ROOT / "wallpapers" / f"{wallpaper}.webp"
    if wallpaper not in WALLPAPERS or not image.is_file():
        raise ValueError(f"Unknown or missing wallpaper: {wallpaper}")
    omp_patch = json.loads((ROOT / "omp/settings.json").read_text())
    tern_patch = json.loads((ROOT / "tern/settings.json").read_text())
    if autonomous:
        omp_patch["tools.approvalMode"] = "yolo"
        tern_patch["paste"] = {"confirm": False}

    omp_dir = Path(command("omp", "config", "path"))
    skill_path = omp_dir / "skills/tern-terminal/SKILL.md"
    if not wallpaper_only and skill_path.is_symlink():
        raise RuntimeError(f"Refusing to replace a linked skill: {skill_path}")
    plugins_dir = Path(command("tern", "plugin", "dir"))
    mcp_path = omp_dir / "mcp.json"
    mcp_patch = None
    if cua:
        existing_mcp = json.loads(mcp_path.read_text()) if mcp_path.exists() else {}
        if not isinstance(existing_mcp, dict) or not isinstance(existing_mcp.get("mcpServers", {}), dict):
            raise ValueError(f"Expected MCP server objects in {mcp_path}")
        if "cua-driver" in existing_mcp.get("disabledServers", []):
            raise ValueError("cua-driver is explicitly disabled in your MCP denylist; remove that entry before opting in.")
        mcp_patch = merge(existing_mcp, json.loads((ROOT / "omp/mcp-cua.json").read_text()))
    tern_settings = plugins_dir.parent / "settings.json"
    existing = json.loads(tern_settings.read_text()) if tern_settings.exists() else {}
    if not isinstance(existing, dict):
        raise ValueError(f"Expected a JSON object in {tern_settings}")
    merged = merge(existing, tern_patch)
    current_roles = json.loads(command("omp", "config", "get", "modelRoles", "--json"))["value"]
    omp_patch["modelRoles"] = merge(current_roles, omp_patch["modelRoles"])
    ignored_skills = json.loads(command("omp", "config", "get", "skills.ignoredSkills", "--json"))["value"]
    omp_patch["skills.ignoredSkills"] = list(dict.fromkeys([*ignored_skills, "cmux-terminal"]))
    destination = plugins_dir / "omp-tern-config-wallpaper"
    if destination.is_symlink():
        raise RuntimeError(f"Refusing to replace a linked plugin: {destination}")

    print(f"omp settings: {omp_dir}")
    print(f"Tern settings: {tern_settings}")
    print(f"Wallpaper plugin: {destination}")
    print(f"Visual pack: {wallpaper}")
    if cua:
        print(f"CUA MCP configuration: {mcp_path}")
    print(f"Approval mode: {'unchanged (wallpaper only)' if wallpaper_only else 'autonomous (yolo)' if autonomous else 'unchanged'}")
    if dry_run:
        print("Dry run: no files changed.")
        return

    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%S%fZ")
    backup = plugins_dir.parent / "omp-tern-config-backups" / stamp
    backup.mkdir(parents=True, mode=0o700)
    if not wallpaper_only:
        for filename in ("config.yml", "config.yaml"):
            source = omp_dir / filename
            if source.exists():
                shutil.copy2(source, backup / filename)
        if cua and mcp_path.exists():
            shutil.copy2(mcp_path, backup / "mcp.json")
        if tern_settings.exists():
            shutil.copy2(tern_settings, backup / "settings.json")
        if skill_path.exists():
            shutil.copy2(skill_path, backup / "tern-terminal-SKILL.md")
    if destination.exists():
        shutil.copytree(destination, backup / "plugin")
    print(f"Backup: {backup}")

    # OMP owns YAML validation, locking and preservation of unrelated keys.
    if not wallpaper_only:
        for key, value in omp_patch.items():
            command("omp", "config", "set", key, json.dumps(value))
        atomic_json(tern_settings, merged)
        skill_path.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(ROOT / "skills/tern-terminal/SKILL.md", skill_path)
        if cua:
            atomic_json(mcp_path, mcp_patch)
    destination.mkdir(parents=True, exist_ok=True)
    for name in ("plugin.toml", "window.luau"):
        shutil.copy2(ROOT / "tern/plugin" / name, destination / name)
    shutil.copy2(image, destination / "wallpaper.webp")
    result = json.loads(command("tern", "plugin", "reload", "--json"))
    own = next((plugin for plugin in result["plugins"] if plugin["id"] == "omp-tern-config-wallpaper"), None)
    if not own or own["status"] != "ready":
        raise RuntimeError(f"Plugin did not load: {json.dumps(result)}")
    if result.get("problems"):
        print(f"Other plugin problems: {json.dumps(result['problems'])}", file=sys.stderr)
    try:
        command("tern", "ctl", "plugins", "run", "reload_config")
    except subprocess.CalledProcessError as error:
        print(f"Settings saved; live reload unavailable ({error}). Reopen Tern.", file=sys.stderr)
    print(f"omp + Tern Config installed with the {wallpaper} visual pack. Provider logins and macOS permissions remain yours.")
    if cua:
        print("CUA added over stdio MCP. Run /mcp reload in an existing omp session.")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="Print targets without changing files")
    parser.add_argument("--autonomous", action="store_true", help="Enable omp yolo mode and disable Tern paste confirmations")
    parser.add_argument("--wallpaper", choices=WALLPAPERS, default="replicant", help="Choose an optional visual pack")
    parser.add_argument("--cua", action="store_true", help="Merge the local CUA Driver MCP server into omp; requires cua-driver on PATH")
    parser.add_argument("--wallpaper-only", action="store_true", help="Change only the wallpaper plugin; leave models, preferences, skills and MCP untouched")
    args = parser.parse_args()
    try:
        install(args.autonomous, args.dry_run, args.wallpaper, args.cua, args.wallpaper_only)
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError) as error:
        parser.exit(1, f"Installation failed: {error}\n")


if __name__ == "__main__":
    main()
