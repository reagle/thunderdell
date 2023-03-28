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
import time

import pendulum as pm

from change_case import sentence_case
from utils.web import get_JSON
from utils.web_api_tokens import NYT_APP_KEY

from .default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


class ScrapeNYT(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping NYT", end="\n")
        ScrapeDefault.__init__(self, url, comment)
        api_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
        query_url = f"""{api_url}?fq=web_url:(\"{url}\")&api-key={NYT_APP_KEY}"""
        print(f"{query_url=}")
        self.json = get_JSON(f"{query_url}")["response"]["docs"][0]

    def get_biblio(self):
        biblio = {
            "author": self.get_author(),
            "title": self.get_title(),
            "c_newspaper": "New York Times",
            "date": self.get_date(),
            "permalink": self.url,
            "excerpt": self.get_excerpt(),
            "comment": self.comment,
            "url": self.url,
        }
        return biblio

    def get_author(self):
        author = self.json["byline"]["original"]
        author = author.removeprefix("By ").replace(" and ", ", ")
        return author.strip()
        # TODO: multiple authors

    def get_title(self):
        headline = self.json["headline"]["main"]
        title = sentence_case(headline)
        return title.strip()

    def get_date(self):
        pub_date = self.json["pub_date"]
        date = pm.parse(pub_date, strict=False).strftime("%Y-%m-%d")
        return date

    def get_excerpt(self):
        excerpt = self.json["abstract"]
        return excerpt.strip()
