#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""
Loggers for BusySponge.

https://github.com/reagle/thunderdell
"""

import logging
import os
import re
import time
from subprocess import Popen

import config

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


def log2goatee(args, biblio):
    """
    Start at a blog entry at goatee
    """

    GOATEE_ROOT = f"{config.HOME}/data/2web/goatee.net/content/"
    info(f"{biblio['comment']=}")
    blog_title, sep, blog_body = biblio["comment"].partition(". ")

    this_year, this_month, this_day = time.strftime("%Y %m %d", NOW).split()
    url = biblio.get("url", None)
    filename = blog_title.lower()

    PHOTO_RE = re.compile(r".*/photo/gallery/(\d\d\d\d/\d\d)/\d\d-\d\d\d\d-(.*)\.jpe?g")
    photo_match = False
    if "goatee.net/photo/" in url:
        photo_match = re.match(PHOTO_RE, url)
        if photo_match:
            # blog_date = re.match(PHOTO_RE, url).group(1).replace("/", "-")
            blog_title = re.match(PHOTO_RE, url).group(2)
            filename = blog_title
            blog_title = blog_title.replace("-", " ")
    filename = filename.strip().replace(" ", "-").replace("'", "")
    filename = GOATEE_ROOT + "{}/{}{}-{}.md".format(
        this_year,
        this_month,
        this_day,
        filename,
    )
    info(f"{blog_title=}")
    info(f"{filename=}")
    if os.path.exists(filename):
        raise FileExistsError(f"\nfilename {filename} already exists")
    fd = open(filename, "w", encoding="utf-8", errors="replace")
    fd.write("---\n")
    fd.write("title: %s\n" % blog_title)
    fd.write("date: %s\n" % time.strftime("%Y-%m-%d", NOW))
    fd.write("tags: \n")
    fd.write("category: \n")
    fd.write("...\n\n")
    fd.write(blog_body.strip())

    if "url":
        if biblio.get("excerpt", False):
            fd.write("\n\n[{}]({})\n\n".format(biblio["title"], biblio["url"]))
            fd.write("> %s\n" % biblio["excerpt"])
        if photo_match:
            path, jpg = url.rsplit("/", 1)
            thumb_url = path + "/thumbs/" + jpg
            alt_text = blog_title.replace("-", " ")
            fd.write(
                """<p><a href="%s"><img alt="%s" class="thumb right" """
                """src="%s"/></a></p>\n\n"""
                % (
                    url,
                    alt_text,
                    thumb_url,
                )
            )
            fd.write(
                f'<p><a href="{url}"><img alt="{alt_text}" '
                f'class="view" src="{url}"/></a></p>'
            )
    fd.close()
    Popen([config.VISUAL, filename])
