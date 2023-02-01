#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Extract the bibliographic keys of the form 'Snide and Smith (2003)'
or '(Snide, Smith and Smittie 2004)' from natural language text"""

# create a way to toss common Cap words or acronyms
# as cited in

import getopt
import os
import re
import sys

catches = []
citations = {}
citation_list = []


def parse_token(name, year):
    name_non = page = ""
    name = name.replace(" ", "")
    name_non = name.replace("'s", "").replace("'", "")
    if ":" in year:
        year, page = year.split(":")
    return name, name_non, year, page


try:
    (options, files) = getopt.getopt(sys.argv[1:], "m:")
except getopt.error:
    print("Error: Unknown option or missing argument.")
file = files[0]
if file[-4:] == ".doc":
    os.system("/usr/bin/antiword -w0 %s > /tmp/tmp-%s" % (file, file))
    file = "/tmp/tmp-%s" % file
fd = open(file, "rb")
for line in fd:
    # print "***", line[0:50]

    # Textual: Tom McArthur's (1986ftw:67)
    t_catches = re.findall(r"""(['\w]+ \(\d\d\d\d\w*(?::\d+)?\))""", line)
    if t_catches != []:
        for catch in t_catches:
            name = name_non = year = page = None
            name, year = catch.split("(")
            year = year[0:-1]  # remove last parens
            name, name_non, year, page = parse_token(name, year)
            if page:
                insert_txt = r"""%s \citeyearpar[p. %s]{%s%s}""" % (
                    name,
                    page,
                    name_non,
                    year,
                )
            else:
                insert_txt = r"""%s \citeyearpar{%s%s}""" % (
                    name,
                    name_non,
                    year,
                )
            # print "*** insert_txt = ", insert_txt
            line = line.replace(catch, insert_txt)
            # print line

    # Parenthetical: (as cited in McArthur 1986:155)
    p_catches = re.findall(
        r"""(\((?:as cited in )?['\w]+ \d\d\d\d\w*(?::\d+)?\))""", line
    )
    if p_catches != []:
        for catch in p_catches:
            catch_ori = catch
            catch = catch[1:-1]  # remove parens
            prefix = name = name_non = year = page = None
            prefix_txt = page_txt = insert_txt = ""
            if catch.startswith("as cited in"):
                prefix = catch[0:12]
                catch = catch[12:]
            else:
                prefix = ""
            name, year = catch.split(" ")
            name, name_non, year, page = parse_token(name, year)
            if prefix:
                prefix_txt = "[%s]" % prefix
            if page:
                page_txt = "[p. %s]" % page
            insert_txt = r"""\citep%s%s{%s%s}""" % (
                prefix_txt,
                page_txt,
                name_non,
                year,
            )
            # print "*** insert_txt = '%s'" % insert_txt
            # print "original = '%s'" % (prefix + catch)
            line = line.replace(catch_ori, insert_txt)
            # print line

    # Multiple Parenthetical: (Stockwell 2001;McArthur 1986)
    mp_catches = re.findall(r"""(\(['\w]+ \d\d\d\d\w*;.*?\))""", line)
    if mp_catches != []:
        for catch in mp_catches:
            # print "catch = '%s'" % catch
            names = catch[1:-1]
            authors = names.split("; ")
            insert_txt = r"(\citealt{"
            for author in authors:
                author = author.replace(" ", "").replace(", ", "")
                insert_txt += """%s,""" % author
                # print "*** insert_txt = '%s'" % insert_txt
        insert_txt += "})"
        # print "**** insert_txt = '%s'" % insert_txt
        line = line.replace(catch, insert_txt)

    print(line, end=" ")
