"""Scrape ArXiv bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
from typing import Any, TypedDict, cast

from thunderdell import query_arxiv
from thunderdell.change_case import sentence_case

from .default import ScrapeDefault


class ArxivBibDict(TypedDict, total=False):
    """Type definition for ArXiv bibliographic data."""

    author: dict[str, str] | list[dict[str, str]]
    published: str
    URL: str
    title: str


class ScrapeArXiv(ScrapeDefault):
    """Use arXiv API to get biblio data.

    Thank you to arXiv for use of its open access interoperability
    https://arxiv.org/help/api/index
    https://arxiv.org/help/api/basics.
    """

    def __init__(self, url: str, comment: str) -> None:
        """Initialize ArXiv scraper with URL and comment."""
        print("Scraping arXiv;", end="\n")
        self.identifier = url[6:]
        self.url = f"https://arxiv.org/abs/{self.identifier}"
        self.comment = comment
        self.dict_bib: ArxivBibDict | None = None

    def get_biblio(self) -> dict[str, Any]:
        """Retrieve bibliographic data from ArXiv API."""
        logging.info(f"url = {self.url}")

        # Try to convert identifier to int if needed, otherwise use as string
        try:
            query_param = int(self.identifier)  # type: int | str
        except ValueError:
            query_param = self.identifier

        query_result = query_arxiv.query(query_param)  # type: ignore[arg-type]

        # Handle case where query returns False or other falsy value
        if not query_result or not isinstance(query_result, dict):
            logging.error(f"Failed to query ArXiv for {self.identifier}")
            return {
                "entry_type": "report",
                "permalink": self.url,
                "title": "UNKNOWN",
                "author": "UNKNOWN",
                "date": "00000000",
                "organization": "arXiv",
                "identifier": self.identifier,
                "comment": self.comment,
            }

        # this dict matches ArxivBibDict for typing
        self.dict_bib = cast(ArxivBibDict, query_result)
        logging.info(f"{self.dict_bib=}")

        biblio: dict[str, Any] = {
            "entry_type": "report",
            "permalink": self.url,
            "excerpt": "",
            "organization": "arXiv",
            "identifier": self.identifier,
            "comment": self.comment,
        }

        for key, value in list(self.dict_bib.items()):
            logging.info(f"{key=} {value=} {type(value)=}")
            if value in (None, [], ""):
                pass
            elif key == "author":
                biblio["author"] = self.get_author()
            elif key == "published":
                biblio["date"] = self.get_date()
            elif key == "URL":
                biblio["permalink"] = biblio["url"] = value
            else:
                biblio[key] = value

        if "title" not in self.dict_bib:
            biblio["title"] = "UNKNOWN"
        else:
            biblio["title"] = sentence_case(" ".join(biblio["title"].split()))

        logging.info(f"{biblio=}")
        return biblio

    # Override base class methods to maintain compatibility
    def get_author(self) -> str:
        """Get author information from stored bibliographic data.

        >>> scraper = ScrapeArXiv("arXiv:2301.00001", "test")
        Scraping arXiv;
        >>> scraper.dict_bib = {"author": [{"name": "John Doe"}, {"name": "Jane Smith"}]}
        >>> scraper.get_author()
        'John Doe, Jane Smith'
        >>> scraper.dict_bib = {"author": {"name": "Seth Drake"}}
        >>> scraper.get_author()
        'Seth Drake'
        >>> scraper.dict_bib = {}
        >>> scraper.get_author()
        'UNKNOWN'
        """
        if (
            self.dict_bib is None
            or "author" not in self.dict_bib
            or not self.dict_bib["author"]
        ):
            return "UNKNOWN"

        authors = self.dict_bib["author"]
        # Handle single author (dict) vs multiple authors (list of dicts)
        if isinstance(authors, dict):
            return authors["name"]
        else:
            names = [author["name"] for author in authors]
            return ", ".join(names)

    def get_date(self) -> str:
        """Get date information from stored bibliographic data.

        >>> scraper = ScrapeArXiv("arXiv:2301.00001", "test")
        Scraping arXiv;
        >>> scraper.dict_bib = {"published": "2023-01-15T00:00:00Z"}
        >>> scraper.get_date()
        '20230115'
        >>> scraper.dict_bib = {"published": "2023-12-31"}
        >>> scraper.get_date()
        '20231231'
        >>> scraper.dict_bib = {}
        >>> scraper.get_date()
        '00000000'
        """
        if (
            self.dict_bib is None
            or "published" not in self.dict_bib
            or not self.dict_bib["published"]
        ):
            return "00000000"
        date = self.dict_bib["published"][0:10].replace("-", "")
        logging.info(f"{date=}")
        return date
