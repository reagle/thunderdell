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

def unescape_XML(s):
    '''Unescape XML character entities; & < > are defaulted'''
    extras = {"&apos;": "'", "&quot;": '"'}
    return(unescape(s, extras))

import logging
import os
import requests

HOMEDIR = os.path.expanduser('~')

log = logging.getLogger("web_little")
critical = logging.critical
info = logging.info
dbg = logging.debug

def get_HTML(url, referer='', 
    data=None, cookie=None, retry_counter=0, cache_control=None):
    '''Return [HTML content, response] of a given URL.'''
    r = requests.get(url)
    return r.content, r.headers