#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Thunderdell, by Joseph Reagle http://reagle.org/joseph/

Extract a bibliography from a Freeplane mindmap"""

import argparse  # http://docs.python.org/dev/library/argparse.html
import errno
import http.server
import logging
import os
import re
import sys
import textwrap
import urllib.parse
import webbrowser
import xml.etree.ElementTree as et
from collections import namedtuple
from collections.abc import Callable
from typing import NamedTuple
from urllib.parse import parse_qs
from xml.etree.ElementTree import parse

import config
from biblio.fields import (
    BIB_SHORTCUTS,
    BIB_TYPES,
    BIBLATEX_TYPES,
    BORING_WORDS,
    PARTICLES,
    SUFFIXES,
)
from formats import emit_biblatex, emit_json_csl, emit_results, emit_wp, emit_yaml_csl
from utils.text import pretty_tabulate_dict, pretty_tabulate_list, strip_accents
from utils.web import unescape_XML

log_level = logging.ERROR  # 40 # declared here for when imported

# logger function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

#################################################################
# Mindmap parsing, bib building, and query emitting
#################################################################

RESULT_FILE_HEADER = """<!DOCTYPE html>
<html lang="en">
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


def build_bib(
    args: argparse.Namespace,
    file_name: str,
    emitter_func: Callable[[argparse.Namespace, dict], None],
) -> None:
    """Parse and process files, including new ones encountered if chasing"""

    links = []  # list of other files encountered in the mind map
    done = []  # list of files processed, kept to prevent loops
    entries: dict[str, dict] = {}  # dict of {id : {entry}}, by insertion order
    mm_files = [
        file_name,
    ]  # list of file encountered (e.g. chase option)

    # debug(f"   mm_files = {mm_files}")
    while mm_files:
        mm_file = os.path.abspath(mm_files.pop())
        # debug(f"   parsing {mm_file}")
        try:
            doc = parse(mm_file).getroot()
        except (OSError, et.ParseError) as err:
            debug(f"    failed to parse {mm_file} because of {err}")
            continue
        # debug(f"    successfully parsed {mm_file}")
        entries, links = walk_freeplane(args, doc, mm_file, entries, links=[])
        # debug("    done.appending %s" % os.path.abspath(mm_file))
        done.append(mm_file)
        if args.chase:
            # debug("chasing")
            for link in links:
                link = os.path.abspath(os.path.dirname(mm_file) + "/" + link)
                if link not in done and link not in mm_files:
                    if not any(
                        word in link for word in ("syllabus", "readings")
                    ):  # 'old'
                        # debug(f"    mm_files.appending {link}")
                        mm_files.append(link)

    if args.query:
        serve_query(args, entries)
    elif args.pretty:
        show_pretty(args, entries)
    else:
        emitter_func(args, entries)


def walk_freeplane(args, node, mm_file, entries, links):  # noqa: C901
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

    parent_map = {c: p for p in node.iter() for c in p}

    def _query_highlight(node, query):
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

    def _get_author_node(node):
        """Return the nearest author node ancestor"""
        ancestor = _get_parent(node)
        while ancestor.get("STYLE_REF") != "author":
            ancestor = _get_parent(ancestor)
        return ancestor

    def _get_parent(node):
        return parent_map[node]

    for d in node.iter():
        if "LINK" in d.attrib:  # found a local reference link
            if not d.get("LINK").startswith("http:") and d.get("LINK").endswith(".mm"):
                links.append(unescape_XML(d.get("LINK")))
        # skip nodes that are structure, comment, and empty of text
        if "STYLE_REF" in d.attrib and d.get("TEXT"):
            if d.get("STYLE_REF") == "author":
                # pass author as it will be fetched upon new title
                pass
            elif d.get("STYLE_REF") == "title":
                commit_entry(args, entry, entries)  # new entry, so store previous
                entry = {}  # and create new one
                # because entries are based on unique titles, author processing
                # is deferred until now when a new title is found
                author_node = _get_author_node(d)
                entry["ori_author"] = unescape_XML(author_node.get("TEXT"))
                entry["author"] = parse_names(entry["ori_author"])
                entry["title"] = unescape_XML(d.get("TEXT"))
                entry["_mm_file"] = mm_file
                entry["_title_node"] = d
                if "LINK" in d.attrib:
                    entry["url"] = d.get("LINK")
                if args.query:
                    author_highlighted = _query_highlight(author_node, args.query)
                    if author_highlighted is not None:
                        entry["_author_result"] = author_highlighted
                    title_highlighted = _query_highlight(d, args.query)
                    if title_highlighted is not None:
                        entry["_title_result"] = title_highlighted
            else:
                if d.get("STYLE_REF") == "cite":
                    entry["cite"] = unescape_XML(d.get("TEXT"))
                elif d.get("STYLE_REF") == "annotation":
                    entry["annotation"] = unescape_XML(d.get("TEXT").strip())
                if args.query:
                    node_highlighted = _query_highlight(d, args.query)
                    if node_highlighted is not None:
                        entry.setdefault("_node_results", []).append(node_highlighted)

    # commit the last entry as no new titles left
    entries = commit_entry(args, entry, entries)
    return entries, links


