#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This file is used with Thunderdell
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2020 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>

import argparse  # http://docs.python.org/dev/library/argparse.html
import difflib
import logging
import re
import sys
from email import policy
from email.parser import BytesParser
from os.path import splitext

from enchant.checker import SpellChecker  # https://pypi.org/project/pyenchant/
from extract_utils import get_bib_preamble, uncurly

debug = logging.debug
info = logging.info
warning = logging.warning
error = logging.error
critical = logging.critical
exception = logging.exception


def restore_spaces(text):
    """Restore spaces to OCR text using pyenchant, taken from
    https://stackoverflow.com/questions/23314834/tokenizing-unsplit-words-from-ocr-using-nltk
    """

    checker = SpellChecker("en_US")
    # remove spurious hyphens, too aggressive right now...
    text = re.sub(r"([a-zA-Z]{,2})(-)([a-zA-Z]{,2})", r"\1\3", text)
    # debugtext)
    checker.set_text(text)
    for error in checker:
        # debugf'{error.word}, {error.suggest()}')
        for suggestion in error.suggest():
            # suggestion must be same as original with spaces removed
            if error.word.replace(" ", "") == suggestion.replace(" ", ""):
                error.replace(suggestion)
                break
    return checker.get_text()


def process_text(text):
    """Process text for annotation kind, color, and page number, joining
    lines as needed"""

    """
    | first_specified | first_parsed | offset | parsed | result |
    |-----------------|--------------|--------|--------|--------|
    | 5               | 5            | 0      | 10     | 10     |
    | 5               | 7            | -2     | 10     | 08     |
    | 5               | 4            | 1      | 10     | 11     |
    | -3              | 1            | -4     | 10     | 6      |
    | 0               | 1            | None   | 10     | 10     |
    """

    RE_ANNOTATION = re.compile(r"^(?P<kind>\w+) \((?P<color>\w+)\),")
    RE_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
    RE_FIRST = re.compile(r"^First = (\d+)", re.IGNORECASE | re.MULTILINE)
    RE_ISBN = re.compile(r"978(?:-?\d){10}")
    RE_JOIN_LINES = re.compile(r"([a-z] ?)\n\n([a-z])")
    RE_PAGE_NUM = re.compile(
        r"""---[ ]Page[ ]
        (?:p\. )?
        \[? 
        (\d+|[A-Z]+)  # digit or (rare) capital letter. TODO: roman numerals
        \]?[ ]---""",
        re.VERBOSE,
    )
    page_num_first_parsed = None  # 1st page number as parsed
    page_num_first_specfied = None  # 1st page number specified in PDF comment
    page_num_offset = None  # page number offset
    page_num_parsed = None  # actual/parsed page number
    page_num_result = None  # page number result
    color = kind = prefix = ""
    ignore_next_line = False

    text_joined = RE_JOIN_LINES.sub(r"\1\2", text)  # remove spurious \n
    if RE_FIRST.search(text_joined):
        page_num_first_specfied = int(RE_FIRST.search(text_joined).group(1))
        print(f"{page_num_first_specfied=}")
        warning(f"{page_num_first_specfied=}")
    if args.first:
        page_num_first_specfied = args.first

    if RE_DOI.search(text_joined):
        DOI = RE_DOI.search(text_joined).group(0)
        info(f"{DOI=}")
        text_new = get_bib_preamble(DOI)
    elif RE_ISBN.search(text_joined):
        ISBN = RE_ISBN.search(text_joined).group(0)
        info(f"{ISBN=}")
        text_new = get_bib_preamble(ISBN)
    else:
        info(f"NO DOI or ISBN")
        text_new = []

    for line in text_joined.split("\n"):
        if line == "(report generated by GoodReader)":  # end of notes
            break
        warning(f"********************\n{line=}")
        if not line.strip() or ignore_next_line:
            ignore_next_line = False
            continue
        if line.startswith("Bookmark:"):
            ignore_next_line = True
            continue

        if RE_PAGE_NUM.match(line):
            warning(f"{RE_PAGE_NUM.match(line)=}")
            page_num_parsed = RE_PAGE_NUM.match(line).groups(0)[0]
            if page_num_parsed.isdigit():
                page_num_parsed = int(page_num_parsed)
            elif page_num_parsed.isalpha():
                page_num_parsed = ord(page_num_parsed) - 96
            # TODO: when letters are used, what happens after page z?
            # TODO: identify roman numerals
            else:
                print(f"unknown {page_num_parsed}")
                sys.exit()

            warning(f"{page_num_parsed=} SET")
            if not page_num_first_parsed:
                warning(f"SETTING initials")
                page_num_first_parsed = page_num_parsed
                warning(f"{page_num_first_parsed=}")
                if page_num_first_specfied:
                    page_num_offset = (
                        page_num_first_specfied - page_num_first_parsed
                    )
                else:
                    page_num_offset = 0
                warning(f"{page_num_offset=}")
        elif RE_ANNOTATION.match(line):
            debug(f"RE_ANNOTATION match")
            # breakpoint()
            page_num_result = page_num_parsed + page_num_offset
            debug(f"{page_num_result=}")
            kind, color = RE_ANNOTATION.match(line).groupdict().values()
            if kind == "Note":
                prefix = "--"
                page_num_result = ""
            elif kind == "Highlight":
                if color == "yellow":
                    prefix = "excerpt."
                if color == "blue":
                    prefix = "section."
                    page_num_result = ""
        else:
            fixed_line = uncurly(restore_spaces(line))
            debug(f"{page_num_result} {prefix} {fixed_line}".strip())
            text_new.append(f"{page_num_result} {prefix} {fixed_line}".strip())

    return "\n".join(text_new)


