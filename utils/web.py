#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2021 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
"""
Web functionality I frequently make use of.
"""

import html.entities
import json
import logging
import os
import re
from xml.sax.saxutils import escape  # unescape

import requests  # http://docs.python-requests.org/en/latest/

import config
from biblio.keywords import KEY_SHORTCUTS

HOMEDIR = os.path.expanduser("~")

log = logging.getLogger("utils_web")
critical = logging.critical
info = logging.info
dbg = logging.debug


def escape_XML(s):  # http://wiki.python.org/moin/EscapingXml
    """Escape XML character entities; & < > are defaulted"""
    extras = {"\t": "  "}
    return escape(s, extras)


def unescape_XML(text):  # .0937s 4.11%
    """
    Removes HTML or XML character references and entities from text.
    http://effbot.org/zone/re-sub.htm#unescape-htmlentitydefs
    Marginally faster than `from xml.sax.saxutils import escape, unescape`

    """

    def fixup(m):
        text = m.group(0)
        if text[:2] == "&#":
            # character reference
            try:
                if text[:3] == "&#x":
                    return chr(int(text[3:-1], 16))
                else:
                    return chr(int(text[2:-1]))
            except ValueError:
                pass
        else:
            # named entity
            try:
                text = chr(html.entities.name2codepoint[text[1:-1]])
            except KeyError:
                pass
        return text  # leave as is

    return re.sub(r"&#?\w+;", fixup, text)


def get_HTML(
    url,
    referer="",
    data=None,
    cookie=None,
    retry_counter=0,
    cache_control=None,
):
    """Return [HTML content, response] of a given URL."""

    from lxml import etree

    agent_headers = {"User-Agent": "Thunderdell/BusySponge"}
    r = requests.get(url, headers=agent_headers, verify=True)
    # info(f"{r.headers['content-type']=}")
    if "html" in r.headers["content-type"]:
        HTML_bytes = r.content
    else:
        raise IOError("URL content is not HTML.")

    parser_html = etree.HTMLParser()
    doc = etree.fromstring(HTML_bytes, parser_html)
    HTML_parsed = doc

    HTML_utf8 = etree.tostring(HTML_parsed, encoding="utf-8")
    HTML_unicode = HTML_utf8.decode("utf-8", "replace")

    return HTML_bytes, HTML_parsed, HTML_unicode, r


def get_JSON(
    url,
    referer="",
    data=None,
    cookie=None,
    retry_counter=0,
    cache_control=None,
    requested_content_type="application/json",
):
    """Return [JSON content, response] of a given URL."""

    AGENT_HEADERS = {"User-Agent": "Thunderdell/BusySponge"}
    # info(f"{url=}")
    try:
        r = requests.get(url, headers=AGENT_HEADERS, verify=True)
        r.raise_for_status()
    except requests.exceptions.RequestException as e:
        raise SystemExit(f"{e}")
    returned_content_type = r.headers["content-type"].split(";")[0]
    # info(f"{requested_content_type=} == {returned_content_type=}?")
    if requested_content_type == returned_content_type:
        json_content = json.loads(r.content)
        return json_content
    else:
        raise IOError("URL content is not JSON.")


def get_text(url):
    """Textual version of url"""

    import os

    return str(os.popen(f'w3m -O utf8 -cols 10000 -dump "{url}"').read())


