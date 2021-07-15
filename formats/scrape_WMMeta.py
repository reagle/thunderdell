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

from biblio import fields as bf
from utils.web import get_HTML, unescape_XML

from .scrape_default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


class ScrapeWMMeta(ScrapeDefault):
    def __init__(self, url, comment):
        print(("Scraping Wikimedia Meta;"), end="\n")
        ScrapeDefault.__init__(self, url, comment)

    def get_author(self):
        return "Wikimedia"

    def get_title(self):
        title = ScrapeDefault.get_title(self)  # super()?
        return title.replace(" - Meta", "")

    def get_date(self):  # Meta is often foobar because of proxy bugs
        _, _, cite_HTML_u, resp = get_HTML(self.get_permalink())
        # in browser, id="lastmod", but python gets id="footer-info-lastmod"
        day, month, year = re.search(
            r"""<li id="footer-info-lastmod"> This page was last edited """
            r"""on (\d{1,2}) (\w+) (\d\d\d\d)""",
            cite_HTML_u,
        ).groups()
        month = bf.MONTH2DIGIT[month[0:3].lower()]
        return "%d%02d%02d" % (int(year), int(month), int(day))

    def get_org(self):
        return "Wikimedia"

    def get_excerpt(self):
        return ""  # no good way to identify first paragraph at Meta

    def get_permalink(self):
        permalink = self.url.split("/wiki/")[0] + re.search(
            '''<li id="t-permalink"><a href="(.*?)"''', self.html_u
        ).group(1)
        return unescape_XML(permalink)
