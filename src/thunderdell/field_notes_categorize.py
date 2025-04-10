#!/usr/bin/env python3
"""Create a categorized mindmap based on the first `kw=` declaration in each source."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import logging as log
import re
import sys
from collections import defaultdict
from pathlib import Path

import lxml.etree as et

# Define a type alias for clarity
NodeList = list[et._Element]


def extract_first_keyword(node_text: str) -> str | None:
    """Extract the first 'kw=<value>' from the node text."""
    if "kw=" not in node_text:
        return None
    try:
        # Find all 'kw=<non-space-chars>' occurrences, case-insensitive
        matches = re.findall(r"kw=(\S+)", node_text, re.IGNORECASE)
        if matches:
            return matches[0]  # Return the value part of the first match
    except IndexError:
        # This should theoretically not happen with the 'kw=' check, but safety first
        log.warning(f"Regex found 'kw=' but failed to extract value from: {node_text}")
    return None


def categorize_mindmap(old_fn: Path) -> None:
    """Create a categorized mindmap based on the first `kw=` declaration."""
    log.info(f"Processing mindmap file: {old_fn}")
    cat_fn = old_fn.with_stem(old_fn.stem + "-cat").with_suffix(".mm")
    log.info(f"Output categorized mindmap will be: {cat_fn}")

    try:
        old_doc = et.parse(old_fn)
    except et.XMLSyntaxError as e:
        log.error(f"Failed to parse XML file {old_fn}: {e}")
        return
    except FileNotFoundError:
        log.error(f"Input mindmap file not found: {old_fn}")
        return
    except Exception as e:
        log.exception(f"An unexpected error occurred while parsing {old_fn}: {e}")
        return

    old_map = old_doc.getroot()

    # Use defaultdict for cleaner grouping
    categorized_nodes = defaultdict(list)

    # Iterate through all nodes to find 'cite' nodes
    for node in old_map.iterfind(".//node[@STYLE_REF='cite']"):
        keyword = "UNLABELLED"  # Default category
        node_text = node.get("TEXT", "")

        if extracted_kw := extract_first_keyword(node_text):
            keyword = extracted_kw
        else:
            log.warning(f"No 'kw=' found or extracted for node: {node_text[:50]}...")

        # Navigate up to the ancestor 'author' node (assuming structure: author > title > cite)
        title_node = node.getparent()
        if title_node is None:
            log.warning(
                f"Parent (title) node missing for cite node: {node_text[:50]}..."
            )
            continue
        author_node = title_node.getparent()
        if author_node is None:
            log.warning(
                f"Grandparent (author) node missing for cite node: {node_text[:50]}..."
            )
            continue

        log.debug(
            f"Assigning node (author: {author_node.get('TEXT', '')[:30]}...) to category: {keyword}"
        )
        categorized_nodes[keyword].append(author_node)

    if not categorized_nodes:
        log.warning(
            f"No cite nodes found or processed in {old_fn}. No output generated."
        )
        return

    # Create the new mindmap structure
    new_map = et.Element(
        "map", version="freeplane 1.12.1"
    )  # Consider updating version if needed
    new_doc = et.ElementTree(new_map)
    # Use the output filename as the root node text
    root_node = et.SubElement(new_map, "node", TEXT=str(cat_fn.name))

    # Sort categories alphabetically (case-insensitive) and add nodes
    # Use tuple for case-insensitive sort key
    for keyword, node_list in sorted(
        categorized_nodes.items(), key=lambda item: item[0].lower()
    ):
        log.debug(f"Adding category '{keyword}' with {len(node_list)} nodes.")
        cat_node = et.SubElement(root_node, "node", TEXT=keyword)
        # Add all author nodes belonging to this category
        cat_node.extend(node_list)

    # Write the new mindmap file
    try:
        # Use pretty_print for readability
        new_doc.write(
            str(cat_fn), encoding="utf-8", xml_declaration=True, pretty_print=True
        )
        log.info(f"Successfully created categorized mindmap: {cat_fn}")
    except OSError as e:
        log.error(f"Failed to write output file {cat_fn}: {e}")
    except Exception as e:
        log.exception(f"An unexpected error occurred while writing {cat_fn}: {e}")


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    arg_parser = argparse.ArgumentParser(
        description=(
            "Create a categorized mindmap based on the first `kw=` "
            "declaration in each source's cite node."
        ),
        formatter_class=argparse.RawTextHelpFormatter,
    )
    arg_parser.add_argument(
        "filename",
        metavar="FILENAME",
        type=Path,
        help="Mindmap (.mm) file to process.",
    )
    # Optional arguments for logging
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

    args = arg_parser.parse_args(argv)  # Use provided argv or sys.argv[1:]

    # Configure logging
    log_level = log.WARNING  # Default
    if args.verbose == 1:
        log_level = log.INFO
    elif args.verbose >= 2:
        log_level = log.DEBUG

    log_format = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    log_file = Path(sys.argv[0]).stem + ".log" if args.log_to_file else None
    log_mode = (
        "w" if args.log_to_file else None
    )  # Overwrite log file if logging to file

    # Use basicConfig with stream for stderr or filename for file
    if log_file:
        log.basicConfig(
            filename=log_file, filemode=log_mode, level=log_level, format=log_format
        )
    else:
        log.basicConfig(stream=sys.stderr, level=log_level, format=log_format)

    log.debug(f"Log level set to: {log.getLevelName(log_level)}")
    log.debug(f"Parsed arguments: {args}")

    return args


def main(argv: list[str] | None = None) -> None:
    """Parse arguments and run the categorization."""
    args = parse_arguments(argv)
    if not args.filename.is_file():
        log.error(f"Input file not found or is not a file: {args.filename}")
        sys.exit(1)  # Exit if the input file doesn't exist

    categorize_mindmap(args.filename)
    log.info("Categorization process finished.")


if __name__ == "__main__":
    # Pass command line arguments (excluding script name) to main
    main()
