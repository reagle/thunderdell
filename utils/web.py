"""Web utilities.

https://github.com/reagle/thunderdell
"""

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import html.entities
import json
import logging as log
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape  # unescape

import requests  # http://docs.python-requests.org/en/latest/
from lxml import etree

import config
from biblio.keywords import KEY_SHORTCUTS

log = log.getLogger("utils_web")


def get_HTML(
    url: str,
    referer: str = "",
    data: str = "",
    cookie: str = "",
    retry_counter: int = 0,
    cache_control: str = "",
) -> tuple[bytes, etree._Element, str, requests.Response]:
    """Return [HTML content, response] of a given URL."""
    agent_headers = {"User-Agent": "Thunderdell/BusySponge"}
    req = requests.get(url, headers=agent_headers, verify=True)

    if "html" not in req.headers.get("content-type", ""):
        raise OSError("URL content is not HTML.")

    HTML_bytes = req.content

    # Detect the encoding from the response
    encoding = req.encoding or "utf-8"

    # Parse the HTML using the detected encoding
    parser_html = etree.HTMLParser(encoding=encoding)
    HTML_parsed = etree.fromstring(HTML_bytes, parser_html)

    # Decode the bytes to a Unicode string using the detected encoding
    HTML_unicode = HTML_bytes.decode(encoding, "replace")

    return HTML_bytes, HTML_parsed, HTML_unicode, req


def get_JSON(
    url,
    referer="",
    data=None,
    cookie=None,
    retry_counter=0,
    cache_control=None,
    requested_content_type="application/json",
) -> dict[str, Any]:
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
        raise OSError(f"URL content is not JSON. {url=}")


def get_text(url: str) -> str:
    """Textual version of url."""
    import os

    return str(os.popen(f'w3m -O utf8 -cols 10000 -dump "{url}"').read())


