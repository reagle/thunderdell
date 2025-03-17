#!/usr/bin/env python3
"""CGI/web wrapper for thunderdell and busysponge."""

# set shebang locally to latest
# !/usr/bin/env python3
# set the shebang on a2hosting to
# !/home/goateene/opt/bin/python3

import argparse
import logging
import os
import re
import sys
import traceback
import urllib.parse as up
from pathlib import Path

HOME = Path.home()
TD_DIR = HOME / "bin" / "td"
TMP_DIR = HOME / "tmp" / ".td"
sys.path.append(str(TD_DIR))
sys.stdout.reconfigure(encoding="utf-8")


def cgi_main(args):
    """CGI main function."""
    # set stdout encoding for subsequent print commands

    #  https://docs.python.org/3/library/logging.html
    # "Note that the root logger is created with level WARNING."
    # Set level to ERROR here so I don't see warnings imported from
    # thunderdell when running as server.
    # Alternatively, perhaps could name thunderdell logger, so it's not root
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    logging.basicConfig(level=logging.ERROR, format=LOG_FORMAT)

    print("Content-Type: text/html; charset=utf-8\n\n")

    # Get the query string
    query_string = os.environ.get("QUERY_STRING", "")

    # Parse the query string
    form_data = dict(up.parse_qsl(query_string))

    # Access form data
    site = form_data.get("sitesearch", "MindMap")
    query = form_data.get("query", "Wikipedia2008npv")

    query = up.unquote(query)

    # citation keys might start with "@", remove if so
    if query.startswith("@"):
        query = query[1:]

    # site specific queries
    if site == "BusySponge":
        import thunderdell.busy_query

        query_result_file = Path(busy_query.query_sponge(query))
        print(query_result_file.read_text(encoding="utf-8", errors="replace"))
    else:
        MINDMAP = HOME / "joseph" / "readings.mm"

        import thunderdell as td

        args.query = query
        args.query_c = re.compile(re.escape(query), re.IGNORECASE)
        args.chase = True
        args.cgi = True

        td.build_bib(args, MINDMAP, td.emit_results)

        result_file = TMP_DIR / "query-thunderdell.html"
        print(result_file.read_text(encoding="utf-8"))


def print_error(msg):
    """Wrap error message in HTML page."""
    print(
        f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
        <html>
        <head><title>Error</title></head>
        <body>
        <p>{msg}</p>
        </body>
        </html>"""
    )


def main():
    import sys

    arg_parser = argparse.ArgumentParser()
    arg_parser.add_argument("--in_main", action="store_true", default=False)
    arg_parser.add_argument("-c", "--chase", action="store_true", default=True)
    arg_parser.add_argument("-l", "--long_url", action="store_true", default=False)
    arg_parser.add_argument("-p", "--pretty", action="store_true", default=False)
    arg_parser.add_argument("-q", "--query", action="store_true", default=None)
    args = arg_parser.parse_args()

    try:
        cgi_main(args)
    except Exception as e:  # noqa: BLE001
        error_message = f"{type(e).__name__}: {e!s}"
        full_traceback = traceback.format_exc()
        print_error(f"{error_message=}")
        print_error(f"{full_traceback=}")


if __name__ == "__main__":
    main()
