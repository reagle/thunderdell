#!/usr/bin/env python3
"""Process raindrop.io export into format accepted by `extract_dictation.py`."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

# TODO: 2024-10-18 : add DOI ability since some papers are web pages

import argparse
import logging
import re
import sys
import webbrowser
from pathlib import Path

from send2trash import send2trash  # type: ignore

from thunderdell import busy

HOME = Path.home()
URL_RE = re.compile(r"https?://\S+")


def process_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    arg_parser = argparse.ArgumentParser(
        description="""Format raindrop.io annotations for use with
        extract_dictation.py in https://github.com/reagle/thunderdell
        """,
        formatter_class=argparse.RawTextHelpFormatter,
    )
    arg_parser.add_argument(
        "-p",
        "--publish",
        action="store_true",
        default=False,
        help="Publish to social networks (can also `-p` in editor).",
    )

    # positional arguments
    arg_parser.add_argument(
        "file_names",
        nargs="+",
        type=Path,
        metavar="FILE_NAMES",
        help="One or more raindrop.io export files to process.",
    )
    # optional arguments
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
        help="Increase verbosity (can be used multiple times). -V for WARNING, -VV for INFO, -VVV for DEBUG.",
    )
    arg_parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )
    args = arg_parser.parse_args(argv)  # Use provided argv or sys.argv[1:]

    # Configure logging
    log_level = max(
        logging.CRITICAL - (args.verbose * 10), logging.DEBUG
    )  # Default: CRITICAL
    log_format = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    log_file = Path(sys.argv[0]).stem + ".log" if args.log_to_file else None
    log_mode = (
        "w" if args.log_to_file else None
    )  # Overwrite log file if logging to file

    # Use basicConfig with stream for stderr or filename for file
    if log_file:
        logging.basicConfig(
            filename=log_file, filemode=log_mode, level=log_level, format=log_format
        )
    else:
        logging.basicConfig(stream=sys.stderr, level=log_level, format=log_format)

    logging.debug(f"Log level set to: {logging.getLevelName(log_level)}")
    logging.debug(f"Parsed arguments: {args}")

    return args


def process_single_file(args: argparse.Namespace, file_path: Path) -> None:
    """Process a single file for highlights and annotations."""
    logging.info(f"Processing file: {file_path}")
    url = ""
    comment_lines: list[str] = [""]  # Start with an empty line for potential summary

    try:
        file_content = file_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        logging.error(f"File not found: {file_path}. Skipping.")
        return
    except Exception as e:
        logging.exception(f"Error reading file {file_path}: {e}")
        return

    # First pass: find the URL
    for line in file_content.splitlines():
        if match := URL_RE.search(line):
            url = match.group()
            logging.info(f"URL found: {url}")
            break  # Stop after finding the first URL
    else:
        logging.warning(f"No URL found in {file_path}. Skipping processing logic.")
        return  # Cannot proceed without a URL

    # Second pass: process lines for comments/excerpts
    for line in file_content.splitlines():
        line = line.strip()
        if not line or URL_RE.search(
            line
        ):  # Skip empty lines and lines containing the URL
            continue

        # Lines starting with "- " are treated as excerpts
        if line.startswith("- "):
            comment_lines.append(line[2:].strip())
        # Other non-empty lines are treated as annotations, marked with ", "
        else:
            comment_lines.append(f", {line}")

    text = "\n".join(comment_lines)
    logging.debug(f"Generated comment text:\n{text}")

    # Open URL in browser and process with busy.py logic
    try:
        webbrowser.open(url)
        logging.info(f"Opened URL in browser: {url}")
        # Assuming busy.get_scraper and log2mm handle their own errors/logging
        scraper = busy.get_scraper(url, text)  # Pass URL and formatted text
        biblio = scraper.get_biblio()
        biblio["tags"] = "misc"  # default keyword
        if "excerpt" in biblio:
            del biblio["excerpt"]  # remove auto excerpt if present
        busy.log2mm(args, biblio)  # Pass args for potential publish flag etc.
        logging.info(f"Successfully processed and logged to mindmap for {url}")
    except Exception as e:
        logging.exception(f"Error during scraping or mindmap logging for {url}: {e}")


def main(args: argparse.Namespace | None = None) -> None:
    """Parse arguments, setup logging, and run."""
    if args is None:
        args = process_arguments(sys.argv[1:])

    logging.info("==================================")
    logging.info(f"Starting processing with args: {args}")

    files_to_process = args.file_names
    for file_path in files_to_process:
        process_single_file(args, file_path)

    # Ask user about trashing processed files *after* all files are processed
    try:
        user_input = input(
            f"\nTrash processed file(s) ({len(files_to_process)} files)? [y/N]: "
        ).lower()
        if user_input == "y":
            logging.info(
                f"Sending {len(files_to_process)} file(s) to trash: {files_to_process}"
            )
            send2trash(files_to_process)
            logging.info("File(s) sent to trash.")
        else:
            logging.info("Files were not sent to trash.")
    except Exception as e:
        logging.exception(f"Error during file trashing operation: {e}")

    logging.info("Processing finished.")


if __name__ == "__main__":
    main()
