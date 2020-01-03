#!/usr/bin/env python3
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
''' Change the case of some text, making use of varied word lists.
    See http://en.wikipedia.org/wiki/Sentence_case and
    https://www.zotero.org/trac/ticket/832 .'''

import argparse  # http://docs.python.org/dev/library/argparse.html
import codecs
import logging
import os.path
import re
import string
import sys

critical = logging.critical
error = logging.error
warn = logging.warn
info = logging.info
debug = logging.debug
excpt = logging.exception

HOME = os.path.expanduser('~')

ARTICLES = {'a', 'an', 'the'}
CONJUNCTIONS = {'and', 'but', 'nor', 'or'}
SHORT_PREPOSITIONS = {'among', 'as', 'at', 'by', 'for', 'from', 'in',
                      'of', 'on', 'out', 'per', 'to', 'upon', 'with', }
JUNK_WORDS = {'', 're', }
BORING_WORDS = ARTICLES | CONJUNCTIONS | SHORT_PREPOSITIONS | JUNK_WORDS
# BORING_WORDS used in safe_capwords() and change_case()
# not used by fe.py because it doesn't require slow wordset processing  below


def create_wordset(file_name):
    """Returns a wordset given a file"""
    # TODO: adding logging.info() in this function
    # disables all logging up to critical. Why?

    # info("file_name = '%s'" % (file_name))
    wordset = set()
    if os.path.isfile(file_name):
        for line in codecs.open(file_name, 'r', 'utf-8').readlines():
            if line.strip() != '':
                wordset.add(line.strip())
        return wordset
    else:
        raise Exception("Could not find wordset %s" % file_name)
    return set()


# TODO find alternative to hardcoded path that also works with import
LIST_PATH = HOME + "/bin/td/"
WORD_LIST_FN = LIST_PATH + "wordlist-american.txt"
wordset = create_wordset(WORD_LIST_FN)
wordset_lower = set([word for word in wordset if word[0].islower()])
wordset_upper = set([word for word in wordset if word[0].isupper()])
# wordset_nocase used in is_proper_noun()
wordset_nocase = set([word.lower() for word in wordset])

PROPER_NOUNS_FN = LIST_PATH + "wordlist-proper-nouns.txt"
custom_proper_nouns = create_wordset(PROPER_NOUNS_FN)
wordset_proper_nouns = set([word for word in wordset_upper if
                           word.lower() not in wordset_lower])
# proper_nouns used in safe_lower() and is_proper_noun()
proper_nouns = custom_proper_nouns | wordset_proper_nouns


def safe_capwords(text):
    '''string.capwords() but don't capitalize() BORING or lower() acronyms.

    >>> safe_capwords('W3C')
    'W3C'
    >>> safe_capwords('neat')
    'Neat'
    >>> safe_capwords('the')
    'the'

    '''

    info("  safe_capwords: %s text = '%s'" % (type(text), text))
    new_text = []
    words = text.split(' ')
    for word in words:
        info("word = '%s'" % word)
        if word:  # this split will remove multiple white-spaces
            if word.lower() in BORING_WORDS:
                new_text.append(word.lower())
            else:
                new_text.append(word[0].capitalize() + word[1:])
    return ' '.join(new_text)


def safe_lower(text):
    '''Lowercases a word except for proper nouns and acronyms.

    >>> safe_lower('IBM')
    'IBM'
    >>> safe_lower('Neat')
    'neat'
    >>> safe_lower('THE')
    'the'
    >>> safe_lower('AMERICA')
    'America'

    '''

    info("  safe_lower: %s text = '%s'" % (type(text), text))
    new_text = []
    words = text.split(' ')
    for word in words:
        info("  word = '%s'" % word)
        if word:  # this split will remove multiple white-spaces
            word_capitalized = word.capitalize()
            info("  word_capitalized = '%s'" % word_capitalized)
            if word in proper_nouns:
                new_text.append(word)
            elif word.isupper():
                info('    word.isupper(): True')
                if word_capitalized in proper_nouns:
                    new_text.append(word_capitalized)
                else:
                    new_text.append(word.lower())
            else:
                new_text.append(word.lower())
    info("  new_text = '%s'" % new_text)
    return ' '.join(new_text)


def is_proper_noun(word):
    ''' A word is a proper noun if it is in that set or doesn't
    appear in the wordset dictionary. Recurse on hyphenated words.

    >>> is_proper_noun('W3C')
    True
    >>> is_proper_noun('The')
    False

    '''
    info("    word = '%s'" % word)
    parts = word.split('-')  # '([\W]+)'
    # info("parts = '%s'" %parts)
    if len(parts) > 1:
        info("    recursing")
        return any(is_proper_noun(part) for part in parts)
    word = ''.join(ch for ch in word if ch not in set(string.punctuation))
    if word in proper_nouns:  # in list of proper nouns?
        info('    word in proper_nouns: True')
        return True
    if word.lower() not in wordset_nocase:  # not known to me at all: proper
        info("    word.lower() = '%s'" % word.lower())
        info('    word.lower() not in wordset_nocase: True')
        return True
    info("    '%s' is_proper_noun: False" % word)
    return False


def sentence_case(text):
    return change_case(text, case_direction='sentence')


def title_case(text):
    return change_case(text, case_direction='title')


