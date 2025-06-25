"""Flask app for serving busy_query.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import argparse
import re
from pathlib import Path

from flask import Flask, request

from thunderdell import config
from thunderdell.map2bib import (
    RESULT_FILE_HEADER,
    RESULT_FILE_QUERY_BOX,
    build_bib,
    emit_results,
)

app = Flask(__name__)

INITIAL_FILE_HEADER = """<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html>
<meta content="text/html; charset=utf-8" http-equiv="Content-Type"/>
<title>Reagle's Planning Page</title>
<link rel="stylesheet" type="text/css" href="../plan.css" />
<link rel="icon" type="image/x-icon" href="https://reagle.org/favicon.ico">
</head>
<body xml:lang="en" lang="en">
<div>
    <form method="get" action="/bq">
    <input value="Go" name="Go" type="submit" />
    <input size="25" name="query" maxlength="80" type="text" />
    <input name="sitesearch" value="sponge" type="radio" /> BS
    <input name="sitesearch" checked="checked" value="mindmap" type="radio" /> MM
    </form>
</div>"""


def query_mindmap(args):
    """Query mindmap and generate HTML results string."""
    # This function will now return a string instead of writing to a file
    # We'll capture the output in a list of strings
    output = []
    output.append(RESULT_FILE_HEADER)
    output.append(RESULT_FILE_QUERY_BOX % (args.query, args.query))

    file_name = Path(args.input_file).absolute()
    args.direct_query = True

    # We need a way to capture the output of emit_results
    # Let's create a dummy class that has a write method
    class StringEmitter:
        def __init__(self):
            self.buffer = []

        def write(self, s):
            self.buffer.append(s)

        def get_value(self):
            return "".join(self.buffer)

    string_emitter = StringEmitter()
    args.results_file = string_emitter

    entries = build_bib(args, file_name, emit_results)
    emit_results(args, entries)

    output.append(string_emitter.get_value())
    output.append("</ul></body></html>\n")
    return "".join(output)


def query_busysponge(query):
    """Query items logged to planning page made by busy."""
    in_files = [
        config.HOME / "joseph/plan/index.html",
        config.HOME / "joseph/plan/done.html",
    ]

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

    return f"{INITIAL_FILE_HEADER}{out_str}</body></html>"


@app.route("/bq")
def bq():
    """Query the mindmap or sponge."""
    query = request.args.get("query", "")
    site = request.args.get("sitesearch", "mindmap")

    if not query:
        return "Missing 'query' parameter", 400

    if site == "mindmap":
        args = argparse.Namespace()
        args.query = query
        args.query_c = re.compile(re.escape(query), re.IGNORECASE)
        args.chase = True
        args.input_file = config.DEFAULT_MAP
        args.long_url = False
        args.pretty = False
        return query_mindmap(args)
    else:
        return query_busysponge(query)


if __name__ == '__main__':
    app.run(debug=True, port=8080)
