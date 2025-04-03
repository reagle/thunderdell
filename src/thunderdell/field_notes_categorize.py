#!/usr/bin/env python3
"""Create a categorized mindmap based on the first `kw=` declaration in each source."""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import re
from pathlib import Path

import lxml.etree as et


def categorize_mindmap(old_fn: Path) -> None:
    """Create a categorized mindmap based on the first `kw=` declaration in each source."""
    cat_fn = Path(old_fn.stem + "-cat.mm")
    old_doc = et.parse(old_fn)
    old_map = old_doc.getroot()

    categorized_nodes = {}

    for old_node in old_map.iter():
        if old_node.get("STYLE_REF", "default") == "cite":
            keyword = "UNLABELLED"
            title_node = old_node.getparent()
            assert title_node is not None, (
                f"Title node missing for {old_node.get('TEXT', '')}"
            )
            author_node = title_node.getparent()
            assert author_node is not None, (
                f"Author node missing for {old_node.get('TEXT', '')}"
            )
            old_node_text = old_node.get("TEXT", "")
            print(f"{old_node_text}")
            if "kw=" in old_node_text:
                try:
                    kmatch = re.findall(r"kw=\S+", old_node_text, re.IGNORECASE)
                    keyword = kmatch[0].split("kw=")[1]  # use first keyword
                except IndexError as e:
                    print(f"\nCouldn't find kw=__ value for {old_node_text}: {e=}")
            categorized_nodes.setdefault(keyword, []).append(author_node)

    new_map = et.Element("map", version="freeplane 1.12.1")
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


def main():
    import sys

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
    args = arg_parser.parse_args(sys.argv[1:])
    old_fn = Path(args.filename)
    categorize_mindmap(old_fn)


if __name__ == "__main__":
    main()
