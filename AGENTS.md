# Pollyanna Repo

This repository builds and distributes a portable, rename-friendly skill plus installers for Codex, Claude, Cursor, Kiro, Cline, GitHub Copilot, and Windsurf.

## Source of truth

`AGENTS.md` is the shared instruction file for this repo. Keep `CLAUDE.md`, `.cursorrules`, and `.cursor/rules/*.mdc` as thin bridges back to this file.

## Objective

Maintain Pollyanna as an explicitly invoked, ambitious thinking partner that can install a minimally invasive exploration layer over existing repository workflows without changing their downstream purpose.

## Repo layout

- `template/skill/`: Portable skill source with placeholders.
- `config/defaults.env`: Centralized name, title, and bootstrap URL defaults.
- `scripts/render_skill.py`: Render the template into a concrete skill folder.
- `install.sh` and `install.ps1`: Global installers for the supported harnesses.
- Rendered `scripts/pollyanna-paths*` and `scripts/pollyanna-search*`: Engram-style private research notebook and memory helpers.
- Rendered `scripts/pollyanna-install-repo*`: Consent-gated repository integration and upgrade helpers.

## Working rules

- Keep the portable skill free of harness-specific behavior.
- Update the installer, template, and config together when changing the name or paths.
- Keep concrete motivating tasks out of the skill. Encode the general posture and make it derive solutions from intent, capability discovery, research, and first principles.
- Preserve existing workflows. Repository installation may govern exploration and the human-AI interface, but must not rewrite downstream procedures.
- Validate a rendered skill, not only the template source, before considering changes complete.
- Do not commit or push changes without explicit user approval.
