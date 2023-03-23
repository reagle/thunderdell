#!/usr/bin/env python3
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2023 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
""" Change the case of some text, making use of varied word lists.
    See http://en.wikipedia.org/wiki/Sentence_case and
    https://www.zotero.org/trac/ticket/832 ."""

import argparse  # http://docs.python.org/dev/library/argparse.html
import codecs
import logging
import os.path
import re
import string
import sys

from config import BIN_DIR

critical = logging.critical
error = logging.error
warn = logging.warn
info = logging.info
debug = logging.debug
excpt = logging.exception


ARTICLES = {"a", "an", "the"}
CONJUNCTIONS = {"and", "but", "nor", "or"}
SHORT_PREPOSITIONS = {
    "among",
    "as",
    "at",
    "by",
    "for",
    "from",
    "in",
    "of",
    "on",
    "out",
    "per",
    "to",
    "upon",
    "with",
}
JUNK_WORDS = {
    "",
    "re",
}
BORING_WORDS = ARTICLES | CONJUNCTIONS | SHORT_PREPOSITIONS | JUNK_WORDS
# BORING_WORDS is used in safe_capwords() and change_case() below.
# Not used by thunderdell.py because it doesn't require slow
# wordset processing below


def create_wordset(file_name):
    """Returns a wordset given a file"""

    wordset = set()
    if os.path.isfile(file_name):
        for line in codecs.open(file_name, "r", "utf-8").readlines():
            if line.strip() != "":
                wordset.add(line.strip())
        return wordset
    else:
        raise Exception("Could not find wordset %s" % file_name)


# TODO find alternative to hardcoded path that also works with import
LIST_PATH = BIN_DIR + "/biblio/"
WORD_LIST_FN = LIST_PATH + "wordlist-american.txt"
wordset = create_wordset(WORD_LIST_FN)
wordset_lower = {word for word in wordset if word[0].islower()}
wordset_upper = {word for word in wordset if word[0].isupper()}
wordset_nocase = {word.lower() for word in wordset}  # used in is_proper_noun()

PROPER_NOUNS_FN = LIST_PATH + "wordlist-proper-nouns.txt"
custom_proper_nouns = create_wordset(PROPER_NOUNS_FN)
wordset_proper_nouns = {
    word for word in wordset_upper if word.lower() not in wordset_lower
}
# proper_nouns used in safe_lower() and is_proper_noun()
proper_nouns = custom_proper_nouns | wordset_proper_nouns


def sentence_case(text):
    """Convert text to sentence case for APA-like citations

    >>> sentence_case('My Defamation 2.0 Experience: a Story of Wikipedia')
    'My defamation 2.0 experience: A story of Wikipedia'
    """
    return change_case(text, case_direction="sentence")


def title_case(text):
    """Change to sentence or title case.

    >>> title_case('The best title ever')
    'The Best Title Ever'
    """
    return change_case(text, case_direction="title")


def change_case(text, case_direction="sentence"):
    """Change to sentence or title case.

    >>> change_case('I Am A Sentence.', 'sentence')
    'I am a sentence.'
    """
    text = text.strip().replace("  ", " ")
    debug(f"** sentence_case: {type(text)} text = '{text}'")

    # Determine if text is in title-case or all-caps
    # Create abbreviation sans BORING words for title case detection
    text_abbreviated = "".join(
        [word[0] for word in set(text.split()).difference(BORING_WORDS)]
    )
    text_is_titlecase = text_abbreviated.isupper()
    debug(f"  '{text_abbreviated=}' ")
    debug(f"  '{text_is_titlecase=}'")
    debug(f"  '{text.isupper()=}'")

    text = f": {text}"
    PUNCTUATION = ":.?"  # characters that need capitalization afterwards
    PUNCTUATION_RE = r"(:|\.|\?) "  # use parens to keep matched punctuation in split
    phrases = [phrase.strip() for phrase in re.split(PUNCTUATION_RE, text)]
    debug(f"  phrases = '{phrases}'")
    new_text = []
    for phrase in phrases:
        if phrase == "":
            continue
        if phrase in PUNCTUATION:
            new_text.append(phrase)
            continue

        words = phrase.split(" ")
        debug(f"words = '{words}'")
        is_first = True
        for word in words:
            debug("----------------")
            debug(f"word = '{word}'")

            new_word = change_case_word(word, is_first, case_direction)
            new_text.append(new_word)
            is_first = False  # next word will not be is_first

    return (  # readjust spacing around punctuation that split then joined
        " ".join(new_text[1:])
        .replace(" : ", ": ")
        .replace(" . ", ". ")
        .replace(" ? ", "? ")
    )


def change_case_word(word: str, is_first: bool, case_direction: str) -> str:
    """Change the case of a lone word."""
    word_capitalized = word.capitalize()
    if is_proper_noun(word):
        debug("  word is_proper_noun, not changing")
        new_word = word
    elif is_proper_noun(word_capitalized):
        debug("  word_capitalized is_proper_noun")
        new_word = word_capitalized
    else:
        debug(f"  changing case of '{word}'")
        if case_direction == "sentence":
            new_word = word.lower()
            debug(f"  ... to '{new_word}'")
        elif case_direction == "title":
            if word.isupper():
                debug("   lowering word because word.isupper()")
                word = safe_lower(word)
            debug(f"  adding '{word}' as is")
            new_word = safe_capwords(word)
        else:
            raise Exception(f"Unknown {case_direction=}")

        if word and is_first:  # capitalize first word in a phrase
            debug("  capitalize it as first word in phrase")
            new_word = new_word[0].capitalize() + new_word[1:]

    return new_word


