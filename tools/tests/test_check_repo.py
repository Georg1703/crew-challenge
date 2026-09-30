"""Tests for tools/check_repo.py. Run with: python3 -m unittest discover -s tools/tests"""

from __future__ import annotations

import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import check_repo  # noqa: E402


def write(root: Path, rel: str, text: str) -> None:
    path = root / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


class CheckRepoTests(unittest.TestCase):
    def setUp(self) -> None:
        self._tmp = tempfile.TemporaryDirectory()
        self.root = Path(self._tmp.name)

    def tearDown(self) -> None:
        self._tmp.cleanup()

    def errors(self, check) -> list[str]:
        report = check_repo.Report()
        original = check_repo.ROOT
        check_repo.ROOT = self.root
        try:
            check(self.root, report)
        finally:
            check_repo.ROOT = original
        return report.errors

    def test_broken_relative_link_is_reported(self) -> None:
        write(self.root, "docs/a.md", "See [b](b.md) and [missing](nope.md).")
        write(self.root, "docs/b.md", "ok")
        errors = self.errors(check_repo.check_links)
        self.assertEqual(len(errors), 1)
        self.assertIn("nope.md", errors[0])

    def test_links_inside_code_blocks_and_urls_are_ignored(self) -> None:
        write(self.root, "a.md", "```\n[x](missing.md)\n```\n[site](https://example.com) [top](#top)")
        self.assertEqual(self.errors(check_repo.check_links), [])

    def test_claude_md_must_point_to_agents_md(self) -> None:
        write(self.root, "CLAUDE.md", "some other rules")
        errors = self.errors(check_repo.check_required_files)
        self.assertTrue(any("must contain only '@AGENTS.md'" in e for e in errors))

    def test_backtick_paths_under_docs_must_exist(self) -> None:
        write(self.root, "AGENTS.md", "Read `docs/real.md` and `docs/fake.md`, see `backend/later.py`.")
        write(self.root, "docs/real.md", "ok")
        errors = self.errors(check_repo.check_backtick_paths)
        self.assertEqual(len(errors), 1)
        self.assertIn("docs/fake.md", errors[0])

    def test_adr_must_be_indexed_and_have_status(self) -> None:
        write(self.root, "docs/adr/README.md", "- [0001](0001-first.md)")
        write(self.root, "docs/adr/0001-first.md", "# 1\n\n**Status:** Accepted\n")
        write(self.root, "docs/adr/0002-second.md", "# 2\n\nno status\n")
        errors = self.errors(check_repo.check_adrs)
        self.assertTrue(any("Status" in e for e in errors))
        self.assertTrue(any("does not link to 0002-second.md" in e for e in errors))

    def test_adr_numbers_must_be_contiguous(self) -> None:
        write(self.root, "docs/adr/README.md", "[a](0001-a.md) [c](0003-c.md)")
        write(self.root, "docs/adr/0001-a.md", "**Status:** Accepted")
        write(self.root, "docs/adr/0003-c.md", "**Status:** Accepted")
        errors = self.errors(check_repo.check_adrs)
        self.assertTrue(any("contiguous" in e for e in errors))

    def test_milestone_packages_need_valid_status(self) -> None:
        write(
            self.root,
            "docs/milestones/m1.md",
            "### M1.1 · Good\n**Status:** done\n\n### M1.2 · Bad\n**Status:** maybe\n",
        )
        errors = self.errors(check_repo.check_milestones)
        self.assertEqual(len(errors), 1)
        self.assertIn("M1.2", errors[0])


if __name__ == "__main__":
    unittest.main()
