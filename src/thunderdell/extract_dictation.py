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
from typing import Any, Dict, List, Optional, TextIO, Tuple, Union, cast

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
    cites = re.split(r"(\w+) =", line)[1:]
    return list(zip(*[iter(cites)] * 2, strict=True))


def update_entry_with_citations(
    entry: EntryDict, cite_pairs: list[tuple[str, str]]
) -> EntryDict:
    """Update entry dictionary with citation information."""
    for token, value in cite_pairs:
        log.info(f"{token=}, {value=}")
        match token.lower():
            case "keyword":
                if isinstance(entry.get("keyword"), list):
                    entry["keyword"].append(value.strip())
                else:
                    entry["keyword"] = [value.strip()]
            case _:
                entry[token.lower()] = value.strip()

    # Ensure required fields exist
    if "author" not in entry:
        entry["author"] = "Unknown"
    if "title" not in entry:
        entry["title"] = "Untitled"

    # Process subtitle
    if "subtitle" in entry:
        entry["title"] = f"{entry['title']}: {entry['subtitle']}"
        del entry["subtitle"]

    return entry


def build_citation_text(entry: EntryDict) -> str:
    """Build citation text from entry dictionary."""
    citation_parts = []

    for token, value in sorted(entry.items()):
        if token not in ("author", "title", "url", "keyword"):
            value_str = str(value)
            match token:
                case _ if token in BIB_SHORTCUTS:
                    t, v = token.lower(), value_str
                case _ if token.lower() in BIB_FIELDS:
                    t, v = BIB_FIELDS[token.lower()], value_str
                case _:
                    raise ValueError(f"{token=} not in BIB_FIELDS")
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
        started = in_part = in_chapter = in_section = in_subsection = False

    started = True

    # Parse and process citation data
    cite_pairs = parse_citation_pairs(line)
    entry = update_entry_with_citations(entry, cite_pairs)

    # Ensure values are strings
    author = str(entry["author"])
    title = str(entry["title"])

    # Write author node
    mm_fd.write(
        f"""<node STYLE_REF="author" TEXT="{clean(author.title())}" POSITION="RIGHT">\n"""
    )

    # Write title node with optional hyperlink
    if "url" in entry:
        url = str(entry["url"])
        mm_fd.write(
            f"""  <node STYLE_REF="title" LINK="{clean(url)}" TEXT="{clean(title)}">\n"""
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

    match element_type.lower():
        case "part":
            if in_part:
                close_sections(mm_fd, in_subsection, in_section, in_chapter, True)
                in_subsection = in_section = in_chapter = False
                in_part = False
            full_content = f"part{content}"
            mm_fd.write(
                f"""  <node STYLE_REF="quote" TEXT="{clean(full_content)}">\n"""
            )
            in_part = True

        case "chapter":
            if in_chapter:
                close_sections(mm_fd, in_subsection, in_section, True, False)
                in_subsection = in_section = False
                in_chapter = False
            full_content = f"chapter{content}"
            mm_fd.write(
                f"""    <node STYLE_REF="quote" TEXT="{clean(full_content)}">\n"""
            )
            in_chapter = True

        case "section":
            if in_subsection:
                close_sections(mm_fd, True, False, False, False)
                in_subsection = False
            if in_section:
                close_sections(mm_fd, False, True, False, False)
                in_section = False
            mm_fd.write(f"""      <node STYLE_REF="quote" TEXT="{clean(content)}">\n""")
            in_section = True

        case "subsection":
            if in_subsection:
                close_sections(mm_fd, True, False, False, False)
                in_subsection = False
            mm_fd.write(
                f"""        <node STYLE_REF="quote" TEXT="{clean(content)}">\n"""
            )
            in_subsection = True

    return started, in_part, in_chapter, in_section, in_subsection


def process_content_line(mm_fd: TextIO, line: str) -> None:
    """Process general content lines."""
    node_color = "paraphrase"
    line_text = line
    line_no = ""

    # Process page numbers
    page_pattern = r"^([\dcdilmxv]+)(\-[\dcdilmxv]+)? (.*?)(-[\dcdilmxv]+)?$"
    if match := re.match(page_pattern, line, re.I):
        line_no = match.group(1)
        line_no += match.group(2) or ""
        line_no += match.group(4) or ""
        line_no = line_no.lower()  # lower case roman numbers
        line_text = match.group(3).strip()

    # Process excerpts
    if line_text.startswith("excerpt."):
        node_color = "quote"
        line_text = line_text[8:].strip()
    elif line_text.strip().endswith("excerpt."):
        node_color = "quote"
        line_text = line_text[:-8].strip()

    text_content = " ".join(filter(None, [line_no, line_text]))
    mm_fd.write(
        f"""          <node STYLE_REF="{node_color}" TEXT="{clean(text_content)}"/>\n"""
    )


def build_mm_from_txt(
    mm_fd: TextIO,
    line: str,
    started: bool,
    in_part: bool,
    in_chapter: bool,
    in_section: bool,
    in_subsection: bool,
    entry: EntryDict,
) -> tuple[bool, bool, bool, bool, bool, EntryDict]:
    """Build a mindmap from text."""
    if not line or line in ("\r", "\n"):
        return started, in_part, in_chapter, in_section, in_subsection, entry

    state = (started, in_part, in_chapter, in_section, in_subsection)

    # Process line based on content type
    if line.lower().startswith("author ="):
        entry, state = process_author_line(mm_fd, line, entry, state)

    elif match := re.match(r"summary\.(.*)", line, re.I):
        entry["summary"] = match.group(1)
        mm_fd.write(
            f"""  <node STYLE_REF="annotation" TEXT="{clean(str(entry["summary"]))}"/>\n"""
        )

    elif match := re.match(r"(part|chapter|section|subsection)(.*)", line, re.I):
        element_type, content = match.groups()
        state = process_structure_element(mm_fd, element_type, content, state)

    elif line.startswith("--"):
        mm_fd.write(f"""          <node STYLE_REF="default" TEXT="{clean(line)}"/>\n""")

    else:
        process_content_line(mm_fd, line)

    return *state, entry


def create_mm(args: argparse.Namespace, text: str, mm_file_name: Path) -> None:
    """Create a mindmap file from the given text."""
    with mm_file_name.open("w", encoding="utf-8", errors="replace") as mm_fd:
        entry: EntryDict = {"keyword": []}

        # Initialize state variables
        started = False
        in_part = False
        in_chapter = False
        in_section = False
        in_subsection = False

        mm_fd.write(f'{MINDMAP_PREAMBLE}\n<node TEXT="Readings">\n')

        line = ""

        try:
            for _line_number, line in enumerate(text.split("\n")):
                if processed_line := line.strip():
                    (
                        started,
                        in_part,
                        in_chapter,
                        in_section,
                        in_subsection,
                        entry,
                    ) = build_mm_from_txt(
                        mm_fd,
                        processed_line,
                        started,
                        in_part,
                        in_chapter,
                        in_section,
                        in_subsection,
                        entry,
                    )
        except (ValueError, KeyError, IndexError) as err:
            import traceback

            print(f"Error processing line: {line}")
            print(f"Error: {err}")
            print(traceback.format_exc())
            sys.exit(1)
        except FileNotFoundError as err:
            print(f"File not found error: {err}")
            sys.exit(1)
        except PermissionError as err:
            print(f"Permission error: {err}")
            sys.exit(1)

        # Close any open nodes
        if in_subsection:
            mm_fd.write("        </node>\n")
        if in_section:
            mm_fd.write("      </node>\n")
        if in_chapter:
            mm_fd.write("    </node>\n")
        if in_part:
            mm_fd.write("  </node>\n")

        # Close entry nodes
        mm_fd.write("</node>\n</node>\n</node>\n")

        # Close document
        mm_fd.write("</node>\n</map>\n")

        log.info(f"{entry=}")
        # Publish if requested and required fields are present
        if args.publish and all(k in entry for k in ["summary", "title", "url"]):
            summary = str(entry.get("summary", ""))
            title = str(entry.get("title", ""))
            url = str(entry.get("url", ""))
            keywords = entry.get("keyword", [])
            if isinstance(keywords, list):
                keyword_str = " ".join(str(k) for k in keywords)
            else:
                keyword_str = str(keywords)

            yasn_publish(
                summary,
                title,
                "",  # Empty string instead of None for subtitle
                url,
                keyword_str,
            )


def parse_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Process command line arguments."""
    arg_parser = argparse.ArgumentParser(
        description="""Convert dictated notes to mindmap.

        `author` must be first in citation pairs, e.g., "author = ...
        """
    )

    # positional arguments
    arg_parser.add_argument("file_names", nargs="+", type=Path, metavar="FILE_NAMES")

    # optional arguments
    arg_parser.add_argument(
        "-p",
        "--publish",
        action="store_true",
        default=False,
        help="publish to social networks",
    )
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
    arg_parser.add_argument("--version", action="version", version="0.1")

    # Parse arguments
    args = arg_parser.parse_args(argv if argv is not None else sys.argv[1:])

    # Configure logging based on verbosity
    log_level = max(log.CRITICAL - (args.verbose * 10), log.DEBUG)

    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    log.basicConfig(
        filename="extract-dictation.log" if args.log_to_file else None,
        filemode="w" if args.log_to_file else "a",
        level=log_level,
        format=LOG_FORMAT,
    )

    return args


def main(args: argparse.Namespace | None = None) -> None:
    """Process dictation files and convert to mindmaps."""
    if args is None:
        args = parse_arguments()

    log.info(f"{args=}")

    # Process each input file
    for source_fn in args.file_names:
        try:
            if not source_fn.exists():
                log.error(f"File not found: {source_fn}")
                continue

            if text := source_fn.read_text(encoding="utf-8-sig"):
                mm_file_name = source_fn.with_suffix(".mm")
                create_mm(args, text, mm_file_name)
                subprocess.call(["open", "-a", "Freeplane.app", mm_file_name])
            else:
                log.warning(f"Empty file: {source_fn}")
        except Exception as e:
            log.exception(f"Error processing {source_fn}: {e}")


if __name__ == "__main__":
    main()
