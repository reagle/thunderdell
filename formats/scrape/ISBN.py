"""ISBN scraper.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging as log

from change_case import sentence_case

from .default import ScrapeDefault


class ScrapeISBN(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping ISBN;", end="\n")
        self.url = url
        self.comment = comment

    def get_biblio(self):
        import isbn_query

        log.info(f"url = {self.url}")
        json_bib = isbn_query.query(self.url)
        log.info(f"json_bib = '{json_bib}'")
        biblio = {
            "permalink": self.url,
            "excerpt": "",
            "comment": self.comment,
        }
        log.info("### json_bib.items()")
        for key, value in list(json_bib.items()):
            log.info(f"key = '{key}'")
            if key.startswith("subject"):
                continue
            log.info(f"key = '{key}' value = '{value}' type(value) = '{type(value)}'\n")
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
            log.info(f"{bib_dict['author']=}")
            names = bib_dict["author"]
        return names

    def get_date(self, bib_dict):
        # "issued":{"date-parts":[[2007,3]]}
        date_parts = bib_dict["issued"]["date-parts"][0]
        log.info(f"{date_parts=}")
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
        log.info(f"{date=}")
        return date