def yasn_publish(comment: str, title: str, subtitle: str, url: str, tags: str) -> None:
    """Send annotated URL to social networks."""
    log.info(f"'{comment=}', {title=}, {subtitle=}, {url=}, {tags=}")
    photo_path = None

    if tags and tags[0] != "#":  # they've not yet been hashified
        tags = " ".join(
            [f"#{KEY_SHORTCUTS.get(tag, tag)}" for tag in tags.strip().split(" ")]
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
            photo_path = config.HOME / "f" / url[19:]
        if url.startswith("file://"):
            url.replace("file:///", "file://")
            title = ""
            tags = "#image"
            photo_path = Path(url.split("//", 1)[1])
            if not photo_path.exists():
                raise OSError(f"{photo_path} doesn't exist.")
    if url.startswith("file://"):
        url = ""
    total_len = len(comment) + len(tags) + len(title) + len(url)
    log.info(
        f"""comment = {len(comment)}: {comment}
         title = {len(title)}: {title}
         url = {len(url)}: {url}
         tags = {len(tags)}: {tags}
         {total_len=}"""
    )

    twitter_update(comment, title, url, tags, photo_path)
    mastodon_update(comment, title, url, tags, photo_path)


def twitter_update(
    comment: str, title: str, url: str, tags: str, photo_path: Path | None
) -> None:
    """Update the authenticated Twitter account with a tweet and optional photo."""
    # https://github.com/trevorhobenshield/twitter-api-client
    import orjson
    from httpx import Client
    from twitter.account import Account
    from twitter.util import init_session

    from config import TMP_DIR
    from utils.web_api_tokens import (
        TW_EMAIL,
        TW_PASSWORD,
        TW_USERNAME,
    )

    # https://github.com/trevorhobenshield/twitter-api-client/issues/64
    cookies_fp = TMP_DIR / "twitter.cookies"
    # TODO: deal with expired cookies 2023-06-06
    if cookies_fp.exists():
        cookies = orjson.loads(cookies_fp.read_bytes())
        session = Client(cookies=cookies)
        account = Account(session=session)
        log.info(f"using existing {cookies=}")
    else:
        session = init_session()
        account = Account(
            email=TW_EMAIL, username=TW_USERNAME, password=TW_PASSWORD, save=False
        )
        cookies = {
            k: v
            for k, v in account.session.cookies.items()
            if k in {"ct0", "auth_token"}
        }
        cookies_fp.write_bytes(orjson.dumps(cookies))
        log.info(f"using new {cookies=}")

    if photo_path:
        shrunk_msg = shrink_message("twitter", comment, title, "", tags)
        account.tweet(shrunk_msg, media=[{"media": str(photo_path)}])
    else:
        shrunk_msg = shrink_message("twitter", comment, title, url, tags)
        account.tweet(shrunk_msg)
    print(f"tweet worked {len(shrunk_msg)}: {shrunk_msg}")


def mastodon_update(
    comment: str, title: str, url: str, tags: str, photo_path: Path | None
) -> None:
    """Update the authenticated Mastodon account with a tweet and optional photo."""
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
        if photo_path and photo_path.is_file():
            photo_fn = photo_path.stem
            photo_desc = " ".join(
                chunk for chunk in photo_fn.split("-") if not chunk.isdigit()
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


def shrink_message(service: str, comment: str, title: str, url: str, tags: str) -> str:
    """Shrink message to fit into character limit."""
    limit = 500
    if service == "ohai":  # mastodon instance
        limit = 500
    elif service == "twitter":
        limit = 280
    log.info(f"{comment=}")
    PADDING = 7  # = comment_delim + title quotes + spaces
    TWITTER_SHORTENER_LEN = 23  # twitter uses t.co
    limit -= PADDING

    log.info(f"{limit=}")
    message_room = limit - len_twitter(tags)
    log.info(f"message_room - len(tags) = {message_room}")

    log.info(f"{len_twitter(url)=}")
    if service == "twitter" and len_twitter(url) > TWITTER_SHORTENER_LEN:
        message_room = message_room - TWITTER_SHORTENER_LEN
        log.info(f"  shortened to {TWITTER_SHORTENER_LEN}")
    else:
        message_room = message_room - len_twitter(url)
    log.info(f"message_room after url = {message_room}")

    log.info(f"{len_twitter(title)=}")
    if len_twitter(title) > message_room:
        log.info("title is too long")
        title = f"{title[:message_room - 1]}…"
        log.info(f"  truncated to {len_twitter(title)}")
    message_room = message_room - len_twitter(title)
    log.info(f"{message_room=} after title = ")

    log.info(f"{len_twitter(comment)=}")
    if len_twitter(comment) > message_room:
        log.info("comment is too long")
        if message_room > 5:
            log.info(" truncating")
            comment = f"{comment[:message_room - 1]}…"
            log.info(f"  truncated to {len_twitter(comment)}")
            log.info(f"{comment}")
        else:
            log.info(" skipping")
            comment = ""
    message_room = message_room - len_twitter(comment)
    log.info(f"message_room after comment = {message_room}")

    comment_delim = ": " if comment and title else ""
    title = f"“{title}”" if title else ""
    message = f"{comment}{comment_delim}{title} {url} {tags}".strip()
    log.info(f"{len_twitter(message)=}: {message=}")
    return message


def len_twitter(text: str) -> int:
    """Twitter counts code units not code points as part of its character limit.

    https://developer.twitter.com/en/docs/counting-characters

    """
    return len(text.encode("utf-16-le")) // 2


def escape_XML(s: str) -> str:  # http://wiki.python.org/moin/EscapingXml
    """Escape XML character entities including & < >."""
    extras = {"\t": "  "}
    return escape(s, extras)


CURLY_TABLE = str.maketrans({"“": '"', "”": '"', "‘": "'", "’": "'"})


def straighten_quotes(text: str) -> str:
    """Convert curly quotes to straight quotes.

    >>> straighten_quotes('Hello “world”')
    'Hello "world"'
    >>> straighten_quotes('“Curly” quotes')
    '"Curly" quotes'
    >>> straighten_quotes("It's a ‘quoted’ text")
    "It's a 'quoted' text"
    """
    return text.translate(CURLY_TABLE)


def unescape_entities(text: str) -> str:
    """Replace HTML or XML character references and entities with Unicode.

    http://effbot.org/zone/re-sub.htm#unescape-htmlentitydefs

    >>> unescape_entities("&lt;div&gt;foo&lt;/div&gt;")
    '<div>foo</div>'
    >>> unescape_entities("Copyright &copy; 2023 &#x263A;")
    'Copyright © 2023 ☺'
    >>> unescape_entities("Unknown &entity;")
    'Unknown &entity;'
    """

    def fixup_chars(match: re.Match) -> str:
        entity = match.group(1)
        if entity.startswith("#"):
            # Handle numeric character references
            try:
                if entity.startswith("#x"):
                    return chr(int(entity[2:], 16))
                else:
                    return chr(int(entity[1:]))
            except ValueError:
                return match.group(0)  # Return the original match if invalid
        else:
            # Handle named entities
            return html.entities.html5.get(entity, match.group(0))

    entity_RE = re.compile(r"&([#\w]+);")
    return entity_RE.sub(fixup_chars, text)


def canonicalize_url(url: str) -> str:
    """Canonicalize URL.

    >>> canonicalize_url("https://old.reddit.com/r/Python/")
    'https://www.reddit.com/r/Python/'
    >>> canonicalize_url("https://i.reddit.com/r/news/comments/123456.compact")
    'https://www.reddit.com/r/news/comments/123456'
    >>> canonicalize_url("https://example.com/page")
    'https://example.com/page'
    """
    if "reddit.com" in url:
        return re.sub(
            r"^https?://(?:old\.|i\.)?reddit\.com(/.*?)(?:\.compact)?$",
            r"https://www.reddit.com\1",
            url,
        )
    return url
