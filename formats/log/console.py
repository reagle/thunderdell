"""Console logger.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import time

from biblio.keywords import KEY_SHORTCUTS
from utils.web import yasn_publish

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


def log2console(args, biblio):
    """
    Log to console.
    """

    TOKENS = (
        "author",
        "title",
        "subtitle",
        "date",
        "journal",
        "volume",
        "number",
        "publisher",
        "address",
        "DOI",
        "isbn",
        "tags",
        "comment",
        "excerpt",
        "url",
    )
    info(f"biblio = '{biblio}'")
    if biblio["tags"]:
        tags = biblio["tags"].strip().split(" ")
        tags_expanded = ""
        for tag in tags:
            tag = KEY_SHORTCUTS.get(tag, tag)
            tags_expanded += tag + " "
        # biblio['keywords'] = tags_expanded[0:-1]  # removes last space
    bib_in_single_line = ""
    for token in TOKENS:
        info(f"token = '{token}'")
        if token not in biblio:
            if token == "url":  # I want these printed even if don't exist
                biblio["url"] = ""
            elif token == "title":
                biblio["title"] = ""
            elif token == "subtitle":
                biblio["subtitle"] = ""
        if token in biblio and biblio[token]:
            if token == "tags":
                for value in tags_expanded.strip().split(" "):
                    # print('keyword = %s' % value)
                    bib_in_single_line += f"keyword = {value} "
            else:
                # print(('%s = %s' % (token, biblio[token])))
                bib_in_single_line += f"{token} = {biblio[token]} "
    print(f"{bib_in_single_line}")
    if "identifiers" in biblio:
        for identifer, value in list(biblio["identifiers"].items()):
            if identifer.startswith("isbn"):
                print(f"{identifer} = {value[0]}")

    if args.publish:
        yasn_publish(
            biblio["comment"],
            biblio["title"],
            biblio["subtitle"],
            biblio["url"],
            biblio["tags"],
        )
    return bib_in_single_line
