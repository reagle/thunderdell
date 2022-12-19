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
import string
import time

from biblio.fields import SITE_CONTAINER_MAP
from change_case import sentence_case
from dateutil.parser import parse as dt_parse
from utils.text import smart_to_markdown
from utils.web import get_HTML, get_text, unescape_XML

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"


class ScrapeDefault(object):
    """
    Default and base class scraper.
    """

    def __init__(self, url, comment):
        print(("Scraping default Web page;"), end="\n")
        self.url = url
        self.comment = comment
        try:
            self.html_b, self.HTML_p, self.html_u, self.resp = get_HTML(
                url, cache_control="no-cache"
            )
        except IOError:
            self.html_b, self.HTML_p, self.html_u, self.resp = (
                None,
                None,
                None,
                None,
            )

        self.text = None
        if self.html_b:
            self.text = get_text(url)

    def get_biblio(self):
        biblio = {
            "author": self.get_author(),
            "date": self.get_date(),
            "permalink": self.get_permalink(),
            "excerpt": self.get_excerpt(),
            "comment": self.comment,
            "url": self.url,
        }
        biblio["title"], biblio["c_web"] = self.split_title_org()
        for site, container, container_type in SITE_CONTAINER_MAP:
            if site in biblio["url"]:
                info(f"{container=}")
                biblio[container_type] = container
                del biblio["c_web"]
        return biblio

    def get_author(self):
        """return guess of article author"""

        # sadly, lxml doesn't support xpath 2.0 and lower-case()
        AUTHOR_XPATHS = (
            """//meta[@name='DC.Contributor']/@content""",
            """//meta[@name='byl']/@content""",  # NYT
            """//meta[@name='author']/@content""",
            """//meta[@name='Author']/@content""",
            """//meta[@name='AUTHOR']/@content""",
            """//meta[@name='authors']/@content""",
            """//meta[@http-equiv='author']/@content""",
            """//meta[@name='sailthru.author']/@content""",
            """//a[@rel='author']//text()""",
            """//span[@class='author']/text()""",  # WashingtonPost
            """//*[@itemprop='author']//text()""",  # engadget
            """//*[contains(@class,'contributor')]/text()""",
            """//span[@class='name']/text()""",
            # tynan w/ bogus space
            """(//span[@class='dynamic-display_name-user-1 '])[1]/text()""",
            # amazon
            """//a[contains(@href, 'cm_cr_hreview_mr')]/text()""",
            # first of many
            """//*[1][contains(@class, 'byline')][1]//text()""",
        )
        if self.HTML_p is not None:
            info("checking author xpaths")
            for path in AUTHOR_XPATHS:
                info(f"trying = '{path}'")
                xpath_result = self.HTML_p.xpath(path)
                if xpath_result:
                    info(f"{xpath_result=}; {path=}")
                    # 20171204 added space to join below
                    author = string.capwords(" ".join(xpath_result).strip())
                    if author.lower().startswith("by "):
                        author = author[3:]
                    author = author.replace(" And ", ", ")
                    info(f"{author=}; {path=}")
                    if author != "":
                        return author
                    else:
                        continue

        if self.text:
            AUTHOR_REGEXS = (
                r"by ([a-z ]*?)(?:-|, |/ | at | on | posted ).{,35}?\d\d\d\d",
                r"^\W*(?:posted )?by[:]? (.*)",
                r"\d\d\d\d.{,6}? by ([a-z ]*)",
                r"\s{3,}by[:]? (.*)",
            )
            # info(self.text)
            info("checking regexs")
            for regex in AUTHOR_REGEXS:
                info(f"trying = '{regex}'")
                dmatch = re.search(regex, self.text, re.IGNORECASE | re.MULTILINE)
                if dmatch:
                    info(f'matched: "{regex}"')
                    author = dmatch.group(1).strip()
                    MAX_MATCH = 30
                    if " and " in author:
                        MAX_MATCH += 35
                        if ", " in author:
                            MAX_MATCH += 35
                    info("author = '%s'" % dmatch.group())
                    if len(author) > 4 and len(author) < MAX_MATCH:
                        return string.capwords(author)
                    else:
                        info(f"length {len(author)} is <4 or > {MAX_MATCH}")
                else:
                    info(f'failed: "{regex}"')

        return "UNKNOWN"

    def get_date(self):
        """rough match of a date, then pass to dateutil's magic abilities"""

        DATE_XPATHS = (
            """//li/span[@class="byline_label"]"""
            """/following-sibling::span/@title""",
        )  # tynan.com
        if self.HTML_p is not None:
            info("checking date xpaths")
            for path in DATE_XPATHS:
                info(f"trying = '{path}'")
                xpath_result = self.HTML_p.xpath(path)
                if xpath_result:
                    info(f"'{xpath_result=}'; '{path=}'")
                    date = dt_parse(xpath_result[0]).strftime("%Y%m%d")
                    info(f"date = '{date}'; xpath = '{path}'")
                    if date != "":
                        return date
                    else:
                        continue

        date_regexp = r"(\d+,? )?(%s)\w*(,? \d+)?(,? \d+)" % MONTHS
        try:
            dmatch = re.search(date_regexp, self.text, re.IGNORECASE)
            return dt_parse(dmatch.group(0)).strftime("%Y%m%d")
        except (AttributeError, TypeError, ValueError):
            date = time.strftime("%Y%m%d", NOW)
            info(f"making date NOW = {date}")
            return date

    def get_title(self):

        title_regexps = (
            ("http://lists.w3.org/.*", '<!-- subject="(.*?)" -->'),
            ("http://lists.kde.org/.*", r"<title>MARC: msg '(.*?)'</title>"),
            ("https://www.youtube.com", r'''"title":"(.*?)"'''),
            ("", r"<title[^>]*>([^<]+)</title>"),  # default: make sure last
        )

        for prefix, regexp in title_regexps:
            if self.url.startswith(prefix):
                info(f"{prefix=}")
                break

        title = "UNKNOWN TITLE"
        if self.html_u:
            tmatch = re.search(regexp, self.html_u, re.DOTALL | re.IGNORECASE)
            if tmatch:
                title = tmatch.group(1).strip()
                title = unescape_XML(title)
                title = sentence_case(title)
                title = smart_to_markdown(title)
        return title

    def split_title_org(self):
        """Separate the title by a delimiter and test if latter half is the
        organization (if it has certain words (blog) or is too short)"""

        ORG_WORDS = ["blog", "lab", "center"]

        title = title_ori = self.get_title()
        info(f"title_ori = '{title_ori}'")
        org = org_ori = self.get_org()
        info(f"org_ori = '{org_ori}'")
        STRONG_DELIMTERS = re.compile(r"\s[\|—«»]\s")
        WEAK_DELIMITERS = re.compile(r"[:;-]\s")
        if STRONG_DELIMTERS.search(title_ori):
            info("STRONG_DELIMTERS")
            parts = STRONG_DELIMTERS.split(title_ori)
        else:
            info("WEAK_DELIMITERS")
            parts = WEAK_DELIMITERS.split(title_ori)
        info(f"parts = '{parts}'")
        if len(parts) >= 2:
            beginning, end = " : ".join(parts[0:-1]), parts[-1]
            title, org = beginning, end
            title_c14n = title.replace(" ", "").lower()
            org_c14n = org.replace(" ", "").lower()
            if org_ori.lower() in org_c14n.lower():
                info("org_ori.lower() in org_c14n.lower(): pass")
                title, org = " ".join(parts[0:-1]), parts[-1]
            elif org_ori.lower() in title_c14n:
                info("org_ori.lower() in title_c14n: switch")
                title, org = parts[-1], " ".join(parts[0:-1])
            else:
                info(f"{beginning=}, {end=}")
                end_ratio = float(len(end)) / len(beginning + end)
                info(
                    " end_ratio: %d / %d = %.2f"
                    % (len(end), len(beginning + end), end_ratio)
                )
                # if beginning has org_word or end is large (>50%): switch
                if end_ratio > 0.5 or any(
                    word.lower() in beginning for word in ORG_WORDS
                ):
                    info("ratio and org_word: switch")
                    title = end
                    org = beginning
            title = sentence_case(title.strip())
            org = org.strip()
        return title, org

    def get_org(self):
        from urllib.parse import urlparse

        if self.url.startswith("file:"):
            return "local file"
        org_chunks = urlparse(self.url)[1].split(".")
        if org_chunks == [""]:
            org = ""
        elif org_chunks[0] in ("www"):
            org = org_chunks[1]
        elif org_chunks[-2] in ("wordpress", "blogspot", "wikia"):
            org = org_chunks[-3]
        else:
            org = org_chunks[-2]
        return org.title()

    def get_excerpt(self):
        """Select a paragraph if it is long enough and textual"""

        if self.text:
            lines = self.text.split("\n")
            for line in lines:
                line = " ".join(line.split())  # removes redundant space
                if len(line) >= 250:
                    line = smart_to_markdown(line)
                    info(f"line = '{line}'")
                    info(f"length = {len(line)}; 2nd_char = '{line[1]}'")
                    if line[1].isalpha():
                        excerpt = line
                        return excerpt.strip()
        return ""

    def get_permalink(self):
        return self.url