def shrink(service, comment, title, url, tags):
    """Shrink message to fit into limit"""

    if service == "twitter":
        limit = 280
    if service == "octodon":
        limit = 500
    info(f"{comment=}")
    PADDING = 7  # = comment_delim + title quotes + spaces
    TWITTER_SHORTENER_LEN = 23  # twitter uses t.co
    limit = limit - PADDING

    info(f"{limit=}")
    message_room = limit - len(tags)
    info(f"message_room - len(tags) = {message_room}")

    info(f"len(url) = {len(url)}")
    if service == "twitter" and len(url) > TWITTER_SHORTENER_LEN:
        message_room = message_room - TWITTER_SHORTENER_LEN
        info(f"  shortened to {TWITTER_SHORTENER_LEN}")
    else:
        message_room = message_room - len(url)
    info(f"message_room after url = {message_room}")

    info(f"len(title) = {len(title)}")
    if len(title) > message_room:
        info("title is too long")
        title = title[0 : message_room - 1] + "…"
        info(f"  truncated to {len(title)}")
    message_room = message_room - len(title)
    info(f"message_room after title = {message_room}")

    info(f"len(comment) = {len(comment)}")
    if len(comment) > message_room:
        info("comment is too long")
        if message_room > 5:
            info(" truncating")
            comment = comment[0 : message_room - 1] + "…"
            info(f"  truncated to {len(comment)}")
            info(f"{comment}")
        else:
            info(" skipping")
            comment = ""
    message_room = message_room - len(comment)
    info(f"message_room after comment = {message_room}")

    comment_delim = ": " if comment and title else ""
    title = f"“{title}”" if title else ""
    message = f"{comment}{comment_delim}{title} {url} {tags}"
    return message.strip()


def yasn_publish(comment, title, subtitle, url, tags):
    "Send annotated URL to social networks"
    info(f"'{comment=}', {title=}, {subtitle=}, {url=}, {tags=}")
    if tags and tags[0] != "#":  # they've not yet been hashified
        tags = " ".join(
            ["#" + KEY_SHORTCUTS.get(tag, tag) for tag in tags.strip().split(" ")]
        )
    comment, title, subtitle, url, tags = [
        v.strip() if isinstance(v, str) else ""
        for v in [comment, title, subtitle, url, tags]
    ]
    if subtitle:
        title = f"{title}: {subtitle}"
    if url[-4:] in (".jpg", ".png"):
        if "goatee.net/photo" in url:
            title = ""
            tags = "#photo #" + url.rsplit("/")[-1][8:-4].replace("-", " #")
            photo_fn = f"{config.HOME}/f/{url[19:]}"
        if url.startswith("file://"):
            title = ""
            tags = "#image"
            photo_fn = url[7:]
            if not os.path.exists(photo_fn):
                raise IOError(f"{{photo_fn}} doesn't exist.")
    else:
        photo_fn = None
    if url.startswith("file://"):
        url = ""
    total_len = len(comment) + len(tags) + len(title) + len(url)
    info(
        f"""comment = {len(comment)}: {comment}
         title = {len(title)}: {title}
         url = {len(url)}: {url}
         tags = {len(tags)}: {tags}
         {total_len=}"""
    )

    # Twitter
    # https://twython.readthedocs.io/en/latest/index.html
    import tweepy

    from .web_api_tokens import (
        TW_CONSUMER_KEY,
        TW_CONSUMER_SECRET,
        TW_ACCESS_TOKEN,
        TW_ACCESS_TOKEN_SECRET,
    )

    auth = tweepy.OAuthHandler(TW_CONSUMER_KEY, TW_CONSUMER_SECRET)
    auth.set_access_token(TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    try:
        tweet = shrink("twitter", comment, title, "", tags)
        if photo_fn:
            media = api.media_upload(photo_fn)
            api.update_status(status=tweet, media_ids=[media.media_id])
        else:
            api.update_status(status=tweet)
    except tweepy.TweepError as err:
        print(err)
        print(f"tweet failed {len(tweet)}: {tweet}")
    else:
        print(f"tweet worked {len(tweet)}: {tweet}")

    # Mastodon
    import mastodon  # https://mastodonpy.readthedocs.io/en/stable/

    from .web_api_tokens import (
        MASTODON_APP_BASE,
        OCTODON_ACCESS_TOKEN,
    )

    octodon = mastodon.Mastodon(
        access_token=OCTODON_ACCESS_TOKEN, api_base_url=MASTODON_APP_BASE
    )
    toot = shrink("octodon", comment, title, url, tags)
    try:
        if photo_fn:
            media = octodon.media_post(photo_fn)
            octodon.status_post(status=toot, media_ids=media)
        else:
            octodon.status_post(status=toot)
    except mastodon.MastodonError as err:
        print(err)
        print(f"toot failed {len(toot)}: {toot}")
    else:
        print(f"toot worked {len(toot)}: {toot}")
