#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Search freemind mindmaps for text"""

import codecs, getopt, re, os, sys


def walk_freemind(doc,query,links=[]):
    """Walk the freemind XML tree and serach for query"""
    # <node LINK="a.mm" TEXT="A"/>

    import re

    for child in doc:
        if 'LINK' in child():                   # found a local reference link
            if not child('LINK').startswith('http:') and child('LINK').endswith('.mm'):
                links.append(child('LINK'))
#                 print "*** appending", child('LINK')
        if 'TEXT' in child():
            cq = re.compile(query)
            if cq.search(child('TEXT')):
                author = child._parent._parent('TEXT')
                title = child._parent._parent[0]('TEXT')
                cite = child._parent[0]('TEXT')
                print author, ":", title, ":", cite
                print child('TEXT'), "\n"
#            if child('COLOR') == "#338800":     # author
#            elif child('COLOR') == "#090f6b":   # title
#            elif child('COLOR') == "#ff33b8":   # cite

        if len(child) >= 0:
            walk_freemind(child,query,links)
    return links


def open_mm(file,chase):

    import xmltramp     # http://www.aaronsw.com/2002/xmltramp/
    links = []          # a list of other files encountered in the mind map
    done = []           # list of files processed, kept to prevent loops
    bfiles = []
    bfiles.append(file)  # a list of file encountered (e.g., chase option)
    for bfile in bfiles:
#         print "### checking %s in %s where %s is done\n" %(bfile,bfiles,done)
        if bfile in done:
#            print "    already processed", bfile
            continue
        else:
            try:
#                print "    trying to open", bfile
                content = open(bfile, "rb").read()
            except IOError,err:
#                print "    ", err
                continue
            doc = xmltramp.parse(content)
            links = walk_freemind(doc,query,links=[])
#            print "    **** links is", links
            if chase:
                for link in links:
#                    print "      os.path.dirname(bfile)", os.path.dirname(bfile)
                    link = os.path.abspath(os.path.dirname(bfile) + '/' +link)
                    if link not in done:
#                        print "   adding for chasing", link
                        bfiles.append(link)
#            print "   done with ", bfile
            done.append(os.path.abspath(bfile))


#Check to see if the script is executing as main.
if __name__ == "__main__":
## Parse the command line arguments for optional message and files.

    chase = False           # Don't follow freemind links to other local maps
    query = "Reagle"        # default test value

    try:
        (options,files) = getopt.getopt (sys.argv[1:],"q:c")
    except getopt.error:
        print 'Error: Unknown option or missing argument.'
        print '''fs -q (query) -c (chase hyperlinks)'''
        sys.exit()
    if len(files) > 1: print "Warning: ignoring all files but the first"
    file = os.path.abspath(files[0])

    sys.stdout = codecs.getwriter('UTF-8')(sys.__stdout__, errors='replace')
    # change sys.stdout into an object, convert data into UTF-8, and
    # print that to stdout with (no) unencodable characters replaced with '?'.

    for (option,value) in options:
        if option == '-c':
            chase = True
        if option == '-q':
            query = value
    open_mm(file,chase)