# 视频请求路径基线

本目录在学习分支 `workbench/luca` 上，规则见上一级的 AGENTS.md。

## 目的

量出一个视频请求在 vLLM 里每一段花多少时间，找一个没人报过的瓶颈。

| 段 | 谁来测 | 需要 GPU |
|---|---|---|
| 读文件 + 解码 + 抽帧 | `time_decode.py`（直接量） | 否 |
| processor（HF processor 等） | `time_stages.py`（vLLM 自带统计） | 是 |
| 排队 | `time_stages.py` | 是 |
| vision encoder | `time_stages.py`（vLLM 自带统计） | 是 |
| prefill 其余部分 | `time_stages.py` | 是 |

vLLM 自带的 `vllm bench mm-processor` 只覆盖 processor 和 encoder，不覆盖解码，
所以解码单独量。`time_stages.py` 里的 `fetch_decode_ms` 是用总时间减出来的，
含 IPC 等开销，只作交叉核对；解码的数字以 `time_decode.py` 为准。

## 在 GPU 机器上的步骤

```bash
# 1. 环境（按仓库 AGENTS.md）
git clone https://github.com/vllm-project/vllm.git && cd vllm
uv venv --python 3.12 && source .venv/bin/activate
VLLM_USE_PRECOMPILED=1 uv pip install -e . --torch-backend=auto
uv pip install torchcodec          # 可选，用来对比解码后端
sudo apt-get install -y ffmpeg     # 造视频用

# 2. 切到 workbench/luca 分支（或把本目录拷过去），然后造视频（36 个，约几个 GB）
python make_videos.py --out videos

# 3. 解码段：两种解码后端，1 线程和 8 线程
python time_decode.py --sampling qwen3_vl --codec opencv torchcodec --threads 1 8

# 4. 全流程分段（模型按实际可用的换）
python time_stages.py --model <Qwen3-VL 小模型> --repeats 3
```

记下 `git rev-parse HEAD`、CPU 型号和核数、`nvidia-smi` 输出，之后写 issue 要用。

5 分钟的 1080p 片段在默认抽帧下 token 数会超过上下文，`time_stages.py` 会把它记成
一行 `error` 然后继续，这是预期行为。要测长视频就用 `--media-io-kwargs` 降 fps，
或用 `--mm-processor-kwargs` 限制像素。

## 读结果时重点看什么

下面都是读代码后的猜测，还没有数据支持，跑完再判断哪条成立。

1. **多线程解码不成比例。** 连接器用 8 线程的池并发解码，而 OpenCV 每次解码内部
   还会开最多 16 个线程。看 `speedup_8t` 是否远小于 8。
2. **长 GOP 下抽帧变慢。** 同分辨率同时长，对比 `gop2s` 和 `gop10s` 的
   `ms_per_frame`。
3. **解码输出是全分辨率帧。** 缩放发生在后面的 processor 里。看 `out_mb`：
   高分辨率长视频单个请求可能占几个 GB 内存。
4. **两种解码后端的差距。** `opencv` 是默认值，对比 `torchcodec`。
5. **processor 与 encoder 的占比。** 如果 `hf_processor_ms` 明显大于 `encoder_ms`，
   瓶颈在 CPU 侧。

发现可疑点之后，先在仓库里按 AGENTS.md 查重，再决定写 issue 还是 PR。
