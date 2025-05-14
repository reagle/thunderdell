"""Scrape NYTimes bibliographic data using their API.

Use the API because NYTimes blocks some bots.

As of 2023-03-30 the following seems to work without the API
but this could change, so continue with API.

    AGENT_HEADERS = {"User-Agent": "curl/7.54"}

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import time

import arrow

from thunderdell.change_case import sentence_case
from thunderdell.utils import web as uw
from thunderdell.utils.web import get_JSON

from .default import ScrapeDefault

NOW = time.localtime()

NYT_APP_KEY = uw.get_credential("NYT_APP_KEY")


class ScrapeNYT(ScrapeDefault):
    """Scraper for NYT."""

    def __init__(self, url, comment):
        print("Scraping NYT", end="\n")
        ScrapeDefault.__init__(self, url, comment)
        api_url = "https://api.nytimes.com/svc/search/v2/articlesearch.json"
        url = url.split("?")[0]  # remove query parameters from the URL
        # encoded_url = urllib.parse.quote(base_url, safe='') # quote encode URL
        query_url = f"""{api_url}?fq=url:(\"{url}\")&api-key={NYT_APP_KEY}"""
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
        date = arrow.get(pub_date).format("YYYYMMDD")
        return date

    def get_excerpt(self):
        excerpt = self.json["abstract"]
        return excerpt.strip()
