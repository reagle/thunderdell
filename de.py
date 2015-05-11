#!/usr/bin/python2.7
# -*- coding: utf-8 -*-
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2011 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""extract a MM from a dictated text file using particular conventions"""

import os

HOME = os.path.expanduser('~')


def clean(text):
    '''clean and encode text'''
    # TODO: Maybe make use of b.smart_punctuation_to_ascii() and 
    # web_little.escape_XML()
    
    text = text.strip(', \f\r\n')
    REPLACEMENTS = [
        (u'&', '&amp;'),     (u"'", '&apos;'),
        (u'"', '&quot;'),    (u'“', '&quot;'),   (u'”', '&quot;'),
        (u"‘", u"'"),         (u"’", u"'"),
        (u" – ", u" -- "), (u"–", u" -- ")]
        
    for v1, v2 in REPLACEMENTS:
        text = text.replace(v1, v2)
    return text

def get_date():
    import string, time
    now = time.localtime()
    year = time.strftime("%Y",now).lower()
    month = time.strftime("%m",now).lower()
    date_token = time.strftime("%Y%m%d",now)
    return date_token


def parse(line, started, in_part, in_chapter, in_section, in_subsection):

    import re

    author = title = citation = ""
    entry = {}

    #print "*** '%s'" % repr(line)
    if line not in (u'', u'\r' ,u'\n'):
        if line.lower().startswith('author ='):
            # and re.match('([^=]+ = (?=[^=]+)){2,}', line, re.IGNORECASE)
            if started: # Do I need to close a previous entry
                if in_subsection:
                    fdo.write(u"""        </node>\n""")
                    in_subsection = False
                if in_section:
                    fdo.write(u"""      </node>\n""")
                    in_section = False
                if in_chapter:
                    fdo.write(u"""    </node>\n""")
                    in_chapter = False
                if in_part:
                    fdo.write(u"""    </node>\n""")
                    in_part = False

                fdo.write(u"""</node>\n</node>\n""")
                started = False
            started = True
            cites = re.split('(\w+) =',line)[1:] # should space be optional '(\w+) ?='
            # 2 references to an iterable object that are unpacked with '*' and rezipped
            cite_pairs = zip(*[iter(cites)] * 2)
            for token, value in cite_pairs:
                entry[token.lower()] = value.strip()

#             print "*** entry = ", entry
            if 'author' not in entry: entry['author'] = 'Unknown'
            if 'title' not in entry: entry['title'] = 'Untitled'

            fdo.write(u"""<node COLOR="#338800" TEXT="%s" POSITION="RIGHT">\n"""
                    % clean(entry['author'].title()))
            if 'url' in entry:
                fdo.write(u"""  <node COLOR="#090f6b" LINK="%s" TEXT="%s">\n"""
                    % ( clean(entry['url']), clean(entry['title'])))
            else:
                fdo.write(u"""  <node COLOR="#090f6b" TEXT="%s">\n"""
                    % clean(entry['title']))

            #print '***', BIB_FIELDS
            for token, value in sorted(entry.items()):
                if token not in ('author', 'title', 'url'):
                    if token in BIB_SHORTCUTS:
                        t, v = token.lower(),value
                    else:
                        if token.lower() in BIB_FIELDS:
                            t, v = BIB_FIELDS[token.lower()], value
                        else:
                            print "* Unknown token '%s' in %s" %(token, entry['author'])
                            sys.exit
                    citation_add = "%s=%s " %(t,v)
                    citation = citation + citation_add
            if citation != "": clean(citation)
            citation += " r=%s" % get_date()
            fdo.write(u"""  <node COLOR="#ff33b8" TEXT="%s"/>\n"""
                % clean(citation))

        elif re.match('summary\.(.*)', line, re.IGNORECASE):
            matches = re.match('summary\.(.*)',line, re.IGNORECASE)
            fdo.write(u"""  <node COLOR="#999999" TEXT="%s"/>\n"""
                % clean(matches.groups()[0]))

        elif re.match('part.*', line, re.IGNORECASE):
            if in_part:
                if in_chapter:
                    fdo.write(u"""    </node>\n""")      # close chapter
                    in_chapter = False
                if in_section:
                    fdo.write(u"""      </node>\n""")    # close section
                    in_section = False
                if in_subsection:
                    fdo.write(u"""      </node>\n""")    # close section
                    in_subsection = False
                fdo.write(u"""  </node>\n""")            # close part
                in_part = False
            fdo.write(u"""  <node COLOR="#8b12d6" TEXT="%s">\n""" % clean(line))
            in_part = True

        elif re.match('chapter.*', line, re.IGNORECASE):
            if in_chapter:
                if in_section:
                    fdo.write(u"""      </node>\n""")    # close section
                    in_section = False
                if in_subsection:
                    fdo.write(u"""      </node>\n""")    # close section
                    in_subsection = False
                fdo.write(u"""    </node>\n""")            # close chapter
                in_chapter = False
            fdo.write(u"""    <node COLOR="#8b12d6" TEXT="%s">\n""" % clean(line))
            in_chapter = True

        elif re.match('section.*', line, re.IGNORECASE):
            if in_subsection:
                fdo.write(u"""      </node>\n""")    # close section
                in_subsection = False
            if in_section:
                fdo.write(u"""    </node>\n""")
                in_section = False
            fdo.write(u"""      <node COLOR="#8b12d6" TEXT="%s">\n""" % clean(line[9:]))
            in_section = True

        elif re.match('subsection.*', line, re.IGNORECASE):
            if in_subsection:
                fdo.write(u"""    </node>\n""")
                in_subsection = False
            fdo.write(u"""      <node COLOR="#8b12d6" TEXT="%s">\n""" % clean(line[12:]))
            in_subsection = True

        elif re.match('(--.*)', line, re.IGNORECASE):
            fdo.write(u"""          <node COLOR="#000000" TEXT="%s"/>\n"""
                % clean(line))

        elif re.match('(\d+)(\-\d+)? (.*)', line, re.IGNORECASE):
            matches = re.match('(\d+)(\-\d+)? (.*)', line, re.IGNORECASE)
            line_no = matches.group(1)
            if matches.group(2):
                line_no += matches.group(2)
            line_text = matches.group(3)
            if re.match('(.*)(\-\d+)', line_text, re.IGNORECASE):
                matches = re.match('(.*)(\-\d+)', line_text, re.IGNORECASE)
                line_text = matches.group(1)
                line_no += matches.group(2)
            node_color = '#8b12d6'
            if line_text.startswith('excerpt.'):
                node_color = '#166799'
                line_text = line_text[9:]
            if line_text.strip().endswith('excerpt.'):
                node_color = '#166799'
                line_text = line_text[0:-9]
            fdo.write(u"""          <node COLOR="%s" TEXT="%s"/>\n"""
                % (node_color, clean(' '.join((line_no, line_text)))))
        else:
            fdo.write(u"""          <node COLOR="#8b12d6" TEXT="%s"/>\n"""
                % clean(line))

    return started, in_part, in_chapter, in_section, in_subsection


def check(text, fdo):

    import traceback

    started = False
    in_part = False
    in_chapter = False
    in_section = False
    in_subsection = False
    line_number = 0

    fdo.write(u"""<map version="0.7.1">\n<node TEXT="Readings">\n""")

    for line in text.split('\n'):
        try:
            started, in_part, in_chapter, in_section, in_subsection = parse(
                line, started, in_part, in_chapter, in_section, in_subsection)
        except KeyError:
            print traceback.print_tb(sys.exc_traceback), '\n', line_number, line
            sys.exit()
        line_number += 1

    if in_subsection: fdo.write(u"""</node>""") # close the last section
    if in_section: fdo.write(u"""</node>""") # close the last section
    if in_chapter: fdo.write(u"""</node>""") # close the last chapter
    if in_part: fdo.write(u"""</node>""") # close the last part
    fdo.write(u"""</node>\n</node>\n""")  # close the last entry
    fdo.write(u"""</node>\n</map>\n""")   # close the document

#Check to see if the script is executing as main.
if __name__ == "__main__":
## Parse the command line arguments for optional message and files.

    from fe import BIB_SHORTCUTS   # a dict of shotcuts yeilding a field
    from fe import BIB_FIELDS      # a dict of a field yielding its shortcut

    import chardet, codecs, getopt, os, subprocess, sys

    try:
        (options,files) = getopt.getopt (sys.argv[1:],"")
    except getopt.error:
        print 'Error: Unknown option or missing argument.'
    files = [os.path.abspath(file) for file in files]
    for file in files:
        if file.endswith('.rtf'):
            subprocess.call(['/usr/bin/X11/catdoc', '-aw', file],
                stdout=open('%s.txt' % file[0:-4], 'w'))
            file = file[0:-4] + '.txt'
        try:
            encoding = 'UTF-8'
            #encoding = chardet.detect(open(file).read())['encoding']
            fdi = codecs.open(file, "rb", encoding)
            text = fdi.read()
            if encoding == 'UTF-8':
                if text[0] == unicode( codecs.BOM_UTF8, "utf8" ):
                    text = text[1:]
                    print "removed BOM"
            # it's not decoding MS Word txt correctly, word is not starting with
            # utf-8 even though I set to default if no special characters
            # write simple Word txt to UTF-8 encoder
            fileOut = os.path.splitext(file)[0] + '.mm'
            fdo = codecs.open(fileOut, "wb", "utf-8")
            sys.stdout = codecs.getwriter('UTF-8')(sys.__stdout__, errors='replace')
        except IOError:
            print "    file does not exist"
            continue

        check(text, fdo)
        subprocess.call([HOME+'/bin/freemind/freemind.sh', fileOut])
