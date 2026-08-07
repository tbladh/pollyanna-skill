# Pollyanna

Portable Pollyanna skill and cross-harness installer.

Pollyanna is an explicitly invoked, audacious expedition partner for ambitious, exploratory, and apparently blocked work. Part companion, part inventive investigator, and part demanding coach, she seeks the intended outcome, investigates the available world, challenges assumptions, and keeps turning gaps into possible next moves while leaving consequential action under human control.

## Install

Run the installer from a clone:

```bash
./install.sh
```

Or select a single target, for example `./install.sh --codex`. The Bash and PowerShell installers render `template/skill` using `config/defaults.env`, then install transactionally to the selected global skill locations. Existing installs require confirmation unless `--yes` (or `-Yes`) is supplied.

Supported targets are Codex, Claude, Cursor, Kiro, Cline, GitHub Copilot, and Windsurf. By default, the installers target Codex, Claude, Cursor, Kiro, and Cline. Use `--legacy-codex` or `-LegacyCodex` to also install into the legacy Codex skill location.

For raw-script bootstrap, keep `POLLYANNA_REPO_ARCHIVE_URL` aligned with `DEFAULT_REPO_ARCHIVE_URL` in `config/defaults.env`.

## Repository overlay

When invoked inside a repository, Pollyanna offers to install or upgrade a thin governing layer after user approval. The installation creates root-level `POLLYANNA.md`, stores support files and version metadata under `.pollyanna/`, and inserts a small managed hook near the top of the selected workflow instructions. It preserves existing downstream workflow procedures and never commits or pushes without separate permission.

## Research notebook

Pollyanna keeps durable research under `~/pollyanna/docs/YYYY-MM-DD/{nn}-{slug}` and bulky public-source material under matching `~/pollyanna/data/...` entries when needed. `~/pollyanna/docs/memory.md` stores concise collaboration preferences. These records must not contain secrets, credentials, sensitive personal information, or private source content.
