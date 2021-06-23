#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Thunderdell, by Joseph Reagle http://reagle.org/joseph/

Extract a bibliography from a Freeplane mindmap"""

# TODO

import calendar
import errno
import http.server
import logging
import os
import re
import sys
import unicodedata
import urllib.parse
import webbrowser
from collections import namedtuple
from html import escape
from subprocess import call  # needed for testing
from typing import Dict, List, NamedTuple, Optional, Set, Tuple
from urllib.parse import parse_qs
from xml.etree.ElementTree import parse

from web_utils import escape_XML, unescape_XML

log_level = logging.ERROR  # 40 # declared here for when imported

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

useLXML = False
# HOME for path of mindmaps on webhost
HOME = os.path.expanduser("~")
# CLIENT_HOME for path on the client to open mindmaps there
# as f'file://{CLIENT_HOME}/...'
CLIENT_HOME = "/Users/reagle"
DEFAULT_MAP = f"{HOME}/joseph/readings.mm"
DEFAULT_PRETTY_MAP = f"{HOME}/joseph/2005/ethno/field-notes.mm"
CGI_DIR = f"{HOME}/joseph/plan/cgi-bin/"  # for local server

TMP_DIR = f"{HOME}/tmp/.td/"
if not os.path.isdir(TMP_DIR):
    os.makedirs(TMP_DIR)

#################################################################
# Constants, classes, and mappings
#################################################################
# yapf: disable

Date = namedtuple('Date', ['year', 'month', 'day', 'circa', 'time'])

PARTICLES = {"al", "bin", "da", "de", "de la", "Du", "la",
             "van", "van den", "van der", "von",
             "Van", "Von"}
SUFFIXES = {"Jr.", "Sr.", "II", "III", "IV"}

ARTICLES = {'a', 'an', 'the'}
CONJUNCTIONS = {'and', 'but', 'nor', 'or'}
SHORT_PREPOSITIONS = {'among', 'as', 'at', 'by', 'for', 'from', 'in',
                      'of', 'on', 'out', 'per', 'to', 'upon', 'with', }
JUNK_WORDS = {'', 're', }
BORING_WORDS = ARTICLES | CONJUNCTIONS | SHORT_PREPOSITIONS | JUNK_WORDS
# BORING_WORDS used in identity_add_title() and bibformat_title()
# Not imported from change_case because it's an expensive import

MONTH2DIGIT = {
    'jan': '1', 'feb': '2', 'mar': '3',
    'apr': '4', 'may': '5', 'jun': '6',
    'jul': '7', 'aug': '8', 'sep': '9',
    'oct': '10', 'nov': '11', 'dec': '12'}
DIGIT2MONTH = {v: k for (k, v) in MONTH2DIGIT.items()}

# happy to keep using biblatex:address alias of biblatex:location
# keep t, ot, and et straight
BIBLATEX_SHORTCUTS = dict([
    ('id', 'identifier'),
    ('a', 'address'),
    ('ad', 'addendum'),
    ('an', 'annotation'),
    ('au', 'author'),
    ('bt', 'booktitle'),
    ('ch', 'chapter'),
    ('doi', 'doi'),
    ('e', 'editor'),
    ('ed', 'edition'),
    ('et', 'eventtitle'),
    ('g', 'genre'),
    ('hp', 'howpublished'),
    ('in', 'institution'),
    ('i', 'isbn'),
    ('j', 'journal'),
    ('kw', 'keyword'),
    ('mm', 'custom2'),     # mindmap file name
    ('nt', 'note'),
    ('or', 'organization'),
    ('ol', 'origlanguage'), ('od', 'origdate'), ('op', 'origpublisher'),
    ('ot', 'type'),        # org's manual or report subtype, eg W3C REC
    ('ps', 'pubstate'),    # in press, submitted
    ('pp', 'pages'),
    ('pa', 'pagination'),
    ('p', 'publisher'),
    ('r', 'custom1'),      # read date
    ('sc', 'school'),
    ('se', 'series'),
    ('t', 'entry_type'),   # biblatex type
    ('tr', 'translator'),
    ('ti', 'title'), ('st', 'shorttitle'),
    ('rt', 'retype'),
    ('v', 'volume'), ('is', 'issue'), ('n', 'number'),
    ('d', 'date'),
    ('url', 'url'),
    ('urld', 'urldate'),
    ('ve', 'venue'),
    ('c3', 'catalog'), ('c4', 'custom4'), ('c5', 'custom5'),
])

CSL_SHORTCUTS = dict([
    # title (csl:container) fields that also give type
    # hints towards the richer csl:types
    ('cj', 'c_journal'),  # containing_journal
    ('cm', 'c_magazine'),
    ('cn', 'c_newspaper'),
    ('cd', 'c_dictionary'),
    ('cy', 'c_encyclopedia'),
    ('cf', 'c_forum'),  # for post
    ('cb', 'c_blog'),
    ('cw', 'c_web'),
])

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
    'article',
    'book',
    'booklet',
    'collection',    # the larger mutli-author book with editor
    'inbook',        # chapter in a book by a single author
    'incollection',  # chapter in multi-authored book with editor
    'inproceedings',
    'manual',
    'mastersthesis',
    'misc',
    'phdthesis',
    'report',
    'unpublished',
    'patent',
    'periodical',
    'proceedings',
    'online',
}

CSL_TYPES = {
    'article',
    'article-magazine',
    'article-newspaper',
    'article-journal',
    'bill',
    'book',
    'broadcast',
    'chapter',
    'dataset',
    'entry',
    'entry-dictionary',
    'entry-encyclopedia',
    'figure',
    'graphic',
    'interview',
    'legislation',
    'legal_case',
    'manuscript',
    'map',
    'motion_picture',
    'musical_score',
    'pamphlet',
    'paper-conference',
    'patent',
    'post',
    'post-weblog',
    'personal_communication',
    'report',
    'review',
    'review-book',
    'song',
    'speech',
    'thesis',
    'treaty',
    'webpage',
}

BIB_TYPES = BIBLATEX_TYPES | CSL_TYPES

# https://reagle.org/joseph/2013/08/bib-mapping.html
CSL_BIBLATEX_TYPE_MAP = dict([
    # ordering is important so in the reverse mapping online => webpage
    ('article-journal',         'article'),
    ('article-magazine',        'article'),
    ('article-newspaper',       'article'),
    ('chapter',                 'incollection'),
    ('entry',                   'incollection'),
    ('entry-dictionary',        'inreference'),
    ('entry-encyclopedia',      'inreference'),
    ('legal_case',              'misc'),
    ('manuscript',              'unpublished'),
    ('thesis',                  'phdthesis'),  # TODO: duplicate key
    ('thesis',                  'mastersthesis'),
    ('pamphlet',                'booklet'),
    ('paper-conference',        'inproceedings'),
    ('personal_communication',  'letter'),
    ('post',                    'online'),
    ('post-weblog',             'online'),
    ('webpage',                 'online'),
])

BIBLATEX_CSL_TYPE_MAP = dict((v, k) for k, v in
                             list(CSL_BIBLATEX_TYPE_MAP.items()))

BIBLATEX_CSL_FIELD_MAP = dict([
    ('address',        'publisher-place'),
    ('annotation',     'abstract'),
    ('booktitle',      'container-title'),
    ('chapter',        'chapter-number'),
    ('doi',            'DOI'),
    ('eventtitle',     'event'),
    ('institution',    'publisher'),
    ('isbn',           'ISBN'),
    ('journal',        'container-title'),
    ('organization',   'publisher'),
    ('number',         'issue'),
    ('type',           'genre'),
    ('pages',          'page'),
    ('pagination',     'locators'),
    ('school',         'publisher'),
    ('series',         'collection-title'),
    ('shorttitle',     'title-short'),
    ('url',            'URL'),
    ('urldate',        'accessed'),
    ('venue',          'event-place'),
    ('catalog',        'call-number'),
])

CSL_BIBLATEX_FIELD_MAP = dict((v, k) for k, v in
                              list(BIBLATEX_CSL_FIELD_MAP.items()))

# https://en.wikipedia.org/wiki/Template:Citation
BIBLATEX_WP_FIELD_MAP = dict([
    ('c_journal',       'journal'),
    ('c_magazine',      'magazine'),
    ('c_newspaper',     'newspaper'),
    ('c_dictionary',    'work'),
    ('c_encyclopedia',  'work'),
    ('c_forum',         'work'),
    ('c_blog',          'work'),
    ('c_web',           'work'),
    ('urldate',         'accessdate'),
    ('address',         'publication-place'),
    ('booktitle',       'title'),
    ('origdate',        'orig-year'),
])

WP_BIBLATEX_FIELD_MAP = dict((v, k) for k, v in
                             list(BIBLATEX_WP_FIELD_MAP.items()))

BIBTEX_FIELDS = {
    'address', 'annote', 'author', 'booktitle', 'chapter',
    'crossref', 'edition', 'editor', 'howpublished', 'institution', 'journal',
    'key', 'note', 'number', 'organization', 'pages', 'publisher',
    'school', 'series', 'title', 'type', 'volume'}

BIBLATEX_FIELDS = BIBTEX_FIELDS | {
    'addendum', 'annotation',
    'catalog', 'custom1', 'custom2', 'custom4', 'custom5',
    'date', 'doi', 'entry_type', 'eventtitle',
    'identifier', 'isbn', 'issue', 'keyword',
    'origdate', 'origlanguage', 'origpublisher''origyear',
    'pagination', 'pubstate', 'retype', 'shorttitle',
    'translator', 'url', 'urldate', 'venue'}

# url not original bibtex standard, but is common,
# so I include it here and also include it in the note in emit_biblatex.

# yapf: enable
#################################################################
# Utility functions
#################################################################


def pretty_tabulate_list(mylist, cols=3):
    pairs = [
        "\t".join(["%20s" % j for j in mylist[i : i + cols]])
        for i in range(0, len(mylist), cols)
    ]
    print(("\n".join(pairs)))
    print("\n")


def pretty_tabulate_dict(mydict, cols=3):
    pretty_tabulate_list(
        sorted([f"{key}:{value}" for key, value in list(mydict.items())]), cols
    )


def escape_latex(text):
    text = (
        text.replace("$", r"\$")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\~{}")
        .replace("^", r"\^{}")
    )
    return text


def strip_accents(text):
    """strip accents and those chars that can't be stripped"""
    # >>> strip_accents(u'nôn-åscîî')
    # ^ fails because of doctest bug u'non-ascii'
    try:  # test if ascii
        text.encode("ascii")
    except UnicodeEncodeError:
        return "".join(
            x
            for x in unicodedata.normalize("NFKD", text)
            if unicodedata.category(x) != "Mn"
        )
    else:
        return text


