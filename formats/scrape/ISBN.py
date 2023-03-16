#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
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

from change_case import sentence_case

from .default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


class ScrapeISBN(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping ISBN;", end="\n")
        self.url = url
        self.comment = comment

    def get_biblio(self):
        import isbn_query

        info(f"url = {self.url}")
        json_bib = isbn_query.query(self.url)
        info(f"json_bib = '{json_bib}'")
        biblio = {
            "permalink": self.url,
            "excerpt": "",
            "comment": self.comment,
        }
        info("### json_bib.items()")
        for key, value in list(json_bib.items()):
            info(f"key = '{key}'")
            if key.startswith("subject"):
                continue
            info(
                "key = '%s' value = '%s' type(value) = '%s'\n"
                % (key, value, type(value))
            )
            if value in (None, [], ""):
                pass
            elif key == "author":
                biblio["author"] = self.get_author(json_bib)
            elif key == "year":
                biblio["date"] = json_bib["year"]
            elif key == "isbn":
                biblio["isbn"] = json_bib["isbn"]
            elif key == "pageCount":
                biblio["pages"] = json_bib["pageCount"]
            elif key == "publisher":
                biblio["publisher"] = json_bib["publisher"]
            elif key == "city":
                biblio["address"] = json_bib["city"]
            elif key == "url":
                biblio["url"] = json_bib["url"]
                biblio["permalink"] = json_bib["url"]
            else:
                biblio[key] = json_bib[key]
        if "title" in json_bib:
            title = biblio["title"].replace(": ", ": ")
            biblio["title"] = sentence_case(title)
            if "subtitle" in json_bib:
                biblio["subtitle"] = sentence_case(json_bib["subtitle"])
        else:
            biblio["title"] = "UNKNOWN"
        return biblio

    def get_author(self, bib_dict):
        names = "UNKNOWN"
        if "author" in bib_dict:
            info(f"{bib_dict['author']=}")
            names = bib_dict["author"]
        return names

    def get_date(self, bib_dict):
        # "issued":{"date-parts":[[2007,3]]}
        date_parts = bib_dict["issued"]["date-parts"][0]
        info(f"{date_parts=}")
        if len(date_parts) == 3:
            year, month, day = date_parts
            date = "%d%02d%02d" % (int(year), int(month), int(day))
        elif len(date_parts) == 2:
            year, month = date_parts
            date = "%d%02d" % (int(year), int(month))
        elif len(date_parts) == 1:
            date = str(date_parts[0])
        else:
            date = "0000"
        info(f"{date=}")
        return date
