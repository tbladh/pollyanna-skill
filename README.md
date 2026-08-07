# Pollyanna v0.5.1

Pollyanna is an explicitly invoked, audacious expedition partner for ambitious, exploratory, and apparently blocked work. Part companion, part inventive investigator, and part demanding coach, she seeks the intended outcome, investigates the available world, challenges assumptions, and keeps turning gaps into possible next moves while leaving consequential action under human control.

## Supported harnesses

The installer supports global skill installs for Codex, Claude Code, Cursor, Kiro, Cline, GitHub Copilot, and Windsurf.

| Harness | Global installation path | Default broad install |
| --- | --- | --- |
| Codex and compatible harnesses | `~/.agents/skills/pollyanna` | Yes |
| Claude Code | `~/.claude/skills/pollyanna` | Yes |
| Cursor | `~/.cursor/skills/pollyanna` | Yes |
| Kiro | `~/.kiro/skills/pollyanna` | Yes |
| Cline | `~/.cline/skills/pollyanna` | Yes |
| GitHub Copilot native path | `~/.copilot/skills/pollyanna` | Only with the explicit Copilot target |
| Windsurf native path | `~/.codeium/windsurf/skills/pollyanna` | Only with the explicit Windsurf target |
| Legacy Codex | `$CODEX_HOME/skills/pollyanna`, otherwise `~/.codex/skills/pollyanna` | Only when explicitly requested |

The default Codex-compatible `~/.agents/skills/pollyanna` installation can also be discovered by GitHub Copilot and Windsurf. Their native paths are therefore opt-in.

## Requirements

- Python 3 available as `python3`, `python`, or the Windows `py -3` launcher.
- For the Bash remote bootstrap: `curl` and `tar`.
- For installation from a clone: Git, or another way to obtain the repository.
- Permission to create the selected global skill directories and `~/pollyanna/docs/memory.md`.

## Quick install

> [!WARNING]
> The quick installer is intentionally broad. It installs Pollyanna for Codex, Claude Code, Cursor, Kiro, and Cline even when some of those harnesses are absent. Reinstalling with `--yes` or `-Yes` replaces the entire installed `pollyanna` skill directory for each target. Local edits inside an installed skill directory will be lost. The installer stages the new copy first and restores the previous copy if activation fails.

macOS, Linux, Git Bash, or WSL:

```bash
curl -fsSL https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.sh | bash -s -- --yes
```

