"""Emit biblatex bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import argparse
import logging
import re

from thunderdell.biblio.fields import (
    BIB_SHORTCUTS_ITEMS,
    BIBLATEX_TYPES,
    BORING_WORDS,
    CONTAINERS,
    CSL_BIBLATEX_TYPE_MAP,
    CSL_TYPES,
    EXCLUDE_URLS,
    ONLINE_JOURNALS,
)
from thunderdell.types_thunderdell import EntriesDict, PubDate
from thunderdell.utils.text import escape_latex, normalize_whitespace

#################################################################
# Emitter utils
#################################################################


def create_biblatex_author(names):
    """Return the parts of the name joined appropriately.

    The BibTex name parsing is best explained in
    http://www.tug.org/TUGboat/tb27-2/tb87hufflen.pdf.

    >>> create_biblatex_author([('First Middle', 'von', 'Last', 'Jr.'),\
        ('First', '', 'Last', 'II')])
    'von Last, Jr., First Middle and Last, II, First'

    """
    full_names = []

    for name in names:
        full_name = ""
        first, von, last, jr = name[0:4]

        # if a name has no spaces, it is a literal
        if " " not in last and not first and not von and not jr:
            full_names.append("{{last}}")
            continue

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
    # info(f"{entry=}")
    e_t = "misc"

    ## Validate exiting entry_type using CSL or BibLaTeX types
    if "entry_type" in entry:  # already has a type
        # breakpoint()
        e_t = entry["entry_type"]
        if e_t in BIBLATEX_TYPES:
            return e_t
        elif e_t in CSL_TYPES:
            return CSL_BIBLATEX_TYPE_MAP[e_t]
        else:
            raise RuntimeError(f"Unknown entry_type = {e_t}")

    ## https://mirrors.ibiblio.org/CTAN/macros/latex/contrib/biblatex/doc/biblatex.pdf
    ## Guess unknown entry_type based on existence of bibliographic fields
    types_from_fields = [
        # CONTAINER BASED TYPES
        ("article", ["c_journal"]),
        ("periodical", ["c_magazine"]),
        ("periodical", ["c_newspaper"]),
        ("inreference", ["c_dictionary"]),
        ("inreference", ["c_encyclopedia"]),
        ("online", ["c_forum"]),
        ("online", ["c_blog"]),
        ("online", ["c_web"]),
        # PAPERS
        ("article", ["doi"]),
        ("article", ["journal"]),
        ("inproceedings", ["author", "eventtitle"]),
        ("proceedings", ["eventtitle"]),
        ("proceedings", ["booktitle", "editor", "organization"]),
        ("proceedings", ["venue"]),
        # BOOKS: inbook = chapter in single-author; incollection = multi-author
        ("incollection", ["editor", "chapter"]),
        ("incollection", ["title", "booktitle"]),
        ("book", ["author", "title", "publisher"]),
        ("incollection", ["editor"]),
        ("book", ["isbn"]),
        # REPORTS
        ("report", ["institution"]),
        # OTHER
        ("online", ["url"]),
    ]

    for bib_type, fields in types_from_fields:
        # info(f"testing {bib_type=:15} which needs {fields=} ")
        if all(field in entry for field in fields):
            # info("FOUND IT: {bib_type=")
            e_t = bib_type
            break

    return e_t


def bibformat_title(title: str) -> str:
    """Title case text, and preserve/bracket proper names/nouns.

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
        """Title case after some chars, but not ['.] like .title()."""
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


def emit_biblatex(args: argparse.Namespace, entries: EntriesDict):
    """Emit a biblatex file."""
    # debug(f"entries = '{entries}'")

    for _key, entry in sorted(entries.items()):
        entry_type = guess_biblatex_type(entry)
        entry_type_copy = entry_type
        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        logging.info(f"{entry=}")

        # If author is replicated in container then delete author.
        if entry["ori_author"] in container_values:
            del entry["author"]

        # Legal cases are stored with judge names, but author should be removed
        # since they do not appear in references.
        if entry_type == "legal_case":
            del entry["author"]

        # if an edited collection, remove author and booktitle
        if (
            all(f in entry for f in ("author", "editor", "title", "booktitle"))
            and entry["author"] == entry["editor"]
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

        args.outfd.write(f"@{entry_type_copy}{{{entry['identifier']},\n")

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
                    assert isinstance(value, PubDate)  # for pyright
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
                if field in ("author", "editor", "translator"):
                    value = escape_latex(value, exclude=['{', '}'])
                elif field not in (
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