def safe_capwords(text):
    """string.capwords() but don't capitalize() BORING or lower() acronyms.

    >>> safe_capwords('W3C')
    'W3C'
    >>> safe_capwords('neat')
    'Neat'
    >>> safe_capwords('the')
    'the'

    """

    debug(f"  safe_capwords: {type(text)} text = '{text}'")
    new_text = []
    words = text.split(" ")
    for word in words:
        debug("word = '%s'" % word)
        if word:  # this split will remove multiple white-spaces
            if word.lower() in BORING_WORDS:
                new_text.append(word.lower())
            else:
                new_text.append(word[0].capitalize() + word[1:])
    return " ".join(new_text)


def safe_lower(text):
    """Lowercases a word except for proper nouns and acronyms.

    >>> safe_lower('IBM')
    'IBM'
    >>> safe_lower('Neat')
    'neat'
    >>> safe_lower('THE')
    'the'
    >>> safe_lower('AMERICA')
    'America'

    """

    debug(f"  safe_lower: {type(text)} text = '{text}'")
    new_text = []
    words = text.split(" ")
    for word in words:
        debug("  word = '%s'" % word)
        if word:  # this split will remove multiple white-spaces
            word_capitalized = word.capitalize()
            debug("  word_capitalized = '%s'" % word_capitalized)
            if word in proper_nouns:
                new_text.append(word)
            elif word.isupper():
                debug("    word.isupper(): True")
                if word_capitalized in proper_nouns:
                    new_text.append(word_capitalized)
                else:
                    new_text.append(word.lower())
            else:
                new_text.append(word.lower())
    debug("  new_text = '%s'" % new_text)
    return " ".join(new_text)


def is_proper_noun(word):
    """A word is a proper noun if it is in that set or doesn't
    appear in the wordset dictionary. Recurse on hyphenated words.

    >>> is_proper_noun('W3C')
    True
    >>> is_proper_noun('The')
    False
    >>> is_proper_noun('r/AmItheButtface')
    True

    """
    debug("    word = '%s'" % word)
    parts = word.split("-")  # '([\W]+)'
    # debug("parts = '%s'" %parts)
    if len(parts) > 1:
        debug("    recursing")
        return any(is_proper_noun(part) for part in parts)
    word = "".join(ch for ch in word if ch not in set(string.punctuation))
    if word in proper_nouns:  # in list of proper nouns?
        debug("    word in proper_nouns: True")
        return True
    if word.lower() not in wordset_nocase:  # not known to me at all: proper
        debug("    word.lower() = '%s'" % word.lower())
        debug("    word.lower() not in wordset_nocase: True")
        return True
    debug("    '%s' is_proper_noun: False" % word)
    return False


def parse_args() -> argparse.Namespace:
    """Process arguments"""
    # https://docs.python.org/3/library/argparse.html

    arg_parser = argparse.ArgumentParser(
        description="Change the case of some text, defaulting to sentence case."
    )
    # positional arguments
    arg_parser.add_argument("text", nargs="*", metavar="TEXT")
    # optional arguments
    arg_parser.add_argument(
        "-s",
        "--sentence-case",
        action="store_true",
        default=False,
        help="Even if it appears to be sentence case, force it to be so",
    )
    arg_parser.add_argument(
        "-t",
        "--title-case",
        action="store_true",
        default=False,
        help="Capitalize safely, e.g., preserve abbreviations",
    )
    arg_parser.add_argument(
        "-T", "--test", action="store_true", default=False, help="Test"
    )
    arg_parser.add_argument(
        "-o",
        "--out-filename",
        help="output results to filename",
        metavar="FILE",
    )
    arg_parser.add_argument(
        "-L",
        "--log-to-file",
        action="store_true",
        default=False,
        help="log to file %(prog)s.log",
    )
    arg_parser.add_argument(
        "-V",
        "--verbose",
        action="count",
        default=0,
        help="Increase verbosity (specify multiple times for more)",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"1.0 using Python {sys.version}",
    )
    args = arg_parser.parse_args()

    # args.text is a list; make it a string
    args.text = " ".join(args.text)

    log_level = 100  # default
    if args.verbose == 1:
        log_level = logging.CRITICAL  # 50
    elif args.verbose == 2:
        log_level = logging.INFO  # 20
    elif args.verbose >= 3:
        log_level = logging.DEBUG  # 10
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        debug("logging to file")
        logging.basicConfig(
            filename="change_case.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)
    return args


def main(argv):
    """Process arguments and execute."""

    if args.test:
        import doctest

        import pytest

        from tests import test_change_case

        print("Running tests")
        doctest.testmod()
        pytest.main(["-v", "-k", "change_case"])

        test_change_case.test_change_case()
        sys.exit()

    case_type = "title" if args.title_case else "sentence"
    debug(f"{args.text=}")
    debug("case_type = %s" % case_type)
    print(change_case(args.text, case_type))


if "__main__" == __name__:
    args = parse_args()
    main(args)
