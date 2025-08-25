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

# Import functions from map2bib.py
from thunderdell.map2bib import (
    get_identifier,
    parse_date,
    parse_names,
)
from thunderdell.utils.web import xml_escape

HOME = Path.home()


def bibtex_parse(text: str) -> dict[str, dict[str, str]]:
    """Parse bibtex entries using bibtexparser library."""
    import re

    # Add placeholder keys to entries missing them
    counter = 0

    def add_placeholder(match):
        nonlocal counter
        counter += 1
        placeholder = f"PLACEHOLDER_{counter}"
        logging.debug(f"Adding placeholder key: {placeholder}")
        return f"@{match.group(1)}{{{placeholder},\n"

    # Pattern: @type{ followed directly by a field (not a citation key)
    pattern = r"@(\w+)\s*\{\s*\n?\s*(?=[a-z]+\s*=)"
    text = re.sub(pattern, add_placeholder, text, flags=re.IGNORECASE)

    if counter > 0:
        logging.info(
            f"Added {counter} placeholder keys to entries missing citation keys"
        )

    # Configure parser
    parser = BibTexParser(common_strings=True)
    parser.ignore_nonstandard_types = False
    parser.homogenize_fields = False
    parser.customization = convert_to_unicode

    # Parse BibTeX
    try:
        bib_database = bibtexparser.loads(text, parser)
    except Exception as e:
        logging.error(f"bibtexparser failed: {e}")
        raise

    logging.info(f"Parsed {len(bib_database.entries)} BibTeX entries")

    # Convert to output format
    entries = {}
    for idx, entry in enumerate(bib_database.entries, 1):
        key = entry.pop("ID", f"temp_unnamed_{idx}")

        if "ID" in entry:
            print(f"key={key}")
            logging.debug(f"Found citation key: {key}")

        # Filter out ENTRYTYPE, keep all other fields
        entries[key] = {
            field: value for field, value in entry.items() if field != "ENTRYTYPE"
        }

        # Print fields
        for field, value in entries[key].items():
            print(f"{field:10}={value}")

    logging.info(f"Total entries created: {len(entries)}")
    if not entries:
        logging.error("No entries were parsed from the BibTeX file!")

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


def write_entry(fdo, key: str, entry: dict) -> None:
    """Write a single BibTeX entry to the mindmap file."""
    logging.debug(f"Writing entry with key: {key}")

    # Get author string
    if "author" in entry:
        if isinstance(entry["author"], str):
            author_str = format_authors(entry["author"])
        else:
            # Reconstruct from parsed tuples
            names = [
                " ".join(part for part in name_parts if part)
                for name_parts in entry["author"]
            ]
            author_str = " and ".join(names)
    else:
        author_str = "Unknown"

    # Write author node
    fdo.write(f'  <node COLOR="#338800" TEXT="{xml_escape(author_str)}">\n')

    # Write title node
    title = xml_escape(entry.get("title", "Unknown"))
    if "url" in entry:
        fdo.write(
            f'    <node COLOR="#090f6b" LINK="{xml_escape(entry["url"])}" '
            f'TEXT="{title}">\n'
        )
    else:
        fdo.write(f'    <node COLOR="#090f6b" TEXT="{title}">\n')

    # Write citation data
    cite = gather_citation_data(entry)
    cite_parts = [f"key={key}"] + [f"{abbrev}={value}" for abbrev, value in cite]
    cite_str = " ".join(cite_parts)
    fdo.write(f'      <node COLOR="#ff33b8" TEXT="{xml_escape(cite_str)}"/>\n')

    # Write abstract if available
    if "abstract" in entry:
        fdo.write(
            f'      <node COLOR="#999999" TEXT="&quot;{xml_escape(entry["abstract"])}&quot;"/>\n'
        )

    # Close nodes
    fdo.write("    </node>\n  </node>\n")


