"""Types for thunderdell.

https://github.com/reagle/thunderdell
"""

from typing import NamedTuple
from xml.etree.ElementTree import Element


class PubDate(NamedTuple):
    """Date structure."""

    year: str
    month: str | None = None
    day: str | None = None
    circa: str | None = None
    time: str | None = None


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
