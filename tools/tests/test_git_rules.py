"""Tests for tools/git_rules.py."""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from git_rules import check_branch, check_commit_message, main  # noqa: E402


class CommitMessageTests(unittest.TestCase):
    def test_valid_messages(self) -> None:
        for message in [
            "feat(backend): add invite service",
            "fix: handle dst midnight\n\n",
            "feat: add x\n# ------------------------ >8 ------------------------\ndiff --git a b",
            "refactor(frontend)!: rename upload store",
            "docs(repo): explain recipes",
            "Merge branch 'feat/x'",
            "fixup! feat(backend): add invite service",
            "chore(deps): bump django\n# a git comment line",
        ]:
            with self.subTest(message=message):
                self.assertEqual(check_commit_message(message), [])

    def test_invalid_messages(self) -> None:
        cases = {
            "add invite service": "must look like",
            "feature(backend): add invite": "must look like",
            "feat(api): add invite": "must look like",
            "feat(backend):add invite": "must look like",
            "feat(backend): Add invite": "lowercase",
            "feat(backend): add invite.": "period",
            "feat(backend): " + "x" * 80: "characters",
            "feat: add invite\nbody without blank line": "one line",
            "fix: handle dst midnight\n\nLonger explanation.": "one line",
            "feat: add invite\n\nCo-Authored-By: Someone <x@example.com>": "one line",
            "": "empty",
        }
        for message, expected in cases.items():
            with self.subTest(message=message):
                errors = check_commit_message(message)
                self.assertTrue(errors, message)
                self.assertIn(expected, " ".join(errors))


class BranchTests(unittest.TestCase):
    def test_valid_branches(self) -> None:
        for name in ["main", "HEAD", "feat/invite-links", "fix/dst-midnight", "chore/m1-2"]:
            with self.subTest(name=name):
                self.assertEqual(check_branch(name), [])

    def test_invalid_branches(self) -> None:
        for name in ["invite-links", "feat/Invite", "feature/x", "feat/a", "feat/ends-", "dev"]:
            with self.subTest(name=name):
                self.assertTrue(check_branch(name))


class MainTests(unittest.TestCase):
    def test_commit_msg_mode_reads_the_file(self) -> None:
        with tempfile.NamedTemporaryFile("w", suffix=".txt", delete=False) as fh:
            fh.write("nope\n")
        try:
            self.assertEqual(main(["commit-msg", fh.name]), 1)
        finally:
            Path(fh.name).unlink()

    def test_branch_mode_and_usage(self) -> None:
        self.assertEqual(main(["branch", "feat/ok-name"]), 0)
        self.assertEqual(main(["branch", "bad"]), 1)
        self.assertEqual(main([]), 2)


if __name__ == "__main__":
    unittest.main()
