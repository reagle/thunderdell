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
import os
import re
import time
from collections import namedtuple
from subprocess import Popen, call
from xml.etree.ElementTree import ElementTree, SubElement, parse  # Element,

from lxml import etree as l_etree

import config
import thunderdell as td
from biblio import fields as bf
from biblio.keywords import KEY_SHORTCUTS
from change_case import title_case
from utils.web import escape_XML, yasn_publish

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()
MONTHS = "jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec"

#######################################
# Misc utilities
#######################################


def rotate_files(filename, max=5):
    f"""create at most {max} rotating files"""

    bare, ext = os.path.splitext(filename)
    for counter in reversed(range(2, max + 1)):
        old_filename = f"{bare}{counter-1}{ext}"
        new_filename = f"{bare}{counter}{ext}"
        if os.path.exists(old_filename):
            os.rename(old_filename, new_filename)
    if os.path.exists(filename):
        os.rename(filename, f"{bare}1{ext}")


#######################################
# Output loggers
#######################################


def log2mm(biblio, args):
    """
    Log to bibliographic mindmap, see:
        http://reagle.org/joseph/2009/01/thunderdell.html
    """

    print("to log2mm")
    biblio, args.publish = do_console_annotation(biblio, args)
    info(f"{biblio}")

    # now = time.gmtime()
    this_week = time.strftime("%U", NOW)
    this_year = time.strftime("%Y", NOW)
    date_read = time.strftime("%Y%m%d %H:%M UTC", NOW)

    ofile = (
        f"{config.HOME}/data/2web/reagle.org/joseph/2005/ethno/field-notes.mm"
    )
    info(f"{biblio=}")
    author = biblio["author"]
    title = biblio["title"]
    subtitle = biblio["subtitle"] if "subtitle" in biblio else ""
    abstract = biblio["comment"]
    excerpt = biblio["excerpt"]
    permalink = biblio["permalink"]

    # Create citation
    for token in ["author", "title", "url", "permalink", "type"]:
        if token in biblio:  # not needed in citation
            del biblio[token]
    citation = ""
    for key, value in list(biblio.items()):
        if key in bf.BIB_FIELDS:
            info(f"{key=} {value=}")
            citation += f"{bf.BIB_FIELDS[key]}={value} "
    citation += f" r={date_read} "
    if biblio["tags"]:
        tags = biblio["tags"]
        for tag in tags.strip().split(" "):
            keyword = KEY_SHORTCUTS.get(tag, tag)
            citation += "kw=" + keyword + " "
        citation = citation.strip()
    else:
        tags = ""

    mindmap = parse(ofile).getroot()
    mm_years = mindmap[0]
    for mm_year in mm_years:
        if mm_year.get("TEXT") == this_year:
            year_node = mm_year
            break
    else:
        print(f"creating {this_year}")
        year_node = SubElement(
            mm_years, "node", {"TEXT": this_year, "POSITION": "right"}
        )
        week_node = SubElement(
            year_node, "node", {"TEXT": this_week, "POSITION": "right"}
        )

    for week_node in year_node:
        if week_node.get("TEXT") == this_week:
            print(f"week {this_week}")
            break
    else:
        print(f"creating {this_week}")
        week_node = SubElement(
            year_node, "node", {"TEXT": this_week, "POSITION": "right"}
        )

    author_node = SubElement(
        week_node, "node", {"TEXT": author, "STYLE_REF": "author"}
    )
    title_node = SubElement(
        author_node,
        "node",
        {"TEXT": title, "STYLE_REF": "title", "LINK": permalink},
    )
    cite_node = SubElement(  # noqa: F841
        title_node, "node", {"TEXT": citation, "STYLE_REF": "cite"}
    )
    if abstract:
        abstract_node = SubElement(  # noqa: F84
            title_node, "node", {"TEXT": abstract, "STYLE_REF": "annotation"}
        )
    if excerpt:
        for excerpt_chunk in excerpt.split("\n\n"):
            info(f"{excerpt_chunk=}")
            if excerpt_chunk.startswith(", "):
                style_ref = "paraphrase"
                excerpt_chunk = excerpt_chunk[2:]
            elif excerpt_chunk.startswith(". "):
                style_ref = "annotation"
                excerpt_chunk = excerpt_chunk[2:]
            elif excerpt_chunk.startswith("-- "):
                style_ref = "default"
                excerpt_chunk = excerpt_chunk[3:]
            else:
                style_ref = "quote"
            excerpt_node = SubElement(  # noqa: F84
                title_node,
                "node",
                {"TEXT": excerpt_chunk, "STYLE_REF": style_ref},
            )

    ElementTree(mindmap).write(ofile, encoding="utf-8")

    if args.publish:
        info("YASN")
        yasn_publish(abstract, title, subtitle, permalink, tags)


