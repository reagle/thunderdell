"""Scrape Twitter bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import logging
import textwrap

from thunderdell.utils.web import get_HTML, get_text

from .default import ScrapeDefault


class ScrapeTwitter(ScrapeDefault):
    """Scrape Twitter bibliographic data by scraping nitter.net."""

    def __init__(self, url: str, comment: str):
        print("Scraping X/Twitter via nitter.net")
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
            self.html_b = self.html_p = self.html_u = self.resp = None
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
        if self.html_p is not None:
            author_meta = self.html_p.xpath("//meta[@property='og:title']/@content")
            if author_meta:
                author = author_meta[0].split(" / ")[0].strip()
                return author
        return "UNKNOWN"

    def get_title(self) -> str:
        # Use first line of excerpt, shortened to 136 chars with ellipsis
        excerpt = self.get_excerpt()
        if excerpt:
            first_line = excerpt.split("\n")[0]
            return textwrap.shorten(first_line, width=136, placeholder="…")
        return "UNKNOWN TITLE"

    def get_date(self) -> str:
        if self.html_p is not None:
            # span with class "tweet-date" and a child a element text
            date_spans = self.html_p.xpath("//span[@class='tweet-date']/a/text()")
            if date_spans:
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
        if self.html_p is not None:
            # meta property="og:description" content="tweet text"
            desc_meta = self.html_p.xpath("//meta[@property='og:description']/@content")
            if desc_meta:
                return desc_meta[0].strip()
        return ""
