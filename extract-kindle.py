#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#


import argparse  # http://docs.python.org/dev/library/argparse.html
import difflib
import logging
import re
import subprocess
import sys
from email import policy
from email.parser import BytesParser
from os.path import splitext

from bs4 import BeautifulSoup
from utils.extract import get_bib_preamble

import change_case
from utils.text import smart_to_markdown

debug = logging.debug
info = logging.info
warning = logging.warning
error = logging.error
critical = logging.critical
exception = logging.exception


def process_email(file_name):
    """Process parts of a MIME message store in file."""

    with open(file_name, "rb") as fp:
        msg = BytesParser(policy=policy.default).parse(fp)
        for part in msg.walk():
            debug(f"{part=}")
            msg_content_type = part.get_content_subtype()
            if msg_content_type == "html":
                debug("part is HTML: %s" % msg_content_type)
                charset = part.get_content_charset(failobj="utf-8")
                content = part.get_payload(decode=True).decode(charset, "replace")
                return content


def process_html(content):
    """Process text for annotation kind, color, and page number."""

    RE_ISBN = re.compile(r"978(?:-?\d){10}")

    RE_COLOR_PAGE = re.compile(
        r"(?P<color>yellow|blue)</span>\) .*? (?P<type>Page|Location)"
        r" (?P<page>[\dcdilmxv]+)",
    )
    color = ""
    page = ""
    text_new = []
    _, pagination_type, _ = RE_COLOR_PAGE.search(content).groupdict().values()

    if RE_ISBN.search(content):
        ISBN = RE_ISBN.search(content).group(0)
        info(f"{ISBN=}")
        text_new = get_bib_preamble(ISBN)
    text_new.append("edition = Kindle")
    if pagination_type == "Location":
        text_new.append("pagination = location")

    soup = BeautifulSoup(content, "html.parser")
    divs = soup.findAll("div")
    for div in divs:
        debug(f"{div=}")
        if "noteHeading" in str(div):
            try:
                color, _, page = RE_COLOR_PAGE.search(str(div)).groupdict().values()
            except AttributeError:
                color = "black"
        elif "noteText" in str(div):
            note = smart_to_markdown(str(div)[27:-7])
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
        description="""Format Kindle annotations (sent via HTML notes shared in
        *tablet* Kindle app) for use with dictation-extract.py in
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
        help="increase verbosity (specify multiple times for more)",
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

</div><div class="noteHeading">
    Highlight(<span class="highlight_yellow">yellow</span>) - 3. The Rise of the Big Black Woman > Page 88 · Location 1536
</div>
<div class="noteText">
    in the context of the Enlightenment, the British preoccupation with the ills of excess feeding were folded into the racial discourse. This helped to make overindulgence evidence of not only slow wit but also barbarism.
</div>

</html>
"""  # noqa: E501

TEST_OUT = """author = Ron Chernow title = Alexander Hamilton date = 20050329 publisher = Penguin isbn = 9781101200858 url = https://books.google.com/books?isbn=9781101200858\n1 excerpt. PROLOGUE THE OLDEST REVOLUTIONARY WAR WIDOW\n4 excerpt. He and James Madison were the prime movers behind the summoning of the Constitutional Convention and the chief authors of that classic gloss on the national charter, The Federalist, which Hamilton supervised.\n88 excerpt. in the context of the Enlightenment, the British preoccupation with the ills of excess feeding were folded into the racial discourse. This helped to make overindulgence evidence of not only slow wit but also barbarism."""  # noqa: E501

# TODO use '--' or some other method to indicate my thoughts (not
#     paraphrase or quotes.

if __name__ == "__main__":
    args = main(sys.argv[1:])
    info("==================================")
    debug(f"{args=}")
    if args.test:
        TEST_RESULTS = process_html(TEST_IN)
        print("------------------------")
        if repr(TEST_OUT) != repr(TEST_RESULTS):
            print(f"\nSHOULD BE:\n```{repr(TEST_OUT)}```")
            print(f"\nRESULT IS:\n```{repr(TEST_RESULTS)}```")
            # debug(f"{type(TEST_OUT)=}", f"{len(TEST_OUT)=}")
            # debug(f"{type(TEST_RESULTS)=}", f"{len(TEST_RESULTS)=}")
            for diff in difflib.context_diff(
                process_html(TEST_IN).split("\n"), TEST_OUT.split("\n")
            ):
                print(diff)
        else:
            print("tests pass")
        sys.exit()

    file_names = args.file_names
    for file_name in file_names:
        debug(f"{file_name=}")
        if file_name.endswith(".eml"):
            fixed_fn = splitext(file_name)[0] + "-fixed.txt"
            user_input = input("\npublish to social media? 'y' for yes: ")
            if user_input == "y":
                do_publish = "-p"
            else:
                do_publish = ""
            cmd_extract_dication = ["extract-dictation.py", do_publish, fixed_fn]
            content = process_email(file_name)
            new_text = process_html(content)
            if args.output_to_file:
                with open(fixed_fn, "w") as fixed_fd:
                    fixed_fd.write(new_text)
                subprocess.run(["open", fixed_fn])
                user_input = input(
                    "\nfollow up with extract-dictation.py? 'y' for yes: "
                )
                if user_input == "y":
                    subprocess.run(cmd_extract_dication)
                print(f"{cmd_extract_dication}")
            else:
                print(new_text)
        else:
            raise OSError(
                "Do not recognize file type: {file_name} {splitext(file_name)[1]}."
            )