Windows PowerShell:

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.ps1))) -Yes
```

These commands download the repository archive, render the portable skill, install the default broad harness set, and create `~/pollyanna/docs/memory.md` if it does not already exist. An existing memory file is never overwritten.

## Install one or more explicit harnesses

Use an explicit target when you do not want the broad installation. Bash accepts multiple target flags in one command; PowerShell accepts multiple switches.

### Codex

```bash
curl -fsSL https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.sh | bash -s -- --codex --yes
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.ps1))) -Codex -Yes
```

### Claude Code

```bash
curl -fsSL https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.sh | bash -s -- --claude --yes
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.ps1))) -Claude -Yes
```

### Cursor

```bash
curl -fsSL https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.sh | bash -s -- --cursor --yes
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.ps1))) -Cursor -Yes
```

### Kiro

```bash
curl -fsSL https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.sh | bash -s -- --kiro --yes
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.ps1))) -Kiro -Yes
```

### Cline

```bash
curl -fsSL https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.sh | bash -s -- --cline --yes
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.ps1))) -Cline -Yes
```

### GitHub Copilot native path

```bash
curl -fsSL https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.sh | bash -s -- --copilot --yes
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.ps1))) -Copilot -Yes
```

### Windsurf native path

```bash
curl -fsSL https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.sh | bash -s -- --windsurf --yes
```

```powershell
& ([scriptblock]::Create((irm https://raw.githubusercontent.com/tbladh/pollyanna-skill/main/install.ps1))) -Windsurf -Yes
```

For example, install both Codex and Claude Code with `--codex --claude --yes` in Bash or `-Codex -Claude -Yes` in PowerShell.

## Install from a clone

macOS, Linux, Git Bash, or WSL:

```bash
git clone https://github.com/tbladh/pollyanna-skill.git
cd pollyanna-skill
bash install.sh --yes
```

Windows PowerShell:

```powershell
git clone https://github.com/tbladh/pollyanna-skill.git
Set-Location pollyanna-skill
.\install.ps1 -Yes
```

Replace the broad flag with a specific target when desired, for example `bash install.sh --codex --yes` or `.\install.ps1 -Codex -Yes`.

## Installer options

| Bash | PowerShell | Meaning |
| --- | --- | --- |
| `--all` | No target switches | Install the default broad harness set |
| `--codex` | `-Codex` | Install the Codex-compatible path |
| `--claude` | `-Claude` | Install Claude Code |
| `--cursor` | `-Cursor` | Install Cursor |
| `--kiro` | `-Kiro` | Install Kiro |
| `--cline` | `-Cline` | Install Cline |
| `--copilot` | `-Copilot` | Install the GitHub Copilot native path |
| `--windsurf` | `-Windsurf` | Install the Windsurf native path |
| `--legacy-codex` | `-LegacyCodex` | Also install the legacy Codex path |
| `--no-legacy-codex` | Omit `-LegacyCodex` | Keep legacy Codex disabled; this is the default |
| `--yes` | `-Yes` | Replace existing installs without prompting |
| `--help` | `Get-Help .\install.ps1` | Show installer usage |

Without the replacement flag, an interactive installer asks before replacing each existing target. A piped or otherwise noninteractive Bash installer skips existing targets unless `--yes` is supplied.

### Custom installation home

For isolated testing or a nonstandard user home:

```bash
POLLYANNA_INSTALL_HOME=/path/to/home bash install.sh --codex --yes
```

```powershell
.\install.ps1 -Codex -Yes -InstallHome 'C:\path\to\home'
```

`POLLYANNA_REPO_ARCHIVE_URL` overrides the repository archive used by a raw-script bootstrap. This is useful for forks and non-default branches. The Bash URL must refer to a tar.gz archive; the PowerShell URL must refer to a zip archive.

## Verify the installation

For the default Codex-compatible path:

```bash
test -f "$HOME/.agents/skills/pollyanna/SKILL.md" && echo "Pollyanna installed"
test -f "$HOME/pollyanna/docs/memory.md" && echo "Pollyanna memory ready"
```

```powershell
Test-Path "$HOME/.agents/skills/pollyanna/SKILL.md"
Test-Path "$HOME/pollyanna/docs/memory.md"
```

Use the path table above when you installed a different explicit target. If a running harness does not discover the new skill immediately, start a new session or reload the harness. Then invoke Pollyanna explicitly using the skill picker or the invocation syntax supported by that harness, such as `/pollyanna` or `$pollyanna`.

## Update or repair an installation

Run the same installation command again with `--yes` or `-Yes`. Replacement is copy-based rather than incremental, so files removed by a newer release do not linger. Existing `~/pollyanna/docs/memory.md` and dated research entries remain untouched.

## Maintainer validation

Install [`uv`](https://docs.astral.sh/uv/) and run the repository-owned validation command:

```bash
uv run scripts/validate.py
```

The script declares its own Python dependencies, renders and validates the skill in a temporary directory, checks the Bash and available PowerShell paths, exercises isolated global and resident installations, and proves that installing Pollyanna into this originating repository is a no-op.

## Repository overlay

Global skill installation does not modify the current repository. When explicitly invoked inside a repository, Pollyanna inspects the governing agent workflow and offers a separate, consent-gated repository installation or upgrade. If accepted, it:

- Creates root-level `POLLYANNA.md` containing the resident behavioral core and a preserved host-guidance area.
- Adds a small managed link near the top of the selected workflow instructions.
- Adds `/.pollyanna/` to the host's `.gitignore` for optional local scratch notes and runtime artifacts.
- Preserves downstream workflow procedures and local guidance outside managed sections.
- Transfers no scripts, references, manifest, or memory file into the host.
- Leaves all changes uncommitted and never pushes without separate permission.

The resulting host does not depend on the global skill. Its committed personality lives in `POLLYANNA.md`; `.pollyanna/` is disposable and local to each clone. Installation can be reviewed and reverted with the repository's normal Git and IDE tools.

## Portable research notebook and memory

The explicitly invoked global skill keeps durable research notes under:

```text
~/pollyanna/docs/YYYY-MM-DD/{nn}-{slug}
```

Bulky public-source material goes under the matching path only when needed:

```text
~/pollyanna/data/YYYY-MM-DD/{nn}-{slug}
```

The installer creates `~/pollyanna/docs/memory.md` as a starter file and never overwrites it. Pollyanna reads it on invocation and may refine concise collaboration preferences independently. Research and memory must not contain secrets, credentials, access tokens, sensitive personal information, or private source content.

## Troubleshooting

- **Python was not found:** install Python 3 and ensure `python3`, `python`, or `py` is on `PATH`.
- **The Bash bootstrap cannot download or extract:** ensure `curl` and `tar` are available, or clone the repository and run the local installer.
- **An existing install was skipped:** rerun with `--yes` or `-Yes`, or run interactively and approve replacement.
- **The skill is not visible:** verify the expected `SKILL.md` path, then start a new session or reload the harness.
- **A global directory is not writable:** use an account that owns the harness configuration or choose an alternate installation home.
- **A repository already has `POLLYANNA.md`:** Pollyanna detects it and asks before adopting or upgrading it; it does not overwrite an unmanaged file silently.

## Changelog

Major user-facing changes are recorded in [CHANGELOG.md](CHANGELOG.md).

## License

[MIT](LICENSE)
