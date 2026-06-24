"""English Wikipedia scraper.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import re
import time

from thunderdell.biblio import fields as bf
from thunderdell.utils.web import get_HTML, unescape_entities

from .default import ScrapeDefault

NOW = time.localtime()


class ScrapeENWP(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping en.Wikipedia;", end="\n")
        ScrapeDefault.__init__(self, url, comment)

    def get_author(self):
        return "Wikipedia"

    def get_title_org(self):
        return self.get_title(), self.get_org()

    def get_title(self):
        title = ScrapeDefault.get_title(self)  # use super()?
        logging.info(f"title = '{title}'")
        return title.replace(" - Wikipedia", "")

    def get_permalink(self):
        if "oldid" not in self.url and "=Special:" not in self.url:
            permalink = self.url.split("/wiki/")[0] + re.search(
                '''<li id="t-permalink".*?><a href="(.*?)"''', self.html_u
            ).group(1)
            return unescape_entities(permalink)
        else:
            return self.url

    def get_date(self):
        """Find date within span."""
        if "oldid" not in self.url and "=Special:" not in self.url:
            _, _, versioned_HTML_u, resp = get_HTML(self.get_permalink())
            span_match = re.search(
                r"""<span id="mw-revision-date">(.*?), (\d{1,2}) (\w+) """
                r"""(\d\d\d\d)</span>""",
                versioned_HTML_u,
            )
            if span_match:
                _, day, month, year = span_match.groups()
                month = bf.MONTH2DIGIT[month[0:3].lower()]
                return "%d%02d%02d" % (int(year), int(month), int(day))
            if url_date := re.search(r"/(\d{4})-(\d{2})-(\d{2})/", self.url):
                year, month, day = url_date.groups()
                return f"{year}{month}{day}"
            return time.strftime("%Y%m%d", NOW)
        else:
            return time.strftime("%Y%m%d", NOW)

    def get_org(self):
        return "Wikipedia"

    def get_excerpt(self):
        lines = self.text.split("\n")
        for line in lines:
            line = line.strip()
            if (len(line) > 280 and "This page documents" not in line) or (
                "This page in a nutshell" in line
            ):
                return line
        return ""
