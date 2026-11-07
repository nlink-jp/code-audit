#!/usr/bin/env python3
"""Behaviour tests for the bundled scripts (stdlib only).

Runs the scripts under code-audit/scripts/ as subprocesses — the same way the
skill invokes them — and pins repository-wide invariants that do not depend
on any one script existing yet:

- every bundled script imports only the standard library;
- no file inside the distribution boundary carries an absolute local path.
"""

from __future__ import annotations

import ast
import re
import sys
import unittest
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILL = REPO / "code-audit"
SCRIPTS = SKILL / "scripts"

STDLIB = set(getattr(sys, "stdlib_module_names", ()))  # Python 3.10+; empty on 3.9
ABSOLUTE_PATH = re.compile(r"(?<![\w/])/(?:Users|home|private|Volumes)/")


def script_files() -> list[Path]:
    if not SCRIPTS.is_dir():
        return []
    return sorted(SCRIPTS.glob("*.py"))


def imported_modules(path: Path) -> set[str]:
    tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
    names: set[str] = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                names.add(alias.name.split(".")[0])
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            names.add(node.module.split(".")[0])
    return names


class DistributionBoundaryTests(unittest.TestCase):
    def test_bundled_scripts_import_only_stdlib(self) -> None:
        if not STDLIB:
            self.skipTest("sys.stdlib_module_names needs Python 3.10+")
        for script in script_files():
            with self.subTest(script=script.name):
                extra = imported_modules(script) - STDLIB
                self.assertEqual(extra, set(), f"{script.name} imports non-stdlib modules")

    def test_no_absolute_local_paths_in_skill_content(self) -> None:
        for path in sorted(SKILL.rglob("*")):
            if not path.is_file() or "__pycache__" in path.parts:
                continue
            text = path.read_text(encoding="utf-8", errors="replace")
            with self.subTest(file=str(path.relative_to(REPO))):
                self.assertIsNone(ABSOLUTE_PATH.search(text), "absolute local path in skill content")

    def test_frontmatter_name_is_the_slash_command(self) -> None:
        head = (SKILL / "SKILL.md").read_text(encoding="utf-8").split("---")[1]
        self.assertIn("name: code-audit", head)


if __name__ == "__main__":
    unittest.main(argv=[sys.argv[0], "-v"])
