#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009 by Joseph Reagle
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
import httplib2 # http://pypi.python.org/pypi/httplib2/
import os
import socket
import time
import urllib
HOMEDIR = os.path.expanduser('~')

log = logging.getLogger("web_little")
critical = logging.critical
info = logging.info
dbg = logging.debug

def get_HTML(url, referer='', data=None, cookie=None, retry_counter=0, cache_control=None):
    '''Return [HTML content, response] of a given URL.'''
    h = httplib2.Http("%s/.cache/httplib2" % HOMEDIR, timeout=20)
    headers = {'Referer': referer,
            'Content-type': 'application/x-www-form-urlencoded',
            'User-Agent': 'Mozilla/5.0 (Windows; U; Windows NT 5.1; en-US;'
                    'rv:1.8.1.14) Gecko/20080404 Firefox/2.0.0.14',
            'Accept-Language': 'en, en-US',
            'Accept-Encoding': 'identity,gzip,deflate'}
    if retry_counter > 0:
        critical('Trying Again...')
    if retry_counter > 3:
        critical('Could not get source from url: %s' % url)
        return '', None
    if cache_control:
        headers['cache-control'] = cache_control
    try:
        if cookie:
            headers['Cookie'] = response['set-cookie']
        if data:
            response, content = h.request(url, "POST", urllib.urlencode(data), headers=headers, redirections=10)
        else:
            response, content = h.request(url, "GET", headers=headers, redirections=10)
        if 'content-type' in response and 'charset=' in response['content-type']:
            encoding = response['content-type'].split('charset=')[-1]
            if encoding == "none": # a site returned: Content-Type: text/html; charset=none
                encoding = 'utf-8'
            content = content.decode(encoding, 'replace')
        else: # assume utf8, it'd be nice to peek at meta http-equiv charset; use chardetect?
            content = content.decode('utf-8', 'replace')
        # what does httplib2 do when it times out, return a response code 408?
        if 0 < response.status < 300:
            return content, response
        elif response.status in (408, 500, 503, 504, 505):
            critical("Response Code = %s, sleeping before retry %s" % (
                response.status, retry_counter +1))
            time.sleep((retry_counter * 10 + 5)) # pause before retying
            return get_HTML(url, referer, data, cookie, retry_counter + 1)
        else:
            return None
    except (AttributeError, httplib2, socket) as e:
        critical("The server couldn't fulfill the request. for url: %s" % url)
        critical("Error code: %s" % e)
        time.sleep((retry_counter * 10 + 5)) # pause before retying
        return get_HTML(url, referer, data, cookie, retry_counter + 1)