def normalize_whitespace(text):
    """Remove redundant whitespace from a string, including before comma
    >>> normalize_whitespace('sally, joe , john')
    'sally, joe, john'

    """
    text = text.replace(" ,", ",")
    text = " ".join(text.split())
    return text


#################################################################
# Entry construction
#################################################################


def identity_add_title(ident, title):
    """Return a non-colliding identity.

    Disambiguate keys by appending the first letter of first
    3 significant words (i.e., no WP:namespace, articles, conjunctions
    or short prepositions). If only one word, use first, penultimate,
    and last character.

    >>> identity_add_title('Wikipedia 2008', 'Wikipedia:Neutral Point of View')
    'Wikipedia 2008npv'

    """
    # dbg(f"title = '{title}'")
    suffix = ""
    clean_title = (
        title.replace("Wikipedia:", "")
        .replace("Category:", "")
        .replace("WikiEN-l", "")
        .replace("Wikipedia-l", "")
        .replace("Wiki-l", "")
        .replace("Wiktionary-l", "")
        .replace("Foundation-l", "")
        .replace("Textbook-l", "")
        .replace(".0", "")
        .replace("'", "")
    )

    NOT_ALPHANUM_PAT = re.compile("[^a-zA-Z0-9']")
    title_words = NOT_ALPHANUM_PAT.split(clean_title.lower())

    if len(title_words) == 1:
        suffix = f"{title_words[0][0]}{title_words[0][-2]}{title_words[0][-1]}"
    else:
        suffix = "".join(
            [word[0] for word in title_words if word not in BORING_WORDS]
        )
        suffix = suffix[:3]
    ident = f"{ident}{suffix}"
    return ident


def identity_increment(ident, entries):
    """Increment numerical suffix of identity until no longer collides with
    pre-existing entry(s) in the entries dictionary.

    >>> identity_increment('Wikipedia 2008npv',\
    {'Wikipedia 2008npv': {'title': 'Wikipedia:No Point of View',\
    'author': [('', '', 'Wikipedia', '')], 'date': '2008'}})
    'Wikipedia 2008npv1'

    """

    while ident in entries:  # if it still collides
        # dbg(f"\t trying     {ident} crash w/ {entries[ident]['title']}")
        if ident[-1].isdigit():
            suffix = int(ident[-1])
            suffix += 1
            ident = f"{ident[0:-1]}{suffix}"
        else:
            ident += "1"
        # dbg(f'\t yielded    {ident}')
    return ident


def get_ident(entry, entries, delim=""):
    """Create an identifier (key) for the entry"""

    # debug(f"1 {entry=}")
    last_names = []
    for first, von, last, jr in entry["author"]:
        last_names.append(f"{von}{last}".replace(" ", ""))
    if len(last_names) == 1:
        name_part = last_names[0]
    elif len(last_names) == 2:
        name_part = delim.join(last_names[0:2])
    elif len(last_names) == 3:
        name_part = delim.join(last_names[0:3])
    elif len(last_names) > 3:
        name_part = f"{last_names[0]}Etal"

    if "date" not in entry:
        entry["date"] = Date(
            year="0000", month=None, day=None, circa=None, time=None
        )
    year_delim = delim if delim else ""
    # debug(f"2 entry['date'] = {entry['date']}")
    ident = year_delim.join((name_part, entry["date"].year))
    # debug(f"3 ident = {type(ident)} '{ident}'")
    ident = (
        ident.replace(":", "")
        .replace("'", "")  # not permitted in xml name/id attributes
        .replace(".", "")  # punctuation
        .replace("@", "")
        .replace("[", "")
        .replace("]", "")
        .replace("<strong>", "")  # '@' citation designator
        .replace("</strong>", "")  # added by walk_freeplane.query_highlight
    )
    # debug(f"4 ident = {type(ident)} '{ident}'")
    ident = strip_accents(ident)  # unicode buggy in bibtex keys
    if ident[0].isdigit():  # pandoc forbids keys starting with digits
        ident = f"a{ident}"

    ident = identity_add_title(ident, entry["title"])  # get title suffix
    if ident in entries:  # there is a collision
        warning(
            f"collision on {ident}: {entry['title']} & {entries[ident]['title']}"
        )
        ident = identity_increment(ident, entries)
    # debug(f"5 ident = {type(ident)} '{ident}' in {entry['_mm_file']}")
    return ident


def parse_date(when: str) -> NamedTuple:
    """parse dates that starts with 'YYYY' and returns named tuple.
    Without hyphens, strings such as '101210' are ambiguous: years
    have precedence.

    >>> parse_date('20190820 22:24 UTC')
    Date(year='2019', month='08', day='20', circa=None, time='22:24 UTC')
    >>> parse_date('20190820')
    Date(year='2019', month='08', day='20', circa=None, time=None)
    >>> parse_date('101210')
    Date(year='1012', month='10', day=None, circa=None, time=None)
    >>> parse_date('-5')
    Date(year='-5', month=None, day=None, circa=None, time=None)
    >>> parse_date('130~')
    Date(year='130', month=None, day=None, circa=True, time=None)
    """

    year = month = day = circa = time = None
    if " " in when:
        when, time = when.split(" ", 1)
    if when.endswith("~"):
        when = when[:-1]
        circa = True
    if len(when) == 8:
        year = when[0:4]
        month = when[4:6]
        day = when[6:8]
    elif len(when) == 6:
        year = when[0:4]
        month = when[4:6]
    elif len(when) <= 4:
        year = when[0:4]
    else:
        raise Exception(f"{when} is malformed")
    return Date(year, month, day, circa, time)


def pull_citation(entry):
    """Modifies entry with parsed citation

    Uses this convention: "d=20030723 j=Research Policy v=32 n=7 pp=1217-1241"

    """

    entry["custom2"] = entry["_mm_file"].split("/")[-1]

    if "cite" in entry:
        citation = entry["cite"]
        # split around tokens of length 1-3 and
        EQUAL_PAT = re.compile(r"(\w{1,3})=")
        # get rid of first empty string of results
        cites = EQUAL_PAT.split(citation)[1:]
        # 2 refs to an iterable are '*' unpacked and rezipped
        cite_pairs = zip(*[iter(cites)] * 2)
        for short, value in cite_pairs:
            try:
                entry[BIB_SHORTCUTS[short]] = value.strip()
            except KeyError as error:
                print(
                    ("Key error on ", error, entry["title"], entry["_mm_file"])
                )

    # if 'url' in entry and entry['url'] is not None:
    #     if any([site in entry['url'] for site in ('books.google', 'jstor')]):
    #         entry['url'] = entry['url'].split('&')[0]

    if "date" in entry:
        entry["date"] = parse_date(entry["date"])

    if "custom1" in entry and "url" in entry:  # read/accessed date for URLs
        entry["urldate"] = parse_date(entry["custom1"])
        del entry["custom1"]

    if "origdate" in entry:  # original date of publication
        entry["origdate"] = parse_date(entry["origdate"])

    if ": " in entry["title"]:
        if not entry["title"].startswith("Re:"):
            entry["shorttitle"] = entry["title"].split(":")[0].strip()

    if "url" in entry and "oldid" in entry["url"]:
        url = entry["url"]
        url = url.rsplit("#", 1)[0]  # remove fragment
        query = url.split("?", 1)[1]
        queries = parse_qs(query)
        oldid = queries["oldid"][0]
        entry["shorttitle"] = f'{entry["title"]} (oldid={oldid})'
        if not args.long_url:  # short URLs
            base = f'http://{url.split("/")[2]}'
            oldid = f"/?oldid={oldid}"
            diff = f"&diff={queries['diff'][0]}" if "diff" in queries else ""
            entry["url"] = f"{base}{oldid}{diff}"

    if "editor" in entry:
        entry["editor"] = parse_names(entry["editor"])
    if "translator" in entry:
        entry["translator"] = parse_names(entry["translator"])


