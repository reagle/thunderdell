#!/usr/bin/env python3
"""Extract a bibliography from a Freeplane mindmap to multiple formats.

https://reagle.org/joseph/2009/01/thunderdell.html
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import contextlib  # https://docs.python.org/3/library/contextlib.html
import errno
import http.server
import logging as log
import os
import re
import sys
import textwrap
import urllib.parse
import webbrowser
import xml.etree.ElementTree as et
from collections.abc import Callable
from pathlib import Path
from typing import NamedTuple
from urllib.parse import parse_qs

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
    emit_wikipedia,
    emit_yaml_csl,
)
from types_thunderdell import Date, EntryDict
from utils.text import pretty_tabulate_dict, pretty_tabulate_list, strip_accents
from utils.web import unescape_entities

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
    file_name: Path,
    emitter_func: Callable[[argparse.Namespace, dict], None],
) -> None:
    """Build bibliography of entries from a Freeplane mindmap."""
    links = set()
    done = set()
    entries: dict[str, dict] = {}
    mm_files = {file_name}
    while mm_files:
        mm_file = mm_files.pop()
        log.debug(f"   parsing {mm_file}")
        try:
            doc = et.parse(mm_file).getroot()
        except (OSError, et.ParseError) as err:
            log.debug(f"    failed to parse {mm_file} because of {err}")
            continue
        entries, links = walk_freeplane(args, doc, mm_file, entries, links=[])
        done.add(mm_file)
        if args.chase:
            new_links = {
                # (mm_file.parent / link).resolve()
                (Path(mm_file).parent / link).resolve()
                for link in links
                if not any(word in link for word in ("syllabus", "readings"))
            }
            mm_files.update(new_links - done)

    if args.query:
        serve_query(args, entries)
    elif args.pretty:
        show_pretty(args, entries)
    else:
        emitter_func(args, entries)


def walk_freeplane(args, node, mm_file, entries, links):
    """Walk the freeplane XML tree and build dictionary of entries.

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
        """Return a modified node with matches highlighted."""
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

    def _get_author_node(title_node):
        """Return the nearest ancestor that is an author node using parent_map[node]."""
        try:
            ancestor = parent_map[title_node]
            while ancestor.get("STYLE_REF") != "author":
                ancestor = parent_map[ancestor]
            return ancestor
        except KeyError:
            print(f'''ERROR: author node not found for "{title_node.get('TEXT')}"''')
            sys.exit()

    def _remove_identity_hints(authors: str) -> str:
        """Remove identity hints from names.

        Names in the authors strings might have:
        - 'u/' for interviewee using known username
        - 'p/' for interviewee using pseudonym.

        >>> remove_identity_hints("J Smith III, u/Jane Smith, p/AnonymousUser, u/Alice123")
        'J Smith III, AnonymousUser, Alice123'

        """
        return ", ".join(
            [
                author.removeprefix("u/").removeprefix("p/")
                for author in authors.split(", ")
            ]
        )

    for d in node.iter():
        link = d.get("LINK", "")
        if (
            "LINK" in d.attrib
            and (link := d.get("LINK")).endswith(".mm")  # other mindmaps
            and not link.startswith("http")  # local only
            and not link.endswith("-outline.mm")  # no outlines
        ):
            links.append(unescape_entities(link))
        # skip nodes that are structure, comment, and empty of text
        if "STYLE_REF" in d.attrib and d.get("TEXT"):
            if d.get("STYLE_REF") == "author":
                # pass author as it will be fetched upon new title
                pass
            elif d.get("STYLE_REF") == "title":
                commit_entry(args, entry, entries)  # new entry, so store previous
                entry = {}  # and create new one
                # Because entries are based on unique titles, author processing
                # is deferred until now when a new title is found.
                author_node = _get_author_node(d)
                entry["ori_author"] = unescape_entities(author_node.get("TEXT"))
                entry["author"] = parse_names(
                    _remove_identity_hints(entry["ori_author"])
                )
                entry["title"] = unescape_entities(d.get("TEXT"))
                entry["_mm_file"] = str(mm_file)
                entry["_title_node"] = d
                if (url := d.attrib.get("LINK")) and not url.startswith(
                    ("../", "file://")  # ignore local file URLS
                ):
                    entry["url"] = url
                if args.query:
                    author_highlighted = _query_highlight(author_node, args.query)
                    if author_highlighted is not None:
                        entry["_author_result"] = author_highlighted
                    title_highlighted = _query_highlight(d, args.query)
                    if title_highlighted is not None:
                        entry["_title_result"] = title_highlighted
            else:
                if d.get("STYLE_REF") == "cite":
                    entry["cite"] = unescape_entities(d.get("TEXT"))
                elif d.get("STYLE_REF") == "annotation":
                    entry["annotation"] = unescape_entities(d.get("TEXT").strip())
                if args.query:
                    node_highlighted = _query_highlight(d, args.query)
                    if node_highlighted is not None:
                        entry.setdefault("_node_results", []).append(node_highlighted)

    # commit the last entry as no new titles left
    entries = commit_entry(args, entry, entries)
    return entries, links


