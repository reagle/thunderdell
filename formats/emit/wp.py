"""Emit Wikipedia bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import calendar

from biblio.fields import BIB_SHORTCUTS_ITEMS, BIBLATEX_WP_FIELD_MAP


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
        for name_num, name in enumerate(names, 1):
            prefix, suffix = "", name_num
            if field == "editor":
                prefix, suffix = f"editor{name_num!s}-", ""
            args.outfd.write(f"| {prefix}first{suffix} = {name[0]}\n")
            args.outfd.write(f'| {prefix}last{suffix} = {" ".join(name[1:])}\n')

    for key, entry in sorted(entries.items()):
        wp_ident = key
        # debug(f"{wp_ident=}")
        args.outfd.write(f"<ref name={wp_ident}>\n")
        args.outfd.write("{{{{citation\n")

        for _short, field in BIB_SHORTCUTS_ITEMS:
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
                elif field in ("author", "editor"):
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
