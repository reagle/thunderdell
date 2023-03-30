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
