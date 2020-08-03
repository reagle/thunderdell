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

import html.entities
import json
import logging
import os
import re
from xml.sax.saxutils import escape, unescape

import requests  # http://docs.python-requests.org/en/latest/

HOMEDIR = os.path.expanduser("~")

log = logging.getLogger("web_utils")
critical = logging.critical
info = logging.info
dbg = logging.debug


def escape_XML(s):  # http://wiki.python.org/moin/EscapingXml
    """Escape XML character entities; & < > are defaulted"""
    extras = {"\t": "  "}
    return escape(s, extras)


def unescape_XML(text):  # .0937s 4.11%
    """
    Removes HTML or XML character references and entities from text.
    http://effbot.org/zone/re-sub.htm#unescape-htmlentitydefs
    Marginally faster than `from xml.sax.saxutils import escape, unescape`

    """

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

    return re.sub(r"&#?\w+;", fixup, text)


def get_HTML(
    url,
    referer="",
    data=None,
    cookie=None,
    retry_counter=0,
    cache_control=None,
):
    """Return [HTML content, response] of a given URL."""

    from lxml import etree

    agent_headers = {"User-Agent": "Thunderdell/BusySponge"}
    r = requests.get(url, headers=agent_headers, verify=True)
    # info(f"{r.headers['content-type']=}")
    if "html" in r.headers["content-type"]:
        HTML_bytes = r.content
    else:
        raise IOError("URL content is not HTML.")

    parser_html = etree.HTMLParser()
    doc = etree.fromstring(HTML_bytes, parser_html)
    HTML_parsed = doc

    HTML_utf8 = etree.tostring(HTML_parsed, encoding="utf-8")
    HTML_unicode = HTML_utf8.decode("utf-8", "replace")

    return HTML_bytes, HTML_parsed, HTML_unicode, r


def get_JSON(
    url,
    referer="",
    data=None,
    cookie=None,
    retry_counter=0,
    cache_control=None,
    requested_content_type="application/json",
):
    """Return [JSON content, response] of a given URL."""

    AGENT_HEADERS = {"User-Agent": "Thunderdell/BusySponge"}
    info(f"{url=}")
    try:
        r = requests.get(url, headers=AGENT_HEADERS, verify=True)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"{e}")
    returned_content_type = r.headers["content-type"].split(";")[0]
    info(f"{requested_content_type=} == {returned_content_type=}?")
    if requested_content_type == returned_content_type:
        json_content = json.loads(r.content)
        return json_content
    else:
        raise IOError("URL content is not JSON.")


def get_text(url):
    """Textual version of url"""

    import os

    return str(os.popen(f'w3m -O utf8 -cols 10000 -dump "{url}"').read())
