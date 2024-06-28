#!/usr/bin/env python3
"""Convert a bibtex file into a mindmap."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

# TODO 2023-07-07
# - convert about to biblatex date format (d=)
# - handle name variances (e.g., "First Last" without comma)

import logging
import re
from pathlib import Path  # https://docs.python.org/3/library/pathlib.html

HOME = str(Path("~").expanduser())

log_level = 100  # default
critical = logging.critical
info = logging.info
dbg = logging.debug
warn = logging.warn
error = logging.error
excpt = logging.exception


def regex_parse(text: list[str]) -> dict[str, dict[str, str]]:
    key = ""
    entries = {}

    key_pattern = re.compile(r"@\w*{(.*)")  # Beginning/id of bibtex entry
    value_pattern = re.compile(r"\s*(\w+) ?= ?{(.*)},?")

    for line in text:
        print(f"{line=}")
        key_match = key_pattern.match(line)
        if key_match:
            key = key_match.group(1)
            print(f"{key=}")
            entries[key] = {}
            continue  # Keys/IDs are assumed to be alone on single line
        value_match = value_pattern.match(line)
        if value_match:
            field, value = value_match.groups()
            print(f"{field=} {value=}")
            entries[key][field] = value.replace("{", "").replace("}", "")
    return entries


def xml_escape(text: str) -> str:
    """Remove entities and spurious whitespace"""
    import html

    escaped_text = html.escape(text, quote=True).strip()
    return escaped_text


def process(entries: dict, fdo):
    fdo.write("""<map version="1.11.1">\n<node TEXT="Readings">\n""")

    for entry in list(entries.values()):
        info(f"entry = '{entry}'")
        cite = []
        reordered_names = []
        names = xml_escape(entry["author"])
        names = names.split(" and ")
        for name in names:
            last, first = name.split(", ")
            reordered_names.append(first + " " + last)
        fdo.write(
            """  <node COLOR="#338800" TEXT="{}">\n""".format(
                ", ".join(reordered_names)
            )
        )

        if "url" in entry:
            fdo.write(
                """    <node COLOR="#090f6b" LINK="{}" TEXT="{}">\n""".format(
                    xml_escape(entry["url"]), xml_escape(entry["title"])
                )
            )
        else:
            fdo.write(
                """    <node COLOR="#090f6b" TEXT="{}">\n""".format(
                    xml_escape(entry["title"])
                )
            )

        # it would be more elegant to just loop through
        #   `from td import terms`
        # but this creates an ordering that I like
        if "year" in entry:
            cite.append(("y", entry["year"]))
        if "month" in entry:
            cite.append(("m", entry["month"]))
        if "booktitle" in entry:
            cite.append(("bt", entry["booktitle"]))
        if "editor" in entry:
            cite.append(("e", entry["editor"]))
        if "publisher" in entry:
            cite.append(("p", entry["publisher"]))
        if "address" in entry:
            cite.append(("a", entry["address"]))
        if "edition" in entry:
            cite.append(("ed", entry["edition"]))
        if "chapter" in entry:
            cite.append(("ch", entry["chapter"]))
        if "pages" in entry:
            entry["pages"] = entry["pages"].replace("--", "-").replace(" ", "")
            cite.append(("pp", entry["pages"]))
        if "journal" in entry:
            cite.append(("j", entry["journal"]))
        if "volume" in entry:
            cite.append(("v", entry["volume"]))
        if "number" in entry:
            cite.append(("n", entry["number"]))
        if "doi" in entry:
            cite.append(("doi", entry["doi"]))
        if "annote" in entry:
            cite.append(("an", entry["annote"]))
        if "note" in entry:
            cite.append(("nt", entry["note"]))

        fdo.write(
            """      <node COLOR="#ff33b8" TEXT="{}"/>\n""".format(
                xml_escape(" ".join(["{}={}".format(*vals) for vals in cite]))
            )
        )

        if "abstract" in entry:
            fdo.write(
                """      <node COLOR="#999999" \
                TEXT="&quot;{}&quot;"/>\n""".format(xml_escape(entry["abstract"]))
            )

        fdo.write("""    </node>\n  </node>\n""")

    fdo.write("""</node>\n</map>\n""")


if __name__ == "__main__":
    import argparse  # http://docs.python.org/dev/library/argparse.html

    arg_parser = argparse.ArgumentParser(
        description="Converts bibtex files to mindmap."
    )

    # positional arguments
    arg_parser.add_argument("file_names", nargs="+", type=Path, metavar="FILE_NAMES")
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
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument("--version", action="version", version="0.1")
    args = arg_parser.parse_args()

    if args.verbose == 1:
        log_level = logging.CRITICAL
    elif args.verbose == 2:
        log_level = logging.INFO
    elif args.verbose >= 3:
        log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
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
            fdo = file_out.open("w")
        except OSError:
            print(f"{file_path=} does not exist")
            continue
        entries = regex_parse(bibtex_content.split("\n"))
        process(entries, fdo)
        fdo.close()
