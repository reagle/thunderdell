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
import os
import re
from pathlib import Path
from typing import Any
from xml.sax.saxutils import escape  # unescape

import dotenv
import requests  # http://docs.python-requests.org/en/latest/
from lxml import etree  # type: ignore

from thunderdell import config
from thunderdell.biblio.keywords import KEY_SHORTCUTS

log = logging.getLogger("utils_web")


def get_credential(key: str) -> str:
    """Retrieve credential from environ, file, or solicitation."""
    ENV_FN = Path.home() / ".config" / "api-info.env"
    # Make sure the file is not public for security's sake
    if ENV_FN.stat().st_mode & 0o777 != 0o600:
        print(f"WARNING: {ENV_FN} is not 0o600; fixing")
        ENV_FN.chmod(0o600)

    # Load from file; environment value wins unless `override=True`
    dotenv.load_dotenv(dotenv_path=ENV_FN)
    if (value := os.getenv(key)) is None:
        value = input(f"Enter value for {key}: ").strip()
        dotenv.set_key(ENV_FN, key, value)

    return value


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
    logging.info(f"'{comment=}', {title=}, {subtitle=}, {url=}, {tags=}")
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
    logging.info(
        f"""comment = {len(comment)}: {comment}
         title = {len(title)}: {title}
         url = {len(url)}: {url}
         tags = {len(tags)}: {tags}
         {total_len=}"""
    )

    twitter_update(comment, title, url, tags, photo_path)
    mastodon_update(comment, title, url, tags, photo_path)
    bluesky_update(comment, title, url, tags, photo_path)


def bluesky_update(
    comment: str, title: str, url: str, tags: str, photo_path: Path | None
) -> None:
    """Update the authenticated Bluesky account with a post and optional photo."""
    import atproto_core
    from atproto import Client, client_utils, models

    BLUESKY_APP_PASSWORD = get_credential("BLUESKY_APP_PASSWORD")
    BLUESKY_HANDLE = get_credential("BLUESKY_HANDLE")

    # Prepare the base text without tags
    skeet_text = (
        shrink_message("bluesky", comment, title, len(url), len(tags)).rstrip() + "\n"
    )

    try:
        client = Client()
        client.login(BLUESKY_HANDLE, BLUESKY_APP_PASSWORD)

        skeet_obj = client_utils.TextBuilder().text(skeet_text)

        if tags:
            for tag in tags.split():
                # Remove the # if present and add the tag properly
                tag_text = tag.lstrip("#")
                skeet_obj = skeet_obj.text(" ").tag(f"#{tag_text}", tag_text)

        # Add URL if provided
        if url.strip():
            skeet_obj = skeet_obj.text(" ").link(url, url)
        if photo_path and photo_path.is_file():
            photo_desc = get_photo_desc(photo_path)
            img_data = photo_path.read_bytes()
            upload = client.upload_blob(img_data)
            images = [
                models.AppBskyEmbedImages.Image(alt=photo_desc, image=upload.blob)
            ]
            embed = models.AppBskyEmbedImages.Main(images=images)
            response = client.send_post(
                text=skeet_obj.build_text(),
                facets=skeet_obj.build_facets(),
                embed=embed,
                langs=["en-US"],
            )
        else:
            response = client.send_post(
                text=skeet_obj.build_text(),
                facets=skeet_obj.build_facets(),
                langs=["en-US"],
            )

        logging.debug(f"{response=}")
    except atproto_core.exceptions.AtProtocolError as err:  # type: ignore
        print(err)
        print(f"skeet failed {len(skeet_text + url)}: {skeet_text + url}")
    else:
        print(f"skeet worked {len(skeet_obj.build_text())}: {skeet_obj.build_text()}")


def mastodon_update(
    comment: str, title: str, url: str, tags: str, photo_path: Path | None
) -> None:
    """Update the authenticated Mastodon account with a tweet and optional photo."""
    import mastodon  # https://mastodonpy.readthedocs.io/en/stable/

    MASTODON_APP_BASE = get_credential("MASTODON_APP_BASE")
    OHAI_ACCESS_TOKEN = get_credential("OHAI_ACCESS_TOKEN")

    ohai = mastodon.Mastodon(
        access_token=OHAI_ACCESS_TOKEN, api_base_url=MASTODON_APP_BASE
    )
    toot = shrink_message("ohai", comment, title, url, tags)
    try:
        if photo_path and photo_path.is_file():
            photo_desc = get_photo_desc(photo_path)
            media = ohai.media_post(media_file=str(photo_path), description=photo_desc)
            ohai.status_post(status=toot, media_ids=media)
        else:
            ohai.status_post(status=toot)
    except mastodon.MastodonError as err:
        print(err)
        print(f"toot failed {len(toot)}: {toot}")
    else:
        print(f"toot worked {len(toot)}: {toot}")


