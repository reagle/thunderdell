"""Wikimedia Meta scraper.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import re

from biblio import fields as bf
from utils.web import get_HTML, unescape_XML

from .default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


class ScrapeWMMeta(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping Wikimedia Meta;", end="\n")
        ScrapeDefault.__init__(self, url, comment)

    def get_author(self):
        return "Wikimedia"

    def get_title(self):
        title = ScrapeDefault.get_title(self)  # super()?
        return title.replace(" - Meta", "")

    def get_date(self):  # Meta is often foobar because of proxy bugs
        day, month, year = re.search(
            r"""<li id="footer-info-lastmod"> This page was last edited """
            + r"""on (\d{1,2}) (\w+) (\d\d\d\d)""",
            self.html_u,
        ).groups()
        month = bf.MONTH2DIGIT[month[0:3].lower()]
        return "%d%02d%02d" % (int(year), int(month), int(day))

    def get_date_old(self):  # Meta is often foobar because of proxy bugs
        _, _, cite_HTML_u, resp = get_HTML(self.get_permalink())
        # in browser, id="lastmod", but python gets id="footer-info-lastmod"
        day, month, year = re.search(
            r"""<li id="footer-info-lastmod"> This page was last edited """
            + r"""on (\d{1,2}) (\w+) (\d\d\d\d)""",
            cite_HTML_u,
        ).groups()
        month = bf.MONTH2DIGIT[month[0:3].lower()]
        return "%d%02d%02d" % (int(year), int(month), int(day))

    def get_org(self):
        return "Wikimedia"

    def get_excerpt(self):
        return ""  # no good way to identify first paragraph at Meta

    def get_permalink(self):
        url_host = self.url.split("/wiki/")[0]
        url_path = self.html_p.xpath("""//li[@id="t-permalink"]/a/@href""")[0]
        permalink = url_host + url_path
        return unescape_XML(permalink)
