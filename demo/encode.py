#!/usr/bin/env python3
"""Encode real native Tern footage for a public demo; never synthesize frames.

Usage:
    python3 demo/encode.py INPUT.mp4 --gif OUTPUT.gif --video OUTPUT.mp4
    python3 demo/encode.py INPUT.mp4 --gif OUTPUT.gif --video OUTPUT.mp4 --width 1280 --fps 15 --overwrite

Requires FFmpeg on PATH with libx264 and the palettegen/paletteuse filters.
Optional --optimize-gif requires gifsicle; it preserves size/timing and applies mild lossy=20.
Only publish footage already reviewed for private content: removing metadata
cannot remove credentials, conversations, or other information visible on screen.
"""

import argparse
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


def positive_integer(value):
    try:
        number = int(value)
    except ValueError as error:
        raise argparse.ArgumentTypeError("must be a positive integer") from error
    if number <= 0:
        raise argparse.ArgumentTypeError("must be a positive integer")
    return number


def validate_paths(source, outputs, overwrite):
    if not source.is_file():
        raise ValueError(f"Input is not a regular file: {source}")
    with source.open("rb") as recording:
        if not recording.read(1):
            raise ValueError(f"Input recording is empty: {source}")

    paths = [source, *outputs]
    for index, path in enumerate(paths):
        for other in paths[:index]:
            if path.resolve() == other.resolve() or (
                path.exists() and other.exists() and path.samefile(other)
            ):
                raise ValueError(f"Input and output paths must be distinct: {path} and {other}")

    for path, suffix in zip(outputs, (".gif", ".mp4")):
        if path.suffix.lower() != suffix:
            raise ValueError(f"Output must have a {suffix} extension: {path}")
        if path.is_symlink():
            raise ValueError(f"Refusing to replace a symbolic link: {path}")
        if not path.parent.is_dir():
            raise ValueError(f"Output directory does not exist: {path.parent}")
        if path.exists():
            if not path.is_file():
                raise ValueError(f"Output is not a regular file: {path}")
            if not overwrite:
                raise ValueError(
                    f"Output already exists: {path}; use --overwrite only for owned published assets"
                )


def main():
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("input", type=Path, help="real native Tern MP4 recording")
    parser.add_argument("--gif", required=True, type=Path, help="looping GIF destination")
    parser.add_argument("--video", required=True, type=Path, help="H.264 MP4 destination")
    parser.add_argument("--width", type=positive_integer, default=1280, help="scaled width in pixels (default: 1280)")
    parser.add_argument("--fps", type=positive_integer, default=15, help="output frames per second (default: 15)")
    parser.add_argument("--overwrite", action="store_true", help="explicitly replace owned published output assets")
    parser.add_argument("--optimize-gif", action="store_true", help="Use gifsicle O3 with mild lossy=20 to reduce GIF size without changing dimensions or timing")
    args = parser.parse_args()

    source = args.input.expanduser().absolute()
    gif = args.gif.expanduser().absolute()
    video = args.video.expanduser().absolute()
    try:
        ffmpeg = shutil.which("ffmpeg")
        if ffmpeg is None:
            raise ValueError("FFmpeg is required; install it and put ffmpeg on PATH.")
        validate_paths(source, (gif, video), args.overwrite)
        gifsicle = shutil.which("gifsicle") if args.optimize_gif else None
        if args.optimize_gif and not gifsicle:
            raise ValueError("--optimize-gif requires gifsicle on PATH.")

        # Sample and scale once, before either output branches. Padding adds at
        # most one pixel for an odd requested width, without distorting the text.
        filters = (
            f"[0:v:0]fps={args.fps},scale={args.width}:-2:flags=lanczos:reset_sar=1,"
            "split=2[gif_source][video_source];"
            "[gif_source]split=2[gif_frames][palette_frames];"
            "[palette_frames]palettegen=stats_mode=diff:reserve_transparent=1[palette];"
            "[gif_frames][palette]paletteuse=dither=sierra2_4a:diff_mode=rectangle[gif];"
            "[video_source]pad=ceil(iw/2)*2:ceil(ih/2)*2,format=yuv420p[video]"
        )
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-nostdin",
            "-y" if args.overwrite else "-n",
            "-protocol_whitelist", "file", "-i", str(source),
            "-filter_complex", filters,
            "-map", "[gif]", "-an", "-sn", "-dn",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "gif", "-gifflags", "+offsetting+transdiff", "-loop", "0", "-f", "gif", str(gif),
            "-map", "[video]", "-an", "-sn", "-dn",
            "-map_metadata", "-1", "-map_chapters", "-1",
            "-c:v", "libx264", "-crf", "18", "-preset", "slow",
            "-pix_fmt", "yuv420p", "-movflags", "+faststart",
            "-f", "mp4", str(video),
        ]
        subprocess.run(command, check=True)
        if gifsicle:
            with tempfile.TemporaryDirectory(prefix=".gif-opt-", dir=gif.parent) as directory:
                optimized = Path(directory) / "demo.gif"
                subprocess.run([gifsicle, "--optimize=3", "--lossy=20", str(gif),
                                "--output", str(optimized)], check=True)
                optimized.chmod(gif.stat().st_mode & 0o777)
                os.replace(optimized, gif)
    except (OSError, ValueError) as error:
        print(f"encode.py: {error}", file=sys.stderr)
        return 1
    except subprocess.CalledProcessError as error:
        print(
            f"encode.py: encoding/optimization failed (exit {error.returncode}); see its diagnostic above. "
            "Check the source video and the installed FFmpeg/gifsicle capabilities. "
            "Failed outputs may be incomplete.",
            file=sys.stderr,
        )
        return 1
    except KeyboardInterrupt:
        print("encode.py: encoding interrupted; outputs may be incomplete.", file=sys.stderr)
        return 130

    print(f"GIF: {gif}")
    print(f"MP4: {video}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
