#!/usr/bin/env python3
from __future__ import annotations

import argparse
import functools
import http.server
import os
import shutil
import subprocess
import tempfile
import threading
from pathlib import Path


DEFAULT_SKILL_ROOTS = (
    ".agents/skills",
    ".claude/skills",
    ".cursor/skills",
    ".kiro/skills",
    ".cline/skills",
)


class QuietRequestHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, _format: str, *_args: object) -> None:
        pass


def run_checked(command: list[str], *, cwd: Path, env: dict[str, str]) -> None:
    result = subprocess.run(command, cwd=cwd, env=env, text=True, capture_output=True, check=False)
    if result.returncode == 0:
        return
    details = "\n".join(part.strip() for part in (result.stdout, result.stderr) if part.strip())
    raise RuntimeError(f"Bootstrap command failed: {' '.join(command)}\n{details}")


def make_archive(repo_root: Path, temporary_root: Path, archive_format: str) -> Path:
    source_parent = temporary_root / "source"
    source_root = source_parent / "pollyanna-source"
    shutil.copytree(
        repo_root,
        source_root,
        ignore=shutil.ignore_patterns(".git", ".pollyanna", ".pytest_cache", ".venv", "__pycache__"),
    )
    archive_root = temporary_root / "archive"
    archive_root.mkdir()
    return Path(
        shutil.make_archive(
            str(archive_root / "pollyanna-source"),
            archive_format,
            root_dir=source_parent,
            base_dir=source_root.name,
        )
    )


def require_default_install(install_home: Path) -> None:
    expected = [install_home / root / "pollyanna" / "SKILL.md" for root in DEFAULT_SKILL_ROOTS]
    expected.extend(
        (
            install_home / ".agents/skills/pollyanna/assets/POLLYANNA.md",
            install_home / "pollyanna/docs/memory.md",
        )
    )
    missing = [str(path) for path in expected if not path.is_file()]
    if missing:
        raise RuntimeError(f"Bootstrap installer did not create: {', '.join(missing)}")


def run_bootstrap(repo_root: Path, installer_kind: str) -> None:
    with tempfile.TemporaryDirectory(prefix="pollyanna-bootstrap-") as temporary:
        temporary_root = Path(temporary)
        archive_format = "gztar" if installer_kind == "bash" else "zip"
        archive = make_archive(repo_root, temporary_root, archive_format)
        remote_script = temporary_root / ("install.sh" if installer_kind == "bash" else "install.ps1")
        shutil.copy2(repo_root / remote_script.name, remote_script)
        install_home = temporary_root / "install-home"

        handler = functools.partial(QuietRequestHandler, directory=str(archive.parent))
        server = http.server.ThreadingHTTPServer(("127.0.0.1", 0), handler)
        server_thread = threading.Thread(target=server.serve_forever, daemon=True)
        server_thread.start()
        try:
            environment = dict(os.environ)
            environment["POLLYANNA_REPO_ARCHIVE_URL"] = (
                f"http://127.0.0.1:{server.server_port}/{archive.name}"
            )
            environment["POLLYANNA_INSTALL_HOME"] = str(install_home)
            if installer_kind == "bash":
                command = ["bash", str(remote_script), "--yes"]
            else:
                command = [
                    "pwsh",
                    "-NoLogo",
                    "-NoProfile",
                    "-File",
                    str(remote_script),
                    "-Yes",
                    "-InstallHome",
                    str(install_home),
                ]
            run_checked(command, cwd=temporary_root, env=environment)
        finally:
            server.shutdown()
            server.server_close()
            server_thread.join()

        require_default_install(install_home)


def main() -> int:
    parser = argparse.ArgumentParser(description="Exercise Pollyanna's remote-bootstrap installer path.")
    parser.add_argument("installer", choices=("bash", "powershell"))
    parser.add_argument("--repo-root", required=True)
    args = parser.parse_args()
    run_bootstrap(Path(args.repo_root).resolve(), args.installer)
    print(f"{args.installer} bootstrap smoke test passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
