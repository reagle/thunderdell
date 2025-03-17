#!/usr/bin/env python3
"""Query items logged to my planning page made by Busy Sponge."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import re
import sys
import webbrowser
from pathlib import Path

HOME = Path.home()


def query_sponge(query: str) -> Path:
    """Query items logged to my planning page made by Busy Sponge."""
    in_files = [
        HOME / "joseph/plan/index.html",
        HOME / "joseph/plan/done.html",
        HOME / "joseph/plan/2010/s10.html",
        HOME / "joseph/plan/2009/f09.html",
        HOME / "joseph/plan/2009/s09.html",
        HOME / "joseph/plan/2008/f08.html",
        HOME / "joseph/plan/2008/s08.html",
        HOME / "joseph/plan/2007/f07.html",
        HOME / "joseph/plan/2007/s07.html",
        HOME / "joseph/plan/2006/f06.html",
        HOME / "joseph/plan/2006/s06.html",
        HOME / "joseph/plan/2005/f05.html",
        HOME / "joseph/plan/2005/s05.html",
        HOME / "joseph/plan/2004/f04.html",
        HOME / "joseph/plan/2004/s04.html",
        HOME / "joseph/plan/2003/f03.html",
    ]

    out_file = HOME / "tmp/.td/query-sponge-result.html"

    out_str = ""
    query_pattern = re.compile(query, re.DOTALL | re.IGNORECASE)
    li_expression = r'<li class="event".*?>\d\d\d\d\d\d:.*?</li>'
    li_pattern = re.compile(li_expression, re.DOTALL | re.IGNORECASE)

    for file in in_files:
        content = file.read_text(encoding="utf-8", errors="replace")
        lis = li_pattern.findall(content)
        for li in lis:
            if query_pattern.search(li):
                out_str += li

    if out_str:
        out_str = f"<ol>{out_str}</ol>"
    else:
        out_str = f"<p>No results for query '{query}'</p>"

    HTMLPage = f"""<?xml version="1.0" encoding="iso-8859-1"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
        <title>Reagle's Planning Page</title>
        <link rel="stylesheet" type="text/css"
        href="../plan.css" />
        <link rel="icon" type="image/x-icon" href="https://reagle.org/favicon.ico">
        </head>
        <body xml:lang="en" lang="en">
        <div>
            <form method="get"
                  action="https://reagle.org/joseph/plan/cgi-bin/search.cgi">
            <a href="../2005/06/search.html">Searching</a> :
            <input value="Go" name="Go" type="submit" />
              <input size="25" name="query" maxlength="80" type="text" />
              <input name="sitesearch" value="BusySponge"type="radio" /> BS
              <input name="sitesearch" checked="checked"value="MindMap"
               type="radio" /> MM
            </form>
        </div>{out_str}</body></html>"""

    out_file.write_text(HTMLPage, encoding="utf-8")

    return out_file


def main():
    import sys

    query = "".join(sys.argv[1:])
    query_result_file = query_sponge(query)
    webbrowser.open(query_result_file.as_uri())


if __name__ == "__main__":
    main()
