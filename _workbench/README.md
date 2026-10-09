# 工作台

个人脚本和可视化，只存在于 `workbench/luca` 分支。

**这个分支不向上游提 PR。** 要提 PR 时从 `main` 另开分支，不要从这里开。

| 目录 | 内容 |
|---|---|
| `video_baseline/` | 视频请求路径的分段计时脚本，说明见其中的 README |
| `viz/vllm-parts-map.html` | vLLM 部件图，浏览器直接打开 |

同步上游：`git switch main && git pull --ff-only`，然后回到本分支 `git rebase main`。
