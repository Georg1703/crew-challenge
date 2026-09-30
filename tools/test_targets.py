#!/usr/bin/env python3
"""Print pytest targets for backend code changed on this branch (used by `make test-fast`).

Rules:
- A change in `backend/apps/<app>/` selects `apps/<app>`.
- A change in shared code (`config/`, `apps/core/`, `integrations/`, `tests/`, `pyproject.toml`,
  `uv.lock`) selects the whole test suite, because everything depends on it.
- No backend changes selects nothing and pytest is told to run the default suite quickly (`--lf`).

Paths are printed relative to backend/, because pytest runs from there.
"""

from __future__ import annotations

import subprocess
import sys

SHARED_PREFIXES = (
    "backend/config/",
    "backend/apps/core/",
    "backend/integrations/",
    "backend/tests/",
    "backend/pyproject.toml",
    "backend/uv.lock",
    "backend/conftest.py",
)


def changed_files(base: str = "main") -> set[str]:
    def git(*args: str) -> list[str]:
        result = subprocess.run(["git", *args], capture_output=True, text=True)
        return result.stdout.split() if result.returncode == 0 else []

    merge_base = git("merge-base", "HEAD", base)
    files: set[str] = set()
    if merge_base:
        files.update(git("diff", "--name-only", merge_base[0]))
    files.update(git("diff", "--name-only"))  # unstaged
    files.update(git("diff", "--name-only", "--cached"))  # staged
    files.update(git("ls-files", "--others", "--exclude-standard"))  # new files
    return files


def targets(files: set[str]) -> list[str]:
    backend = [f for f in files if f.startswith("backend/")]
    if not backend:
        return ["--lf"]
    if any(f.startswith(SHARED_PREFIXES) for f in backend):
        return []  # empty = full suite
    apps = sorted({f.split("/")[2] for f in backend if f.startswith("backend/apps/") and f.count("/") >= 3})
    return [f"apps/{app}" for app in apps] or ["--lf"]


def main() -> int:
    area = sys.argv[1] if len(sys.argv) > 1 else "backend"
    if area != "backend":
        print(f"unknown area: {area}", file=sys.stderr)
        return 2
    print(" ".join(targets(changed_files())))
    return 0


if __name__ == "__main__":
    sys.exit(main())