def serve_query(args: argparse.Namespace, entries: dict) -> None:
    """Serve crawl/query results and open browser.

    Given the entries resulting from a crawl/query, create a web server and open browser.
    """
    # debug("querying")
    results_file_name = config.TMP_DIR / "query-thunderdell.html"

    if results_file_name.exists():
        results_file_name.unlink()
    try:
        with results_file_name.open(mode="w", encoding="utf-8") as results_file:
            args.results_file = results_file
            results_file.write(RESULT_FILE_HEADER)
            results_file.write(RESULT_FILE_QUERY_BOX % (args.query, args.query))
            emit_results(args, entries)
            results_file.write("</ul></body></html>\n")
    except OSError as err:
        print(f"{err}\nThere was an error writing to {results_file_name}")
        raise
    # debug(f"{results_file=}")
    if args.in_main:
        ADDRESS_IN_USE = False
        os.chdir(config.CGI_DIR.parent)
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
    """Use pretty format."""
    # results_file_name = config.TMP_DIR / "pretty-print.html"
    results_file_name = Path(args.input_file.with_suffix(".html")).absolute()
    try:
        args.results_file = results_file_name.open("w", encoding="utf-8")
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
    """Place an entry in the entries dictionary with default values if need be."""
    if entry != {}:
        entry.setdefault("author", [("John", "", "Doe", "")])
        entry.setdefault("ori_author", [("John", "", "Doe", "")])
        entry.setdefault("title", "Unknown")
        entry.setdefault("date", "0000")
        entry.setdefault("_mm_file", "")

        # pull the citation, create an identifier, and enter in entries
        try:
            entry = pull_citation(args, entry)  # parse a=b c=d syntax
        except Exception:
            print(f"pull_citation error on {entry['author']}: {entry['_mm_file']}")
            raise
        entry["identifier"] = get_identifier(entry, entries)
        entries[entry["identifier"]] = entry
    return entries


#################################################################
# Entry construction
#################################################################


def pull_citation(args, entry: EntryDict) -> EntryDict:
    """Modify entry with parsed citation and field-specific heuristics.

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


def parse_pairs(entry: EntryDict) -> EntryDict:
    """Parse entry['cite'] values as `key=value` pairs; add them to entry dictionary.

    >>> entry = {"cite": "d=20030723 j=Research Policy v=32 n=7 pp=1217-1241", "title": "Test", "_mm_file": "test.mm"}
    >>> BIB_SHORTCUTS = {"d": "date", "j": "journal", "v": "volume", "n": "number", "pp": "pages"}
    >>> parse_pairs(entry)
    {'cite': 'd=20030723 j=Research Policy v=32 n=7 pp=1217-1241', 'title': 'Test', '_mm_file': 'test.mm', 'date': '20030723', 'journal': 'Research Policy', 'volume': '32', 'number': '7', 'pages': '1217-1241'}

    """
    if citation := entry.get("cite"):
        CITE_RE = re.compile(
            r"""
            (\w{1,3})=([^=]+)  # key = value
            (?=                # positive lookahead (don't consume characters)
                \s+\w{1,3}=|$  # space(s), another key-value pair OR end of string
            )
            """,
            re.VERBOSE,
        )

        # Use regex to find all key-value pairs in one pass
        for short, value in CITE_RE.findall(citation):
            # Look up the full key name in BIB_SHORTCUTS
            if key := BIB_SHORTCUTS.get(short):
                value = value.strip()
                if key == "keyword" and key in entry:
                    # Append new keywords to existing ones
                    entry[key] += f", {value}"
                else:
                    # Set or overwrite the value for other keys
                    entry[key] = value
            else:
                print(f"Key error on {short}, {entry['title']}, {entry['_mm_file']}")
    return entry


def identity_add_title(ident: str, title: str) -> str:
    """Return a non-colliding identity.

    Disambiguate keys by appending the first letter of first
    3 significant words (e.g., no WP:namespace, articles, conjunctions
    or short prepositions). If only one word, use first, penultimate,
    and last character.

    >>> identity_add_title('Wikipedia 2008', 'Wikipedia:Neutral Point of View')
    'Wikipedia 2008npv'

    """
    # debug(f"title = '{title}'")
    suffix = ""

    CLEAN_PATTERN = re.compile(
        r"""
        ^Wikipedia:|           # Wikipedia namespaces
        ^Category:|
        ^\[WikiEN-l\]|         # email lists
        ^\[Wikipedia-l\]|
        ^\[Wiki-l\]|
        ^\[Wiktionary-l\]|
        ^\[Foundation-l\]|
        ^\[Textbook-l\]|
        \.0|                   # 2.0
        '|                     # apostrophe
        ^r/                    # subreddits
    """,
        flags=re.VERBOSE,
    )
    NOT_ALPHANUM_PAT = re.compile("[^a-zA-Z0-9']")

    clean_title = CLEAN_PATTERN.sub("", title) or "foo"
    title_words = NOT_ALPHANUM_PAT.split(clean_title.lower())

    if len(title_words) == 1:
        suffix = f"{title_words[0][0]}{title_words[0][-2:]}"
    else:
        suffix = "".join([word[0] for word in title_words if word not in BORING_WORDS])
        suffix = suffix[:3]
    ident = f"{ident}{suffix}"
    return ident


def identity_increment(ident, entries):
    """Increment numerical suffix of identity until no longer collides.

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


