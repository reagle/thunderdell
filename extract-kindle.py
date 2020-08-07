#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This file is used with Thunderdell/
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2020 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>


from bs4 import BeautifulSoup
from email import policy
from email.parser import BytesParser
from extract_utils import uncurly, get_bib_preamble
from os.path import basename, splitext
import argparse  # http://docs.python.org/dev/library/argparse.html
import busy  # https://github.com/reagle/thunderdell
import change_case
import difflib
import email
import logging
import re
import sys

debug = logging.debug
info = logging.info
warning = logging.warning
error = logging.error
critical = logging.critical
exception = logging.exception


def process_html(content):
    """Process text for annotation kind, color, and page number."""

    RE_ISBN = re.compile(r"978(?:-?\d){10}")
    RE_COLOR_PAGE = re.compile(
        r"(?P<color>yellow|blue)</span>\) - Page (?P<page>[\dcdilmxv]+)"
    )
    color = ""
    page = ""
    text_new = []

    # replace '’' with "'"

    if RE_ISBN.search(content):
        ISBN = RE_ISBN.search(content).group(0)
        info(f"{ISBN=}")
        text_new = get_bib_preamble(ISBN)

    soup = BeautifulSoup(content, "html.parser")
    divs = soup.findAll("div")
    for div in divs:
        debug(f"{div=}")
        if "noteHeading" in str(div):
            try:
                color, page = (
                    RE_COLOR_PAGE.search(str(div)).groupdict().values()
                )
            except AttributeError:
                color = "black"
        elif "noteText" in str(div):
            note = uncurly(str(div)[27:-7])
            if color == "blue":
                note = change_case.title_case(note)
                text_new.append(f"section. {note}")
            elif color == "yellow":
                text_new.append(f"{page} excerpt. {note}")
            elif color == "black":
                text_new.append(f"-- {note}")

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
        "-o",
        "--output-to-file",
        action="store_true",
        default=False,
        help="output to FILE-fixed.EXT",
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
            filename="extract-kindle.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    return args


TEST_IN = """
<html>
<div class="noteText">
    ISBN: 978-1-101-20085-8
</div>
<div class="noteText">
    Men are rather reasoning than reasonable animals, for the most part governed by the impulse of passion.—LETTER OF APRIL 16, 1802
</div><div class="sectionHeading">
    PROLOGUE: The Oldest Revolutionary War Widow
</div>
<div class="noteHeading">
    Highlight(<span class="highlight_yellow">yellow</span>) - Page 1 · Location 205
</div>
<div class="noteText">
    PROLOGUE THE OLDEST REVOLUTIONARY WAR WIDOW
</div><div class="noteHeading">
    Highlight(<span class="highlight_yellow">yellow</span>) - Page 4 · Location 274
</div>
<div class="noteText">
    He and James Madison were the prime movers behind the summoning of the Constitutional Convention and the chief authors of that classic gloss on the national charter, The Federalist, which Hamilton supervised.
</div>
</html>
"""

TEST_OUT = """author = Ron Chernow title = Alexander Hamilton date = 20050329 publisher = Penguin isbn = 9781101200858 url = https://books.google.com/books?isbn=9781101200858
1 excerpt. PROLOGUE THE OLDEST REVOLUTIONARY WAR WIDOW
4 excerpt. He and James Madison were the prime movers behind the summoning of the Constitutional Convention and the chief authors of that classic gloss on the national charter, The Federalist, which Hamilton supervised."""

# TODO use '--' or some other method to indicate my thoughts (not
#     paraphrase or quotes.

if __name__ == "__main__":
    args = main(sys.argv[1:])
    debug(f"==================================")
    debug(f"{args=}")
    if args.test:
        TEST_RESULTS = process_html(TEST_IN)
        print("------------------------")
        print(f"\nSHOULD BE:\n```{repr(TEST_OUT)}```")
        print(f"\nRESULT IS:\n```{repr(TEST_RESULTS)}```")
        # debug(f"{type(TEST_OUT)=}", f"{len(TEST_OUT)=}")
        # debug(f"{type(TEST_RESULTS)=}", f"{len(TEST_RESULTS)=}")
        for diff in difflib.context_diff(
            process_html(TEST_IN).split("\n"), TEST_OUT.split("\n")
        ):
            print(diff)
        sys.exit()

    file_names = args.file_names
    for file_name in file_names:
        debug(f"{file_name=}")
        if args.output_to_file:
            fixed_fn = splitext(file_name)[0] + "-fixed.txt"
            fixed_fd = open(fixed_fn, "w")
        else:
            fixed_fd = sys.stdout

        if file_name.endswith(".eml"):
            with open(file_name, "rb") as fp:
                msg = BytesParser(policy=policy.default).parse(fp)
                for part in msg.walk():
                    debug(f"{part=}")
                    msg_content_type = part.get_content_subtype()
                    if msg_content_type == "html":
                        debug(f"part is HTML: %s" % msg_content_type)
                        charset = part.get_content_charset(failobj="utf-8")
                        content = part.get_payload(decode=True).decode(
                            charset, "replace"
                        )
                        new_text = process_html(content)

            fixed_fd.write(new_text)
            fixed_fd.close()

        else:
            print(
                "Do not recognize file type: {file_name} {splitext(file_name)[1]}."
            )
            sys.exit()