def serve_query(args: argparse.Namespace, entries: dict) -> None:
    """
    Given the entries resulting from a query and crawl of the mindmaps,
    create a web server and open browser.
    """

    # debug("querying")
    results_file_name = f"{config.TMP_DIR}query-thunderdell.html"
    if os.path.exists(results_file_name):
        os.remove(results_file_name)
    try:
        args.results_file = open(results_file_name, "w", encoding="utf-8")
    except OSError as err:
        print(f"{err}")
        print(f"There was an error writing to {results_file_name}")
        raise
    args.results_file.write(RESULT_FILE_HEADER)
    args.results_file.write(RESULT_FILE_QUERY_BOX % (args.query, args.query))
    emit_results(args, entries)
    args.results_file.write("</ul></body></html>\n")
    args.results_file.close()
    # debug(f"{results_file=}")
    if args.in_main:
        ADDRESS_IN_USE = False
        os.chdir(config.CGI_DIR + "/..")
        handler = http.server.CGIHTTPRequestHandler
        handler.cgi_directories = ["/cgi-bin"]
        try:
            server = http.server.HTTPServer(("localhost", 8000), handler)
        except OSError as error:
            if error.errno == errno.EADDRINUSE:
                ADDRESS_IN_USE = True
                print("address in use")
            else:
                raise
        webbrowser.open(f"http://localhost:8000/cgi-bin/search.cgi?query={args.query}")
        if not ADDRESS_IN_USE:
            server.serve_forever()  # type: ignore[unbound]


def show_pretty(args: argparse.Namespace, entries: dict) -> None:
    """
    Given the entries resulting from a crawl of the mindmaps,
    create a local web page and open browser.
    """
    results_file_name = f"{config.TMP_DIR}pretty-print.html"
    try:
        args.results_file = open(results_file_name, "w", encoding="utf-8")
    except OSError as err:
        print(f"{err}")
        print(f"There was an error writing to {results_file_name}")
        raise
    args.results_file.write(RESULT_FILE_HEADER)
    args.results_file.write(
        '    <title>Pretty Mind Map</title></head><body>\n<ul class="top">\n'
    )
    for entry in list(entries.values()):
        args.query = entry["identifier"]
        emit_results(args, entries)
    args.results_file.write("</ul></body></html>\n")
    args.results_file.close()
    if args.in_main:
        webbrowser.open(f"file://{results_file_name}")


def commit_entry(args, entry, entries):
    """Place an entry in the entries dictionary
    with default values if need be"""
    if entry != {}:
        entry.setdefault("author", [("", "John", "Doe", "")])
        entry.setdefault("ori_author", [("", "John", "Doe", "")])
        entry.setdefault("title", "Unknown")
        entry.setdefault("0000")
        entry.setdefault("_mm_file", "")

        # pull the citation, create an identifier, and enter in entries
        try:
            entry = pull_citation(args, entry)  # parse a=b c=d syntax
        except Exception:
            print(f"pull_citation error on {entry['author']}: {entry['_mm_file']}")
            raise
        entry["identifier"] = get_ident(entry, entries)
        entries[entry["identifier"]] = entry
    return entries


#################################################################
# Entry construction
#################################################################

