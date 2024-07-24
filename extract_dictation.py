#!/usr/bin/env python3
"""Extract a mindmap from a dictated text file using ad-hoc conventions."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import logging as log
import re
import subprocess
import sys
import time
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html
from typing import TextIO

from biblio.fields import (
    BIB_FIELDS,  # dict of field to its shortcut
    BIB_SHORTCUTS,  # dict of shortcuts to a field
)
from utils.web import yasn_publish

HOME = Path.home()


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

# CL_CO = {'annotation': '#999999', 'author': '#338800', 'title': '#090f6b',
#     'cite': '#ff33b8', 'author': '#338800',
#     'quote': '#166799', 'paraphrase': '#8b12d6',
#     'default': '#000000', None: None}
# CO_CL = dict([(label, color) for color, label in list(CL_CO.items())])


def clean(text):
    """clean and encode text"""
    # TODO: Maybe make use of b.smart_punctuation_to_ascii() and
    # utils_web.escape_XML()

    text = text.strip(", \f\r\n")
    REPLACEMENTS = [
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
    for v1, v2 in REPLACEMENTS:
        text = text.replace(v1, v2)
    return text


def get_date():
    now = time.localtime()
    # year = time.strftime("%Y", now).lower()
    # month = time.strftime("%m", now).lower()
    date_token = time.strftime("%Y%m%d", now)
    return date_token


def build_mm_from_txt(
    mm_fd: TextIO,
    line: str,
    started: bool,
    in_part: bool,
    in_chapter: bool,
    in_section: bool,
    in_subsection: bool,
    entry: dict,
) -> tuple[bool, bool, bool, bool, bool, dict]:
    citation = ""

    if line not in ("", "\r", "\n"):
        # print(f"{line=}")
        if line.lower().startswith("author ="):
            # and re.match('([^=]+ = (?=[^=]+)){2,}', line, re.I)
            if started:  # Do I need to close a previous entry
                if in_subsection:
                    mm_fd.write("""        </node>\n""")
                    in_subsection = False
                if in_section:
                    mm_fd.write("""      </node>\n""")
                    in_section = False
                if in_chapter:
                    mm_fd.write("""    </node>\n""")
                    in_chapter = False
                if in_part:
                    mm_fd.write("""    </node>\n""")
                    in_part = False

                mm_fd.write("""</node>\n</node>\n""")
                started = False
            started = True
            # should space be optional '(\w+) ?='
            cites = re.split(r"(\w+) =", line)[1:]
            # 2 references to an iterable object that are
            # unpacked with '*' and rezipped
            cite_pairs = list(zip(*[iter(cites)] * 2, strict=True))
            for token, value in cite_pairs:
                log.info(f"{token=}, {value=}")
                if token == "keyword":
                    log.info(f"{entry=}")
                    entry.setdefault("keyword", []).append(value.strip())
                else:
                    entry[token.lower()] = value.strip()

            if "author" not in entry:
                entry["author"] = "Unknown"
            if "title" not in entry:
                entry["title"] = "Untitled"
            if "subtitle" in entry:
                entry["title"] += ": " + entry["subtitle"]
                del entry["subtitle"]

            mm_fd.write(
                """<node STYLE_REF="{}" TEXT="{}" POSITION="RIGHT">\n""".format(
                    "author", clean(entry["author"].title())
                )
            )
            if "url" in entry:  # write title with hyperlink
                mm_fd.write(
                    """  <node STYLE_REF="{}" LINK="{}" TEXT="{}">\n""".format(
                        "title", clean(entry["url"]), clean(entry["title"])
                    )
                )
            else:
                mm_fd.write(  # write plain title
                    """  <node STYLE_REF="{}" TEXT="{}">\n""".format(
                        "title", clean(entry["title"])
                    )
                )

            for token, value in sorted(entry.items()):
                if token not in ("author", "title", "url", "keyword"):
                    if token in BIB_SHORTCUTS:
                        t, v = token.lower(), value
                    else:
                        if token.lower() in BIB_FIELDS:
                            t, v = BIB_FIELDS[token.lower()], value
                        else:
                            raise Exception(f"{token=} not in BIB_FIELDS")
                    citation_add = f" {t}={v}"
                    citation += citation_add
                if token == "keyword":
                    citation += " kw=" + " kw=".join(value)
            if citation != "":
                clean(citation)
            citation += f" r={get_date()}"
            mm_fd.write(f"""  <node STYLE_REF="cite" TEXT="{clean(citation)}"/>\n""")

        elif re.match(r"summary\.(.*)", line, re.I):
            matches = re.match(r"summary\.(.*)", line, re.I)
            entry["summary"] = matches.groups()[0]
            mm_fd.write(
                """  <node STYLE_REF="{}" TEXT="{}"/>\n""".format(
                    "annotation", clean(entry["summary"])
                )
            )

        elif re.match("part.*", line, re.I):
            if in_part:
                if in_chapter:
                    mm_fd.write("""    </node>\n""")  # close chapter
                    in_chapter = False
                if in_section:
                    mm_fd.write("""      </node>\n""")  # close section
                    in_section = False
                if in_subsection:
                    mm_fd.write("""      </node>\n""")  # close section
                    in_subsection = False
                mm_fd.write("""  </node>\n""")  # close part
                in_part = False
            mm_fd.write(
                """  <node STYLE_REF="{}" TEXT="{}">\n""".format("quote", clean(line))
            )
            in_part = True

        elif re.match("chapter.*", line, re.I):
            if in_chapter:
                if in_section:
                    mm_fd.write("""      </node>\n""")  # close section
                    in_section = False
                if in_subsection:
                    mm_fd.write("""      </node>\n""")  # close section
                    in_subsection = False
                mm_fd.write("""    </node>\n""")  # close chapter
                in_chapter = False
            mm_fd.write(
                """    <node STYLE_REF="{}" TEXT="{}">\n""".format("quote", clean(line))
            )
            in_chapter = True

        elif re.match("section.*", line, re.I):
            if in_subsection:
                mm_fd.write("""      </node>\n""")  # close section
                in_subsection = False
            if in_section:
                mm_fd.write("""    </node>\n""")
                in_section = False
            mm_fd.write(
                """      <node STYLE_REF="{}" TEXT="{}">\n""".format(
                    "quote", clean(line[9:])
                )
            )
            in_section = True

        elif re.match("subsection.*", line, re.I):
            if in_subsection:
                mm_fd.write("""    </node>\n""")
                in_subsection = False
            mm_fd.write(
                """      <node STYLE_REF="{}" TEXT="{}">\n""".format(
                    "quote", clean(line[12:])
                )
            )
            in_subsection = True

        elif re.match("(--.*)", line, re.I):
            mm_fd.write(
                """          <node STYLE_REF="{}" TEXT="{}"/>\n""".format(
                    "default", clean(line)
                )
            )

        else:
            node_color = "paraphrase"
            line_text = line
            line_no = ""
            # DIGIT_CHARS = '[\dcdilmxv]'  # arabic and roman numbers
            PAGE_NUM_PAT = r"^([\dcdilmxv]+)(\-[\dcdilmxv]+)? (.*?)(-[\dcdilmxv]+)?$"
            matches = re.match(PAGE_NUM_PAT, line, re.I)
            if matches:
                line_no = matches.group(1)
                if matches.group(2):
                    line_no += matches.group(2)
                if matches.group(4):
                    line_no += matches.group(4)
                line_no = line_no.lower()  # lower case roman numbers
                line_text = matches.group(3).strip()

            if line_text.startswith("excerpt."):
                node_color = "quote"
                line_text = line_text[9:]
            if line_text.strip().endswith("excerpt."):
                node_color = "quote"
                line_text = line_text[0:-9]

            mm_fd.write(
                """          <node STYLE_REF="{}" TEXT="{}"/>\n""".format(
                    node_color, clean(" ".join((line_no, line_text)))
                )
            )

    return started, in_part, in_chapter, in_section, in_subsection, entry


def create_mm(args: argparse.Namespace, text: str, mm_file_name: Path) -> None:
    import traceback

    with mm_file_name.open("w", encoding="utf-8", errors="replace") as mm_fd:
        entry = {}  # a bibliographic entry for yasn_publish
        entry["keyword"] = []  # there might not be any
        started = False
        in_part = False
        in_chapter = False
        in_section = False
        in_subsection = False
        line_number = 0

        mm_fd.write(f"""{MINDMAP_PREAMBLE}\n<node TEXT="Readings">\n""")

        for line_number, line in enumerate(text.split("\n")):
            line = line.strip()
            try:
                (
                    started,
                    in_part,
                    in_chapter,
                    in_section,
                    in_subsection,
                    entry,
                ) = build_mm_from_txt(
                    mm_fd,
                    line,
                    started,
                    in_part,
                    in_chapter,
                    in_section,
                    in_subsection,
                    entry,
                )
            except KeyError as err:
                print(err)
                print(traceback.print_tb(sys.exc_info()[2]), "\n", line_number, line)
                sys.exit()

        if in_subsection:
            mm_fd.write("""</node>""")  # close the last subsection
        if in_section:
            mm_fd.write("""</node>""")  # close the last section
        if in_chapter:
            mm_fd.write("""</node>""")  # close the last chapter
        if in_part:
            mm_fd.write("""</node>""")  # close the last part
        mm_fd.write("""</node>\n</node>\n</node>\n""")  # close the last entry
        mm_fd.write("""</node>\n</map>\n""")  # close the document
        log.info(f"{entry=}")
        if args.publish:
            yasn_publish(
                entry["summary"],
                entry["title"],
                None,
                entry["url"],
                " ".join(entry["keyword"]),
            )


def process_args(argv):
    """Process arguments"""
    # https://docs.python.org/3/library/argparse.html
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
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument("--version", action="version", version="0.1")
    args = arg_parser.parse_args(argv)

    log_level = (log.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        log.basicConfig(
            filename="extract-dictation.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        log.basicConfig(level=log_level, format=LOG_FORMAT)

    return args


if __name__ == "__main__":
    args = process_args(sys.argv[1:])
    log.critical("==================================")
    log.critical(f"{args=}")
    for source_fn in args.file_names:
        text = source_fn.read_text(encoding="utf-8-sig")
        mm_file_name = source_fn.with_suffix(".mm")
        create_mm(args, text, mm_file_name)
        subprocess.call(["open", "-a", "Freeplane.app", mm_file_name])