#################################################################
# Biblatex utilities
#################################################################


def create_biblatex_author(names):
    """Return the parts of the name joined appropriately.
    The BibTex name parsing is best explained in
    http://www.tug.org/TUGboat/tb27-2/tb87hufflen.pdf

    >>> create_biblatex_author([('First Middle', 'von', 'Last', 'Jr.'),\
        ('First', '', 'Last', 'II')])
    'von Last, Jr., First Middle and Last, II, First'

    """
    full_names = []

    for name in names:
        full_name = ""
        first, von, last, jr = name[0:4]

        if all(s.islower() for s in (first, last)):  # {{hooks}, {bell}}
            first = f"{{first}}"
            last = f"{{last}}"

        if von != "":
            full_name += von + " "
        if last != "":
            full_name += last
        if jr != "":
            full_name += ", " + jr
        if first != "":
            full_name += ", " + first
        full_names.append(full_name)

    full_names = " and ".join(full_names)
    full_names = normalize_whitespace(full_names)
    return full_names


# yapf: disable
def guess_biblatex_type(entry):
    """Guess whether the type of this entry is book, article, etc.

    >>> guess_biblatex_type({'author': [('', '', 'Smith', '')],\
        'eventtitle': 'Proceedings of WikiSym 08',\
        'publisher': 'ACM',\
        'title': 'A Great Paper',\
        'venue': 'Porto, Portugal California',\
        'date': '2008'})
    'inproceedings'

    """
    if 'entry_type' in entry:         # already has a type
        e_t = entry['entry_type']
        if e_t in BIBLATEX_TYPES:
            pass
        elif e_t in CSL_TYPES:
            e_t = CSL_BIBLATEX_TYPE_MAP[e_t]
        else:
            print(f"Unknown entry_type = {e_t}")
            sys.exit()
        return e_t
    if 'entry_type' in entry:         # already has a type
        return entry['entry_type']
    else:
        e_t = 'misc'
        if 'eventtitle' in entry:
            if 'author' in entry:           e_t = 'inproceedings'
            else:                           e_t = 'proceedings'
        elif 'booktitle' in entry:
            if 'editor' not in entry:       e_t = 'inbook'
            else:
                if 'author' in entry or \
                    'chapter' in entry:      e_t = 'incollection'
                else:                        e_t = 'collection'
        elif 'journal' in entry:             e_t = 'article'

        elif 'author' in entry and 'title' in entry and 'publisher' in entry:
                                            e_t = 'book'
        elif 'institution' in entry:
            e_t = 'report'
            if 'type' in entry:
                if 'report' in entry['type'].lower(): e_t = 'report'
                if 'thesis' in entry['type'].lower(): e_t = 'mastersthesis'
                if 'dissertation' in entry['type'].lower(): e_t = 'phdthesis'
        elif 'url' in entry:                e_t = 'online'
        elif 'doi' in entry:                e_t = 'online'
        elif 'date' not in entry:           e_t = 'unpublished'

        return e_t

def guess_csl_type(entry):
    """Guess whether the type of this entry is book, article, etc.

    >>> guess_csl_type({'author': [('', '', 'Smith', '')],\
        'eventtitle': 'Proceedings of WikiSym 08',\
        'publisher': 'ACM',\
        'title': 'A Great Paper',\
        'venue': 'Porto, Portugal California',\
        'date': '2008'})
    ('paper-conference', None, None)

    """
    genre = None
    medium = None
    if 'entry_type' in entry:         # already has a type
        et = entry['entry_type']
        if et in CSL_TYPES:
            return et, genre, medium
        elif et in BIBLATEX_TYPES:
            if et == 'mastersthesis':
                return 'thesis', "Master's thesis", medium
            elif et == 'phdthesis':
                return 'thesis', "PhD thesis", medium
            else:
                return BIBLATEX_CSL_TYPE_MAP[et], genre, medium
        else:
            print(f"Unknown entry_type = {et}")
            sys.exit()
    et = 'no-type'
    # debug(f"looking at containers for {entry}")
    if 'c_web' in entry:                et = 'webpage'
    elif 'c_blog' in entry:             et = 'post-weblog'
    elif 'c_newspaper' in entry:        et = 'article-newspaper'
    elif 'c_magazine' in entry:         et = 'article-magazine'
    elif 'c_journal' in entry:          et = 'article-journal'
    elif 'c_dictionary' in entry:       et = 'entry-dictionary'
    elif 'c_encyclopedia' in entry:     et = 'entry-encyclopedia'
    elif 'c_forum' in entry:            et = 'post'
    else:
        if 'eventtitle' in entry:           et = 'paper-conference'
        elif 'booktitle' in entry:
            if 'editor' in entry:           # collection or incollection
                if 'chapter' in entry:      et = 'chapter'
                else:                       et = 'book'   # ? collection
            elif 'organization' in entry:   et = 'paper-conference'
            else:                           et = 'chapter'
        elif 'journal' in entry:            et = 'article-journal'

        elif 'author' in entry and 'title' in entry and 'publisher' in entry:
                                            et = 'book'
        elif 'author' not in entry:
            if 'venue' in entry:            et = 'book'         # ? proceedings
            if 'editor' in entry:           et = 'book'         # ? collection
        elif 'institution' in entry:
            et = 'report'
            if 'type' in entry:
                org_subtype = entry['type'].lower()
                if 'report' in org_subtype: et = 'report'
                if 'thesis' in org_subtype or 'dissertation' in org_subtype:
                                            et = 'thesis'
        elif 'url' in entry:                et = 'webpage'
        elif 'doi' in entry:                et = 'article'
        elif 'date' not in entry:           et = 'manuscript'
    return et, genre, medium
# yapf: enable


def bibformat_title(title):
    """Title case text, and preserve/bracket proper names/nouns
    See http://nwalsh.com/tex/texhelp/bibtx-24.html
    >>> bibformat_title("Wikirage: What's hot now on Wikipedia")
    "{Wikirage:} {What's} Hot Now on {Wikipedia}"
    >>> bibformat_title('Re: "Suicide methods" article')
    "{Re:} `{Suicide} Methods' Article"
    >>> bibformat_title('''"Am I ugly?": The "disturbing" teen YouTube trend''')
    "`Am {I} Ugly?': {The} `Disturbing' Teen {YouTube} Trend"

    """
    cased_title = quoted_title = []

    WORDS2PROTECT = {"vs.", "oldid"}

    WHITESPACE_PAT = re.compile(r"""(\s+['(`"]?)""", re.UNICODE)  # \W+
    words = WHITESPACE_PAT.split(title)

    CHUNK_PAT = re.compile(r"""([-:])""", re.UNICODE)

    def my_title(text):
        """title case after some chars, but not ['.] like .title()"""

        text_list = list(text)
        text_list[0] = text_list[0].upper()
        for chunk in CHUNK_PAT.finditer(text):
            index = chunk.start()
            if index + 1 < len(text_list):
                text_list[index + 1] = text_list[index + 1].upper()
        return "".join(text_list)

    for word in words:
        if len(word) > 0:
            # debug(f"word = '{word}'")
            if not (word[0].isalpha()):
                # debug("not (word[0].isalpha())")
                cased_title.append(word)
            elif word in BORING_WORDS:  # imported from change_case.py
                # debug("word in BORING_WORDS")
                cased_title.append(word)
            elif word in WORDS2PROTECT:
                # debug(f"protecting lower '{word}'")
                cased_title.append(f"{{word}}")
            elif word[0].isupper():
                # debug(f"protecting title '{word}'")
                cased_title.append(f"{{{my_title(word)}}}")
            else:
                # debug("else nothing")
                cased_title.append(my_title(word))
    quoted_title = "".join(cased_title)

    # convert quotes to LaTeX then convert doubles to singles within the title
    if quoted_title[0] == '"':  # First char is a quote
        quoted_title = f"``{quoted_title[1:]}"
    # open quote
    quoted_title = quoted_title.replace(' "', " ``").replace(" '", " `")
    # close quote
    quoted_title = quoted_title.replace('" ', "'' ")
    # left-over close quote
    quoted_title = quoted_title.replace('"', "''")
    # single quotes
    quoted_title = quoted_title.replace("``", "`").replace("''", "'")

    return quoted_title


#################################################################
# Emitters
#################################################################

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


