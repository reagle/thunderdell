#!/usr/bin/env python3
"""Extract a mindmap from a dictated text file using ad-hoc conventions."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import logging as log
import re
import subprocess
import sys
import time
from pathlib import Path
from typing import Any, TextIO

from thunderdell.biblio.fields import (
    BIB_FIELDS,  # dict of field to its shortcut
    BIB_SHORTCUTS,  # dict of shortcuts to a field
)
from thunderdell.utils.web import yasn_publish

HOME = Path.home()

# Type aliases for improved readability
EntryDict = dict[str, Any]
MindmapState = tuple[bool, bool, bool, bool, bool]


MINDMAP_PREAMBLE = """<map version="freeplane 1.5.9">
    <node TEXT="reading" FOLDED="false" ID="ID_327818409">
        <font SIZE="18"/>
        <hook NAME="MapStyle">
            <map_styles>
                <stylenode LOCALIZED_TEXT="styles.root_node" STYLE="oval"
                 UNIFORM_SHAPE="true" VGAP_QUANTITY="24.0 pt">
                    <font SIZE="24"/>
                    <stylenode LOCALIZED_TEXT="styles.user-defined"
                     POSITION="right" STYLE="bubble">
                        <stylenode TEXT="author" COLOR="#338800"/>
                        <stylenode TEXT="title" COLOR="#090f6b"/>
                        <stylenode TEXT="cite" COLOR="#ff33b8"/>
                        <stylenode TEXT="annotation" COLOR="#999999"/>
                        <stylenode TEXT="quote" COLOR="#166799"/>
                        <stylenode TEXT="paraphrase" COLOR="#8b12d6"/>
                    </stylenode>
                </stylenode>
            </map_styles>
        </hook>
