#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# This file is used with Thunderdell
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2020 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>

import logging
import re
import sys

import busy  # https://github.com/reagle/thunderdell

debug = logging.debug
info = logging.info
warning = logging.warning
error = logging.error
critical = logging.critical
exception = logging.exception


def uncurly(text):
    """Replace curly quotes with straight, and dashes to markdown"""
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("–", "--")
        .replace("—", "---")
    )
    return text


def get_bib_preamble(token):

    info(f"{token=}")
    if token.startswith("10"):
        scrape_token = busy.scrape_DOI
    else:
        scrape_token = busy.scrape_ISBN
    params = {
        "scheme": "c",
        "tags": "misc",
        "comment": "",
    }
    try:
        biblio = scrape_token(f"{token}", "").get_biblio()
        biblio["tags"] = ""
        result = [busy.log2console(biblio).strip()]
    except:
        result = []
    return result