def prepare_date_for_entry(entry: dict) -> None:
    """Parse and set date field in entry from year/month fields."""
    from datetime import datetime

    if "year" in entry:
        year = entry["year"]
        month_str = entry.get("month", "")

        if month_str:
            # Try parsing month name to number
            for fmt in ["%B", "%b", "%m"]:  # Full name, abbrev, number
                try:
                    month_num = datetime.strptime(month_str, fmt).month
                    month = f"{month_num:02d}"
                    break
                except ValueError:
                    continue
            else:
                logging.warning(f"Invalid month format: {month_str}")
                month = ""
        else:
            month = ""

        date_str = f"{year}{month}" if month else year
        entry["date"] = parse_date(date_str)
    else:
        logging.warning("No year found, using default date 0000")
        entry["date"] = parse_date("0000")


def process(entries: dict, file_path: Path) -> None:
    """Convert bibtex entries to mindmap XML format and write to file."""
    logging.info(f"Processing {len(entries)} entries for file {file_path}")

    if not entries:
        logging.error("No entries to process!")
        return

    # Create a new dict with proper keys using get_identifier
    entries_with_keys = {}

    for temp_key, entry in entries.items():
        logging.debug(f"Processing entry with temp key: {temp_key}")

        try:
            # Parse author names if needed for get_identifier
            if "author" in entry and isinstance(entry["author"], str):
                logging.debug(f"Parsing author string: {entry['author']}")
                entry["author"] = parse_names(entry["author"])
                logging.debug(f"Parsed authors: {entry['author']}")
            elif "author" not in entry:
                logging.warning(f"No author found for {temp_key}, using default")
                entry["author"] = [("", "", "Unknown", "")]

            # Parse and set date field
            prepare_date_for_entry(entry)

            # Add required fields for get_identifier
            entry.setdefault("title", "Unknown")
            entry.setdefault("_mm_file", str(file_path))

            # Generate a proper identifier
            new_key = get_identifier(entry, entries_with_keys)
            entries_with_keys[new_key] = entry
            logging.info(f"Generated key '{new_key}' for entry (was '{temp_key}')")

        except Exception as e:
            logging.error(f"Error processing entry {temp_key}: {e}", exc_info=True)
            # Continue with next entry
            continue

    logging.info(f"Successfully processed {len(entries_with_keys)} entries")

    if not entries_with_keys:
        logging.error("No entries were successfully processed!")
        return

    try:
        with file_path.open("w") as fdo:
            # Write header
            fdo.write("""<map version="1.11.1">\n<node TEXT="Readings">\n""")
            logging.debug("Wrote mindmap header")

            # Process each entry with its generated key
            for key, entry in entries_with_keys.items():
                logging.info(f"Writing entry with key '{key}'")
                write_entry(fdo, key, entry)

            # Write footer
            fdo.write("""</node>\n</map>\n""")
            logging.debug("Wrote mindmap footer")

        logging.info(f"Successfully wrote mindmap to {file_path}")

    except Exception as e:
        logging.error(f"Error writing to file {file_path}: {e}", exc_info=True)
        raise


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

    # Setup logging
    log_level = logging.CRITICAL - (args.verbose * 10) if args.verbose else logging.INFO
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"

    logging.basicConfig(
        filename="extract-bibtex.log",
        filemode="w",
        level=log_level,
        format=LOG_FORMAT,
    )

    if args.log_to_file:
        print("Logging to file: extract_bibtex.log")

    logging.info(f"Starting extract_bibtex v{__version__}")

    for file_path in args.file_names:
        print(f"\nProcessing: {file_path}")

        try:
            bibtex_content = file_path.read_text(encoding="utf-8", errors="replace")
            file_out = file_path.with_suffix(".mm")

            entries = bibtex_parse(bibtex_content)
            if not entries:
                print(f"WARNING: No entries found in {file_path}")
                continue

            print(f"Found {len(entries)} entries")
            process(entries, file_out)

            if file_out.exists():
                print(f"✓ Created {file_out} ({file_out.stat().st_size} bytes)")
            else:
                print(f"ERROR: Failed to create {file_out}")

        except OSError as e:
            print(f"ERROR: {file_path} - {e}")
        except Exception as e:
            logging.error(f"Error processing {file_path}: {e}", exc_info=True)
            print(f"ERROR processing {file_path}: {e}")


if __name__ == "__main__":
    main()
