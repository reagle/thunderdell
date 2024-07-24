#!/usr/bin/env python3
"""Process Kindle email export into format accepted by `extract_dictation.py`."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import logging as log
import re
import subprocess
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup  # type:ignore

import change_case
from extract_dictation import create_mm
from utils.extract import get_bib_preamble
from utils.text import smart_to_markdown


def process_email(file_name: Path) -> str:
    """Process parts of a MIME message stored in file."""

    with file_name.open(mode="rb") as fp:
        msg = BytesParser(policy=policy.default).parse(fp)
        for part in msg.walk():
            msg_content_type = part.get_content_subtype()
            log.debug(f"{part=}, {msg_content_type=}")
            if msg_content_type == "html":
                log.debug(f"part is HTML: {msg_content_type}")
                charset = part.get_content_charset(failobj="utf-8")
                content = part.get_payload(decode=True).decode(charset, "replace")  # type: ignore
                return content
        raise Exception("There's no HTML attachment to process.")


def process_html(content: str) -> str:
    """Process text for annotation kind, color, and page number."""

    RE_ISBN = re.compile(r"978(?:-?\d){10}")

    RE_COLOR_PAGE = re.compile(
        r"(?P<color>yellow|blue)</span>\) .*? (?P<type>Page|Location)"
        + r" (?P<page>[\dcdilmxv]+)",
    )
    color = ""
    page = ""
    text_new = []
    _, pagination_type, _ = RE_COLOR_PAGE.search(content).groupdict().values()

    if RE_ISBN.search(content):
        ISBN = RE_ISBN.search(content).group(0)
        log.info(f"{ISBN=}")
        text_new = get_bib_preamble(ISBN)
    text_new.append("edition = Kindle")
    if pagination_type == "Location":
        text_new.append("pagination = location")

    soup = BeautifulSoup(content, "html.parser")
    divs = soup.findAll("div")
    for div in divs:
        log.debug(f"{div=}")
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


def parse_args(argv: list) -> argparse.Namespace:
    """Process arguments"""
    # https://docs.python.org/3/library/argparse.html
    """Process arguments"""
    # https://docs.python.org/3/library/argparse.html
    arg_parser = argparse.ArgumentParser(
        description="""Format Kindle annotations (sent via HTML notes shared in
        *tablet* Kindle app) for use with dictation-extract.py in
        https://github.com/reagle/thunderdell
        """
    )

    # positional arguments
    arg_parser.add_argument("file_names", nargs="*", type=Path, metavar="FILE_NAMES")
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

    log_level = (log.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    if args.log_to_file:
        log.basicConfig(
            filename="extract-kindle.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        log.basicConfig(level=log_level, format=LOG_FORMAT)

    return args


if __name__ == "__main__":
    args = parse_args(sys.argv[1:])
    log.info("==================================")
    log.debug(f"{args=}")

    file_names = args.file_names
    for file_name in file_names:
        log.debug(f"{file_name=}")
        fixed_fn = file_name.with_stem(file_name.stem + "-fixed").with_suffix(".txt")
        if file_name.suffix == ".eml":
            log.info(f"processing {file_name} as eml")
            html_content = process_email(file_name)
        elif file_name.suffix == ".html":
            log.info(f"processing {file_name} as html")
            html_content = file_name.read_text()
        else:
            raise OSError(
                "Do not recognize file type: {file_name} {splitext(file_name)[1]}."
            )

        new_text = process_html(html_content)

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
