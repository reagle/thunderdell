#!/usr/bin/env python3
"""Change the case of some text, making use of varied word lists.

http://en.wikipedia.org/wiki/Sentence_case
https://www.zotero.org/trac/ticket/832
"""
from pathlib import Path

__author__ = "Joseph Reagle"
__copyright__ = "Copyright (C) 2009-2023 Joseph Reagle"
__license__ = "GLPv3"
__version__ = "1.0"

import argparse  # http://docs.python.org/dev/library/argparse.html
import logging
import re
import string
import sys
from pathlib import Path

# from thunderdell.config import PROJECT_ROOT
from thunderdell.config import PROPER_NOUNS_FN, WORD_LIST_FN

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
# Not used by map2bib.py because it doesn't require slow
# wordset processing below


def create_wordset(file_path: Path) -> set:
    """Return a wordset given a file."""
    wordset = set()
    if file_path.is_file():
        for line in file_path.read_text(encoding="utf-8").splitlines():
            if line.strip() != "":
                wordset.add(line.strip())
        return wordset
    else:
        raise Exception(f"Could not find wordset {file_path}")


# TODO find alternative to hardcoded path that also works with import
# WORD_LIST_FN = PROJECT_ROOT / "biblio" / "wordlist-american.txt"
wordset = create_wordset(WORD_LIST_FN)
wordset_lower = {word for word in wordset if word[0].islower()}
wordset_upper = {word for word in wordset if word[0].isupper()}
wordset_nocase = {word.lower() for word in wordset}  # used in is_proper_noun()

# PROPER_NOUNS_FN = PROJECT_ROOT / "biblio" / "wordlist-proper-nouns.txt"
custom_proper_nouns = create_wordset(PROPER_NOUNS_FN)
wordset_proper_nouns = {
    word for word in wordset_upper if word.lower() not in wordset_lower
}
# proper_nouns used in safe_lower() and is_proper_noun()
proper_nouns = custom_proper_nouns | wordset_proper_nouns


def sentence_case(text: str) -> str:
    """Convert text to sentence case for APA-like citations.

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


def change_case(text: str, case_direction: str="sentence") -> str:
    """Change to sentence or title case.

    >>> change_case('I Am A Sentence.', 'sentence')
    'I am a sentence.'
    """
    text = text.strip().replace("  ", " ")
    logging.debug(f"** sentence_case: {type(text)} text = '{text}'")

    # Determine if text is in title-case or all-caps
    # Create abbreviation sans BORING words for title case detection
    text_abbreviated = "".join(
        [word[0] for word in set(text.split()).difference(BORING_WORDS)]
    )
    text_is_titlecase = text_abbreviated.isupper()
    logging.debug(f"  '{text_abbreviated=}' ")
    logging.debug(f"  '{text_is_titlecase=}'")
    logging.debug(f"  '{text.isupper()=}'")

    text = f": {text}"
    PUNCTUATION = ":.?"  # characters that need capitalization afterwards
    PUNCTUATION_RE = r"(:|\.|\?) "  # use parens to keep matched punctuation in split
    phrases = [phrase.strip() for phrase in re.split(PUNCTUATION_RE, text)]
    logging.debug(f"  phrases = '{phrases}'")
    new_text = []
    for phrase in phrases:
        if phrase == "":
            continue
        if phrase in PUNCTUATION:
            new_text.append(phrase)
            continue

        words = phrase.split(" ")
        logging.debug(f"words = '{words}'")
        is_first = True
        for word in words:
            logging.debug("----------------")
            logging.debug(f"word = '{word}'")

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
        logging.debug("  word is_proper_noun, not changing")
        new_word = word
    elif is_proper_noun(word_capitalized):
        logging.debug("  word_capitalized is_proper_noun")
        new_word = word_capitalized
    else:
        logging.debug(f"  changing case of '{word}'")
        if case_direction == "sentence":
            new_word = word.lower()
            logging.debug(f"  ... to '{new_word}'")
        elif case_direction == "title":
            if word.isupper():
                logging.debug("   lowering word because word.isupper()")
                word = safe_lower(word)
            logging.debug(f"  adding '{word}' as is")
            new_word = safe_capwords(word)
        else:
            raise Exception(f"Unknown {case_direction=}")

        if word and is_first:  # capitalize first word in a phrase
            logging.debug("  capitalize it as first word in phrase")
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
    logging.debug(f"  safe_capwords: {type(text)} text = '{text}'")
    new_text = []
    words = text.split(" ")
    for word in words:
        logging.debug(f"word = '{word}'")
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
    logging.debug(f"  safe_lower: {type(text)} text = '{text}'")
    new_text = []
    words = text.split(" ")
    for word in words:
        logging.debug(f"  word = '{word}'")
        if word:  # this split will remove multiple white-spaces
            word_capitalized = word.capitalize()
            logging.debug(f"  word_capitalized = '{word_capitalized}'")
            if word in proper_nouns:
                new_text.append(word)
            elif word.isupper():
                logging.debug("    word.isupper(): True")
                if word_capitalized in proper_nouns:
                    new_text.append(word_capitalized)
                else:
                    new_text.append(word.lower())
            else:
                new_text.append(word.lower())
    logging.debug(f"  new_text = '{new_text}'")
    return " ".join(new_text)


def is_proper_noun(word: str) -> bool:
    """Check if proper noun.

    A word is a proper noun if it is in that set or doesn't
    appear in the wordset dictionary. Recurse on hyphenated words.

    >>> is_proper_noun('W3C')
    True
    >>> is_proper_noun('The')
    False
    >>> is_proper_noun('r/AmItheButtface')
    True

    """
    logging.debug(f"    word = '{word}'")
    parts = word.split("-")  # '([\W]+)'
    # debug("parts = '%s'" %parts)
    if len(parts) > 1:
        logging.debug("    recursing")
        return any(is_proper_noun(part) for part in parts)
    word = "".join(ch for ch in word if ch not in set(string.punctuation))
    if word in proper_nouns:  # in list of proper nouns?
        logging.debug("    word in proper_nouns: True")
        return True
    if word.lower() not in wordset_nocase:  # not known to me at all: proper
        logging.debug(f"    word.lower() = '{word.lower()}'")
        logging.debug("    word.lower() not in wordset_nocase: True")
        return True
    logging.debug(f"    '{word}' is_proper_noun: False")
    return False


def process_arguments(argv: list[str] | None = None) -> argparse.Namespace:
    """Process arguments."""
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
        "-o",
        "--out-filename",
        type=Path,
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
        help="increase verbosity from critical though error, warning, info, and debug",
    )
    arg_parser.add_argument(
        "--version",
        action="version",
        version=f"{__version__} using Python {sys.version}",
    )
    args = arg_parser.parse_args(sys.argv[1:])

    # args.text is a list; make it a string
    args.text = " ".join(args.text)

    return args


def main(args: argparse.Namespace | None = None):
    """Set up logging and execute."""
    if args is None:
        args = process_arguments(sys.argv[1:])

    log_level = (logging.CRITICAL) - (args.verbose * 10)
    LOG_FORMAT = "%(levelname).4s %(funcName).10s:%(lineno)-4d| %(message)s"
    if args.log_to_file:
        logging.debug("logging to file")
        logging.basicConfig(
            filename="change_case.log",
            filemode="w",
            level=log_level,
            format=LOG_FORMAT,
        )
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    case_type = "title" if args.title_case else "sentence"
    logging.debug(f"{args.text=}")
    logging.debug(f"case_type = {case_type}")
    print(change_case(args.text, case_type))


if __name__ == "__main__":
    main()
