#!/usr/bin/env python3
"""Process GoodReader email export into format accepted by `extract_dictation.py`."""

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
from email.message import EmailMessage
from email.parser import BytesParser
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html

# https://pyenchant.github.io/pyenchant/
# pyenchant provides useful compound word corrections,
# but is an annoying dependency; if there's a problem test with
# `import enchant; print(enchant.__version__)`
# and then `pip uninstall pyenchant; pip install pyenchant`
import enchant
import enchant.checker
import roman

# https://pypi.org/project/Send2Trash/
from send2trash import send2trash  # type: ignore

from thunderdell.extract_dictation import create_mm
from thunderdell.utils.extract import get_bib_preamble
from thunderdell.utils.text import smart_to_markdown

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
    """Process text for annotation kind, color, and page number, joining lines as needed."""
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

    # 1st page specified in args or PDF comment
    page_num_first_specfied: int = args.first
    page_num_first_parsed: int = 0  # 1st page number as parsed
    page_num_offset: int = 0  # page number offset
    page_num_parsed: int | str = 0  # page number parsed, can be roman
    page_num_result: int | str = 0  # page number result, can be roman or ""
    color = kind = prefix = ""
    ignore_next_line = False
    is_roman = False

    text_joined = RE_JOIN_LINES.sub(r"\1\2", text)  # remove spurious \n
    if match := _get_group_n(RE_FIRST, text_joined, 1):
        page_num_first_specfied = int(match)
        logging.debug(f"{page_num_first_specfied=}")

    text_new = add_doi_isbn_info(text_joined)
    for line in text_joined.split("\n"):
        logging.debug(f"setting {is_roman=}")
        if line == "(report generated by GoodReader)":  # end of notes
            break
        logging.debug(f"******************** {line=}")
        if not line.strip() or ignore_next_line:
            ignore_next_line = False
            continue
        if line.startswith("Bookmark:"):
            ignore_next_line = True
            continue

        if page_num_match := RE_PAGE_NUM.match(line):
            logging.info(f"{page_num_match=}")
            page_num_parsed = str(page_num_match.group(1))
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
                    logging.debug(f"setting {is_roman=}")
            else:
                print(f"unknown {page_num_parsed}")
                sys.exit()

            logging.debug(f"{page_num_parsed=} SET")
            if not page_num_first_parsed:
                logging.debug("SETTING initials")
                page_num_first_parsed = int(page_num_parsed)
                logging.debug(f"{page_num_first_parsed=}")
                if page_num_first_specfied:
                    page_num_offset = page_num_first_specfied - page_num_first_parsed
                else:
                    page_num_offset = 0
                logging.debug(f"{page_num_offset=}")
        elif annotation_match := RE_ANNOTATION.match(line):
            logging.debug("RE_ANNOTATION match")
            logging.debug(f"{page_num_parsed=}")
            logging.debug(f"{page_num_offset=}")
            page_num_result = int(page_num_parsed) + page_num_offset
            logging.debug(f"{page_num_result=}")
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
            logging.debug(f"testing {is_roman=}")
            if page_num_result and is_roman:
                page_num_result = roman.toRoman(page_num_result).lower()
            fixed_line = smart_to_markdown(clean_pdf_ocr(line))
            logging.debug(f"{page_num_result} {prefix} {fixed_line}".strip())
            text_new.append(f"{page_num_result} {prefix} {fixed_line}".strip())

    return "\n".join(text_new)


def add_doi_isbn_info(text_joined: str) -> list[str]:
    """If ISBN/DOI, add metadata."""
    if DOI := _get_group_n(RE_DOI, text_joined, 0):
        logging.info(f"{DOI=}")
        text_new = get_bib_preamble(DOI)
    elif ISBN := _get_group_n(RE_ISBN, text_joined, 0):
        logging.info(f"{ISBN=}")
        text_new = get_bib_preamble(ISBN)
    else:
        logging.info("NO DOI or ISBN")
        text_new = []
    return text_new


