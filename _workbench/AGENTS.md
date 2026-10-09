# _workbench

Personal scripts and visualizations on the `workbench/luca` branch. Not part of
vLLM; the root `AGENTS.md` contribution policy governs upstream work only.

- **Never upstream this directory.** Start PR branches from `main`, not from
  this branch, and check that the PR diff has no `_workbench/` paths.
- **Publishable findings need public inputs.** Reproductions for issues and PRs
  use the ffmpeg-generated clips, never private or employer data.
- **Move code out when it becomes a contribution.** A script that turns into an
  upstream benchmark or test is rewritten in the upstream location on a fresh
  branch; do not cherry-pick commits from here.
- **Keep both copies of an HTML page in sync.** A page under `viz/` may also be
  published as an artifact from a separate source file; update both.
