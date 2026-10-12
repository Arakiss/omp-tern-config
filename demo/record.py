#!/usr/bin/env python3
"""Replay the vetted real English Orbit session in Tern's native renderer.

Usage: python3 demo/record.py --output /tmp/omp-tern-native.mp4
Requires Tern and FFmpeg on PATH. No model request, private session or desktop
capture is performed. The included TSP trace is a real run, not invented output.
"""
import argparse
import base64
import json
from pathlib import Path
import shutil
import socket
import subprocess
import tempfile
import time
import os

ROOT = Path(__file__).resolve().parents[1]
TRACE = ROOT / "demo/orbit.out.jsonl"
PACKS = ("ghost-shell", "cyberpunk", "replicant", "dunes")


def wallpaper_sheet(pack):
    # Use the exact CSS literal owned by the native wallpaper plugin.
    template = (ROOT / "tern/plugin/window.luau").read_text(encoding="utf-8")
    opener = 'tern.css("wallpaper", [['
    image_slot = ']] .. image .. [['
    if template.count(opener) != 1 or template.count(image_slot) != 1 or not template.rstrip().endswith("]])"):
        raise ValueError("Wallpaper plugin CSS format changed; update the demo extractor.")
    body = template.split(opener, 1)[1].rstrip()[:-3]
    image = base64.b64encode((ROOT / "wallpapers" / f"{pack}.webp").read_bytes()).decode("ascii")
    return body.replace(image_slot, image)


def wait_for_server(process, endpoint):
    deadline = time.monotonic() + 30
    while time.monotonic() < deadline:
        if process.poll() is not None:
            raise RuntimeError(f"Tern exited during startup ({process.returncode}).")
        with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as connection:
            try:
                connection.connect(str(endpoint))
                return
            except (FileNotFoundError, ConnectionRefusedError):
                time.sleep(0.05)
    raise RuntimeError("Tern's isolated control socket did not become ready.")


def record(output, overwrite=False, hud=False):
    tern = shutil.which("tern")
    if not tern or not shutil.which("ffmpeg"):
        raise RuntimeError("Install Tern and FFmpeg and put both on PATH.")
    if output.suffix.lower() != ".mp4" or output.is_symlink():
        raise ValueError("Output must be a non-symlink .mp4 path.")
    if output.exists() and not overwrite:
        raise ValueError(f"Output exists: {output}; pass --overwrite only for an owned demo.")
    if not output.parent.is_dir():
        raise ValueError(f"Output directory does not exist: {output.parent}")
    rows = [json.loads(line) for line in TRACE.read_text(encoding="utf-8").splitlines() if line.strip()]
    duration = max(row["t"] for row in rows) - min(row["t"] for row in rows)
    with tempfile.TemporaryDirectory(prefix="omp-tern-public-", dir="/tmp") as folder:
        scratch = Path(folder)
        endpoint = scratch / "control.sock"
        frames = scratch / "frames"
        sheets = {}
        for pack in PACKS:
            sheets[pack] = scratch / f"{pack}.css"
            sheets[pack].write_text(wallpaper_sheet(pack), encoding="utf-8")
        environment = os.environ.copy()
        environment.update(TERN_CONFIG_DIR=str(scratch), TERN_DAEMON_SOCKET=str(scratch / "daemon.sock"))
        with (scratch / "renderer.log").open("w", encoding="utf-8") as log:
            process = subprocess.Popen(
                [tern, "serve", "--control", str(endpoint), "--out", str(frames)],
                cwd=scratch, env=environment, stdout=log, stderr=subprocess.STDOUT,
            )
            try:
                wait_for_server(process, endpoint)
                # ctl resolves special file arguments before its scenario tokenizer.
                # Bare scratch filenames avoid its quoted-path handling and clone-path spaces.
                shutil.copyfile(TRACE, scratch / "orbit.out.jsonl")
                lines = [
                    "size 1440 900 1", "font 18", "ui-font-size 15",
                    "theme dark titanium", "style solid", "pane-headers always", "status-bar on",
                    'carly lua "return cx.settings:set([[theme]], [[Dark]])"', "carly close",
                    'rename "ORBIT / Real coding demo"',
                    "css demo-wallpaper ghost-shell.css",
                ]
                if hud:
                    shutil.copyfile(ROOT / "tern/ui/hud.css", scratch / "hud.css")
                    lines.append("css demo-hud hud.css")
                lines += [
                    "wait 5000",
                    "surface-play orbit.out.jsonl",
                    "record start native-demo fps 30 speed 1",
                    "surface-play orbit.out.jsonl paced 1",
                    "wait 7000",
                    "css demo-wallpaper cyberpunk.css",
                    f"wait {max(duration - 7000, 0) + 2500}",
                    "css demo-wallpaper replicant.css", "wait 2500",
                    "css demo-wallpaper dunes.css", "wait 2500",
                    "css demo-wallpaper ghost-shell.css", "wait 3000",
                    "record stop",
                ]
                scenario = scratch / "record.txt"
                scenario.write_text("\n".join(lines) + "\n", encoding="utf-8")
                result = subprocess.run(
                    [tern, "ctl", "--control", str(endpoint), "--file", str(scenario)],
                    cwd=scratch, env=environment, capture_output=True, text=True, timeout=300,
                )
                if result.returncode:
                    raise RuntimeError(result.stderr.strip() or result.stdout.strip())
                recording = frames / "serve/native-demo.mp4"
                if not recording.is_file():
                    raise RuntimeError(f"Native recorder returned no footage: {result.stdout}")
                with recording.open("rb") as source, output.open("wb" if overwrite else "xb") as destination:
                    shutil.copyfileobj(source, destination)
                print(result.stdout.strip())
                print(f"Native recording: {output}")
            finally:
                if process.poll() is None:
                    try:
                        subprocess.run([tern, "ctl", "--control", str(endpoint), "quit"],
                                       capture_output=True, timeout=5, check=False)
                        process.wait(timeout=5)
                    except (OSError, subprocess.TimeoutExpired):
                        process.terminate()
                        try:
                            process.wait(timeout=5)
                        except subprocess.TimeoutExpired:
                            process.kill()
                            process.wait()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", required=True, type=Path)
    parser.add_argument("--overwrite", action="store_true")
    parser.add_argument("--hud", action="store_true", help="Opt in to this pack's static neon chrome")
    args = parser.parse_args()
    try:
        record(args.output.expanduser().absolute(), args.overwrite, args.hud)
    except (OSError, ValueError, RuntimeError, subprocess.TimeoutExpired) as error:
        parser.exit(1, f"record.py: {error}\n")


if __name__ == "__main__":
    main()
