"""Textual utilities.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import re
from typing import Any

from unidecode import unidecode


def escape_latex(text: str) -> str:
    r"""Escape special LaTeX characters.

    >>> escape_latex('100% & $5 #tag')
    '100\\% \\& \\$5 \\#tag'
    >>> escape_latex('under_score {curly} ~tilde')
    'under\\_score \\{curly\\} \\~{}tilde'
    """
    return f"{text}".translate(
        str.maketrans(
            {
                "$": r"\$",
                "&": r"\&",
                "%": r"\%",
                "#": r"\#",
                "_": r"\_",
                "{": r"\{",
                "}": r"\}",
                "~": r"\~{}",
                "^": r"\^{}",
            }
        )
    )


def normalize_whitespace(text: str) -> str:
    """Remove redundant whitespace from a string, including before comma.

    >>> normalize_whitespace('sally, joe , john')
    'sally, joe, john'
    >>> normalize_whitespace('too   many     spaces')
    'too many spaces'
    """
    text = text.replace(" ,", ",")
    text = " ".join(text.split())
    return text


def pretty_tabulate_list(mylist: list[str], cols: int = 4) -> str:
    """Format a list into columns."""
    mylist.sort()
    pairs = [
        "".join(f"{item:20}" for item in mylist[i : i + cols])
        for i in range(0, len(mylist), cols)
    ]
    return "\n" + "\n".join(pairs)


def pretty_tabulate_dict(mydict: dict[str, Any], cols: int = 4) -> str:
    """Format a dictionary into columns."""
    return pretty_tabulate_list(
        [f"{key}:{value}" for key, value in mydict.items()], cols
    )


def strip_accents(text: str) -> str:
    """Strip accents and transliterate non-ASCII characters.

    >>> strip_accents('nôn-åscîî')
    'non-ascii'
    >>> strip_accents('Søren Dinesen Østergaard')
    'Soren Dinesen Ostergaard'
    """
    return unidecode(text)


def smart_to_markdown(text: str) -> str:
    """Convert smart quotes and dashes to markdown format.

    >>> smart_to_markdown('“Hello,” she said.')
    '"Hello," she said.'
    >>> smart_to_markdown('It’s a win–win situation—really!')
    "It's a win--win situation---really!"
    """
    # Replace smart quotes and dashes using replace() method
    return text.translate(
        str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'", "–": "--", "—": "---"})
    )


def html_to_text(text: str) -> str:
    """Extract text content from HTML.

    >>> html_to_text('<p>Hello <b>world</b>!</p>')
    'Hello world!'
    >>> html_to_text('<div>Line 1<br/>Line 2</div>')
    'Line 1Line 2'
    """
    import xml.etree.ElementTree

    return "".join(xml.etree.ElementTree.fromstring(text).itertext())


def truncate_text(text: str, length: int) -> str:
    """Truncate text at sentence boundary if possible.

    >>> truncate_text('This is short. This is long and will be cut.', 20)
    'This is short.'
    >>> truncate_text('This is a very long sentence without punctuation', 20)
    'This is a very long…'
    """
    fragments = re.split("([.!?])", text.strip())

    # If no sentence boundaries found, truncate at character limit
    if len(fragments) == 1:
        if len(text) > length:
            return text[: length - 1] + "…"
        return text

    result = fragments.pop(0)
    for fragment in fragments:
        if len(result) + len(fragment) >= length:
            if len(result) >= length:
                result = result[: length - 1] + "…"
            return result
        result = result + fragment
    return result
