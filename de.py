#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""extract a MM from a dictated text file using particular conventions"""

import os
HOME = os.path.expanduser('~')

MINDMAP_PREAMBLE = '''<map version="freeplane 1.5.9">
    <node TEXT="reading" FOLDED="false" ID="ID_327818409" STYLE="oval">
        <font SIZE="18"/>
        <hook NAME="MapStyle">
            <map_styles>
                <stylenode LOCALIZED_TEXT="styles.root_node" STYLE="oval"
                 UNIFORM_SHAPE="true" VGAP_QUANTITY="24.0 pt">
                    <font SIZE="24"/>
                    <stylenode LOCALIZED_TEXT="styles.user-defined"
                     POSITION="right" STYLE="bubble">
                        <stylenode TEXT="author" COLOR="#338800"/>
                        <stylenode TEXT="title" COLOR="#090f6b"/>
                        <stylenode TEXT="cite" COLOR="#ff33b8"/>
                        <stylenode TEXT="annotation" COLOR="#999999"/>
                        <stylenode TEXT="quote" COLOR="#166799"/>
                        <stylenode TEXT="paraphrase" COLOR="#8b12d6"/>
                    </stylenode>
                </stylenode>
            </map_styles>
        </hook>
'''

# CL_CO = {'annotation': '#999999', 'author': '#338800', 'title': '#090f6b',
#     'cite': '#ff33b8', 'author': '#338800',
#     'quote': '#166799', 'paraphrase': '#8b12d6',
#     'default': '#000000', None: None}
# CO_CL = dict([(label, color) for color, label in list(CL_CO.items())])


def clean(text):
    '''clean and encode text'''
    # TODO: Maybe make use of b.smart_punctuation_to_ascii() and
    # web_little.escape_XML()

    text = text.strip(', \f\r\n')
    REPLACEMENTS = [
        ('&', '&amp;'), ("'", '&apos;'),
        ('"', '&quot;'), ('“', '&quot;'),
        ('”', '&quot;'), ("‘", "'"),
        ("’", "'"), (" – ", " -- "), ("–", " -- ")]

    for v1, v2 in REPLACEMENTS:
        text = text.replace(v1, v2)
    return text


def get_date():
    import string
    import time
    now = time.localtime()
    year = time.strftime("%Y", now).lower()
    month = time.strftime("%m", now).lower()
    date_token = time.strftime("%Y%m%d", now)
    return date_token


def parse(line, started, in_part, in_chapter, in_section, in_subsection):

    import re

    author = title = citation = ""
    entry = {}

    if line not in ('', '\r', '\n'):
        if line.lower().startswith('author ='):
            # and re.match('([^=]+ = (?=[^=]+)){2,}', line, re.I)
            if started:  # Do I need to close a previous entry
                if in_subsection:
                    file_out.write("""        </node>\n""")
                    in_subsection = False
                if in_section:
                    file_out.write("""      </node>\n""")
                    in_section = False
                if in_chapter:
                    file_out.write("""    </node>\n""")
                    in_chapter = False
                if in_part:
                    file_out.write("""    </node>\n""")
                    in_part = False

                file_out.write("""</node>\n</node>\n""")
                started = False
            started = True
            # should space be optional '(\w+) ?='
            cites = re.split('(\w+) =', line)[1:]
            # 2 references to an iterable object that are
            # unpacked with '*' and rezipped
            cite_pairs = list(zip(*[iter(cites)] * 2))
            for token, value in cite_pairs:
                entry[token.lower()] = value.strip()

            if 'author' not in entry:
                entry['author'] = 'Unknown'
            if 'title' not in entry:
                entry['title'] = 'Untitled'
            if 'subtitle' in entry:
                entry['title'] += ': ' + entry['subtitle']
                del entry['subtitle']

            file_out.write(
                """<node STYLE_REF="%s" TEXT="%s" POSITION="RIGHT">\n"""
                % ('author', clean(entry['author'].title())))
            if 'url' in entry:
                file_out.write(
                    """  <node STYLE_REF="%s" LINK="%s" TEXT="%s">\n"""
                    % ('title', clean(entry['url']), clean(entry['title'])))
            else:
                file_out.write(
                    """  <node STYLE_REF="%s" TEXT="%s">\n"""
                    % ('title', clean(entry['title'])))

            for token, value in sorted(entry.items()):
                if token not in ('author', 'title', 'url'):
                    if token in BIB_SHORTCUTS:
                        t, v = token.lower(), value
                    else:
                        if token.lower() in BIB_FIELDS:
                            t, v = BIB_FIELDS[token.lower()], value
                        else:
                            print("* Unknown token '%s' in %s" % (
                                token, entry['author']))
                            sys.exit
                    citation_add = "%s=%s " % (t, v)
                    citation = citation + citation_add
            if citation != "":
                clean(citation)
            citation += " r=%s" % get_date()
            file_out.write("""  <node STYLE_REF="%s" TEXT="%s"/>\n"""
                           % ('cite', clean(citation)))

        elif re.match('summary\.(.*)', line, re.I):
            matches = re.match('summary\.(.*)', line, re.I)
            file_out.write("""  <node STYLE_REF="%s" TEXT="%s"/>\n"""
                           % ('annotation', clean(matches.groups()[0])))

        elif re.match('part.*', line, re.I):
            if in_part:
                if in_chapter:
                    file_out.write("""    </node>\n""")      # close chapter
                    in_chapter = False
                if in_section:
                    file_out.write("""      </node>\n""")    # close section
                    in_section = False
                if in_subsection:
                    file_out.write("""      </node>\n""")    # close section
                    in_subsection = False
                file_out.write("""  </node>\n""")            # close part
                in_part = False
            file_out.write("""  <node STYLE_REF="%s" TEXT="%s">\n"""
                           % ('paraphrase', clean(line)))
            in_part = True

        elif re.match('chapter.*', line, re.I):
            if in_chapter:
                if in_section:
                    file_out.write("""      </node>\n""")    # close section
                    in_section = False
                if in_subsection:
                    file_out.write("""      </node>\n""")    # close section
                    in_subsection = False
                file_out.write("""    </node>\n""")            # close chapter
                in_chapter = False
            file_out.write("""    <node STYLE_REF="%s" TEXT="%s">\n"""
                           % ('paraphrase', clean(line)))
            in_chapter = True

        elif re.match('section.*', line, re.I):
            if in_subsection:
                file_out.write("""      </node>\n""")    # close section
                in_subsection = False
            if in_section:
                file_out.write("""    </node>\n""")
                in_section = False
            file_out.write("""      <node STYLE_REF="%s" TEXT="%s">\n"""
                           % ('paraphrase', clean(line[9:])))
            in_section = True

        elif re.match('subsection.*', line, re.I):
            if in_subsection:
                file_out.write("""    </node>\n""")
                in_subsection = False
            file_out.write("""      <node STYLE_REF="%s" TEXT="%s">\n"""
                           % ('paraphrase', clean(line[12:])))
            in_subsection = True

        elif re.match('(--.*)', line, re.I):
            file_out.write("""          <node STYLE_REF="%s" TEXT="%s"/>\n"""
                           % ('default', clean(line)))

        else:
            node_color = 'paraphrase'
            line_text = line
            # print(line)
            line_no = ''
            line_split = line.split(' ')
            # DIGIT_CHARS = '[\dcdilmxv]'  # arabic and roman numbers
            PAGE_NUM_PAT = '^([\dcdilmxv]+)(\-[\dcdilmxv]+)? (.*?)(-[\dcdilmxv]+)?$'

            matches = re.match(PAGE_NUM_PAT, line, re.I)
            if matches:
                print(matches.groups())
                line_no = matches.group(1)
                if matches.group(2):
                    line_no += matches.group(2)
                if matches.group(4):
                    line_no += matches.group(4)
                line_no = line_no.lower()   # lower case roman numbers
                line_text = matches.group(3).strip()

            if line_text.startswith('excerpt.'):
                node_color = 'quote'
                line_text = line_text[9:]
            if line_text.strip().endswith('excerpt.'):
                node_color = 'quote'
                line_text = line_text[0:-9]

            file_out.write(
                """          <node STYLE_REF="%s" TEXT="%s"/>\n"""
                % (node_color, clean(' '.join((line_no, line_text)))))

    return started, in_part, in_chapter, in_section, in_subsection


