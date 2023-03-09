#!/usr/bin/env python3
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

import logging

import arxiv_query
from change_case import sentence_case

from .scrape_default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


class ScrapeArXiv(ScrapeDefault):
    """Use arXiv API to get biblio data.
    Thank you to arXiv for use of its open access interoperability
    https://arxiv.org/help/api/index
    https://arxiv.org/help/api/basics
    """

    def __init__(self, url, comment):
        print("Scraping arXiv;", end="\n")
        self.identifier = url[6:]
        self.url = f"https://arxiv.org/abs/{self.identifier}"
        self.comment = comment

    def get_biblio(self):
        info(f"url = {self.url}")
        dict_bib = arxiv_query.query(self.identifier)
        info(f"{dict_bib=}")
        biblio = {
            "entry_type": "report",
            "permalink": self.url,
            "excerpt": "",
            "organization": "arXiv",
            "identifier": self.identifier,
            "comment": self.comment,
        }
        for key, value in list(dict_bib.items()):
            info(f"{key=} {value=} {type(value)=}")
            if value in (None, [], ""):
                pass
            elif key == "author":
                biblio["author"] = self.get_author(dict_bib)
            elif key == "published":
                biblio["date"] = self.get_date(dict_bib)
            elif key == "URL":
                biblio["permalink"] = biblio["url"] = dict_bib["URL"]
            else:
                biblio[key] = dict_bib[key]
        if "title" not in dict_bib:
            biblio["title"] = "UNKNOWN"
        else:
            biblio["title"] = sentence_case(" ".join(biblio["title"].split()))
        info(f"{biblio=}")
        return biblio

    def get_author(self, bib_dict):
        names = "UNKNOWN"
        if "author" in bib_dict:
            names = [author["name"] for author in bib_dict["author"]]
        return ", ".join(names)

    def get_date(self, bib_dict):
        date = bib_dict["published"][0:10].replace("-", "")
        info(f"{date=}")
        return date
