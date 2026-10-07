#!/usr/bin/env python3
"""Repo-level consistency checks, run by `make check-repo` and CI.

These checks keep the documentation that agents rely on trustworthy:

1. Required agent entry files exist, and every CLAUDE.md only points to its AGENTS.md.
2. Relative links in Markdown files resolve to real files.
3. Repo paths mentioned in backticks inside agent-facing docs exist
   (only for folders that must already exist: docs/, tools/, .claude/, .github/, infra/aws/).
4. No secret files are tracked by git.
5. Docs, the Makefile, and repo tooling use plain ASCII (no em dashes, arrows, box drawing).
   UI translation files are not checked, so Romanian diacritics stay allowed there.

Standard library only, so it runs before any project dependency is installed.
"""

from __future__ import annotations

import re
import subprocess
import sys
from dataclasses import dataclass, field
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent

REQUIRED_FILES = [
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    ".env.example",
    "Makefile",
    "backend/AGENTS.md",
    "backend/CLAUDE.md",
    "frontend/AGENTS.md",
    "frontend/CLAUDE.md",
    "infra/AGENTS.md",
    "infra/CLAUDE.md",
    "docs/glossary.md",
    "docs/recipes/README.md",
    "docs/architecture/overview.md",
    ".claude/settings.json",
]

# Not ours or not tracked: dependencies, builds, caches, and what Playwright writes after a run.
SKIP_DIRS = {
    ".git",
    "node_modules",
    ".venv",
    "dist",
    "dev-dist",
    ".pytest_cache",
    "tools/tests/fixtures",
    "test-results",
    "playwright-report",
}

# Backticked paths starting with these prefixes must exist today.
CHECKED_PATH_PREFIXES = ("docs/", "tools/", ".claude/", ".github/", "infra/aws/")


LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BACKTICK_PATH_RE = re.compile(r"`([.\w][\w./-]*)`")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)

    def error(self, where: Path | str, message: str) -> None:
        location = where.relative_to(ROOT) if isinstance(where, Path) else where
        self.errors.append(f"{location}: {message}")


def skipped(rel: str) -> bool:
    """A path inside one of SKIP_DIRS, at any depth."""
    return any(rel == d or rel.startswith(d + "/") or f"/{d}/" in f"/{rel}" for d in SKIP_DIRS)


def iter_markdown(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if skipped(rel):
            continue
        files.append(path)
    return files


def strip_code_blocks(text: str) -> str:
    """Remove fenced code blocks so example links inside them are not checked."""
    return re.sub(r"```.*?```", "", text, flags=re.DOTALL)


def check_required_files(root: Path, report: Report) -> None:
    for rel in REQUIRED_FILES:
        if not (root / rel).is_file():
            report.error(rel, "required file is missing")
    for claude in [root / "CLAUDE.md", *root.glob("*/CLAUDE.md")]:
        if claude.is_file() and claude.read_text(encoding="utf-8").strip() != "@AGENTS.md":
            report.error(claude, "must contain only '@AGENTS.md' so all agents read the same rules")


def check_links(root: Path, report: Report) -> None:
    for md in iter_markdown(root):
        text = strip_code_blocks(md.read_text(encoding="utf-8"))
        for target in LINK_RE.findall(text):
            if re.match(r"^[a-z]+:", target) or target.startswith("#"):
                continue  # external URL, mailto:, or in-page anchor
            path_part = target.split("#", 1)[0]
            if not path_part:
                continue
            resolved = (md.parent / path_part).resolve()
            if not resolved.exists():
                report.error(md, f"broken link -> {target}")


def check_backtick_paths(root: Path, report: Report) -> None:
    agent_docs = [
        *root.glob("**/AGENTS.md"),
        *(root / "docs" / "recipes").glob("*.md"),
        *(root / ".claude" / "commands").glob("*.md"),
    ]
    for md in sorted(set(agent_docs)):
        if "node_modules" in md.parts:
            continue
        text = strip_code_blocks(md.read_text(encoding="utf-8"))
        for candidate in BACKTICK_PATH_RE.findall(text):
            if not candidate.startswith(CHECKED_PATH_PREFIXES):
                continue
            if any(ch in candidate for ch in "<>*{}") or re.search(r"NNNN", candidate):
                continue  # a pattern, not a concrete path
            if not (root / candidate.rstrip("/")).exists():
                report.error(md, f"mentions `{candidate}`, which does not exist")


ASCII_ONLY_SUFFIXES = (".md", ".py", ".yml", ".yaml", ".toml", ".sh", ".example")
ASCII_ONLY_NAMES = {"Makefile", ".editorconfig", ".gitignore", ".gitattributes"}
ASCII_EXEMPT_PREFIXES = ("frontend/src/i18n/",)


def check_ascii(root: Path, report: Report) -> None:
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if not path.is_file() or skipped(rel):
            continue
        if rel.startswith(ASCII_EXEMPT_PREFIXES):
            continue
        if not (path.name in ASCII_ONLY_NAMES or path.name.endswith(ASCII_ONLY_SUFFIXES)):
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for lineno, line in enumerate(text.splitlines(), start=1):
            bad = sorted({ch for ch in line if ord(ch) > 127})
            if bad:
                shown = " ".join(f"U+{ord(ch):04X}" for ch in bad)
                report.error(f"{rel}:{lineno}", f"non-ASCII character(s) {shown}; use plain ASCII")


def check_no_tracked_secrets(root: Path, report: Report) -> None:
    try:
        tracked = subprocess.run(
            ["git", "ls-files"], cwd=root, capture_output=True, text=True, check=True
        ).stdout.splitlines()
    except (OSError, subprocess.CalledProcessError):
        return  # not a git checkout (e.g. an exported archive)
    for rel in tracked:
        name = Path(rel).name
        if (name == ".env" or (name.startswith(".env.") and name != ".env.example")) or name.endswith(
            (".pem", ".key")
        ):
            report.error(rel, "secret-looking file is tracked by git; remove it and rotate the secret")


def run(root: Path = ROOT) -> Report:
    report = Report()
    check_required_files(root, report)
    check_links(root, report)
    check_backtick_paths(root, report)
    check_no_tracked_secrets(root, report)
    check_ascii(root, report)
    return report


def main() -> int:
    report = run()
    if report.errors:
        print(f"ERROR: repo checks found {len(report.errors)} problem(s):")
        for err in report.errors:
            print(f"  - {err}")
        return 1
    print("OK: repo checks passed")
    return 0


if __name__ == "__main__":
    sys.exit(main())
