#!/usr/bin/env -S uv run --script
# /// script
# requires-python = ">=3.10"
# dependencies = [
#   "pyyaml>=6.0.2,<7",
# ]
# ///
from __future__ import annotations

import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

import yaml


MAX_SKILL_NAME_LENGTH = 64
ALLOWED_FRONTMATTER_KEYS = {
    "allowed-tools",
    "description",
    "license",
    "metadata",
    "name",
}


class ValidationError(RuntimeError):
    pass


def require(condition: bool, message: str) -> None:
    if not condition:
        raise ValidationError(message)


def run_checked(
    command: list[str],
    *,
    cwd: Path,
    env: dict[str, str] | None = None,
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        command,
        cwd=cwd,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        details = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        suffix = f"\n{details}" if details else ""
        raise ValidationError(f"Command failed: {' '.join(command)}{suffix}")
    return result


def load_frontmatter(skill_md: Path) -> dict[str, object]:
    content = skill_md.read_text(encoding="utf-8")
    match = re.match(r"^---\n(.*?)\n---", content, re.DOTALL)
    require(match is not None, "SKILL.md must begin with valid YAML frontmatter.")
    value = yaml.safe_load(match.group(1))
    require(isinstance(value, dict), "SKILL.md frontmatter must be a mapping.")
    return value


def validate_skill_metadata(skill_root: Path) -> None:
    skill_md = skill_root / "SKILL.md"
    require(skill_md.is_file(), "Rendered SKILL.md was not created.")
    frontmatter = load_frontmatter(skill_md)
    unexpected = set(frontmatter) - ALLOWED_FRONTMATTER_KEYS
    require(not unexpected, f"Unexpected SKILL.md frontmatter keys: {sorted(unexpected)}")

    name = frontmatter.get("name")
    description = frontmatter.get("description")
    require(isinstance(name, str) and bool(name.strip()), "Skill name must be a non-empty string.")
    require(
        bool(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", name)),
        "Skill name must use lowercase hyphen-case.",
    )
    require(len(name) <= MAX_SKILL_NAME_LENGTH, "Skill name exceeds 64 characters.")
    require(
        isinstance(description, str) and bool(description.strip()),
        "Skill description must be a non-empty string.",
    )
    require(len(description) <= 1024, "Skill description exceeds 1024 characters.")
    require("<" not in description and ">" not in description, "Skill description contains angle brackets.")

    agent_yaml = skill_root / "agents" / "openai.yaml"
    require(agent_yaml.is_file(), "Rendered agents/openai.yaml was not created.")
    agent_metadata = yaml.safe_load(agent_yaml.read_text(encoding="utf-8"))
    require(isinstance(agent_metadata, dict), "agents/openai.yaml must be a mapping.")
    interface = agent_metadata.get("interface")
    require(isinstance(interface, dict), "agents/openai.yaml must define interface metadata.")
    for key in ("display_name", "short_description", "default_prompt"):
        require(isinstance(interface.get(key), str) and bool(interface[key].strip()), f"Missing interface.{key}.")
    policy = agent_metadata.get("policy")
    require(
        isinstance(policy, dict) and policy.get("allow_implicit_invocation") is False,
        "Pollyanna must remain explicitly invoked.",
    )

    for path in (skill_md, agent_yaml):
        require("__PRODUCT_" not in path.read_text(encoding="utf-8"), f"Unresolved placeholder in {path}.")


def standard_validator_path() -> Path | None:
    override = os.environ.get("POLLYANNA_QUICK_VALIDATE")
    if override:
        path = Path(override).expanduser().resolve()
        require(path.is_file(), f"POLLYANNA_QUICK_VALIDATE does not name a file: {path}")
        return path

    candidates: list[Path] = []
    codex_home = os.environ.get("CODEX_HOME")
    if codex_home:
        candidates.append(Path(codex_home) / "skills/.system/skill-creator/scripts/quick_validate.py")
    candidates.append(Path.home() / ".codex/skills/.system/skill-creator/scripts/quick_validate.py")
    return next((path for path in candidates if path.is_file()), None)


def validate_python_syntax(repo_root: Path) -> None:
    paths = [
        repo_root / "scripts/bootstrap_smoke.py",
        repo_root / "scripts/render_skill.py",
        repo_root / "scripts/token_cost.py",
        repo_root / "scripts/validate.py",
    ]
    paths.extend(sorted((repo_root / "template/skill/scripts").glob("*.py")))
    for path in paths:
        compile(path.read_text(encoding="utf-8"), str(path), "exec")


def validate_shell_syntax(repo_root: Path) -> None:
    bash = shutil.which("bash")
    require(bash is not None, "Bash is required to validate the Unix installers.")
    paths = [repo_root / "install.sh"]
    for path in sorted((repo_root / "template/skill/scripts").iterdir()):
        if path.is_file() and path.suffix == "" and path.read_bytes().startswith(b"#!/usr/bin/env bash"):
            paths.append(path)
    run_checked([bash, "-n", *(str(path) for path in paths)], cwd=repo_root)


def validate_powershell_syntax(repo_root: Path) -> bool:
    pwsh = shutil.which("pwsh")
    if pwsh is None:
        return False
    parser = (
        "$tokens = $null; $errors = $null; "
        "[System.Management.Automation.Language.Parser]::ParseFile($env:POLLYANNA_VALIDATE_PATH, [ref]$tokens, [ref]$errors) | Out-Null; "
        "if ($errors.Count) { $errors | ForEach-Object { Write-Error $_ }; exit 1 }"
    )
    paths = [repo_root / "install.ps1"]
    paths.extend(sorted((repo_root / "template/skill/scripts").glob("*.ps1")))
    for path in paths:
        environment = dict(os.environ)
        environment["POLLYANNA_VALIDATE_PATH"] = str(path)
        run_checked([pwsh, "-NoLogo", "-NoProfile", "-Command", parser], cwd=repo_root, env=environment)
    return True


def validate_version_references(repo_root: Path) -> None:
    config_match = re.search(
        r"^PRODUCT_VERSION=(?P<version>[^\s]+)$",
        (repo_root / "config/defaults.env").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    require(config_match is not None, "config/defaults.env must define PRODUCT_VERSION.")
    version = config_match.group("version")

    policy_match = re.search(
        r"<!-- pollyanna:managed:start version=(?P<version>[^ ]+) -->",
        (repo_root / "POLLYANNA.md").read_text(encoding="utf-8"),
    )
    require(policy_match is not None, "POLLYANNA.md must define a managed version.")
    require(policy_match.group("version") == version, "Managed policy version does not match PRODUCT_VERSION.")

    changelog_match = re.search(
        r"^## (?P<version>[^\s]+) - ",
        (repo_root / "CHANGELOG.md").read_text(encoding="utf-8"),
        re.MULTILINE,
    )
    require(changelog_match is not None, "CHANGELOG.md must begin with a versioned release entry.")
    require(changelog_match.group("version") == version, "Latest changelog version does not match PRODUCT_VERSION.")

    readme = (repo_root / "README.md").read_text(encoding="utf-8")
    require(not re.search(r"^# Pollyanna v", readme, re.MULTILINE), "README.md must not carry a release version.")


def load_json_result(result: subprocess.CompletedProcess[str], operation: str) -> dict[str, object]:
    try:
        value = json.loads(result.stdout)
    except json.JSONDecodeError as error:
        raise ValidationError(f"{operation} did not return valid JSON: {error}") from error
    require(isinstance(value, dict), f"{operation} must return a JSON object.")
    return value


def validate_repo_installer(repo_root: Path, skill_root: Path, temporary_root: Path) -> None:
    installer = skill_root / "scripts/install_repo.py"
    require(installer.is_file(), "Rendered repository installer was not created.")
    watched = [
        repo_root / "POLLYANNA.md",
        repo_root / ".gitignore",
        repo_root / "AGENTS.md",
        repo_root / ".github/copilot-instructions.md",
    ]
    before = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched}
    self_result = run_checked(
        [
            sys.executable,
            str(installer),
            "install",
            "--repo-root",
            str(repo_root),
            "--workflow-file",
            "AGENTS.md",
            "--json",
        ],
        cwd=repo_root,
    )
    self_install = load_json_result(self_result, "Self-installation")
    require(self_install.get("no_op") is True, "Self-installation was not a no-op.")
    require(self_install.get("changed_files") == [], "Self-installation reported changed files.")
    after = {path: (path.read_bytes(), path.stat().st_mtime_ns) for path in watched}
    require(before == after, "Self-installation wrote to an aligned originating repository.")

    host = temporary_root / "fresh-host"
    host.mkdir()
    first_result = run_checked(
        [sys.executable, str(installer), "install", "--repo-root", str(host), "--json"],
        cwd=repo_root,
    )
    first_install = load_json_result(first_result, "Fresh-host installation")
    require(first_install.get("no_op") is False, "Fresh-host installation unexpectedly reported a no-op.")
    files = {path.relative_to(host).as_posix() for path in host.rglob("*") if path.is_file()}
    require(files == {".gitignore", "AGENTS.md", "POLLYANNA.md"}, f"Unexpected host payload: {sorted(files)}")
    require(not (host / ".pollyanna").exists(), "Host installation created a .pollyanna payload.")

    repeat_result = run_checked(
        [sys.executable, str(installer), "install", "--repo-root", str(host), "--json"],
        cwd=repo_root,
    )
    repeat_install = load_json_result(repeat_result, "Repeated host installation")
    require(repeat_install.get("no_op") is True, "Repeated host installation was not a no-op.")


def validate_global_installers(repo_root: Path, temporary_root: Path, powershell_available: bool) -> None:
    default_skill_roots = (
        ".agents/skills",
        ".claude/skills",
        ".cursor/skills",
        ".kiro/skills",
        ".cline/skills",
    )

    def require_default_install(install_home: Path, platform: str) -> None:
        paths = [install_home / root / "pollyanna/SKILL.md" for root in default_skill_roots]
        paths.extend(
            (
                install_home / ".agents/skills/pollyanna/assets/POLLYANNA.md",
                install_home / "pollyanna/docs/memory.md",
            )
        )
        for path in paths:
            require(path.is_file(), f"{platform} global installer did not create {path}.")

    bash_home = temporary_root / "bash-home"
    bash_env = dict(os.environ)
    bash_env["POLLYANNA_INSTALL_HOME"] = str(bash_home)
    run_checked(
        ["bash", str(repo_root / "install.sh"), "--yes"],
        cwd=repo_root,
        env=bash_env,
    )
    require_default_install(bash_home, "Bash")

    if powershell_available:
        powershell_home = temporary_root / "powershell-home"
        run_checked(
            [
                "pwsh",
                "-NoLogo",
                "-NoProfile",
                "-File",
                str(repo_root / "install.ps1"),
                "-Yes",
                "-InstallHome",
                str(powershell_home),
            ],
            cwd=repo_root,
        )
        require_default_install(powershell_home, "PowerShell")


def validate_executable_modes(repo_root: Path, skill_root: Path) -> None:
    paths = [
        repo_root / "install.sh",
        repo_root / "scripts/render_skill.py",
        repo_root / "scripts/token_cost.py",
        repo_root / "scripts/validate.py",
    ]
    paths.extend(
        path
        for path in (skill_root / "scripts").iterdir()
        if path.is_file() and path.suffix in {"", ".py"}
    )
    for path in paths:
        require(os.access(path, os.X_OK), f"Expected executable file mode on {path}.")


def validate_token_cost_calculator(repo_root: Path) -> None:
    git = shutil.which("git")
    comparison_ref: str | None = None
    if git is not None:
        for candidate in ("main", "origin/main"):
            ref_check = subprocess.run(
                [git, "rev-parse", "--verify", "--quiet", candidate],
                cwd=repo_root,
                capture_output=True,
                check=False,
            )
            if ref_check.returncode == 0:
                comparison_ref = candidate
                break
    command = [sys.executable, str(repo_root / "scripts/token_cost.py"), "--repo-root", str(repo_root), "--json"]
    if comparison_ref is not None:
        command.extend(("--compare-ref", comparison_ref))
    result = run_checked(
        command,
        cwd=repo_root,
    )
    output = load_json_result(result, "Token cost calculation")
    report = output.get("current")
    require(isinstance(report, dict), "Token cost report is missing current metrics.")
    for subject in ("installed_skill", "repo_merged_pollyanna"):
        metrics = report.get(subject)
        require(isinstance(metrics, dict), f"Token cost report is missing {subject}.")
        for metric in ("characters", "words", "estimated_tokens"):
            value = metrics.get(metric)
            require(isinstance(value, int) and value > 0, f"Invalid {subject}.{metric} in token cost report.")
    if comparison_ref is not None:
        require(output.get("comparison_ref") == comparison_ref, "Token cost report used the wrong comparison ref.")
    warnings = output.get("warnings")
    require(isinstance(warnings, list), "Token cost report is missing growth warnings.")
    for warning in warnings:
        require(isinstance(warning, str), "Token cost report contains an invalid growth warning.")
        print(f"Token cost warning: {warning}")


def main() -> int:
    repo_root = Path(__file__).resolve().parent.parent
    checks = ["metadata", "Python syntax", "Bash syntax"]
    validate_version_references(repo_root)
    checks.append("version references")
    validate_python_syntax(repo_root)
    validate_shell_syntax(repo_root)
    powershell_available = validate_powershell_syntax(repo_root)
    if powershell_available:
        checks.append("PowerShell syntax")

    with tempfile.TemporaryDirectory(prefix="pollyanna-validation-") as temporary:
        temporary_root = Path(temporary)
        render_result = run_checked(
            [
                sys.executable,
                str(repo_root / "scripts/render_skill.py"),
                "--repo-root",
                str(repo_root),
                "--output-dir",
                str(temporary_root / "rendered"),
            ],
            cwd=repo_root,
        )
        skill_root = Path(render_result.stdout.strip()).resolve()
        require(skill_root.is_dir(), "Renderer did not return a valid skill directory.")
        validate_skill_metadata(skill_root)

        standard_validator = standard_validator_path()
        if standard_validator is not None:
            run_checked([sys.executable, str(standard_validator), str(skill_root)], cwd=repo_root)
            checks.append("standard skill validator")

        validate_executable_modes(repo_root, skill_root)
        validate_token_cost_calculator(repo_root)
        validate_repo_installer(repo_root, skill_root, temporary_root)
        validate_global_installers(repo_root, temporary_root, powershell_available)
        run_checked(
            [sys.executable, str(repo_root / "scripts/bootstrap_smoke.py"), "bash", "--repo-root", str(repo_root)],
            cwd=repo_root,
        )
        checks.extend(
            [
                "rendered artifact",
                "token cost calculator",
                "repository installer",
                "global installers",
                "Bash bootstrap",
                "ouroboros no-op",
            ]
        )

    git = shutil.which("git")
    if git is not None:
        run_checked([git, "diff", "--check"], cwd=repo_root)
        checks.append("Git whitespace")

    print("Pollyanna validation passed:")
    for check in checks:
        print(f"- {check}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValidationError as error:
        print(f"Pollyanna validation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
