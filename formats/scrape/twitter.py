"""Scrape Twitter bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import textwrap

import pendulum as pm

# https://github.com/trevorhobenshield/twitter-api-client
from twitter.scraper import Scraper
from twitter.util import init_session

from .default import ScrapeDefault

session = init_session()
scraper = Scraper(session=session)

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


class ScrapeTwitter(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping twitter", end="\n")
        ScrapeDefault.__init__(self, url, comment)

        # extract username and id
        if "://twitter.com/" in self.url:
            identity = url.rsplit("/", 1)[1]
        else:
            raise RuntimeError("cannot identify twitter ID in {url}")
        twitter_result = scraper.tweets_by_id([identity])
        self.status = twitter_result[0]["data"]["tweetResult"]["result"]
        print(f"{self.status=}")

    def get_biblio(self):
        biblio = {
            "author": self.get_author(),
            "title": self.get_title(),
            "date": self.get_date(),
            "permalink": self.url,
            "excerpt": self.get_excerpt(),
            "comment": self.comment,
            "url": self.url,
            "organization": "Twitter",
        }
        return biblio

    def get_author(self):
        name = self.status["core"]["user_results"]["result"]["legacy"]["name"].strip()
        screen_name = self.status["core"]["user_results"]["result"]["legacy"][
            "screen_name"
        ].strip()
        print(f"{name=}")
        return f"{name} ({screen_name})"

    def get_title(self):
        title = self.status["legacy"]["full_text"].split("\n")[0]
        title = textwrap.shorten(title, 136, break_long_words=False, placeholder="...")
        return title

    def get_date(self):
        created_at = self.status["legacy"]["created_at"]
        return pm.parse(created_at, strict=False).strftime("%Y%m%d")  # type: ignore

    def get_excerpt(self):
        return self.status["legacy"]["full_text"].strip()
