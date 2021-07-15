#!/usr/bin/env python3
# -*- coding: utf-8 -*-
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
import textwrap

from dateutil.parser import parse as dt_parse

# https://twython.readthedocs.io/en/latest/index.html
from twython import Twython, TwythonError
from utils.web_api_tokens import (
    TW_ACCESS_TOKEN,
    TW_ACCESS_TOKEN_SECRET,
    TW_CONSUMER_KEY,
    TW_CONSUMER_SECRET,
)

from .scrape_default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

twitter = Twython(
    TW_CONSUMER_KEY,
    TW_CONSUMER_SECRET,
    TW_ACCESS_TOKEN,
    TW_ACCESS_TOKEN_SECRET,
)


class ScrapeTwitter(ScrapeDefault):
    def __init__(self, url, comment):
        print(("Scraping twitter"), end="\n")
        ScrapeDefault.__init__(self, url, comment)

        # extract username and id
        if "://twitter.com/" in self.url:
            id = url.rsplit("/", 1)[1]
        else:
            raise RuntimeError("cannot identify twitter ID in {url}")

        try:
            self.status = twitter.show_status(id=id, tweet_mode="extended")
        except TwythonError as err:
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
        return f"{name} ({screen_name})"

    def get_title(self):

        title = self.status["full_text"].split("\n")[0]
        title = textwrap.shorten(
            title, 136, break_long_words=False, placeholder="..."
        )
        return title

    def get_date(self):

        return dt_parse(self.status["created_at"]).strftime("%Y%m%d")

    def get_excerpt(self):

        return self.status["full_text"].strip()
