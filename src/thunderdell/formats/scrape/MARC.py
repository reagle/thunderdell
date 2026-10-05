"""MARC email archive scraper.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import re
import time

from .default import ScrapeDefault


class ScrapeMARC(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping MARC;", end="\n")
        ScrapeDefault.__init__(self, url, comment)

    def get_author(self):
        # re.search returns None rather than raising, so fall back with `or`.
        author = re.search(
            """From: *<a href=".*?">(.*?)</a>""", self.html_u
        ) or re.search("""From: *(.*)""", self.html_u)
        if author is None:
            return "UNKNOWN"
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
        if (match := re.search("""Subject: *(.*)""", self.html_u)) is None:
            return "UNKNOWN"
        subject = match.group(1)
        if subject.startswith("<a href") and (
            linked := re.search("""<a href=".*?">(.*?)</a>""", subject)
        ):
            subject = linked.group(1)
        subject = subject.replace("[Wikipedia-l] ", "").replace("[WikiEN-l] ", "")
        return subject

    def get_date(self):
        if (
            match := re.search("""Date: *<a href=".*?">(.*?)</a>""", self.html_u)
        ) is None:
            return ScrapeDefault.get_date(self)
        mdate = match.group(1)
        try:
            date = time.strptime(mdate, "%Y-%m-%d %I:%M:%S")
        except ValueError:
            date = time.strptime(mdate, "%Y-%m-%d %H:%M:%S")
        return time.strftime("%Y%m%d", date)

    def get_org(self):
        if match := re.search("""List: *<a href=".*?">(.*?)</a>""", self.html_u):
            return match.group(1)
        return ScrapeDefault.get_org(self)

    def get_excerpt(self):
        excerpt = ""
        msg_body = "\n".join(self.html_u.splitlines()[13:-17])
        msg_paras = msg_body.split("\n\n")
        for para in msg_paras:
            if para.count("\n") > 2 and not para.count("&gt;") > 1:
                excerpt = para.replace("\n", " ")
                break
        return excerpt.strip()

    def get_permalink(self):
        return self.url
