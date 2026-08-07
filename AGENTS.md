# Pollyanna Repo

<!-- pollyanna:hook:start version=0.5.2 -->
> Read [POLLYANNA.md](POLLYANNA.md) before proceeding. Apply it as the governing guidance for exploration, intent discovery, option framing, and the human-AI interface while preserving this workflow's downstream purpose and procedures.
<!-- pollyanna:hook:end -->


This repository builds and distributes a portable, rename-friendly skill plus installers for Codex, Claude, Cursor, Kiro, Cline, GitHub Copilot, and Windsurf.

## Source of truth

`AGENTS.md` is the shared instruction file for this repo. Keep `CLAUDE.md`, `.cursorrules`, and `.cursor/rules/*.mdc` as thin bridges back to this file.

## Objective

Maintain Pollyanna as an explicitly invoked, ambitious thinking partner that can install a minimally invasive exploration layer over existing repository workflows without changing their downstream purpose.

## Repo layout

- `POLLYANNA.md`: Canonical resident-host personality and source for the portable skill's shared psychological core.
- `template/skill/`: Portable skill source with placeholders.
- `config/defaults.env`: Centralized name, title, and bootstrap URL defaults.
- `scripts/render_skill.py`: Render the template into a concrete skill folder.
- `install.sh` and `install.ps1`: Global installers for the supported harnesses.
- Rendered `scripts/pollyanna-paths*` and `scripts/pollyanna-search*`: Engram-style private research notebook and memory helpers.
- Rendered `scripts/pollyanna-install-repo*`: Consent-gated resident-host integration and upgrade helpers. These remain in the portable skill and are not transferred into hosts.
- `.pollyanna/`: Ignored local scratch state only; never treat its contents as source.

## Working rules

- Keep the portable skill free of harness-specific behavior.
- Keep resident behavior canonical in root `POLLYANNA.md`; render its shared core into the portable skill instead of duplicating it by hand.
- Update the installer, template, and config together when changing the name or paths.
- Keep concrete motivating tasks out of the skill. Encode the general posture and make it derive solutions from intent, capability discovery, research, and first principles.
- Preserve existing workflows. Repository installation may govern exploration and the human-AI interface, but must not rewrite downstream procedures.
- Run `uv run scripts/validate.py` before considering changes complete. It owns validation dependencies, validates the rendered artifact and installers, and proves that self-installation is a no-op.
- Use a short-lived branch and pull request for normal changes to this repository. Keep `main` as the branch served by the public bootstrap commands.
- Treat committing, pushing, creating a pull request, and merging it as separate actions that each require unmistakable user approval at the moment of action. Never infer approval from an implementation request, a stated branch or destination, or a plan to use pull requests.
