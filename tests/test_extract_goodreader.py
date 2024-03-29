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
from config import TESTS_FOLDER
from extract_goodreader import parse_args, process_text


def test_process_text():
    """
    Tests the processing of a GoodReader export.
    """

    test_args = ["--first", 0]
    args = parse_args(test_args)

    given_fn = TESTS_FOLDER / "goodreader-given.txt"
    with open(given_fn) as given_fd:
        given = given_fd.read()

    result = process_text(args, given)
    # print(f"{result=}")

    with open(TESTS_FOLDER / "goodreader-result.txt", "w") as result_fd:
        result_fd.write(result)
    with open(TESTS_FOLDER / "goodreader-expected.txt") as expected_fd:
        expected = expected_fd.read()
    # print(f"{expected=}")
    assert result == expected


if __name__ == "__main__":
    test_process_text()