def emit_biblatex(entries):
    """Emit a biblatex file"""
    # dbg(f"entries = '{entries}'")

    for key, entry in sorted(entries.items()):
        entry_type = guess_biblatex_type(entry)
        entry_type_copy = entry_type
        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        if entry["ori_author"] in container_values:
            if not args.author_create:
                del entry["author"]
            else:
                entry["author"] = [["", "", "".join(entry["ori_author"]), ""]]

        # if an edited collection, remove author and booktitle
        if all(f in entry for f in ("author", "editor", "title", "booktitle")):
            if (
                entry["author"] == entry["editor"]
                and entry["title"] == entry["booktitle"]
            ):
                del entry["author"]
                del entry["booktitle"]

        # CSL type and field conversions
        # debug(f"{entry=}")
        for field in ("c_blog", "c_web", "c_forum"):
            if field in entry:
                entry_type_copy = "online"
                entry["organization"] = entry[field]
                del entry[field]
                continue
        for field in ("c_journal", "c_magazine", "c_newspaper"):
            if field in entry:
                entry_type_copy = "article"
                entry["journal"] = entry[field]
                del entry[field]
                continue
        for field in ("c_dictionary", "c_encyclopedia"):
            if field in entry:
                entry_type_copy = "inreference"
                entry["booktitle"] = entry[field]
                del entry[field]
                continue

        args.outfd.write(f'@{entry_type_copy}{{{entry["identifier"]},\n')

        for short, field in BIB_SHORTCUTS_ITEMS:
            if field in entry and entry[field] is not None:
                # critical(f"short, field = '{short} , {field}'")
                # skip these fields
                value = entry[field]
                if field in ("identifier", "entry_type", "ori_author"):
                    continue
                if field == "urldate" and "url" not in entry:
                    continue  # no url, no 'read on'
                if field in ("url"):
                    # debug(f"url = {value}")
                    if any(ban for ban in EXCLUDE_URLS if ban in value):
                        # debug("banned")
                        continue
                    # if online_only and not (online or online journal)
                    if args.urls_online_only and not (
                        entry_type == "online"
                        or any(j for j in ONLINE_JOURNALS if j in entry["url"])
                    ):
                        # debug("not online")
                        continue

                # if value not a proper string, make it so
                # debug(f"{value=}; type = {type(value)}")
                if field in ("author", "editor", "translator"):
                    value = create_biblatex_author(value)
                if field in ("date", "urldate", "origdate"):
                    date = "-".join(
                        filter(None, (value.year, value.month, value.day))
                    )
                    date = date + "~" if value.circa else date
                    value = date

                # escape latex brackets.
                #   url and howpublished shouldn't be changed
                #   author may have curly brackets that should not be escaped
                #   date is a named_tuple that doesn't need escaping
                # debug(f"{field}")
                if field not in (
                    "author",
                    "url",
                    "howpublished",
                    "date",
                    "origdate",
                    "urldate",
                ):
                    value = escape_latex(value)

                # protect case in titles
                if field in ("title", "shorttitle"):
                    value = bibformat_title(value)

                args.outfd.write(f"   {field} = {{{value}}},\n")
        args.outfd.write("}\n")


def emit_yaml_csl(entries):
    """Emit citations in YAML/CSL for input to pandoc

    See: https://reagle.org/joseph/2013/08/bib-mapping.html
        http://www.yaml.org/spec/1.2/spec.html
        http://jessenoller.com/blog/2009/04/13/yaml-aint-markup-language-completely-different

    """
    # import yaml

    def escape_yaml(s):
        if s:  # faster to just quote than testing for tokens
            s = s.replace('"', r"'")
            # s = s.replace("#", r"\#") # this was introducing slashes in URLs
            s = s.replace("@", r"\\@")  # single slash caused bugs in past
            s = f'"{s}"'
        return s

    def emit_yaml_people(people):
        """yaml writer for authors and editors"""

        for person in people:
            # debug("person = '%s'" % (' '.join(person)))
            # biblatex ('First Middle', 'von', 'Last', 'Jr.')
            # CSL ('family', 'given', 'suffix' 'non-dropping-particle',
            #      'dropping-particle')
            given, particle, family, suffix = person
            args.outfd.write(f"  - family: {escape_yaml(family)}\n")
            if given:
                args.outfd.write(f"    given: {escape_yaml(given)}\n")
                # args.outfd.write('    given:\n')
                # for given_part in given.split(' '):
                #     args.outfd.write('    - %s\n' % escape_yaml(given_part))
            if suffix:
                args.outfd.write(f"    suffix: {escape_yaml(suffix)}\n")
            if particle:
                args.outfd.write(
                    f"    non-dropping-particle: " f"{escape_yaml(particle)}\n"
                )

    def emit_yaml_date(date, season=None):
        """yaml writer for dates"""

        if date.year:
            args.outfd.write(f"    year: {date.year}\n")
        if date.month:
            args.outfd.write(f"    month: {date.month}\n")
        if date.day:
            args.outfd.write(f"    day: {date.day}\n")
        if date.circa:
            args.outfd.write(f"    circa: true\n")
        if season:
            args.outfd.write(f"    season: {season}\n")

    def yaml_protect_case(title):
        """Preserve/bracket proper names/nouns
        https://github.com/jgm/pandoc-citeproc/blob/master/man/pandoc-citeproc.1.md
        >>> yaml_protect_case("The iKettle – a world off its rocker")
        "The <span class='nocase'>iKettle</span> – a world off its rocker"
        """
        PROTECT_PAT = re.compile(
            r"""
            \b # empty string at beginning or end of word
            (
            [a-z]+ # one or more lower case
            [A-Z\./] # capital, period, or forward slash
            \S+ # one or more non-whitespace
            )
            \b # empty string at beginning or end of word
            """,
            re.VERBOSE,
        )
        return PROTECT_PAT.sub(r"<span class='nocase'>\1</span>", title)

    # begin YAML file
    # http://blog.martinfenner.org/2013/07/30/citeproc-yaml-for-bibliographies/#citeproc-yaml
    args.outfd.write("---\n")
    args.outfd.write("references:\n")

    for key, entry in sorted(entries.items()):
        entry_type, genre, medium = guess_csl_type(entry)
        args.outfd.write(f'- id: {entry["identifier"]}\n')
        args.outfd.write(f"  type: {entry_type}\n")
        if genre:
            args.outfd.write(f"  genre: {genre}\n")
        if medium:
            args.outfd.write(f"  medium: {medium}\n")

        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        if entry["ori_author"] in container_values:
            if not args.author_create:
                del entry["author"]
            else:
                entry["author"] = [["", "", "".join(entry["ori_author"]), ""]]

        for short, field in BIB_SHORTCUTS_ITEMS:
            if field in entry and entry[field] is not None:
                value = entry[field]
                # debug(f"short, field = '{short} , {field}'")
                # skipped fields
                if field in ("identifier", "entry_type", "issue"):
                    continue

                # special format fields
                if field == "title":
                    title = yaml_protect_case(escape_yaml((value)))
                    args.outfd.write(f"  title: {title}\n")
                    continue
                if field in ("author", "editor", "translator"):
                    args.outfd.write(f"  {field}:\n")
                    emit_yaml_people(value)
                    continue
                if field in ("date", "origdate", "urldate"):
                    # debug(f'field = {field}')
                    if value == "0000":
                        continue
                    if field == "date":
                        # debug(f"value = '{value}'")
                        season = entry["issue"] if "issue" in entry else None
                        args.outfd.write("  issued:\n")
                        emit_yaml_date(value, season)
                    if field == "origdate":
                        # debug(f"value = '{value}'")
                        args.outfd.write("  original-date:\n")
                        emit_yaml_date(value)
                    if field == "urldate":
                        args.outfd.write("  accessed:\n")
                        emit_yaml_date(value)
                    continue

                if field == "urldate" and "url" not in entry:
                    continue  # no url, no 'read on'
                if field == "url":
                    # debug(f"url = {value}")
                    if any(ban for ban in EXCLUDE_URLS if ban in value):
                        # debug("banned")
                        continue
                    # skip articles+URL w/ no pagination & other offline types
                    if args.urls_online_only:
                        # debug("urls_online_only TRUE")
                        if entry_type in {"post", "post-weblog", "webpage"}:
                            # debug(f"  not skipping online types")
                            pass
                        elif "pages" in entry:
                            # debug("  skipping url, paginated item")
                            continue
                    # debug(f"  writing url WITHOUT escape_yaml")
                    args.outfd.write(f'  URL: "{value}"\n')
                    continue
                if (
                    field == "eventtitle"
                    and "container-title" not in entry
                    and "booktitle" not in entry
                ):
                    args.outfd.write(
                        f'  container-title: "Proceedings of {value}"\n'
                    )
                    continue
                # 'Blog' is the null value I use in the mindmap
                if field == "c_blog" and entry[field] == "Blog":
                    # netloc = urllib.parse.urlparse(entry['url']).netloc
                    # args.outfd.write(
                    #     f'  container-title: "Personal"\n')
                    continue

                # debug(f"{field=}")
                if field in CONTAINERS:
                    # debug(f"in CONTAINERS")
                    field = "container-title"
                    value = yaml_protect_case(value)
                    # debug(f"{value=}")
                if field in BIBLATEX_CSL_FIELD_MAP:
                    # debug(f"bib2csl field FROM =  {field}")
                    field = BIBLATEX_CSL_FIELD_MAP[field]
                    # debug(f"bib2csl field TO   = {field}")
                args.outfd.write(f"  {field}: {escape_yaml(value)}\n")
    args.outfd.write("...\n")