def clean_identifier(ident: str) -> str:
    """Remove chars not liked by XML, bibtex, pandoc, etc.

    >>> clean_identifier("José Alvereze@[hispania]")
    'Jose Alverezehispania'

    >>> clean_identifier("<strong>123JohnSmith</strong>")
    'a123JohnSmith'
    """
    clean_id = (
        ident.replace("<strong>", "")  # added by walk_freeplane.query_highlight
        .replace("</strong>", "")  # ...
        .replace(":", "")  # used for XML namespaces
        .replace("'", "")  # not permitted in XML name/id attributes
        .replace("/", "")
        .replace("’", "")
        .replace(".", "")  # punctuation
        .replace("@", "")
        .replace("[", "")
        .replace("]", "")
        .replace("(", "")
        .replace(")", "")
    )
    # debug(f"4 clean_id = {type(clean_id)} '{clean_id}'")
    clean_id = strip_accents(clean_id)  # unicode is buggy in bibtex keys
    if clean_id[0].isdigit():  # pandoc forbids keys starting with digits
        clean_id = f"a{clean_id}"
    return clean_id


def get_identifier(entry: dict, entries: dict, delim: str = ""):
    """Create an identifier (key) for the entry based on last names, year, and title."""
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
    ident = clean_identifier(ident)
    ident = identity_add_title(ident, entry["title"])  # get title suffix
    if ident in entries:  # there is a collision
        log.warning(
            f"collision on {ident}: {entry['title']} & {entries[ident]['title']}"
        )
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

    """
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
            if len(chunks) > 0 and chunks[-1] in PARTICLES:
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
        type=Path,
        metavar="FILENAME",
        help="mindmap to process",
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
        help="increase verbosity from critical though error, warning, info, and debug",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__} using Python {sys.version}",
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
    file_name = args.input_file.absolute()

    log_level = (log.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    if args.log_to_file:
        print("logging to file")
        log.basicConfig(
            filename="td.log", filemode="w", level=log_level, format=LOG_FORMAT
        )
    else:
        log.basicConfig(level=log_level, format=LOG_FORMAT)

    args.in_main = True
    args.outfd = sys.stdout

    if args.bibtex:
        args.biblatex = True
    if args.pretty and file_name == config.DEFAULT_MAP:
        file_name = config.DEFAULT_PRETTY_MAP
    if args.WP_citation:
        emitter_func = emit_wikipedia
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

    # Determine the output file path
    if args.output_to_file:
        if args.YAML_CSL:
            suffix = ".yaml"
        elif args.JSON_CSL:
            suffix = ".json"
        elif args.biblatex:
            suffix = ".bib"
        elif args.WP_citation:
            suffix = ".wiki"
        else:
            raise ValueError("Unknown output format")
        output_path = file_name.with_suffix(suffix)
    else:
        output_path = None

    if args.tests:
        import doctest

        from tests import test_thunderdell
        # from tests import test_extract_kindle, text_extract_goodreader

        print("Running tests")
        doctest.testmod()
        test_thunderdell.test_results()
        # test_extract_kindle.test_process_html()
        # test_extract_goodreader.test_process_text()
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

    # Use a context manager to handle the output
    with contextlib.ExitStack() as stack:
        if output_path:
            args.outfd = stack.enter_context(output_path.open("w", encoding="utf-8"))
        else:
            args.outfd = sys.stdout

        build_bib(args, file_name, emitter_func)
