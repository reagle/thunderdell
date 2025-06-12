#!/usr/bin/env python3
"""Log and annotate a URL to loggers with data from scraper.

Log and annotate a URL to loggers (e.g., mindmap, blogs) with meta/bibliographic data about the URL from a scraper.

https://reagle.org/joseph/2009/01/thunderdell.html
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

# TODO
# - archive URLs to f/old/`r=`

import argparse
import logging
import re
import sys
import time
import urllib.parse
from collections.abc import Callable

from thunderdell.biblio import fields as bf
from thunderdell.biblio.keywords import LIST_OF_KEYSHORTCUTS
from thunderdell.formats import (
    ScrapeDefault,
    log2console,
    log2goatee,
    log2mm,
    log2nifty,
    log2opencodex,
    log2work,
)
from thunderdell.utils.web import canonicalize_url

NOW = time.localtime()
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"

#######################################
# Dispatchers
#######################################


def get_scraper(url: str, comment: str) -> ScrapeDefault:
    """Use the URL to specify a screen scraper, e.g.,.

    busy.py c .test https://en.wikipedia.org/wiki/Joseph_M._Reagle_Jr.
    busy.py c .test https://meta.wikimedia.org/wiki/Steward_requests/Bot_status
    busy.py c .test https://old.reddit.com/r/Python/comments/ojze8e/lets_write_a_toy_emulator_in_python/
    busy.py c .test https://twitter.com/moiragweigel/status/1415393653678395393
    busy.py c .test https://twitter.com/vaurorapub/status/1415394419688181761
    busy.py c .test https://ohai.social/@0xadada@freeradical.zone/109473390214845816
    busy.py c .test doi:10.1177/1097184x15613831
    busy.py c .test isbn:9780860917137
    busy.py c .test arxiv:2001.08293
    """
    from importlib import import_module

    url = urllib.parse.unquote(url)
    url = canonicalize_url(url)
    logging.info(f"url = '{url}'")

    # Structured dispatch tables with import metadata
    url_scrapers = (
        ("doi:", ("thunderdell.formats", "ScrapeDOI")),
        ("isbn:", ("thunderdell.formats", "ScrapeISBN")),
        ("arxiv:", ("thunderdell.formats", "ScrapeArXiv")),
        ("https://en.wikipedia.org/w", ("thunderdell.formats", "ScrapeENWP")),
        ("https://marc.info/", ("thunderdell.formats", "ScrapeMARC")),
        ("https://meta.wikimedia.org/w", ("thunderdell.formats", "ScrapeWMMeta")),
        ("https://ohai.social/", ("thunderdell.formats", "ScrapeMastodon")),
        ("https://x.com/", ("thunderdell.formats", "ScrapeTwitter")),
        ("https://twitter.com/", ("thunderdell.formats", "ScrapeTwitter")),
        ("https://www.nytimes.com/", ("thunderdell.formats", "ScrapeNYT")),
        ("https://www.reddit.com/", ("thunderdell.formats", "ScrapeReddit")),
    )

    # Iterate through the dispatch table and check URL prefix and dynamically import
    # This prevents unnecessary imports and slowdowns
    for prefix, (module_name, class_name) in url_scrapers:
        if url.lower().startswith(prefix):
            logging.info(f"Using {class_name} for {prefix} URL")
            # Import the module dynamically
            module = import_module(module_name)
            # Get the class from the module
            scraper_class = getattr(module, class_name)
            return scraper_class(url, comment)

    return ScrapeDefault(url, comment)


def get_logger(text: str) -> tuple[Callable, dict]:
    """Given the argument return a function and parameters."""
    # tags must be prefixed by dot; URL no longer required
    LOG_REGEX = re.compile(
        r"(?P<scheme>\w) (?P<tags>(\.\w+ )+)?"
        + r"(?P<url>(arxiv|doi|isbn|http|file)\S* ?)?(?P<comment>.*)",
        re.IGNORECASE,
    )

    if LOG_REGEX.match(text):
        params = {}
        if (match := LOG_REGEX.match(text)) is not None:
            params = match.groupdict()
        if params.get("tags"):
            params["tags"] = params["tags"].replace(".", "")
        if params.get("url"):
            # unescape zshell safe pasting/bracketing
            params["url"] = (
                params["url"]
                .replace(r"\#", "#")
                .replace(r"\&", "&")
                .replace(r"\?", "?")
                .replace(r"\=", "=")
            )

        logging.info(f"params = '{params}'")
        function_map = {
            "n": log2nifty,
            "j": log2work,
            "m": log2mm,
            "c": log2console,
            "o": log2opencodex,
            "g": log2goatee,
        }
        function = function_map.get(params["scheme"], None)

        if function:
            return function, params
        else:
            print_usage(f"""Sorry, unknown scheme: '{params["scheme"]}'.""")
    else:
        print_usage(f"Sorry, I can't parse the argument: '{text}'.")
    sys.exit()


#######################################
# Miscellaneous
#######################################

DESCRIPTION = DESCRIPTION = "Given a URL, tag, scrape, and log it."

EPILOG = """
  blog codex:    b o [pra|soc|tec] TAGS URL|DOI|ISBN TITLE. BODY
  blog goatee:   b g URL|DOI|ISBN TITLE. BODY
  mindmap:       b m TAGS URL|DOI|ISBN ABSTRACT
  nifty:         b n TAGS URL|DOI|ISBN COMMENT
  work plan:     b j TAGS URL|DOI|ISBN COMMENT
  console:       b c TAGS URL|DOI|ISBN COMMENT
    's. ' begins summary
    '> '  begins excerpt (as does a character)
    ', '  begins paraphrase
    '-- ' begins note
    'key=value' for metadata; e.g.,
      au=John Smith ti=Greatet Book Ever d=2001 cb=Blogger.com et=cb
      Entry types (et=cb) values must be typed as container shortcut.
"""


def print_usage(message: str) -> None:
    print(message)
    print(DESCRIPTION)
    print(EPILOG)


def main():
    import sys

    arg_parser = argparse.ArgumentParser(
        prog="b",
        usage="%(prog)s [options] [URL] logger [keyword] [text]",
        description=DESCRIPTION,
        epilog=EPILOG,
        formatter_class=argparse.RawTextHelpFormatter,
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
        help="increase verbosity from critical though error, warning, info, and debug",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__} using Python {sys.version}",
    )
    args = arg_parser.parse_args(sys.argv[1:])

    log_level = (logging.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
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

    if args.keyword_shortcuts:
        for dictionary in LIST_OF_KEYSHORTCUTS:
            print(pretty_tabulate_dict(dictionary, 4))
        sys.exit()
    if args.container_shortcuts:
        print(pretty_tabulate_dict(bf.CSL_SHORTCUTS, 4))
        sys.exit()

    logger, params = get_logger(" ".join(args.text))
    logging.info("-------------------------------------------------------")
    logging.info("-------------------------------------------------------")
    logging.info(f"{logger=}")
    logging.info(f"{params=}")
    comment = "" if not params["comment"] else params["comment"]
    if params["url"]:  # not all log2work entries have urls
        scraper = get_scraper(params["url"].strip(), comment)
        biblio = scraper.get_biblio()
    else:
        biblio = {"title": "", "url": "", "comment": comment}
    biblio["tags"] = params["tags"]
    logging.info(f"{biblio=}")
    logger(args, biblio)


if __name__ == "__main__":
    main()
