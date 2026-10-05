"""Scrape Twitter bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GPLv3"
__version__ = "1.0"

import logging
import re
import textwrap

from thunderdell.utils.web import get_HTML, get_text, xpath_strings

from .default import ScrapeDefault


class ScrapeTwitter(ScrapeDefault):
    """Scrape Twitter bibliographic data by scraping nitter.net."""

    def __init__(self, url: str, comment: str):
        print("Scraping X/Twitter via nitter.net")
        # busy routes twitter.com here too; it is the same site as x.com.
        url = re.sub(r"://(?:www\.|mobile\.)?twitter\.com/", "://x.com/", url, count=1)
        if "://x.com/" not in url:
            raise RuntimeError(f"Invalid X/Twitter URL: {url}")
        self.url = url
        self.nitter_url = url.replace("://x.com/", "://nitter.net/")
        self.comment = comment
        try:
            self.html_b, self.html_p, self.html_u, self.resp = get_HTML(
                self.nitter_url, cache_control="no-cache"
            )
        except OSError as e:
            logging.warning(f"{e} unable to get_HTML {self.nitter_url=}")
            self.html_b = self.html_p = self.resp = None
            self.html_u = ""
        self.text = None
        if self.html_b:
            self.text = get_text(self.nitter_url)

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
        if author_meta := xpath_strings(
            self.html_p, "//meta[@property='og:title']/@content"
        ):
            return author_meta[0].split(" / ")[0].strip()
        return "UNKNOWN"

    def get_title(self) -> str:
        # Use first line of excerpt, shortened to 136 chars with ellipsis
        excerpt = self.get_excerpt()
        if excerpt:
            first_line = excerpt.split("\n")[0]
            return textwrap.shorten(first_line, width=136, placeholder="…")
        return "UNKNOWN TITLE"

    def get_date(self) -> str:
        # span with class "tweet-date" and a child a element text
        if date_spans := xpath_strings(
            self.html_p, "//span[@class='tweet-date']/a/text()"
        ):
            date_str = date_spans[0].strip()
            # Try to parse date string to YYYYMMDD
            from thunderdell.utils.dates import parse_date

            parsed_date = parse_date(date_str)
            if parsed_date:
                return parsed_date
        # fallback to default date
        import time

        return time.strftime("%Y%m%d")

    def get_excerpt(self) -> str:
        # meta property="og:description" content="tweet text"
        if desc_meta := xpath_strings(
            self.html_p, "//meta[@property='og:description']/@content"
        ):
            return desc_meta[0].strip()
        return ""