"""


def clean(text: str) -> str:
    """Clean and encode text for XML.

    >>> clean('Test & "quotes"')
    'Test &amp; &quot;quotes&quot;'
    >>> clean('Test – dash')
    'Test -- dash'
    """
    text = text.strip(", \f\r\n")
    replacements = [
        ("&", "&amp;"),
        ("\N{APOSTROPHE}", "&apos;"),
        ("\N{QUOTATION MARK}", "&quot;"),
        ("\N{LEFT DOUBLE QUOTATION MARK}", "&quot;"),
        ("\N{RIGHT DOUBLE QUOTATION MARK}", "&quot;"),
        ("\N{LEFT SINGLE QUOTATION MARK}", "\N{APOSTROPHE}"),
        ("\N{RIGHT SINGLE QUOTATION MARK}", "\N{APOSTROPHE}"),
        (" \N{EN DASH} ", " -- "),
        ("\N{EN DASH}", " -- "),
    ]
    for old, new in replacements:
        text = text.replace(old, new)
    return text


def get_date() -> str:
    """Return the current date as a string in YYYYMMDD format."""
    return time.strftime("%Y%m%d")


def close_sections(
    mm_fd: TextIO,
    close_subsection: bool = False,
    close_section: bool = False,
    close_chapter: bool = False,
    close_part: bool = False,
) -> None:
    """Close open section nodes in the mindmap."""
    if close_subsection:
        mm_fd.write("        </node>\n")
    if close_section:
        mm_fd.write("      </node>\n")
    if close_chapter:
        mm_fd.write("    </node>\n")
    if close_part:
        mm_fd.write("  </node>\n")


def parse_citation_pairs(line: str) -> list[tuple[str, str]]:
    """Parse citation key-value pairs from a line."""
    # Split by "key =", keeping delimiters; filter out empty strings
    parts = [p.strip() for p in re.split(r"(\w+\s*=)", line) if p]
    # Group keys and values
    return [(parts[i].replace("=", "").strip(), parts[i + 1]) for i in range(0, len(parts), 2)]


def update_entry_with_citations(
    entry: EntryDict, cite_pairs: list[tuple[str, str]]
) -> EntryDict:
    """Update entry dictionary with citation information."""
    for token, value in cite_pairs:
        log.info(f"{token=}, {value=}")
        token_lower = token.lower()
        match token_lower:
            case "keyword":
                if isinstance(entry.get("keyword"), list):
                    entry["keyword"].append(value)
                else:
                    entry["keyword"] = [value]
            case "subtitle":
                # Handle subtitle merging later
                entry[token_lower] = value
            case _:
                entry[token_lower] = value

    # Ensure required fields exist
    entry.setdefault("author", "Unknown")
    entry.setdefault("title", "Untitled")

    # Process subtitle
    if subtitle := entry.pop("subtitle", None):
        entry["title"] = f"{entry['title']}: {subtitle}"

    return entry


def build_citation_text(entry: EntryDict) -> str:
    """Build citation text from entry dictionary."""
    citation_parts = []

    for token, value in sorted(entry.items()):
        if token not in ("author", "title", "url", "keyword", "summary"):
            value_str = str(value)
            token_lower = token.lower()
            if token_lower in BIB_SHORTCUTS:
                t, v = token_lower, value_str
            elif token_lower in BIB_FIELDS:
                t, v = BIB_FIELDS[token_lower], value_str
            else:
                # Log or handle unknown tokens if necessary, but don't raise error here
                log.warning(f"Token '{token}' not in BIB_FIELDS or BIB_SHORTCUTS")
                continue  # Skip unknown tokens for citation string
            citation_parts.append(f"{t}={v}")
        elif token == "keyword" and isinstance(value, list):
            citation_parts.extend([f"kw={kw!s}" for kw in value])

    citation = " ".join(citation_parts)
    citation += f" r={get_date()}"
    return citation


def process_author_line(
    mm_fd: TextIO, line: str, entry: EntryDict, state: MindmapState
) -> tuple[EntryDict, MindmapState]:
    """Process an author line and update entry data."""
    started, in_part, in_chapter, in_section, in_subsection = state

    # Close previous entry if needed
    if started:
        close_sections(mm_fd, in_subsection, in_section, in_chapter, in_part)
        mm_fd.write("</node>\n</node>\n")
        # Reset state for the new entry
        started = in_part = in_chapter = in_section = in_subsection = False
        entry = {"keyword": []}  # Reset entry for the new citation block

    started = True

    # Parse and process citation data
    cite_pairs = parse_citation_pairs(line)
    entry = update_entry_with_citations(entry, cite_pairs)

    # Ensure values are strings for XML writing
    author = str(entry["author"])
    title = str(entry["title"])

    # Write author node
    mm_fd.write(
        f"""<node STYLE_REF="author" TEXT="{clean(author.title())}" POSITION="RIGHT">\n"""
    )

    # Write title node with optional hyperlink
    if url := entry.get("url"):
        mm_fd.write(
            f"""  <node STYLE_REF="title" LINK="{clean(str(url))}" TEXT="{clean(title)}">\n"""
        )
    else:
        mm_fd.write(f"""  <node STYLE_REF="title" TEXT="{clean(title)}">\n""")

    # Add citation node
    citation = build_citation_text(entry)
    mm_fd.write(f"""  <node STYLE_REF="cite" TEXT="{clean(citation)}"/>\n""")

    return entry, (started, in_part, in_chapter, in_section, in_subsection)


def process_structure_element(
    mm_fd: TextIO, element_type: str, content: str, state: MindmapState
) -> MindmapState:
    """Process structural elements (part, chapter, section, subsection)."""
    started, in_part, in_chapter, in_section, in_subsection = state
    content = content.strip() # Clean content whitespace

    match element_type.lower():
        case "part":
            if in_part:
                close_sections(mm_fd, in_subsection, in_section, in_chapter, True)
                in_subsection = in_section = in_chapter = False
            full_content = f"part {content}" if content else "part"
            mm_fd.write(
                f"""  <node STYLE_REF="quote" TEXT="{clean(full_content)}">\n"""
            )
            in_part = True
            # Reset lower levels as we start a new part
            in_chapter = in_section = in_subsection = False

        case "chapter":
            if in_chapter:
                close_sections(mm_fd, in_subsection, in_section, True, False)
                in_subsection = in_section = False
            full_content = f"chapter {content}" if content else "chapter"
            mm_fd.write(
                f"""    <node STYLE_REF="quote" TEXT="{clean(full_content)}">\n"""
            )
            in_chapter = True
            # Reset lower levels as we start a new chapter
            in_section = in_subsection = False

        case "section":
            if in_subsection:
                close_sections(mm_fd, True, False, False, False)
            if in_section:
                close_sections(mm_fd, False, True, False, False)
            full_content = f"section {content}" if content else "section"
            mm_fd.write(f"""      <node STYLE_REF="quote" TEXT="{clean(full_content)}">\n""")
            in_section = True
            # Reset lower level as we start a new section
            in_subsection = False

        case "subsection":
            if in_subsection:
                close_sections(mm_fd, True, False, False, False)
            full_content = f"subsection {content}" if content else "subsection"
            mm_fd.write(
                f"""        <node STYLE_REF="quote" TEXT="{clean(full_content)}">\n"""
            )
            in_subsection = True

    return started, in_part, in_chapter, in_section, in_subsection


def process_content_line(mm_fd: TextIO, line: str) -> None:
    """Process general content lines."""
    node_color = "paraphrase"
    line_text = line
    line_no = ""

    # Process page numbers (improved regex)
    page_pattern = r"^([\dcdilmxv]+(?:-[\dcdilmxv]+)?)\s+(.*?)(?:-([\dcdilmxv]+))?$"
    if match := re.match(page_pattern, line, re.I):
        line_no = match.group(1)
        if end_range := match.group(3): # Handle optional end range like '1-2' or '1-x'
             line_no += f"-{end_range}"
        line_no = line_no.lower()  # lower case roman numbers
        line_text = match.group(2).strip() # Content is group 2

    # Process excerpts (case-insensitive and flexible position)
    if line_text.lower().startswith("excerpt."):
        node_color = "quote"
        line_text = line_text[len("excerpt.") :].lstrip()
    elif line_text.lower().endswith(".excerpt"):
        node_color = "quote"
        line_text = line_text[: -len(".excerpt")].rstrip()

    text_content = f"{line_no} {line_text}".strip()
    mm_fd.write(
        f"""          <node STYLE_REF="{node_color}" TEXT="{clean(text_content)}"/>\n"""
    )


def build_mm_from_txt(
    mm_fd: TextIO,
    line: str,
    state: MindmapState,
    entry: EntryDict,
) -> tuple[MindmapState, EntryDict]:
    """Build a mindmap from a single line of text."""
    if not line or line in ("\r", "\n"):
        return state, entry

    started, in_part, in_chapter, in_section, in_subsection = state
    new_state = state
    new_entry = entry

    # Process line based on content type (case-insensitive checks)
    line_lower = line.lower()
    if line_lower.startswith("author ="):
        new_entry, new_state = process_author_line(mm_fd, line, entry, state)

    elif match := re.match(r"summary\.(.*)", line, re.I):
        summary_text = match.group(1).strip()
        entry["summary"] = summary_text
        mm_fd.write(
            f"""  <node STYLE_REF="annotation" TEXT="{clean(summary_text)}"/>\n"""
        )

    elif match := re.match(r"(part|chapter|section|subsection)(.*)", line, re.I):
        element_type, content = match.groups()
        new_state = process_structure_element(mm_fd, element_type, content, state)

    elif line.startswith("--"): # Treat as a literal separator/note
        mm_fd.write(f"""          <node STYLE_REF="default" TEXT="{clean(line)}"/>\n""")

    else: # Default case: process as content (page number, excerpt, paraphrase)
        # Ensure content is placed within the current structure level
        indent = "  " * (2 + sum([in_part, in_chapter, in_section, in_subsection]))
        # Temporarily adjust process_content_line or add logic here if needed
        # to handle indentation based on state. For now, assuming it writes
        # at the deepest level. A better approach might be to pass indent level.
        # Let's assume process_content_line writes at a fixed indent for now.
        # A better refactor would adjust indentation based on state.
        # For now, we'll keep the original fixed indent in process_content_line.
        process_content_line(mm_fd, line)


    return new_state, new_entry


def create_mm(args: argparse.Namespace, text: str, mm_file_name: Path) -> None:
    """Create a mindmap file from the given text."""
    with mm_file_name.open("w", encoding="utf-8", errors="replace") as mm_fd:
        entry: EntryDict = {"keyword": []}

        # Initialize state variables
        state: MindmapState = (False, False, False, False, False) # started, part, chapter, section, subsection

        mm_fd.write(f'{MINDMAP_PREAMBLE}\n<node TEXT="Readings">\n')

        current_entry: EntryDict = {"keyword": []} # Holds data for the current citation block

        try:
            for line_number, line in enumerate(text.split("\n")):
                if processed_line := line.strip():
                    state, current_entry = build_mm_from_txt(
                        mm_fd,
                        processed_line,
                        state,
                        current_entry,
                    )
        except (ValueError, KeyError, IndexError, TypeError) as err:
            import traceback
            print(f"Error processing line {line_number+1}: '{line}'")
            print(f"Current state: {state}")
            print(f"Current entry: {current_entry}")
            print(f"Error: {err}")
            print(traceback.format_exc())
            sys.exit(1)
        except FileNotFoundError as err:
            print(f"File not found error: {err}")
            sys.exit(1)
        except PermissionError as err:
            print(f"Permission error: {err}")
            sys.exit(1)

        # Unpack final state
        started, in_part, in_chapter, in_section, in_subsection = state

        # Close any open section nodes at the end of the file
        if started: # Ensure the last entry's nodes are closed
             close_sections(mm_fd, in_subsection, in_section, in_chapter, in_part)
             mm_fd.write("</node>\n</node>\n") # Close title and author nodes

        # Close document structure
        mm_fd.write("</node>\n") # Close "Readings" node
        mm_fd.write("</node>\n</map>\n") # Close root node and map

        log.info(f"Final entry state before potential publish: {current_entry=}")
        # Publish if requested and required fields are present in the *last* entry processed
        if args.publish and all(k in current_entry for k in ["summary", "title", "url"]):
            summary = str(current_entry.get("summary", ""))
            title = str(current_entry.get("title", ""))
            url = str(current_entry.get("url", ""))
            keywords = current_entry.get("keyword", [])
            keyword_str = " ".join(map(str, keywords)) if isinstance(keywords, list) else str(keywords)

            yasn_publish(
                summary,
                title,
                "",  # Empty string for subtitle
                url,
                keyword_str,
            )


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command line arguments."""
    arg_parser = argparse.ArgumentParser(
        description="""Convert dictated notes to mindmap.

        `author` must be first in citation pairs, e.g., "author = ...
        """,
        formatter_class=argparse.RawTextHelpFormatter,
    )

    # positional arguments
    arg_parser.add_argument("file_names", nargs="+", type=Path, metavar="FILE_NAMES",
                            help="One or more text files to process.")

    # optional arguments
    arg_parser.add_argument(
        "-p",
        "--publish",
        action="store_true",
        default=False,
        help="Publish the last entry's summary/title/URL to social networks (via yasn).",
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
        help="Increase verbosity (can be used multiple times). -V for WARNING, -VV for INFO, -VVV for DEBUG.",
    )
    arg_parser.add_argument(
        "--version", action="version", version=f"%(prog)s {__version__}"
    )

    # Parse arguments
    args = arg_parser.parse_args(argv) # Use provided argv or sys.argv[1:]

    # Configure logging based on verbosity
    log_level = max(log.CRITICAL - (args.verbose * 10), log.DEBUG) # Default: CRITICAL
    log_format = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    log_file = Path(sys.argv[0]).stem + ".log" if args.log_to_file else None
    log_mode = "w" if args.log_to_file else None # Overwrite log file if logging to file

    # Use basicConfig with stream for stderr or filename for file
    if log_file:
        log.basicConfig(filename=log_file, filemode=log_mode, level=log_level, format=log_format)
    else:
        log.basicConfig(stream=sys.stderr, level=log_level, format=log_format)


    log.debug(f"Log level set to: {log.getLevelName(log_level)}")
    log.debug(f"Parsed arguments: {args}")

    return args


