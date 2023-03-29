#!/usr/bin/env python3
"""Process GoodReader email export into format accepted by `extract-dictation.py`.
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import logging
import re
import subprocess
import sys
from email import policy
from email.parser import BytesParser
from os.path import splitext

import roman
from enchant.checker import SpellChecker  # https://pypi.org/project/pyenchant/

from utils.extract import get_bib_preamble
from utils.text import smart_to_markdown

debug = logging.debug
info = logging.info
debug = logging.debug
error = logging.error
critical = logging.critical
exception = logging.exception


RE_ANNOTATION = re.compile(r"^(?P<kind>\w+) \((?P<color>\w+)\),")
RE_DOI = re.compile(r"10\.\d{4,9}/[-._;()/:A-Z0-9]+", re.IGNORECASE)
RE_FIRST = re.compile(r"^First = (\d+)", re.IGNORECASE | re.MULTILINE)
RE_ISBN = re.compile(r"978(?:-?\d){10}")
RE_JOIN_LINES = re.compile(r"([a-z] ?)\n\n([a-z])")
RE_PAGE_NUM = re.compile(
    r"""---[ ]Page[ ]
    (?:p\.[ ])?
    \[?
    (\d+|[A-Z]+|[ivxlc]+)
    \]?
    [ ]---""",
    re.VERBOSE,
)


def process_text(args: argparse.Namespace, text: str) -> str:
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

    Table: exemplar values for page calculation
    """

    # 1st page number specified in PDF comment
    page_num_first_specfied = args.first  # 1st page specified
    page_num_first_parsed = None  # 1st page number as parsed
    page_num_offset = None  # page number offset
    page_num_parsed = None  # actual/parsed page number
    page_num_result = None  # page number result
    color = kind = prefix = ""
    ignore_next_line = False
    is_roman = False

    text_joined = RE_JOIN_LINES.sub(r"\1\2", text)  # remove spurious \n
    if match := _get_group_n(RE_FIRST, text_joined, 1):
        page_num_first_specfied = int(match)
        debug(f"{page_num_first_specfied=}")

    text_new = add_doi_isbn_info(text_joined)
    for line in text_joined.split("\n"):
        debug(f"setting {is_roman=}")
        if line == "(report generated by GoodReader)":  # end of notes
            break
        debug(f"******************** {line=}")
        if not line.strip() or ignore_next_line:
            ignore_next_line = False
            continue
        if line.startswith("Bookmark:"):
            ignore_next_line = True
            continue

        if page_num_match := RE_PAGE_NUM.match(line):
            info(f"{page_num_match=}")
            assert page_num_match is not None  # pyright needs for group(1) below
            page_num_parsed = page_num_match.group(1)
            if page_num_parsed.isdigit():
                page_num_parsed = int(page_num_parsed)
                is_roman = False
            elif page_num_parsed.isalpha():
                if page_num_parsed.isupper():
                    page_num_parsed = ord(page_num_parsed) - 96
                    is_roman = False
                    # TODO: weird PDFs using uppercase, what's after "Z"?
                else:
                    page_num_parsed = roman.fromRoman(page_num_parsed.upper())
                    is_roman = True
                    debug(f"setting {is_roman=}")
            else:
                print(f"unknown {page_num_parsed}")
                sys.exit()

            debug(f"{page_num_parsed=} SET")
            if not page_num_first_parsed:
                debug("SETTING initials")
                page_num_first_parsed = page_num_parsed
                debug(f"{page_num_first_parsed=}")
                if page_num_first_specfied:
                    page_num_offset = page_num_first_specfied - page_num_first_parsed
                else:
                    page_num_offset = 0
                debug(f"{page_num_offset=}")
        elif annotation_match := RE_ANNOTATION.match(line):
            debug("RE_ANNOTATION match")
            debug(f"{page_num_parsed=}")
            debug(f"{page_num_offset=}")
            page_num_result = page_num_parsed + page_num_offset
            debug(f"{page_num_result=}")
            # Kinds are either:
            # - "Highlight (cyan)": section title
            # - "Highlight (yellow)": excerpted text
            # - "Note (yellow)": reader comment
            kind, color = annotation_match.groupdict().values()
            if kind == "Note":
                prefix = "--"
                page_num_result = ""
            elif kind == "Highlight":
                if color == "yellow":
                    prefix = "excerpt."
                if color == "cyan":
                    prefix = "section."
                    page_num_result = ""
        else:
            debug(f"testing {is_roman=}")
            if page_num_result and is_roman:
                page_num_result = roman.toRoman(page_num_result).lower()
            fixed_line = smart_to_markdown(restore_spaces(line))
            debug(f"{page_num_result} {prefix} {fixed_line}".strip())
            text_new.append(f"{page_num_result} {prefix} {fixed_line}".strip())

    return "\n".join(text_new)


def add_doi_isbn_info(text_joined: str) -> list[str]:
    """If ISBN/DOI, add metadata."""
    if DOI := _get_group_n(RE_DOI, text_joined, 0):
        info(f"{DOI=}")
        text_new = get_bib_preamble(DOI)
    elif ISBN := _get_group_n(RE_ISBN, text_joined, 0):
        info(f"{ISBN=}")
        text_new = get_bib_preamble(ISBN)
    else:
        info("NO DOI or ISBN")
        text_new = []
    return text_new


def restore_spaces(text) -> str:
    """Restore spaces to OCR text using pyenchant, taken from
    https://stackoverflow.com/questions/23314834/tokenizing-unsplit-words-from-ocr-using-nltk
    """

    checker = SpellChecker("en_US")
    # remove spurious hyphens, too aggressive right now...
    text = re.sub(r"([a-zA-Z]{,2})(-)([a-zA-Z]{,2})", r"\1\3", text)
    # debug(text)
    checker.set_text(text)
    for error in checker:
        # debug(f'{error.word}, {error.suggest()}')
        for suggestion in error.suggest():
            # suggestion must be same as original with spaces removed
            if error.word.replace(" ", "") == suggestion.replace(" ", ""):
                error.replace(suggestion)
                break
    return checker.get_text()


def _get_group_n(regex: re.Pattern, text: str, number: int) -> str | None:
    """Type friendly matching function"""
    match = regex.search(text)
    return match.group(number) if match else None


def parse_args(argv: list) -> argparse.Namespace:
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
        default=0,
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
            filename="extract-goodreader.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    return args


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    text: str = ""

    critical("==================================")
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
                        debug("part is plain: %s" % msg_content_type)
                        charset = part.get_content_charset(failobj="utf-8")
                        content = part.get_payload(decode=True).decode(
                            charset, "replace"
                        )
                        text = content
                        debug(f"TEXT IS:\n ```{text}```")
        else:
            with open(file_name) as f:
                text = f.read()

        new_text = process_text(args, text)

        fixed_fn = splitext(file_name)[0] + "-fixed.txt"
        user_input = input("\npublish to social media? 'y' for yes: ")
        if user_input == "y":
            do_publish = "-p"
        else:
            do_publish = ""
        cmd_extract_dication = ["extract-dictation.py", do_publish, fixed_fn]
        if args.output_to_file:
            with open(fixed_fn, "w") as fixed_fd:
                fixed_fd.write(new_text)
            subprocess.run(["open", fixed_fn])
            user_input = input("\nfollow up with extract-dictation.py? 'y' for yes: ")
            if user_input == "y":
                subprocess.run(cmd_extract_dication)
            print(f"{cmd_extract_dication}")
        else:
            print(new_text)
