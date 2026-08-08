# Contributing to Pollyanna

`main` is the live source for Pollyanna's public bootstrap commands. Normal changes therefore travel through a short-lived branch and a pull request.

1. Create a branch from current `main`.
2. Make one focused change.
3. Run `uv run scripts/validate.py` locally and review any token-cost growth warning before proceeding.
4. Push the branch and open a pull request.
5. Let the GitHub checks pass on Linux, Windows, and macOS.
6. Review the change, then merge the pull request.

For a solo-maintained repository, the author may perform that review and explicitly approve the merge. Require a pull request and passing checks on `main`, but do not require a second reviewer merely to satisfy a setting.

Keep the portable skill, resident policy, renderer, installers, and documentation aligned. Do not commit generated scratch data under `.pollyanna/`.

Agents must obtain distinct human approval before committing, pushing, creating a pull request, or merging it. These gates keep the human in control; they do not alter the one-command installation experience.
