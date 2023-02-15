#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Functions for emitting bibliographic entries to a file format."""

import logging
import re
import sys

# from thunderdell import CLIENT_HOME, HOME
# import config
from biblio.fields import (
    BIB_SHORTCUTS_ITEMS,
    BIBLATEX_TYPES,
    BORING_WORDS,
    CONTAINERS,
    CSL_BIBLATEX_TYPE_MAP,
    CSL_TYPES,
    EXCLUDE_URLS,
    ONLINE_JOURNALS,
)
from utils.text import escape_latex, normalize_whitespace

# logger function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

#################################################################
# Emitter utils
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
            first = "{{first}}"
            last = "{{last}}"

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


# fmt: off flake8: noqa
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
    if "entry_type" in entry:  # already has a type
        e_t = entry["entry_type"]
        if e_t in BIBLATEX_TYPES:
            pass
        elif e_t in CSL_TYPES:
            e_t = CSL_BIBLATEX_TYPE_MAP[e_t]
        else:
            print(f"Unknown entry_type = {e_t}")
            sys.exit()
        return e_t
    if "entry_type" in entry:  # already has a type
        return entry["entry_type"]
    else:
        e_t = "misc"
        if "eventtitle" in entry:
            if "author" in entry:
                e_t = "inproceedings"
            else:
                e_t = "proceedings"
        elif "booktitle" in entry:
            if "editor" not in entry:
                e_t = "inbook"
            else:
                if "author" in entry or "chapter" in entry:
                    e_t = "incollection"
                else:
                    e_t = "collection"
        elif "journal" in entry:
            e_t = "article"

        elif "author" in entry and "title" in entry and "publisher" in entry:
            e_t = "book"
        elif "institution" in entry:
            e_t = "report"
            if "type" in entry:
                if "report" in entry["type"].lower():
                    e_t = "report"
                if "thesis" in entry["type"].lower():
                    e_t = "mastersthesis"
                if "dissertation" in entry["type"].lower():
                    e_t = "phdthesis"
        elif "url" in entry:
            e_t = "online"
        elif "doi" in entry:
            e_t = "online"
        elif "date" not in entry:
            e_t = "unpublished"

        return e_t


# fmt: on


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
                cased_title.append("{{word}}")
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


def emit_biblatex(args, entries):
    """Emit a biblatex file"""
    # debug(f"entries = '{entries}'")

    for _key, entry in sorted(entries.items()):
        entry_type = guess_biblatex_type(entry)
        entry_type_copy = entry_type
        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        info(f"{entry=}")
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

        for _short, field in BIB_SHORTCUTS_ITEMS:
            if field in entry and entry[field] is not None:
                # critical(f"_short, field = '{_short} , {field}'")
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
                    date = "-".join(filter(None, (value.year, value.month, value.day)))
                    date = date + "~" if value.circa else date
                    value = date

                    if args.bibtex:
                        if entry["date"].year:
                            args.outfd.write(f"   year = {{{entry['date'].year}}},\n")
                        if entry["date"].month:
                            args.outfd.write(f"   month = {{{entry['date'].month}}},\n")
                        if entry["date"].day:
                            args.outfd.write(f"   day = {{{entry['date'].day}}},\n")

                # escape latex brackets.
                #   url and howpublished shouldn't be changed
                #   author may have curly brackets that should not be escaped
                #   date is a named_tuple that doesn't need escaping
                # debug(f"{field}")
                if field not in (
                    # "author",  # but underscores still need escape
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
