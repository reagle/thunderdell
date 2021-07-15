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
import re
import time
from datetime import datetime

from change_case import sentence_case
from utils.web import get_JSON

from .scrape_default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"


class ScrapeReddit(ScrapeDefault):
    def __init__(self, url, comment):
        print(("Scraping reddit"), end="\n")
        ScrapeDefault.__init__(self, url, comment)

        RE_REDDIT_URL = re.compile(
            r"""
                (?P<prefix>http.*?reddit\.com/)
                (?P<root>(r/\w+)|(u(ser)?/\w+)|(wiki/\w+))
                (?P<post>/comments/(?P<pid>\w+)/(?P<title>\w+)/)?
                (?P<comment>(?P<cid>\w+))?
                """,
            re.VERBOSE,
        )

        self.type = "unknown"
        self.json = get_JSON(f"{url}.json")
        debug(f"{self.json=}")
        if RE_REDDIT_URL.match(url):
            self.url_dict = RE_REDDIT_URL.match(url).groupdict()
            info(f"{self.url_dict=}")
            if self.url_dict["cid"]:
                self.type = "comment"
            elif self.url_dict["pid"]:
                self.type = "post"
            elif self.url_dict["root"]:
                if self.url_dict["root"].startswith("r/"):
                    self.type = "subreddit"
                elif self.url_dict["root"].startswith("u/"):
                    self.type = "user"
                if self.url_dict["root"].startswith("wiki/"):
                    self.type = "wiki"
        info(f"{self.type=}")

    def get_biblio(self):
        biblio = {
            "author": self.get_author(),
            "title": self.get_title(),
            "date": self.get_date(),
            "permalink": self.get_permalink(),
            "excerpt": self.get_excerpt(),
            "comment": self.comment,
            "url": self.url,
            # "organization": self.get_org(),
        }
        container = "c_web"
        if self.type in ("post", "comment"):
            container = "c_forum"
        biblio[container] = self.get_org()
        return biblio

    def get_org(self):

        info("GETTING ORG")
        organization = "Reddit"
        info(f"{self.type=}")
        if self.type in ["post", "comment"]:
            organization = self.url_dict["root"]
        info(f"{organization=}")
        return organization.strip()

    def get_author(self):

        author = "Reddit"
        if self.type == "post":
            author = self.json[0]["data"]["children"][0]["data"]["author"]
        if self.type == "comment":
            info(f"{self.json[1]=}")
            author = self.json[1]["data"]["children"][0]["data"]["author"]
        info(f"{author=}")
        return author.strip()

    def get_title(self):

        title = "UNKNOWN"
        if self.type == "subreddit":
            title = self.url_dict["root"]
        elif self.type in ["post", "comment"]:
            title = sentence_case(
                self.json[0]["data"]["children"][0]["data"]["title"]
            )
        info(f"{title=}")
        return title.strip()

    def get_date(self):

        # date_init = time.strftime("%Y%m%d", NOW)
        created = time.mktime(NOW)  # TODO convert to float epock time
        if self.type == "post":
            created = self.json[0]["data"]["children"][0]["data"]["created"]
        if self.type == "comment":
            created = self.json[1]["data"]["children"][0]["data"]["created"]
        date = datetime.fromtimestamp(created).strftime("%Y%m%d")
        return date.strip()

    def get_excerpt(self):

        excerpt = ""
        if self.type == "post":
            post_data = self.json[0]["data"]["children"][0]["data"]
            if "selftext" in post_data:
                excerpt = post_data["selftext"]  # self post
            elif "url_overridden_by_dest" in post_data:
                excerpt = post_data["url_overridden_by_dest"]  # link post
        elif self.type == "comment":
            excerpt = self.json[1]["data"]["children"][0]["data"]["body"]
        info(f"returning {excerpt}")
        return excerpt.strip()