def emit_json_csl(entries):
    """Emit citations in CSL/JSON for input to pandoc

    See: https://reagle.org/joseph/2013/08/bib-mapping.html
        https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html

    """

    def escape_csl(s):
        if s:  # faster to just quote than testing for tokens
            s = s.replace('"', r"'")
            # s = s.replace("#", r"\#") # this was introducing slashes in URLs
            s = s.replace("@", r"\\@")  # single slash caused bugs in past
            s = f'"{s}"'
        if s.isdigit():
            return int(s)
        else:
            return s

    def do_csl_person(person):
        """csl writer for authors and editors"""

        # biblatex ('First Middle', 'von', 'Last', 'Jr.')
        # CSL ('family', 'given', 'suffix' 'non-dropping-particle',
        #      'dropping-particle')
        # debug("person = '%s'" % (' '.join(person)))
        given, particle, family, suffix = person
        person_buffer = []
        person_buffer.append("        { ")
        person_buffer.append(f'"family": {escape_csl(family)}, ')
        if given:
            person_buffer.append(f'"given": {escape_csl(given)}, ')
            # person_buffer.append('    given:\n')
            # for given_part in given.split(' '):
            #     person_buffer.append('    - %s\n' % escape_csl(given_part))
        if suffix:
            person_buffer.append(f'"suffix": {escape_csl(suffix)}, ')
        if particle:
            person_buffer.append(
                f'"non-dropping-particle": {escape_csl(particle)}, '
            )
        person_buffer.append("},\n")
        return person_buffer

    def do_csl_date(date, season=None):
        """csl writer for dates"""

        date_buffer = []
        date_buffer.append("{")
        date_buffer.append('"date-parts": [ [ ')
        # int() removes leading 0 for json
        if date.year:
            date_buffer.append(f"{int(date.year)}, ")
        if date.month:
            date_buffer.append(f"{int(date.month)}, ")
        if date.day:
            date_buffer.append(f"{int(date.day)}, ")
        date_buffer.append("] ],\n")
        if date.circa:
            date_buffer.append(f'        "circa": true,\n')
        if season:
            date_buffer.append(f'        "season": "{season}",\n')
        date_buffer.append("    },\n")

        debug(f"{date_buffer=}")
        return date_buffer

    def csl_protect_case(title):
        """Preserve/bracket proper names/nouns
        https://github.com/jgm/pandoc-citeproc/blob/master/man/pandoc-citeproc.1.md
        >>> csl_protect_case("The iKettle – a world off its rocker")
        "The <span class='nocase'>iKettle</span> – a world off its rocker"
        """
        PROTECT_PAT = re.compile(
            r"""
            \b # empty string at beginning or end of word
            (
            [a-z]+ # one or more lower case
            [A-Z\./] # capital, period, or forward slash
            \S+ # one or more non-whitespace
            )
            \b # empty string at beginning or end of word
            """,
            re.VERBOSE,
        )
        return PROTECT_PAT.sub(r"<span class='nocase'>\1</span>", title)

    ## start of json buffer, to be written out after comma cleanup
    file_buffer = ["[\n"]
    for key, entry in sorted(entries.items()):
        # debug(f"{key=}")
        entry_type, genre, medium = guess_csl_type(entry)
        file_buffer.append(f'  {{ "id": "{entry["identifier"]}",\n')
        file_buffer.append(f'    "type": "{entry_type}",\n')
        if genre:
            file_buffer.append(f'    "genre": "{genre}",\n')
        if medium:
            file_buffer.append(f'    "medium": "{medium}",\n')

        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        if entry["ori_author"] in container_values:
            if not args.author_create:
                del entry["author"]
            else:
                entry["author"] = [["", "", "".join(entry["ori_author"]), ""]]

        for short, field in BIB_SHORTCUTS_ITEMS:
            if field in entry and entry[field] is not None:
                value = entry[field]
                # debug(f"short, field = '{short} , {field}'")
                # skipped fields
                if field in ("identifier", "entry_type", "issue"):
                    continue

                # special format fields
                if field == "title":
                    title = csl_protect_case(escape_csl((value)))
                    file_buffer.append(f'    "title": {title},\n')
                    continue
                if field in ("author", "editor", "translator"):
                    file_buffer.append(f'    "{field}": [\n')
                    for person in value:
                        # debug(f"{person=} in {value=}")
                        # debug(f"{file_buffer=}")
                        file_buffer.extend(do_csl_person(person))
                    file_buffer.append("      ],\n")
                    # debug(f"done people")
                    continue
                if field in ("date", "origdate", "urldate"):
                    # debug(f"field = {field}")
                    if value == "0000":
                        continue
                    if field == "date":
                        # debug(f"value = '{value}'")
                        season = entry["issue"] if "issue" in entry else None
                        file_buffer.append('    "issued": ')
                        file_buffer.extend(do_csl_date(value, season))
                    if field == "origdate":
                        # debug(f"value = '{value}'")
                        file_buffer.append('    "original-date": ')
                        file_buffer.extend(do_csl_date(value))
                    if field == "urldate":
                        file_buffer.append('    "accessed": ')
                        file_buffer.extend(do_csl_date(value))
                    continue

                if field == "urldate" and "url" not in entry:
                    continue  # no url, no 'read on'
                if field == "url":
                    # debug(f"url = {value}")
                    if any(ban for ban in EXCLUDE_URLS if ban in value):
                        # debug("banned")
                        continue
                    # skip articles+URL w/ no pagination & other offline types
                    if args.urls_online_only:
                        # debug("urls_online_only TRUE")
                        if entry_type in {"post", "post-weblog", "webpage"}:
                            # debug(f"  not skipping online types")
                            pass
                        elif "pages" in entry:
                            # debug("  skipping url, paginated item")
                            continue
                    # debug(f"  writing url WITHOUT escape_csl")
                    file_buffer.append(f'    "URL": "{value}",\n')
                    continue
                if (
                    field == "eventtitle"
                    and "container-title" not in entry
                    and "booktitle" not in entry
                ):
                    file_buffer.append(
                        f'    "container-title": "Proceedings of {value}",\n'
                    )
                    continue
                # 'Blog' is the null value I use in the mindmap
                if field == "c_blog" and entry[field] == "Blog":
                    # netloc = urllib.parse.urlparse(entry['url']).netloc
                    # file_buffer.append(
                    #     f'  container-title: "Personal"\n')
                    continue

                # debug(f"{field=}")
                if field in CONTAINERS:
                    # debug(f"in CONTAINERS")
                    field = "container-title"
                    value = csl_protect_case(value)
                    # debug(f"{value=}")
                if field in BIBLATEX_CSL_FIELD_MAP:
                    # debug(f"bib2csl field FROM =  {field}")
                    field = BIBLATEX_CSL_FIELD_MAP[field]
                    # debug(f"bib2csl field TO   = {field}")
                file_buffer.append(f'    "{field}": {escape_csl(value)},\n')
        file_buffer.append("  },\n")

    file_buffer = "".join(file_buffer) + "]\n"
    # remove trailing commas with a regex
    file_buffer = re.sub(r""",(?=\s*[}\]])""", "", file_buffer)
    args.outfd.write(file_buffer)


def emit_wp_citation(entries):
    """Emit citations in Wikipedia's {{citation}} template format for
    use in a List-defined references block.

    See: https://en.wikipedia.org/wiki/Help:List-defined_references
    See: https://en.wikipedia.org/wiki/Template:Cite

    """
    # TODO: Wikipedia dates may not be YYYY-MM, only YYYY or YYYY-MM-DD

    # debug(f"********************")
    # debug(f"{entries=}")

    def output_wp_names(field, names):
        """Rejigger names for odd WP author and editor conventions."""
        name_num = 0
        for name in names:
            name_num += 1
            if field == "author":
                prefix = ""
                suffix = name_num
            elif field == "editor":
                prefix = f"editor{str(name_num)}-"
                suffix = ""
            args.outfd.write(f"| {prefix}first{suffix} = {name[0]}\n")
            args.outfd.write(
                f'| {prefix}last{suffix} = {" ".join(name[1:])}\n'
            )

    for key, entry in sorted(entries.items()):
        wp_ident = key
        # debug(f"{wp_ident=}")
        args.outfd.write(f"<ref name={wp_ident}>\n")
        args.outfd.write(f"{{{{citation\n")

        for short, field in BIB_SHORTCUTS_ITEMS:
            if field in entry and entry[field] is not None:
                value = entry[field]
                if field in (
                    "annotation",
                    "chapter",
                    "custom1",
                    "custom2",
                    "entry_type",
                    "identifier",
                    "keyword",
                    "note",
                    "shorttitle",
                ):
                    continue
                elif field == "author":
                    output_wp_names(field, value)
                    continue
                elif field == "editor":
                    output_wp_names(field, value)
                    continue
                elif field in ("date", "origdate", "urldate"):
                    date = value.year
                    if value.month:
                        date = (
                            f"{calendar.month_name[int(value.month)]} {date}"
                        )
                    if value.day:
                        date = f"{value.day.lstrip('0')} {date}"
                    # date = "-".join(
                    #     filter(None, (value.year, value.month, value.day))
                    # )
                    if value.circa:
                        date = "{{circa|" + date + "}}"
                    value = date
                elif field == "title":  # TODO: convert value to title case?
                    if "booktitle" in entry:
                        field = "chapter"
                if field in BIBLATEX_WP_FIELD_MAP:
                    field = BIBLATEX_WP_FIELD_MAP[field]
                args.outfd.write(f"| {field} = {value}\n")
        args.outfd.write("}}\n</ref>\n")


