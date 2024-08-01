"""Types for thunderdell.

https://github.com/reagle/thunderdell
"""

from collections.abc import Sequence
from typing import Dict, NamedTuple, Optional
from xml.etree.ElementTree import Element


class Date(NamedTuple):
    """Date structure."""

    year: str
    month: Optional[str] = None
    day: Optional[str] = None
    circa: Optional[bool] = None
    time: Optional[str] = None


class EntryDict(Dict):
    """Structure of entry."""

    _mm_file: str
    _title_node: Element
    author: Sequence[tuple]
    cite: str
    custom1: str
    custom2: str
    date: Date
    entry_type: str
    identifier: str
    number: str
    organization: str
    ori_author: str
    shorttitle: str
    title: str
    url: str
    urldate: Date
