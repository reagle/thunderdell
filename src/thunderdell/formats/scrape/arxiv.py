"""Scrape ArXiv bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging

from thunderdell import arxiv_query
from thunderdell.change_case import sentence_case

from .default import ScrapeDefault


class ScrapeArXiv(ScrapeDefault):
    """Use arXiv API to get biblio data.

    Thank you to arXiv for use of its open access interoperability
    https://arxiv.org/help/api/index
    https://arxiv.org/help/api/basics.
    """

    def __init__(self, url, comment):
        print("Scraping arXiv;", end="\n")
        self.identifier = url[6:]
        self.url = f"https://arxiv.org/abs/{self.identifier}"
        self.comment = comment

    def get_biblio(self):
        logging.info(f"url = {self.url}")
        dict_bib = arxiv_query.query(self.identifier)
        logging.info(f"{dict_bib=}")
        biblio = {
            "entry_type": "report",
            "permalink": self.url,
            "excerpt": "",
            "organization": "arXiv",
            "identifier": self.identifier,
            "comment": self.comment,
        }
        for key, value in list(dict_bib.items()):
            logging.info(f"{key=} {value=} {type(value)=}")
            if value in (None, [], ""):
                pass
            elif key == "author":
                biblio["author"] = self.get_author(dict_bib)
            elif key == "published":
                biblio["date"] = self.get_date(dict_bib)
            elif key == "URL":
                biblio["permalink"] = biblio["url"] = dict_bib["URL"]
            else:
                biblio[key] = dict_bib[key]
        if "title" not in dict_bib:
            biblio["title"] = "UNKNOWN"
        else:
            biblio["title"] = sentence_case(" ".join(biblio["title"].split()))
        logging.info(f"{biblio=}")
        return biblio

    def get_author(self, bib_dict):
        names = "UNKNOWN"
        if "author" in bib_dict:
            names = [author["name"] for author in bib_dict["author"]]
        return ", ".join(names)

    def get_date(self, bib_dict):
        date = bib_dict["published"][0:10].replace("-", "")
        logging.info(f"{date=}")
        return date
