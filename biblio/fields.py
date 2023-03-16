#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Defines the many data schemes (keys, values, and fields)
of bibliographic formats"""

from collections import namedtuple

Date = namedtuple("Date", ["year", "month", "day", "circa", "time"])

#################################################################
# Constants, classes, and mappings
#################################################################

PARTICLES = {
    "al",
    "bin",
    "da",
    "de",
    "de la",
    "Du",
    "la",
    "van",
    "van den",
    "van der",
    "von",
    "Van",
    "Von",
}
SUFFIXES = {"Jr.", "Sr.", "II", "III", "IV"}

ARTICLES = {"a", "an", "the"}
CONJUNCTIONS = {"and", "but", "nor", "or"}
SHORT_PREPOSITIONS = {
    "among",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "out",
    "per",
    "to",
    "upon",
    "with",
}
JUNK_WORDS = {
    "",
    "re",
}
BORING_WORDS = ARTICLES | CONJUNCTIONS | SHORT_PREPOSITIONS | JUNK_WORDS
# BORING_WORDS used in identity_add_title() and bibformat_title()
# Not imported from change_case because it's an expensive import

MONTH2DIGIT = {
    "jan": "1",
    "feb": "2",
    "mar": "3",
    "apr": "4",
    "may": "5",
    "jun": "6",
    "jul": "7",
    "aug": "8",
    "sep": "9",
    "oct": "10",
    "nov": "11",
    "dec": "12",
}
DIGIT2MONTH = {v: k for (k, v) in MONTH2DIGIT.items()}

# happy to keep using biblatex:address alias of biblatex:location
# keep t, ot, and et straight
BIBLATEX_SHORTCUTS = {
    "id": "identifier",
    "a": "address",
    "ad": "addendum",
    "an": "annotation",
    "au": "author",
    "bt": "booktitle",
    "ch": "chapter",
    "doi": "doi",
    "e": "editor",
    "ed": "edition",
    "et": "eventtitle",
    "g": "genre",
    "hp": "howpublished",
    "in": "institution",
    "i": "isbn",
    "j": "journal",
    "kw": "keyword",
    "mm": "custom2",  # mindmap file name
    "nt": "note",
    "or": "organization",
    "ol": "origlanguage",
    "od": "origdate",
    "op": "origpublisher",
    "ot": "type",  # org's manual or report subtype, eg W3C REC
    "ps": "pubstate",  # in press, submitted
    "pp": "pages",
    "pa": "pagination",
    "p": "publisher",
    "r": "custom1",  # read date
    "sc": "school",
    "se": "series",
    "t": "entry_type",  # biblatex type
    "tr": "translator",
    "ti": "title",
    "st": "shorttitle",
    "rt": "retype",
    "v": "volume",
    "is": "issue",
    "n": "number",
    "d": "date",
    "url": "url",
    "urld": "urldate",
    "ve": "venue",
    "c3": "catalog",
    "c4": "custom4",
    "c5": "custom5",
}

CSL_SHORTCUTS = {
    "cj": "c_journal",  # containing_journal
    "cm": "c_magazine",
    "cn": "c_newspaper",
    "cd": "c_dictionary",
    "cy": "c_encyclopedia",
    "cf": "c_forum",  # for post
    "cb": "c_blog",
    "cw": "c_web",
}

BIB_SHORTCUTS = BIBLATEX_SHORTCUTS.copy()
BIB_SHORTCUTS.update(CSL_SHORTCUTS)
BIB_SHORTCUTS_ITEMS = sorted(BIB_SHORTCUTS.items(), key=lambda t: t[1])

BIB_FIELDS = {field: short for (short, field) in BIB_SHORTCUTS.items()}

CSL_FIELDS = {field: short for (short, field) in CSL_SHORTCUTS.items()}

CONTAINERS = list(CSL_SHORTCUTS.values())
# 2020-03-23 why append,
#   leads to duplicate "container-title" errors in YAML parsing
# CONTAINERS.append('organization')

BIBLATEX_TYPES = {
    "article",
    "book",
    "booklet",
    "collection",  # the larger mutli-author book with editor
    "inbook",  # chapter in a book by a single author
    "incollection",  # chapter in multi-authored book with editor
    "inproceedings",
    "manual",
    "mastersthesis",
    "misc",
    "phdthesis",
    "report",
    "unpublished",
    "patent",
    "periodical",
    "proceedings",
    "online",
}

CSL_TYPES = {
    "article",
    "article-magazine",
    "article-newspaper",
    "article-journal",
    "bill",
    "book",
    "broadcast",
    "chapter",
    "dataset",
    "entry",
    "entry-dictionary",
    "entry-encyclopedia",
    "figure",
    "graphic",
    "interview",
    "legislation",
    "legal_case",
    "manuscript",
    "map",
    "motion_picture",
    "musical_score",
    "pamphlet",
    "paper-conference",
    "patent",
    "post",
    "post-weblog",
    "personal_communication",
    "report",
    "review",
    "review-book",
    "song",
    "speech",
    "thesis",
    "treaty",
    "webpage",
}

BIB_TYPES = BIBLATEX_TYPES | CSL_TYPES


# fmt: off
# https://reagle.org/joseph/2013/08/bib-mapping.html
CSL_BIBLATEX_TYPE_MAP = {
    "article-journal":          "article",
    "article-magazine":         "article",
    "article-newspaper":        "article",
    "chapter":                  "incollection",
    "entry":                    "incollection",
    "entry-dictionary":         "inreference",
    "entry-encyclopedia":       "inreference",
    "legal_case":               "misc",
    "manuscript":               "unpublished",
    "thesis":                   "phdthesis",  
    # "thesis":                   "mastersthesis", # TODO: duplicate key
    "pamphlet":                 "booklet",
    "paper-conference":         "inproceedings",
    "personal_communication":   "letter",
    "post":                     "online",
    "post-weblog":              "online",
    "webpage":                  "online"
}

BIBLATEX_CSL_TYPE_MAP = {v: k for k, v in list(CSL_BIBLATEX_TYPE_MAP.items())}

BIBLATEX_CSL_FIELD_MAP = {
    "address":              "publisher-place",
    "annotation":           "abstract",
    "booktitle":            "container-title",
    "chapter":              "chapter-number",
    "doi":                  "DOI",
    "eventtitle":           "event",
    "institution":          "publisher",
    "isbn":                 "ISBN",
    "journal":              "container-title",
    "organization":         "publisher",
    "number":               "issue",
    "type":                 "genre",
    "pages":                "page",
    "pagination":           "locators",
    "school":               "publisher",
    "series":               "collection-title",
    "shorttitle":           "title-short",
    "url":                  "URL",
    "urldate":              "accessed",
    "venue":                "event-place",
    "catalog":              "call-number",
}

CSL_BIBLATEX_FIELD_MAP = {v: k for k, v in list(BIBLATEX_CSL_FIELD_MAP.items())}

# https://en.wikipedia.org/wiki/Template:Citation
BIBLATEX_WP_FIELD_MAP = {
    "c_journal":        "journal",
    "c_magazine":       "magazine",
    "c_newspaper":      "newspaper",
    "c_dictionary":     "work",
    "c_encyclopedia":   "work",
    "c_forum":          "work",
    "c_blog":           "work",
    "c_web":            "work",
    "urldate":          "accessdate",
    "address":          "publication-place",
    "booktitle":        "title",
    "origdate":         "orig-year",
}

# fmt: on

WP_BIBLATEX_FIELD_MAP = {v: k for k, v in list(BIBLATEX_WP_FIELD_MAP.items())}

BIBTEX_FIELDS = {
    "address",
    "annote",
    "author",
    "booktitle",
    "chapter",
    "crossref",
    "edition",
    "editor",
    "howpublished",
    "institution",
    "journal",
    "key",
    "note",
    "number",
    "organization",
    "pages",
    "publisher",
    "school",
    "series",
    "title",
    "type",
    "volume",
}

BIBLATEX_FIELDS = BIBTEX_FIELDS | {
    "addendum",
    "annotation",
    "catalog",
    "custom1",
    "custom2",
    "custom4",
    "custom5",
    "date",
    "doi",
    "entry_type",
    "eventtitle",
    "identifier",
    "isbn",
    "issue",
    "keyword",
    "origdate",
    "origlanguage",
    "origpublisherorigyear",
    "pagination",
    "pubstate",
    "retype",
    "shorttitle",
    "translator",
    "url",
    "urldate",
    "venue",
}

# url not original bibtex standard, but is common,
# so I include it here and also include it in the note in emit_biblatex.

EXCLUDE_URLS = [
    "search?q=cache",
    "proquest",
    "books.google",
    "amazon.com",
    "data/1work/",
]
ONLINE_JOURNALS = [
    "firstmonday.org",
    "media-culture.org",
    "salon.com",
    "slate.com",
]

SITE_CONTAINER_MAP = (
    ("arstechnica.com", "Ars Technica", "c_newspaper"),
    ("atlantic.com", "The Atlantic", "c_magazine"),
    ("boingboing.net", "Boing Boing", "c_blog"),
    ("dailydot", "The Daily Dot", "c_newspaper"),
    ("engadget.com", "Engadget", "c_blog"),
    ("forbes.com", "Forbes", "c_magazine"),
    ("huffingtonpost", "Huffington Post", "c_newspaper"),
    ("lifehacker.com", "Lifehacker", "c_newspaper"),
    ("medium.com", "Medium", "c_blog"),
    ("newyorker.com", "New Yorker", "c_magazine"),
    ("nytimes.com", "The New York Times", "c_newspaper"),
    ("salon.com", "Salon", "c_magazine"),
    ("slate.com", "Slate", "c_magazine"),
    ("techcrunch.com", "TechCrunch", "c_newspaper"),
    ("theguardian", "The Guardian", "c_newspaper"),
    ("verge.com", "The Verge", "c_newspaper"),
    ("Wikipedia_Signpost", "Wikipedia Signpost", "c_web"),
    ("wired.com", "Wired", "c_magazine"),
    ("wsj.com", "The Wall Street Journal", "c_newspaper"),
    ("washingtonpost.com", "The Washington Post", "c_newspaper"),
    ("fourhourworkweek.com", "4-Hour Workweek", "c_blog"),
    # ('', '',  'c_magazine'),
)
