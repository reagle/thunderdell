#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# On Webfaction [1] this script and its parent directory must be chmod 711
# [1]: http://docs.webfaction.com/software/static.html#error-500-internal-server-error

# Main function
def cgi_main():
    global opts
    import codecs, cgi, os, re, sys, urlparse
    from urllib import quote, unquote

    from os.path import expanduser
    HOME = expanduser("~")

    sys.stdout = codecs.getwriter('UTF-8')(sys.__stdout__, errors='replace')

    env = os.environ

    print('Content-Type: text/html; charset=utf-8\n\n')

    form = cgi.FieldStorage()
    charset = form.getfirst('_charset_', 'utf-8')

    query = form.getfirst('query', 'Wikipedia2008npv') # Möller2007ecl
    site = form.getvalue('sitesearch', 'MindMap')
    #query = form.getfirst('query', 'aux2bib')
    #site = form.getvalue('sitesearch', 'BusySponge') 

    query = unquote(query).decode(charset)
    
    if query.startswith('@'):
        query = query[1:]

    if site == "BusySponge":
        sys.path.append(HOME+'/bin')
        import bsq
        query_result_file = bsq.queryBSponge(query)
        fileObj = codecs.open(query_result_file, "r", "utf-8", "replace" )
        print fileObj.read()
        fileObj.close()
    else:
        sys.path.append(HOME+"/bin/fe")
        sys.path.append(HOME+"/bin/lib/python2.7/site-packages/python_dateutil-1.5-py2.7.egg/")
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

        fileObj = codecs.open(fe.TMP_DIR + 'query-thunderdell.html', "r", "utf-8")
        print fileObj.read()
        fileObj.close()

def print_error(msg):
    import sys

    print """<!DOCTYPE HTML PUBLIC "-//W3C//DTD HTML 4.0 Transitional//EN">
    <html>
    <head><title>Error</title></head>
    <body>
    <p>%s</p>
    </body>
    </html>""" % msg
    sys.exit()


if __name__ == '__main__':
    try:
        cgi_main()
    except Exception as e:
        print_error(e)
