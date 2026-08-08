#!/usr/bin/env python3
"""Report the prompt size of the rendered skill and resident repository policy."""
from __future__ import annotations

import argparse
import io
import json
import math
import re
import subprocess
import sys
import tarfile
import tempfile
from pathlib import Path


CHARACTERS_PER_TOKEN = 4
SIGNIFICANT_TOKEN_GROWTH = 250
SIGNIFICANT_TOKEN_GROWTH_PERCENT = 10
SUBJECTS = ("installed_skill", "repo_merged_pollyanna")


def measure(text: str) -> dict[str, int]:
    """Return stable, tokenizer-independent prompt-size estimates for text."""
    characters = len(text)
    return {
        "characters": characters,
        "words": len(re.findall(r"\S+", text)),
        "estimated_tokens": math.ceil(characters / CHARACTERS_PER_TOKEN),
    }


def render_skill(repo_root: Path, output_dir: Path) -> Path:
    result = subprocess.run(
        [
            sys.executable,
            str(repo_root / "scripts" / "render_skill.py"),
            "--repo-root",
            str(repo_root),
            "--output-dir",
            str(output_dir),
        ],
        cwd=repo_root,
        text=True,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        details = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
        message = "Could not render the installed skill."
        if details:
            message = f"{message}\n{details}"
        raise RuntimeError(message)

    skill_root = Path(result.stdout.strip()).resolve()
    skill_md = skill_root / "SKILL.md"
    if not skill_md.is_file():
        raise RuntimeError("Renderer did not create SKILL.md.")
    return skill_md


def report(repo_root: Path) -> dict[str, dict[str, int]]:
    policy_path = repo_root / "POLLYANNA.md"
    if not policy_path.is_file():
        raise RuntimeError(f"Repository policy was not found: {policy_path}")

    with tempfile.TemporaryDirectory(prefix="pollyanna-token-cost-") as temporary:
        skill_path = render_skill(repo_root, Path(temporary) / "rendered")
        installed_skill = measure(skill_path.read_text(encoding="utf-8"))

    return {
        "installed_skill": installed_skill,
        "repo_merged_pollyanna": measure(policy_path.read_text(encoding="utf-8")),
    }


def archived_repository(repo_root: Path, ref: str, destination: Path) -> Path:
    result = subprocess.run(
        ["git", "archive", "--format=tar", ref],
        cwd=repo_root,
        capture_output=True,
        check=False,
    )
    if result.returncode != 0:
        details = result.stderr.decode("utf-8", errors="replace").strip()
        message = f"Could not read Git ref {ref!r}."
        if details:
            message = f"{message}\n{details}"
        raise RuntimeError(message)

    with tarfile.open(fileobj=io.BytesIO(result.stdout)) as archive:
        root = destination.resolve()
        for member in archive.getmembers():
            target = (root / member.name).resolve()
            if target != root and root not in target.parents:
                raise RuntimeError(f"Git ref {ref!r} contains an unsafe archive path: {member.name}")
        archive.extractall(root)
    return destination


def compare(current: dict[str, dict[str, int]], baseline: dict[str, dict[str, int]]) -> tuple[dict[str, dict[str, int | float]], list[str]]:
    changes: dict[str, dict[str, int | float]] = {}
    warnings: list[str] = []
    for subject in SUBJECTS:
        current_tokens = current[subject]["estimated_tokens"]
        baseline_tokens = baseline[subject]["estimated_tokens"]
        token_delta = current_tokens - baseline_tokens
        token_percent = (token_delta / baseline_tokens * 100) if baseline_tokens else 0.0
        changes[subject] = {
            "estimated_token_delta": token_delta,
            "estimated_token_percent": round(token_percent, 1),
        }
        if token_delta >= SIGNIFICANT_TOKEN_GROWTH or token_percent >= SIGNIFICANT_TOKEN_GROWTH_PERCENT:
            warnings.append(
                f"{subject} grew by {token_delta:,} estimated tokens ({token_percent:.1f}%) "
                f"since the comparison ref."
            )
    return changes, warnings


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Measure Pollyanna's rendered skill prompt and merged resident repository policy."
    )
    parser.add_argument(
        "--repo-root",
        type=Path,
        default=Path(__file__).resolve().parent.parent,
        help="Repository root to measure (default: this repository).",
    )
    parser.add_argument(
        "--compare-ref",
        help="Git ref to use as the prompt-size baseline; emits warnings for significant growth.",
    )
    parser.add_argument("--json", action="store_true", help="Write the report as JSON.")
    args = parser.parse_args()

    repo_root = args.repo_root.resolve()
    current = report(repo_root)
    baseline: dict[str, dict[str, int]] | None = None
    changes: dict[str, dict[str, int | float]] | None = None
    warnings: list[str] = []
    if args.compare_ref:
        with tempfile.TemporaryDirectory(prefix="pollyanna-token-baseline-") as temporary:
            baseline = report(archived_repository(repo_root, args.compare_ref, Path(temporary)))
        changes, warnings = compare(current, baseline)

    if args.json:
        output: dict[str, object] = {"current": current, "warnings": warnings}
        if baseline is not None and changes is not None:
            output["comparison_ref"] = args.compare_ref
            output["baseline"] = baseline
            output["changes"] = changes
        print(json.dumps(output, indent=2, sort_keys=True))
    else:
        print("Estimated tokens use ceil(characters / 4); actual tokenizer counts vary.")
        print()
        for label, metrics in (
            ("Installed skill (rendered SKILL.md)", current["installed_skill"]),
            ("Repo merged Pollyanna (POLLYANNA.md)", current["repo_merged_pollyanna"]),
        ):
            print(label)
            print(f"  Characters: {metrics['characters']:,}")
            print(f"  Words: {metrics['words']:,}")
            print(f"  Estimated tokens: {metrics['estimated_tokens']:,}")
        if baseline is not None and changes is not None:
            print()
            print(f"Compared with {args.compare_ref}")
            for subject, metrics in changes.items():
                print(
                    f"  {subject}: {metrics['estimated_token_delta']:+,} estimated tokens "
                    f"({metrics['estimated_token_percent']:+.1f}%)"
                )
        for warning in warnings:
            print(f"WARNING: {warning}", file=sys.stderr)
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"Token cost calculation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
