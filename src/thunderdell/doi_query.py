#!/usr/bin/env python3
"""Return CrossRef bibliographic data for a given a DOI.

http://www.crossref.org/CrossTech/2011/11/turning_dois_into_formatted_ci.html
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import json
import logging as log
import pprint
import sys

import requests

log_level = 100  # default
log.critical = log.critical
log.info = log.info
log.debug = log.debug

# https://citation.crosscite.org/docs.html
# Types available to output to the CLI
ACCEPT_HEADERS = {
    "json": "application/citeproc+json",
    "bibtex": "text/bibliography;style=bibtex",
}

# Types I'm prepared to parse
ACCEPTABLE_TYPES = (
    "application/vnd.citationstyles.csl+json",
    "application/citeproc+json",
)


def query(doi, accept="application/citeproc+json"):
    """Query the DOI Web service; returns string."""
    log.info(f"{accept=}")
    log.info(f"{doi=}")
    headers = {"Accept": accept}
    url = f"http://dx.doi.org/{doi}"
    log.info(f"{url=}")
    r = requests.get(url, headers=headers)
    log.debug(f"{r=} {r.content=}")
    returned_content_type = r.headers["content-type"].split(";")[0].strip()
    if returned_content_type in ACCEPTABLE_TYPES:
        json_bib = json.loads(r.content)
        log.info(f"{json_bib=}")
        return json_bib
    else:
        raise RuntimeError(
            "DOI service returned unknown type:\n"
            + f"{returned_content_type=}"
            + f"{r.content.splitlines()[0:10]}"
        )
        # as part of failure, could return
        # curl -LH "Accept: text/x-bibliography;"
        #          " style=apa" https://doi.org/10.26300/spsf-tc23


def main():
    import argparse
    arg_parser = argparse.ArgumentParser(
        description="Given a doi return bibliographic data."
    )
    # positional arguments
    arg_parser.add_argument("DOI", nargs="+")
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
    args = arg_parser.parse_args()

    log_level = (log.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    if args.log_to_file:
        log.basicConfig(
            filename="doi_query.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        log.basicConfig(level=log_level, format=LOG_FORMAT)

    accept = ACCEPT_HEADERS["json"]
    if args.style:
        accept = ACCEPT_HEADERS.get(args.style, args.style)
    log.info(f"accept = {accept} ")

    pprint.pprint(query(args.DOI[0], accept))

if __name__ == "__main__":
    main()
