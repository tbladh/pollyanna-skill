#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import os
import re
import shutil
from pathlib import Path


VERSION = "__PRODUCT_VERSION__"
CORE_START = "<!-- pollyanna:core:start -->"
CORE_END = "<!-- pollyanna:core:end -->"
MANAGED_END = "<!-- pollyanna:managed:end -->"
HOOK_END = "<!-- pollyanna:hook:end -->"
MANAGED_RE = re.compile(
    r"<!-- pollyanna:managed:start version=(?P<version>[^ ]+) -->(?P<body>.*?)"
    r"<!-- pollyanna:managed:end -->",
    re.DOTALL,
)
HOOK_RE = re.compile(
    r"<!-- pollyanna:hook:start version=(?P<version>[^ ]+) -->.*?"
    r"<!-- pollyanna:hook:end -->",
    re.DOTALL,
)
WORKFLOW_CANDIDATES = (
    "AGENTS.md",
    "CLAUDE.md",
    ".github/copilot-instructions.md",
    ".cursorrules",
)


def skill_root() -> Path:
    return Path(__file__).resolve().parent.parent


def resolve_repo(value: str) -> Path:
    repo = Path(value).resolve()
    if not repo.is_dir():
        raise ValueError(f"Repository root is not a directory: {repo}")
    return repo


def resolve_inside(repo: Path, value: str) -> Path:
    candidate = (repo / value).resolve()
    try:
        candidate.relative_to(repo)
    except ValueError as error:
        raise ValueError(f"Workflow file must be inside the repository: {value}") from error
    return candidate


