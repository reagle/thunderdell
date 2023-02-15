#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""
Loggers for BusySponge.

https://github.com/reagle/thunderdell
"""

import logging
import re
import time

import config

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


def log2nifty(args, biblio):
    """
    Log to personal blog.
    """

    print("to log2nifty\n")
    ofile = f"{config.HOME}/data/2web/goatee.net/nifty-stuff.html"

    title = biblio["title"]
    comment = biblio["comment"]
    url = biblio["url"]

    date_token = time.strftime("%y%m%d", NOW)
    log_item = f'<dt><a href="{url}">{title}</a> ({date_token})</dt><dd>{comment}</dd>'

    fd = open(ofile)
    content = fd.read()
    fd.close()

    INSERTION_RE = re.compile('(<dl style="clear: left;">)')
    newcontent = INSERTION_RE.sub(
        "\\1 \n  %s" % log_item, content, re.DOTALL | re.IGNORECASE
    )
    if newcontent:
        fd = open(ofile, "w", encoding="utf-8", errors="replace")
        fd.write(newcontent)
        fd.close()
    else:
        raise RuntimeError("Sorry, output regexp subsitution failed.")
