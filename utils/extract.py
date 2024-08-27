"""Extraction utilities.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging as log

import formats


class args:
    """Initialize args."""

    publish = False  # don't tweet at this level


def get_bib_preamble(token):
    """Call out to get and format biblio information using ISBN/DOI APIs."""
    log.info(f"{token=}")
    scrape_token = formats.ScrapeDOI if token.startswith("10") else formats.ScrapeISBN
    biblio = scrape_token(f"{token}", "").get_biblio()
    biblio["tags"] = ""
    result = [formats.log2console(args, biblio).strip()]
    return result
