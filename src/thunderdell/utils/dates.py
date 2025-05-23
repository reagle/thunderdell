"""Extraction utilities.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
from datetime import datetime

import dateutil.parser as du  # type: ignore


def parse_date(date_str: str, date_format: str = "%Y%m%d") -> str:
    """Detect if epoch seconds or ISO-like, parse, and return formatted string.

    arrow.get is not flexible enough parser, so use dateutil.

    >>> parse_date("1613474400")
    '20210216'
    >>> parse_date("2021-02-16T11:20:00Z")
    '20210216'
    """
    if date_str.isdigit() and len(date_str) == 10:
        # Epoch timestamp in seconds
        dt_result = datetime.fromtimestamp(int(date_str))
    else:
        # ISO-like or other format
        dt_result = du.parse(date_str)
    return dt_result.strftime(date_format)
