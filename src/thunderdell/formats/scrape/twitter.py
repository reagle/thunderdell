"""Scrape Twitter bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import textwrap
import warnings

import arrow

# https://github.com/trevorhobenshield/twitter-api-client/
from twitter.scraper import Scraper

# from twitter.util import init_session
import thunderdell.utils.web as uw

from .default import ScrapeDefault

# twitter-api-client has some regex syntax warnings; should be raw strings
# ... site-packages/twitter/scraper.py:549: SyntaxWarning: invalid escape sequence '\d'
warnings.filterwarnings("ignore", category=SyntaxWarning)


class ScrapeTwitter(ScrapeDefault):
    """Scrape Twitter bibliographic data."""

    def __init__(self, url: str, comment: str):
        TW_EMAIL = uw.get_credential("TW_EMAIL")
        TW_USERNAME = uw.get_credential("TW_USERNAME")
        TW_PASSWORD = uw.get_credential("TW_PASSWORD")
        print("Scraping X/Twitter")
        # super().__init__(url, comment) # TODO: don't need this 2025-03-10

        if "://x.com/" not in url:
            raise RuntimeError(f"Invalid X/Twitter URL: {url}")

        # Neither guest nor user/password sessions work reliably 2025-03-10;
        # library suggests using cookies, which I've yet TODO
        # scraper = Scraper(session=init_session())
        scraper = Scraper(TW_EMAIL, TW_USERNAME, TW_PASSWORD)
        identity = url.rsplit("/", 1)[1]
        twitter_result = scraper.tweets_by_id([identity])

        self.status = twitter_result[0]["data"]["tweetResult"]["result"]
        print(f"Status retrieved: {self.status['legacy']['id_str']}")

    def get_biblio(self) -> dict[str, str]:
        return {
            "author": self.get_author(),
            "title": self.get_title(),
            "date": self.get_date(),
            "permalink": self.url,
            "excerpt": self.get_excerpt(),
            "comment": self.comment,
            "url": self.url,
            "organization": "X/Twitter",
        }

    def get_author(self) -> str:
        user = self.status["core"]["user_results"]["result"]["legacy"]
        return f"{user['name'].strip()} (@{user['screen_name'].strip()})"

    def get_title(self) -> str:
        first_line = self.status["legacy"]["full_text"].split("\n")[0]
        return textwrap.shorten(first_line, 136, placeholder="...")

    def get_date(self) -> str:
        return arrow.get(
            self.status["legacy"]["created_at"], "ddd MMM DD HH:mm:ss Z YYYY"
        ).format("YYYYMMDD")

    def get_excerpt(self) -> str:
        return self.status["legacy"]["full_text"].strip()