def main(argv: list[str] | None = None) -> None:
    """Process dictation files and convert to mindmaps."""
    args = parse_arguments(argv)

    log.info(f"Starting processing for files: {args.file_names}")

    # Process each input file
    for source_fn in args.file_names:
        log.info(f"Processing file: {source_fn}")
        try:
            if not source_fn.exists():
                log.error(f"File not found: {source_fn}. Skipping.")
                continue
            if not source_fn.is_file():
                log.error(f"Path is not a file: {source_fn}. Skipping.")
                continue

            if text := source_fn.read_text(encoding="utf-8-sig"):
                mm_file_name = source_fn.with_suffix(".mm")
                log.info(f"Creating mindmap: {mm_file_name}")
                create_mm(args, text, mm_file_name)
                log.info(f"Mindmap created: {mm_file_name}")
                # Attempt to open with Freeplane
                try:
                    subprocess.run(["open", "-a", "Freeplane.app", mm_file_name], check=True)
                    log.info(f"Opened {mm_file_name} in Freeplane.")
                except FileNotFoundError:
                    log.warning("Could not find 'open' command. Is this macOS?")
                except subprocess.CalledProcessError as e:
                    log.warning(f"Could not open {mm_file_name} in Freeplane: {e}")

            else:
                log.warning(f"File is empty: {source_fn}. Skipping.")
        except Exception as e:
            log.exception(f"An unexpected error occurred while processing {source_fn}: {e}")
            # Optionally continue to next file or re-raise/exit
            # continue

    log.info("Processing finished.")


if __name__ == "__main__":
    main()
