"""DOI scraper.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging as log

import doi_query
from change_case import sentence_case

from .default import ScrapeDefault


class ScrapeDOI(ScrapeDefault):
    def __init__(self, url, comment):
        print("Scraping DOI;", end="\n")
        self.url = url
        self.comment = comment

    def get_biblio(self):
        log.info(f"url = {self.url}")
        json_bib = doi_query.query(self.url)
        log.info(f"{json_bib=}")
        biblio = {
            "permalink": self.url,
            "excerpt": "",
            "comment": self.comment,
        }
        for key, value in list(json_bib.items()):
            log.info(f"{key=} {value=} {type(value)=}")
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
        log.info(f"{biblio=}")
        return biblio

    def get_author(self, bib_dict):
        names = "UNKNOWN"
        if "author" in bib_dict:
            names = ""
            for name_dic in bib_dict["author"]:
                log.info(f"name_dic = '{name_dic}'")
                if "literal" in name_dic:
                    name_reverse = name_dic["literal"].split(", ")
                    joined_name = f"{name_reverse[1]} {name_reverse[0]}"
                else:
                    joined_name = f"{name_dic['given']} {name_dic['family']}"
                log.info(f"joined_name = '{joined_name}'")
                names = names + ", " + joined_name
            names = names[2:]  # remove first comma
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