def log2nifty(biblio, args):
    """
    Log to personal blog.
    """

    print("to log2nifty\n")
    ofile = f"{config.HOME}/data/2web/goatee.net/nifty-stuff.html"

    title = biblio["title"]
    comment = biblio["comment"]
    url = biblio["url"]

    date_token = time.strftime("%y%m%d", NOW)
    log_item = (
        f'<dt><a href="{url}">{title}</a> '
        f"({date_token})</dt><dd>{comment}</dd>"
    )

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


def log2work(biblio, args):
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


def log2console(biblio, args):
    """
    Log to console.
    """

    TOKENS = (
        "author",
        "title",
        "subtitle",
        "date",
        "journal",
        "volume",
        "number",
        "publisher",
        "address",
        "DOI",
        "isbn",
        "tags",
        "comment",
        "excerpt",
        "url",
    )
    info(f"biblio = '{biblio}'")
    if biblio["tags"]:
        tags = biblio["tags"].strip().split(" ")
        tags_expanded = ""
        for tag in tags:
            tag = KEY_SHORTCUTS.get(tag, tag)
            tags_expanded += tag + " "
        # biblio['keywords'] = tags_expanded[0:-1]  # removes last space
    bib_in_single_line = ""
    for token in TOKENS:
        info(f"token = '{token}'")
        if token not in biblio:
            if token == "url":  # I want these printed even if don't exist
                biblio["url"] = ""
            elif token == "title":
                biblio["title"] = ""
            elif token == "subtitle":
                biblio["subtitle"] = ""
        if token in biblio and biblio[token]:
            if token == "tags":
                for value in tags_expanded.strip().split(" "):
                    # print('keyword = %s' % value)
                    bib_in_single_line += "keyword = %s " % value
            else:
                # print(('%s = %s' % (token, biblio[token])))
                bib_in_single_line += "%s = %s " % (token, biblio[token])
    print(f"{bib_in_single_line}")
    if "identifiers" in biblio:
        for identifer, value in list(biblio["identifiers"].items()):
            if identifer.startswith("isbn"):
                print(f"{identifer} = {value[0]}")

    if args.publish:
        yasn_publish(
            biblio["comment"],
            biblio["title"],
            biblio["subtitle"],
            biblio["url"],
            biblio["tags"],
        )
    return bib_in_single_line


def blog_at_opencodex(biblio, args):
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


