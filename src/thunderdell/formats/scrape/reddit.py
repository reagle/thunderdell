"""Scrape Reddit bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import re
import time
from datetime import datetime
from urllib.parse import urlparse, urlunparse

import praw

import thunderdell.utils.web as uw
from thunderdell.change_case import sentence_case

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

        reddit = praw.Reddit(
            user_agent=uw.get_credential("REDDIT_USER_AGENT"),
            client_id=uw.get_credential("REDDIT_CLIENT_ID"),
            client_secret=uw.get_credential("REDDIT_CLIENT_SECRET"),
            username=uw.get_credential("REDDIT_USERNAME"),
            password=uw.get_credential("REDDIT_PASSWORD"),
        )

        self.type = "unknown"
        url_parsed = urlparse(url_clean)._replace(query="", fragment="")
        url_clean = urlunparse(url_parsed)

        if match := RE_REDDIT_URL.match(url_clean):
            self.url_dict = match.groupdict()
            logging.info(f"{self.url_dict=}")
            if self.url_dict["cid"]:
                self.type = "comment"
                self.reddit_obj = reddit.comment(id=self.url_dict["cid"])
                self.submission = self.reddit_obj.submission
            elif self.url_dict["pid"]:
                self.type = "post"
                self.reddit_obj = reddit.submission(url=url_clean)
                self.submission = self.reddit_obj
            elif self.url_dict["root"]:
                root = self.url_dict["root"]
                if root.startswith("r/"):
                    self.type = "subreddit"
                    self.reddit_obj = reddit.subreddit(root[2:])
                elif root.startswith(("u/", "user/")):
                    self.type = "user"
                    self.reddit_obj = reddit.redditor(root.split("/", 1)[1])
                elif root.startswith("wiki/"):
                    self.type = "wiki"
        else:
            raise TypeError("Unknown type of Reddit resource.")
        logging.info(f"{self.type=}")

    def get_biblio(self):
        biblio = {
            "author": self.get_author(),
            "title": self.get_title(),
            "date": self.get_date(),
            "permalink": self.get_permalink(),
            "excerpt": self.get_excerpt(),
            "comment": self.comment,
            "url": self.url,
        }
        container = "c_web"
        if self.type in ("post", "comment"):
            container = "c_forum"
        biblio[container] = self.get_org()
        return biblio

    def get_org(self):
        logging.info("GETTING ORG")
        organization = "Reddit"
        if self.type in ["post", "comment"]:
            organization = self.url_dict["root"]
        logging.info(f"{organization=}")
        return organization.strip()

    def get_author(self):
        author = "Reddit"
        if self.type in ("post", "comment"):
            author = self.reddit_obj.author.name if self.reddit_obj.author else "[deleted]"
        logging.info(f"{author=}")
        return author

    def get_title(self):
        title = "UNKNOWN"
        if self.type == "subreddit":
            title = self.url_dict["root"]
        elif self.type in ("post", "comment"):
            title = sentence_case(self.submission.title)
        logging.info(f"{title=}")
        return title.strip()

    def get_date(self):
        created = time.mktime(NOW)
        if self.type in ("post", "comment"):
            created = self.reddit_obj.created_utc
        return datetime.fromtimestamp(created).strftime("%Y%m%d")

    def get_excerpt(self):
        excerpt = ""
        if self.type == "post":
            if self.reddit_obj.selftext:
                excerpt = self.reddit_obj.selftext
            elif hasattr(self.reddit_obj, "url"):
                excerpt = self.reddit_obj.url
        elif self.type == "comment":
            excerpt = self.reddit_obj.body
        logging.info(f"returning {excerpt}")
        return excerpt.strip()
