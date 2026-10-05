"""Wikimedia Meta scraper.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import re

from thunderdell.biblio import fields as bf
from thunderdell.utils.web import unescape_entities, xpath_strings

from .default import ScrapeDefault


class ScrapeWMMeta(ScrapeDefault):
    """Scrape Wikimedia Meta wiki."""

    def __init__(self, url, comment):
        print("Scraping Wikimedia Meta;", end="\n")
        ScrapeDefault.__init__(self, url, comment)

    def get_author(self):
        return "Wikimedia"

    def get_title(self):
        title = ScrapeDefault.get_title(self)  # super()?
        return title.replace(" - Meta", "")

    def get_date(self):  # Meta is often foobar because of proxy bugs
        match = re.search(
            r"""<li id="footer-info-lastmod"> This page was last edited """
            + r"""on (\d{1,2}) (\w+) (\d\d\d\d)""",
            self.html_u or "",
        )
        if match is None:  # no footer: use the generic meta/datefinder/today logic
            return ScrapeDefault.get_date(self)
        day, month, year = match.groups()
        month = bf.MONTH2DIGIT[month[0:3].lower()]
        return f"{int(year)}{int(month):02d}{int(day):02d}"

    def get_org(self):
        return "Wikimedia"

    def get_excerpt(self):
        return ""  # no good way to identify first paragraph at Meta

    def get_permalink(self):
        url_host = self.url.split("/wiki/")[0]
        url_paths = xpath_strings(self.html_p, """//li[@id="t-permalink"]/a/@href""")
        if not url_paths:
            return self.url
        permalink = url_host + url_paths[0]
        return unescape_entities(permalink)
