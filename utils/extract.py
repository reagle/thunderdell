"""Extraction utilities.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging

import formats

# mnemonic: CEWID
critical = logging.critical  # 50
error = logging.error  # 40
warn = logging.warn  # 30
info = logging.info  # 20
debug = logging.debug  # 10
excpt = logging.exception  # 40, includes exception info


class args:
    publish = False  # don't tweet at this level


def get_bib_preamble(token):
    """Call out to format.ISBN/DOI APIs and get biblio information"""
    info(f"{token=}")
    if token.startswith("10"):
        scrape_token = formats.ScrapeDOI
    else:
        scrape_token = formats.ScrapeISBN
    biblio = scrape_token(f"{token}", "").get_biblio()
    biblio["tags"] = ""
    result = [formats.log2console(args, biblio).strip()]
    return result
