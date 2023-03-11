#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
"""
Run tests against golden YAML results; 
useful for detecting inadvertent changes.
"""
import subprocess
from config import HOME, THUNDERDELL_EXE, TESTS_FOLDER
from pathlib import Path


def test_results():
    """
    Tests the overall parsing of Mindmap XML and the relationships between
    authors with multiple titles and nested authors.
    """

    for test_fn in sorted(TESTS_FOLDER.glob("*.mm")):
        print(f"{test_fn=}")
        output = subprocess.run(
            [THUNDERDELL_EXE, "-i", test_fn],
            capture_output=True,
        )
        result = output.stdout.decode("utf-8")
        expect = open(test_fn.with_suffix(".yaml")).read()
        assert result == expect


if __name__ == "__main__":
    test_results()
