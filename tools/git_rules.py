#!/usr/bin/env python3
"""Commit message and branch name rules, run by pre-commit.

Commit messages are one line in Conventional Commits form (no body, no trailers):

    <type>(<scope>): <subject>        scope is optional; "!" before ":" marks a breaking change
    feat(backend): add invite service
    fix(frontend): keep upload progress after reload
    docs: explain the upload flow

Branch names:

    <type>/<short-description>        lowercase letters, digits and hyphens
    feat/invite-links
    fix/dst-midnight

Usage:
    python3 tools/git_rules.py commit-msg <path-to-message-file>
    python3 tools/git_rules.py branch [<name>]    (defaults to the current branch)

Standard library only.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

TYPES = ("feat", "fix", "refactor", "perf", "test", "docs", "build", "ci", "chore", "revert")
SCOPES = ("backend", "frontend", "infra", "repo", "deps")
MAX_SUBJECT = 72

COMMIT_RE = re.compile(
    rf"^(?P<type>{'|'.join(TYPES)})"
    rf"(?:\((?P<scope>{'|'.join(SCOPES)})\))?"
    r"(?P<breaking>!)?: (?P<subject>\S.*)$"
)
BRANCH_RE = re.compile(rf"^(?:{'|'.join(TYPES)})/[a-z0-9][a-z0-9-]{{1,48}}[a-z0-9]$")
# Commits git or tools create on their own.
AUTO_COMMIT_RE = re.compile(r"^(Merge |Revert \"|fixup! |squash! |amend! )")
ALLOWED_BRANCHES = {"main", "HEAD"}  # HEAD = detached (rebase, CI checkouts)


# `git commit -v` appends the diff below this line; it is not part of the message.
SCISSORS_RE = re.compile(r"^# -+ >8 -+$", re.MULTILINE)


def check_commit_message(message: str) -> list[str]:
    message = SCISSORS_RE.split(message, maxsplit=1)[0]
    lines = [line for line in message.splitlines() if not line.startswith("#")]
    subject = lines[0].strip() if lines else ""
    if not subject:
        return ["The commit message is empty."]
    if AUTO_COMMIT_RE.match(subject):
        return []
    errors: list[str] = []
    match = COMMIT_RE.match(subject)
    if not match:
        errors.append(
            f"Subject must look like '<type>(<scope>): <subject>'.\n"
            f"    types:  {', '.join(TYPES)}\n"
            f"    scopes: {', '.join(SCOPES)} (optional)\n"
            f"    got:    {subject!r}"
        )
    else:
        text = match.group("subject")
        if text.endswith("."):
            errors.append("Subject must not end with a period.")
        if text[0].isupper():
            errors.append("Subject starts with a lowercase verb: 'add invite service'.")
    if len(subject) > MAX_SUBJECT:
        errors.append(f"Subject is {len(subject)} characters; keep it to {MAX_SUBJECT}.")
    if any(line.strip() for line in lines[1:]):
        errors.append("Use one line only: no body and no trailers such as Co-Authored-By.")
    return errors


def check_branch(name: str) -> list[str]:
    if name in ALLOWED_BRANCHES or BRANCH_RE.match(name):
        return []
    return [
        f"Branch {name!r} must look like '<type>/<short-description>', "
        f"for example 'feat/invite-links'.\n    types: {', '.join(TYPES)}"
    ]


def current_branch() -> str:
    result = subprocess.run(
        ["git", "rev-parse", "--abbrev-ref", "HEAD"], capture_output=True, text=True, check=False
    )
    return result.stdout.strip() or "HEAD"


def main(argv: list[str]) -> int:
    if len(argv) >= 2 and argv[0] == "commit-msg":
        errors = check_commit_message(Path(argv[1]).read_text(encoding="utf-8"))
        what = "commit message"
    elif argv and argv[0] == "branch":
        errors = check_branch(argv[1] if len(argv) > 1 else current_branch())
        what = "branch name"
    else:
        print(__doc__)
        return 2
    if errors:
        print(f"ERROR: invalid {what}:")
        for err in errors:
            print(f"  - {err}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
