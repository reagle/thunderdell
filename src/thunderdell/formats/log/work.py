"""Work planning page logger.

Uses lxml.html (not lxml.etree) to parse and serialize index.html as HTML5.
This avoids XHTML self-closing tags (e.g., <meta/>) that the W3C validator
flags, and preserves unicode without mojibake.

Pipeline: wiki_update.py (BeautifulSoup) -> work.py (lxml.html) -> tidy
All three tools must produce parseable HTML5 for each other.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"


import logging
import time

from lxml import html as l_html

from thunderdell import config
from thunderdell.biblio.keywords import KEY_SHORTCUTS
from thunderdell.utils.web import xml_escape, yasn_publish

NOW = time.localtime()


def log2work(args, biblio):
    """Log to work microblog."""
    import hashlib

    print("to log2work\n")
    logging.info(f"biblio = '{biblio}'")
    ofile = config.HOME / "data/2web/reagle.org/joseph/plan/index.html"
    logging.info(f"{ofile=}")
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
    logging.info(f"hashtags = '{hashtags}'")
    html_comment = f'{comment} <a href="{xml_escape(url)}">{xml_escape(title)}</a>'
    date_token = time.strftime("%y%m%d", NOW)
    digest = hashlib.md5(html_comment.encode("utf-8", "replace")).hexdigest()
    uid = "e" + date_token + "-" + digest[:5]
    log_item = (
        f'<li class="event" id="{uid}">{date_token}: {hashtags}] {html_comment}</li>'
    )
    logging.info(f"{log_item=}")

    plan_tree = l_html.parse(str(ofile))
    ul_found = plan_tree.xpath("""//div[@id='Done']/ul""")
    logging.info(f"ul_found = {ul_found}")
    if ul_found:
        ul_found[0].text = "\n"  # newline after <ul>
        log_item_xml = l_html.fragment_fromstring(log_item)
        log_item_xml.tail = "\n"  # newline after </li>
        ul_found[0].insert(0, log_item_xml)
        new_content = l_html.tostring(
            plan_tree, pretty_print=True, encoding="unicode", method="html"
        )
        ofile.write_text(new_content, encoding="utf-8")
    else:
        raise RuntimeError("Sorry, not found: //x:div[@id='Done']/x:ul")

    if args.publish:
        yasn_publish(comment, title, subtitle, url, hashtags)
