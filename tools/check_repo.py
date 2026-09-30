#!/usr/bin/env python3
"""Repo-level consistency checks, run by `make check-repo` and CI.

These checks keep the documentation that agents rely on trustworthy:

1. Required agent entry files exist, and every CLAUDE.md only points to its AGENTS.md.
2. Relative links in Markdown files resolve to real files.
3. Repo paths mentioned in backticks inside agent-facing docs exist
   (only for folders that must already exist: docs/, tools/, .claude/, .github/, infra/aws/).
4. ADRs are numbered, have a valid status, and are listed in docs/adr/README.md.
5. Every work package in docs/milestones/*.md has a valid status line.
6. No secret files are tracked by git.
7. Docs, the Makefile, and repo tooling use plain ASCII (no em dashes, arrows, box drawing).
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
    "docs/product-plan.md",
    "docs/adr/README.md",
    "docs/recipes/README.md",
    "docs/milestones/m1.md",
    ".claude/settings.json",
]

SKIP_DIRS = {".git", "node_modules", ".venv", "dist", "dev-dist", ".pytest_cache", "tools/tests/fixtures"}

# Backticked paths starting with these prefixes must exist today.
CHECKED_PATH_PREFIXES = ("docs/", "tools/", ".claude/", ".github/", "infra/aws/")

ADR_STATUSES = {"Proposed", "Accepted", "Deprecated", "Superseded"}
PACKAGE_STATUSES = {"todo", "in progress", "done", "blocked"}

LINK_RE = re.compile(r"(?<!!)\[[^\]]*\]\(([^)\s]+)(?:\s+\"[^\"]*\")?\)")
BACKTICK_PATH_RE = re.compile(r"`([.\w][\w./-]*)`")
ADR_FILE_RE = re.compile(r"^(\d{4})-[a-z0-9-]+\.md$")
PACKAGE_HEADING_RE = re.compile(r"^### (M\d+\.\d+) - .+$")
PACKAGE_STATUS_RE = re.compile(r"^\*\*Status:\*\* (.+?)\s*$")


@dataclass
class Report:
    errors: list[str] = field(default_factory=list)

    def error(self, where: Path | str, message: str) -> None:
        location = where.relative_to(ROOT) if isinstance(where, Path) else where
        self.errors.append(f"{location}: {message}")


def iter_markdown(root: Path) -> list[Path]:
    files = []
    for path in sorted(root.rglob("*.md")):
        rel = path.relative_to(root).as_posix()
        if any(rel == d or rel.startswith(d + "/") or f"/{d}/" in f"/{rel}" for d in SKIP_DIRS):
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
            if any(ch in candidate for ch in "<>*{}") or re.search(r"\bmN\b|NNNN", candidate):
                continue  # a pattern, not a concrete path
            if not (root / candidate.rstrip("/")).exists():
                report.error(md, f"mentions `{candidate}`, which does not exist")


def check_adrs(root: Path, report: Report) -> None:
    adr_dir = root / "docs" / "adr"
    index_path = adr_dir / "README.md"
    if not index_path.is_file():
        return
    index = index_path.read_text(encoding="utf-8")
    numbers: list[int] = []
    for path in sorted(adr_dir.glob("*.md")):
        if path.name in {"README.md", "template.md"}:
            continue
        match = ADR_FILE_RE.match(path.name)
        if not match:
            report.error(path, "ADR file name must look like 0001-short-title.md")
            continue
        numbers.append(int(match.group(1)))
        text = path.read_text(encoding="utf-8")
        status = re.search(r"^\*\*Status:\*\* (\w+)", text, flags=re.MULTILINE)
        if not status or status.group(1) not in ADR_STATUSES:
            report.error(path, f"needs a '**Status:** <{'|'.join(sorted(ADR_STATUSES))}>' line")
        if f"({path.name})" not in index:
            report.error(index_path, f"does not link to {path.name}")
    expected = list(range(1, len(numbers) + 1))
    if sorted(numbers) != expected:
        report.error(adr_dir, f"ADR numbers must be contiguous from 0001, found {sorted(numbers)}")


def check_milestones(root: Path, report: Report) -> None:
    for path in sorted((root / "docs" / "milestones").glob("m*.md")):
        lines = path.read_text(encoding="utf-8").splitlines()
        seen: set[str] = set()
        for i, line in enumerate(lines):
            heading = PACKAGE_HEADING_RE.match(line)
            if not heading:
                continue
            package = heading.group(1)
            if package in seen:
                report.error(path, f"work package {package} is listed twice")
            seen.add(package)
            status_line = next((line for line in lines[i + 1 : i + 4] if line.strip()), "")
            status = PACKAGE_STATUS_RE.match(status_line)
            if not status or status.group(1) not in PACKAGE_STATUSES:
                report.error(
                    path,
                    f"{package}: the line after the heading must be "
                    f"'**Status:** <{'|'.join(sorted(PACKAGE_STATUSES))}>'",
                )
        if not seen:
            report.error(path, "no work packages found (headings must look like '### M1.1 - Title')")


ASCII_ONLY_SUFFIXES = (".md", ".py", ".yml", ".yaml", ".toml", ".sh", ".example")
ASCII_ONLY_NAMES = {"Makefile", ".editorconfig", ".gitignore", ".gitattributes"}
ASCII_EXEMPT_PREFIXES = ("frontend/src/i18n/",)


def check_ascii(root: Path, report: Report) -> None:
    for path in sorted(root.rglob("*")):
        rel = path.relative_to(root).as_posix()
        if not path.is_file() or any(part in {".git", "node_modules", ".venv"} for part in path.parts):
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
    check_adrs(root, report)
    check_milestones(root, report)
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
