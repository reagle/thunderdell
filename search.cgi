#!/usr/bin/env python3

# set shebang locally to latest
# !/usr/bin/env python3
# set the shebang on a2hosting to
# !/home/goateene/opt/bin/python3

import argparse
import traceback
import warnings

warnings.filterwarnings("ignore", category=DeprecationWarning)


def cgi_main(args):
    import cgi
    import codecs
    import logging
    import re
    import sys
    from pathlib import Path
    from urllib.parse import unquote

    HOME = Path.home()
    TMP_DIR = HOME / "tmp" / ".td"
    # http://stackoverflow.com/questions/4374455/how-to-set-sys-stdout-encoding-in-python-3
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    #  https://docs.python.org/3/library/logging.html
    # "Note that the root logger is created with level WARNING."
    # Set level to ERROR here so I don't see warnings imported from
    # thunderdell when running as server.
    # Alternatively, perhaps could name thunderdell logger, so it's not root
    LOG_FORMAT = "%(levelname).3s %(funcName).5s: %(message)s"
    logging.basicConfig(level=logging.ERROR, format=LOG_FORMAT)

    print("Content-Type: text/html; charset=utf-8\n\n")

    # TODO replace cgi with urllib.parse.parse_qsl
    # cgi deprecated in 3.11 https://peps.python.org/pep-0594/#cgi
    form = cgi.FieldStorage()
    query = form.getfirst("query", "Wikipedia2008npv")  # Möller2007ecl
    site = form.getvalue("sitesearch", "MindMap")
    # query = form.getfirst('query', 'aux2bib')
    # site = form.getvalue('sitesearch', 'BusySponge')

    query = unquote(query)

    if query.startswith("@"):
        query = query[1:]

    sys.path.append(str(HOME / "bin/td"))
    if site == "BusySponge":
        import busy_query

        query_result_file = Path(busy_query.query_sponge(query))
        print(query_result_file.read_text(encoding="utf-8", errors="replace"))
        # fileObj = codecs.open(query_result_file, "r", "utf-8", "replace")
        # print(fileObj.read())
        # fileObj.close()
    else:
        MINDMAP = HOME / "joseph/readings.mm"

        import thunderdell as td

        args.query = query
        args.query_c = re.compile(re.escape(query), re.IGNORECASE)
        args.chase = True
        args.cgi = True

        def _ignore(_):
            pass  # this overrides td's logging

        td.critical = _ignore
        td.info = _ignore
        td.dbg = _ignore

        td.build_bib(args, MINDMAP, td.emit_results)

        result_file = TMP_DIR / "query-thunderdell.html"
        print(result_file.read_text(encoding="utf-8"))


def print_error(msg):
    print(
        f"""<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
        <html>
        <head><title>Error</title></head>
        <body>
        <p>{msg}</p>
        </body>
        </html>"""
    )


if __name__ == "__main__":
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
        error_message = f"{type(e).__name__}: {str(e)}"
        full_traceback = traceback.format_exc()
        print_error(f"{error_message=}")
        print_error(f"{full_traceback=}")
