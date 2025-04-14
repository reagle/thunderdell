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

import lxml.etree as et

from thunderdell.config import TESTS_FOLDER
from thunderdell.map2bib import (
    process_arguments,
    walk_freeplane,
)


def diff_strings(a: str, b: str) -> str:
    """Return a string representation of the differences between two strings."""
    diff = difflib.ndiff(a.splitlines(keepends=True), b.splitlines(keepends=True))
    return "".join(diff)


class CaptureOutput:
    """Context manager to capture output that would go to a file."""

    def __init__(self):
        self.captured_output = ""

    def write(self, text):
        self.captured_output += text

    def close(self):
        pass


def test_results():
    """Test results of direct function calls to map2bib functionality.

    Tests the overall parsing of Mindmap XML and the relationships between
    authors with multiple titles and nested authors.
    """
    for test_fn in sorted(TESTS_FOLDER.glob("*.mm")):
        print(f"{test_fn=}")

        # Parse arguments similar to command line but directly in Python
        args = process_arguments(["-i", str(test_fn)])
        args.in_main = False  # Prevent browser opening and server starting

        # Set up capture for output
        output_capture = CaptureOutput()
        args.outfd = output_capture

        # Load the XML file
        doc = et.parse(test_fn).getroot()

        # Initialize entries dictionary
        entries = {}

        # Process the mindmap directly
        entries, _ = walk_freeplane(args, doc, test_fn, entries, links=[])

        # Use the YAML emitter (default behavior)
        from thunderdell.formats import emit_yaml_csl

        emit_yaml_csl(args, entries)

        # Get the result and compare with expected
        result = output_capture.captured_output
        expect = test_fn.with_suffix(".yaml").read_text()

        assert result == expect, (
            f"\nExpected:\n{expect}\n\nGot:\n{result}\n\nDiff:\n{diff_strings(expect, result)}"
        )


if __name__ == "__main__":
    test_results()
