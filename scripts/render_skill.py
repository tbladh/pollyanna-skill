#!/usr/bin/env python3
from __future__ import annotations

import argparse
import os
import re
import shutil
from pathlib import Path


SHARED_START = "<!-- pollyanna:shared:start -->"
SHARED_END = "<!-- pollyanna:shared:end -->"
MANAGED_RE = re.compile(
    r"<!-- pollyanna:managed:start version=(?P<version>[^ ]+) -->.*?"
    r"<!-- pollyanna:managed:end -->",
    re.DOTALL,
)


def load_env_file(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, sep, value = line.partition("=")
        if not sep:
            raise ValueError(f"Invalid config line: {raw_line}")
        values[key.strip()] = value.strip()
    return values


def apply_env_overrides(values: dict[str, str]) -> dict[str, str]:
    merged = dict(values)
    for key in list(merged):
        if key in os.environ and os.environ[key]:
            merged[key] = os.environ[key]
    return merged


def render_text(text: str, replacements: dict[str, str]) -> str:
    rendered = text
    for key, value in replacements.items():
        rendered = rendered.replace(key, value)
    return rendered


def extract_between(text: str, start_marker: str, end_marker: str, source_name: str) -> str:
    start = text.find(start_marker)
    end = text.find(end_marker)
    if start < 0 or end <= start:
        raise ValueError(f"{source_name} does not contain a valid {start_marker} block.")
    return text[start + len(start_marker) : end].strip()


def main() -> int:
    parser = argparse.ArgumentParser(description="Render the Pollyanna skill template.")
    parser.add_argument("--repo-root", required=True, help="Repository root path")
    parser.add_argument("--output-dir", required=True, help="Directory to write the rendered skill into")
    args = parser.parse_args()

    repo_root = Path(args.repo_root).resolve()
    output_dir = Path(args.output_dir).resolve()
    config = apply_env_overrides(load_env_file(repo_root / "config" / "defaults.env"))
    template_root = repo_root / "template" / "skill"
    rendered_root = output_dir / config["PRODUCT_NAME"]
    host_policy_text = (repo_root / "POLLYANNA.md").read_text(encoding="utf-8")
    managed_match = MANAGED_RE.search(host_policy_text)
    if not managed_match:
        raise ValueError("POLLYANNA.md does not contain a valid managed resident policy.")
    if managed_match.group("version") != config["PRODUCT_VERSION"]:
        raise ValueError(
            "POLLYANNA.md managed version does not match PRODUCT_VERSION in config/defaults.env."
        )
    shared_core = extract_between(host_policy_text, SHARED_START, SHARED_END, "POLLYANNA.md")

    replacements = {
        "__PRODUCT_NAME__": config["PRODUCT_NAME"],
        "__PRODUCT_TITLE__": config["PRODUCT_TITLE"],
        "__PRODUCT_VERSION__": config["PRODUCT_VERSION"],
        "__HOME_ROOT_NAME__": config["HOME_ROOT_NAME"],
        "__DOCS_SUBDIR__": config["DOCS_SUBDIR"],
        "__DATA_SUBDIR__": config["DATA_SUBDIR"],
        "__MEMORY_FILE_NAME__": config["MEMORY_FILE_NAME"],
        "__POLLYANNA_SHARED_CORE__": shared_core,
    }

    shutil.copytree(template_root, rendered_root, dirs_exist_ok=True)
    assets_root = rendered_root / "assets"
    assets_root.mkdir(parents=True, exist_ok=True)
    (assets_root / "POLLYANNA.md").write_text(
        f"# Pollyanna\n\n{managed_match.group(0)}\n",
        encoding="utf-8",
    )

    for path in rendered_root.rglob("*"):
        if not path.is_file():
            continue
        source_mode = path.stat().st_mode
        text = path.read_text(encoding="utf-8")
        rendered_text = render_text(text, replacements)
        unresolved = (
            "__PRODUCT_",
            "__HOME_ROOT_NAME__",
            "__DOCS_SUBDIR__",
            "__DATA_SUBDIR__",
            "__MEMORY_FILE_NAME__",
            "__POLLYANNA_",
        )
        if any(token in rendered_text for token in unresolved):
            raise ValueError(f"Unresolved placeholder found in {path}")
        path.write_text(rendered_text, encoding="utf-8")
        os.chmod(path, source_mode)

    print(rendered_root)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
