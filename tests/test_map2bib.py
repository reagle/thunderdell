#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
"""Run tests against golden YAML results; useful for detecting inadvertent changes.

Run in parent folder as `pytest tests`.
"""

import difflib
import subprocess

from thunderdell.config import TESTS_FOLDER, THUNDERDELL_EXE


def diff_strings(a: str, b: str) -> str:
    """Return a string representation of the differences between two strings."""
    diff = difflib.ndiff(a.splitlines(keepends=True), b.splitlines(keepends=True))
    return "".join(diff)


def test_results():
    """Test results of running thunder.

    Tests the overall parsing of Mindmap XML and the relationships between
    authors with multiple titles and nested authors.
    """
    for test_fn in sorted(TESTS_FOLDER.glob("*.mm")):
        print(f"{test_fn=}")
        output = subprocess.run(
            [str(THUNDERDELL_EXE), "-i", test_fn],
            capture_output=True,
        )
        result = output.stdout.decode("utf-8")
        # expect = open(test_fn.with_suffix(".yaml")).read()
        expect = test_fn.with_suffix(".yaml").read_text()
        assert result == expect, (
            f"\nExpected:\n{expect}\n\nGot:\n{result}\n\nDiff:\n{diff_strings(expect, result)}"
        )


if __name__ == "__main__":
    test_results()
