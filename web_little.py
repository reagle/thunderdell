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

from xml.sax.saxutils import escape, unescape
def escape_XML(s): # http://wiki.python.org/moin/EscapingXml
    '''Escape XML character entities; & < > are defaulted'''
    extras = {'\t' : '  '}
    return escape(s, extras)

#def unescape_XML(s):
    #'''Unescape XML character entities; & < > are defaulted'''
    #extras = {  "&apos;": "'", 
                #"&quot;": '"',
                #"&#8220;": '"',
                #"&#8221;"; '"',
                #"&laquo;": u'«',
                #"&raquo;": u'»',
                #"&mdash;": '-',}
    #return(unescape(s, extras))

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
    
    
import logging
import os
import requests # http://docs.python-requests.org/en/latest/

HOMEDIR = os.path.expanduser('~')

log = logging.getLogger("web_little")
critical = logging.critical
info = logging.info
dbg = logging.debug

def get_HTML(url, referer='', 
    data=None, cookie=None, retry_counter=0, cache_control=None):
    '''Return [HTML content, response] of a given URL.'''
    
    agent_headers = {"User-Agent" : "Thunderdell/BusySponge"}
    r = requests.get(url, headers=agent_headers)
    info("r.headers['content-type'] = %s" % r.headers['content-type'])
    if 'html' in r.headers['content-type']:
        return r.content.decode(r.encoding), r.headers
    else:
        raise IOError("URL content is not HTML.")