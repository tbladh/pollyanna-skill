#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
from pathlib import Path


VERSION = "__PRODUCT_VERSION__"
MANAGED_END = "<!-- pollyanna:managed:end -->"
HOOK_END = "<!-- pollyanna:hook:end -->"
IGNORE_RULE = "/.pollyanna/"
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
SCAN_EXCLUDED_DIRS = {
    ".git",
    ".pollyanna",
    ".venv",
    "build",
    "dist",
    "node_modules",
    "vendor",
}
MAX_INSTRUCTION_BYTES = 2 * 1024 * 1024


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


def policy_source_path() -> Path:
    rendered_asset = skill_root() / "assets" / "POLLYANNA.md"
    if rendered_asset.is_file():
        return rendered_asset
    source_repo_policy = skill_root().parent.parent / "POLLYANNA.md"
    if source_repo_policy.is_file():
        return source_repo_policy
    raise ValueError("Could not find the resident POLLYANNA.md policy source.")


def desired_managed_block() -> tuple[str, re.Match[str]]:
    text = policy_source_path().read_text(encoding="utf-8")
    match = MANAGED_RE.search(text)
    if not match:
        raise ValueError("Resident policy source does not contain a valid managed block.")
    if match.group("version") != VERSION:
        raise ValueError("Resident policy version does not match the rendered skill version.")
    return match.group(0), match


