#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-

# Main function
def cgi_main():
    global opts
    import codecs, cgi, os, re, sys, urlparse
    from urllib import quote, unquote

    sys.stdout = codecs.getwriter('UTF-8')(sys.__stdout__, errors='replace')

    env = os.environ
    #debug = True

    print 'Content-Type: text/html; charset=utf-8\n\n'

    form = cgi.FieldStorage()
    charset = form.getfirst('_charset_', 'utf-8')
    #print "** charset", charset
    query = form.getfirst('query', 'Wikipedia2008npv') # Möller2007ecl
    query = unquote(query).decode(charset)
    #print "** post query", type(query), query

    site = form.getvalue('sitesearch', 'MindMap') # todo: getlist

    #try:
    if site == "BusySponge":
        sys.path.append('/home/reagle/bin')
        import bsq
        query_result_file = bsq.queryBSponge(query)
        fileObj = codecs.open(query_result_file, "r", "utf-8", "replace" )
        print fileObj.read()
        fileObj.close()
    else:
        sys.path.append("/home/reagle/bin/fe")
        sys.path.append("/home/reagle/bin/lib/python2.7/site-packages/python_dateutil-1.5-py2.7.egg/")
        MINDMAP = ('/home/reagle/data/2web/reagle.org/joseph/readings.mm')

        import fe
        output = fe.emit_results
        fe.opts.query = query
        fe.opts.query_c = re.compile(re.escape(query), re.IGNORECASE)
        fe.opts.chase = True
        fe.opts.cgi = True

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
    cgi_main()
    