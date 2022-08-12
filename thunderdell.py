#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <https://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Thunderdell, by Joseph Reagle http://reagle.org/joseph/

Extract a bibliography from a Freeplane mindmap"""

# TODO

import errno
import http.server
import logging
import os
import re
import sys
import urllib.parse
import webbrowser
import xml.etree.ElementTree as et

from collections import namedtuple
from subprocess import call  # noqa F401 needed for doctests
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

from formats import (
    emit_biblatex,
    emit_json_csl,
    emit_results,
    emit_wp,
    emit_yaml_csl,
)

from utils.text import (
    pretty_tabulate_dict,
    pretty_tabulate_list,
    strip_accents,
)
from utils.web import unescape_XML

log_level = logging.ERROR  # 40 # declared here for when imported

# logger function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

Date = namedtuple("Date", ["year", "month", "day", "circa", "time"])

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
        entry["date"] = Date(year="0000", month=None, day=None, circa=None, time=None)
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
        warning(f"collision on {ident}: {entry['title']} & {entries[ident]['title']}")
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
                print(("Key error on ", error, entry["title"], entry["_mm_file"]))

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

    # # split off unneeded search parameters
    # if 'url' in entry and entry['url'] is not None:
    #     if any([site in entry['url'] for site in ('books.google', 'jstor')]):
    #         entry['url'] = entry['url'].split('&')[0]

    # remove private Reddit message URLs
    if "url" in entry and entry["url"].startswith("https://www.reddit.com/message"):
        entry.pop("url")
        entry.pop("urldate", None)

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
        except Exception:
            print(f"pull_citation error on {entry['author']}: " f"{entry['_mm_file']}")
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

    parent_map = {c: p for p in node.iter() for c in p}

    def get_parent(node):
        return parent_map[node]

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
            if not d.get("LINK").startswith("http:") and d.get("LINK").endswith(".mm"):
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
                    author_highlighted = query_highlight(author_node, args.query)
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
                        entry.setdefault("_node_results", []).append(node_highlighted)

    # commit the last entry as no new titles left
    entries = commit_entry(entry, entries)
    return entries, links


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


def build_bib(args, file_name, output):
    """Parse and process files, including new ones encountered if chasing"""

    links = []  # list of other files encountered in the mind map
    done = []  # list of files processed, kept to prevent loops
    entries = dict()  # dict of {id : {entry}}, by insertion order
    mm_files = [
        file_name,
    ]  # list of file encountered (e.g., chase option)
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
        entries, links = walk_freeplane(doc, mm_file, entries, links=[])
        # debug("    done.appending %s" % os.path.abspath(mm_file))
        done.append(mm_file)
        if args.chase:
            # debug("chasing")
            for link in links:
                link = os.path.abspath(os.path.dirname(mm_file) + "/" + link)
                if link not in done and link not in mm_files:
                    if not any(
                        [word in link for word in ("syllabus", "readings")]
                    ):  # 'old'
                        # debug(f"    mm_files.appending {link}")
                        mm_files.append(link)

    if args.query:
        # debug("querying")
        results_file_name = f"{config.TMP_DIR}query-thunderdell.html"
        if os.path.exists(results_file_name):
            os.remove(results_file_name)
        try:
            results_file = open(results_file_name, "w", encoding="utf-8")
        except OSError as err:
            print(f"{err}")
            print(f"There was an error writing to {results_file_name}")
            raise
        results_file.write(RESULT_FILE_HEADER)
        results_file.write(RESULT_FILE_QUERY_BOX % (args.query, args.query))
        emit_results(args, entries, args.query, results_file)
        results_file.write("</ul></body></html>\n")
        results_file.close()
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
        results_file_name = f"{config.TMP_DIR}pretty-print.html"
        try:
            results_file = open(results_file_name, "w", encoding="utf-8")
        except OSError as err:
            print(f"{err}")
            print(f"There was an error writing to {results_file_name}")
            raise
        results_file.write(RESULT_FILE_HEADER)
        results_file.write(
            "    <title>Pretty Mind Map</title></head>" '<body>\n<ul class="top">\n'
        )
        for entry in list(entries.values()):
            args.query = entry["identifier"]
            emit_results(args, entries, args.query, results_file)
        results_file.write("</ul></body></html>\n")
        results_file.close()
        if args.in_main:
            webbrowser.open(f"file://{results_file_name}")

    else:
        output(args, entries)
    return


# TODO: replace "~/bin" with HOME
# TODO: move golden tests to something standard, perhaps:
# https://pypi.org/project/pytest-golden/
# https://stackoverflow.com/questions/3942820/how-to-do-unit-testing-of-functions-writing-files-using-pythons-unittest


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

    if args.pretty and file_name == config.DEFAULT_MAP:
        file_name = config.DEFAULT_PRETTY_MAP
    if args.WP_citation:
        output = emit_wp
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
        print("      pa=section|paragraph|location|chapter|verse|column|line\n\n")
        sys.exit()
    if args.query:
        args.query = " ".join(args.query)
        args.query = urllib.parse.unquote(args.query)
        output = emit_results
    build_bib(args, file_name, output)
    args.outfd.close()
else:

    class args:
        in_main = False  # imported or called from cgi
        chase = True  # Follow freeplane links to other local maps
        long_url = False  # Use short 'oldid' URLs for mediawikis
        urls_online_only = False  # Emit urls for @online only
        pretty = False  # Print as HTML with citation at end
        query = None  # Query the bibliographies
