#!/usr/bin/env python3
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
import time

from biblio import fields as bf
from utils.web import get_HTML, unescape_XML

from .scrape_default import ScrapeDefault

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


class ScrapeENWP(ScrapeDefault):
    def __init__(self, url, comment):
        print(("Scraping en.Wikipedia;"), end="\n")
        ScrapeDefault.__init__(self, url, comment)

    def get_author(self):
        return "Wikipedia"

    def split_title_org(self):
        return self.get_title(), self.get_org()

    def get_title(self):
        title = ScrapeDefault.get_title(self)  # use super()?
        info(f"title = '{title}'")
        return title.replace(" - Wikipedia", "")

    def get_permalink(self):
        if "oldid" not in self.url and "=Special:" not in self.url:
            permalink = self.url.split("/wiki/")[0] + re.search(
                '''<li id="t-permalink".*?><a href="(.*?)"''', self.html_u
            ).group(1)
            return unescape_XML(permalink)
        else:
            return self.url

    def get_date(self):
        """find date within span"""
        if "oldid" not in self.url and "=Special:" not in self.url:
            _, _, versioned_HTML_u, resp = get_HTML(self.get_permalink())
            _, day, month, year = re.search(
                r"""<span id="mw-revision-date">(.*?), (\d{1,2}) (\w+) """
                r"""(\d\d\d\d)</span>""",
                versioned_HTML_u,
            ).groups()
            month = bf.MONTH2DIGIT[month[0:3].lower()]
            return "%d%02d%02d" % (int(year), int(month), int(day))
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
