"""Scrape Twitter bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import asyncio
import textwrap

import arrow

# Import twikit instead of twitter-api-client
from twikit import Client

import thunderdell.utils.web as uw
from thunderdell import config

from .default import ScrapeDefault


class ScrapeTwitter(ScrapeDefault):
    """Scrape Twitter bibliographic data using twikit."""

    def __init__(self, url: str, comment: str):
        print("Scraping X/Twitter")
        super().__init__(url, comment)

        if "://x.com/" not in url:
            raise RuntimeError(f"Invalid X/Twitter URL: {url}")

        # Get credentials
        TW_EMAIL = uw.get_credential("TW_EMAIL")
        TW_USERNAME = uw.get_credential("TW_USERNAME")
        TW_PASSWORD = uw.get_credential("TW_PASSWORD")

        self.tweet_id = url.rsplit("/", 1)[1]

        try:
            self.status = asyncio.run(
                self._fetch_tweet(TW_USERNAME, TW_EMAIL, TW_PASSWORD)
            )
            print(f"Status retrieved: {self.tweet_id}")
        except Exception as exc:
            raise RuntimeError(f"Failed to fetch tweet: {exc}") from exc

    async def _fetch_tweet(self, username: str, email: str, password: str):
        """Fetch tweet using twikit."""
        client = Client("en-US")

        # Login with credentials and cache cookies
        await client.login(
            auth_info_1=username,
            auth_info_2=email,
            password=password,
            cookies_file=str(config.TMP_DIR / "twitter-cookies.json"),
            enable_ui_metrics=True,  # Reduces risk of account suspension
        )

        tweet = await client.get_tweet_by_id(self.tweet_id)
        return tweet

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
        return (
            f"{self.status.user.name.strip()} (@{self.status.user.screen_name.strip()})"
        )

    def get_title(self) -> str:
        first_line = self.status.text.split("\n")[0]
        return textwrap.shorten(first_line, 136, placeholder="...")

    def get_date(self) -> str:
        # Convert Twitter date format to YYYYMMDD
        return arrow.get(self.status.created_at_datetime).format("YYYYMMDD")

    def get_excerpt(self) -> str:
        # Get full tweet text
        return self.status.text.strip()
