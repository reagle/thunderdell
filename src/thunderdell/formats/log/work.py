"""Work planning page logger.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging as log
import time
import unicodedata

from lxml import etree as l_etree

from thunderdell import config
from thunderdell.biblio.keywords import KEY_SHORTCUTS
from thunderdell.utils.web import escape_XML, yasn_publish

NOW = time.localtime()


def log2work(args, biblio):
    """Log to work microblog."""
    import hashlib

    print("to log2work\n")
    log.info(f"biblio = '{biblio}'")
    ofile = config.HOME / "data/2web/reagle.org/joseph/plan/index.html"
    log.info(f"{ofile=}")
    subtitle = biblio["subtitle"].strip() if "subtitle" in biblio else ""
    title = biblio["title"].strip() + subtitle
    url = biblio["url"].strip()
    comment = biblio["comment"].strip() if biblio["comment"] else ""
    if biblio["tags"]:
        hashtags = ""
        for tag in biblio["tags"].strip().split(" "):
            hashtags += f"#{KEY_SHORTCUTS.get(tag, tag)} "
        hashtags = hashtags.strip()
    else:
        hashtags = "#misc"
    log.info(f"hashtags = '{hashtags}'")
    html_comment = f'{comment} <a href="{escape_XML(url)}">{escape_XML(title)}</a>'
    date_token = time.strftime("%y%m%d", NOW)
    digest = hashlib.md5(html_comment.encode("utf-8", "replace")).hexdigest()
    uid = "e" + date_token + "-" + digest[:5]
    log_item = (
        f'<li class="event" id="{uid}">{date_token}: {hashtags}] {html_comment}</li>'
    )
    log.info(f"{log_item=}")

    plan_tree = l_etree.parse(
        str(ofile), l_etree.XMLParser(ns_clean=True, recover=True)
    )
    ul_found = plan_tree.xpath("""//div[@id='Done']/ul""")
    log.info(f"ul_found = {ul_found}")
    if ul_found:
        ul_found[0].text = "\n              "
        try:  # lxml bug https://bugs.launchpad.net/lxml/+bug/1902364
            log_item_xml = l_etree.XML(log_item)
        except l_etree.XMLSyntaxError:
            # if lxml chokes on unicode, convert to ascii
            log_item_xml = l_etree.XML(
                unicodedata.normalize("NFKD", log_item).encode("ascii", "ignore")
            )
        log_item_xml.tail = "\n\n      "
        ul_found[0].insert(0, log_item_xml)
        new_content = l_etree.tostring(
            plan_tree, pretty_print=True, encoding="unicode", method="xml"
        )
        ofile.write_text(new_content, encoding="utf-8")
    else:
        raise RuntimeError("Sorry, not found: //x:div[@id='Done']/x:ul")

    if args.publish:
        yasn_publish(comment, title, subtitle, url, hashtags)