def clean_pdf_ocr(text: str) -> str:
    """Remove OCR artifacts of junk hyphens and missing spaces.

    >>> clean_pdf_ocr('Do follow-ups for your coworker until lu-nch-bre-ak --- he sometimesloses focus.')
    'Do follow-ups for your coworker until lunch-break --- he sometimes loses focus.'
    """
    new_text = remove_junk_hyphens(text)
    new_text = restore_lost_spaces(new_text)

    return new_text


def remove_junk_hyphens(
    text: str,
    hyphen_RE: re.Pattern = re.compile(r"([a-zA-Z]{2,})(-)([a-zA-Z]{2,})"),
) -> str:
    """Remove junk hyphens from PDFs using pyenchant.

    Test if the constituent parts of hyphenated text are actual words.

    >>> remove_junk_hyphens('Do follow-ups for your coworker until lu-nch-bre-ak.')
    'Do follow-ups for your coworker until lunch-break.'
    """
    enchant_d = enchant.Dict("en_US")
    matches = hyphen_RE.findall(text)

    for match in matches:
        hyphenated_word = match[0] + match[1] + match[2]
        logging.debug(f"{hyphenated_word=}")
        logging.debug(f"{enchant_d.check(match[0])=}")
        logging.debug(f"{enchant_d.check(match[2])=}")
        if not (enchant_d.check(match[0]) and enchant_d.check(match[2])):
            replacement = match[0] + match[2]
            text = text.replace(hyphenated_word, replacement)

    return text


def restore_lost_spaces(text: str) -> str:
    """Restore lost spaces in PDFs using pyenchant.

    Replace words not in a dictionary with nearest suggestion, which
    is often two words separated by a space.

    >>> restore_lost_spaces('Excerpts sometimeslose their spaces.')
    'Excerpts sometimes lose their spaces.'
    """
    checker = enchant.checker.SpellChecker("en_US")
    logging.debug(text)
    checker.set_text(text)
    for error in checker:
        assert error.word is not None  # for typing
        logging.debug(f"{error.word}, {error.suggest()}")
        for suggestion in error.suggest():
            # Suggestion must be same as original with spaces removed
            if error.word.replace(" ", "") == suggestion.replace(" ", ""):
                error.replace(suggestion)
                break
    return str(checker.get_text())  # str() for typing


def _get_group_n(regex: re.Pattern, text: str, number: int) -> str | None:
    """Match function -- for typing."""
    match = regex.search(text)
    return match.group(number) if match else None


def process_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Process arguments."""
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
        "-t",
        "--trash",
        action="store_true",
        default=False,
        help="trash file after prompt for running extract-dictation",
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
        help="increase verbosity from critical though error, warning, info, and debug",
    )
    arg_parser.add_argument("--version", action="version", version="0.1")
    args = arg_parser.parse_args(argv)

    log_level = (logging.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
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


def main(args: argparse.Namespace | None = None) -> None:
    """Parse arguments, setup logging, and run."""
    if args is None:
        args = process_arguments(sys.argv[1:])

    logging.info("==================================")
    logging.info(f"{args=}")

    for file_name in args.file_names:
        text: str = ""
        if file_name.suffix == ".eml":
            with file_name.open("rb") as fp:
                msg: EmailMessage = BytesParser(policy=policy.default).parse(fp)
            text = ""
            if msg.is_multipart():
                for part in msg.walk():
                    if part.get_content_type() == "text/plain":
                        charset = part.get_content_charset(failobj="utf-8")
                        payload = part.get_payload(decode=True)
                        if isinstance(payload, bytes):
                            text += payload.decode(charset, "replace")
            else:
                charset = msg.get_content_charset(failobj="utf-8")
                payload = msg.get_payload(decode=True)
                if isinstance(payload, bytes):
                    text = payload.decode(charset, "replace")
            if not text:
                raise ValueError("No text content found in the email.")
            logging.debug(f"TEXT IS:\n ```{text}```")
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

            if args.trash or input("\nTrash file? 'y' for yes,\n") == "y":
                detrius = [
                    file_name.stem + ".eml",
                    file_name.stem + "-fixed.txt",
                    file_name.stem + ".mm",
                ]
                send2trash(detrius)
        else:
            print(new_text)


if __name__ == "__main__":
    main()