def read_manifest(repo: Path) -> dict[str, object] | None:
    manifest_path = repo / ".pollyanna" / "manifest.json"
    if not manifest_path.is_file():
        return None
    try:
        value = json.loads(manifest_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return None
    return value if isinstance(value, dict) else None


def installed_version(repo: Path) -> str | None:
    manifest = read_manifest(repo)
    if manifest and isinstance(manifest.get("version"), str):
        return str(manifest["version"])
    policy_path = repo / "POLLYANNA.md"
    if policy_path.is_file():
        match = MANAGED_RE.search(policy_path.read_text(encoding="utf-8"))
        if match:
            return match.group("version")
    return None


def version_tuple(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    parts = re.findall(r"\d+", value)
    return tuple(int(part) for part in parts)


def workflow_candidates(repo: Path) -> list[str]:
    return [name for name in WORKFLOW_CANDIDATES if (repo / name).is_file()]


def status(repo: Path) -> dict[str, object]:
    policy_path = repo / "POLLYANNA.md"
    current = installed_version(repo)
    unmanaged_policy = policy_path.is_file() and not MANAGED_RE.search(
        policy_path.read_text(encoding="utf-8")
    )
    candidates = workflow_candidates(repo)
    return {
        "repo_root": str(repo),
        "available_version": VERSION,
        "installed": policy_path.is_file() or (repo / ".pollyanna").is_dir(),
        "installed_version": current,
        "upgrade_available": bool(current and version_tuple(VERSION) > version_tuple(current)),
        "unmanaged_policy": unmanaged_policy,
        "workflow_candidates": candidates,
        "suggested_workflow_files": candidates[:1] or ["AGENTS.md"],
    }


def extract_core() -> str:
    source_path = skill_root() / "SKILL.md"
    if source_path.is_file():
        text = source_path.read_text(encoding="utf-8")
        start = text.find(CORE_START)
        end = text.find(CORE_END)
        if start >= 0 and end > start:
            return text[start + len(CORE_START) : end].strip()

    installed_policy = skill_root().parent / "POLLYANNA.md"
    if installed_policy.is_file():
        match = MANAGED_RE.search(installed_policy.read_text(encoding="utf-8"))
        if match:
            return match.group("body").strip()
    raise ValueError("Could not find a valid Pollyanna behavioral core.")


def managed_policy_block() -> str:
    return (
        f"<!-- pollyanna:managed:start version={VERSION} -->\n"
        f"{extract_core()}\n"
        f"{MANAGED_END}"
    )


def render_policy(existing: str | None, adopt_existing: bool) -> str:
    managed = managed_policy_block()
    if existing is None:
        return (
            "# Pollyanna\n\n"
            f"{managed}\n\n"
            "## Repository-specific guidance\n\n"
            "Add local refinements here. Content outside the managed block is preserved during upgrades.\n"
        )
    if MANAGED_RE.search(existing):
        rendered = MANAGED_RE.sub(lambda _match: managed, existing, count=1)
        return rendered if rendered.endswith("\n") else rendered + "\n"
    if not adopt_existing:
        raise ValueError(
            "An unmanaged POLLYANNA.md already exists. Inspect it and rerun with --adopt-existing only after the user approves adoption."
        )
    preserved = existing.strip()
    return (
        "# Pollyanna\n\n"
        f"{managed}\n\n"
        "## Preserved local guidance\n\n"
        f"{preserved}\n"
    )


def hook_block(workflow_path: Path, repo: Path) -> str:
    link = os.path.relpath(repo / "POLLYANNA.md", workflow_path.parent).replace(os.sep, "/")
    return (
        f"<!-- pollyanna:hook:start version={VERSION} -->\n"
        f"> Read [{link}]({link}) before proceeding. Apply it as the governing guidance for exploration, intent discovery, option framing, and the human-AI interface while preserving this workflow's downstream purpose and procedures.\n"
        f"{HOOK_END}"
    )


def insert_near_top(text: str, hook: str) -> str:
    lines = text.splitlines()
    index = 0
    if lines and lines[0].strip() == "---":
        for candidate in range(1, len(lines)):
            if lines[candidate].strip() == "---":
                index = candidate + 1
                break
    while index < len(lines) and not lines[index].strip():
        index += 1
    if index < len(lines) and lines[index].lstrip().startswith("#"):
        index += 1
    before = lines[:index]
    after = lines[index:]
    rendered = before + ["", hook, ""] + after
    return "\n".join(rendered).rstrip() + "\n"


def render_workflow(existing: str | None, workflow_path: Path, repo: Path) -> str:
    hook = hook_block(workflow_path, repo)
    if existing is None:
        return f"# Repository instructions\n\n{hook}\n"
    if HOOK_RE.search(existing):
        rendered = HOOK_RE.sub(lambda _match: hook, existing, count=1)
        return rendered if rendered.endswith("\n") else rendered + "\n"
    if "POLLYANNA.md" in existing:
        return existing if existing.endswith("\n") else existing + "\n"
    return insert_near_top(existing, hook)


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.pollyanna-new-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    if path.exists():
        os.chmod(temporary, path.stat().st_mode)
    os.replace(temporary, path)


def stage_support(repo: Path, workflow_files: list[str]) -> tuple[Path, Path | None]:
    source = skill_root()
    destination = repo / ".pollyanna"
    stage = repo / f".pollyanna.new.{os.getpid()}"
    backup = repo / f".pollyanna.previous.{os.getpid()}"
    if destination.is_symlink() or (destination.exists() and not destination.is_dir()):
        raise ValueError(f"Repository support path must be a normal directory: {destination}")
    for stale in (stage, backup):
        if stale.exists():
            shutil.rmtree(stale)
    if destination.exists():
        shutil.copytree(destination, stage)
    else:
        stage.mkdir(parents=True)
    ignore = shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo")
    for folder_name in ("scripts", "references"):
        source_folder = source / folder_name
        if source_folder.is_dir():
            staged_folder = stage / folder_name
            if staged_folder.exists():
                shutil.rmtree(staged_folder)
            shutil.copytree(source_folder, stage / folder_name, dirs_exist_ok=True, ignore=ignore)
    manifest = {
        "name": "pollyanna",
        "version": VERSION,
        "policy_file": "POLLYANNA.md",
        "workflow_files": workflow_files,
        "managed_directories": ["scripts", "references"],
    }
    (stage / "manifest.json").write_text(
        json.dumps(manifest, indent=2, sort_keys=True) + "\n",
        encoding="utf-8",
    )
    if destination.exists():
        os.replace(destination, backup)
    try:
        os.replace(stage, destination)
    except Exception:
        if backup.exists():
            os.replace(backup, destination)
        raise
    return destination, backup if backup.exists() else None


def restore_file(path: Path, previous: bytes | None) -> None:
    if previous is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(previous)


def install(
    repo: Path,
    workflow_values: list[str],
    adopt_existing: bool,
) -> dict[str, object]:
    selected = workflow_values or workflow_candidates(repo)[:1] or ["AGENTS.md"]
    selected = list(dict.fromkeys(selected))
    workflow_paths = [resolve_inside(repo, value) for value in selected]
    policy_path = repo / "POLLYANNA.md"
    policy_existing = policy_path.read_text(encoding="utf-8") if policy_path.is_file() else None
    policy_rendered = render_policy(policy_existing, adopt_existing)

    rendered_workflows: dict[Path, str] = {}
    for workflow_path in workflow_paths:
        existing = workflow_path.read_text(encoding="utf-8") if workflow_path.is_file() else None
        rendered_workflows[workflow_path] = render_workflow(existing, workflow_path, repo)

    changed_paths = [
        path
        for path, rendered in [(policy_path, policy_rendered), *rendered_workflows.items()]
        if not path.is_file() or path.read_text(encoding="utf-8") != rendered
    ]
    previous_files = {
        path: path.read_bytes() if path.is_file() else None
        for path in [policy_path, *workflow_paths]
    }
    destination, backup = stage_support(repo, selected)
    try:
        write_atomic(policy_path, policy_rendered)
        for workflow_path, rendered in rendered_workflows.items():
            write_atomic(workflow_path, rendered)
    except Exception:
        for path, previous in previous_files.items():
            restore_file(path, previous)
        if destination.exists():
            shutil.rmtree(destination)
        if backup and backup.exists():
            os.replace(backup, destination)
        raise
    if backup and backup.exists():
        shutil.rmtree(backup)

    return {
        "repo_root": str(repo),
        "version": VERSION,
        "policy_file": str(policy_path),
        "support_dir": str(destination),
        "workflow_files": [str(path) for path in workflow_paths],
        "changed_files": [str(path) for path in changed_paths] + [str(destination)],
    }


def emit(value: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
    else:
        if isinstance(value, dict):
            for key, item in value.items():
                print(f"{key}={item}")
        else:
            print(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect, install, or upgrade Pollyanna in a repository.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Inspect a repository for Pollyanna integration.")
    status_parser.add_argument("--repo-root", required=True)
    status_parser.add_argument("--json", action="store_true")

    install_parser = subparsers.add_parser("install", help="Install or upgrade Pollyanna after user approval.")
    install_parser.add_argument("--repo-root", required=True)
    install_parser.add_argument(
        "--workflow-file",
        action="append",
        default=[],
        help="Repository-relative governing instruction file. Repeat only for independent workflows.",
    )
    install_parser.add_argument(
        "--adopt-existing",
        action="store_true",
        help="Preserve an unmanaged existing POLLYANNA.md below the new managed policy.",
    )
    install_parser.add_argument("--json", action="store_true")
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    repo = resolve_repo(args.repo_root)
    if args.command == "status":
        result = status(repo)
    else:
        result = install(repo, args.workflow_file, args.adopt_existing)
    emit(result, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
