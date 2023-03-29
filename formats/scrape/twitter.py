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

# https://realpython.com/twitter-bot-python-tweepy/
import tweepy

from utils.web_api_tokens import (
    TW_ACCESS_TOKEN,
    TW_ACCESS_TOKEN_SECRET,
    TW_CONSUMER_KEY,
    TW_CONSUMER_SECRET,
)

from .default import ScrapeDefault

auth = tweepy.OAuthHandler(TW_CONSUMER_KEY, TW_CONSUMER_SECRET)
auth.set_access_token(TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET)
api = tweepy.API(auth)

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
        try:
            self.status = api.get_status(id=identity)._json
        except tweepy.TweepError as err:
            print(err)
            raise err

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
        name = self.status["user"]["name"].strip()
        screen_name = self.status["user"]["screen_name"].strip()
        print(f"{name=}")
        return f"{name} ({screen_name})"

    def get_title(self):
        title = self.status["text"].split("\n")[0]
        title = textwrap.shorten(title, 136, break_long_words=False, placeholder="...")
        return title

    def get_date(self):
        return pm.parse(self.status["created_at"], strict=False).strftime("%Y%m%d")

    def get_excerpt(self):
        return self.status["text"].strip()
