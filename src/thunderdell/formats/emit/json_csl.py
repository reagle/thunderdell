"""Emit JSON/CSL bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import json
import logging
import re
from collections.abc import Sequence
from typing import Any

from thunderdell.biblio.fields import (
    BIB_SHORTCUTS_ITEMS,
    BIBLATEX_CSL_FIELD_MAP,
    CONTAINERS,
    EXCLUDE_URLS,
)
from thunderdell.formats.emit.yaml_csl import guess_csl_type
from thunderdell.types_thunderdell import EntryDict


def escape_csl(s: str | None) -> str | int | None:
    r"""Escape CSL string for JSON output.

    >>> escape_csl("Hello\nWorld")
    '"Hello\\nWorld"'
    >>> escape_csl('He said "yes"')
    '"He said \\"yes\\""'
    >>> escape_csl("email@example.com")
    '"email@example.com"'
    >>> escape_csl("12345")
    12345
    >>> escape_csl(None) is None
    True
    """
    if s is None:
        return None
    if s.isdigit():
        return int(s)
    return json.dumps(s)


def do_csl_person(person: Sequence[str]) -> dict[str, str]:
    """CSL writer for authors and editors.

    biblatex: ('First Middle', 'von', 'Last', 'Jr.')
    CSL: ('family', 'given', 'suffix' 'non-dropping-particle',
          'dropping-particle')
    """
    given, particle, family, suffix = person
    person_dict: dict[str, str] = {}
    if family:
        person_dict["family"] = family
    if given:
        person_dict["given"] = given
    if suffix:
        person_dict["suffix"] = suffix
    if particle:
        person_dict["non-dropping-particle"] = particle
    return person_dict


def do_csl_date(date: Any, season: str | None = None) -> dict[str, Any]:
    r"""CSL writer for dates.

    >>> class DummyDate:
    ...     def __init__(self):
    ...         self.year = 2023
    ...         self.month = 4
    ...         self.day = 29
    ...         self.circa = False
    >>> do_csl_date(DummyDate())
    {'date-parts': [[2023, 4, 29]]}

    >>> class DummyDateCirca:
    ...     def __init__(self):
    ...         self.year = 2023
    ...         self.month = 4
    ...         self.day = 29
    ...         self.circa = True
    >>> do_csl_date(DummyDateCirca(), season="spring")
    {'date-parts': [[2023, 4, 29]], 'circa': True, 'season': 'spring'}

    """
    date_parts = []
    if date.year:
        date_parts.append(int(date.year))
    if date.month:
        date_parts.append(int(date.month))
    if date.day:
        date_parts.append(int(date.day))

    date_dict: dict[str, Any] = {"date-parts": [date_parts]}
    if getattr(date, "circa", False):
        date_dict["circa"] = True
    if season:
        date_dict["season"] = season

    logging.debug(f"{date_dict=}")
    return date_dict


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


def csl_protect_case(title: str) -> str:
    """Preserve/bracket proper names/nouns in title.

    See:
    https://github.com/jgm/pandoc-citeproc/blob/master/man/pandoc-citeproc.1.md

    >>> csl_protect_case("The iKettle – a world off its rocker")
    "The <span class='nocase'>iKettle</span> – a world off its rocker"
    """
    return PROTECT_PAT.sub(r"<span class='nocase'>\1</span>", title)


def emit_json_csl(args: Any, entries: dict[str, EntryDict]) -> None:
    """Emit citations in CSL/JSON format for input to pandoc."""
    # NOTE: csljson can NOT be included as markdown document yaml metadata
    # TODO: reduce redundancies with emit_yasn
    # TODO: yaml uses markdown `*` for italics, JSON needs <i>...</i>

    output_list = []
    for _key, entry in sorted(entries.items()):
        entry_type, genre, medium = guess_csl_type(entry)
        obj: dict[str, Any] = {
            "id": entry["identifier"],
            "type": entry_type,
        }
        if genre:
            obj["genre"] = genre
        if medium:
            obj["medium"] = medium

        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        if entry["ori_author"] in container_values:
            if not args.author_create:
                entry.pop("author", None)
            else:
                entry["author"] = [["", "", "".join(entry["ori_author"]), ""]]

        for _short, field in BIB_SHORTCUTS_ITEMS:
            if entry.get(field):
                value = entry[field]
                if field in ("identifier", "entry_type"):  # already done above
                    continue
                if field in ("issue"):  # done below with date/season
                    continue

                if field == "title":
                    escaped_value = escape_csl(value)
                    if isinstance(escaped_value, str):
                        title = csl_protect_case(escaped_value)
                    else:
                        title = str(escaped_value)
                    obj["title"] = (
                        json.loads(title) if isinstance(title, str) else title
                    )
                    continue
                if field in ("author", "editor", "translator"):
                    obj[field] = [do_csl_person(person) for person in value]
                    continue
                if field in ("date", "origdate", "urldate"):
                    if value == "0000":
                        continue
                    if field == "date":
                        season = entry.get("issue", None)
                        obj["issued"] = do_csl_date(value, season)
                    if field == "origdate":
                        obj["original-date"] = do_csl_date(value)
                    if field == "urldate":
                        obj["accessed"] = do_csl_date(value)
                    continue

                if field == "urldate" and "url" not in entry:
                    continue  # no url, no 'read on'
                if field == "url":
                    if any(ban for ban in EXCLUDE_URLS if ban in value):
                        continue
                    if args.urls_online_only:
                        if entry_type in {"post", "post-weblog", "webpage"}:
                            pass
                        elif "pages" in entry:
                            continue
                    obj["URL"] = value
                    continue
                # if (
                #     field == "eventtitle"
                #     and "container-title" not in entry
                #     and "booktitle" not in entry
                # ):
                #     obj["container-title"] = f"Proceedings of {value}"
                #     continue
                if field == "c_blog" and entry[field] == "Blog":
                    continue

                if field in CONTAINERS:
                    field = "container-title"
                    value = csl_protect_case(value)
                if field in BIBLATEX_CSL_FIELD_MAP:
                    field = BIBLATEX_CSL_FIELD_MAP[field]
                obj[field] = value
        output_list.append(obj)

    json.dump(output_list, args.outfd, indent=2)
    args.outfd.write("\n")
