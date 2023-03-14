#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""
Busy Query, by Joseph Reagle http://reagle.org/joseph/

Query items logged to my planning page made by Busy Sponge.

https://github.com/reagle/thunderdell
"""


import codecs
import os
import re
import sys
import webbrowser

HOME = os.path.expanduser("~")


def query_sponge(query: str) -> str:
    in_files = [
        HOME + "/joseph/plan/plans/index.html",
        HOME + "/joseph/plan/plans/20.html",
        HOME + "/joseph/plan/plans/18.html",
        HOME + "/joseph/plan/plans/16.html",
        HOME + "/joseph/plan/plans/15.html",
        HOME + "/joseph/plan/plans/12.html",
        HOME + "/joseph/plan/plans/11s.html",
        HOME + "/joseph/plan/plans/11f.html",
        HOME + "/joseph/plan/2010/s10.html",
        HOME + "/joseph/plan/2009/f09.html",
        HOME + "/joseph/plan/2009/s09.html",
        HOME + "/joseph/plan/2008/f08.html",
        HOME + "/joseph/plan/2008/s08.html",
        HOME + "/joseph/plan/2007/f07.html",
        HOME + "/joseph/plan/2007/s07.html",
        HOME + "/joseph/plan/2006/f06.html",
        HOME + "/joseph/plan/2006/s06.html",
        HOME + "/joseph/plan/2005/f05.html",
        HOME + "/joseph/plan/2005/s05.html",
        HOME + "/joseph/plan/2004/f04.html",
        HOME + "/joseph/plan/2004/s04.html",
        HOME + "/joseph/plan/2003/f03.html",
        # HOME+"/data/2web/WWW/Team/Reagle/Overview.html",
        # HOME+"/data/2web/WWW/Team/Reagle/history.html",
    ]

    out_file = HOME + "/tmp/.td/query-sponge-result.html"

    out_str = ""
    query_pattern = re.compile(query, re.DOTALL | re.IGNORECASE)
    li_expression = r'<li class="event".*?>\d\d\d\d\d\d:.*?</li>'
    li_pattern = re.compile(li_expression, re.DOTALL | re.IGNORECASE)

    for file in in_files:
        in_fd = codecs.open(file, "r", "utf-8", "replace")
        content = in_fd.read()
        in_fd.close()
        lis = li_pattern.findall(content)
        for li in lis:
            if query_pattern.search(li):
                out_str = out_str + li

    if out_str != "":
        out_str = """<ol>%s</ol>""" % out_str
    else:
        out_str = """<p>No results for query '%s'</p>""" % query

    HTMLPage = (
        """<?xml version="1.0" encoding="iso-8859-1"?>
        <!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
        "http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
        <html xmlns="http://www.w3.org/1999/xhtml">
        <title>Reagle's Planning Page</title>
        <link rel="stylesheet" type="text/css"
        href="../plans/plan.css" />
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
        </div>%s</body></html>"""
        % out_str
    )

    out_fd = codecs.open(out_file, "w", "utf-8", "replace")
    out_fd.write(HTMLPage)
    out_fd.close()

    return out_file


# If the script is from console (main) then open browser.
if __name__ == "__main__":
    query = "".join(sys.argv[1:])
    query_result_file = query_sponge(query)
    # call([BROWSER, query_result_file])
    webbrowser.open("file://" + query_result_file)
