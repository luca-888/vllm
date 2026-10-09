"""Generate a reproducible video workload with ffmpeg's built-in sources.

Every clip comes from `testsrc2`, so anyone with ffmpeg gets the same bytes'
worth of content without downloading a dataset. Edit MATRIX to match the shape
of your real workload (duration, resolution, fps, codec, GOP).

Usage:
    python make_videos.py --out videos
"""

import argparse
import itertools
import json
import subprocess
from pathlib import Path

# (duration_s, (width, height), fps, codec, gop_seconds)
DURATIONS = [10, 60, 300]
RESOLUTIONS = [(640, 360), (1280, 720), (1920, 1080)]
FPS = [30]
CODECS = ["libx264", "libx265"]
# Long GOPs make seeking to a sampled frame expensive; 2 s is a common
# streaming default, 10 s is typical of camera/archival footage.
GOP_SECONDS = [2, 10]


def make(out_dir: Path, duration, size, fps, codec, gop_s) -> dict:
    w, h = size
    tag = "h264" if codec == "libx264" else "h265"
    path = out_dir / f"{tag}_{w}x{h}_{fps}fps_{duration}s_gop{gop_s}s.mp4"
    if not path.exists():
        cmd = [
            "ffmpeg", "-loglevel", "error", "-y",
            "-f", "lavfi",
            "-i", f"testsrc2=size={w}x{h}:rate={fps}:duration={duration}",
            "-c:v", codec, "-preset", "medium", "-crf", "23",
            "-g", str(gop_s * fps), "-pix_fmt", "yuv420p",
            "-movflags", "+faststart",
        ]  # fmt: skip
        if codec == "libx265":
            cmd += ["-tag:v", "hvc1", "-x265-params", "log-level=error"]
        subprocess.run([*cmd, str(path)], check=True)
    return {
        "path": str(path.resolve()),
        "codec": tag,
        "width": w,
        "height": h,
        "fps": fps,
        "duration_s": duration,
        "gop_s": gop_s,
        "size_mb": round(path.stat().st_size / 2**20, 2),
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", type=Path, default=Path("videos"))
    parser.add_argument(
        "--quick", action="store_true", help="only the 10 s clips, for a smoke test"
    )
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)

    durations = DURATIONS[:1] if args.quick else DURATIONS
    manifest = [
        make(args.out, *combo)
        for combo in itertools.product(durations, RESOLUTIONS, FPS, CODECS, GOP_SECONDS)
    ]
    (args.out / "manifest.json").write_text(json.dumps(manifest, indent=2))
    print(f"{len(manifest)} clips -> {args.out}/manifest.json")


if __name__ == "__main__":
    main()
