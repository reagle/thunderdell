"""Emit HTML version of bibliographic data.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import re
import urllib.parse
from html import escape
from pathlib import Path

import lxml.etree as et  # type: ignore[reportMissingModuleSource]

from thunderdell import config
from thunderdell.types_thunderdell import EntriesDict, EntryDict

# from thunderdell.formats.emit.biblatex import create_biblatex_author
from thunderdell.utils.web import straighten_quotes, xml_escape


def emit_results(
    args: argparse.Namespace,
    entries: EntriesDict,
) -> None:
    """Emit the results of the query."""
    query = args.query
    results_file = args.results_file
    spaces = " "
    for _, entry in sorted(entries.items()):
        identifier = entry["identifier"]
        title = entry["title"]
        date = entry["date"]
        cite = entry.get("cite", "")
        url = entry.get("url", "")
        base_mm_file = Path(entry["_mm_file"]).name
        MM_mm_file = get_url_MM(entry["_mm_file"])

        # If I am what was queried, print all of me
        if entry["identifier"] == query:
            results_file.write(f'{spaces}<li class="li_entry_identifier">\n')
            spaces = spaces + " "
            results_file.write(f'{spaces}<ul class="tit_tree">\n')
            spaces = spaces + " "
            results_file.write(
                f'{spaces}<li style="text-align: right">[<a href="{MM_mm_file}">{base_mm_file}</a>]</li>\n',
            )
            fl_names = ", ".join(name[0] + " " + name[2] for name in entry["author"])
            title_mdn = f"{title}"
            if url:
                title_mdn = f"[{title}]({url})"

            # For ease of use, JavaScript ⧉ button copies
            JS_CLICK_TO_COPY = (
                """<li class="mdn">"""
                """<a href="javascript:document.addEventListener("""
                """'click', () => {{navigator.clipboard.writeText('%s');"""
                """}});">⧉</a> %s\n"""
            )
            mdn_cite = f"[@{identifier}]"
            results_file.write(JS_CLICK_TO_COPY % (escape(mdn_cite), mdn_cite))
            mdn_footnote = f"[^{identifier}]:  {fl_names}, {date[0]},  «{title_mdn}»"
            results_file.write(JS_CLICK_TO_COPY % (escape(mdn_footnote), mdn_footnote))

            results_file.write(f'{spaces}<li class="author">{fl_names}</li>\n')
            pretty_print(entry["_title_node"], entry, spaces, results_file)
            results_file.write(f"{spaces}</ul><!--tit_tree-->\n")
            results_file.write(f"{spaces}</li>\n")

        # If some nodes were matched, pretty print with citation info reversed
        if "_node_results" in entry:
            print_entry(
                identifier,
                title,
                url,
                cite,
                MM_mm_file,
                base_mm_file,
                spaces,
                results_file,
            )
            results_file.write(f'<li class="cite">{cite}</li>')
            if len(entry["_node_results"]) > 0:
                results_file.write(f"{spaces}<li>\n")
                spaces = spaces + " "
                results_file.write(f'{spaces}<ul class="li_node_results">\n')
                spaces = spaces + " "
                for node in entry["_node_results"]:
                    reverse_print(node, entry, spaces, results_file)
                spaces = spaces[0:-1]
            results_file.write(f"{spaces}</ul><!--li_node_results-->\n")
            spaces = spaces[0:-1]
            results_file.write(f"{spaces}</li>\n")

        # If my author or title matched, print biblio w/ link to complete entry
        elif "_author_result" in entry:
            print_entry(
                identifier,
                title,
                url,
                cite,
                MM_mm_file,
                base_mm_file,
                spaces,
                results_file,
            )
            results_file.write(f'<li class="cite">{cite}</li>')
        elif "_title_result" in entry:
            title = entry["_title_result"].get("TEXT")
            print_entry(
                identifier,
                title,
                url,
                cite,
                MM_mm_file,
                base_mm_file,
                spaces,
                results_file,
            )


LOCATOR_PREFIX_MAP = {
    "section": ", sec.",
    "paragraph": ", para.",
    "location": ", loc.",
    "chapter": ", ch.",
    "verse": ", vers.",
    "column": ", col.",
    "line": ", line",
}


