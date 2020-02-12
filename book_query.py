#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2015 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
""" Return bibliographic data for a given a ISBN.
"""

from datetime import datetime
from dateutil.parser import parse
import json
import logging
import pprint
import requests
import sys

log_level = 100  # default
critical = logging.critical
info = logging.info
dbg = logging.debug


def query(isbn):
    """Query available ISBN services"""
    bib = {}
    bib_open = bib_google = None

    bib_open = open_query(isbn)
    if not bib_open or "author" not in bib_open:
        bib_google = google_query(isbn)
    if not (bib_open or bib_google):
        raise Exception("All ISBN queries failed")
    if bib_open:
        bib.update(bib_open)
    if bib_google:
        bib.update(bib_google)
    return bib


def open_query(isbn):
    """Query the ISBN Web service; returns string"""
    # https://openlibrary.org/dev/docs/api/books
    # https://openlibrary.org/api/books?bibkeys=ISBN:0472069322&jscmd=details&format=json

    if isbn.startswith("isbn:"):
        isbn = isbn[5:]
    isbn = isbn.replace("-", "")
    info(f"{isbn=}")
    URL = (
        f"https://openlibrary.org/api/books?bibkeys=ISBN:{isbn}"
        "&jscmd=details&format=json"
    )
    info(f"{URL=}")
    r = requests.get(URL)
    returned_content_type = r.headers["content-type"]
    info(f"r.content = '{r.content}'")
    if returned_content_type.startswith("application/json"):
        if r.content != b"{}":
            json_bib = {"isbn": str(isbn)}
            json_result = json.loads(r.content)
            json_vol = json_result[f"ISBN:{isbn}"]
            json_details = json_vol["details"]
            for key, value in list(json_details.items()):
                if key == "authors":
                    json_bib["author"] = ", ".join(
                        [author["name"] for author in json_details["authors"]]
                    )
                if key == "by_statement":
                    json_bib["author"] = json_details["by_statement"]
                elif key == "publishers":
                    json_bib["publisher"] = json_details[key][0]
                elif key == "publish_places":
                    json_bib["address"] = json_details[key][0]
                elif key == "publish_date":
                    json_bib["date"] = parse(json_details[key]).strftime(
                        "%Y%m%d"
                    )
                elif type(value) == str:
                    json_bib[key] = value.strip()
                    info("  value = '%s'" % json_bib[key])
            json_bib["url"] = f"https://books.google.com/books?isbn={isbn}"
            if "title" in json_bib and "subtitle" in json_bib:
                subtitle = json_bib["subtitle"]
                json_bib["title"] += ": " + subtitle[:1].upper() + subtitle[1:]
                del json_bib["subtitle"]
            return json_bib
        else:
            print(f"Open Library unknown ISBN {isbn}")
            return False
    else:
        print("Open Library ISBN API did not return application/json")
        return False


def google_query(isbn):
    """Query the ISBN Web service; returns string"""
    # https://books.google.com/books?isbn=0472069322

    if isbn.startswith("isbn:"):
        isbn = isbn[5:]
    isbn = isbn.replace("-", "")
    info(f"{isbn=}")
    URL = f"https://www.googleapis.com/books/v1/volumes?q=isbn:{isbn}"
    info(f"{URL=}")
    r = requests.get(URL)
    returned_content_type = r.headers["content-type"]
    # info(f"r.content = '{r.content}'")
    json_bib = {"isbn": str(isbn)}
    if returned_content_type.startswith("application/json"):
        json_result = json.loads(r.content)
        info(f"json_result['totalItems']={json_result['totalItems']}")
        if json_result["totalItems"] == 0:
            print((f"Google unknown ISBN for {isbn}"))
            return False
        json_vol = json_result["items"][0]["volumeInfo"]
        for key, value in list(json_vol.items()):
            if key == "authors":
                json_bib["author"] = ", ".join(value)
            if key == "publishedDate":
                json_bib["date"] = value.replace("-", "")
            elif type(value) == str:
                json_bib[key] = value.strip()
                info(f"  value = '{json_bib[key]}'")
        json_bib["url"] = f"https://books.google.com/books?isbn={isbn}"
        return json_bib
    else:
        print("Google ISBN API did not return application/json")
        return False


if "__main__" == __name__:

    import argparse

    arg_parser = argparse.ArgumentParser(
        description="Given a isbn return bibliographic data."
    )
    # positional arguments
    arg_parser.add_argument("ISBN", nargs="+")
    # optional arguments
    arg_parser.add_argument("-s", "--style", help="style of bibliography data")
    arg_parser.add_argument(
        "-l",
        "--log-to-file",
        action="store_true",
        default=False,
        help="log to file %(prog)s.log",
    )
    arg_parser.add_argument(
        "-V",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument("--version", action="version", version="0.1")
    args = arg_parser.parse_args()

    if args.verbose == 1:
        log_level = logging.CRITICAL
    elif args.verbose == 2:
        log_level = logging.INFO
    elif args.verbose >= 3:
        log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(
            filename="isbn_query.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    info(args.ISBN[0])
    pprint.pprint(query(args.ISBN[0]))
