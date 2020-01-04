#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Convert a bibtex file into a mindmap."""

import logging
from os import chdir, environ, mkdir, rename
from os.path import abspath, exists, expanduser, splitext
import re
import sys

HOME = expanduser("~")

log_level = 100  # default
critical = logging.critical
info = logging.info
dbg = logging.debug
warn = logging.warn
error = logging.error
excpt = logging.exception


def regexParse(text):

    entries = {}
    key_pat = re.compile(r"@\w+{(.*),")
    value_pat = re.compile(r"\s+(\w+) ?= ?{(.*)},?")
    for line in text:
        key_match = key_pat.match(line)
        if key_match:
            key = key_match.group(1)
            entries[key] = {}
            continue
        value_match = value_pat.match(line)
        if value_match:
            field, value = value_match.groups()
            entries[key][field] = value.replace("{", "").replace("}", "")
    return entries


def xml_escape(text):
    """Remove entities and spurious whitespace"""
    import cgi

    escaped_text = cgi.escape(text, quote=True).strip()
    return escaped_text


def process(entries):

    fdo.write("""<map version="0.7.2">\n<node TEXT="Readings">\n""")

    for entry in list(entries.values()):
        info("entry = '%s'" % (entry))
        cite = []
        reordered_names = []
        names = xml_escape(entry["author"])
        names = names.split(" and ")
        for name in names:
            last, first = name.split(", ")
            reordered_names.append(first + " " + last)
        fdo.write(
            """  <node COLOR="#338800" TEXT="%s">\n"""
            % ", ".join(reordered_names)
        )

        if "url" in entry:
            fdo.write(
                """    <node COLOR="#090f6b" LINK="%s" TEXT="%s">\n"""
                % (xml_escape(entry["url"]), xml_escape(entry["title"]))
            )
        else:
            fdo.write(
                """    <node COLOR="#090f6b" TEXT="%s">\n"""
                % xml_escape(entry["title"])
            )

        # it would be more elegant to just loop through
        #   `from fe import terms`
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
            """      <node COLOR="#ff33b8" TEXT="%s"/>\n"""
            % xml_escape(" ".join(["%s=%s" % vals for vals in cite]))
        )

        if "abstract" in entry:
            fdo.write(
                """      <node COLOR="#999999" \
                TEXT="&quot;%s&quot;"/>\n"""
                % xml_escape(entry["abstract"])
            )

        fdo.write("""    </node>\n  </node>\n""")

    fdo.write("""</node>\n</map>\n""")


if __name__ == "__main__":

    import argparse  # http://docs.python.org/dev/library/argparse.html

    arg_parser = argparse.ArgumentParser(description="TBD")

    # positional arguments
    arg_parser.add_argument("files", nargs="+", metavar="FILE")
    # optional arguments
    arg_parser.add_argument(
        "-L",
        "--log-to-file",
        action="store_true",
        default=False,
        help="log to file %(prog)s.log",
    )
    arg_parser.add_argument(
        "-n",
        "--number",
        type=int,
        default=10,
        help="some number (default: %(default)s)",
    )
    arg_parser.add_argument(
        "-V",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument("--version", action="version", version="TBD")
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
            filename="PROG-TEMPLATE.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    # Do some actual work.
    files = [abspath(file_name) for file_name in args.files]
    for file_name in files:
        try:
<<<<<<< HEAD
            src = open(
                file_name, "r", encoding="utf-8", errors="replace"
            ).read()
=======
            src = open(file_name, "r", encoding="utf-8", errors="replace").read()
>>>>>>> 0c9f3dd5a069cb78a83556b8af617fd755ab83ec
            fileOut = splitext(file_name)[0] + ".mm"
            fdo = open(fileOut, "wb", encoding="utf-8", errors="replace")
        except IOError:
            print("    file does not exist")
            continue
        entries = regexParse(src.split("\n"))
        process(entries)