def reverse_print(node: et._Element, entry: EntryDict, spaces: str, results_file):
    """Move locator number to the end of the text with the biblatex key."""
    style_ref = node.get("STYLE_REF", "default")
    text = straighten_quotes(node.get("TEXT", ""))
    text = xml_escape(text)
    text = text.replace(  # restore my query_highlight strongs
        "&lt;strong&gt;", "<strong>"
    ).replace("&lt;/strong&gt;", "</strong>")
    quote_mark = "&gt; " if style_ref == "quote" else ""
    # Don't reverse short texts and certain style refs
    if len(text) < 50 or style_ref in ["author", "title", "cite"]:
        cite = ""
    else:
        locator = ""
        LOCATOR_PAT = re.compile(r"^(?:<strong>)?(\d+(?:-\d+)?)(?:</strong>)? (.*)")
        matches = LOCATOR_PAT.match(text)
        if matches:
            text = matches.group(2)
            locator = matches.group(1)
            # http://mirrors.ibiblio.org/CTAN/macros/latex/exptl/biblatex/doc/biblatex.pdf
            # biblatex: page, column, line, verse, section, paragraph
            # kindle: location
            if "pagination" in entry:
                prefix = LOCATOR_PREFIX_MAP.get(entry["pagination"], None)
                if prefix is None:
                    raise Exception(
                        f"unknown locator '{entry['pagination']}' "
                        + f"for '{entry['title']}' in '{entry['custom2']}'"
                    )
                locator = f"{prefix} {locator}"
            else:
                # If no pagination specified, assume page number
                locator = f", pp. {locator}" if "-" in locator else f", p. {locator}"
        cite = f" [@{entry['identifier'].replace(' ', '')}{locator}]"

    hypertext = text

    # If node has first child <font BOLD="true"/> then embolden
    style = ""
    if len(node) > 0 and node[0].tag == "font" and node[0].get("BOLD") == "true":
        style = "font-weight: bold"

    if "LINK" in node.attrib:
        link = escape(node.get("LINK", ""))
        hypertext = f'<a class="reverse_print" href="{link}">{text}</a>'

    results_file.write(
        f'{spaces}<li style="{style}" class="{style_ref}">'
        + f"{quote_mark}{hypertext}{cite}</li>\n"
    )


def pretty_print(node: et._Element, entry: EntryDict, spaces: str, results_file):
    """Pretty print a node and descendants into indented HTML."""
    if node.get("TEXT") is not None:
        reverse_print(node, entry, spaces, results_file)
    # TODO: replace manual HTML with simpleHTMLwriter,markup.py, or yattag
    if len(node) > 0:
        results_file.write(f'{spaces}<li><ul class="pprint_recurse">\n')
        spaces = spaces + " "
        for child in node:
            if child.get("STYLE_REF") == "author":
                break
            pretty_print(child, entry, spaces, results_file)
        spaces = spaces[0:-1]
        results_file.write(f"{spaces}</ul></li><!--pprint_recurse-->\n")


def print_entry(
    identifier: str,
    # author,
    # date,
    title: str,
    url: str,
    cite: str,
    MM_mm_file: str,
    base_mm_file: str,
    spaces: str,
    results_file,
):
    """Print entry."""
    identifier_html = (
        '<li class="identifier_html">'
        f'<a href="{get_url_query(identifier)}">{identifier}</a>'
    )
    title_html = f'<a class="title_html" href="{get_url_query(title)}">{title}</a>'
    link_html = f'[<a class="link_html" href="{url}">url</a>]' if url else ""
    from_html = f'from <a class="from_html" href="{MM_mm_file}">{base_mm_file}</a>'
    results_file.write(
        f"{spaces}{identifier_html}, <em>{title_html}</em> {link_html} [{from_html}]"
    )
    results_file.write(f"{spaces}</li><!--identifier_html-->\n")


def get_url_query(token: str) -> str:
    """Return the URL for an HTML link to the actual title."""
    token = token.replace("<strong>", "").replace("</strong>", "")
    # urllib won't accept unicode
    token = urllib.parse.quote(token.encode("utf-8"))
    # debug(f"token = '{token}' type = '{type(token)}'")
    url_query = escape("/joseph/plan/qb/?query=%s") % token
    # debug(f"url_query = '{url_query}' type = '{type(url_query)}'")
    return url_query


def get_url_MM(file_name: str) -> str:
    """Return URL for the source MindMap based on whether CGI or cmdline."""
    if __name__ == "__main__":
        return file_name
    else:  # CGI
        file_path = Path(file_name).absolute()
        client_path = file_path.relative_to(config.HOME)
        return f"file://{config.CLIENT_HOME / client_path}"
