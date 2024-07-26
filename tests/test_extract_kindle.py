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

from config import TESTS_FOLDER  # Path object
from extract_kindle import process_html  # parse_args


def test_process_html():
    """Tests the processing of a Kindle HTML export."""
    # test_args = []
    # args = parse_args(test_args)

    given_fn = TESTS_FOLDER / "kindle-given.html"
    given_txt = given_fn.read_text()

    result_txt = process_html(given_txt)
    # print(f"{result=}")

    (TESTS_FOLDER / "kindle-result.txt").write_text(result_txt)
    expected_txt = (TESTS_FOLDER / "kindle-expected.txt").read_text()
    # print(f"{expected=}")
    assert result_txt == expected_txt


if __name__ == "__main__":
    test_process_html()
