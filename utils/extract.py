#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

import logging

# TODO: this is a recursive import, move to logger and scaper specific
import busy  # https://github.com/reagle/thunderdell

debug = logging.debug
info = logging.info
warning = logging.warning
error = logging.error
critical = logging.critical
exception = logging.exception


class args:
    publish = False  # don't tweet at this level


def get_bib_preamble(token):

    info(f"{token=}")
    if token.startswith("10"):
        scrape_token = busy.scrape_DOI
    else:
        scrape_token = busy.scrape_ISBN
    biblio = scrape_token(f"{token}", "").get_biblio()
    biblio["tags"] = ""
    result = [busy.log2console(args, biblio).strip()]
    return result
