#!/usr/bin/env python3
"""Unified server for thunderdell queries (mindmap and BusySponge)."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import errno
import http.server
import logging
import os
import re
import sys
import traceback
import urllib.parse
import webbrowser
from pathlib import Path

from thunderdell import config

# Import only necessary functions from map2bib, not HTTP serving parts
from thunderdell.map2bib import (
    RESULT_FILE_HEADER,
    RESULT_FILE_QUERY_BOX,
    build_bib,
    emit_results,
)

# Constants
HTML_HEADER = """<?xml version="1.0" encoding="iso-8859-1"?>
<!DOCTYPE html PUBLIC "-//W3C//DTD XHTML 1.0 Transitional//EN"
"http://www.w3.org/TR/xhtml1/DTD/xhtml1-transitional.dtd">
<html xmlns="http://www.w3.org/1999/xhtml">
<title>Reagle's Planning Page</title>
<link rel="stylesheet" type="text/css" href="../plan.css" />
<link rel="icon" type="image/x-icon" href="https://reagle.org/favicon.ico">
</head>
<body xml:lang="en" lang="en">
<div>
    <form method="get" action="search.cgi">
    <input value="Go" name="Go" type="submit" />
    <input size="25" name="query" maxlength="80" type="text" />
    <input name="sitesearch" value="BusySponge" type="radio" /> BS
    <input name="sitesearch" checked="checked" value="MindMap" type="radio" /> MM
    </form>
</div>"""


def query_mindmap(args):
    """Query mindmap and generate HTML results file."""
    results_file_name = config.TMP_DIR / "query-thunderdell.html"

    if results_file_name.exists():
        results_file_name.unlink()

    try:
        with results_file_name.open(mode="w", encoding="utf-8") as results_file:
            args.results_file = results_file

            # Write HTML header
            results_file.write(RESULT_FILE_HEADER)
            results_file.write(RESULT_FILE_QUERY_BOX % (args.query, args.query))

            # Build and emit results
            file_name = Path(args.input_file).absolute()

            # Set direct_query flag to avoid circular calls
            args.direct_query = True
            entries = build_bib(args, file_name, emit_results)

            # Generate results directly
            emit_results(args, entries)

            # Close HTML
            results_file.write("</ul></body></html>\n")
    except OSError as err:
        print(f"{err}\nThere was an error writing to {results_file_name}")
        raise

    return results_file_name


def query_busysponge(query):
    """Query items logged to planning page made by Busy Sponge."""
    in_files = [
        config.HOME / "joseph/plan/index.html",
        config.HOME / "joseph/plan/done.html",
    ]

    out_file = config.TMP_DIR / "query-sponge-result.html"

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

    HTMLPage = f"{HTML_HEADER}{out_str}</body></html>"
    out_file.write_text(HTMLPage, encoding="utf-8")

    return out_file


def serve_local(port=8000):
    """Start a local HTTP server for development."""
    os.chdir(config.CGI_DIR.parent)
    handler = http.server.CGIHTTPRequestHandler
    handler.cgi_directories = ["/cgi-bin"]

    try:
        server = http.server.HTTPServer(("localhost", port), handler)
        print(f"Starting local server on http://localhost:{port}")
        print("Press Ctrl+C to stop")
        server.serve_forever()
    except OSError as error:
        if error.errno == errno.EADDRINUSE:
            print(f"Port {port} already in use")
        else:
            raise
    except KeyboardInterrupt:
        print("\nServer stopped")


def handle_cgi():
    """Handle CGI requests for a2hosting."""
    # Set stdout encoding for proper UTF-8 output
    sys.stdout.reconfigure(encoding="utf-8")

    # Print HTTP headers
    print("Content-Type: text/html; charset=utf-8\n\n")

    # Get and parse query parameters
    query_string = os.environ.get("QUERY_STRING", "")
    form_data = dict(urllib.parse.parse_qsl(query_string))

    site = form_data.get("sitesearch", "MindMap")
    query = form_data.get("query", "Wikipedia2008npv")
    query = urllib.parse.unquote(query)

    # Remove "@" prefix if present (for citation keys)
    if query.startswith("@"):
        query = query[1:]

    try:
        # Handle site-specific queries
        if site == "BusySponge":
            result_file = query_busysponge(query)
            print(result_file.read_text(encoding="utf-8", errors="replace"))
        else:
            # Set up args for mindmap query
            args = argparse.Namespace()
            args.query = query
            args.query_c = re.compile(re.escape(query), re.IGNORECASE)
            args.chase = True
            args.cgi = True
            args.input_file = config.DEFAULT_MAP
            args.long_url = False
            args.pretty = False

            # Generate results
            query_mindmap(args)

            # Output results
            result_file = config.TMP_DIR / "query-thunderdell.html"
            print(result_file.read_text(encoding="utf-8"))
    except Exception as e:
        print(
            f"<h1>Error</h1><pre>{type(e).__name__}: {e!s}\n\n{traceback.format_exc()}</pre>"
        )


def main():
    """Parse command-line arguments and run in appropriate mode."""
    parser = argparse.ArgumentParser(
        description="Unified server for thunderdell queries"
    )
    parser.add_argument(
        "-l", "--local", action="store_true", help="Run as a local server"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8000,
        help="Port for local server (default: 8000)",
    )
    parser.add_argument("-q", "--query", help="Query string (for CLI mode)")
    parser.add_argument(
        "-s",
        "--site",
        choices=["MindMap", "BusySponge"],
        default="MindMap",
        help="Site to query (default: MindMap)",
    )
    parser.add_argument(
        "-c",
        "--chase",
        action="store_true",
        default=True,
        help="Chase links between MMs",
    )
    parser.add_argument(
        "-b",
        "--browser",
        action="store_true",
        default=False,
        help="Open results in browser (for CLI mode)",
    )
    parser.add_argument(
        "-V",
        "--verbose",
        dest="verbose",
        action="count",
        default=0,
        help="increase verbosity from critical though error, warning, info, and debug",
    )
    parser.add_argument(
        "-L",
        "--log-to-file",
        action="store_true",
        default=False,
        help="log to file td.log",
    )

    args = parser.parse_args()

    log_level = (logging.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    if args.log_to_file:
        print("logging to file")
        logging.basicConfig(
            filename="td.log", filemode="w", level=log_level, format=LOG_FORMAT
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    # Determine execution mode
    if "SCRIPT_NAME" in os.environ:
        # CGI mode (running on web server)
        handle_cgi()
    elif args.local:
        # Local server mode
        serve_local(args.port)
    elif args.query:
        # CLI query mode
        if args.site == "BusySponge":
            result_file = query_busysponge(args.query)
        else:
            query_args = argparse.Namespace()
            query_args.query = args.query
            query_args.query_c = re.compile(re.escape(args.query), re.IGNORECASE)
            query_args.chase = args.chase
            query_args.input_file = config.DEFAULT_MAP
            query_args.long_url = False
            query_args.pretty = False
            result_file = query_mindmap(query_args)

        # Open in browser if requested
        if args.browser:
            webbrowser.open(result_file.as_uri())
        else:
            print(f"Results written to {result_file}")
    else:
        # No valid mode specified
        parser.print_help()


if __name__ == "__main__":
    main()
