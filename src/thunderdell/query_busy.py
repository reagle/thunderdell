#!/usr/bin/env python3
"""Unified server for thunderdell queries (mindmap and sponge) using Flask.

This module can be run as a local web server or as a command-line tool.
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse
import logging
import re
import socket
import subprocess
import sys
import time
import urllib.parse
import webbrowser
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
    <form method="get" action="/joseph/plan/qb/">
    <input value="Go" name="Go" type="submit" />
    <input size="25" name="query" maxlength="80" type="text" />
    <input name="sitesearch" value="sponge" type="radio" /> BS
    <input name="sitesearch" checked="checked" value="mindmap" type="radio" /> MM
    </form>
</div>"""


def query_mindmap(args):
    """Query mindmap and generate HTML results string."""
    output = []
    output.append(RESULT_FILE_HEADER)
    output.append(RESULT_FILE_QUERY_BOX % (args.query, args.query))

    file_name = Path(args.input_file).absolute()
    args.direct_query = True

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


@app.route("/joseph/plan/qb/")
def qb():
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


def is_port_in_use(port: int) -> bool:
    """Check if a TCP port is in use on localhost."""
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(0.1)
        return sock.connect_ex(("127.0.0.1", port)) == 0


def open_browser_silent(url: str) -> None:
    """Open browser without showing stderr messages."""
    import os
    import platform

    system = platform.system()
    with open(os.devnull, "w") as devnull:  # noqa: PTH123
        if system == "Darwin":  # macOS
            subprocess.Popen(["open", url], stderr=devnull)
        elif system == "Linux":
            subprocess.Popen(["xdg-open", url], stderr=devnull)
        elif system == "Windows":
            subprocess.Popen(
                ["cmd", "/c", "start", "", url], stderr=devnull, shell=True
            )
        else:
            # Fallback to webbrowser for unknown systems
            webbrowser.open(url)


def process_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Parse command-line arguments and return Namespace."""
    parser = argparse.ArgumentParser(
        description="Unified server for thunderdell queries"
    )
    parser.add_argument(
        "-p",
        "--port",
        type=int,
        default=8080,
        help="Port for local server (default: 8080)",
    )
    parser.add_argument("-q", "--query", help="Query string (for CLI mode)")
    parser.add_argument(
        "-s",
        "--site",
        choices=["mindmap", "sponge"],
        default="mindmap",
        help="Site to query (default: mindmap)",
    )
    parser.add_argument(
        "-c",
        "--chase",
        action="store_true",
        default=True,
        help="Chase links between mindmaps",
    )
    parser.add_argument(
        "--server",
        action="store_true",
        help="Run the Flask web server (for internal use).",
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

    args = parser.parse_args(argv)
    return args


def main(argv: list[str] | None = None):
    """Detect running mode."""
    args = process_arguments(argv)

    log_level = (logging.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname)s:%(name)s:%(message)s"
    if args.log_to_file:
        print("logging to file")
        logging.basicConfig(
            filename="td.log", filemode="w", level=log_level, format=LOG_FORMAT
        )
    else:
        root_logger = logging.getLogger()
        if root_logger.hasHandlers():
            root_logger.handlers.clear()
        logging.basicConfig(level=log_level, format=LOG_FORMAT, stream=sys.stderr)

    logging.debug(f"Arguments parsed: {args}")

    if args.server:
        # Internal mode to run the server process
        app.run(debug=True, port=args.port)

    elif args.query:
        # CLI/client mode
        if not is_port_in_use(args.port):
            logging.info(f"Server not running on port {args.port}. Starting it.")
            command = [sys.executable, __file__, "--server", f"--port={args.port}"]
            subprocess.Popen(command, close_fds=True)
            logging.info(f"Server process started with command: {' '.join(command)}")
            time.sleep(2)  # Give server time to start
        else:
            logging.info(f"Server already running on port {args.port}.")

        query_encoded = urllib.parse.quote(args.query)
        url = f"http://127.0.0.1:{args.port}/joseph/plan/qb/?query={query_encoded}&sitesearch={args.site}"
        print(f"Opening browser to: {url}")
        open_browser_silent(url)

    else:
        # Default behavior: start server in foreground
        logging.info(f"Starting Flask server on port {args.port}")
        app.run(debug=True, port=args.port)


if __name__ == "__main__":
    main()
