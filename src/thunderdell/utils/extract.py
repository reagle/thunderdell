"""Extraction utilities.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging

import requests

from thunderdell.formats.scrape.DOI import ScrapeDOI
from thunderdell.formats.scrape.ISBN import ScrapeISBN
from thunderdell.formats.log.console import log2console


class args:
    """Initialize args."""

    publish = False  # don't tweet at this level


def get_bib_preamble(token: str) -> list[str]:
    """Call out to get and format biblio information using ISBN/DOI APIs."""
    logging.info(f"{token=}")
    scrape_token = ScrapeDOI if token.startswith("10") else ScrapeISBN
    biblio = scrape_token(f"{token}", "").get_biblio()
    biblio["tags"] = ""
    result = [log2console(args, biblio).strip()]
    return result
