#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""
BusySponge, by Joseph Reagle http://reagle.org/joseph/

BusySponge permits me to easily log and annotate a URL to various loggers
(e.g., mindmap, blogs) with meta/bibliographic data about the URL from
a scraping.

https://github.com/reagle/thunderdell
"""

# TODO
# - archive URLs to f/old/`r=`

import argparse
import logging
import re
import sys
import time

from biblio import fields as bf
from biblio.keywords import LIST_OF_KEYSHORTCUTS
from formats import (
    log2console,
    log2goatee,
    log2mm,
    log2nifty,
    log2opencodex,
    log2work,
)
from formats import (
    ScrapeDefault,
    ScrapeISBN,
    ScrapeDOI,
    ScrapeMARC,
    ScrapeENWP,
    ScrapeWMMeta,
    ScrapeTwitter,
    ScrapeReddit,
)
from utils.text import pretty_tabulate_dict

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"

#######################################
# Dispatchers
#######################################


def get_scraper(url, comment):
    """
    Use the URL to specify a screenscraper.
    """

    url = re.sub(  # use canonical reddit domain
        r"(https?://(old|i)\.reddit.com/(.*)(\.compact)?)",
        r"https://www.reddit.com/\3",
        url,
    )
    info(f"url = '{url}'")
    if url.lower().startswith("doi:"):
        return ScrapeDOI(url, comment)
    elif url.lower().startswith("isbn:"):
        return ScrapeISBN(url, comment)
    else:
        host_path = url.split("//")[1]
        dispatch_scraper = (
            ("en.wikipedia.org/w", ScrapeENWP),
            ("meta.wikimedia.org/w", ScrapeWMMeta),
            ("marc.info/", ScrapeMARC),
            ("twitter.com/", ScrapeTwitter),
            ("www.reddit.com/", ScrapeReddit),
            ("", ScrapeDefault),  # default: make sure last
        )

        for prefix, scraper in dispatch_scraper:
            if host_path.startswith(prefix):
                info(f"scrape = {scraper} ")
                return scraper(url, comment)  # creates instance


def get_logger(text):
    """
    Given the argument return a function and parameters.
    """

    # tags must be prefixed by dot; URL no longer required
    LOG_REGEX = re.compile(
        r"(?P<scheme>\w) (?P<tags>(\.\w+ )+)?"
        r"(?P<url>(doi|isbn|http)\S* ?)?(?P<comment>.*)",
        re.IGNORECASE,
    )

    if LOG_REGEX.match(text):
        params = LOG_REGEX.match(text).groupdict()
        if "tags" in params and params["tags"]:
            params["tags"] = params["tags"].replace(".", "")
        if "url" in params and params["url"]:
            # unescape zshell safe pasting/bracketing
            params["url"] = (
                params["url"]
                .replace(r"\#", "#")
                .replace(r"\&", "&")
                .replace(r"\?", "?")
                .replace(r"\=", "=")
            )
        info(f"params = '{params}'")
        function = None
        if params["scheme"] == "n":
            function = log2nifty
        elif params["scheme"] == "j":
            function = log2work
        elif params["scheme"] == "m":
            function = log2mm
        elif params["scheme"] == "c":
            function = log2console
        elif params["scheme"] == "o":
            function = log2opencodex
        elif params["scheme"] == "g":
            function = log2goatee
        if function:
            return function, params
        else:
            print_usage("Sorry, unknown scheme: '%s'." % params["scheme"])
    else:
        print_usage(f"Sorry, I can't parse the argument: '{text}'.")
    sys.exit()


#######################################
# Miscellaneous
#######################################

DESCRIPTION = f"""
blog codex:    b o [pra|soc|tec] TAGS URL|DOI TITLE. BODY
blog goatee:   b g URL|DOI TITLE. BODY
mindmap:       b m TAGS URL|DOI ABSTRACT
nifty:         b n TAGS URL|DOI COMMENT
work plan:     b j TAGS URL|DOI COMMENT
console:       b c TAGS URL|DOI COMMENT
  's. ' begins summary
  '> '  begins excerpt (as does a character)
  ', '  begins paraphrase
  '-- ' begins note
  'key=value' for metadata; e.g.,
    au=John Smith ti=Greatet Book Ever d=2001 cb=Blogger.com et=cb
    Entry types (et=cb) values must be typed as container shortcut.
"""


def print_usage(message):
    print(message)
    print(DESCRIPTION)


# Check to see if the script is executing as main.
if __name__ == "__main__":

    arg_parser = argparse.ArgumentParser(
        prog="b",
        usage="%(prog)s [options] [URL] logger [keyword] [text]",
        description=DESCRIPTION,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    arg_parser.add_argument(
        "-T",
        "--tests",
        action="store_true",
        default=False,
        help="run doc tests",
    )
    arg_parser.add_argument(
        "-C",
        "--container-shortcuts",
        action="store_true",
        default=False,
        help="show container shortcuts (cb, cw, cf, ...)",
    )
    arg_parser.add_argument(
        "-K",
        "--keyword-shortcuts",
        action="store_true",
        default=False,
        help="show keyword shortcuts  (adv, fem, wp, ...)",
    )
    arg_parser.add_argument(
        "-p",
        "--publish",
        action="store_true",
        default=False,
        help="publish to social networks",
    )
    arg_parser.add_argument("text", nargs="*")
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
    log_level = logging.ERROR  # 40

    if args.verbose == 1:
        log_level = logging.WARNING  # 30
    elif args.verbose == 2:
        log_level = logging.INFO  # 20
    elif args.verbose >= 3:
        log_level = logging.DEBUG  # 10
    LOG_FORMAT = "%(levelname).3s %(funcName).5s: %(message)s"
    if args.log_to_file:
        print("logging to file")
        logging.basicConfig(
            filename="busy.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    if args.tests:
        print("Running doctests")
        import doctest

        doctest.testmod()
        sys.exit()
    if args.keyword_shortcuts:
        for dictionary in LIST_OF_KEYSHORTCUTS:
            pretty_tabulate_dict(dictionary, 3)
        sys.exit()
    if args.container_shortcuts:
        pretty_tabulate_dict(bf.CSL_SHORTCUTS, 3)
        sys.exit()

    logger, params = get_logger(" ".join(args.text))
    info("-------------------------------------------------------")
    info("-------------------------------------------------------")
    info(f"{logger=}")
    info(f"{params=}")
    comment = "" if not params["comment"] else params["comment"]
    if params["url"]:  # not all log2work entries have urls
        scraper = get_scraper(params["url"].strip(), comment)
        biblio = scraper.get_biblio()
    else:
        biblio = {"title": "", "url": "", "comment": comment}
    biblio["tags"] = params["tags"]
    info(f"{biblio=}")
    logger(args, biblio)
else:  # imported as module

    class args:
        publish = False
