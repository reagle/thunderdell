#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Functions for emitting bibliographic entries to a file format."""

import logging
import re

from biblio.fields import (
    BIB_SHORTCUTS_ITEMS,
    BIBLATEX_CSL_FIELD_MAP,
    BIBLATEX_CSL_TYPE_MAP,
    BIBLATEX_TYPES,
    CONTAINERS,
    CSL_TYPES,
    EXCLUDE_URLS,
)

# logger function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


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
    if "entry_type" in entry:  # already has a type
        et = entry["entry_type"]
        if et in CSL_TYPES:
            return et, genre, medium
        elif et in BIBLATEX_TYPES:
            if et == "mastersthesis":
                return "thesis", "Master's thesis", medium
            elif et == "phdthesis":
                return "thesis", "PhD thesis", medium
            else:
                return BIBLATEX_CSL_TYPE_MAP[et], genre, medium
        else:
            raise RuntimeError(f"Unknown entry_type = {et}")

    # fmt: off
    et = "no-type"
    # debug(f"looking at containers for {entry}")
    if "c_web" in entry:                et = "webpage"
    elif "c_blog" in entry:             et = "post-weblog"
    elif "c_newspaper" in entry:        et = "article-newspaper"
    elif "c_magazine" in entry:         et = "article-magazine"
    elif "c_journal" in entry:          et = "article-journal"
    elif "c_dictionary" in entry:       et = "entry-dictionary"
    elif "c_encyclopedia" in entry:     et = "entry-encyclopedia"
    elif "c_forum" in entry:            et = "post"
    else:
        if "eventtitle" in entry:           et = "paper-conference"
        elif "booktitle" in entry:
            if "editor" in entry:           # collection or incollection
                if "chapter" in entry:      et = "chapter"
                else:                       et = "book"   # ? collection
            elif "organization" in entry:   et = "paper-conference"
            else:                           et = "chapter"
        elif "journal" in entry:            et = "article-journal"

        elif "author" in entry and "title" in entry and "publisher" in entry:
            et = "book"
        elif "author" not in entry:
            if "venue" in entry:            et = "book"         # ? proceedings
            if "editor" in entry:           et = "book"         # ? collection
        elif "institution" in entry:
            et = "report"
            if "type" in entry:
                org_subtype = entry["type"].lower()
                if "report" in org_subtype: et = "report"
                if "thesis" in org_subtype or "dissertation" in org_subtype:
                    et = "thesis"
        elif "url" in entry:                et = "webpage"
        elif "doi" in entry:                et = "article"
        elif "date" not in entry:           et = "manuscript"
    # fmt: on
    return et, genre, medium


def emit_yaml_csl(args, entries):
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
                    f"    non-dropping-particle: {escape_yaml(particle)}\n"
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
            args.outfd.write("    circa: true\n")
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

    for _key, entry in sorted(entries.items()):
        entry_type, genre, medium = guess_csl_type(entry)
        args.outfd.write(f'- id: {entry["identifier"]}\n')
        args.outfd.write(f"  type: {entry_type}\n")
        if genre:
            args.outfd.write(f"  genre: {genre}\n")
        if medium:
            args.outfd.write(f"  medium: {medium}\n")

        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        if entry.get("ori_author") in container_values:
            if not args.author_create:
                del entry["author"]
            else:
                entry["author"] = [["", "", "".join(entry["ori_author"]), ""]]

        for _short, field in BIB_SHORTCUTS_ITEMS:
            if field in entry and entry[field] is not None:
                value = entry[field]
                # debug(f"short, field = '{short} , {field}'")
                # skipped fields
                if field in ("identifier", "entry_type", "issue"):
                    continue

                # special format fields
                if field == "title":
                    title = yaml_protect_case(escape_yaml(value))
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
                    args.outfd.write(f'  container-title: "Proceedings of {value}"\n')
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
