"""Web utilities.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import html.entities
import json
import logging
import re
from pathlib import Path
from xml.sax.saxutils import escape  # unescape

import requests  # http://docs.python-requests.org/en/latest/

import config
from biblio.keywords import KEY_SHORTCUTS

log = logging.getLogger("utils_web")
critical = logging.critical
info = logging.info
dbg = logging.debug


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
        raise OSError("URL content is not HTML.")

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
    except requests.exceptions.RequestException as exc:
        raise SystemExit(f"{exc}") from exc
    returned_content_type = r.headers["content-type"].split(";")[0]
    # info(f"{requested_content_type=} == {returned_content_type=}?")
    if requested_content_type == returned_content_type:
        return json.loads(r.content)
    else:
        raise OSError("URL content is not JSON.")


def get_text(url: str) -> str:
    """Textual version of url"""

    import os

    return str(os.popen(f'w3m -O utf8 -cols 10000 -dump "{url}"').read())


def yasn_publish(comment, title, subtitle, url, tags):
    "Send annotated URL to social networks"
    info(f"'{comment=}', {title=}, {subtitle=}, {url=}, {tags=}")
    if tags and tags[0] != "#":  # they've not yet been hashified
        tags = " ".join(
            ["#" + KEY_SHORTCUTS.get(tag, tag) for tag in tags.strip().split(" ")]
        )
    comment, title, subtitle, url, tags = (
        v.strip() if isinstance(v, str) else ""
        for v in [comment, title, subtitle, url, tags]
    )
    if subtitle:
        title = f"{title}: {subtitle}"
    if url[-4:] in (".jpg", ".png"):
        if "goatee.net/photo" in url:
            title = ""
            tags = "#photo #" + url.rsplit("/")[-1][8:-4].replace("-", " #")
            photo_path = Path(f"{config.HOME}/f/{url[19:]}")
        if url.startswith("file://"):
            url.replace("file:///", "file://")
            title = ""
            tags = "#image"
            photo_path = Path(url.split("//", 1)[1])
            if not photo_path.exists():
                raise OSError(f"{photo_path} doesn't exist.")
    else:
        photo_path = None
    if url.startswith("file://"):
        url = ""
    total_len = len(comment) + len(tags) + len(title) + len(url)
    info(f"""comment = {len(comment)}: {comment}
         title = {len(title)}: {title}
         url = {len(url)}: {url}
         tags = {len(tags)}: {tags}
         {total_len=}""")

    twitter_update(comment, title, url, tags, photo_path)
    mastodon_update(comment, title, url, tags, photo_path)


def twitter_update(
    comment: str, title: str, url: str, tags: str, photo_path: Path
) -> None:
    import tweepy  # https://twython.readthedocs.io/en/latest/index.html

    from .web_api_tokens import (
        TW_ACCESS_TOKEN,
        TW_ACCESS_TOKEN_SECRET,
        TW_CONSUMER_KEY,
        TW_CONSUMER_SECRET,
    )

    auth = tweepy.OAuthHandler(TW_CONSUMER_KEY, TW_CONSUMER_SECRET)
    auth.set_access_token(TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET)
    api = tweepy.API(auth)
    try:
        if photo_path:
            tweet = shrink_message("twitter", comment, title, "", tags)
            media = api.media_upload(photo_path)
            api.update_status(status=tweet, media_ids=[media.media_id])
        else:
            tweet = shrink_message("twitter", comment, title, url, tags)
            api.update_status(status=tweet)
    except tweepy.errors.TweepyException as err:
        print(err)
        print(f"tweet failed {len(tweet)}: {tweet}")
    else:
        print(f"tweet worked {len(tweet)}: {tweet}")


def mastodon_update(
    comment: str, title: str, url: str, tags: str, photo_path: Path
) -> None:
    import mastodon  # https://mastodonpy.readthedocs.io/en/stable/

    from .web_api_tokens import (
        MASTODON_APP_BASE,
        OHAI_ACCESS_TOKEN,
    )

    ohai = mastodon.Mastodon(
        access_token=OHAI_ACCESS_TOKEN, api_base_url=MASTODON_APP_BASE
    )
    toot = shrink_message("ohai", comment, title, url, tags)
    try:
        if photo_path:
            photo_fn = Path(photo_path).stem
            photo_desc = " ".join(
                [chunk for chunk in photo_fn.split("-") if not chunk.isdigit()]
            )
            media = ohai.media_post(media_file=str(photo_path), description=photo_desc)
            ohai.status_post(status=toot, media_ids=media)
        else:
            ohai.status_post(status=toot)
    except mastodon.MastodonError as err:
        print(err)
        print(f"toot failed {len(toot)}: {toot}")
    else:
        print(f"toot worked {len(toot)}: {toot}")


def shrink_message(service, comment, title, url, tags):
    """Shrink message to fit into limit"""

    if service == "ohai":  # mastodon instance
        limit = 500
    elif service == "twitter":
        limit = 280
    info(f"{comment=}")
    PADDING = 7  # = comment_delim + title quotes + spaces
    TWITTER_SHORTENER_LEN = 23  # twitter uses t.co
    limit = limit - PADDING

    info(f"{limit=}")
    message_room = limit - len_twitter(tags)
    info(f"message_room - len(tags) = {message_room}")

    info(f"{len_twitter(url)=}")
    if service == "twitter" and len_twitter(url) > TWITTER_SHORTENER_LEN:
        message_room = message_room - TWITTER_SHORTENER_LEN
        info(f"  shortened to {TWITTER_SHORTENER_LEN}")
    else:
        message_room = message_room - len_twitter(url)
    info(f"message_room after url = {message_room}")

    info(f"{len_twitter(title)=}")
    if len_twitter(title) > message_room:
        info("title is too long")
        title = f"{title[:message_room - 1]}…"
        info(f"  truncated to {len_twitter(title)}")
    message_room = message_room - len_twitter(title)
    info(f"{message_room=} after title = ")

    info(f"{len_twitter(comment)=}")
    if len_twitter(comment) > message_room:
        info("comment is too long")
        if message_room > 5:
            info(" truncating")
            comment = f"{comment[:message_room - 1]}…"
            info(f"  truncated to {len_twitter(comment)}")
            info(f"{comment}")
        else:
            info(" skipping")
            comment = ""
    message_room = message_room - len_twitter(comment)
    info(f"message_room after comment = {message_room}")

    comment_delim = ": " if comment and title else ""
    title = f"“{title}”" if title else ""
    message = f"{comment}{comment_delim}{title} {url} {tags}".strip()
    info(f"{len_twitter(message)=}: {message=}")
    return message


def len_twitter(text: str) -> int:
    """
    Twitter counts code units not code points as part of its
    character limit.

    https://developer.twitter.com/en/docs/counting-characters

    """

    return len(text.encode("utf-16-le")) // 2


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

    def fixup_chars(m):
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

    return re.sub(r"&#?\w+;", fixup_chars, text)