def twitter_update(
    comment: str, title: str, url: str, tags: str, photo_path: Path | None
) -> None:
    """Update the authenticated Twitter account with a tweet and optional photo.

    Twitter often won't post larger messages (even if within 280 chars) yet won't raise an exception.
    Twitter also only allows ~3 posts a day via twikit.
    """
    import asyncio

    from twikit import Client, errors

    async def _twitter_update_async():
        TW_EMAIL = get_credential("TW_EMAIL")
        TW_PASSWORD = get_credential("TW_PASSWORD")
        TW_USERNAME = get_credential("TW_USERNAME")

        client = Client(language="en-US")

        shrunk_msg = ""  # Initialize shrunk_msg
        try:
            await client.login(
                auth_info_1=TW_USERNAME,
                auth_info_2=TW_EMAIL,
                password=TW_PASSWORD,
                cookies_file=str(config.TMP_DIR / "twitter-cookies.json"),
            )

            if photo_path and photo_path.is_file():
                shrunk_msg = shrink_message("twitter", comment, title, "", tags)
                media_id = await client.upload_media(
                    source=str(photo_path), wait_for_completion=True
                )
                alt_text = get_photo_desc(photo_path) or title or "Image"

                await client.create_media_metadata(media_id, alt_text=alt_text)
                tweet_response = await client.create_tweet(
                    text=shrunk_msg, media_ids=[media_id]
                )
            else:
                shrunk_msg = shrink_message("twitter", comment, title, url, tags)
                tweet_response = await client.create_tweet(text=shrunk_msg)

            logging.debug(
                f"Tweet response: {tweet_response.id if tweet_response else 'No response'}"
            )
            print(f"tweet worked {len(shrunk_msg)}: {shrunk_msg}")

        except errors.TwitterException as e:
            print(f"Tweet failed: {e}")
            logging.error(f"Tweet failed for message '{shrunk_msg}': {e}")
        except Exception as e:  # noqa: BLE001
            print(f"Tweet failed: {e}")
            logging.error(
                f"An unexpected error occurred during Twitter update for '{shrunk_msg}': {e}"
            )

    asyncio.run(_twitter_update_async())


def get_photo_desc(photo_path: Path) -> str:
    """Extract photo description from filename."""
    photo_fn = photo_path.stem
    return " ".join(chunk for chunk in photo_fn.split("-") if not chunk.isdigit())


def generate_countable_string(length: int) -> str:
    """Generate a string of specified length with a visual counting system.

    >>> len(generate_countable_string(8))
    8
    >>> generate_countable_string(8)
    '¹²³⁴⁵⁶⁷⁸'
    >>> len(generate_countable_string(117))
    117
    >>> len('¹²³⁴⁵⁶⁷⁸⁹1¹²³⁴⁵⁶⁷⁸⁹2¹²³⁴⁵⁶⁷⁸⁹3¹²³⁴⁵⁶⁷⁸⁹4¹²³⁴⁵⁶⁷⁸⁹5¹²³⁴⁵⁶⁷⁸⁹6¹²³⁴⁵⁶⁷⁸⁹7¹²³⁴⁵⁶⁷⁸⁹8¹²³⁴⁵⁶⁷⁸⁹9¹²³⁴⁵⁶⁷⁸⁹10²³⁴⁵⁶⁷⁸⁹11²³⁴⁵⁶⁷⁸⁹12²³⁴⁵⁶⁷⁸⁹13²³⁴⁵⁶⁷⁸⁹14²³⁴⁵⁶⁷⁸⁹15²³⁴⁵⁶⁷⁸⁹16²³⁴⁵⁶⁷⁸⁹17²³⁴⁵⁶⁷⁸⁹18²³⁴⁵⁶⁷⁸⁹19²³⁴⁵⁶⁷⁸⁹20²³⁴⁵⁶⁷⁸⁹21²³⁴⁵⁶⁷⁸⁹22²³⁴⁵')
    225
    """
    superscripts = "¹²³⁴⁵⁶⁷⁸⁹"
    result = ""
    tens = 0

    while len(result) < length:
        if tens == 0:
            result += superscripts[: min(9, length)]
        else:
            tens_str = str(tens)
            if len(result) + len(tens_str) > length:
                break
            result += tens_str

            skip = len(tens_str) - 1
            remaining = length - len(result)
            result += superscripts[skip : skip + min(9 - skip, remaining)]

        tens += 1

    return result


