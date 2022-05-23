#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Functions for emitting bibliographic entries to a file format."""

import logging
import os
import re
import urllib
from html import escape

# from thunderdell import CLIENT_HOME, HOME
import config
from utils.web import escape_XML

from formats.emit_biblatex import create_biblatex_author

# logger function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


def emit_results(args, entries, query, results_file):
    """Emit the results of the query"""

    def reverse_print(node, entry, spaces):
        """Move locator number to the end of the text with the biblatex key"""
        style_ref = node.get("STYLE_REF", "default")
        text = escape_XML(node.get("TEXT"))
        text = text.replace(  # restore my query_highlight strongs
            "&lt;strong&gt;", "<strong>"
        ).replace("&lt;/strong&gt;", "</strong>")
        prefix = "&gt; " if style_ref == "quote" else ""
        # don't reverse short texts and certain style refs
        if len(text) < 50 or style_ref in ["author", "title", "cite"]:
            cite = ""
            # prefix = ""  # this could remove ">" from short quotes
        else:
            locator = ""
            LOCATOR_PAT = re.compile(
                r"^(?:<strong>)?(\d+(?:-\d+)?)(?:</strong>)? (.*)"
            )
            matches = LOCATOR_PAT.match(text)
            if matches:
                text = matches.group(2)
                locator = matches.group(1)
                # http://mirrors.ibiblio.org/CTAN/macros/latex/exptl/biblatex/doc/biblatex.pdf
                # biblatex: page, column, line, verse, section, paragraph
                # kindle: location
                if "pagination" in entry:
                    if entry["pagination"] == "section":
                        locator = f", sec. {locator}"
                    elif entry["pagination"] == "paragraph":
                        locator = f", para. {locator}"
                    elif entry["pagination"] == "location":
                        locator = f", loc. {locator}"
                    elif entry["pagination"] == "chapter":
                        locator = f", ch. {locator}"
                    elif entry["pagination"] == "verse":
                        locator = f", vers. {locator}"
                    elif entry["pagination"] == "column":
                        locator = f", col. {locator}"
                    elif entry["pagination"] == "line":
                        locator = f", line {locator}"
                    else:
                        raise Exception(
                            f"unknown locator '{entry['pagination']}' "
                            f"for '{entry['title']}' in '{entry['custom2']}'"
                        )
                else:
                    if "-" in locator:
                        locator = f", pp. {locator}"
                    else:
                        locator = f", p. {locator}"
            cite = f" [@{entry['identifier'].replace(' ', '')}{locator}]"

        hypertext = text

        # if node has first child <font BOLD="true"/> then embolden
        style = ""
        if len(node) > 0:
            if node[0].tag == "font" and node[0].get("BOLD") == "true":
                style = "font-weight: bold"

        if "LINK" in node.attrib:
            link = escape(node.get("LINK"))
            hypertext = f'<a class="reverse_print" href="{link}">{text}</a>'

        results_file.write(
            f'{spaces}<li style="{style}" class="{style_ref}">'
            f"{prefix}{hypertext}{cite}</li>\n"
        )

    def pretty_print(node, entry, spaces):
        """Pretty print a node and descendants into indented HTML"""
        # bug: nested titles are printed twice. 101217
        if node.get("TEXT") is not None:
            reverse_print(node, entry, spaces)
        # I should clean all of this up to use simpleHTMLwriter,
        # markup.py, or yattag
        if len(node) > 0:
            results_file.write(f'{spaces}<li><ul class="pprint_recurse">\n')
            spaces = spaces + " "
            for child in node:
                if child.get("STYLE_REF") == "author":
                    break
                pretty_print(child, entry, spaces)
            spaces = spaces[0:-1]
            results_file.write(f"{spaces}</ul></li><!--pprint_recurse-->\n")

    def get_url_query(token):
        """Return the URL for an HTML link to the actual title"""
        token = token.replace("<strong>", "").replace("</strong>", "")
        # urllib won't accept unicode
        token = urllib.parse.quote(token.encode("utf-8"))
        # debug(f"token = '{token}' type = '{type(token)}'")
        url_query = escape("search.cgi?query=%s") % token
        # debug(f"url_query = '{url_query}' type = '{type(url_query)}'")
        return url_query

    def get_url_MM(file_name):
        """Return URL for the source MindMap based on whether CGI or cmdline"""
        if __name__ == "__main__":
            return file_name
        else:  # CGI
            client_path = file_name.replace(
                f"{config.HOME}", f"{config.CLIENT_HOME}"
            )
            return f"file://{client_path}"

    def print_entry(
        identifier, author, date, title, url, MM_mm_file, base_mm_file, spaces
    ):
        identifier_html = (
            f'<li class="identifier_html">'
            f'<a href="{get_url_query(identifier)}">{identifier}</a>'
        )
        title_html = (
            f'<a class="title_html"'
            f' href="{get_url_query(title)}">{title}</a>'
        )
        if url:
            link_html = f'[<a class="link_html" href="{url}">url</a>]'
        else:
            link_html = ""
        from_html = (
            f'from <a class="from_html" '
            f'href="{MM_mm_file}">{base_mm_file}</a>'
        )
        results_file.write(
            f"{spaces}{identifier_html}, "
            f"<em>{title_html}</em> {link_html} [{from_html}]"
        )
        results_file.write(f"{spaces}</li><!--identifier_html-->\n")

    spaces = " "
    for key, entry in sorted(entries.items()):
        identifier = entry["identifier"]
        author = create_biblatex_author(entry["author"])
        title = entry["title"]
        date = entry["date"]
        url = entry.get("url", "")
        base_mm_file = os.path.basename(entry["_mm_file"])
        MM_mm_file = get_url_MM(entry["_mm_file"])

        # if I am what was queried, print all of me
        if entry["identifier"] == args.query:
            results_file.write(
                '%s<li class="li_entry_identifier">\n' % (spaces)
            )
            spaces = spaces + " "
            results_file.write('%s<ul class="tit_tree">\n' % (spaces))
            spaces = spaces + " "
            results_file.write(
                '%s<li style="text-align: right">[<a href="%s">%s</a>]</li>\n'
                % (spaces, MM_mm_file, base_mm_file),
            )
            fl_names = ", ".join(
                name[0] + " " + name[2] for name in entry["author"]
            )
            title_mdn = f"{title}"
            if url:
                title_mdn = f"[{title}]({url})"
            JS_CLICK_TO_COPY = (
                """<li class="mdn">"""
                """<a href="javascript:document.addEventListener("""
                """'click', () => {{navigator.clipboard.writeText('%s');"""
                """}});">⧉</a> %s\n"""
            )
            mdn_cite = f"[@{identifier}]"
            results_file.write(JS_CLICK_TO_COPY % (escape(mdn_cite), mdn_cite))
            mdn_footnote = (
                f"[^{identifier}]:" f"  {fl_names}, {date[0]}, {title_mdn}"
            )
            results_file.write(
                JS_CLICK_TO_COPY % (escape(mdn_footnote), mdn_footnote)
            )
            mdn_link = (
                f"""[{identifier}]: {url}"""
                f"""" {fl_names}, {date[0]}, «{title}»" """
            )
            results_file.write(JS_CLICK_TO_COPY % (escape(mdn_link), mdn_link))
            results_file.write(f'{spaces}<li class="author">{fl_names}</li>\n')
            # results_file.write(f'{spaces}<li class="pretty_print">\n')
            pretty_print(entry["_title_node"], entry, spaces)
            # results_file.write(f'{spaces}</li><!--pretty_print-->')
            results_file.write(f"{spaces}</ul><!--tit_tree-->\n"),
            results_file.write(f"{spaces}</li>\n"),

        # if some nodes were matched, PP with citation info reversed
        if "_node_results" in entry:
            print_entry(
                identifier,
                author,
                date,
                title,
                url,
                MM_mm_file,
                base_mm_file,
                spaces,
            )
            if len(entry["_node_results"]) > 0:
                results_file.write(f"{spaces}<li>\n")
                spaces = spaces + " "
                results_file.write(f'{spaces}<ul class="li_node_results">\n')
                spaces = spaces + " "
                for node in entry["_node_results"]:
                    reverse_print(node, entry, spaces)
                spaces = spaces[0:-1]
            results_file.write(f"{spaces}</ul><!--li_node_results-->\n")
            spaces = spaces[0:-1]
            results_file.write(f"{spaces}</li>\n")
        # if my author or title matched, print biblio w/ link to complete entry
        elif "_author_result" in entry:
            author = (
                f"{entry['_author_result'].get('TEXT')}"
                f"{entry['date'].year}"
            )
            print_entry(
                identifier,
                author,
                date,
                title,
                url,
                MM_mm_file,
                base_mm_file,
                spaces,
            )
        elif "_title_result" in entry:
            title = entry["_title_result"].get("TEXT")
            print_entry(
                identifier,
                author,
                date,
                title,
                url,
                MM_mm_file,
                base_mm_file,
                spaces,
            )
