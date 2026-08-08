#!/usr/bin/env python3
"""Report the prompt size of the rendered skill and resident repository policy."""
from __future__ import annotations

import argparse
import json
import math
import re
import subprocess
import sys
import tempfile
from pathlib import Path


CHARACTERS_PER_TOKEN = 4


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
    parser.add_argument("--json", action="store_true", help="Write the report as JSON.")
    args = parser.parse_args()

    result = report(args.repo_root.resolve())
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print("Estimated tokens use ceil(characters / 4); actual tokenizer counts vary.")
        print()
        for label, metrics in (
            ("Installed skill (rendered SKILL.md)", result["installed_skill"]),
            ("Repo merged Pollyanna (POLLYANNA.md)", result["repo_merged_pollyanna"]),
        ):
            print(label)
            print(f"  Characters: {metrics['characters']:,}")
            print(f"  Words: {metrics['words']:,}")
            print(f"  Estimated tokens: {metrics['estimated_tokens']:,}")
    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except RuntimeError as error:
        print(f"Token cost calculation failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
