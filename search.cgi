#!/usr/bin/env python2.6
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
        #os.remove('/tmp/query-sponge-result.html')
    else:
        sys.path.append("/home/reagle/bin/fe")
        import fe
        file = ('/home/reagle/data/2web/reagle.org/joseph/readings.mm')
        output = fe.emit_results
        fe.opts.query = query
        fe.opts.query_c = re.compile(re.escape(query), re.IGNORECASE)
        fe.opts.chase = True
        fe.opts.cgi = True

        fe.build_bib(file, output)

        fileObj = codecs.open('/tmp/query-thunderdell.html', "r", "utf-8")
        print fileObj.read()
        fileObj.close()
        #os.remove('/tmp/query-%s.html' % fe.opts.query)
    #except Exception, error:
            #print_error(error)
            #raise

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

