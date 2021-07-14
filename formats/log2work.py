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
import time

import config
from biblio.keywords import KEY_SHORTCUTS
from lxml import etree as l_etree
from utils.web import escape_XML, yasn_publish

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


def log2work(args, biblio):
    """
    Log to work microblog
    """
    import hashlib

    print("to log2work\n")
    info(f"biblio = '{biblio}'")
    ofile = f"{config.HOME}/data/2web/reagle.org/joseph/plan/plans/index.html"
    info(f"{ofile=}")
    subtitle = biblio["subtitle"].strip() if "subtitle" in biblio else ""
    title = biblio["title"].strip() + subtitle
    url = biblio["url"].strip()
    comment = biblio["comment"].strip() if biblio["comment"] else ""
    if biblio["tags"]:
        hashtags = ""
        for tag in biblio["tags"].strip().split(" "):
            hashtags += "#%s " % KEY_SHORTCUTS.get(tag, tag)
        hashtags = hashtags.strip()
    else:
        hashtags = "#misc"
    info(f"hashtags = '{hashtags}'")
    html_comment = (
        f'{comment} <a href="{escape_XML(url)}">{escape_XML(title)}</a>'
    )
    date_token = time.strftime("%y%m%d", NOW)
    digest = hashlib.md5(html_comment.encode("utf-8", "replace")).hexdigest()
    uid = "e" + date_token + "-" + digest[:4]
    log_item = (
        f'<li class="event" id="{uid}">{date_token}: '
        f"{hashtags}] {html_comment}</li>"
    )
    info(log_item)

    plan_tree = l_etree.parse(
        ofile, l_etree.XMLParser(ns_clean=True, recover=True)
    )
    ul_found = plan_tree.xpath(
        """//x:div[@id='Done']/x:ul""",
        namespaces={"x": "http://www.w3.org/1999/xhtml"},
    )  # ul_found = plan_tree.xpath('''//div[@id='Done']/ul''')
    info("ul_found = %s" % (ul_found))
    if ul_found:
        ul_found[0].text = "\n              "
        log_item_xml = l_etree.XML(log_item)
        log_item_xml.tail = "\n\n              "
        ul_found[0].insert(0, log_item_xml)
        new_content = l_etree.tostring(
            plan_tree, pretty_print=True, encoding="unicode", method="xml"
        )
        new_plan_fd = open(ofile, "w", encoding="utf-8", errors="replace")
        new_plan_fd.write(new_content)
        new_plan_fd.close()
    else:
        raise RuntimeError("Sorry, not found: //x:div[@id='Done']/x:ul")

    if args.publish:
        yasn_publish(comment, title, subtitle, url, hashtags)