#!/usr/bin/env python3
"""Unified server for thunderdell queries (mindmap and BusySponge)."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
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
    logging.info("Starting query_mindmap")
    results_file_name = config.TMP_DIR / "query-thunderdell.html"

    if results_file_name.exists():
        logging.debug(f"Removing existing results file {results_file_name}")
        results_file_name.unlink()

    try:
        with results_file_name.open(mode="w", encoding="utf-8") as results_file:
            args.results_file = results_file

            logging.debug("Writing HTML header")
            results_file.write(RESULT_FILE_HEADER)
            results_file.write(RESULT_FILE_QUERY_BOX % (args.query, args.query))

            file_name = Path(args.input_file).absolute()
            logging.debug(f"Building bibliography from {file_name}")

            args.direct_query = True
            entries = build_bib(args, file_name, emit_results)

            logging.debug("Emitting results")
            emit_results(args, entries)

            logging.debug("Closing HTML")
            results_file.write("</ul></body></html>\n")
    except OSError as err:
        logging.error(f"Error writing to {results_file_name}: {err}")
        raise

    logging.info(f"query_mindmap completed, results at {results_file_name}")
    return results_file_name


def query_busysponge(query):
    """Query items logged to planning page made by Busy Sponge."""
    logging.info(f"Starting query_busysponge with query: {query}")
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
        logging.debug(f"Reading file {file}")
        content = file.read_text(encoding="utf-8", errors="replace")
        lis = li_pattern.findall(content)
        for li in lis:
            if query_pattern.search(li):
                logging.debug(f"Match found in list item: {li[:60]}...")
                out_str += li

    if out_str:
        out_str = f"<ol>{out_str}</ol>"
    else:
        logging.info(f"No results found for query '{query}'")
        out_str = f"<p>No results for query '{query}'</p>"

    HTMLPage = f"{HTML_HEADER}{out_str}</body></html>"
    out_file.write_text(HTMLPage, encoding="utf-8")
    logging.info(f"query_busysponge completed, results at {out_file}")

    return out_file


def serve_local(port=8000):
    """Create and return an HTTPServer instance."""
    logging.info(f"Starting local server on port {port}")
    os.chdir(config.CGI_DIR.parent)
    handler = http.server.CGIHTTPRequestHandler
    handler.cgi_directories = ["/cgi-bin"]

    server = http.server.HTTPServer(("localhost", port), handler)
    return server


def handle_cgi():
    """Handle CGI requests for a2hosting."""
    logging.info("Handling CGI request")
    # Set stdout encoding for proper UTF-8 output
    sys.stdout.reconfigure(encoding="utf-8")  # type: ignore

    # Print HTTP headers
    print("Content-Type: text/html; charset=utf-8\n\n")

    # Get and parse query parameters
    query_string = os.environ.get("QUERY_STRING", "")
    logging.debug(f"QUERY_STRING: {query_string}")
    form_data = dict(urllib.parse.parse_qsl(query_string))

    site = form_data.get("sitesearch", "MindMap")
    query = form_data.get("query", "Wikipedia2008npv")
    query = urllib.parse.unquote(query)
    logging.info(f"Site: {site}, Query: {query}")

    # Remove "@" prefix if present (for citation keys)
    if query.startswith("@"):
        query = query[1:]
        logging.debug("Removed '@' prefix from query")

    try:
        # Handle site-specific queries
        if site == "BusySponge":
            logging.info("Querying BusySponge")
            result_file = query_busysponge(query)
            print(result_file.read_text(encoding="utf-8", errors="replace"))
        else:
            logging.info("Querying MindMap")
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
        logging.error(f"Exception in handle_cgi: {e}", exc_info=True)
        print(
            f"<h1>Error</h1><pre>{type(e).__name__}: {e!s}\n\n{traceback.format_exc()}</pre>"
        )


import socket
import threading
import time


def is_port_in_use(port: int) -> bool:
    """Check if a TCP port is in use on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.5)
        result = sock.connect_ex(("localhost", port))
        return result == 0


def start_server_in_thread(port: int) -> threading.Thread:
    """Start the local server in a background thread."""
    server = serve_local(port)

    def run_server():
        logging.info(f"Server thread starting on port {port}")
        try:
            server.serve_forever()
        except Exception as e:
            logging.error(f"Server error: {e}", exc_info=True)
        logging.info("Server thread exiting")

    server_thread = threading.Thread(target=run_server, daemon=True)
    server_thread.start()
    return server_thread


def wait_for_port(port: int, timeout=5.0):
    """Wait until the port is open or timeout."""
    import socket
    import time

    start = time.time()
    while time.time() - start < timeout:
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.settimeout(0.5)
            if sock.connect_ex(("localhost", port)) == 0:
                return True
        time.sleep(0.1)
    return False


def main():
    """Parse command-line arguments and run in appropriate mode."""
    logging.info("Starting main()")
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

    logging.debug(f"Arguments parsed: {args}")

    # Determine execution mode
    if "SCRIPT_NAME" in os.environ:
        logging.info("Detected CGI environment")
        # CGI mode (running on web server)
        handle_cgi()
    elif args.local:
        logging.info("Running in local server mode")
        # Local server mode
        server = serve_local(args.port)
        try:
            logging.info(f"Serving local server on port {args.port}")
            server.serve_forever()
        except KeyboardInterrupt:
            logging.info("Server stopped by user")
            print("\nServer stopped")
    elif args.query:
        logging.info(f"Running CLI query mode with query: {args.query}")
        # CLI query mode
        if args.site == "BusySponge":
            logging.info("Querying BusySponge site")
            result_file = query_busysponge(args.query)
            if args.browser:
                logging.info("Opening results in browser")
                webbrowser.open(result_file.as_uri())
            else:
                logging.info(f"Results written to {result_file}")
                print(f"Results written to {result_file}")
        else:
            logging.info("Querying MindMap site")

            # Check if local server is running on the specified port
            if not is_port_in_use(args.port):
                logging.info(
                    f"Local server not running on port {args.port}, starting it"
                )
                start_server_in_thread(args.port)
                if not wait_for_port(args.port, timeout=10):
                    logging.error(
                        f"Server did not start listening on port {args.port} within timeout"
                    )
                    sys.exit(1)
            else:
                logging.info(f"Local server already running on port {args.port}")

            # Open browser to local server CGI with query
            query_encoded = urllib.parse.quote(args.query)
            url = (
                f"http://localhost:{args.port}/cgi-bin/search.cgi?query={query_encoded}"
            )
            logging.info(f"Opening browser to {url}")
            webbrowser.open(url)
    else:
        logging.warning("No valid mode specified, printing help")
        # No valid mode specified
        parser.print_help()


if __name__ == "__main__":
    main()
