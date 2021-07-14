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
from datetime import datetime

from dateutil.parser import parse as dt_parse

from biblio import fields as bf
from biblio.fields import SITE_CONTAINER_MAP
from change_case import sentence_case
from utils.text import smart_to_markdown
from utils.web import get_HTML, get_JSON, get_text, unescape_XML


# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"


class scrape_default(object):
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
                dmatch = re.search(
                    regex, self.text, re.IGNORECASE | re.MULTILINE
                )
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

        org_chunks = urlparse(self.url)[1].split(".")
        if org_chunks[0] in ("www"):
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


class scrape_ISBN(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping ISBN;"), end="\n")
        self.url = url
        self.comment = comment

    def get_biblio(self):

        import book_query

        info(f"url = {self.url}")
        json_bib = book_query.query(self.url)
        info(f"json_bib = '{json_bib}'")
        biblio = {
            "permalink": self.url,
            "excerpt": "",
            "comment": self.comment,
        }
        info("### json_bib.items()")
        for key, value in list(json_bib.items()):
            info(f"key = '{key}'")
            if key.startswith("subject"):
                continue
            info(
                "key = '%s' value = '%s' type(value) = '%s'\n"
                % (key, value, type(value))
            )
            if value in (None, [], ""):
                pass
            elif key == "author":
                biblio["author"] = self.get_author(json_bib)
            elif key == "year":
                biblio["date"] = json_bib["year"]
            elif key == "isbn":
                biblio["isbn"] = json_bib["isbn"]
            elif key == "pageCount":
                biblio["pages"] = json_bib["pageCount"]
            elif key == "publisher":
                biblio["publisher"] = json_bib["publisher"]
            elif key == "city":
                biblio["address"] = json_bib["city"]
            elif key == "url":
                biblio["url"] = json_bib["url"]
                biblio["permalink"] = json_bib["url"]
            else:
                biblio[key] = json_bib[key]
        if "title" in json_bib:
            title = biblio["title"].replace(": ", ": ")
            biblio["title"] = sentence_case(title)
            if "subtitle" in json_bib:
                biblio["subtitle"] = sentence_case(json_bib["subtitle"])
        else:
            biblio["title"] = "UNKNOWN"
        return biblio

    def get_author(self, bib_dict):
        names = "UNKNOWN"
        if "author" in bib_dict:
            info(f"{bib_dict['author']=}")
            names = bib_dict["author"]
        return names

    def get_date(self, bib_dict):
        # "issued":{"date-parts":[[2007,3]]}
        date_parts = bib_dict["issued"]["date-parts"][0]
        info(f"{date_parts=}")
        if len(date_parts) == 3:
            year, month, day = date_parts
            date = "%d%02d%02d" % (int(year), int(month), int(day))
        elif len(date_parts) == 2:
            year, month = date_parts
            date = "%d%02d" % (int(year), int(month))
        elif len(date_parts) == 1:
            date = str(date_parts[0])
        else:
            date = "0000"
        info(f"{date=}")
        return date


class scrape_DOI(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping DOI;"), end="\n")
        self.url = url
        self.comment = comment

    def get_biblio(self):

        import doi_query

        info(f"url = {self.url}")
        json_bib = doi_query.query(self.url)
        biblio = {
            "permalink": self.url,
            "excerpt": "",
            "comment": self.comment,
        }
        for key, value in list(json_bib.items()):
            info(f"{key=} {value=} {type(value)=}")
            if value in (None, [], ""):
                pass
            elif key == "author":
                biblio["author"] = self.get_author(json_bib)
            elif key == "issued":
                biblio["date"] = self.get_date(json_bib)
            elif key == "page":
                biblio["pages"] = json_bib["page"]
            elif key == "container-title":
                biblio["journal"] = json_bib["container-title"]
            elif key == "issue":
                biblio["number"] = json_bib["issue"]
            elif key == "URL":
                biblio["permalink"] = biblio["url"] = json_bib["URL"]
            else:
                biblio[key] = json_bib[key]
        if "title" not in json_bib:
            biblio["title"] = "UNKNOWN"
        else:
            biblio["title"] = sentence_case(" ".join(biblio["title"].split()))
        info(f"{biblio=}")
        return biblio

    def get_author(self, bib_dict):
        names = "UNKNOWN"
        if "author" in bib_dict:
            names = ""
            for name_dic in bib_dict["author"]:
                info(f"name_dic = '{name_dic}'")
                joined_name = f"{name_dic['given']} {name_dic['family']}"
                info(f"joined_name = '{joined_name}'")
                names = names + ", " + joined_name
            names = names[2:]  # remove first comma
        return names

    def get_date(self, bib_dict):
        # "issued":{"date-parts":[[2007,3]]}
        date_parts = bib_dict["issued"]["date-parts"][0]
        info(f"{date_parts=}")
        if len(date_parts) == 3:
            year, month, day = date_parts
            date = "%d%02d%02d" % (int(year), int(month), int(day))
        elif len(date_parts) == 2:
            year, month = date_parts
            date = "%d%02d" % (int(year), int(month))
        elif len(date_parts) == 1:
            date = str(date_parts[0])
        else:
            date = "0000"
        info(f"{date=}")
        return date


class scrape_MARC(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping MARC;"), end="\n")
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        try:
            author = re.search(
                """From: *<a href=".*?">(.*?)</a>""", self.html_u
            )
        except AttributeError:
            author = re.search("""From: *(.*)""", self.html_u)
        author = author.group(1)
        author = (
            author.replace(" () ", "@")
            .replace(" ! ", ".")
            .replace("&lt;", "<")
            .replace("&gt;", ">")
        )
        author = author.split(" <")[0]
        author = author.replace('"', "")
        return author

    def get_title(self):
        subject = re.search("""Subject: *(.*)""", self.html_u).group(1)
        if subject.startswith("<a href"):
            subject = re.search("""<a href=".*?">(.*?)</a>""", subject).group(
                1
            )
        subject = subject.replace("[Wikipedia-l] ", "").replace(
            "[WikiEN-l] ", ""
        )
        return subject

    def get_date(self):
        mdate = re.search(
            """Date: *<a href=".*?">(.*?)</a>""", self.html_u
        ).group(1)
        try:
            date = time.strptime(mdate, "%Y-%m-%d %I:%M:%S")
        except ValueError:
            date = time.strptime(mdate, "%Y-%m-%d %H:%M:%S")
        return time.strftime("%Y%m%d", date)

    def get_org(self):
        return re.search(
            """List: *<a href=".*?">(.*?)</a>""", self.html_u
        ).group(1)

    def get_excerpt(self):
        excerpt = ""
        msg_body = "\n".join(self.html_u.splitlines()[13:-17])
        msg_paras = msg_body.split("\n\n")
        for para in msg_paras:
            if para.count("\n") > 2:
                if not para.count("&gt;") > 1:
                    excerpt = para.replace("\n", " ")
                    break
        return excerpt.strip()

    def get_permalink(self):
        return self.url


class scrape_ENWP(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping en.Wikipedia;"), end="\n")
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        return "Wikipedia"

    def split_title_org(self):
        return self.get_title(), self.get_org()

    def get_title(self):
        title = scrape_default.get_title(self)  # use super()?
        info(f"title = '{title}'")
        return title.replace(" - Wikipedia", "")

    def get_permalink(self):
        if "oldid" not in self.url and "=Special:" not in self.url:
            permalink = self.url.split("/wiki/")[0] + re.search(
                '''<li id="t-permalink"><a href="(.*?)"''', self.html_u
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


class scrape_WMMeta(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping Wikimedia Meta;"), end="\n")
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        return "Wikimedia"

    def get_title(self):
        title = scrape_default.get_title(self)  # super()?
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


class scrape_twitter(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping twitter"), end="\n")
        scrape_default.__init__(self, url, comment)

    def get_biblio(self):
        biblio = {
            "author": self.get_author(),
            "title": self.get_title(),
            "date": self.get_date(),
            "permalink": self.get_permalink(),
            "excerpt": self.get_excerpt(),
            "comment": self.comment,
            "url": self.url,
            "organization": "Twitter",
        }
        return biblio

    def get_author(self):

        # TODO: 20210714 xpath throw an error on author
        # twitter return crap if JS not detected
        author = self.HTML_p.xpath("//div[@data-user-id]/@data-name")[0]
        return author.strip()

    def get_title(self):

        authororg_title = self.HTML_p.xpath("//title/text()")[0]
        info(f"{authororg_title=}")
        author_org, title = authororg_title.split(":", 1)
        # author_org, title = authororg_title.split('|', 1)
        # author = author_org.split('/', 1)[1]
        return title.strip()

    def get_date(self):

        date = self.HTML_p.xpath(
            "//a[contains(@class,'tweet-timestamp')]/span/@data-time"
        )[0]
        date = datetime.fromtimestamp(int(date)).strftime("%Y%m%d")
        return date

    def get_excerpt(self):

        excerpt = self.HTML_p.xpath(
            "//p[contains(@class,'tweet-text')]/text()"
        )[0]
        return excerpt


class scrape_reddit(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping reddit"), end="\n")
        scrape_default.__init__(self, url, comment)

        RE_REDDIT_URL = re.compile(
            r"""
                (?P<prefix>http.*?reddit\.com/)
                (?P<root>(r/\w+)|(u(ser)?/\w+)|(wiki/\w+))
                (?P<post>/comments/(?P<pid>\w+)/(?P<title>\w+)/)?
                (?P<comment>(?P<cid>\w+))?
                """,
            re.VERBOSE,
        )

        self.type = "unknown"
        self.json = get_JSON(f"{url}.json")
        debug(f"{self.json=}")
        if RE_REDDIT_URL.match(url):
            self.url_dict = RE_REDDIT_URL.match(url).groupdict()
            info(f"{self.url_dict=}")
            if self.url_dict["cid"]:
                self.type = "comment"
            elif self.url_dict["pid"]:
                self.type = "post"
            elif self.url_dict["root"]:
                if self.url_dict["root"].startswith("r/"):
                    self.type = "subreddit"
                elif self.url_dict["root"].startswith("u/"):
                    self.type = "user"
                if self.url_dict["root"].startswith("wiki/"):
                    self.type = "wiki"
        info(f"{self.type=}")

    def get_biblio(self):
        biblio = {
            "author": self.get_author(),
            "title": self.get_title(),
            "date": self.get_date(),
            "permalink": self.get_permalink(),
            "excerpt": self.get_excerpt(),
            "comment": self.comment,
            "url": self.url,
            # "organization": self.get_org(),
        }
        container = "c_web"
        if self.type in ("post", "comment"):
            container = "c_forum"
        biblio[container] = self.get_org()
        return biblio

    def get_org(self):

        info("GETTING ORG")
        organization = "Reddit"
        info(f"{self.type=}")
        if self.type in ["post", "comment"]:
            organization = self.url_dict["root"]
        info(f"{organization=}")
        return organization.strip()

    def get_author(self):

        author = "Reddit"
        if self.type == "post":
            author = self.json[0]["data"]["children"][0]["data"]["author"]
        if self.type == "comment":
            info(f"{self.json[1]=}")
            author = self.json[1]["data"]["children"][0]["data"]["author"]
        info(f"{author=}")
        return author.strip()

    def get_title(self):

        title = "UNKNOWN"
        if self.type == "subreddit":
            title = self.url_dict["root"]
        elif self.type in ["post", "comment"]:
            title = sentence_case(
                self.json[0]["data"]["children"][0]["data"]["title"]
            )
        info(f"{title=}")
        return title.strip()

    def get_date(self):

        # date_init = time.strftime("%Y%m%d", NOW)
        created = time.mktime(NOW)  # TODO convert to float epock time
        if self.type == "post":
            created = self.json[0]["data"]["children"][0]["data"]["created"]
        if self.type == "comment":
            created = self.json[1]["data"]["children"][0]["data"]["created"]
        date = datetime.fromtimestamp(created).strftime("%Y%m%d")
        return date.strip()

    def get_excerpt(self):

        excerpt = ""
        if self.type == "post":
            post_data = self.json[0]["data"]["children"][0]["data"]
            if "selftext" in post_data:
                excerpt = post_data["selftext"]  # self post
            elif "url_overridden_by_dest" in post_data:
                excerpt = post_data["url_overridden_by_dest"]  # link post
        elif self.type == "comment":
            excerpt = self.json[1]["data"]["children"][0]["data"]["body"]
        info(f"returning {excerpt}")
        return excerpt.strip()
