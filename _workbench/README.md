# 学习工作台

`workbench/luca` 分支是专门用来学 vLLM 的地方：读代码、加插桩、做测量、画图。
这里不受上游贡献规则约束，具体放宽了什么见 [AGENTS.md](AGENTS.md)。

可以放在这里的东西：

- 测量和实验脚本
- 可视化页面和笔记
- 为了看清行为而对 vLLM 源码做的临时改动（提交信息以 `exp:` 开头）

唯一的硬边界：这里的东西不直接进上游。要提 issue 或 PR 时，从 `main` 另开分支重做。

| 目录 | 内容 |
|---|---|
| `video_baseline/` | 视频请求路径的分段计时脚本 |
| `viz/vllm-parts-map.html` | vLLM 部件图，浏览器直接打开 |

同步上游：`git switch main && git pull --ff-only`，回到本分支后 `git rebase main`。
