"""Emit YAML/CSL bibliographic data.

This modules uses strings because pyyaml is slow.
This constrained YAML is fast and works with pandoc-wrappers.md2bib().

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import re

from thunderdell.biblio.fields import (
    BIB_SHORTCUTS_ITEMS,
    BIBLATEX_CSL_FIELD_MAP,
    BIBLATEX_CSL_TYPE_MAP,
    BIBLATEX_TYPES,
    CONTAINERS,
    CSL_TYPES,
    EXCLUDE_URLS,
)
from thunderdell.types_thunderdell import EntriesDict, EntryDict, PersonName, PubDate


def guess_csl_type(entry: EntryDict) -> tuple[str, str | None, str | None]:
    """Guess whether the type of this entry is book, article, etc.

    >>> guess_csl_type({'author': [('', '', 'Smith', '')],\
        'eventtitle': 'Proceedings of WikiSym 08',\
        'publisher': 'ACM',\
        'title': 'A Great Paper',\
        'venue': 'Porto, Portugal California',\
        'date': '2008'})
    ('paper-conference', None, None)

    """
    # logging.info(f"{entry=}")
    genre: str | None = None
    medium: str | None = None
    e_t: str = "no-type"

    ## Validate exiting entry_type using CSL or BibLaTeX types
    if "entry_type" in entry:
        e_t = entry["entry_type"]
        if e_t in CSL_TYPES:
            return e_t, genre, medium
        elif e_t in BIBLATEX_TYPES:
            if e_t == "mastersthesis":
                return "thesis", "Master's thesis", medium
            elif e_t == "phdthesis":
                return "thesis", "PhD thesis", medium
            else:
                return BIBLATEX_CSL_TYPE_MAP[e_t], genre, medium
        else:
            raise RuntimeError(f"Unknown entry_type = {e_t}")

    ## Guess unknown entry_type based on existence of bibliographic fields
    types_from_fields = (
        # CONTAINER BASED TYPES
        ("article-journal", ["c_journal"]),
        ("article-magazine", ["c_magazine"]),
        ("article-newspaper", ["c_newspaper"]),
        ("entry-dictionary", ["c_dictionary"]),
        ("entry-encyclopedia", ["c_encyclopedia"]),
        ("post", ["c_forum"]),
        ("post-weblog", ["c_blog"]),
        ("webpage", ["c_web"]),
        # PAPERS
        ("article-journal", ["doi"]),
        ("article-journal", ["journal"]),
        ("paper-conference", ["eventtitle"]),
        ("paper-conference", ["booktitle", "editor", "organization"]),
        ("paper-conference", ["venue"]),
        # BOOKS
        ("chapter", ["chapter"]),
        ("chapter", ["booktitle"]),
        ("book", ["author", "title", "publisher"]),
        ("book", ["isbn"]),
        # REPORTS
        ("report", ["institution"]),
        # OTHER
        ("webpage", ["url"]),
    )

    for bib_type, fields in types_from_fields:
        # logging.info(f"testing {bib_type=:15} which needs {fields=} ")
        if all(field in entry for field in fields):
            # logging.info("FOUND IT: {bib_type=")
            e_t = bib_type
            break

    return e_t, genre, medium


def escape_yaml(s: str) -> str:
    r"""Escape YAML strings.

    >>> escape_yaml('hello "world"')
    '"hello \'world\'"'
    >>> escape_yaml('')
    ''
    """
    if s:  # faster to just quote than testing for tokens
        s = s.replace('"', r"'")
        # s = s.replace("#", r"\#") # this was introducing slashes in URLs
        s = s.replace("@", r"\\@")  # single slash caused bugs in past
        s = f'"{s}"'
    return s


def emit_yaml_people(people: list[PersonName]) -> str:
    """Yaml writer for authors and editors.

    >>> people = [("John", "van", "Doe", ""), ("Jim", "", "Smith", "Jr.")]
    >>> print(emit_yaml_people(people))
      - family: "Doe"
        given: "John"
        non-dropping-particle: "van"
      - family: "Smith"
        given: "Jim"
        suffix: "Jr."
    """
    lines = []
    for person in people:
        given, particle, family, suffix = person
        # if a name has no spaces, it is a literal
        if " " not in family and not given and not particle and not suffix:
            lines.append(f"  - literal: {escape_yaml(family)}")
        else:
            lines.append(f"  - family: {escape_yaml(family)}")
            if given:
                lines.append(f"    given: {escape_yaml(given)}")
            if suffix:
                lines.append(f"    suffix: {escape_yaml(suffix)}")
            if particle:
                lines.append(f"    non-dropping-particle: {escape_yaml(particle)}")
    return "\n".join(lines)


def emit_yaml_date(date: PubDate, season: str | None = None) -> str:
    """Yaml writer for dates.

    >>> from thunderdell.types_thunderdell import PubDate
    >>> d = PubDate(year=2023, month=6, day=15, circa=False)
    >>> print(emit_yaml_date(d))
        year: 2023
        month: 6
        day: 15
    """
    lines = []
    if date.year:
        lines.append(f"    year: {date.year}")
    if date.month:
        lines.append(f"    month: {date.month}")
    if date.day:
        lines.append(f"    day: {date.day}")
    if date.circa:
        lines.append("    circa: true")
    if season:
        lines.append(f"    season: {season}")
    return "\n".join(lines)


def yaml_protect_case(title: str) -> str:
    """Preserve/bracket proper names/nouns.

    https://github.com/jgm/pandoc-citeproc/blob/master/man/pandoc-citeproc.1.md

    >>> yaml_protect_case("The iKettle – a world off its rocker")
    "The <span class='nocase'>iKettle</span> – a world off its rocker"
    """
    return PROTECT_PAT.sub(r"<span class='nocase'>\1</span>", title)


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


def emit_yaml_csl(args: argparse.Namespace, entries: EntriesDict) -> None:
    """Emit citations in YAML/CSL for input to pandoc.

    See: https://reagle.org/joseph/2013/08/bib-mapping.html
        http://www.yaml.org/spec/1.2/spec.html
        http://jessenoller.com/blog/2009/04/13/yaml-aint-markup-language-completely-different

    """
    # begin YAML file
    # http://blog.martinfenner.org/2013/07/30/citeproc-yaml-for-bibliographies/#citeproc-yaml
    args.outfd.write("---\n")
    args.outfd.write("references:\n")

    for _key, entry in sorted(entries.items()):
        entry_type, genre, medium = guess_csl_type(entry)
        args.outfd.write(f"- id: {entry['identifier']}\n")
        args.outfd.write(f"  type: {entry_type}\n")
        if genre:
            args.outfd.write(f"  genre: {genre}\n")
        if medium:
            args.outfd.write(f"  medium: {medium}\n")

        # If author is replicated in container then delete author.
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        if entry.get("ori_author", None) in container_values:
            del entry["author"]

        # Legal cases are stored with judge names, but author should be removed
        # since they do not appear in references.
        if entry_type == "legal_case":
            del entry["author"]

        for _short, field in BIB_SHORTCUTS_ITEMS:
            if field in entry and entry[field] is not None:
                value = entry[field]
                # logging.debug(f"short, field = '{short} , {field}'")
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
                    args.outfd.write(emit_yaml_people(value) + "\n")
                    continue
                if field in ("date", "origdate", "urldate"):
                    # logging.debug(f'field = {field}')
                    if value == "0000":
                        continue
                    if field == "date":
                        # logging.debug(f"value = '{value}'")
                        season = entry.get("issue", None)
                        args.outfd.write("  issued:\n")
                        args.outfd.write(emit_yaml_date(value, season) + "\n")
                    if field == "origdate":
                        # logging.debug(f"value = '{value}'")
                        args.outfd.write("  original-date:\n")
                        args.outfd.write(emit_yaml_date(value) + "\n")
                    if field == "urldate":
                        args.outfd.write("  accessed:\n")
                        args.outfd.write(emit_yaml_date(value) + "\n")
                    continue

                if field == "urldate" and "url" not in entry:
                    continue  # no url, no 'read on'
                if field == "url":
                    # logging.debug(f"url = {value}")
                    if any(ban in value for ban in EXCLUDE_URLS):
                        # logging.debug("banned")
                        continue
                    # skip articles+URL w/ no pagination & other offline types
                    if args.urls_online_only:
                        # logging.debug("urls_online_only TRUE")
                        if entry_type in {"post", "post-weblog", "webpage"}:
                            # logging.debug(f"  not skipping online types")
                            pass
                        elif "pages" in entry:
                            # logging.debug("  skipping url, paginated item")
                            continue
                    # logging.debug(f"  writing url in pointy brackets WITHOUT escape_yaml")
                    # Placing URL in pointy brackets is useful and avoids having
                    # to escape specific characters.
                    args.outfd.write(f'  URL: "<{value}>"\n')
                    continue
                if (
                    field == "eventtitle"
                    and "container-title" not in entry
                    and "booktitle" not in entry
                    and "publisher" in entry
                ):
                    args.outfd.write(f'  container-title: "Proceedings of {value}"\n')
                    continue
                # 'Blog' is the null value I use in the mindmap.
                if field == "c_blog" and entry[field] == "Blog":
                    # netloc = urllib.parse.urlparse(entry['url']).netloc
                    # args.outfd.write(
                    #     f'  container-title: "Personal"\n')
                    continue

                # logging.debug(f"{field=}")
                if field in CONTAINERS:
                    # logging.debug(f"in CONTAINERS")
                    field = "container-title"
                    value = yaml_protect_case(value)
                    # logging.debug(f"{value=}")
                if field in BIBLATEX_CSL_FIELD_MAP:
                    # logging.debug(f"bib2csl field FROM =  {field}")
                    field = BIBLATEX_CSL_FIELD_MAP[field]
                    # logging.debug(f"bib2csl field TO   = {field}")
                args.outfd.write(f"  {field}: {escape_yaml(value)}\n")
    args.outfd.write("...\n")
