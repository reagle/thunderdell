"""Scrape Reddit bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging as log
import re
import time
from datetime import datetime
from urllib.parse import urlparse, urlunparse

from thunderdell.change_case import sentence_case
from thunderdell.utils.web import get_JSON

from .default import ScrapeDefault

NOW = time.localtime()


class ScrapeReddit(ScrapeDefault):
    """Scrape Reddit class."""

    def __init__(self, url_clean, comment):
        print("Scraping reddit", end="\n")
        ScrapeDefault.__init__(self, url_clean, comment)

        RE_REDDIT_URL = re.compile(
            r"""
                (?P<prefix>http.*?reddit\.com/)
                (?P<root>(r/[\w\.]+)|(u(ser)?/\w+)|(wiki/\w+))
                (?P<post>/comments/(?P<pid>\w+)/(?P<title>\w+)/)?
                (?P<comment>(?P<cid>\w+))?
                """,
            re.VERBOSE,
        )

        self.type = "unknown"
        url_parsed = urlparse(url_clean)._replace(query="", fragment="")
        url_clean = urlunparse(url_parsed)
        self.json = get_JSON(f"{url_clean}.json")
        if match := RE_REDDIT_URL.match(url_clean):
            self.url_dict = match.groupdict()
            log.info(f"{self.url_dict=}")
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
        else:
            raise TypeError("Unknown type of Reddit resource.")
        log.info(f"{self.type=}")

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
        log.info("GETTING ORG")
        organization = "Reddit"
        log.info(f"{self.type=}")
        if self.type in ["post", "comment"]:
            organization = self.url_dict["root"]
        log.info(f"{organization=}")
        return organization.strip()

    def get_author(self):
        author = "Reddit"
        if self.type == "post":
            author = self.json[0]["data"]["children"][0]["data"]["author"]
        if self.type == "comment":
            log.info(f"{self.json[1]=}")
            author = self.json[1]["data"]["children"][0]["data"]["author"]
        log.info(f"{author=}")
        return author.strip()

    def get_title(self):
        title = "UNKNOWN"
        if self.type == "subreddit":
            title = self.url_dict["root"]
        elif self.type in ["post", "comment"]:
            title = sentence_case(self.json[0]["data"]["children"][0]["data"]["title"])
        log.info(f"{title=}")
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
        log.info(f"returning {excerpt}")
        return excerpt.strip()
