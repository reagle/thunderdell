#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2015 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
''' Return bibliographic data for a given a ISBN.
    See http://xisbn.worldcat.org/xisbnadmin/doc/api.htm#getmetadata
'''

import json
import logging
import pprint
import requests
import sys

log_level = 100 # default
critical = logging.critical
info = logging.info
dbg = logging.debug

def query(isbn):
    """Query the ISBN Web service; returns string"""
    # https://books.google.com/books?isbn=0472069322

    if isbn.startswith('isbn:'):
        isbn = isbn[5:]
    info("isbn = '%s'" %isbn)
    URL = ('http://xisbn.worldcat.org/webservices/xid/isbn/{isbn}?method=getMetadata&format=json&fl=*')
    info("isbn = '%s'" %isbn)
    r = requests.get(URL.format(isbn=isbn))
    returned_content_type = r.headers['content-type']
    info("r.content = '%s'" % r.content)
    if returned_content_type.startswith('text/plain'): # no 'application/json'
        json_bib = json.loads(r.content)
        info("json_bib['stat'] = '%s'" %json_bib['stat'])
        if 'unknownId' in json_bib['stat']:
            raise Exception("Unknown ISBN (Book too new?)")
        if 'invalidId' in json_bib['stat']:
            raise Exception("Invalid ISBN (Tyo?)")
        json_bib = json_bib['list'][0]
        for key, value in json_bib.items():
     		if type(value) == str or type(value) == unicode:
	            value = value.strip()
	            value = value[0:-1] if value.endswith('.') else value
	            info("  value = '%s'" %value)
	            json_bib[key] = value
        json_bib['url'] = 'https://books.google.com/books?isbn=%s' % isbn.replace('-', '')
        return(json_bib)
    else:
        return False

if '__main__' == __name__:

    import argparse 
    arg_parser = argparse.ArgumentParser(
        description='Given a isbn return bibliographic data.')
    # positional arguments
    arg_parser.add_argument('ISBN', nargs='+')
    # optional arguments
    arg_parser.add_argument("-s", "--style",
        help="style of bibliography data")
    arg_parser.add_argument('-l', '--log-to-file',
        action="store_true", default=False,
        help="log to file %(prog)s.log")
    arg_parser.add_argument('-V', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    arg_parser.add_argument('--version', action='version', version='0.1')
    args = arg_parser.parse_args()

    if args.verbose == 1: log_level = logging.CRITICAL
    elif args.verbose == 2: log_level = logging.INFO
    elif args.verbose >= 3: log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(filename='isbn_query.log', filemode='w',
            level=log_level, format = LOG_FORMAT)
    else:
        logging.basicConfig(level=log_level, format = LOG_FORMAT)

    info(args.ISBN[0])
    pprint.pprint(query(args.ISBN[0]))