Date = namedtuple("Date", ["year", "month", "day", "circa", "time"])


def pull_citation(args, entry: dict) -> dict:
    """Modifies entry with parsed citation and field-specific heuristics

    Uses this convention: "d=20030723 j=Research Policy v=32 n=7 pp=1217-1241"

    """

    # TODO: for Wayback Machine, make dates circa and prefix container 2022-09-26

    entry = parse_pairs(entry)

    # Reformat date fields
    for date_field in ["date", "custom1", "origdate"]:
        if date_field in entry:
            entry[date_field] = parse_date(entry[date_field])
    entry["urldate"] = entry.pop("custom1", None)

    # Reformat other names
    for name_field in ["editor", "translator"]:
        if name_field in entry:
            entry[name_field] = parse_names(entry[name_field])

    # Detach subtitle from shorttitle
    if ": " in entry["title"] and not entry["title"].startswith("Re:"):
        entry["shorttitle"] = entry["title"].split(":")[0].strip()

    # Include full path to MM file
    entry["custom2"] = entry["_mm_file"]  # .split("/")[-1]

    # Remove private Reddit message URLs
    if "url" in entry and entry["url"].startswith("https://www.reddit.com/message"):
        entry.pop("url")
        entry.pop("urldate", None)

    # Process Wikipedia perma/oldid
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

    return entry


def parse_pairs(entry: dict) -> dict:
    """Parse pairs of the form: "d=20030723 j=Research Policy v=32 n=7 pp=1217-1241"""

    if "cite" in entry:
        citation = entry["cite"]
        # split around tokens of length 1-3 and
        EQUAL_PAT = re.compile(r"(\w{1,3})=")
        # get rid of first empty string of results
        cites = EQUAL_PAT.split(citation)[1:]
        # 2 refs to an iterable are '*' unpacked and rezipped
        cite_pairs = zip(*[iter(cites)] * 2, strict=True)  # pyright: ignore
        for short, value in cite_pairs:  # pyright: ignore
            try:
                entry[BIB_SHORTCUTS[short]] = value.strip()
            except KeyError as error:
                print(("Key error on ", error, entry["title"], entry["_mm_file"]))
    return entry


def identity_add_title(ident, title):
    """Return a non-colliding identity.

    Disambiguate keys by appending the first letter of first
    3 significant words (i.e., no WP:namespace, articles, conjunctions
    or short prepositions). If only one word, use first, penultimate,
    and last character.

    >>> identity_add_title('Wikipedia 2008', 'Wikipedia:Neutral Point of View')
    'Wikipedia 2008npv'

    """
    # debug(f"title = '{title}'")
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
        suffix = "".join([word[0] for word in title_words if word not in BORING_WORDS])
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
        # debug(f"\t trying     {ident} crash w/ {entries[ident]['title']}")
        if ident[-1].isdigit():
            suffix = int(ident[-1])
            suffix += 1
            ident = f"{ident[0:-1]}{suffix}"
        else:
            ident += "1"
        # debug(f"\t yielded    {ident}")
    return ident


def get_ident(entry, entries, delim: str = ""):
    """
    Create an identifier (key) for the entry based on last names, year, and title"""

    # debug(f"1 {entry=}")
    last_names = []
    name_part = ""

    # Unpack first, von, late, and jr
    for _, von, last, _ in entry["author"]:
        last_names.append(f"{von}{last}".replace(" ", ""))

    # Join the last names depending on how many there are: > 3 is "et al."
    if len(last_names) == 1:
        name_part = last_names[0]
    elif len(last_names) == 2:
        name_part = delim.join(last_names[0:2])
    elif len(last_names) == 3:
        name_part = delim.join(last_names[0:3])
    elif len(last_names) > 3:
        name_part = f"{last_names[0]}Etal"

    if "date" not in entry:
        entry["date"] = Date(year="0000", month=None, day=None, circa=None, time=None)
    year_delim = delim if delim else ""
    # debug(f"2 entry['date'] = {entry['date']}")
    ident = year_delim.join((name_part, entry["date"].year))
    # debug(f"3 ident = {type(ident)} '{ident}'")
    ident = (
        ident.replace(":", "")
        .replace("'", "")  # not permitted in xml name/id attributes
        .replace("’", "")
        .replace(".", "")  # punctuation
        .replace("@", "")
        .replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
        .replace("<strong>", "")  # '@' citation designator
        .replace("</strong>", "")  # added by walk_freeplane.query_highlight
    )
    # debug(f"4 ident = {type(ident)} '{ident}'")
    ident = strip_accents(ident)  # unicode buggy in bibtex keys
    if ident[0].isdigit():  # pandoc forbids keys starting with digits
        ident = f"a{ident}"

    ident = identity_add_title(ident, entry["title"])  # get title suffix
    if ident in entries:  # there is a collision
        warning(f"collision on {ident}: {entry['title']} & {entries[ident]['title']}")
        ident = identity_increment(ident, entries)
    # debug(f"5 ident = {type(ident)} '{ident}' in {entry['_mm_file']}")
    return ident


