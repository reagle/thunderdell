#!/usr/bin/env python3
"""Return bibliographic data for a given a arXiv number.

https://arxiv.org/help/api/index
https://arxiv.org/help/api/basics
http://export.arxiv.org/api/query?id_list=2001.08293
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import logging
import pprint
import sys

import requests
import xmltodict

ACCEPT_HEADERS = {
    "atom": "application/atom+xml",
}


def query(number: int, accept: str = "application/atom+xml") -> dict | bool:
    """Query the arXiv API with a given number and accept header."""
    logging.info(f"{accept=}")
    logging.info(f"{number=}")
    headers = {"Accept": accept}
    url = f"http://export.arxiv.org/api/query?id_list={number}"
    logging.info(f"{url=}")
    r = requests.get(url, headers=headers)
    requested_content_type = accept.split(";")[0]
    logging.debug(f"{r=}")
    returned_content_type = r.headers["content-type"]
    logging.info("{returned_content_type=}; {requested_content_type=}")
    if requested_content_type in returned_content_type:
        xml_bib = r.content
        return xmltodict.parse(xml_bib)["feed"]["entry"]

    else:
        return False


def parse_args(args: list[str] = sys.argv[1:]) -> argparse.Namespace:
    """Parse command-line arguments."""
    arg_parser = argparse.ArgumentParser(
        description="Given an arXiv number return bibliographic data."
    )
    # positional arguments
    arg_parser.add_argument("number", nargs="+")
    # optional arguments
    arg_parser.add_argument("-s", "--style", help="style of bibliography data")
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
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__} using Python {sys.version}",
    )
    return arg_parser.parse_args(args)


def main(args: argparse.Namespace | None = None) -> None:
    """Set up logging and execute script."""
    # Parse arguments if not provided
    if args is None:
        args = parse_args()

    log_level = (logging.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    if args.log_to_file:
        logging.basicConfig(
            filename="query_arxiv.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    # Determine accept header
    if args.style and args.style in ACCEPT_HEADERS:
        accept = ACCEPT_HEADERS[args.style]
    elif args.style:
        accept = args.style
    else:
        accept = ACCEPT_HEADERS["atom"]

    logging.info(f"accept = {accept} ")

    pprint.pprint(query(args.number[0], accept))


if __name__ == "__main__":
    args = parse_args()
    main(args)
