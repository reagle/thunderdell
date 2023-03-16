#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""
Loggers for BusySponge.

https://github.com/reagle/thunderdell
"""

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
                    bib_in_single_line += "keyword = %s " % value
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
