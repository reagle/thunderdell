#!/usr/bin/env python3
# -*- coding: utf-8 -*-

# set shebang locally to
#!/usr/bin/env python3.8
# set the shebang on a2hosting to
#!/home/goateene/opt/bin/python3


def cgi_main():
    global args
    import codecs, cgi, os, re, sys
    from urllib.parse import quote, unquote

    HOME = os.path.expanduser("~")

    # http://stackoverflow.com/questions/4374455/how-to-set-sys-stdout-encoding-in-python-3
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    env = os.environ

    print("Content-Type: text/html; charset=utf-8\n\n")

    form = cgi.FieldStorage()
    charset = form.getfirst("_charset_", "utf-8")

    query = form.getfirst("query", "Wikipedia2008npv")  # Möller2007ecl
    site = form.getvalue("sitesearch", "MindMap")
    # query = form.getfirst('query', 'aux2bib')
    # site = form.getvalue('sitesearch', 'BusySponge')

    query = unquote(query)

    if query.startswith("@"):
        query = query[1:]

    sys.path.append(HOME + "/bin/td")
    if site == "BusySponge":
        import busy_query

        query_result_file = busy_query.query_sponge(query)
        fileObj = codecs.open(query_result_file, "r", "utf-8", "replace")
        print((fileObj.read()))
        fileObj.close()
    else:
        MINDMAP = HOME + "/joseph/readings.mm"

        import thunderdell as td

        output = td.emit_results
        td.args.query = query
        td.args.query_c = re.compile(re.escape(query), re.IGNORECASE)
        td.args.chase = True
        td.args.cgi = True

        def _ignore(_):
            pass  # this overrides td's logging

        td.critical = _ignore
        td.info = _ignore
        td.dbg = _ignore

        td.build_bib(MINDMAP, output)

        fileObj = codecs.open(td.TMP_DIR + "query-thunderdell.html", "r", "utf-8")
        print((fileObj.read()))
        fileObj.close()


def print_error(msg):
    import sys

    print(
        (
            """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
        <html>
        <head><title>Error</title></head>
        <body>
        <p>%s</p>
        </body>
        </html>"""
            % msg
        )
    )
    sys.exit()


if __name__ == "__main__":
    try:
        cgi_main()
    except Exception as e:
        print_error(e)
