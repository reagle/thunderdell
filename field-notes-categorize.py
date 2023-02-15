#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2022 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

""" Create a categorized (based on `kw=`) mindmap from a chronological one. """

import argparse  # http://docs.python.org/dev/library/argparse.html
import os
import re

import lxml.etree as et

arg_parser = argparse.ArgumentParser(
    description=(
        "Transform mindmap organized by weeks into one organized by categories, which"
        " are populated using the first `kw=foo` bibliography field of each entry."
    )
)
arg_parser.add_argument(
    "filename",
    metavar="FILENAME",
    help="filename to process",
)
args = arg_parser.parse_args()
old_fn = args.filename
fileName, extension = os.path.splitext(old_fn)
cat_fn = f"{fileName}-cat.mm"

old_doc = et.parse(old_fn)
old_map = old_doc.getroot()

categorized_nodes = {}

for old_node in old_map.getiterator():
    if old_node.get("STYLE_REF", "default") == "cite":
        if "kw=" in old_node.get("TEXT"):
            kmatch = re.findall(r"kw=\S+", old_node.get("TEXT"), re.IGNORECASE)
            keyword = kmatch[0].split("kw=")[1]  # use first keyword
        else:
            keyword = "UNLABELLED"
        categorized_nodes.setdefault(keyword, []).append(
            old_node.getparent().getparent()
        )


new_map = et.Element("map", version="1.10.3")
new_doc = et.ElementTree(new_map)
root_node = et.SubElement(new_map, "node")
root_node.set("TEXT", "%s" % cat_fn)

for keyword, node_list in sorted(  # make tuple sort case insensitive
    categorized_nodes.items(), key=lambda t: tuple(t[0].lower())
):
    cat_node = et.SubElement(root_node, "node")
    cat_node.set("TEXT", keyword)
    for author_node in node_list:
        cat_node.append(author_node)

new_doc.write(cat_fn)
