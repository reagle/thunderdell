#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
"""
The InstaPaper app can export highlights and notes to a file.
This script processes this format and transforms it into
the (ad-hoc) format accepted by `extract-dictation.py`.
"""

import argparse  # http://docs.python.org/dev/library/argparse.html
import logging
import re
import sys
import webbrowser
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html

import busy

HOME = str(Path("~").expanduser())
sys.path.insert(0, f"{HOME}/bin/td")

debug = logging.debug
info = logging.info
warning = logging.warning
error = logging.error
critical = logging.critical
exception = logging.exception


def main(argv):
    """Process arguments"""
    # https://docs.python.org/3/library/argparse.html
    arg_parser = argparse.ArgumentParser(
        description="""Format Instapaper annotations for use with
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
    arg_parser.add_argument("file_names", nargs="+", metavar="FILE_NAMES")
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
            filename="extract-instapaper.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    return args


def process_files(args, file_names):
    URL_RE = re.compile(r"# \[.*\]\((.*)\)")
    for file_name in file_names:
        info(f"{file_name=}")
        with open(file_name) as f:
            lines = f.readlines()
            first_line = lines[0]
            info(f"{first_line=}")
            comment = "\n" + "".join(lines).replace("\n\u200b\n", "").replace(
                "\n\n", "\n"
            )
            info(f"{comment=}")
            url = URL_RE.match(first_line).groups()[0]
            info(f"{url=}")
            webbrowser.open(url)
            params = {"scheme": "c", "url": url, "comment": ""}
            scraper = busy.get_scraper(params["url"].strip(), comment)
            biblio = scraper.get_biblio()
            biblio["tags"] = "misc"  # default keyword
            del biblio["excerpt"]  # no need for auto excerpt
            busy.log2mm(args, biblio)


if __name__ == "__main__":
    args = main(sys.argv[1:])
    critical("==================================")
    critical(f"{args=}")
    process_files(args, args.file_names)
