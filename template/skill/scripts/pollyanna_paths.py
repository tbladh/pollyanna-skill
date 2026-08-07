#!/usr/bin/env python3
from __future__ import annotations

import argparse
import datetime as dt
import json
import re
from pathlib import Path


ENTRY_RE = re.compile(r"^(?P<date>\d{4}-\d{2}-\d{2})/(?P<sequence>\d+)-(?P<slug>[a-z0-9][a-z0-9-]*)$")
MEMORY_TEMPLATE = """# __PRODUCT_TITLE__ Memory

This local file stores durable collaboration preferences learned by __PRODUCT_TITLE__. Keep it concise and never store secrets, credentials, tokens, sensitive personal information, or private source content.

## Collaboration Preferences


## Useful Context


## Approaches That Work


## Overrides

"""


def slugify(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", value.strip().lower())
    slug = re.sub(r"-{2,}", "-", slug).strip("-")
    return slug or "item"


def iso_date(value: str | None) -> str:
    if value is None:
        return dt.date.today().isoformat()
    return dt.date.fromisoformat(value).isoformat()


def next_sequence(root: Path, docs_subdir: str, data_subdir: str, date_str: str) -> int:
    highest = 0
    for branch in (docs_subdir, data_subdir):
        date_dir = root / branch / date_str
        if not date_dir.exists():
            continue
        for child in date_dir.iterdir():
            if not child.is_dir():
                continue
            match = re.match(r"^(\d+)-", child.name)
            if match:
                highest = max(highest, int(match.group(1)))
    return highest + 1


def has_any_file(path: Path) -> bool:
    return path.exists() and any(child.is_file() for child in path.rglob("*"))


def ensure_entry(
    root: Path,
    docs_subdir: str,
    data_subdir: str,
    entry_rel: str,
    with_data: bool,
) -> dict[str, object]:
    match = ENTRY_RE.match(entry_rel)
    if not match:
        raise ValueError(
            "entry_rel must match YYYY-MM-DD/{nn}-slug using lowercase letters, digits, and hyphens."
        )
    dt.date.fromisoformat(match.group("date"))
    if int(match.group("sequence")) < 1:
        raise ValueError("entry_rel sequence must be at least 1.")

    docs_dir = root / docs_subdir / entry_rel
    data_dir = root / data_subdir / entry_rel
    docs_dir.mkdir(parents=True, exist_ok=True)
    if with_data:
        data_dir.mkdir(parents=True, exist_ok=True)

    return {
        "root_dir": str(root),
        "entry_rel": entry_rel,
        "date": match.group("date"),
        "sequence": int(match.group("sequence")),
        "slug": match.group("slug"),
        "docs_dir": str(docs_dir),
        "data_dir": str(data_dir),
        "docs_dir_exists": docs_dir.exists(),
        "data_dir_exists": data_dir.exists(),
        "docs_has_files": has_any_file(docs_dir),
        "data_has_files": has_any_file(data_dir),
        "has_docs": has_any_file(docs_dir),
        "has_data": has_any_file(data_dir),
    }


def ensure_memory_file(args: argparse.Namespace) -> dict[str, object]:
    root = Path.home() / args.home_root_name
    docs_root = root / args.docs_subdir
    memory_file = docs_root / args.memory_file_name
    docs_root.mkdir(parents=True, exist_ok=True)
    created = False
    if not memory_file.exists():
        memory_file.write_text(MEMORY_TEMPLATE, encoding="utf-8")
        created = True

    return {
        "root_dir": str(root),
        "docs_root": str(docs_root),
        "memory_file": str(memory_file),
        "memory_file_exists": memory_file.exists(),
        "memory_file_created": created,
    }


def create_entry(args: argparse.Namespace) -> dict[str, object]:
    root = Path.home() / args.home_root_name
    date_str = iso_date(args.date)
    slug = slugify(args.slug)
    if args.sequence is not None and args.sequence < 1:
        raise ValueError("sequence must be at least 1.")
    sequence = args.sequence if args.sequence is not None else next_sequence(root, args.docs_subdir, args.data_subdir, date_str)
    entry_rel = f"{date_str}/{sequence:02d}-{slug}"
    return ensure_entry(root, args.docs_subdir, args.data_subdir, entry_rel, args.with_data)


def ensure_existing_entry(args: argparse.Namespace) -> dict[str, object]:
    root = Path.home() / args.home_root_name
    return ensure_entry(root, args.docs_subdir, args.data_subdir, args.entry_rel, args.with_data)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Create or reuse a Pollyanna research entry.")
    parser.add_argument("--home-root-name", default="__HOME_ROOT_NAME__")
    parser.add_argument("--docs-subdir", default="__DOCS_SUBDIR__")
    parser.add_argument("--data-subdir", default="__DATA_SUBDIR__")
    parser.add_argument("--memory-file-name", default="__MEMORY_FILE_NAME__")

    subparsers = parser.add_subparsers(dest="command", required=True)

    create = subparsers.add_parser("create", help="Create a new Pollyanna research entry.")
    create.add_argument("--slug", required=True, help="Slug basis for the folder name.")
    create.add_argument("--date", help="Override the date in YYYY-MM-DD format.")
    create.add_argument("--sequence", type=int, help="Override the numeric prefix.")
    create.add_argument("--with-data", action="store_true", help="Also create the matching data directory.")
    create.add_argument("--json", action="store_true", help="Emit JSON.")
    create.set_defaults(handler=create_entry)

    ensure = subparsers.add_parser("ensure", help="Ensure an existing entry exists.")
    ensure.add_argument("--entry-rel", required=True, help="Relative entry path, such as YYYY-MM-DD/01-example.")
    ensure.add_argument("--with-data", action="store_true", help="Also create the matching data directory.")
    ensure.add_argument("--json", action="store_true", help="Emit JSON.")
    ensure.set_defaults(handler=ensure_existing_entry)

    memory = subparsers.add_parser("memory", help="Ensure the root memory file exists.")
    memory.add_argument("--json", action="store_true", help="Emit JSON.")
    memory.set_defaults(handler=ensure_memory_file)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    result = args.handler(args)

    if getattr(args, "json", False):
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        keys = ("entry_rel", "docs_dir", "data_dir") if "entry_rel" in result else ("memory_file",)
        for key in keys:
            print(f"{key}={result[key]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