def check(text, file_out):

    import traceback

    started = False
    in_part = False
    in_chapter = False
    in_section = False
    in_subsection = False
    line_number = 0

    file_out.write("""%s\n<node TEXT="Readings">\n""" % MINDMAP_PREAMBLE)

    for line in text.split('\n'):
        line = line.strip()
        try:
            started, in_part, in_chapter, in_section, in_subsection = parse(
                line, started, in_part, in_chapter, in_section, in_subsection)
        except KeyError:
            print(traceback.print_tb(
                sys.exc_info()[2]), '\n', line_number, line)
            sys.exit()
        line_number += 1

    if in_subsection: file_out.write("""</node>""")  # close the last section
    if in_section: file_out.write("""</node>""")  # close the last section
    if in_chapter: file_out.write("""</node>""")  # close the last chapter
    if in_part: file_out.write("""</node>""")  # close the last part
    file_out.write("""</node>\n</node>\n</node>\n""")  # close the last entry
    file_out.write("""</node>\n</map>\n""")   # close the document


# Check to see if the script is executing as main.
if __name__ == "__main__":
    # Parse the command line arguments for optional message and files.

    from fe import BIB_SHORTCUTS   # a dict of shotcuts yeilding a field
    from fe import BIB_FIELDS      # a dict of a field yielding its shortcut

    import codecs
    import chardet
    import getopt
    import os
    import subprocess
    import sys

    try:
        (options, file_names) = getopt.getopt(sys.argv[1:], "")
    except getopt.error:
        print('Error: Unknown option or missing argument.')
    file_names = [os.path.abspath(file_name) for file_name in file_names]
    for file_name in file_names:
        if file_name.endswith('.rtf'):
            subprocess.call(
                ['/usr/bin/X11/catdoc', '-aw', file_name],
                stdout=open('%s.txt' % file_name[0:-4], 'w',
                encoding='utf-8', errors='replace'))
            file_name = file_name[0:-4] + '.txt'
        try:
            encoding = 'UTF-8'
            # encoding = chardet.detect(open(file_name).read())['encoding']
            fdi = open(file_name, "r", encoding=encoding, errors='replace')
            text = fdi.read()
            if encoding == 'UTF-8':
                if text[0] == str(codecs.BOM_UTF8, "utf8"):
                    text = text[1:]
                    print("removed BOM")
            # it's not decoding MS Word txt right, word is not starting with
            # utf-8 even though I set to default if no special characters
            # write simple Word txt to UTF-8 encoder
            file_name_out = os.path.splitext(file_name)[0] + '.mm'
            file_out = open(file_name_out, "w", encoding="utf-8",
                            errors='replace')
            # sys.stdout = codecs.getwriter('UTF-8')(
            #     sys.__stdout__, errors='replace')
        except IOError:
            print("    file_name does not exist")
            continue

        check(text, file_out)
        subprocess.call(['open', '-a', 'Freeplane.app', file_name_out])
