"""Time the fetch-side video stage that `vllm bench mm-processor` does not cover.

Calls `VideoMediaIO.load_bytes` exactly as the media connector does: bytes in,
sampled frames out. This is decode + frame sampling; no GPU or model needed.

For each clip it reports single-call latency, then throughput with N calls in
a thread pool (the connector runs loads in a pool of
VLLM_MEDIA_LOADING_THREAD_COUNT threads, default 8), so poor scaling shows up
as `speedup` well below `threads`.

Usage:
    python time_decode.py --manifest videos/manifest.json \
        --sampling qwen3_vl --codec opencv torchcodec --threads 1 8
"""

import argparse
import json
import statistics
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

from vllm.multimodal.media import ImageMediaIO, VideoMediaIO


def describe(frames) -> tuple[int, str, float]:
    shape = tuple(frames.shape)
    nbytes = frames.nbytes if hasattr(frames, "nbytes") else frames.numel()
    return shape[0], "x".join(map(str, shape[1:])), nbytes / 2**20


def bench_clip(
    io: VideoMediaIO,
    data: bytes,
    repeats: int,
    threads: list[int],
    mem_budget_gb: float,
):
    io.load_bytes(data)  # warm up codec init and page cache

    single = []
    for _ in range(repeats):
        t0 = time.perf_counter()
        media = io.load_bytes(data)
        single.append(time.perf_counter() - t0)
    frames, _ = media.media
    num_frames, frame_shape, out_mb = describe(frames)

    row = {
        "frames_out": num_frames,
        "frame_shape": frame_shape,
        "out_mb": round(out_mb, 1),
        "decode_ms_median": round(statistics.median(single) * 1e3, 1),
        "decode_ms_min": round(min(single) * 1e3, 1),
        "ms_per_frame": round(statistics.median(single) * 1e3 / num_frames, 2),
    }
    del media, frames
    base_rate = 1 / statistics.median(single)

    def load_and_drop(_) -> None:
        io.load_bytes(data)

    for n in threads:
        if n == 1:
            continue
        # n decoded clips are alive at once.
        if n * out_mb / 1024 > mem_budget_gb:
            row[f"speedup_{n}t"] = "skipped: over --mem-budget-gb"
            continue
        jobs = n * repeats
        with ThreadPoolExecutor(max_workers=n) as pool:
            t0 = time.perf_counter()
            list(pool.map(load_and_drop, range(jobs)))
            rate = jobs / (time.perf_counter() - t0)
        row[f"speedup_{n}t"] = round(rate / base_rate, 2)
    return row


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--manifest", type=Path, default=Path("videos/manifest.json"))
    parser.add_argument(
        "--sampling",
        default="qwen3_vl",
        help="frame-sampling backend (the `video_backend` media-io kwarg)",
    )
    parser.add_argument(
        "--codec",
        nargs="+",
        default=["opencv"],
        help="decoder backends (the `backend` media-io kwarg)",
    )
    parser.add_argument("--threads", nargs="+", type=int, default=[1, 8])
    parser.add_argument("--repeats", type=int, default=5)
    parser.add_argument("--mem-budget-gb", type=float, default=16.0)
    parser.add_argument("--fps", type=float, default=None, help="override target fps")
    parser.add_argument("--out", type=Path, default=Path("decode_results.json"))
    args = parser.parse_args()

    clips = json.loads(args.manifest.read_text())
    rows = []
    for codec in args.codec:
        kwargs = {"video_backend": args.sampling, "backend": codec}
        if args.fps is not None:
            kwargs["fps"] = args.fps
        io = VideoMediaIO(ImageMediaIO(), num_frames=-1, **kwargs)
        for clip in clips:
            data = Path(clip["path"]).read_bytes()
            try:
                row = bench_clip(
                    io, data, args.repeats, args.threads, args.mem_budget_gb
                )
            except Exception as exc:  # keep going; a failure is a finding too
                row = {"error": f"{type(exc).__name__}: {exc}"[:200]}
            row = {
                "clip": Path(clip["path"]).stem,
                "codec_backend": codec,
                "size_mb": clip["size_mb"],
                **row,
            }
            rows.append(row)
            print(json.dumps(row))

    args.out.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
