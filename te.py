#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2015 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""parse inconsistently formatted bibliographies into a Freemind minmap"""

def clean_xml(text):
    """Remove entities and remove spurious whitespace"""

    if text != None:
        text = text.replace('&', '&amp;').replace('"', '&quot;').replace("'", '&apos;')
        text = text.strip()
    return text

def fix_authors(authors):
    import string

    authors = string.replace(authors, ' and ', ', ')
    s_authors = authors.split(',')
    if len(s_authors) > 1:
        authors = s_authors[1].strip() + ' ' + s_authors[0].strip()
        for name in s_authors[2:]:
            authors = authors + ', ' + name.strip()
    return authors

def parse(line):


    import re
    from fe import terms_reverse    # a dict of a term yielding its token

    formats = (

        ('f1  a (y) t, j, v(n), p',
        r"""(.*?)\((\d\d\d\d)\)?\.? ?"(.*?)" ?(.*?)(\d+)\((\d+)\)?: (?:pp\.? )?(\d+-?\d+)""",
        ['author', 'year','title','journal','volume','number','pages']),

    
        ('j1  a (y) "t." j v(n): p',
        r"""(.*?)\((\d\d\d\d)\)?\.? ?"(.*?)" ?(.*?)(\d+)\((\d+)\)?: (?:pp\.? )?(\d+-?\d+)""",
        ['author', 'year','title','journal','volume','number','pages']),

        ('j2  a. y "t" j v(n): p',
        r"""(.*\.) ?(\d\d\d\d). ?"(.*?)" (.*?) (\d+)\((\d+)\): ?(?:pp\.? )?(\d+-?\d+)""",
        ['author', 'year','title','journal','volume','number','pages']),


        ('j3  a (y) t. j v(n): p',  # same as above without quotes around title
        r"""(.*?)\((\d\d\d\d)\)\. ?(.*?)\. ?(.*?)(\d+)\((\d+)\)?: (?:pp\.? )?(\d+-?\d+)""",
        ['author', 'year','title','journal','volume','number','pages']),


        ('j3.1  a (y) t. j, v, n, p',  # same as above but pages follow comma
        r"""(.*?)\((\d\d\d\d)\)\. ?(.*?)\. ?(.*?), (\d+), (\d+-\d+)\.""",
        ['author', 'year','title','journal','volume','pages']),

#         Alison, Turner (Oct., 2003). Blogging with NeLH. Health Information on the Internet, 35(1), 10-11. Abstract: A brief account of setting up a collaborative weblog, as part of a virtual support network for librarians and trainers.
        
        ('j3.2  a (y). t. j, v(n), p. Abstract: ',  # has an abstract!
        r"""(.*?)\((.*?)\)\. ?(.*?)\. ?(.*?), (\d+)\((\d+)\), ?(\d+-?\d+)\. Abstract: (.*?)\.""",
        ['author', 'year','title','journal','volume','pages','annote']),

#         ('j3.3  a (y). t. j, v(n), p. Abstract: ',  # catch all
#         r"""(.*?)\((.*?)\)\. ?(.*?)\. ?(.*?) (.*)""",
#         ['author', 'year','title','journal','annote']),

                
        ('j4  a y. t. j, v(n): p',
        r"""(.*?) ?(\d\d\d\d). ?(.*?)\. ?(.*?)\, ?(\d+)(\(\d\))?: ?(\d+-?\d+)""",
        ['author', 'year','title','journal','volume','number','pages']),

        ('j4.1 a y t. j v(n): p', # same but
        r"""(.*?) ?(\d\d\d\d)\.? (.*?)\. (.*?) ?(\d+)(\(\d\))?: (\d+-?\d+)""",
        ['author', 'year','title','journal','volume','number','pages']),

        ('b1  a(y)t.a,:p',
        r"""(.*?)\((\d\d\d\d)\)\.? ?"?(.*?)\."? ?(.*?)(?::|,) (.*)""",
        ['author','year','title','address','publisher'] ),

        ('b2  a"t"b.e.a:p,y,p',
        r"""(.*?)\. ?"(.*)" (.*?)\. (.*?(?:\(eds\.\) ))?(.*?): (.*?), (\d\d\d\d)(?:, (\d+-?\d+))?""",
        ['author','title','booktitle','editor','address','publisher','year','pages']),

        ('b2.1 a"t"b.e.a:p,y,p',
        r"""(.*?)\. ?"(.*)", in (.*?)\(eds.\) ?(.*?), (.*?): (.*?), (\d\d\d\d)""",
        ['author','title','booktitle','editor','address','publisher','year']),

        ('b2.2 a (eds.) y t. a:p',
        r"""(.*?) \(eds.\)\. ?(\d\d\d\d)\.? ?"?(.*?)\."? ?(.*?)(?::|,) (.*)""",
        ['author','year','title','address','publisher']),

        ('b3 a. "t" bt, p, a, y',
        r"""(.*?) "(.*?)" (.*?), (.*?), (.*?), (\d\d\d\d)""",
        ['author','title','booktitle','publisher','address','year']),


        ('j5  a"t"j,v,n,myp',
        r"""(.*?)\. ?"(.*)" (.*?), (\d+), (\d+), (\d\d\d\d): (\d+-?\d+)""",
        ['author','title','journal','volume','number','year','pages'] ),

        ('j5.1 a"t"j,v,n,myp',  # without number
        r"""(.*?)\. ?"(.*)" (.*?), (\d+), ?(\d\d\d\d): (\d+-?\d+)""",
        ['author','title','journal','volume','year','pages'] ),


        ('j6 a."t"j,v,n,y:p',
        r"""(.*). "(.*?)" (.*?),? ?(\d+), ?(\d+)(?::|,) ?(\d\d\d\d)(?::|,) ?(\d+-?\d+)""",
        ['author','title','journal','volume','number','year','pages']),


        ('j7  a."t" j (v:n) y, pp p.',
        r"""(.*). "(.*?)," ?(.*?) \((\d+):(\d+)\),?( \w+)? ?(\d\d\d\d), (?:p+)? (\d+-?\d+)""",
        ['author','title','journal','volume','number','month','year','pages']),

        ('j7.71 a."t" j (v:n) y, pp p.',    # when there's no number
        r"""(.*). "(.*?)," ?(.*?) \((\d+)\),?( \w+)? ?(\d\d\d\d), (?:p+)? (\d+-?\d+)""",
        ['author','title','journal','volume','month','year','pages']),


        ('j8  a."t" j m? y',
        r"""(.*). "(.*?)" (.*?). (\w+) (\d\d\d\d)""",
        ['author','title','journal','month','year']),


        ('j9',
        r"""(.*?) \((\d\d\d\d)\)\.? ?"(.*?)" (.*?)\. (.*).""",
        ['author','year','title','journal','custom1']),

        ('j10',
        r"""(.*?) (\d\d\d\d)\.? ?"?(.*?)"? (.*)""",
        ['author','year','title','custom1']),

    )

