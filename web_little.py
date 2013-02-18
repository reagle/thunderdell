#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2011 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
"""
Web functionality I frequently make use of.
"""

import chardet
import logging
import os
import requests # http://docs.python-requests.org/en/latest/
import sys

HOMEDIR = os.path.expanduser('~')

log = logging.getLogger("web_little")
critical = logging.critical
info = logging.info
dbg = logging.debug

from xml.sax.saxutils import escape, unescape
def escape_XML(s): # http://wiki.python.org/moin/EscapingXml
    '''Escape XML character entities; & < > are defaulted'''
    extras = {'\t' : '  '}
    return escape(s, extras)

import re, htmlentitydefs
def unescape_XML(text):
    '''
    Removes HTML or XML character references and entities from a text string.
    http://effbot.org/zone/re-sub.htm#unescape-htmlentitydefs
    
    '''
    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return unichr(int(text[3:-1], 16))
                else:
                    return unichr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = unichr(htmlentitydefs.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text # leave as is
    return re.sub("&#?\w+;", fixup, text)
    

def get_HTML(url, referer='', 
    data=None, cookie=None, retry_counter=0, cache_control=None):
    '''Return [HTML content, response] of a given URL.'''
    
    agent_headers = {"User-Agent" : "Thunderdell/BusySponge"}
    r = requests.get(url, headers=agent_headers)
    info("r.headers['content-type'] = %s" % r.headers['content-type'])
    if 'html' in r.headers['content-type']:
        info("r.encoding = '%s'" %(r.encoding))
        chardet_encoding = chardet.detect(r.content)
        info("chardet_encoding = %s" %chardet_encoding)
        if chardet_encoding['confidence'] > 0.85:
            try:
                content = r.content.decode(chardet_encoding['encoding'])
            except UnicodeDecodeError:
                content = r.content.decode(r.encoding)
        else:
            content = r.content.decode(r.encoding)
        return content, r.headers
    else:
        raise IOError("URL content is not HTML.")