def parse_date(when: str) -> NamedTuple:
    """Parse dates that starts with 'YYYY' and returns named tuple.
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


if __name__ == "__main__":
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
        "--bibtex",
        default=False,
        action="store_true",
        help="modify biblatex to use bibtex's year/month fields",
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
        default=config.DEFAULT_MAP,
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
        help="show biblatex shortcuts, fields, and types used by td",
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
        help="output goes to FILENAME.ext (BOOLEAN)",
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
        help=(
            "emit Wikipedia {{citation}} format which can be "
            "cited via {{sfn|Author2004|loc=p. 45}}. "
            "See: http://en.wikipedia.org/wiki/Template:Cite"
        ),
    )
    arg_parser.add_argument(
        "-y",
        "--YAML-CSL",
        default=False,
        action="store_true",
        help="emit YAML/CSL for use with pandoc [default]",
    )

    args = arg_parser.parse_args()
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
            filename="td.log", filemode="w", level=log_level, format=LOG_FORMAT
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    args.in_main = True
    args.outfd = sys.stdout

    if args.bibtex:
        args.biblatex = True
    if args.pretty and file_name == config.DEFAULT_MAP:
        file_name = config.DEFAULT_PRETTY_MAP
    if args.WP_citation:
        emitter_func = emit_wp
    elif args.biblatex:
        emitter_func = emit_biblatex
    elif args.JSON_CSL:
        emitter_func = emit_json_csl
    else:
        args.YAML_CSL = True
        emitter_func = emit_yaml_csl
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
        else:
            extension = ".unknown"
            raise Exception(f"unknown {extension}")
        output_fn = f"{os.path.splitext(file_name)[0]}{extension}"
        args.outfd = open(output_fn, "w", encoding="utf-8")
    if args.tests:
        import doctest

        from tests import test_thunderdell

        print("Running tests")
        doctest.testmod()
        test_thunderdell.test_results()
        sys.exit()

    if args.fields:
        print(
            textwrap.dedent(
                f"""
                ================ BIBLATEX_TYPES_ (deprecated) =========
                http://intelligent.pe.kr/LaTex/bibtex2.htm\n
                {pretty_tabulate_list(list(BIBLATEX_TYPES))}

                    d=2013 in=MIT t=mastersthesis
                    d=2013 in=MIT t=phdthesis

                ================  CSL_TYPES (preferred) ================ 
                http://aurimasv.github.io/z2csl/typeMap.xml\n
                {pretty_tabulate_list(list(BIB_TYPES))}

                    d=2014 p=ACM et=Conference on FOO ve=Boston
                    d=2013 in=MIT t=thesis g=Undergraduate thesis
                    d=2013 in=MIT t=thesis g=Masters thesis
                    d=2013 in=MIT t=thesis g=PhD dissertation
                
                ================  FIELD_SHORTCUTS ================
                 
                {pretty_tabulate_dict(BIB_SHORTCUTS)}

                    t=biblatex/CSL type (e.g., t=thesis)
                    ot=organization's subtype (e.g., W3C REC)
                    pa=section|paragraph|location|chapter|verse|column|line\n\n
        """
            )
        )
        sys.exit()

    if args.query:
        args.query = " ".join(args.query)
        args.query = urllib.parse.unquote(args.query)
        emitter_func = emit_results
    build_bib(args, file_name, emitter_func)
    args.outfd.close()
