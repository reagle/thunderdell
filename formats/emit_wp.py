#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Functions for emitting bibliographic entries to a file format."""

import calendar
import logging

# from thunderdell import CLIENT_HOME, HOME
from biblio.fields import BIB_SHORTCUTS_ITEMS, BIBLATEX_WP_FIELD_MAP

# logger function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


def emit_wp(args, entries):
    """Emit citations in Wikipedia's {{citation}} template format for
    use in a List-defined references block.

    See: https://en.wikipedia.org/wiki/Help:List-defined_references
    See: https://en.wikipedia.org/wiki/Template:Cite

    """
    # TODO: Wikipedia dates may not be YYYY-MM, only YYYY or YYYY-MM-DD

    # debug(f"********************")
    # debug(f"{entries=}")

    def output_wp_names(field, names):
        """Rejigger names for odd WP author and editor conventions."""
        name_num = 0
        for name in names:
            name_num += 1
            if field == "author":
                prefix = ""
                suffix = name_num
            elif field == "editor":
                prefix = f"editor{str(name_num)}-"
                suffix = ""
            args.outfd.write(f"| {prefix}first{suffix} = {name[0]}\n")
            args.outfd.write(f'| {prefix}last{suffix} = {" ".join(name[1:])}\n')

    for key, entry in sorted(entries.items()):
        wp_ident = key
        # debug(f"{wp_ident=}")
        args.outfd.write(f"<ref name={wp_ident}>\n")
        args.outfd.write("{{{{citation\n")

        for short, field in BIB_SHORTCUTS_ITEMS:
            if field in entry and entry[field] is not None:
                value = entry[field]
                if field in (
                    "annotation",
                    "chapter",
                    "custom1",
                    "custom2",
                    "entry_type",
                    "identifier",
                    "keyword",
                    "note",
                    "shorttitle",
                ):
                    continue
                elif field == "author":
                    output_wp_names(field, value)
                    continue
                elif field == "editor":
                    output_wp_names(field, value)
                    continue
                elif field in ("date", "origdate", "urldate"):
                    date = value.year
                    if value.month:
                        date = f"{calendar.month_name[int(value.month)]} {date}"
                    if value.day:
                        date = f"{value.day.lstrip('0')} {date}"
                    # date = "-".join(
                    #     filter(None, (value.year, value.month, value.day))
                    # )
                    if value.circa:
                        date = "{{circa|" + date + "}}"
                    value = date
                elif field == "title":  # TODO: convert value to title case?
                    if "booktitle" in entry:
                        field = "chapter"
                if field in BIBLATEX_WP_FIELD_MAP:
                    field = BIBLATEX_WP_FIELD_MAP[field]
                args.outfd.write(f"| {field} = {value}\n")
        args.outfd.write("}}\n</ref>\n")
