"""Textual utilities.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import re
import unicodedata

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug


def escape_latex(text: str) -> str:
    """Escape common characters for Latex"""

    text = (
        text.replace("$", r"\$")
        .replace("&", r"\&")
        .replace("%", r"\%")
        .replace("#", r"\#")
        .replace("_", r"\_")
        .replace("{", r"\{")
        .replace("}", r"\}")
        .replace("~", r"\~{}")
        .replace("^", r"\^{}")
    )
    return text


def normalize_whitespace(text: str) -> str:
    """Remove redundant whitespace from a string, including before comma
    >>> normalize_whitespace('sally, joe , john')
    'sally, joe, john'

    """
    text = text.replace(" ,", ",")
    text = " ".join(text.split())
    return text


def pretty_tabulate_list(mylist: list, cols: int = 4) -> str:
    mylist.sort()
    pairs = [
        "".join(["%20s" % j for j in mylist[i : i + cols]])
        for i in range(0, len(mylist), cols)
    ]
    return "\n" + "\n".join(pairs)


def pretty_tabulate_dict(mydict: dict, cols: int = 4) -> str:
    return pretty_tabulate_list(
        [f"{key}:{value}" for key, value in mydict.items()], cols
    )


def strip_accents(text: str) -> str:
    """strip accents and those chars that can't be stripped"""
    # >>> strip_accents(u'nôn-åscîî')
    # ^ fails because of doctest bug u'non-ascii'
    try:  # test if ascii
        text.encode("ascii")
    except UnicodeEncodeError:
        return "".join(
            x
            for x in unicodedata.normalize("NFKD", text)
            if unicodedata.category(x) != "Mn"
        )
    else:
        return text


def smart_to_markdown(text: str) -> str:
    """Convert unicode punctuation (i.e., "smart quotes") to markdown form."""
    text = (
        text.replace("“", '"')
        .replace("”", '"')
        .replace("‘", "'")
        .replace("’", "'")
        .replace("–", "--")
        .replace("—", "---")
    )
    return text


def html_to_text(text: str) -> str:
    import xml.etree.ElementTree

    return "".join(xml.etree.ElementTree.fromstring(text).itertext())


def truncate_text(text: str, length: int) -> str:
    fragments = re.split("([.!?])", text.strip())
    result = fragments.pop(0)
    for fragment in fragments:
        print(f"{result=}")
        print(f"{fragment=}")
        if len(result) + len(fragment) >= length:
            if len(result) >= length:
                result = result[0 : length - 1] + "…"
            return result
        result = result + fragment
    return result