def digest(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def version_tuple(value: str | None) -> tuple[int, ...]:
    if not value:
        return ()
    return tuple(int(part) for part in re.findall(r"\d+", value))


def workflow_candidates(repo: Path) -> list[str]:
    return [name for name in WORKFLOW_CANDIDATES if (repo / name).is_file()]


def discover_hook_files(repo: Path) -> list[str]:
    discovered: set[str] = set()
    for directory, directory_names, file_names in os.walk(repo):
        directory_names[:] = [
            name for name in directory_names if name not in SCAN_EXCLUDED_DIRS
        ]
        directory_path = Path(directory)
        for file_name in file_names:
            candidate = directory_path / file_name
            try:
                if candidate.is_symlink() or candidate.stat().st_size > MAX_INSTRUCTION_BYTES:
                    continue
                text = candidate.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            if HOOK_RE.search(text):
                discovered.add(candidate.relative_to(repo).as_posix())
    return sorted(discovered)


def ignore_rule_present(text: str | None) -> bool:
    if text is None:
        return False
    accepted = {".pollyanna", ".pollyanna/", "/.pollyanna", "/.pollyanna/"}
    return any(line.strip() in accepted for line in text.splitlines())


def status(repo: Path) -> dict[str, object]:
    desired_block, desired_match = desired_managed_block()
    policy_path = repo / "POLLYANNA.md"
    policy_text = policy_path.read_text(encoding="utf-8") if policy_path.is_file() else None
    installed_match = MANAGED_RE.search(policy_text) if policy_text is not None else None
    current_version = installed_match.group("version") if installed_match else None
    installed_body = installed_match.group("body") if installed_match else None
    hooks = discover_hook_files(repo)
    gitignore_path = repo / ".gitignore"
    gitignore_text = gitignore_path.read_text(encoding="utf-8") if gitignore_path.is_file() else None
    candidates = workflow_candidates(repo)
    return {
        "repo_root": str(repo),
        "available_version": VERSION,
        "available_core_sha256": digest(desired_match.group("body")),
        "installed": installed_match is not None,
        "installed_version": current_version,
        "installed_core_sha256": digest(installed_body) if installed_body is not None else None,
        "policy_aligned": bool(installed_match and installed_match.group(0) == desired_block),
        "upgrade_available": bool(
            current_version and version_tuple(VERSION) > version_tuple(current_version)
        ),
        "content_update_available": bool(
            installed_match and installed_match.group(0) != desired_block
        ),
        "unmanaged_policy": bool(policy_text is not None and installed_match is None),
        "gitignore_aligned": ignore_rule_present(gitignore_text),
        "workflow_candidates": candidates,
        "workflow_hooks": hooks,
        "suggested_workflow_files": hooks or candidates[:1] or ["AGENTS.md"],
    }


def render_policy(existing: str | None, adopt_existing: bool) -> str:
    managed, _match = desired_managed_block()
    if existing is None:
        return (
            "# Pollyanna\n\n"
            f"{managed}\n\n"
            "## Repository-specific guidance\n\n"
            "Add durable host refinements here. Content outside the managed block is preserved during upgrades.\n"
        )
    if MANAGED_RE.search(existing):
        rendered = MANAGED_RE.sub(lambda _existing: managed, existing, count=1)
        return rendered if rendered.endswith("\n") else rendered + "\n"
    if not adopt_existing:
        raise ValueError(
            "An unmanaged POLLYANNA.md already exists. Inspect it and rerun with --adopt-existing only after the user approves adoption."
        )
    return (
        "# Pollyanna\n\n"
        f"{managed}\n\n"
        "## Preserved local guidance\n\n"
        f"{existing.strip()}\n"
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
    return "\n".join(lines[:index] + ["", hook, ""] + lines[index:]).rstrip() + "\n"


def render_workflow(existing: str | None, workflow_path: Path, repo: Path) -> str:
    hook = hook_block(workflow_path, repo)
    if existing is None:
        return f"# Repository instructions\n\n{hook}\n"
    if HOOK_RE.search(existing):
        rendered = HOOK_RE.sub(lambda _existing: hook, existing, count=1)
        return rendered if rendered.endswith("\n") else rendered + "\n"
    return insert_near_top(existing, hook)


def render_gitignore(existing: str | None) -> str:
    if ignore_rule_present(existing):
        return existing or ""
    base = (existing or "").rstrip("\n")
    return f"{base}\n{IGNORE_RULE}\n" if base else f"{IGNORE_RULE}\n"


def write_atomic(path: Path, content: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.pollyanna-new-{os.getpid()}")
    temporary.write_text(content, encoding="utf-8")
    if path.exists():
        os.chmod(temporary, path.stat().st_mode)
    os.replace(temporary, path)


def restore_file(path: Path, previous: bytes | None, mode: int | None) -> None:
    if previous is None:
        if path.exists():
            path.unlink()
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(previous)
    if mode is not None:
        os.chmod(path, mode)


def install(repo: Path, workflow_values: list[str], adopt_existing: bool) -> dict[str, object]:
    existing_hooks = discover_hook_files(repo)
    if workflow_values:
        selected = [*existing_hooks, *workflow_values]
    else:
        selected = existing_hooks or workflow_candidates(repo)[:1] or ["AGENTS.md"]
    selected = list(dict.fromkeys(selected))
    workflow_paths = [resolve_inside(repo, value) for value in selected]

    policy_path = repo / "POLLYANNA.md"
    policy_existing = policy_path.read_text(encoding="utf-8") if policy_path.is_file() else None
    rendered: dict[Path, str] = {
        policy_path: render_policy(policy_existing, adopt_existing),
    }
    for workflow_path in workflow_paths:
        existing = workflow_path.read_text(encoding="utf-8") if workflow_path.is_file() else None
        rendered[workflow_path] = render_workflow(existing, workflow_path, repo)
    gitignore_path = repo / ".gitignore"
    gitignore_existing = gitignore_path.read_text(encoding="utf-8") if gitignore_path.is_file() else None
    rendered[gitignore_path] = render_gitignore(gitignore_existing)

    changed_paths = [
        path
        for path, content in rendered.items()
        if not path.is_file() or path.read_text(encoding="utf-8") != content
    ]
    previous = {
        path: (
            path.read_bytes() if path.is_file() else None,
            path.stat().st_mode if path.is_file() else None,
        )
        for path in changed_paths
    }
    try:
        for path in changed_paths:
            write_atomic(path, rendered[path])
    except Exception:
        for path, (content, mode) in previous.items():
            restore_file(path, content, mode)
        raise

    return {
        "repo_root": str(repo),
        "version": VERSION,
        "policy_file": str(policy_path),
        "gitignore_file": str(gitignore_path),
        "workflow_files": [str(path) for path in workflow_paths],
        "changed_files": [str(path) for path in changed_paths],
        "no_op": not changed_paths,
    }


def emit(value: object, as_json: bool) -> None:
    if as_json:
        print(json.dumps(value, indent=2, sort_keys=True))
    elif isinstance(value, dict):
        for key, item in value.items():
            print(f"{key}={item}")
    else:
        print(value)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Inspect, install, or upgrade Pollyanna in a host repository.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    status_parser = subparsers.add_parser("status", help="Inspect a repository for resident Pollyanna integration.")
    status_parser.add_argument("--repo-root", required=True)
    status_parser.add_argument("--json", action="store_true")

    install_parser = subparsers.add_parser("install", help="Install or upgrade resident Pollyanna after user approval.")
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
    result = status(repo) if args.command == "status" else install(
        repo, args.workflow_file, args.adopt_existing
    )
    emit(result, args.json)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
