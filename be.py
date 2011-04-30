#!/usr/bin/env python2.6
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Convert a bibtex file into a mindmap."""

import re
import sys

def regexParse(text):

    entries = {}
    key_pat = re.compile('@\w+{(.*),')
    value_pat = re.compile('[ ]+(\w+) = {(.*)},')
    for line in text:
        key_match = key_pat.match(line)
        if key_match:
            key = key_match.group(1)
            entries[key] = {}
            continue
        value_match = value_pat.match(line)
        if value_match:
            field, value = value_match.groups()
            entries[key][field] = value
    return entries

def xml_escape(text):
    """Remove entities and spurious whitespace"""
    import cgi

    escaped_text = cgi.escape(text, quote=True).strip()
    return escaped_text

def process(entries):

    print entries
    fdo.write("""<map version="0.7.2">\n<node TEXT="Readings">\n""")

    for entry in entries.values():
        cite = []
        names = xml_escape(entry['author'])
        fdo.write("""  <node COLOR="#338800" TEXT="%s">\n""" \
            % names)

        if 'url' in entry:
            fdo.write("""    <node COLOR="#090f6b" LINK="%s" TEXT="%s">\n""" \
                % (xml_escape(entry['url']),xml_escape(entry['title'])))
        else:
            fdo.write("""    <node COLOR="#090f6b" TEXT="%s">\n""" \
                % xml_escape(entry['title']))

        # it would be more elegant to just loop through
        #   `from fe import terms`
        # but this creates an ordering that I like
        if 'year' in entry:
            cite.append(('y',entry['year']))
        if 'month' in entry:
            cite.append(('m',entry['month']))
        if 'booktitle' in entry:
            cite.append(('bt',entry['booktitle']))
        if 'editor' in entry:
            cite.append(('e',entry['editor']))
        if 'publisher' in entry:
            cite.append(('p',entry['publisher']))
        if 'address' in entry:
            cite.append(('a',entry['address']))
        if 'edition' in entry:
            cite.append(('ed',entry['edition']))
        if 'chapter' in entry:
            cite.append(('ch',entry['chapter']))
        if 'pages' in entry:
            cite.append(('pp',entry['pages']))
        if 'journal' in entry:
            cite.append(('j',entry['journal']))
        if 'volume' in entry:
            cite.append(('v',entry['volume']))
        if 'number' in entry:
            cite.append(('n',entry['number']))
        if 'annote' in entry:
            cite.append(('an',entry['annote']))
        if 'note' in entry:
            cite.append(('nt',entry['note']))

        fdo.write("""      <node COLOR="#ff33b8" TEXT="%s"/>\n"""  % \
            xml_escape(' '.join(["%s=%s" % vals for vals in cite])))

        if 'abstract' in entry:
            fdo.write("""      <node COLOR="#999999" \
                TEXT="&quot;%s&quot;"/>\n""" % xml_escape(entry['abstract']))

        fdo.write("""    </node>\n  </node>\n""")

    fdo.write("""</node>\n</map>\n""")

if __name__ == "__main__":

    import codecs, getopt, os, sys


    try:
        (options,files) = getopt.getopt (sys.argv[1:],"")
    except getopt.error:
        print 'Error: Unknown option or missing argument.'

    files = [os.path.abspath(file) for file in files]
    for file in files:
        try:
            src = codecs.open(file, "r", "utf-8", "replace").read()
            fileOut = os.path.splitext(file)[0] + '.mm'
            fdo = codecs.open(fileOut, "wb", "utf-8", "replace")
        except IOError:
            print "    file does not exist"
            continue
        entries = regexParse(src.split('\n'))
        process(entries)
        #os.system('~/bin/freemind/freemind.sh %s' %fileOut)
