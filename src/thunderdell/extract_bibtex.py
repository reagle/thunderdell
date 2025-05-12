#!/usr/bin/env python3
"""Convert a bibtex file into a mindmap."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2025 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.5"

import argparse
import logging
import sys
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html

import bibtexparser
from bibtexparser.bparser import BibTexParser
from bibtexparser.customization import convert_to_unicode

from thunderdell.utils.web import xml_escape

HOME = Path.home()


def bibtex_parse(text: list[str]) -> dict[str, dict[str, str]]:
    """Parse bibtex entries using bibtexparser library.

    >>> bibtex_eg = [
    ...     '@Article{Smith2023,',
    ...     '    author = "John Smith",',
    ...     '    title = "Example Title",',
    ...     '    journal = "Journal of Examples",',
    ...     '    year = "2023",',
    ...     '}',
    ... ]
    >>> bibtex_parse(bibtex_eg)
    key=Smith2023
    year      =2023
    journal   =Journal of Examples
    title     =Example Title
    author    =John Smith
    {'Smith2023': {'year': '2023', 'journal': 'Journal of Examples', 'title': 'Example Title', 'author': 'John Smith'}}
    """
    parser = BibTexParser()
    parser.customization = convert_to_unicode
    parser.ignore_nonstandard_types = False
    # Parse the BibTeX string
    bib_database = bibtexparser.loads("".join(text), parser)
    # Convert the parsed entries to the desired output format
    entries = {}
    for entry in bib_database.entries:
        key = entry.pop("ID")  # Extract the citation key
        print(f"key={key}")
        entries[key] = {}
        for field, value in entry.items():
            if field != "ENTRYTYPE":  # Skip the entry type field
                print(f"{field:10}={value}")
                entries[key][field] = value
    return entries


def format_authors(author_string: str) -> str:
    """Format authors from BibTeX format to desired output format.

    Handles both "LastName, FirstName" and "FirstName LastName" formats.

    >>> format_authors("Smith, John")
    'John Smith'
    >>> format_authors("John Smith")
    'John Smith'
    >>> format_authors("Smith, John and Doe, Jane")
    'John Smith and Jane Doe'
    >>> format_authors("John Smith and Jane Doe")
    'John Smith and Jane Doe'
    """
    authors = []

    # Split multiple authors (delimited by " and ")
    for name in author_string.split(" and "):
        name = name.strip()

        # Check if name is in "LastName, FirstName" format
        if ", " in name:
            last, first = name.split(", ", 1)
            authors.append(f"{first} {last}")
        else:
            # Name is already in "FirstName LastName" format
            authors.append(name)

    # Join authors with " and "
    return " and ".join(authors)


def gather_citation_data(entry: dict) -> list[tuple[str, str]]:
    """Extract and format citation data from a BibTeX entry.

    >>> gather_citation_data({"year": "2023", "journal": "Nature"})
    [('y', '2023'), ('j', 'Nature')]
    """
    # Field mapping with desired order
    # I could import from elsewhere but I want this ordering
    field_mapping = [
        ("year", "y"),
        ("month", "m"),
        ("booktitle", "bt"),
        ("editor", "e"),
        ("publisher", "p"),
        ("address", "a"),
        ("edition", "ed"),
        ("chapter", "ch"),
        ("pages", "pp"),
        ("journal", "j"),
        ("volume", "v"),
        ("number", "n"),
        ("doi", "doi"),
        ("annote", "an"),
        ("note", "nt"),
    ]

    cite = []
    for field, abbrev in field_mapping:
        if field in entry:
            value = entry[field]
            # Special handling for pages
            if field == "pages":
                value = value.replace("--", "-").replace(" ", "")
            cite.append((abbrev, value))

    return cite


def write_entry(fdo, entry: dict) -> None:
    """Write a single BibTeX entry to the mindmap file."""
    # Write author node
    author_str = format_authors(entry["author"])
    fdo.write(f"""  <node COLOR="#338800" TEXT="{author_str}">\n""")

    # Write title node with URL if available
    if "url" in entry:
        fdo.write(
            f"""    <node COLOR="#090f6b" LINK="{xml_escape(entry["url"])}" """
            f"""TEXT="{xml_escape(entry["title"])}">\n"""
        )
    else:
        fdo.write(
            f"""    <node COLOR="#090f6b" TEXT="{xml_escape(entry["title"])}">\n"""
        )

    # Write citation data
    cite = gather_citation_data(entry)
    cite_str = " ".join([f"{abbrev}={value}" for abbrev, value in cite])
    fdo.write(f"""      <node COLOR="#ff33b8" TEXT="{xml_escape(cite_str)}"/>\n""")

    # Write abstract if available
    if "abstract" in entry:
        fdo.write(
            f"""      <node COLOR="#999999" TEXT="&quot;{xml_escape(entry["abstract"])}&quot;"/>\n"""
        )

    # Close nodes
    fdo.write("""    </node>\n  </node>\n""")


def process(entries: dict, file_path: Path) -> None:
    """Convert bibtex entries to mindmap XML format and write to file."""
    with file_path.open("w") as fdo:
        # Write header
        fdo.write("""<map version="1.11.1">\n<node TEXT="Readings">\n""")

        # Process each entry
        for entry in entries.values():
            logging.info(f"entry = '{entry}'")
            write_entry(fdo, entry)

        # Write footer
        fdo.write("""</node>\n</map>\n""")


def process_arguments(args) -> argparse.Namespace:
    """Parse command line arguments."""
    arg_parser = argparse.ArgumentParser(
        description="Converts bibtex files to mindmap."
    )

    # positional arguments
    arg_parser.add_argument("file_names", nargs="*", type=Path, metavar="FILE_NAMES")
    # optional arguments
    arg_parser.add_argument(
        "-L",
        "--log-to-file",
        action="store_true",
        default=False,
        help="log to file %(prog)s.log",
    )
    arg_parser.add_argument(
        "-V",
        "--verbose",
        action="count",
        default=0,
        help="increase verbosity from critical though error, warning, info, and debug",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__} using Python {sys.version}",
    )
    return arg_parser.parse_args(args)


def main(args: argparse.Namespace | None = None):
    """Parse arguments, setup logging, and process bibtex files."""
    if args is None:
        args = process_arguments(sys.argv[1:])

    log_level = (logging.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    if args.log_to_file:
        logging.basicConfig(
            filename="extract_bibtex.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    for file_path in args.file_names:
        try:
            bibtex_content = file_path.read_text(encoding="utf-8", errors="replace")
            file_out = file_path.with_suffix(".mm")
        except OSError:
            print(f"{file_path=} does not exist")
            continue
        entries = bibtex_parse(bibtex_content.split("\n"))
        process(entries, file_out)


if __name__ == "__main__":
    main()
