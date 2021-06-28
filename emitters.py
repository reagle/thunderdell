#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Functions for emitting bibliographic entries to a file format."""

import calendar
import logging
import os
import re
import sys
import urllib
from html import escape

from biblio_fields import (
    BIB_SHORTCUTS_ITEMS,
    BIBLATEX_CSL_FIELD_MAP,
    BIBLATEX_CSL_TYPE_MAP,
    BIBLATEX_TYPES,
    BIBLATEX_WP_FIELD_MAP,
    BORING_WORDS,
    CONTAINERS,
    CSL_BIBLATEX_TYPE_MAP,
    CSL_TYPES,
    EXCLUDE_URLS,
    ONLINE_JOURNALS,
)

# from thunderdell import CLIENT_HOME, HOME
from utils_text import escape_latex, normalize_whitespace
from utils_web import escape_XML

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


# fmt: off
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

    """  # noqa: E501
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


def emit_biblatex(entries, args):
    """Emit a biblatex file"""
    # debug(f"entries = '{entries}'")

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


def emit_yaml_csl(entries, args):
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


def emit_json_csl(entries, args):
    """Emit citations in CSL/JSON for input to pandoc

    See: https://reagle.org/joseph/2013/08/bib-mapping.html
        https://citeproc-js.readthedocs.io/en/latest/csl-json/markup.html

    """

    # NOTE: csljson can NOT be including as md doc yaml metadata
    # TODO: reduce redundancies with emit_yasn
    # TODO: yaml uses markdown `*` for italics, JSON needs <i>...</i>

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

    # # start of json buffer, to be written out after comma cleanup
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


def emit_wp_citation(entries, args):
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


def emit_results(entries, query, results_file, args):
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
        # debug(f"token = '{token}' type = '{type(token)}'")
        url_query = escape("search.cgi?query=%s") % token
        # debug(f"url_query = '{url_query}' type = '{type(url_query)}'")
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
