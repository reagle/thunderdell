#!/usr/bin/env python3
"""Process Kindle email export into format accepted by `extract_dictation.py`."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import logging
import re
import subprocess
import sys
from email import policy
from email.parser import BytesParser
from pathlib import Path

from bs4 import BeautifulSoup  # type: ignore

from thunderdell.change_case import title_case
from thunderdell.extract_dictation import create_mm
from thunderdell.utils.extract import get_bib_preamble
from thunderdell.utils.text import smart_to_markdown


def process_email(file_name: Path) -> str:
    """Process parts of a MIME message stored in file."""
    with file_name.open(mode="rb") as fp:
        msg = BytesParser(policy=policy.default).parse(fp)
        for part in msg.walk():
            msg_content_type = part.get_content_subtype()
            logging.debug(f"{part=}, {msg_content_type=}")
            if msg_content_type == "html":
                logging.debug(f"part is HTML: {msg_content_type}")
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

    if match := RE_COLOR_PAGE.search(content):
        _, pagination_type, _ = match.groupdict().values()
    else:
        pagination_type = ""

    if isbn_match := RE_ISBN.search(content):
        ISBN = isbn_match.group(0)
        logging.info(f"{ISBN=}")
        text_new = get_bib_preamble(ISBN)

    text_new.append("edition = Kindle")
    if pagination_type == "Location":
        text_new.append("pagination = location")

    soup = BeautifulSoup(content, "html.parser")
    divs = soup.find_all("div")
    for div in divs:
        logging.debug(f"{div=}")
        if "noteHeading" in str(div):
            try:
                if color_page_match := RE_COLOR_PAGE.search(str(div)):
                    color, _, page = color_page_match.groupdict().values()
                else:
                    color = "black"
            except AttributeError:
                color = "black"
        elif "noteText" in str(div):
            note = smart_to_markdown(str(div)[27:-7])
            match color:
                case "blue":
                    note = title_case(note)
                    text_new.append(f"section. {note}")
                case "yellow":
                    text_new.append(f"{page} excerpt. {note}")
                case "black":
                    text_new.append(f"-- {note}")

    return "\n".join(text_new)


def process_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Process command line arguments."""
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
        "-V",
        "--verbose",
        action="count",
        default=0,
        help="increase verbosity from critical though error, warning, info, and debug",
    )
    arg_parser.add_argument("--version", action="version", version="0.1")

    args = arg_parser.parse_args(argv if argv is not None else sys.argv[1:])

    log_level = max(logging.CRITICAL - (args.verbose * 10), logging.DEBUG)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
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


def main(args: argparse.Namespace | None = None) -> None:
    """Parse arguments, setup logging, and run."""
    if args is None:
        args = process_arguments(sys.argv[1:])
    logging.info("==================================")
    logging.debug(f"{args=}")

    for file_name in args.file_names:
        logging.debug(f"{file_name=}")
        fixed_fn = file_name.with_stem(file_name.stem + "-fixed").with_suffix(".txt")

        match file_name.suffix:
            case ".eml":
                logging.info(f"processing {file_name} as eml")
                html_content = process_email(file_name)
            case ".html":
                logging.info(f"processing {file_name} as html")
                html_content = file_name.read_text()
            case _:
                raise OSError(
                    f"Do not recognize file type: {file_name} {file_name.suffix}."
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
                args.publish = user_input == "yp"
                mm_file_name = file_name.with_suffix(".mm")
                edited_text = fixed_fn.read_text()
                create_mm(args, edited_text, mm_file_name)
                subprocess.call(["open", "-a", "Freeplane.app", mm_file_name])
        else:
            print(new_text)


if __name__ == "__main__":
    main()
