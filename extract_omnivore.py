#!/usr/bin/env python3
"""Process Omnivore.app export into format accepted by `extract_dictation.py`."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import logging
import re
import sys
import webbrowser
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html

from send2trash import send2trash  # type: ignore

import busy

HOME = Path.home()

# mnemonic: CEWID
critical = logging.critical  # 50
error = logging.error  # 40
warn = logging.warn  # 30
info = logging.info  # 20
dbg = logging.debug  # 10
excpt = logging.exception  # 40, includes exception info


def main(argv: list[str]) -> argparse.Namespace:
    """Process arguments"""
    # https://docs.python.org/3/library/argparse.html
    arg_parser = argparse.ArgumentParser(
        description="""Format Omnivore.app annotations for use with
        dictation-extract.py in
            https://github.com/reagle/thunderdell
        """
    )
    arg_parser.add_argument(
        "-p",
        "--publish",
        action="store_true",
        default=False,
        help="publish to social networks (can also `-p` in editor)",
    )

    # positional arguments
    arg_parser.add_argument("file_names", nargs="+", type=Path, metavar="FILE_NAMES")
    # optional arguments
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

    log_level = (logging.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(
            filename="extract-omnivore.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    return args


def process_files(args: argparse.Namespace, file_paths: list[Path]) -> None:
    """
    Process files for highlights and annotations using console annotation syntax:
    .summary
    excerpt
    , annotation
    """
    URL_RE = re.compile(r"https?://\S+")
    for file_path in file_paths:
        info(f"{file_path=}")
        url_found = False
        url = ""
        comment = [""]  # initial line for summary

        for line in file_path.read_text().splitlines():
            line = line.strip()

            if not url_found:
                if match := URL_RE.search(line):
                    url = match.group()
                    url_found = True
                    print(f"URL found in {file_path}: {url}")
                continue

            if not line:
                continue

            # lines are presumed to be excerpts, so remove blockquote symbol
            if line.startswith("> "):
                comment.append(line[2:].strip())
            # else, mark with comma as it's a user annotation
            else:
                comment.append(f", {line}")

        text = "\n".join(comment)

        webbrowser.open(url)
        params = {"scheme": "c", "url": url, "comment": ""}
        scraper = busy.get_scraper(params["url"].strip(), text)
        biblio = scraper.get_biblio()
        biblio["tags"] = "misc"  # default keyword
        del biblio["excerpt"]  # no need for auto excerpt
        busy.log2mm(args, biblio)


if __name__ == "__main__":
    args = main(sys.argv[1:])
    critical("==================================")
    critical(f"{args=}")
    process_files(args, args.file_names)
    user_input = input("\nTrash processed file? 'y' for yes,\n")
    if user_input == "y":
        send2trash(args.file_names)
