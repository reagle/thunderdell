#!/usr/bin/env python3
"""Process GoodReader email export into format accepted by `extract_dictation.py`.
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
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html

import roman  # type:ignore

# https://pypi.org/project/pyenchant/
from enchant.checker import SpellChecker  # type:ignore
from enchant import Dict
from typing import Pattern

from extract_dictation import create_mm
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
            fixed_line = smart_to_markdown(clean_ocr(line))
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


def clean_ocr(text: str) -> str:
    """Remove OCR artifacts of junk hyphens and missing spaces"""
    new_text = remove_junk_hyphens(text)
    new_text = restore_spaces(new_text)
    return new_text


def remove_junk_hyphens(
    text: str,
    hyphen_RE: Pattern = re.compile(r"([a-zA-Z]{2,})(-)([a-zA-Z]{2,})"),
    enchant_d: Dict = Dict("en_US"),  # noqa: B008 (performed once at definition)
) -> str:
    """Remove junk hyphens from PDF/OCR text.

    >>> remove_junk_hyphens('Do out-calls for your co-worker until lunch, then sw-ap.')
    'Do out-calls for your co-worker until lunch, then swap.'
    """
    matches = hyphen_RE.findall(text)

    for match in matches:
        hyphenated_word = match[0] + match[1] + match[2]
        debug(f"{hyphenated_word=}")
        debug(f"{enchant_d.check(match[0])=}")
        debug(f"{enchant_d.check(match[2])=}")
        if not (enchant_d.check(match[0]) and enchant_d.check(match[2])):
            replacement = match[0] + match[2]
            text = text.replace(hyphenated_word, replacement)

    return text


def restore_spaces(text: str) -> str:
    """Restore lost spaces in PDFs using pyenchant, taken from
    https://stackoverflow.com/questions/23314834/tokenizing-unsplit-words-from-ocr-using-nltk
    """

    checker = SpellChecker("en_US")
    debug(text)
    checker.set_text(text)
    for error in checker:
        debug(f"{error.word}, {error.suggest()}")
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
        extract_dictation.py in
            https://github.com/reagle/thunderdell
        """
    )

    # positional arguments
    arg_parser.add_argument("file_names", nargs="*", type=Path, metavar="FILE_NAMES")
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

    critical("==================================")
    critical(f"{args=}")

    for file_name in args.file_names:
        text: str = ""
        if file_name.suffix == ".eml":
            with file_name.open("rb") as fp:
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
                        raise TypeError(
                            f"Can extract text because {msg_content_type=} is unknown."
                        )
        else:
            text = file_name.read_text()

        new_text = process_text(args, text)

        fixed_fn = file_name.with_stem(file_name.stem + "-fixed").with_suffix(".txt")

        if args.output_to_file:
            fixed_fn.write_text(new_text)
            subprocess.run(["open", str(fixed_fn)])
            user_input = input(
                "\nWhen you are done in the text editor, should I invoke"
                + " `extract_dictation.py`?\n"
                + " 'y' for yes,\n"
                + " 'yp' to also include `-p` (publish to social media)\n: "
            )

            if user_input.startswith("y"):
                args.publish = False
                if user_input == "yp":
                    args.publish = True
                mm_file_name = file_name.with_suffix(".mm")
                edited_text = fixed_fn.read_text()
                create_mm(args, edited_text, mm_file_name)
                subprocess.call(["open", "-a", "Freeplane.app", mm_file_name])
        else:
            print(new_text)
