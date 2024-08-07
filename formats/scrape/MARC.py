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
        try:
            author = re.search("""From: *<a href=".*?">(.*?)</a>""", self.html_u)
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
            subject = re.search("""<a href=".*?">(.*?)</a>""", subject).group(1)
        subject = subject.replace("[Wikipedia-l] ", "").replace("[WikiEN-l] ", "")
        return subject

    def get_date(self):
        mdate = re.search("""Date: *<a href=".*?">(.*?)</a>""", self.html_u).group(1)
        try:
            date = time.strptime(mdate, "%Y-%m-%d %I:%M:%S")
        except ValueError:
            date = time.strptime(mdate, "%Y-%m-%d %H:%M:%S")
        return time.strftime("%Y%m%d", date)

    def get_org(self):
        return re.search("""List: *<a href=".*?">(.*?)</a>""", self.html_u).group(1)

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