def blog_at_goatee(biblio, args):
    """
    Start at a blog entry at goatee
    """

    GOATEE_ROOT = f"{config.HOME}/data/2web/goatee.net/content/"
    info(f"{biblio['comment']=}")
    blog_title, sep, blog_body = biblio["comment"].partition(". ")

    this_year, this_month, this_day = time.strftime("%Y %m %d", NOW).split()
    url = biblio.get("url", None)
    filename = blog_title.lower()

    PHOTO_RE = re.compile(
        r".*/photo/gallery/(\d\d\d\d/\d\d)" r"/\d\d-\d\d\d\d-(.*)\.jpe?g"
    )
    photo_match = False
    if "goatee.net/photo/" in url:
        photo_match = re.match(PHOTO_RE, url)
        if photo_match:
            # blog_date = re.match(PHOTO_RE, url).group(1).replace("/", "-")
            blog_title = re.match(PHOTO_RE, url).group(2)
            filename = blog_title
            blog_title = blog_title.replace("-", " ")
    filename = filename.strip().replace(" ", "-").replace("'", "")
    filename = GOATEE_ROOT + "%s/%s%s-%s.md" % (
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
            fd.write("\n\n[%s](%s)\n\n" % (biblio["title"], biblio["url"]))
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


def do_console_annotation(biblio, args):
    """Augment biblio with console annotations"""

    Date = namedtuple("Date", ["year", "month", "day", "circa", "time"])

    def get_tentative_ident(biblio):  # TODO: import from elsewhere? 2021-07-09
        info(biblio)
        return td.get_ident(
            {
                "author": td.parse_names(biblio["author"]),
                "title": biblio["title"],
                # 'date': biblio['date'][0:4],
                "date": Date(
                    year=biblio["date"][0:4],
                    month=None,
                    day=None,
                    circa=None,
                    time=None,
                ),
                "_mm_file": "CONSOLE",
            },
            {},
        )

    def edit_annotation(initial_text, resume_edit=False):
        """Write initial bib info to a tmp file, edit and return"""

        annotation_fn = f"{config.TMP_DIR}b-annotation.txt"
        if not resume_edit:
            rotate_files(annotation_fn)
            if os.path.exists(annotation_fn):
                os.remove(annotation_fn)
            with open(annotation_fn, "w", encoding="utf-8") as annotation_file:
                annotation_file.write(initial_text)
        call([config.EDITOR, annotation_fn])
        return open(annotation_fn, "r", encoding="utf-8").readlines()

    def parse_bib(biblio, edited_text, args):
        """Parse the bib assignments"""

        # biblio['tags'] and whether to yasn publish are overwritten by
        # pre-populated and then edited console annotation
        biblio["tags"] = ""
        do_publish = False
        from_Instapaper = False  # are following lines Instapaper markdown?
        console_annotations = ""
        biblio["comment"] = ""

        print(("@%s\n" % (tentative_id)))
        EQUAL_PAT = re.compile(r"(\w{1,3})=")
        for line in edited_text:
            info(f"{line=}")
            line = line.replace("\u200b", "")  # Instapaper export artifact
            line = line.strip()
            if line == "":
                continue
            if line.startswith("# ["):
                from_Instapaper = True
                info(f"{from_Instapaper=}")
                continue
            if line == "-p":
                do_publish = True
                warning(f"{do_publish=}")
            elif line.startswith("s."):
                biblio["comment"] = line[2:].strip()
                info(f"{biblio['comment']=}")
            elif "=" in line[0:3]:  # citation only if near start of line
                cites = EQUAL_PAT.split(line)[1:]
                # 2 refs to an iterable are '*' unpacked and rezipped
                cite_pairs = list(zip(*[iter(cites)] * 2))
                info(f"{cite_pairs=}")
                for short, value in cite_pairs:
                    info(f"{bf.BIB_SHORTCUTS=}")
                    info(f"{bf.BIB_TYPES=}")
                    info(f"short,value = {short},{value}")
                    # if short == "t":  # 't=phdthesis'
                    # biblio[bf.BIB_SHORTCUTS[value]] = biblio["c_web"]
                    if short == "kw":  # 'kw=complicity
                        biblio["tags"] += " " + value.strip()
                    else:
                        biblio[bf.BIB_SHORTCUTS[short]] = value.strip()
            else:
                if from_Instapaper:
                    if line.startswith(">"):
                        line = line[1:]  # remove redundant quote mark
                    elif line.startswith("-"):
                        pass  # leave comments alone
                    else:
                        line = ", " + line  # prepend paraphrase mark
                console_annotations += "\n\n" + line.strip()

        info("biblio.get('excerpt', '') = '%s'" % (biblio.get("excerpt", "")))
        info(f"console_annotations = '{console_annotations}'")
        biblio["excerpt"] = biblio.get("excerpt", "") + console_annotations

        # See if there is a container/bf.CSL_SHORTCUTS redundant with 'c_web'
        if (
            "c_web" in biblio
            and len(
                list(
                    biblio[c]
                    for c in list(bf.CSL_SHORTCUTS.values())
                    if c in biblio
                )
            )
            > 1
        ):
            del biblio["c_web"]
        return biblio, do_publish

    # code of do_console_annotation
    info(f"{biblio['author']=}")
    tentative_id = get_tentative_ident(biblio)
    initial_text = [
        f"d={biblio['date']} au={biblio['author']} ti={biblio['title']}"
    ]
    for key in biblio:
        if key.startswith("c_"):
            initial_text.append(
                f"{bf.CSL_FIELDS[key]}={title_case(biblio[key])}"
            )
        if key == "tags" and biblio["tags"]:
            tags = " ".join(
                [
                    "kw=" + KEY_SHORTCUTS.get(tag, tag)
                    for tag in biblio["tags"].strip().split(" ")
                ]
            )
            initial_text.append(tags)
    if args.publish:
        warning("appending -p to text")
        initial_text.append("-p")
    if "comment" in biblio and biblio["comment"].strip():
        initial_text.append("s. " + biblio["comment"])
    initial_text = "\n".join(initial_text) + "\n"
    edited_text = edit_annotation(initial_text)
    try:
        biblio, do_publish = parse_bib(biblio, edited_text, args)
    except (TypeError, KeyError) as e:
        print(("Error parsing biblio assignments: %s\nTry again." % e))
        time.sleep(2)
        edited_text = edit_annotation("", resume_edit=True)
        biblio, do_publish = parse_bib(biblio, edited_text, args)

    tweaked_id = get_tentative_ident(biblio)
    if tweaked_id != tentative_id:
        print(("logged: %s to" % get_tentative_ident(biblio)), end="\n")
    return biblio, do_publish
