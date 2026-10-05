"""Personal nifty page logger.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import re
import time

from thunderdell import config

NOW = time.localtime()


def log2nifty(args, biblio):
    """Log to personal blog."""
    print("to log2nifty\n")
    ofile = config.HOME / "data/2web/goatee.net/nifty-stuff.html"

    title = biblio["title"]
    comment = biblio["comment"]
    url = biblio["url"]

    date_token = time.strftime("%y%m%d", NOW)
    log_item = f'<dt><a href="{url}">{title}</a> ({date_token})</dt><dd>{comment}</dd>'

    content = ofile.read_text(encoding="utf-8")

    INSERTION_RE = re.compile('(<dl style="clear: left;">)', re.IGNORECASE)
    # A function replacement keeps backslashes in the title or comment literal.
    # (The flags used to be passed as sub's count argument.)
    newcontent, count = INSERTION_RE.subn(
        lambda match: f"{match[1]} \n  {log_item}", content, count=1
    )
    if count:
        ofile.write_text(newcontent, encoding="utf-8")
    else:
        raise RuntimeError("Sorry, output regexp substitution failed.")
