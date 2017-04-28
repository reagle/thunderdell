#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-

# On Webfaction [1] this script and its parent directory must be chmod 711
# [1]: http://docs.webfaction.com/software/static.html#error-500-internal-server-error
# On Webfaction env python3 = python3.2; so I must set 3.5 on the shebang above

def cgi_main():
    global opts
    import codecs, cgi, os, re, sys
    from urllib.parse import quote, unquote

    from os.path import expanduser
    HOME = expanduser("~")

    # http://stackoverflow.com/questions/4374455/how-to-set-sys-stdout-encoding-in-python-3
    sys.stdout = codecs.getwriter("utf-8")(sys.stdout.detach())

    env = os.environ

    print('Content-Type: text/html; charset=utf-8\n\n')

    form = cgi.FieldStorage()
    charset = form.getfirst('_charset_', 'utf-8')

    query = form.getfirst('query', 'Wikipedia2008npv') # Möller2007ecl
    site = form.getvalue('sitesearch', 'MindMap')
    #query = form.getfirst('query', 'aux2bib')
    #site = form.getvalue('sitesearch', 'BusySponge') 

    query = unquote(query) 

    if query.startswith('@'):
        query = query[1:]

    if site == "BusySponge":
        sys.path.append(HOME+'/bin')
        import bsq
        query_result_file = bsq.queryBSponge(query)
        fileObj = codecs.open(query_result_file, "r", "utf-8", "replace" )
        print((fileObj.read()))
        fileObj.close()
    else:
        sys.path.append(HOME+"/bin/fe")
        MINDMAP = (HOME+'/data/2web/reagle.org/joseph/readings.mm')

        import fe
        output = fe.emit_results
        fe.opts.query = query
        fe.opts.query_c = re.compile(re.escape(query), re.IGNORECASE)
        fe.opts.chase = True
        fe.opts.cgi = True
        
        def _ignore(_): pass # this overrides fe's logging
        fe.critical = _ignore
        fe.info =  _ignore
        fe.dbg =  _ignore

        fe.build_bib(MINDMAP, output)

        fileObj = codecs.open(fe.TMP_DIR + 'query-thunderdell.html', 
                              "r", "utf-8")
        print((fileObj.read()))
        fileObj.close()

def print_error(msg):
    import sys

    print((
        """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
        <html>
        <head><title>Error</title></head>
        <body>
        <p>%s</p>
        </body>
        </html>""" % msg))
    sys.exit()


if __name__ == '__main__':
    try:
        cgi_main()
    except Exception as e:
        print_error(e)
