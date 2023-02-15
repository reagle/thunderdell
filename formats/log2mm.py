#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""
Loggers for BusySponge.

https://github.com/reagle/thunderdell
"""

import logging
import time
from xml.etree.ElementTree import ElementTree, SubElement, parse  # Element,

import config
from biblio import fields as bf
from biblio.keywords import KEY_SHORTCUTS
from utils.web import yasn_publish

from .do_console_annotation import do_console_annotation

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


def log2mm(args, biblio):
    """
    Log to bibliographic mindmap, see:
        http://reagle.org/joseph/2009/01/thunderdell.html
    """

    print("to log2mm")
    biblio, args.publish = do_console_annotation(args, biblio)
    info(f"{biblio}")

    # now = time.gmtime()
    this_week = time.strftime("%U", NOW)
    this_year = time.strftime("%Y", NOW)
    date_read = time.strftime("%Y%m%d %H:%M UTC", NOW)

    ofile = f"{config.HOME}/data/2web/reagle.org/joseph/2005/ethno/field-notes.mm"
    info(f"{biblio=}")
    author = biblio["author"]
    title = biblio["title"]
    subtitle = biblio["subtitle"] if "subtitle" in biblio else ""
    abstract = biblio["comment"]
    excerpt = biblio["excerpt"]
    permalink = biblio["permalink"]

    # Create citation
    for token in ["author", "title", "url", "permalink", "type"]:
        if token in biblio:  # not needed in citation
            del biblio[token]
    citation = ""
    for key, value in list(biblio.items()):
        if key in bf.BIB_FIELDS:
            info(f"{key=} {value=}")
            citation += f"{bf.BIB_FIELDS[key]}={value} "
    citation += f" r={date_read} "
    if biblio["tags"]:
        tags = biblio["tags"]
        for tag in tags.strip().split(" "):
            keyword = KEY_SHORTCUTS.get(tag, tag)
            citation += "kw=" + keyword + " "
        citation = citation.strip()
    else:
        tags = ""

    mindmap = parse(ofile).getroot()
    mm_years = mindmap[0]
    for mm_year in mm_years:
        if mm_year.get("TEXT") == this_year:
            year_node = mm_year
            break
    else:
        print(f"creating {this_year}")
        year_node = SubElement(
            mm_years, "node", {"TEXT": this_year, "POSITION": "right"}
        )
        week_node = SubElement(
            year_node, "node", {"TEXT": this_week, "POSITION": "right"}
        )

    for week_node in year_node:
        if week_node.get("TEXT") == this_week:
            print(f"week {this_week}")
            break
    else:
        print(f"creating {this_week}")
        week_node = SubElement(
            year_node, "node", {"TEXT": this_week, "POSITION": "right"}
        )

    author_node = SubElement(week_node, "node", {"TEXT": author, "STYLE_REF": "author"})
    title_node = SubElement(
        author_node,
        "node",
        {"TEXT": title, "STYLE_REF": "title", "LINK": permalink},
    )
    cite_node = SubElement(  # noqa: F841
        title_node, "node", {"TEXT": citation, "STYLE_REF": "cite"}
    )
    if abstract:
        SubElement(title_node, "node", {"TEXT": abstract, "STYLE_REF": "annotation"})
    if excerpt:
        for excerpt_chunk in excerpt.split("\n\n"):
            info(f"{excerpt_chunk=}")
            if excerpt_chunk.startswith(", "):
                style_ref = "paraphrase"
                excerpt_chunk = excerpt_chunk[2:]
            elif excerpt_chunk.startswith(". "):
                style_ref = "annotation"
                excerpt_chunk = excerpt_chunk[2:]
            elif excerpt_chunk.startswith("-- "):
                style_ref = "default"
                excerpt_chunk = excerpt_chunk[3:]
            else:
                style_ref = "quote"
            SubElement(
                title_node,
                "node",
                {"TEXT": excerpt_chunk, "STYLE_REF": style_ref},
            )

    ElementTree(mindmap).write(ofile, encoding="utf-8")

    if args.publish:
        info("YASN")
        yasn_publish(abstract, title, subtitle, permalink, tags)
