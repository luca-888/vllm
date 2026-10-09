# Learning branch

`workbench/luca` exists for learning vLLM: reading, instrumenting, measuring,
drawing. Nothing on it is a contribution, so the production rules in the root
`AGENTS.md` are relaxed here. This applies to `_workbench/` and to experimental
edits of vLLM source made on this branch.

## Relaxed here

- **No contribution gate.** No duplicate-work search, no busywork rule, no PR
  checklist. Small, throwaway, and exploratory changes are the point.
- **Edit vLLM source freely to learn.** Add timers, prints, asserts, or rewrite
  a function to see what breaks. Prefix those commits with `exp:` so they are
  easy to find and drop.
- **Explain generously.** Comments, notes, and diagrams are written for a
  learner, in Chinese where that reads better. Ignore "minimize comments" and
  "assume the reader knows vLLM".
- **No test or style bar.** Scripts need no tests; one-off benchmarks belong
  here. Line length, docstring format, and commit sign-off are not enforced.

## Don't ask, just do

Luca has pre-authorized everything on this branch and on the experiment box
(`ssh gpu-117`, repo at `/root/vllm`, needs `sudo`). Do not stop to ask for
confirmation; act, then report what was done.

- Reading and writing under `/root/vllm` with `sudo`, running experiments,
  installing packages there.
- Committing and pushing to `workbench/luca`.

Only stop for deleting results or data that cannot be regenerated, and for
anything that touches upstream `vllm-project/vllm`.

## Still holds

- **Python goes through `uv` and `.venv/bin/python`.**
- **Say what was measured and what was only read.** A number is either from a
  run on named hardware or it is a guess.
- **Nothing leaves this branch as-is.** A finding that becomes an issue or PR is
  redone on a fresh branch from `main` under the full root rules: rewritten, not
  cherry-picked, and reproduced with public inputs only.

## Layout

- `video_baseline/` — per-stage timing of the video request path.
- `viz/` — HTML pages. A page may also be published from a separate source
  file; update both copies.