def emit_results(entries, query, results_file):
    """Emit the results of the query"""

    def reverse_print(node, entry, spaces):
        """Move locator number to the end of the text with the biblatex key"""
        style_ref = node.get("STYLE_REF", "default")
        text = escape_XML(node.get("TEXT"))
        text = text.replace(  # restore my query_highlight strongs
            "&lt;strong&gt;", "<strong>"
        ).replace("&lt;/strong&gt;", "</strong>")
        prefix = "&gt; " if style_ref == "quote" else ""
        # don't reverse short texts and certain style refs
        if len(text) < 50 or style_ref in ["author", "title", "cite"]:
            cite = ""
            # prefix = ""  # this could remove ">" from short quotes
        else:
            locator = ""
            LOCATOR_PAT = re.compile(
                r"^(?:<strong>)?(\d+(?:-\d+)?)(?:</strong>)? (.*)"
            )
            matches = LOCATOR_PAT.match(text)
            if matches:
                text = matches.group(2)
                locator = matches.group(1)
                # http://mirrors.ibiblio.org/CTAN/macros/latex/exptl/biblatex/doc/biblatex.pdf
                # biblatex: page, column, line, verse, section, paragraph
                # kindle: location
                if "pagination" in entry:
                    if entry["pagination"] == "section":
                        locator = f", sec. {locator}"
                    elif entry["pagination"] == "paragraph":
                        locator = f", para. {locator}"
                    elif entry["pagination"] == "location":
                        locator = f", loc. {locator}"
                    elif entry["pagination"] == "chapter":
                        locator = f", ch. {locator}"
                    elif entry["pagination"] == "verse":
                        locator = f", vers. {locator}"
                    elif entry["pagination"] == "column":
                        locator = f", col. {locator}"
                    elif entry["pagination"] == "line":
                        locator = f", line {locator}"
                    else:
                        raise Exception(
                            f"unknown locator '{entry['pagination']}' "
                            f"for '{entry['title']}' in '{entry['custom2']}'"
                        )
                else:
                    if "-" in locator:
                        locator = f", pp. {locator}"
                    else:
                        locator = f", p. {locator}"
            cite = f" [@{entry['identifier'].replace(' ', '')}{locator}]"

        hypertext = text

        # if node has first child <font BOLD="true"/> then embolden
        style = ""
        if len(node) > 0:
            if node[0].tag == "font" and node[0].get("BOLD") == "true":
                style = "font-weight: bold"

        if "LINK" in node.attrib:
            link = escape(node.get("LINK"))
            hypertext = f'<a class="reverse_print" href="{link}">{text}</a>'

        results_file.write(
            f'{spaces}<li style="{style}" class="{style_ref}">'
            f"{prefix}{hypertext}{cite}</li>\n"
        )

    def pretty_print(node, entry, spaces):
        """Pretty print a node and descendants into indented HTML"""
        # bug: nested titles are printed twice. 101217
        if node.get("TEXT") is not None:
            reverse_print(node, entry, spaces)
        # I should clean all of this up to use simpleHTMLwriter,
        # markup.py, or yattag
        if len(node) > 0:
            results_file.write(f'{spaces}<li><ul class="pprint_recurse">\n')
            spaces = spaces + " "
            for child in node:
                if child.get("STYLE_REF") == "author":
                    break
                pretty_print(child, entry, spaces)
            spaces = spaces[0:-1]
            results_file.write(f"{spaces}</ul></li><!--pprint_recurse-->\n")

    def get_url_query(token):
        """Return the URL for an HTML link to the actual title"""
        token = token.replace("<strong>", "").replace("</strong>", "")
        # urllib won't accept unicode
        token = urllib.parse.quote(token.encode("utf-8"))
        # dbg(f"token = '{token}' type = '{type(token)}'")
        url_query = escape("search.cgi?query=%s") % token
        # dbg(f"url_query = '{url_query}' type = '{type(url_query)}'")
        return url_query

    def get_url_MM(file_name):
        """Return URL for the source MindMap based on whether CGI or cmdline"""
        if __name__ == "__main__":
            return file_name
        else:  # CGI
            client_path = file_name.replace(f"{HOME}", f"{CLIENT_HOME}")
            return f"file://{client_path}"

    def print_entry(
        identifier, author, date, title, url, MM_mm_file, base_mm_file, spaces
    ):
        identifier_html = (
            f'<li class="identifier_html">'
            f'<a href="{get_url_query(identifier)}">{identifier}</a>'
        )
        title_html = (
            f'<a class="title_html"'
            f' href="{get_url_query(title)}">{title}</a>'
        )
        if url:
            link_html = f'[<a class="link_html" href="{url}">url</a>]'
        else:
            link_html = ""
        from_html = (
            f'from <a class="from_html" '
            f'href="{MM_mm_file}">{base_mm_file}</a>'
        )
        results_file.write(
            f"{spaces}{identifier_html}, "
            f"<em>{title_html}</em> {link_html} [{from_html}]"
        )
        results_file.write(f"{spaces}</li><!--identifier_html-->\n")

    spaces = " "
    for key, entry in sorted(entries.items()):
        identifier = entry["identifier"]
        author = create_biblatex_author(entry["author"])
        title = entry["title"]
        date = entry["date"]
        url = entry.get("url", "")
        base_mm_file = os.path.basename(entry["_mm_file"])
        MM_mm_file = get_url_MM(entry["_mm_file"])

        # if I am what was queried, print all of me
        if entry["identifier"] == args.query:
            results_file.write(
                '%s<li class="li_entry_identifier">\n' % (spaces)
            )
            spaces = spaces + " "
            results_file.write('%s<ul class="tit_tree">\n' % (spaces))
            spaces = spaces + " "
            results_file.write(
                '%s<li style="text-align: right">[<a href="%s">%s</a>]</li>\n'
                % (spaces, MM_mm_file, base_mm_file),
            )
            fl_names = ", ".join(
                name[0] + " " + name[2] for name in entry["author"]
            )
            title_mdn = f"{title}"
            if url:
                title_mdn = f"[{title}]({url})"
            results_file.write(
                '%s<li class="mdn">[%s]: %s, %s, "%s".</li>\n'
                % (spaces, identifier, fl_names, date[0], title_mdn)
            )
            results_file.write(f'{spaces}<li class="author">{fl_names}</li>\n')
            # results_file.write(f'{spaces}<li class="pretty_print">\n')
            pretty_print(entry["_title_node"], entry, spaces)
            # results_file.write(f'{spaces}</li><!--pretty_print-->')
            results_file.write(f"{spaces}</ul><!--tit_tree-->\n"),
            results_file.write(f"{spaces}</li>\n"),

        # if some nodes were matched, PP with citation info reversed
        if "_node_results" in entry:
            print_entry(
                identifier,
                author,
                date,
                title,
                url,
                MM_mm_file,
                base_mm_file,
                spaces,
            )
            if len(entry["_node_results"]) > 0:
                results_file.write(f"{spaces}<li>\n")
                spaces = spaces + " "
                results_file.write(f'{spaces}<ul class="li_node_results">\n')
                spaces = spaces + " "
                for node in entry["_node_results"]:
                    reverse_print(node, entry, spaces)
                spaces = spaces[0:-1]
            results_file.write(f"{spaces}</ul><!--li_node_results-->\n")
            spaces = spaces[0:-1]
            results_file.write(f"{spaces}</li>\n")
        # if my author or title matched, print biblio w/ link to complete entry
        elif "_author_result" in entry:
            author = (
                f"{entry['_author_result'].get('TEXT')}"
                f"{entry['date'].year}"
            )
            print_entry(
                identifier,
                author,
                date,
                title,
                url,
                MM_mm_file,
                base_mm_file,
                spaces,
            )
        elif "_title_result" in entry:
            title = entry["_title_result"].get("TEXT")
            print_entry(
                identifier,
                author,
                date,
                title,
                url,
                MM_mm_file,
                base_mm_file,
                spaces,
            )


#################################################################
# Mindmap parsing and bib building
#################################################################