def shrink_message(
    service: str, comment: str, title: str, url: str | int, tags: str | int
) -> str:
    """Shrink message to fit into service specific character limit.

    Use URL shortening rules and codepoint counts.
    Parameters {url, tags} can be strings or their length.

    >>> long_comment = long_title = generate_countable_string(501)
    >>> shrink_message("twitter", "Comment", long_title, "http://url.com", "#tag")
    '“¹²³⁴⁵⁶⁷⁸⁹1¹²³⁴⁵⁶⁷⁸⁹2¹²³⁴⁵⁶⁷⁸⁹3¹²³⁴⁵⁶⁷⁸⁹4¹²³⁴⁵⁶⁷⁸⁹5¹²³⁴⁵⁶⁷⁸⁹6¹²³⁴⁵⁶⁷⁸⁹7¹²³⁴⁵⁶⁷⁸⁹8¹²³⁴⁵⁶⁷⁸⁹9¹²³⁴⁵⁶⁷⁸⁹10²³⁴⁵⁶⁷⁸⁹11²³⁴⁵⁶⁷⁸⁹12²³⁴⁵⁶⁷⁸⁹13²³⁴⁵⁶⁷⁸⁹14²³⁴⁵⁶⁷⁸⁹15²³⁴⁵⁶⁷⁸⁹16²³⁴⁵⁶⁷⁸⁹17²³⁴⁵⁶⁷⁸⁹18²³⁴⁵⁶⁷⁸⁹19²³⁴⁵⁶⁷⁸⁹20²³⁴⁵⁶⁷⁸⁹21²³⁴⁵⁶⁷⁸⁹22²³⁴⁵⁶⁷⁸⁹23²³⁴⁵⁶⁷⁸⁹24²³⁴⁵⁶⁷⁸⁹25²³⁴…” http://url.com #tag'

    >>> result = shrink_message("twitter", "Comment", long_title, "http://url.com", "#tag")
    >>> len(result) <= 280 and '…' in result
    True

    >>> msg = shrink_message("bluesky", long_comment, long_title, 14, "#tag")
    >>> len(msg) <= 300
    True

    >>> msg = shrink_message("ohai", "comment", long_title, "http://url.com", "#tag")
    >>> len(msg) <= 500
    True

    >>> emoji = "👩‍👩‍👧‍👦" * 280  # family emoji with multiple codepoints
    >>> msg = shrink_message("twitter", emoji, "Title", "http://url.com", "#tag")
    >>> len(msg) <= 280
    True
    """
    LIMITS = {
        "twitter": 280,
        "bluesky": 300,
        "ohai": 500,  # Mastodon instance
    }
    PADDING = 7  # for comment delimiter, title quotes, and spaces
    MININUM_ROOM = 10

    limit = LIMITS[service]
    logging.info(f"Service: {service}, limit: {limit}")

    limit -= PADDING
    logging.debug(f"Adjusted limit after removing padding: {limit}")

    if isinstance(tags, str):
        tag_len = len_cp(tags)
    elif isinstance(tags, int):
        tag_len = tags
        tags = ""
    logging.debug(f"tag length in codepoints: {tag_len}")
    message_room = limit - tag_len
    logging.debug(
        f"Message room after subtracting tags length ({tag_len}): {message_room}"
    )

    if isinstance(url, str):
        url_len = len_cp(url)
    elif isinstance(url, int):
        url_len = url
        url = ""
    logging.debug(f"URL length in codepoints: {url_len}")
    message_room -= url_len
    logging.debug(f"Message room after subtracting URL: {message_room}")

    title_len = len_cp(title)
    if title_len > message_room:
        logging.debug(f"Title too long ({title_len}), truncating to {message_room - 1}")
        title = f"{title[: message_room - 1]}…"
        logging.debug(f"Truncated title length: {len_cp(title)}")
    message_room -= len_cp(title)
    logging.debug(f"Message room after subtracting title: {message_room}")

    # What does the code chunk below do, why message_room >5?
    comment_len = len_cp(comment)
    if comment_len > message_room:
        logging.info(
            f"Comment too long ({comment_len}), truncating or skipping to fit in {message_room}"
        )
        if message_room > MININUM_ROOM:
            comment = f"{comment[: message_room - 1]}…"
            logging.info(f"Truncated comment length: {len_cp(comment)}")
        else:
            comment = ""
            logging.info("Comment skipped due to insufficient room")
    message_room -= len_cp(comment)
    logging.info(f"Message room after subtracting comment: {message_room}")
    title = f"“{title}”" if title else ""

    message_parts = [part for part in [comment, title, url, tags] if part]
    message = " ".join(message_parts)
    return message


def len_cp(text: str) -> int:
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
