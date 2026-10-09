"""Per-stage latency of one video request through the offline engine (needs GPU).

For each clip, sends one chat request with max_tokens=1 and splits its
time-to-first-token into:

    fetch_decode  everything outside the stages below, by subtraction from wall
                  time: file read + decode + frame sampling + IPC overhead
    processor     HF processor and the rest of vLLM's mm preprocessing
    queue         engine-core QUEUED -> SCHEDULED
    encoder       vision encoder forward
    prefill_rest  SCHEDULED -> first token, minus encoder

Processor and encoder numbers come from the same registry that
`vllm bench mm-processor` reads; the processor cache is disabled so repeats
are not cache hits.

Usage:
    python time_stages.py --model Qwen/Qwen3-VL-4B-Instruct \
        --manifest videos/manifest.json --repeats 3
"""

import argparse
import json
import statistics
import time
from pathlib import Path

from vllm import LLM, SamplingParams
from vllm.benchmarks.mm_processor import get_timing_stats_from_engine


def run_once(llm: LLM, path: str, sampling_params: SamplingParams) -> dict:
    messages = [
        {
            "role": "user",
            "content": [
                {"type": "video_url", "video_url": {"url": f"file://{path}"}},
                {"type": "text", "text": "Describe this video in one word."},
            ],
        }
    ]
    get_timing_stats_from_engine(llm.llm_engine)  # drop stale entries

    t0 = time.perf_counter()
    (output,) = llm.chat(messages, sampling_params, use_tqdm=False)
    wall = time.perf_counter() - t0

    stats = get_timing_stats_from_engine(llm.llm_engine)
    stage = next(iter(stats.values()), {})
    metrics = output.metrics
    processor = stage.get("preprocessor_total_secs", 0.0)
    encoder = stage.get("encoder_forward_secs", 0.0)
    queue = metrics.scheduled_ts - metrics.queued_ts
    prefill = metrics.first_token_ts - metrics.scheduled_ts
    ttft = metrics.first_token_latency
    return {
        "prompt_tokens": len(output.prompt_token_ids),
        "wall_ms": wall * 1e3,
        "ttft_ms": ttft * 1e3,
        "fetch_decode_ms": (wall - processor - queue - prefill) * 1e3,
        "processor_ms": processor * 1e3,
        "hf_processor_ms": stage.get("apply_hf_processor_secs", 0.0) * 1e3,
        "queue_ms": queue * 1e3,
        "encoder_ms": encoder * 1e3,
        "prefill_rest_ms": (prefill - encoder) * 1e3,
    }


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", required=True)
    parser.add_argument("--manifest", type=Path, default=Path("videos/manifest.json"))
    parser.add_argument("--repeats", type=int, default=3)
    parser.add_argument("--max-model-len", type=int, default=None)
    parser.add_argument(
        "--media-io-kwargs",
        type=json.loads,
        default=None,
        help='e.g. \'{"video": {"fps": 1, "backend": "torchcodec"}}\'',
    )
    parser.add_argument("--mm-processor-kwargs", type=json.loads, default=None)
    parser.add_argument("--out", type=Path, default=Path("stage_results.json"))
    args = parser.parse_args()

    clips = json.loads(args.manifest.read_text())
    media_root = str(Path(clips[0]["path"]).parent)

    llm = LLM(
        model=args.model,
        max_model_len=args.max_model_len,
        limit_mm_per_prompt={"video": 1},
        allowed_local_media_path=media_root,
        media_io_kwargs=args.media_io_kwargs,
        mm_processor_kwargs=args.mm_processor_kwargs,
        mm_processor_cache_gb=0,
        enable_mm_processor_stats=True,
    )
    sampling_params = SamplingParams(max_tokens=1, temperature=0.0)

    rows = []
    for i, clip in enumerate(clips):
        name = Path(clip["path"]).stem
        try:
            if i == 0:
                run_once(llm, clip["path"], sampling_params)  # warm up
            runs = [
                run_once(llm, clip["path"], sampling_params)
                for _ in range(args.repeats)
            ]
            row = {
                key: round(statistics.median(run[key] for run in runs), 1)
                for key in runs[0]
            }
        except Exception as exc:  # e.g. prompt longer than max_model_len
            row = {"error": f"{type(exc).__name__}: {exc}"[:200]}
        row = {"clip": name, **row}
        rows.append(row)
        print(json.dumps(row))

    args.out.write_text(json.dumps(rows, indent=2))
    print(f"\nwrote {args.out}")


if __name__ == "__main__":
    main()
