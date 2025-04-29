"""Emit JSON/CSL bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import re
from collections.abc import Sequence
from typing import Any, List, Optional, Union

from thunderdell.biblio.fields import (
    BIB_SHORTCUTS_ITEMS,
    BIBLATEX_CSL_FIELD_MAP,
    CONTAINERS,
    EXCLUDE_URLS,
)
from thunderdell.formats.emit.yaml_csl import guess_csl_type


def escape_csl(s: str | None) -> str | int | None:
    """Escape CSL string for JSON output."""
    if s:  # faster to just quote than testing for tokens
        s = s.replace("\n", "\\n")
        s = s.replace('"', r"'")
        # s = s.replace("#", r"\#") # this was introducing slashes in URLs
        s = s.replace("@", r"\\@")  # single slash caused bugs in past
        s = f'"{s}"'
    if s and s.isdigit():
        return int(s)
    else:
        return s


def do_csl_person(person: Sequence[str]) -> list[str]:
    """CSL writer for authors and editors."""
    # biblatex ('First Middle', 'von', 'Last', 'Jr.')
    # CSL ('family', 'given', 'suffix' 'non-dropping-particle',
    #      'dropping-particle')
    # debug("person = '%s'" % (' '.join(person)))
    given, particle, family, suffix = person
    person_buffer: list[str] = []
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
        person_buffer.append(f'"non-dropping-particle": {escape_csl(particle)}, ')
    person_buffer.append("},\n")
    return person_buffer


def do_csl_date(date: Any, season: str | None = None) -> list[str]:
    """CSL writer for dates."""
    date_buffer: list[str] = []
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
        date_buffer.append('        "circa": true,\n')
    if season:
        date_buffer.append(f'        "season": "{season}",\n')
    date_buffer.append("    },\n")

    logging.debug(f"{date_buffer=}")
    return date_buffer


def csl_protect_case(title: str) -> str:
    """Preserve/bracket proper names/nouns in title.

    See:
    https://github.com/jgm/pandoc-citeproc/blob/master/man/pandoc-citeproc.1.md
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


def emit_json_csl(args: Any, entries: dict[str, dict[str, Any]]) -> None:
    """Emit citations in CSL/JSON format for input to pandoc."""
    # NOTE: csljson can NOT be included as markdown document yaml metadata
    # TODO: reduce redundancies with emit_yasn
    # TODO: yaml uses markdown `*` for italics, JSON needs <i>...</i>

    # Start of json buffer, to be written out after comma cleanup
    # NOTE: f-string interpolation does not happen immediately
    # when the string is appended to the list 2024-05-02
    file_buffer = ["[\n"]
    for _key, entry in sorted(entries.items()):
        # debug(f"{_key=}")
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

        for _short, field in BIB_SHORTCUTS_ITEMS:
            if entry.get(field):
                value = entry[field]
                # debug(f"short, field = '{short} , {field}'")
                if field in ("identifier", "entry_type"):  # already done above
                    continue
                if field in ("issue"):  # done below with date/season
                    continue

                # special format fields
                if field == "title":
                    title = csl_protect_case(escape_csl(value))
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
                        season = entry.get("issue", None)
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
