#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2015-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
""" Return bibliographic data for a given a arXiv number.

Thank you to arXiv for use of its open access interoperability
https://arxiv.org/help/api/index
https://arxiv.org/help/api/basics
http://export.arxiv.org/api/query?id_list=2001.08293
"""

import logging
import pprint
import sys

import requests
import xmltodict

log_level = 100  # default
critical = logging.critical
info = logging.info
debug = logging.debug

ACCEPT_HEADERS = {
    "atom": "application/atom+xml",
}


def query(number, accept="application/atom+xml"):
    """Query the number Web service; returns string"""

    info(f"{accept=}")
    info(f"{number=}")
    headers = {"Accept": accept}
    url = "http://export.arxiv.org/api/query?id_list=%s" % number
    info(f"{url=}")
    r = requests.get(url, headers=headers)
    requested_content_type = accept.split(";")[0]
    debug(f"{r=}")
    returned_content_type = r.headers["content-type"]
    info("{returned_content_type=}; {requested_content_type=}")
    if requested_content_type in returned_content_type:
        xml_bib = r.content
        return xmltodict.parse(xml_bib)["feed"]["entry"]

    else:
        return False


if "__main__" == __name__:
    import argparse

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
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"1.0 using Python {sys.version}",
    )
    args = arg_parser.parse_args()

    if args.verbose == 1:
        log_level = logging.CRITICAL
    elif args.verbose == 2:
        log_level = logging.INFO
    elif args.verbose >= 3:
        log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(
            filename="arxiv_query.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    accept = ACCEPT_HEADERS["atom"]
    if args.style:
        if args.style in ACCEPT_HEADERS:
            accept = ACCEPT_HEADERS[args.style]
        else:
            accept = args.style
    info("accept = %s " % accept)

    pprint.pprint(query(args.number[0], accept))
