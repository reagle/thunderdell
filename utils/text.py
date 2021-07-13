#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Textual utilities."""

import logging
import unicodedata

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


def escape_latex(text):
    text = (
        text.replace("$", r"\$")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\~{}")
        .replace("^", r"\^{}")
    )
    return text


def normalize_whitespace(text):
    """Remove redundant whitespace from a string, including before comma
    >>> normalize_whitespace('sally, joe , john')
    'sally, joe, john'

    """
    text = text.replace(" ,", ",")
    text = " ".join(text.split())
    return text


def pretty_tabulate_list(mylist, cols=3):
    pairs = [
        "\t".join(["%20s" % j for j in mylist[i : i + cols]])
        for i in range(0, len(mylist), cols)
    ]
    print(("\n".join(pairs)))
    print("\n")


def pretty_tabulate_dict(mydict, cols=3):
    pretty_tabulate_list(
        sorted([f"{key}:{value}" for key, value in list(mydict.items())]), cols
    )


def strip_accents(text):
    """strip accents and those chars that can't be stripped"""
    # >>> strip_accents(u'nôn-åscîî')
    # ^ fails because of doctest bug u'non-ascii'
    try:  # test if ascii
        text.encode("ascii")
    except UnicodeEncodeError:
        return "".join(
            x
            for x in unicodedata.normalize("NFKD", text)
            if unicodedata.category(x) != "Mn"
        )
    else:
        return text


def smart_to_markdown(text):
    """Convert unicode punctuation (i.e., "smart quotes") to markdown form."""
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("–", "--")
        .replace("—", "---")
    )
    return text