def parse_names(names):
    """Do author parsing magic to figure out name components.

    http://artis.imag.fr/~Xavier.Decoret/resources/xdkbibtex/bibtex_summary.html
    http://code.google.com/p/bibstuff/source/browse/trunk/bibname.py?r=6
        parse_raw_names_parts()

    >>> parse_names('First Middle von Last Jr.')
    [('First Middle', 'von', 'Last', 'Jr.')]

    >>> parse_names('First Last, Last')
    [('First', '', 'Last', ''), ('', '', 'Last', '')]

    >>> parse_names('First van der Last, First van der Last II, van Last')
    [('First', 'van der', 'Last', ''), ('First', 'van der', 'Last', 'II'), ('', 'van', 'Last', '')]

    """  # noqa: E501

    names_p = []
    # debug(f"names = '{names}'")
    names_split = names.split(",")
    for name in names_split:
        name = name.strip()
        # debug(f"name = '{name}'")
        first = last = von = jr = ""
        chunks = name.strip().split()

        if "van" in chunks and chunks[chunks.index("van") + 1] in (
            "den",
            "der",
        ):
            chunks[chunks.index("van") : chunks.index("van") + 2] = [
                "van " + chunks[chunks.index("van") + 1]
            ]

        if len(chunks) > 1:
            if chunks[-1] in SUFFIXES:
                jr = chunks.pop(-1)
            last = chunks.pop(-1)
            if len(chunks) > 0:
                if chunks[-1] in PARTICLES:
                    von = chunks.pop(-1)
            first = " ".join(chunks)
        else:
            last = name

        names_p.append((first, von, last, jr))
    return names_p


def commit_entry(entry, entries):
    """Place an entry in the entries dictionary
    with default values if need be"""
    if entry != {}:
        entry.setdefault("author", [("", "John", "Doe", "")])
        entry.setdefault("title", "Unknown")
        entry.setdefault("0000")
        entry.setdefault("_mm_file", "")

        # pull the citation, create an identifier, and enter in entries
        try:
            pull_citation(entry)  # break the citation up
        except:
            print(
                f"pull_citation error on {entry['author']}: "
                f"{entry['_mm_file']}"
            )
            raise
        entry["identifier"] = get_ident(entry, entries)
        entries[entry["identifier"]] = entry
    return entries


def walk_freeplane(node, mm_file, entries, links):
    """Walk the freeplane XML tree and build:
    1. a dictionary of bibliographic entries.
    2. (optionally) for any given entry, lists of author, title, or
        other nodes that match a query.

    This function had originally been implemented recursively, but now
    iterates over a depth-first order list of tree nodes in order to
    satisfy the two requirements:
    1. a single author may have more than one title, and
    2. references without a year should end up in entries with year='0000'.
    Consequently, an entry is only committed when a new title
    is encountered or it is the last entry.

    """
    author_node = None
    entry = {}

    if useLXML is False:
        parent_map = {c: p for p in node.iter() for c in p}

        def get_parent(node):
            return parent_map[node]

    elif useLXML is True:

        def get_parent(node):
            return node.getparent()

    def query_highlight(node, query):
        """Return a modified node with matches highlighted"""
        query_lower = query.lower()
        text = node.get("TEXT")
        text_lower = text.lower()
        if query_lower in text_lower:
            start_index = text_lower.find(query_lower)
            end_index = start_index + len(query_lower)
            result = (
                f"{text[0:start_index]}"
                f"<strong>{text[start_index: end_index]}</strong>"
                f"{text[end_index:]}"
            )
            node.set("TEXT", result)
            return node
        return None

    def get_author_node(node):
        """Return the nearest author node ancestor"""
        ancestor = get_parent(node)
        while ancestor.get("STYLE_REF") != "author":
            ancestor = get_parent(ancestor)
        return ancestor

    for d in node.iter():
        if "LINK" in d.attrib:  # found a local reference link
            if not d.get("LINK").startswith("http:") and d.get(
                "LINK"
            ).endswith(".mm"):
                links.append(unescape_XML(d.get("LINK")))
        # skip nodes that are structure, comment, and empty of text
        if "STYLE_REF" in d.attrib and d.get("TEXT"):
            if d.get("STYLE_REF") == "author":
                # pass author as it will be fetched upon new title
                pass
            elif d.get("STYLE_REF") == "title":
                commit_entry(entry, entries)  # new entry, so store previous
                entry = {}  # and create new one
                # because entries are based on unique titles, author processing
                # is deferred until now when a new title is found
                author_node = get_author_node(d)
                entry["ori_author"] = unescape_XML(author_node.get("TEXT"))
                entry["author"] = parse_names(entry["ori_author"])
                entry["title"] = unescape_XML(d.get("TEXT"))
                entry["_mm_file"] = mm_file
                entry["_title_node"] = d
                if "LINK" in d.attrib:
                    entry["url"] = d.get("LINK")
                if args.query:
                    author_highlighted = query_highlight(
                        author_node, args.query
                    )
                    if author_highlighted is not None:
                        entry["_author_result"] = author_highlighted
                    title_highlighted = query_highlight(d, args.query)
                    if title_highlighted is not None:
                        entry["_title_result"] = title_highlighted
            else:
                if d.get("STYLE_REF") == "cite":
                    entry["cite"] = unescape_XML(d.get("TEXT"))
                elif d.get("STYLE_REF") == "annotation":
                    entry["annotation"] = unescape_XML(d.get("TEXT").strip())
                if args.query:
                    node_highlighted = query_highlight(d, args.query)
                    if node_highlighted is not None:
                        entry.setdefault("_node_results", []).append(
                            node_highlighted
                        )

    # commit the last entry as no new titles left
    entries = commit_entry(entry, entries)
    return entries, links


RESULT_FILE_HEADER = """<!DOCTYPE html>
<html>
<head>
<meta http-equiv="Content-Type"
content="text/html; charset=UTF-8" />
<link href="https://reagle.org/joseph/2005/01/mm-print.css"
rel="stylesheet" type="text/css" />
"""

RESULT_FILE_QUERY_BOX = """    <title>Results for '%s'</title>
</head>
<body>
<div>
    <form method="get" action="search.cgi">
    <input type="submit" value="Go" name="Go" /> <input type="text" size="25"
    name="query" maxlength="80" /> <input type="radio" name="sitesearch"
    value="BusySponge" /> BS <input type="radio" name="sitesearch"
    checked="checked" value="MindMap" /> MM</form>
</div>
<h2>Results for '%s'</h2>
<ul class="RESULT_FILE_QUERY_BOX">
"""


def build_bib(file_name, output):
    """Parse and process files, including new ones encountered if chasing"""

    links = []  # list of other files encountered in the mind map
    done = []  # list of files processed, kept to prevent loops
    entries = dict()  # dict of {id : {entry}}, by insertion order
    mm_files = [
        file_name,
    ]  # list of file encountered (e.g., chase option)
    # dbg(f"   mm_files = {mm_files}")
    while mm_files:
        mm_file = os.path.abspath(mm_files.pop())
        # dbg(f"   parsing {mm_file}")
        try:
            doc = parse(mm_file).getroot()
        except IOError as err:
            # dbg(f"    failed to parse {mm_file} because of {err}")
            continue
        # dbg(f"    successfully parsed {mm_file}")
        entries, links = walk_freeplane(doc, mm_file, entries, links=[])
        # dbg("    done.appending %s" % os.path.abspath(mm_file))
        done.append(mm_file)
        if args.chase:
            for link in links:
                link = os.path.abspath(os.path.dirname(mm_file) + "/" + link)
                if link not in done and link not in mm_files:
                    if not any(
                        [word in link for word in ("syllabus", "readings")]
                    ):  # 'old'
                        # dbg(f"    mm_files.appending {link}")
                        mm_files.append(link)

    if args.query:
        results_file_name = f"{TMP_DIR}query-thunderdell.html"
        if os.path.exists(results_file_name):
            os.remove(results_file_name)
        try:
            results_file = open(results_file_name, "w", encoding="utf-8")
        except IOError:
            print(("There was an error writing to", results_file_name))
            sys.exit()
        results_file.write(RESULT_FILE_HEADER)
        results_file.write(RESULT_FILE_QUERY_BOX % (args.query, args.query))
        emit_results(entries, args.query, results_file)
        results_file.write("</ul></body></html>\n")
        results_file.close()
        if args.in_main:
            ADDRESS_IN_USE = False
            os.chdir(CGI_DIR + "/..")
            handler = http.server.CGIHTTPRequestHandler
            handler.cgi_directories = ["/cgi-bin"]
            try:
                server = http.server.HTTPServer(("localhost", 8000), handler)
            except OSError as error:
                if error.errno == errno.EADDRINUSE:
                    ADDRESS_IN_USE = True
                    print(f"address in use")
                else:
                    raise
            # below runs the query twice I think, but still fast
            webbrowser.open(
                f"http://localhost:8000/cgi-bin/search.cgi?query={args.query}"
            )
            if not ADDRESS_IN_USE:
                server.serve_forever()
    elif args.pretty:
        results_file_name = f"{TMP_DIR}pretty-print.html"
        try:
            results_file = open(results_file_name, "w", encoding="utf-8")
        except IOError:
            print(("There was an error writing to", results_file_name))
            sys.exit()
        results_file.write(RESULT_FILE_HEADER)
        results_file.write(
            "    <title>Pretty Mind Map</title></head>"
            '<body>\n<ul class="top">\n'
        )
        for entry in list(entries.values()):
            args.query = entry["identifier"]
            emit_results(entries, args.query, results_file)
        results_file.write("</ul></body></html>\n")
        results_file.close()
        if args.in_main:
            webbrowser.open(f"file://{results_file_name}")

    else:
        output(entries)
    return


