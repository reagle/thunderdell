#!/usr/bin/env python3.6
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2015-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
''' Return CrossRef bibliographic data for a given a DOI.
    See http://www.crossref.org/CrossTech/2011/11/turning_dois_into_formatted_ci.html
'''

import json
import logging
import pprint
import requests
import sys

log_level = 100  # default
critical = logging.critical
info = logging.info
dbg = logging.debug

ACCEPT_HEADERS = {
    'json': 'application/citeproc+json',
    'bibtex': 'text/bibliography;style=bibtex', }


def query(doi, accept='application/citeproc+json'):
    """Query the DOI Web service; returns string"""

    info('accept = %s ' % accept)
    info("doi = %s" % doi)
    headers = {'Accept': accept}
    url = "http://dx.doi.org/%s" % doi
    info("url = '%s'" % url)
    r = requests.get(url, headers=headers)
    requested_content_type = accept.split(';')[0]
    returned_content_type = r.headers['content-type']
    info("returned_content_type = '%s'; requested_content_type = '%s'"
         % (returned_content_type, requested_content_type))
    if requested_content_type in returned_content_type:
        json_bib = json.loads(r.content)
        return(json_bib)
    else:
        return False

if '__main__' == __name__:

    import argparse
    arg_parser = argparse.ArgumentParser(
        description='Given a doi return bibliographic data.')
    # positional arguments
    arg_parser.add_argument('DOI', nargs='+')
    # optional arguments
    arg_parser.add_argument(
        "-s", "--style",
        help="style of bibliography data")
    arg_parser.add_argument(
        '-L', '--log-to-file',
        action="store_true", default=False,
        help="log to file %(prog)s.log")
    arg_parser.add_argument(
        '-V', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    arg_parser.add_argument('--version', action='version', version='0.1')
    args = arg_parser.parse_args()

    if args.verbose == 1: log_level = logging.CRITICAL
    elif args.verbose == 2: log_level = logging.INFO
    elif args.verbose >= 3: log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(filename='doi_query.log', filemode='w',
                            level=log_level, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    accept = ACCEPT_HEADERS['json']
    if args.style:
        if args.style in ACCEPT_HEADERS:
            accept = ACCEPT_HEADERS[args.style]
        else:
            accept = args.style
    info('accept = %s ' % accept)

    pprint.pprint(query(args.DOI[0], accept))
