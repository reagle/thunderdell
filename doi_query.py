#!/usr/bin/env python3
"""Return CrossRef bibliographic data for a given a DOI.

http://www.crossref.org/CrossTech/2011/11/turning_dois_into_formatted_ci.html 
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import json
import logging
import pprint
import sys

import requests

log_level = 100  # default
critical = logging.critical
info = logging.info
debug = logging.debug

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
    """Query the DOI Web service; returns string"""

    info(f"{accept=}")
    info(f"{doi=}")
    headers = {"Accept": accept}
    url = "http://dx.doi.org/%s" % doi
    info(f"{url=}")
    r = requests.get(url, headers=headers)
    debug(f"{r=} {r.content=}")
    returned_content_type = r.headers["content-type"].split("; ")[0]
    if returned_content_type in ACCEPTABLE_TYPES:
        json_bib = json.loads(r.content)
        info(f"{json_bib=}")
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


if __name__ == "__main__":
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
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__} using Python {sys.version}",
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
            filename="doi_query.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    accept = ACCEPT_HEADERS["json"]
    if args.style:
        if args.style in ACCEPT_HEADERS:
            accept = ACCEPT_HEADERS[args.style]
        else:
            accept = args.style
    info("accept = %s " % accept)

    pprint.pprint(query(args.DOI[0], accept))
