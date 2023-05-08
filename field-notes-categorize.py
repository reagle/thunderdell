#!/usr/bin/env python3
"""Create a categorized mindmap based on the first `kw=` declaration in
each source.
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import pdb
import re
from pathlib import Path

import lxml.etree as et


def categorize_mindmap(old_fn: Path) -> None:
    cat_fn = Path(old_fn.stem + "-cat.mm")
    old_doc = et.parse(old_fn)
    old_map = old_doc.getroot()

    categorized_nodes = {}

    for old_node in old_map.getiterator():
        if old_node.get("STYLE_REF", "default") == "cite":
            print(f"{old_node.get('TEXT')}")
            if "kw=" in old_node.get("TEXT"):
                try:
                    kmatch = re.findall(r"kw=\S+", old_node.get("TEXT"), re.IGNORECASE)
                    keyword = kmatch[0].split("kw=")[1]  # use first keyword
                except IndexError as e:
                    print(
                        f"\nCouldn't find kw=__ value for {old_node.get('TEXT')}: {e=}"
                    )
            else:
                keyword = "UNLABELLED"
            categorized_nodes.setdefault(keyword, []).append(
                old_node.getparent().getparent()
            )

    new_map = et.Element("map", version="1.10.3")
    new_doc = et.ElementTree(new_map)
    root_node = et.SubElement(new_map, "node")
    root_node.set("TEXT", str(cat_fn))

    for keyword, node_list in sorted(
        categorized_nodes.items(), key=lambda t: tuple(t[0].lower())
    ):
        cat_node = et.SubElement(root_node, "node")
        cat_node.set("TEXT", keyword)
        for author_node in node_list:
            cat_node.append(author_node)

    new_doc.write(cat_fn)


if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        description=(
            "Create a categorized mindmap based on the first `kw=` "
            "declaration in each source."
        )
    )
    arg_parser.add_argument(
        "filename",
        metavar="FILENAME",
        help="filename to process",
    )
    args = arg_parser.parse_args()
    old_fn = Path(args.filename)
    categorize_mindmap(old_fn)
