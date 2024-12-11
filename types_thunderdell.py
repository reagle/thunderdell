"""Types for thunderdell.

https://github.com/reagle/thunderdell
"""

from collections.abc import Sequence
from typing import NamedTuple, Optional
from xml.etree.ElementTree import Element


class PubDate(NamedTuple):
    """Date structure."""

    year: str
    month: Optional[str] = None
    day: Optional[str] = None
    circa: Optional[bool] = None
    time: Optional[str] = None


class PersonName(NamedTuple):
    """Name structure."""

    first: str
    middle: str
    last: str
    suffix: str


class EntryDict(dict):
    """Structure of entry."""

    _mm_file: str
    _title_node: Element
    author: list[PersonName]
    cite: str
    custom1: str
    custom2: str
    date: PubDate
    entry_type: str
    identifier: str
    number: str
    organization: str
    ori_author: str
    shorttitle: str
    title: str
    url: str
    urldate: PubDate
