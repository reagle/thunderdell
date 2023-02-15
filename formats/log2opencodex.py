#!/usr/bin/env python3
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
import os
import time
from subprocess import Popen

import config
from biblio.keywords import KEY_SHORTCUTS

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


def log2opencodex(args, biblio):
    """
    Start at a blog entry at opencodex
    """

    blog_title = blog_body = ""
    CODEX_ROOT = f"{config.HOME}/data/2web/reagle.org/joseph/content/"
    this_year, this_month, this_day = time.strftime("%Y %m %d", NOW).split()
    blog_title = " ".join(biblio["title"].split(" ")[0:3])
    entry = biblio["comment"]

    category = "social"
    tags = ""
    if biblio["tags"]:
        tags = biblio["tags"].strip().split(" ")
        category = KEY_SHORTCUTS.get(tags[0], tags[0])
        tags_expanded = ""
        for tag in tags:
            tag = KEY_SHORTCUTS.get(tag, tag)
            tags_expanded += tag + ","
        tags = tags_expanded[0:-1]  # removes last comma

    if entry:
        blog_title, sep, blog_body = entry.partition(".")
        info(
            f"blog_title='{blog_title.strip()}' sep='{sep}' "
            f"blog_body='{blog_body.strip()}'"
        )
    info(f"blog_title='{blog_title}'")

    filename = (
        blog_title.lower()
        .replace(":", "")
        .replace(" ", "-")
        .replace("'", "")
        .replace("/", "-")
    )
    filename = f"{CODEX_ROOT}{category}/{this_year}-{filename}.md"
    info(f"{filename=}")
    if os.path.exists(filename):
        raise FileExistsError(f"\nfilename {filename} already exists")
    fd = open(filename, "w", encoding="utf-8", errors="replace")
    fd.write("---\n")
    fd.write("title: %s\n" % blog_title)
    fd.write("date: %s\n" % time.strftime("%Y-%m-%d", NOW))
    fd.write("tags: %s\n" % tags)
    fd.write("category: %s\n" % category)
    fd.write("...\n\n")
    fd.write(blog_body.strip())
    if "url" in biblio and "excerpt" in biblio:
        fd.write("\n\n[%s](%s)\n\n" % (biblio["title"], biblio["url"]))
        fd.write("> %s\n" % biblio["excerpt"])
    fd.close()
    Popen([config.VISUAL, filename])
