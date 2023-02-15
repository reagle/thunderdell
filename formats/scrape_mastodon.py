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

# import textwrap
import mastodon  # https://mastodonpy.readthedocs.io/en/stable/

import utils.text as ut
import utils.web_api_tokens as wat

from .scrape_default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

api = mastodon.Mastodon(
    access_token=wat.OHAI_ACCESS_TOKEN, api_base_url=wat.MASTODON_APP_BASE
)


class ScrapeMastodon(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping mastodon", end="\n")
        ScrapeDefault.__init__(self, url, comment)

        # extract id
        if "://ohai.social/" in self.url:
            identity = url.rsplit("/", 1)[1]
        else:
            raise RuntimeError("cannot identify message ID in {url}")
        try:
            self.status = api.status(id=identity)
        except mastodon.MastodonError as err:
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
            "url": self.get_url(),
            "organization": "Mastodon",
        }
        return biblio

    def get_author(self):
        user_name = self.status["account"]["username"].strip()
        acct_name = self.status["account"]["acct"].strip()
        print(f"{acct_name=}")
        return f"{user_name} ({acct_name})"

    def get_title(self) -> str:
        # wrap multiple `p` elements in a single parent for parsing
        html = "<div>" + self.status["content"] + "</div>"
        text = ut.html_to_text("<div>" + html + "</div>")
        # title = textwrap.shorten(text, 136, break_long_words=False, placeholder="...")
        title = ut.truncate_text(text, 136)
        return title

    def get_date(self):
        return self.status["created_at"].strftime("%Y%m%d")

    def get_excerpt(self):
        # TODO: support multi-paragraph and richcontent in Freeplane mindmap
        #    eg: <richcontent TYPE="DETAILS" CONTENT-TYPE="plain/html"/>
        # wrap multiple `p` elements in a single parent for parsing
        html = "<div>" + self.status["content"] + "</div>"
        text = ut.html_to_text(html)
        return text

    def get_url(self):
        return self.status["url"]
