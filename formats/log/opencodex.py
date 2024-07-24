"""Research blog logger.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import logging as log
import time
from subprocess import Popen

import config
from biblio.keywords import KEY_SHORTCUTS

NOW = time.localtime()


def log2opencodex(args, biblio):
    """
    Start at a blog entry at opencodex
    """

    blog_title = blog_body = ""
    CODEX_ROOT = config.HOME / "data/2web/reagle.org/joseph/content/"
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
        log.info(
            f"blog_title='{blog_title.strip()}' sep='{sep}' "
            f"blog_body='{blog_body.strip()}'"
        )
    log.info(f"blog_title='{blog_title}'")

    filename = (
        blog_title.lower()
        .replace(":", "")
        .replace(" ", "-")
        .replace("'", "")
        .replace("/", "-")
    )
    filename = CODEX_ROOT / category / f"{this_year}-{filename}.md"
    log.info(f"{filename=}")
    if filename.exists():
        raise FileExistsError(f"\nfilename {filename} already exists")

    with filename.open("w", encoding="utf-8", errors="replace") as fd:
        fd.write("---\n")
        fd.write(f"title: {blog_title}\n")
        fd.write(f"date: {time.strftime('%Y-%m-%d', NOW)}\n")
        fd.write(f"tags: {tags}\n")
        fd.write(f"category: {category}\n")
        fd.write("...\n\n")
        fd.write(blog_body.strip())
        if "url" in biblio and "excerpt" in biblio:
            fd.write(f"\n\n[{biblio['title']}]({biblio['url']})\n\n")
            fd.write(f"> {biblio['excerpt']}\n")

    Popen([config.VISUAL, str(filename)])
