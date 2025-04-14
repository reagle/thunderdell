#!/usr/bin/env python3
"""Return bibliographic data for a given an ISBN."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import json
import logging as log
import pprint
import sys
from pathlib import Path
from typing import Any

import arrow
import requests

# Type alias for bibliography dictionary
BibDict = dict[str, Any]


def _normalize_isbn(isbn: str) -> str:
    """Remove 'isbn:' prefix and hyphens."""
    if isbn.lower().startswith("isbn:"):
        isbn = isbn[5:]
    return isbn.replace("-", "").strip()


def open_query(isbn: str, session: requests.Session) -> BibDict | None:
    """Query the Open Library Books API."""
    # https://openlibrary.org/dev/docs/api/books
    isbn_norm = _normalize_isbn(isbn)
    url = (
        f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn_norm}"
        "&jscmd=details&format=json"
    )
    log.info(f"Querying Open Library: {url}")
    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()  # Raise HTTPError for bad responses (4xx or 5xx)
    except requests.exceptions.RequestException as e:
        log.error(f"Open Library request failed for ISBN {isbn_norm}: {e}")
        return None

    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        log.warning(
            f"Open Library did not return JSON for ISBN {isbn_norm}. "
            f"Content-Type: {content_type}"
        )
        return None

    try:
        json_result = response.json()
    except json.JSONDecodeError as e:
        log.error(f"Failed to decode JSON from Open Library for ISBN {isbn_norm}: {e}")
        log.debug(f"Response content: {response.text}")
        return None

    if not json_result:  # Check for empty JSON response {}
        log.warning(f"Open Library returned empty result for ISBN {isbn_norm}")
        return None

    result_key = f"ISBN:{isbn_norm}"
    if result_key not in json_result:
        log.warning(f"ISBN {isbn_norm} not found in Open Library response.")
        return None

    json_vol = json_result[result_key]
    if "details" not in json_vol:
        log.warning(f"No 'details' found in Open Library response for ISBN {isbn_norm}")
        return None

    json_details = json_vol["details"]
    bib_entry: BibDict = {"isbn": isbn_norm}  # Start with normalized ISBN

    # Extract fields carefully
    if authors := json_details.get("authors"):
        bib_entry["author"] = ", ".join(
            author.get("name", "Unknown Author") for author in authors
        )
    elif by_statement := json_details.get("by_statement"):
        bib_entry["author"] = by_statement.strip().rstrip(".").strip()  # Clean up

    if publishers := json_details.get("publishers"):
        bib_entry["publisher"] = publishers[0]
    if places := json_details.get("publish_places"):
        bib_entry["address"] = places[0]

    if pub_date := json_details.get("publish_date"):
        try:
            # Attempt to parse various date formats flexibly
            bib_entry["date"] = arrow.get(pub_date).format("YYYYMMDD")
        except arrow.parser.ParserError:
            log.warning(
                f"Could not parse Open Library date '{pub_date}' for ISBN {isbn_norm}. "
                "Attempting year extraction."
            )
            # Fallback: try to extract just the year if parsing fails
            year_match = arrow.get(pub_date, ["YYYY", "YYYY-MM", "MM-YYYY"])
            if year_match:
                bib_entry["date"] = year_match.format("YYYY")
            else:
                log.error(f"Failed to extract year from '{pub_date}'")

    if title := json_details.get("title"):
        bib_entry["title"] = str(title).strip()  # Ensure string and strip

    # Combine title and subtitle if both exist
    if "title" in bib_entry and (subtitle := json_details.get("subtitle")):
        subtitle_str = str(subtitle).strip()
        bib_entry["title"] += f": {subtitle_str[:1].upper()}{subtitle_str[1:]}"

    # Add other string fields directly
    for key, value in json_details.items():
        if key not in bib_entry and isinstance(value, str):
            bib_entry[key] = value.strip()

    bib_entry["url"] = f"https://books.google.com/books?isbn={isbn_norm}"  # Default URL

    log.debug(f"Open Library result for {isbn_norm}: {bib_entry}")
    return bib_entry


def google_query(isbn: str, session: requests.Session) -> BibDict | None:
    """Query the Google Books API."""
    isbn_norm = _normalize_isbn(isbn)
    url = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn_norm}"
    log.info(f"Querying Google Books API: {url}")

    try:
        response = session.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        log.error(f"Google Books API request failed for ISBN {isbn_norm}: {e}")
        return None

    content_type = response.headers.get("content-type", "")
    if not content_type.startswith("application/json"):
        log.warning(
            f"Google Books API did not return JSON for ISBN {isbn_norm}. "
            f"Content-Type: {content_type}"
        )
        return None

    try:
        json_result = response.json()
    except json.JSONDecodeError as e:
        log.error(
            f"Failed to decode JSON from Google Books API for ISBN {isbn_norm}: {e}"
        )
        log.debug(f"Response content: {response.text}")
        return None

    if json_result.get("totalItems", 0) == 0 or not json_result.get("items"):
        log.warning(f"Google Books API found no items for ISBN {isbn_norm}")
        return None

    # Assume the first item is the best match
    json_vol_info = json_result["items"][0].get("volumeInfo", {})
    bib_entry: BibDict = {"isbn": isbn_norm}

    if authors := json_vol_info.get("authors"):
        bib_entry["author"] = ", ".join(authors)
    if pub_date := json_vol_info.get("publishedDate"):
        # Google dates are usually YYYY or YYYY-MM-DD
        try:
            arrow_date = arrow.get(pub_date)
            # Format based on precision
            if len(pub_date) == 4:  # YYYY
                bib_entry["date"] = arrow_date.format("YYYY")
            elif len(pub_date) == 7:  # YYYY-MM
                bib_entry["date"] = arrow_date.format("YYYYMM")
            else:  # Assume YYYY-MM-DD or similar
                bib_entry["date"] = arrow_date.format("YYYYMMDD")
        except arrow.parser.ParserError:
            log.warning(
                f"Could not parse Google date '{pub_date}' for ISBN {isbn_norm}. Storing as is."
            )
            bib_entry["date"] = pub_date  # Store raw if unparseable

    if title := json_vol_info.get("title"):
        bib_entry["title"] = str(title).strip()

    # Combine title and subtitle
    if "title" in bib_entry and (subtitle := json_vol_info.get("subtitle")):
        subtitle_str = str(subtitle).strip()
        bib_entry["title"] += f": {subtitle_str[:1].upper()}{subtitle_str[1:]}"

    # Add other relevant string fields
    for key in ["publisher", "description", "language"]:
        if (value := json_vol_info.get(key)) and isinstance(value, str):
            bib_entry[key] = value.strip()

    bib_entry["url"] = f"https://books.google.com/books?isbn={isbn_norm}"

    log.debug(f"Google Books API result for {isbn_norm}: {bib_entry}")
    return bib_entry


def query(isbn: str) -> BibDict:
    """Query available ISBN services and merge results."""
    log.info(f"Starting query for ISBN: {isbn}")
    bib: BibDict = {}
    bib_open = bib_google = None

    with requests.Session() as session:
        # Try Open Library first
        bib_open = open_query(isbn, session)

        # Try Google if Open Library failed or lacks author/title
        needs_google = not bib_open or not all(k in bib_open for k in ["author", "title"])
        if needs_google:
            log.info(f"Querying Google as Open Library result was insufficient for {isbn}")
            bib_google = google_query(isbn, session)

    if not bib_open and not bib_google:
        raise ValueError(f"All ISBN queries failed for {isbn}")

    # Merge results: Google data preferred for core fields if available,
    # then Open Library, ensuring essential fields are present.
    if bib_google:
        bib.update(bib_google)
    if bib_open:
        # Update with Open Library data only if the key doesn't exist from Google
        for key, value in bib_open.items():
            bib.setdefault(key, value)

    # Final check for essential fields
    if not all(k in bib for k in ["author", "title", "date", "isbn", "url"]):
        log.warning(f"Query result for {isbn} might be incomplete: {bib}")
        # Ensure defaults if absolutely necessary, though upstream should provide
        bib.setdefault("author", "Unknown Author")
        bib.setdefault("title", "Unknown Title")
        bib.setdefault("date", "Unknown Date")
        # isbn and url should always be set by the query functions

    log.info(f"Completed query for ISBN {isbn}")
    return bib


def process_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    arg_parser = argparse.ArgumentParser(
        description="Given one or more ISBNs, return bibliographic data."
    )
    arg_parser.add_argument(
        "isbns",
        metavar="ISBN",
        nargs="+",
        help="One or more ISBNs to query.",
    )
    # Optional arguments
    arg_parser.add_argument(
        "-s",
        "--style",
        help="Style of bibliography data (Currently unused, placeholder).",
    )
    arg_parser.add_argument(
        "-L",
        "--log-to-file",
        action="store_true",
        default=False,
        help="Log messages to %(prog)s.log instead of stderr.",
    )
    arg_parser.add_argument(
        "-V",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (-V: INFO, -VV: DEBUG).",
    )
    arg_parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    args = arg_parser.parse_args(argv)

    # Configure logging
    log_level = log.WARNING  # Default
    if args.verbose == 1:
        log_level = log.INFO
    elif args.verbose >= 2:
        log_level = log.DEBUG

    log_format = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    log_file = Path(sys.argv[0]).stem + ".log" if args.log_to_file else None
    log_mode = "w"

    # Use basicConfig with stream for stderr or filename for file
    if log_file:
        log.basicConfig(
            filename=log_file, filemode=log_mode, level=log_level, format=log_format
        )
    else:
        log.basicConfig(stream=sys.stderr, level=log_level, format=log_format)

    # Configure requests logging level based on verbosity
    log.getLogger("requests").setLevel(log.WARNING if args.verbose < 2 else log.DEBUG)
    log.getLogger("urllib3").setLevel(log.WARNING if args.verbose < 2 else log.DEBUG)

    log.debug(f"Log level set to: {log.getLevelName(log_level)}")
    log.debug(f"Parsed arguments: {args}")

    return args


def main(args: argparse.Namespace | None = None) -> None:
    """Parse arguments, setup logging, and run."""
    if args is None:
        args = process_arguments(sys.argv[1:])

    results = {}
    # Use a session for potential connection reuse
    with requests.Session() as session:
        # Set a user-agent
        session.headers.update(
            {"User-Agent": f"thunderdell/{__version__} (Python-requests)"}
        )

        for isbn_input in args.isbns:
            try:
                result = query(isbn_input, session)
                results[isbn_input] = result
                log.info(f"Successfully retrieved data for ISBN: {isbn_input}")
                print(f"ISBN: {isbn_input} | Result: {result}")
            except ValueError as e:
                log.error(f"Query failed for ISBN {isbn_input}: {e}")
                results[isbn_input] = {"error": str(e)}
                print(f"ISBN: {isbn_input} | Error: {e}")
            except Exception as e:
                log.exception(
                    f"An unexpected error occurred for ISBN {isbn_input}: {e}"
                )
                results[isbn_input] = {"error": f"Unexpected error: {e}"}
                print(f"ISBN: {isbn_input} | Unexpected Error: {e}")

    log.info("ISBN query process finished.")


if __name__ == "__main__":
    main(sys.argv[1:])