def change_case(text, case_direction='sentence'):
    ''' Convert text to sentence case for APA like citations

    >>> sentence_case('My Defamation 2.0 Experience: a Story of Wikipedia')
    'My defamation 2.0 experience: A story of Wikipedia'

    '''
    text = text.strip().replace('  ', ' ')
    info("** sentence_case: %s text = '%s'" % (type(text), text))

    # create abbreviation sans BORING words
    info(set(text.split()).difference(BORING_WORDS))
    text_abbreviation = ''.join(
        [word[0] for word in set(text.split()).difference(BORING_WORDS)])
    info("  text_abbreviation = %s " % text_abbreviation)
    text_is_titlecase = text_abbreviation.isupper()
    info("  text_is_titlecase = '%s'" % text_is_titlecase)
    text_is_ALLCAPS = text.isupper()
    info("  text_is_ALLCAPS = '%s'" % text_is_ALLCAPS)

    text = ': ' + text  # make first phrase consistent for processing below
    PUNCTUATION = ":.?"
    PUNCTUATION_RE = r'(:|\.|\?) '  # use parens to keep them in the split
    phrases = [phrase.strip() for phrase in re.split(PUNCTUATION_RE, text)]
    info("  phrases = '%s'" % phrases)
    new_text = []
    for phrase in phrases:
        if phrase == '':
            continue
        if phrase in PUNCTUATION:
            new_text.append(phrase)
            continue

        words = phrase.split(' ')
        info("words = '%s'" % words)
        for index, word in enumerate(words):
            # [0].upper() + word[1:].lower()
            word_capitalized = word.capitalize()
            info("----------------")
            info("word = '%s'" % word)
            if is_proper_noun(word):
                # info("  word is_proper_noun")
                new_word = word
            elif is_proper_noun(word_capitalized):
                # info("  word_capitalized is_proper_noun")
                new_word = word_capitalized
            else:
                info("  changing case of '%s'" % word)
                if case_direction == 'sentence':
                    new_word = word.lower()
                elif case_direction == 'title':
                    info("  text_is_ALLCAPS = '%s'" % text_is_ALLCAPS)
                    if text_is_ALLCAPS:
                        info('   lowering word because text_is_ALLCAPS')
                        word = safe_lower(word)
                    info("  adding '%s' as is" % word)
                    new_word = safe_capwords(word)
                else:
                    raise Exception(
                        "Unknown case_direction = '%s'" % case_direction)
            if word and index == 0:  # capitalize first word in a phrase
                info("  capitalizing it as first word in phrase")
                new_word = new_word[0].capitalize() + new_word[1:]

            new_text.append(new_word)

    return ' '.join(new_text[1:]) \
        .replace(' : ', ': ') \
        .replace(' . ', '. ') \
        .replace(' ? ', '? ')


def test(change_case, case_direction):
    '''Prints out sentence case (default) for a number of test strings'''
    TESTS = (
        'My Defamation 2.0 Experience: A Story of Wikipedia and a Boy',
        'My defamation 2.0 experience: a story of Wikipedia and a boy',
        'Broadband makes women and Aaron happy',
        'Broadband Makes Women and Aaron Happy',
        'Tax Example Explains the Value of Hosted Software to Business',
        'PS3 shipments pass 35 million units worldwide',
        'New Theorem Proved by Poincaré',
        'Wikipedia goes 3D',
        'Wikipedia trumps Britannica',
        "Wikirage: What's hot now on Wikipedia",
        'Glycogen: A Trojan Horse for Neurons',
        'Characterization of the SKN7 Ortholog of Aspergillus Fumigatus',
        'Wikipedia:Attribution',
        'Why Do People Write for Wikipedia? Incentives to Contribute',
        '<span class="pplri7t-x-x-120">Wikipedia:WikiLove</span>',
        'The Altruism Question: Toward a Social-Psychological Answer',
        '  Human Services:  Cambridge War Memorial Recreation Center',
        'Career Advice:     Stop Admitting Ph.D. Students - Inside Higher Ed',
        'THIS SENTENCE ABOUT AOL IN AMERICA IS ALL CAPS',
        'Lessons I learned on the road as a Digital Nomad', )

    import doctest
    doctest.testmod()

    for test in TESTS:
        info("case_direction = '%s'" % case_direction)
        print((change_case(test, case_direction)))


def main(argv):
    """Process arguments and execute."""

    arg_parser = argparse.ArgumentParser(
        description='Change the case of some text, '
        'defaulting to sentence case.')
    # positional arguments
    arg_parser.add_argument('text', nargs='*', metavar='TEXT')
    # optional arguments
    arg_parser.add_argument(
        "-s", "--sentence-case",
        action="store_true", default=False,
        help="Even if it appears to be sentence case, force it to be so")
    arg_parser.add_argument(
        "-t", "--title-case",
        action="store_true", default=False,
        help="Capitalize safely, e.g., preserve abbreviations")
    arg_parser.add_argument(
        "-T", "--test",
        action="store_true", default=False,
        help="Test")
    arg_parser.add_argument(
        "-o", "--out-filename",
        help="output results to filename", metavar="FILE")
    arg_parser.add_argument(
        '-L', '--log-to-file',
        action="store_true", default=False,
        help="log to file %(prog)s.log")
    arg_parser.add_argument(
        '-V', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    arg_parser.add_argument('--version', action='version', version='TBD')
    args = arg_parser.parse_args()

    log_level = 100  # default
    if args.verbose == 1: log_level = logging.CRITICAL  # 50
    elif args.verbose == 2: log_level = logging.INFO    # 20
    elif args.verbose >= 3: log_level = logging.DEBUG   # 10
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        info("logging to file")
        logging.basicConfig(filename='change_case.log', filemode='w',
                            level=log_level, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    case_direction = 'sentence'
    if args.title_case:
            case_direction = 'title'
    info("case_direction = %s" % case_direction)

    if args.test:
        test(change_case, case_direction)
    else:
        text = ' '.join(args.text)
        result = change_case(text, case_direction)
        info(result)
        print(result)


if '__main__' == __name__:
    main(sys.argv[1:])
