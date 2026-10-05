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

from thunderdell import extract_kindle
from thunderdell.config import TESTS_FOLDER  # Path object
from thunderdell.extract_kindle import process_html  # parse_args


def test_process_html(monkeypatch):
    """Tests the processing of a Kindle HTML export."""
    # The ISBN lookup hits Google Books, which rate-limits (429); use its expected
    # first line so the test runs offline and checks only the HTML parsing.
    expected_txt = (TESTS_FOLDER / "kindle-expected.txt").read_text()
    preamble = expected_txt.split("\n", 1)[0]
    monkeypatch.setattr(extract_kindle, "get_bib_preamble", lambda _isbn: [preamble])
    # test_args = []
    # args = parse_args(test_args)

    given_fn = TESTS_FOLDER / "kindle-given.html"
    given_txt = given_fn.read_text()

    result_txt = process_html(given_txt)
    # print(f"{result=}")

    (TESTS_FOLDER / "kindle-result.txt").write_text(result_txt)
    # print(f"{expected=}")
    assert result_txt == expected_txt


if __name__ == "__main__":
    test_process_html()
