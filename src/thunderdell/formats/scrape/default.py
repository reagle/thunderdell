"""Scrape web page bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import datetime
import logging
import re
import string
import time
from urllib.parse import urlparse

import datefinder  # https://github.com/akoumjian/datefinder

from thunderdell.biblio.fields import SITE_CONTAINER_MAP
from thunderdell.change_case import sentence_case
from thunderdell.utils.dates import parse_date
from thunderdell.utils.text import smart_to_markdown
from thunderdell.utils.web import get_HTML, get_text, unescape_entities

NOW = time.localtime()
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"


def winnow_dates(self) -> datetime.datetime:
    """Validate and sanity check results from datefinder.

    Remove dates if:
    - in the future
    - older than 50 years.
    """
    now = datetime.datetime.now()
    fifty_years_ago = now - datetime.timedelta(days=50 * 365.25)
    winnowed_dates = []

    for date in datefinder.find_dates(self.text):
        if date <= now and date >= fifty_years_ago:
            winnowed_dates.append(date)
    return winnowed_dates[0]


class ScrapeDefault:
    """Default and base class scraper."""

    def __init__(self, url, comment):
        print("Scraping default Web page;", end="\n")
        self.url = url
        self.comment = comment
        try:
            self.html_b, self.html_p, self.html_u, self.resp = get_HTML(
                url, cache_control="no-cache"
            )
        except OSError:
            self.html_b, self.html_p, self.html_u, self.resp = (
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
                logging.info(f"{container=}")
                biblio[container_type] = container
                del biblio["c_web"]
        return biblio

    def get_author(self):
        """Return guess of article author."""
        # sadly, lxml doesn't support xpath 2.0 and lower-case()
        AUTHOR_XPATHS = (
            """//meta[@name='DC.Contributor']/@content""",
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
            # ZDNet
            """//*[contains(@class, 'globalAuthor')]//*[contains(@class, 'link')]/text()""",
        )
        if self.html_p is not None:
            logging.info("checking author xpaths")
            for path in AUTHOR_XPATHS:
                logging.info(f"trying = '{path}'")
                xpath_result = self.html_p.xpath(path)
                if xpath_result:
                    logging.info(f"{xpath_result=}; {path=}")
                    author = string.capwords(" ".join(xpath_result).strip())
                    if author.lower().startswith("by "):
                        author = author[3:]
                    author = author.replace(" And ", ", ")
                    logging.info(f"{author=}; {path=}")
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
            logging.info("checking regexs")
            for regex in AUTHOR_REGEXS:
                logging.info(f"trying = '{regex}'")
                dmatch = re.search(regex, self.text, re.IGNORECASE | re.MULTILINE)
                if dmatch:
                    logging.info(f'matched: "{regex}"')
                    author = dmatch.group(1).strip()
                    MAX_MATCH = 30
                    if " and " in author:
                        MAX_MATCH += 35
                        if ", " in author:
                            MAX_MATCH += 35
                    logging.info(f"author = '{dmatch.group()}'")
                    if len(author) > 4 and len(author) < MAX_MATCH:
                        return string.capwords(author)
                    else:
                        logging.info(f"length {len(author)} is <4 or > {MAX_MATCH}")
                else:
                    logging.info(f'failed: "{regex}"')

        return "UNKNOWN"

    def get_date(self):
        """Return date from xpath, guess from datefinder, or today's date."""
        DATE_XPATHS = (
            """//meta[@name="date"]/@content""",
            """//meta[@name="pubdate"]/@content""",
            """//meta[@property="article:published_time"]/@content""",
            """//li/span[@class="byline_label"]/following-sibling::span/@title""",
            """//relative-time/@datetime""",
        )
        if self.html_p is not None:
            logging.info("checking date xpaths")
            for path in DATE_XPATHS:
                logging.info(f"trying = '{path}'")
                xpath_result = self.html_p.xpath(path)
                if xpath_result:
                    logging.info(f"'{xpath_result=}'; '{path=}'")
                    date = parse_date(xpath_result[0])
                    logging.info(f"date = '{date}'; xpath = '{path}'")
                    if date != "":
                        return date
                    else:
                        continue

        date = time.strftime("%Y%m%d", NOW)
        try:
            date = winnow_dates(self).strftime("%Y%m%d")
        except (TypeError, IndexError) as e:
            logging.info(f"date not found returning default NOW: {e}")
        return date

    def get_title(self):
        url_title_regexps = {
            "lists.w3.org": '<!-- subject="(.*?)" -->',
            "lists.kde.org": r"<title>MARC: msg '(.*?)'</title>",
            "www.youtube.com": r'''"title":"(.*?)"''',
            "DEFAULT": r"<title[^>]*>([^<]+)</title>",
        }

        url = urlparse(self.url)
        title_regexp = url_title_regexps.get(url.netloc, url_title_regexps["DEFAULT"])
        title = "UNKNOWN TITLE"
        if self.html_u:
            tmatch = re.search(title_regexp, self.html_u, re.DOTALL | re.IGNORECASE)
            if tmatch:
                title = tmatch.group(1).strip()
                title = unescape_entities(title)
                title = sentence_case(title)
                title = smart_to_markdown(title)
        return title

    def split_title_org(self):
        """Split the title from the org.

        Separate the title by a delimiter and test if latter half is the
        organization (if it has certain words (blog) or is too short).
        """
        ORG_WORDS = ["blog", "lab", "center"]

        title = title_ori = self.get_title()
        logging.info(f"title_ori = '{title_ori}'")
        org = org_ori = self.get_org()
        logging.info(f"org_ori = '{org_ori}'")
        STRONG_DELIMTERS = re.compile(r"\s[\|—«»]\s")
        WEAK_DELIMITERS = re.compile(r"[:;-]\s")
        if STRONG_DELIMTERS.search(title_ori):
            logging.info("STRONG_DELIMTERS")
            parts = STRONG_DELIMTERS.split(title_ori)
        else:
            logging.info("WEAK_DELIMITERS")
            parts = WEAK_DELIMITERS.split(title_ori)
        logging.info(f"parts = '{parts}'")
        if len(parts) >= 2:
            beginning, end = " : ".join(parts[0:-1]), parts[-1]
            title, org = beginning, end
            title_c14n = title.replace(" ", "").lower()
            org_c14n = org.replace(" ", "").lower()
            if org_ori.lower() in org_c14n.lower():
                logging.info("org_ori.lower() in org_c14n.lower(): pass")
                title, org = " ".join(parts[0:-1]), parts[-1]
            elif org_ori.lower() in title_c14n:
                logging.info("org_ori.lower() in title_c14n: switch")
                title, org = parts[-1], " ".join(parts[0:-1])
            else:
                logging.info(f"{beginning=}, {end=}")
                end_ratio = float(len(end)) / len(beginning + end)
                logging.info(
                    " end_ratio: %d / %d = %.2f"
                    % (len(end), len(beginning + end), end_ratio)
                )
                # if beginning has org_word or end is large (>50%): switch
                if end_ratio > 0.5 or any(
                    word.lower() in beginning for word in ORG_WORDS
                ):
                    logging.info("ratio and org_word: switch")
                    title = end
                    org = beginning
            title = sentence_case(title.strip())
            org = org.strip()
        return title, org

    def get_org(self):
        if self.url.startswith("file:"):
            return "local file"
        org_chunks = urlparse(self.url).netloc.split(".")
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
        """Select a paragraph if it is long enough and textual."""
        if self.text:
            lines = self.text.split("\n")
            for line in lines:
                line = " ".join(line.split())  # removes redundant space
                if len(line) >= 250:
                    line = smart_to_markdown(line)
                    logging.info(f"line = '{line}'")
                    logging.info(f"length = {len(line)}; 2nd_char = '{line[1]}'")
                    if line[1].isalpha():
                        excerpt = line
                        return excerpt.strip()
        return ""

    def get_permalink(self):
        return self.url