def _test_results():
    """
    Tests the overall parsing of Mindmap XML and the relationships between
    authors with multiple titles and nested authors.

    >>> call('thunderdell.py -i ~/bin/td/tests/author-child.mm > \
    /tmp/author-child.yaml; \
    diff ~/bin/td/tests/author-child.yaml /tmp/author-child.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/author-descendent.mm > \
    /tmp/author-descendent.yaml; \
    diff ~/bin/td/tests/author-descendent.yaml /tmp/author-descendent.yaml', \
    shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/authorless.mm > \
    /tmp/authorless.yaml; \
    diff ~/bin/td/tests/authorless.yaml /tmp/authorless.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/authors.mm > \
    /tmp/authors.yaml; \
    diff ~/bin/td/tests/authors.yaml /tmp/authors.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/case.mm > \
    /tmp/case.yaml; \
    diff ~/bin/td/tests/case.yaml /tmp/case.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/csl.mm > \
    /tmp/csl.yaml; \
    diff ~/bin/td/tests/csl.yaml /tmp/csl.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/date.mm > /tmp/date.yaml; \
    diff ~/bin/td/tests/date.yaml /tmp/date.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/editors.mm > \
    /tmp/editors.yaml; \
    diff ~/bin/td/tests/editors.yaml /tmp/editors.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/online.mm > /tmp/online.yaml; \
    diff ~/bin/td/tests/online.yaml /tmp/online.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/title-escapes.mm > \
    /tmp/title-escapes.yaml; \
    diff ~/bin/td/tests/title-escapes.yaml /tmp/title-escapes.yaml', \
    shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/title-title.mm > \
    /tmp/title-title.yaml; \
    diff ~/bin/td/tests/title-title.yaml /tmp/title-title.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/von.mm > /tmp/von.yaml; \
    diff ~/bin/td/tests/von.yaml /tmp/von.yaml', shell=True)
    0
    >>> call('thunderdell.py -i ~/bin/td/tests/title-quotes.mm > /tmp/title-quotes.yaml; \
    diff ~/bin/td/tests/title-quotes.yaml /tmp/title-quotes.yaml', shell=True)
    0

    """  # noqa: E501


if __name__ == "__main__":
    import argparse  # http://docs.python.org/dev/library/argparse.html

    arg_parser = argparse.ArgumentParser(
        description="""Outputs YAML/CSL bibliography.\n
    Note: Keys are created by appending the first letter of first
    3 significant words (i.e., no WP:namespace, articles, conjunctions
    or short prepositions). If only one word, use first, penultimate,
    and last character."""
    )
    arg_parser.add_argument(
        "-a",
        "--author-create",
        default=False,
        action="store_true",
        help="create author for anon entries using container",
    )
    arg_parser.add_argument(
        "-b",
        "--biblatex",
        default=False,
        action="store_true",
        help="emit biblatex fields",
    )
    arg_parser.add_argument(
        "-c",
        "--chase",
        action="store_true",
        default=False,
        help="chase links between MMs",
    )
    arg_parser.add_argument(
        "-D",
        "--defaults",
        action="store_true",
        default=False,
        help="chase, output YAML/CSL, use default map and output file",
    )
    arg_parser.add_argument(
        "-i",
        "--input-file",
        default=DEFAULT_MAP,
        metavar="FILENAME",
        help="mindmap to process",
    )
    arg_parser.add_argument(
        "-k",
        "--keys",
        default="-no-keys",
        action="store_const",
        const="-use-keys",
        help="show biblatex keys in displayed HTML",
    )
    arg_parser.add_argument(
        "-F",
        "--fields",
        action="store_true",
        default=False,
        help="show biblatex shortcuts, fields, and types used by fe",
    )
    arg_parser.add_argument(
        "-j",
        "--JSON-CSL",
        default=False,
        action="store_true",
        help="emit JSON/CSL for use with pandoc",
    )
    arg_parser.add_argument(
        "-l",
        "--long-url",
        action="store_true",
        default=False,
        help="use long URLs",
    )
    arg_parser.add_argument(
        "-o",
        "--output-to-file",
        default=False,
        action="store_true",
        help="output goes to FILENAME.yaml (BOOLEAN)",
    )
    arg_parser.add_argument(
        "-p",
        "--pretty",
        action="store_true",
        default=False,
        help="pretty print",
    )
    arg_parser.add_argument(
        "-q", "--query", nargs="+", help="query the mindmaps", metavar="QUERY"
    )
    arg_parser.add_argument(
        "-s",
        "--style",
        default="apalike",
        help="use biblatex stylesheet (default: apalike)",
        metavar="BST",
    )
    arg_parser.add_argument(
        "-T", "--tests", action="store_true", default=False, help="run tests"
    )
    arg_parser.add_argument(
        "-u",
        "--urls_online_only",
        action="store_true",
        default=False,
        help="emit URLs for online resources only",
    )
    arg_parser.add_argument(
        "-V",
        "--verbose",
        dest="verbose",
        action="count",
        default=0,
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"1.0 using Python {sys.version}",
    )
    arg_parser.add_argument(
        "-L",
        "--log-to-file",
        action="store_true",
        default=False,
        help="log to file %(prog)s.log",
    )
    arg_parser.add_argument(
        "-w",
        "--WP-citation",
        default=False,
        action="store_true",
        help="emit Wikipedia {{citation}} format which can be "
        "cited via {{sfn|Author2004|loc=p. 45}}. "
        "See: http://en.wikipedia.org/wiki/Template:Cite",
    )
    arg_parser.add_argument(
        "-y",
        "--YAML-CSL",
        default=False,
        action="store_true",
        help="emit YAML/CSL for use with pandoc [default]",
    )

    args = arg_parser.parse_args()
    # print(args)
    file_name = os.path.abspath(args.input_file)

    log_level = logging.ERROR  # 40
    if args.verbose == 1:
        log_level = logging.WARNING  # 30
    elif args.verbose == 2:
        log_level = logging.INFO  # 20
    elif args.verbose >= 3:
        log_level = logging.DEBUG  # 10
    LOG_FORMAT = "%(levelname).3s %(funcName).5s: %(message)s"
    if args.log_to_file:
        print("logging to file")
        logging.basicConfig(
            filename="fe.log", filemode="w", level=log_level, format=LOG_FORMAT
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    args.in_main = True
    args.outfd = sys.stdout

    if args.pretty and file_name == DEFAULT_MAP:
        file_name = DEFAULT_PRETTY_MAP
    if args.WP_citation:
        output = emit_wp_citation
    elif args.biblatex:
        output = emit_biblatex
    elif args.JSON_CSL:
        output = emit_json_csl
    else:
        args.YAML_CSL = True
        output = emit_yaml_csl
    if args.defaults:
        args.chase = True
        args.output_to_file = True
    if args.output_to_file:
        if args.YAML_CSL:
            extension = ".yaml"
        elif args.JSON_CSL:
            extension = ".json"
        elif args.biblatex:
            extension = ".bib"
        elif args.WP_citation:
            extension = ".wiki"
        output_fn = f"{os.path.splitext(file_name)[0]}{extension}"
        args.outfd = open(output_fn, "w", encoding="utf-8")
    if args.tests:
        print("Running doctests")
        import doctest

        doctest.testmod()
    if args.fields:
        print("\n                         _BIBLATEX_TYPES_ (deprecated)")
        print("               http://intelligent.pe.kr/LaTex/bibtex2.htm\n")
        pretty_tabulate_list(list(BIBLATEX_TYPES))
        print("                          _EXAMPLES_\n")
        print("      d=2013 in=MIT t=mastersthesis")
        print("      d=2013 in=MIT t=phdthesis")

        print("\n                          _CSL_TYPES_ (preferred)")
        print("              http://aurimasv.github.io/z2csl/typeMap.xml\n")
        pretty_tabulate_list(list(BIB_TYPES))
        print("                          _EXAMPLES_\n")
        print("      d=2014 p=ACM et=Conference on FOO ve=Boston")
        print("      d=2013 in=MIT t=thesis g=Undergraduate thesis")
        print("      d=2013 in=MIT t=thesis g=Masters thesis")
        print("      d=2013 in=MIT t=thesis g=PhD dissertation")
        print("\n\n")
        print("\n                             _FIELD_SHORTCUTS_")
        pretty_tabulate_dict(BIB_SHORTCUTS)
        print("      t=biblatex/CSL type (e.g., t=thesis)")
        print("      ot=organization's subtype (e.g., W3C REC)")
        print(
            "      pa=section|paragraph|location|chapter|verse|column|line\n\n"
        )
        sys.exit()
    if args.query:
        args.query = " ".join(args.query)
        args.query = urllib.parse.unquote(args.query)
        output = emit_results
    build_bib(file_name, output)
    args.outfd.close()
else:

    class args:
        in_main = False  # imported or called from cgi
        chase = True  # Follow freeplane links to other local maps
        long_url = False  # Use short 'oldid' URLs for mediawikis
        urls_online_only = False  # Emit urls for @online only
        pretty = False  # Print as HTML with citation at end
        query = None  # Query the bibliographies
