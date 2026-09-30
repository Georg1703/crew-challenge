"""Tests for tools/test_targets.py."""

from __future__ import annotations

import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from test_targets import targets  # noqa: E402


class TestTargetsTests(unittest.TestCase):
    def test_no_backend_changes_runs_last_failed(self) -> None:
        self.assertEqual(targets({"frontend/src/main.tsx", "docs/glossary.md"}), ["--lf"])

    def test_app_changes_select_those_apps(self) -> None:
        files = {"backend/apps/crews/services.py", "backend/apps/accounts/api/views.py"}
        self.assertEqual(targets(files), ["apps/accounts", "apps/crews"])

    def test_shared_code_change_runs_everything(self) -> None:
        files = {"backend/apps/crews/services.py", "backend/apps/core/clock.py"}
        self.assertEqual(targets(files), [])


if __name__ == "__main__":
    unittest.main()
