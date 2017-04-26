#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
"""
Web functionality I frequently make use of.
"""

import chardet
import html.entities
import logging
from lxml import etree
import os
import re
import sys
from xml.sax.saxutils import escape, unescape

import requests  # http://docs.python-requests.org/en/latest/

HOMEDIR = os.path.expanduser('~')

log = logging.getLogger("web_little")
critical = logging.critical
info = logging.info
dbg = logging.debug


def escape_XML(s):  # http://wiki.python.org/moin/EscapingXml
    '''Escape XML character entities; & < > are defaulted'''
    extras = {'\t': '  '}
    return escape(s, extras)


# def unescape_XML(o): #.117s 5.45%
#     '''Unescape XML character entities in a string;
#     &<> are by default; I add apostrophe and quote'''

#     extras = {"&apos;": "'", "&quot;": '"'}
#     return(unescape(o, extras))


def unescape_XML(text):  #.0937s 4.11%
    '''
    Removes HTML or XML character references and entities from text.
    http://effbot.org/zone/re-sub.htm#unescape-htmlentitydefs
    Marginally faster than `from xml.sax.saxutils import escape, unescape`

    '''
    import html.entities
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(html.entities.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is
    return re.sub("&#?\w+;", fixup, text)


def get_HTML_content(
        url, referer='', data=None, cookie=None,
        retry_counter=0, cache_control=None):
    '''Return [HTML content, headers] of a given URL.
    Note: I try to guess the encoding and return unicode. However, etree
    will not parse unicode with an encoding declaration within it.
    However, get_HTM will return a parse tree if that's what you need.
    '''

    agent_headers = {"User-Agent": "Thunderdell/BusySponge"}
    r = requests.get(url, headers=agent_headers, verify=True)
    info("r.headers['content-type'] = %s" % r.headers['content-type'])
    if 'html' in r.headers['content-type']:
        info("r       encoding = '%s'" % (r.encoding))
        chardet_encoding = chardet.detect(r.content)
        info("chardet_encoding = %s" % chardet_encoding)
        if chardet_encoding['confidence'] > 0.85:
            try:
                info("chardet encoding = '%s'" % (
                    chardet_encoding['encoding']))
                content_uni = r.content.decode(chardet_encoding['encoding'])
            except UnicodeDecodeError:
                info("r       encoding = '%s'" % (r.encoding))
                content_uni = r.content.decode(r.encoding)
        else:
            info("r       encoding = '%s'" % (r.encoding))
            content_uni = r.content.decode(r.encoding)
        return content_uni, r.headers
    else:
        raise IOError("URL content is not HTML.")


def get_HTML(
        url, referer='', data=None, cookie=None,
        retry_counter=0, cache_control=None):
    '''Return [HTML content, response] of a given URL.'''

    agent_headers = {"User-Agent": "Thunderdell/BusySponge"}
    r = requests.get(url, headers=agent_headers, verify=True)
    info("r.headers['content-type'] = %s" % r.headers['content-type'])
    if 'html' in r.headers['content-type']:
        HTML_bytes = r.content
    else:
        raise IOError("URL content is not HTML.")

    parser_html = etree.HTMLParser()
    doc = etree.fromstring(HTML_bytes, parser_html)
    HTML_parsed = doc

    HTML_utf8 = etree.tostring(HTML_parsed, encoding='utf-8')
    HTML_unicode = HTML_utf8.decode('utf-8', 'replace')

    return HTML_bytes, HTML_parsed, HTML_unicode, r


def get_text(url):
    '''Textual version of url'''

    import os

    return str(os.popen('w3m -O utf8 -cols 10000 '
                        '-dump "%s"' % url).read())
