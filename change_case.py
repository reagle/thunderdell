#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2012 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#
''' Change the case of some text, making use of varied word lists. 
    See http://en.wikipedia.org/wiki/Sentence_case and
    https://www.zotero.org/trac/ticket/832 .'''

import codecs
import locale
import logging
from os import chdir, environ, mkdir, rename
from os.path import abspath, exists, isfile, splitext
import re
import sys

HOME = environ['HOME']

log_level = 100 # default
critical = logging.critical
info = logging.info
dbg = logging.debug
warn = logging.warn
error = logging.error
excpt = logging.exception

BORING_WORDS = set(['a', 'an', 'and', 'at', 'by', 'for', 'if', 'in', 
    'of', 'or', 'the', 'to'])
PROPER_NOUNS_FN = 'reagle-proper-nouns.txt' # nltk.pos_tag(nltk.word_tokenize(content))
WORD_LIST_FN = '/usr/share/dict/american-english'

def create_wordset(file_name):
    '''Add words to set'''
    wordset = set()
    if isfile(file_name):
        for line in codecs.open(file_name, 'r', 'utf-8').readlines():
            if line.strip() != '':
                wordset.add(line.strip())
        return wordset
    else:
        return set()

custom_proper_nouns = create_wordset(PROPER_NOUNS_FN)
wordset = create_wordset(WORD_LIST_FN)
wordset_nocase = set([word.lower() for word in wordset])
wordset_lower = set([word for word in wordset if word[0].islower()])
wordset_upper = set([word for word in wordset if word[0].isupper()])
wordset_proper_nouns = set([word for word in wordset_upper if 
                        word.lower() not in wordset_lower]) # remove if in both
proper_nouns = custom_proper_nouns | wordset_proper_nouns


def is_proper_noun(word):
    ''' A word is a proper if it has a period or capital letter within, or
    appears in the proper_nouns set. Recurses on hypenated words.
    >>> is_proper_noun('W3C')
    True
    >>> is_proper_noun('The')
    False
    
    '''
    if '-' in word: # hyphenated
        parts = word.split('-')
        return any(is_proper_noun(part) for part in parts)
    if (re.search('\.|[A-Z]', word[1:]) or     # capital or period within
            word in proper_nouns or         
            word.lower() not in wordset_nocase):
        return True
    return False

    
def sentence_case(text, force_lower=False):
    ''' Convert title to sentence case for APA like citations
    >>> sentence_case('My Defamation 2.0 Experience: a Story of Wikipedia and a Boy')
    'My defamation 2.0 experience: A story of Wikipedia and a boy'
    
    '''
    text = text.strip().replace('  ', ' ')
    text_abbreviation = ''.join([word[0] for word in # sentence abbreviated sans BORING
        set(text.split()).difference(BORING_WORDS)]) 
    text_is_titlecase = text_abbreviation.isupper()     # if all upper, in title case
    
    text = ': ' + text # make first phrase consistent for processing below
    PUNCTUATION = ":.?"
    PUNCTUATION_RE = r'(:|\.|\?) ' # use parens to keep them in the split
    phrases = [phrase.strip() for phrase in re.split(PUNCTUATION_RE, text)]
    new_text = []
    for phrase in phrases:
        if phrase == '':
            continue
        if phrase in PUNCTUATION:
            new_text.append(phrase)
            continue
        words = phrase.split(' ')
        if len(words) >= 3:
            first_word, rest_of_phrase = words[0], words[1:]
        elif len(words) == 2:
            first_word, rest_of_phrase = words[0], [words[1]]
        else:
            first_word, rest_of_phrase = words[0], []
        new_text.append(first_word[0].capitalize() + first_word[1:])
        if text_is_titlecase or force_lower:         # down convert rest of phrase
            for word in rest_of_phrase:
                if is_proper_noun(word): 
                    pass    
                else:        
                    word = word.lower()
                new_text.append(word)
        else:                        # sentence case, so add rest of phrase
            new_text.extend(rest_of_phrase)
    return ' '.join(new_text[1:]).replace(' : ', ': ') \
                .replace(' . ', '. ') \
                .replace(' ? ', '? ')

def test():
    TESTS = (
        'My Defamation 2.0 Experience: A Story of Wikipedia and a Boy',
        'My defamation 2.0 experience: a story of Wikipedia and a boy',
        'Broadband makes women and Aaron happy',
        'Broadband Makes Women and Aaron Happy',
        'Tax Example Explains the Value of Hosted Software to Business',
        'PS3 shipments pass 35 million units worldwide',
        u'New Theorem Proved by Poincaré',
        'Wikipedia goes 3D',
        'Wikipedia trumps Britannica',
        "Glycogen: A Trojan Horse for Neurons",
        "Characterization of the SKN7 Ortholog of Aspergillus Fumigatus",
        "Wikipedia:Attribution",
        "Why Do People Write for Wikipedia? Incentives to Contribute to Open-Content Publishing",
        '<span class="pplri7t-x-x-120">Wikipedia:WikiLove</span>',
        'The Altruism Question: Toward a Social-Psychological Answer',
        '  Human Services:  Cambridge War Memorial Recreation Center',
        'Career Advice:     Stop Admitting Ph.D. Students - Inside Higher Ed'
        )
            
    for test in TESTS:
        print(sentence_case(test))

if '__main__' == __name__:

    import argparse # http://docs.python.org/dev/library/argparse.html
    arg_parser = argparse.ArgumentParser(
        description='Convert gives text to sentence case.')
    
    # positional arguments
    arg_parser.add_argument('text', nargs='*', metavar='TEXT')
    # optional arguments
    arg_parser.add_argument("-t", "--test",
                    action="store_true", default=False,
                    help="boolean value")
    arg_parser.add_argument("-o", "--out-filename",
                    help="output results to filename", metavar="FILE")
    arg_parser.add_argument('-l', '--log-to-file',
                    action="store_true", default=False,
                    help="log to file %(prog)s.log")
    arg_parser.add_argument('-v', '--verbose', action='count', default=0,
                    help="Increase verbosity (specify multiple times for more)")
    arg_parser.add_argument('--version', action='version', version='TBD')
    args = arg_parser.parse_args()

    if args.verbose == 1: log_level = logging.CRITICAL
    elif args.verbose == 2: log_level = logging.INFO
    elif args.verbose >= 3: log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(filename='change_case.log', filemode='w',
            level=log_level, format = LOG_FORMAT)
    else:
        logging.basicConfig(level=log_level, format = LOG_FORMAT)

    if args.test:
        test()
        sys.exit()
    if args.text:
        text = ' '.join(args.text)
        print(sentence_case(text))