#     print "*** '%s'" % line
    line = line.strip()
    for id,query,terms in formats:
#         print "    trying", id
        compile_obj = re.compile(query)
        match_obj = compile_obj.match(line)
        if not match_obj:
            continue
#         print "match on", id
        match_group = match_obj.groups()
        author = title = bib = ""
        for term in terms:
            index = terms.index(term)
            value = clean_xml(match_group[index])
            if term == 'author':
                authors = value
                authors = fix_authors(value)
                sys.stdout.write("""<node COLOR="#338800" TEXT="%s" POSITION="left">\n""" % authors)
            elif term == 'title':
                sys.stdout.write("""<node COLOR="#090f6b" TEXT="%s" POSITION="left">\n""" % value)
            else:
                if value != None:
                    bib = bib + "%s=%s " %(terms_reverse[term],value.strip()) # terms or terms reverse? 051219
        bib = bib.strip()
        sys.stdout.write("""<node COLOR="#ff33b8" TEXT="%s" POSITION="left"/>\n""" %bib)
        sys.stdout.write("""</node>\n</node>\n""")
        return
#     else:
#         if line != '': print "no good", line


def check(fd):
    sys.stdout.write("""<map version="0.7.1">\n<node TEXT="Readings">\n""")

    for line in fd:
        parse(line)

    sys.stdout.write("""</node>\n</map>\n""")

#Check to see if the script is executing as main.
if __name__ == "__main__":
## Parse the command line arguments for optional message and files.

    import codecs, getopt, os, sys
    sys.stdout = codecs.getwriter('UTF-8')(sys.__stdout__, errors='replace')
    # change sys.stdout into an object, convert data into UTF-8, and
    # print that to stdout with (no) unencodable characters replaced with '?'.

    try:
        (options,files) = getopt.getopt (sys.argv[1:],"")
    except getopt.error:
        print 'Error: Unknown option or missing argument.'
    files = [os.path.abspath(file) for file in files]
    for file in files:
        try:
            fd = codecs.open(file, "rb", "utf-8", "replace")
        except IOError:
            print "    file does not exist"
            continue
        check(fd)
