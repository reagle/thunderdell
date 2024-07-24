"""Mindmap logger.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging as log
import time
from xml.etree.ElementTree import ElementTree, SubElement, parse  # Element,

import config
from biblio import fields as bf
from biblio.keywords import KEY_SHORTCUTS
from utils.web import yasn_publish

from .annotate import do_console_annotation

NOW = time.localtime()
CURLY_TABLE = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


def straighten_quotes(text):
    """
    Convert curly quotes to straight quotes.

    >>> straighten_quotes('Hello “world”')
    'Hello "world"'
    >>> straighten_quotes('“Curly” quotes')
    '"Curly" quotes'
    >>> straighten_quotes("It's a ‘quoted’ text")
    "It's a 'quoted' text"
    >>> straighten_quotes(None)
    None
    """
    if text is None:
        return None
    return text.translate(CURLY_TABLE)


def log2mm(args, biblio):
    """
    Log to bibliographic mindmap, see:
        http://reagle.org/joseph/2009/01/thunderdell.html
    """

    print("to log2mm")
    biblio, args.publish = do_console_annotation(args, biblio)
    log.info(f"{biblio}")

    this_week = time.strftime("%U", NOW)
    this_year = time.strftime("%Y", NOW)
    date_read = time.strftime("%Y%m%d %H:%M UTC", NOW)

    ofile = config.HOME / "data/2web/reagle.org/joseph/2005/ethno/field-notes.mm"
    log.info(f"{biblio=}")
    author = biblio["author"]
    title = biblio["title"]
    subtitle = biblio.get("subtitle", "")
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
            log.info(f"{key=} {value=}")
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

    mindmap = parse(str(ofile)).getroot()
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
        {
            "TEXT": title,
            "STYLE_REF": "title",
            "FORMAT": "markdownPatternFormat",
            "LINK": permalink,
        },
    )
    cite_node = SubElement(  # noqa: F841
        title_node,
        "node",
        {"TEXT": citation, "STYLE_REF": "cite", "FORMAT": "markdownPatternFormat"},
    )
    if abstract:
        SubElement(
            title_node,
            "node",
            {
                "TEXT": abstract,
                "STYLE_REF": "annotation",
                "FORMAT": "markdownPatternFormat",
            },
        )
    if excerpt:
        for excerpt_chunk in excerpt.split("\n\n"):
            log.info(f"{excerpt_chunk=}")
            if excerpt_chunk == "":
                continue
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
                {
                    "TEXT": excerpt_chunk,
                    "STYLE_REF": style_ref,
                    "FORMAT": "markdownPatternFormat",
                },
            )

    ElementTree(mindmap).write(str(ofile), encoding="utf-8")

    if args.publish:
        log.info("YASN")
        yasn_publish(abstract, title, subtitle, permalink, tags)
