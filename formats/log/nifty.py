"""Personal nifty page logger.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import re
import time

import config

# function aliases
critical = logging.critical
error = logging.error
warning = logging.warning
info = logging.info
debug = logging.debug

NOW = time.localtime()


def log2nifty(args, biblio):
    """
    Log to personal blog.
    """

    print("to log2nifty\n")
    ofile = f"{config.HOME}/data/2web/goatee.net/nifty-stuff.html"

    title = biblio["title"]
    comment = biblio["comment"]
    url = biblio["url"]

    date_token = time.strftime("%y%m%d", NOW)
    log_item = f'<dt><a href="{url}">{title}</a> ({date_token})</dt><dd>{comment}</dd>'

    fd = open(ofile)
    content = fd.read()
    fd.close()

    INSERTION_RE = re.compile('(<dl style="clear: left;">)')
    newcontent = INSERTION_RE.sub(
        "\\1 \n  %s" % log_item, content, re.DOTALL | re.IGNORECASE
    )
    if newcontent:
        fd = open(ofile, "w", encoding="utf-8", errors="replace")
        fd.write(newcontent)
        fd.close()
    else:
        raise RuntimeError("Sorry, output regexp subsitution failed.")