def main(argv):
    """Process arguments"""
    # https://docs.python.org/3/library/argparse.html
    arg_parser = argparse.ArgumentParser(
        description="""Format (emailed) GoodRead annotation for use with
        dictation-extract.py in
            https://github.com/reagle/thunderdell
        """
    )

    # positional arguments
    arg_parser.add_argument("file_names", nargs="*", metavar="FILE_NAMES")
    # optional arguments
    arg_parser.add_argument(
        "-f",
        "--first",
        type=int,
        default=None,
        help=r"""first page in actual PDF pagination,
            can also be specified as annotation within PDF: `first = \d+`""",
    )
    arg_parser.add_argument(
        "-o",
        "--output-to-file",
        action="store_true",
        default=False,
        help="output to FILE-fixed.txt",
    )
    arg_parser.add_argument(
        "-L",
        "--log-to-file",
        action="store_true",
        default=False,
        help="log to file %(prog)s.log",
    )
    arg_parser.add_argument(
        "-T",
        "--test",
        action="store_true",
        default=False,
        help="run doc tests",
    )
    arg_parser.add_argument(
        "-V",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument("--version", action="version", version="0.1")
    args = arg_parser.parse_args(argv)

    log_level = 100  # default
    if args.verbose >= 3:
        log_level = logging.DEBUG  # 10
    elif args.verbose == 2:
        log_level = logging.INFO  # 20
    elif args.verbose == 1:
        log_level = logging.ERROR  # 40
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(
            filename="exract-goodreader.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    return args


TEST_IN = """
--- Page 2 ---

Note (yellow), reagle:
First = 92

Highlight (yellow), reagle:
10.1093/isq/sqy041

--- Page 36 ---

Bookmark:
Dec 9

Highlight (blue), reagle:
3 A World Brain as an “Education System”

Highlight (blue), reagle:
3.1 A World BrainasaLearning System

Note (yellow), reagle:
Little discussion of HG Wells directly—rather a literaturereview of work related to motifs in Wells

--- Page 39 ---

Highlight (blue), reagle:
3.2 A World Brain asaTeaching System

--- Page 71 ---

In my own view, there is an urgentneed for a sudden surge of

understanding, positive thinking andaltruistic attitudes.

"""

TEST_OUT = """author = Duncan Bell title = Founding the world state: H. G. Wells on empire and the English-Speaking peoples date = 20181201 journal = International Studies Quarterly volume = 62 number = 4 publisher = Oxford University Press (OUP) DOI = 10.1093/isq/sqy041 url = http://dx.doi.org/10.1093/isq/sqy041\n-- First = 92\n92 excerpt. 10.1093/isq/sqy041\nsection. 3 A World Brain as an "Education System"\nsection. 3.1 A World BrainasaLearning System\n-- Little discussion of HG Wells directly---rather a literature review of work related to motifs in Wells\nsection. 3.2 A World Brain asaTeaching System\nsection. In my own view, there is an urgent need for a sudden surge of understanding, positive thinking and altruistic attitudes."""

if __name__ == "__main__":
    args = main(sys.argv[1:])
    critical(f"==================================")
    critical(f"{args=}")
    file_names = args.file_names

    for file_name in file_names:
        if file_name.endswith(".eml"):
            with open(file_name, "rb") as fp:
                msg = BytesParser(policy=policy.default).parse(fp)
                for part in msg.walk():
                    debug(f"{part=}")
                    msg_content_type = part.get_content_subtype()
                    debug(f"{msg_content_type=}")
                    if msg_content_type == "plain":
                        debug(f"part is plain: %s" % msg_content_type)
                        charset = part.get_content_charset(failobj="utf-8")
                        content = part.get_payload(decode=True).decode(
                            charset, "replace"
                        )
                        text = content
                        debug(f"TEXT IS:\n ```{text}```")
        else:
            with open(file_name) as f:
                text = f.read()

        new_text = process_text(text)

        if args.output_to_file:
            fixed_fn = splitext(file_name)[0] + "-fixed.txt"
            fixed_fd = open(fixed_fn, "w")
        else:
            fixed_fd = sys.stdout
        fixed_fd.write(new_text)
        fixed_fd.close()

    if args.test:
        TEST_RESULTS = process_text(TEST_IN)
        print("------------------------")
        print(f"\nSHOULD BE:\n```{repr(TEST_OUT)}```")
        print(f"\nRESULT IS:\n```{repr(TEST_RESULTS)}```")
        debug(f"{type(TEST_OUT)=}", f"{len(TEST_OUT)=}")
        debug(f"{type(TEST_RESULTS)=}", f"{len(TEST_RESULTS)=}")
        if TEST_OUT == TEST_RESULTS:
            print(f"\nPASS\n")
        else:
            print(f"\nFAIL: DIFF IS:\n")
            for diff in difflib.context_diff(
                TEST_RESULTS.split("\n"),
                TEST_OUT.split("\n"),
                fromfile="SHOULD",
                tofile="RESULT",
                n=0,
                lineterm="",
            ):
                print(f"{diff}", end="\n")
