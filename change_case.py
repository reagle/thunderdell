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
from fe import BORING_WORDS
import logging
from os.path import isfile
import re
import string
import sys

critical = logging.critical
info = logging.info        
dbg = logging.debug        

def create_wordset(file_name): # info() will invoke other logging params
    '''Returns a wordset given a file'''
    wordset = set()
    if isfile(file_name):
        for line in codecs.open(file_name, 'r', 'utf-8').readlines():
            if line.strip() != '':
                wordset.add(line.strip())
        return wordset
    else:
        return set()

PROPER_NOUNS_FN = 'wordlist-proper-nouns.txt'
WORD_LIST_FN = 'wordlist-american.txt'
custom_proper_nouns = create_wordset(PROPER_NOUNS_FN)
wordset = create_wordset(WORD_LIST_FN)
wordset_nocase = set([word.lower() for word in wordset])
wordset_lower = set([word for word in wordset if word[0].islower()])
wordset_upper = set([word for word in wordset if word[0].isupper()])
wordset_proper_nouns = set([word for word in wordset_upper if
    word.lower() not in wordset_lower])  # remove if in both
proper_nouns = custom_proper_nouns | wordset_proper_nouns

def safe_capwords(text):
    '''Like string.capwords() but won't lowercase rest of an acronym.

    >>> safe_capwords('W3C')
    'W3C'
    >>> safe_capwords('the')
    'The'

    '''

    return text[0].capitalize() + text[1:]


def is_proper_noun(word, text_is_ALLCAPS=False):
    ''' A word is a proper noun if it is in that set or doesn't 
    appear in the wordset dictionary. Recurse on hyphenated words.

    >>> is_proper_noun('W3C')
    True
    >>> is_proper_noun('The')
    False
    
    '''
    info("word = '%s'" %word)
    parts = word.split('-') # '([\W]+)'
    if len(parts) > 1:
        info("recursing")
        return any(is_proper_noun(part) for part in parts)
    word = word.translate(string.maketrans("",""), string.punctuation)
    if word in proper_nouns:
        info('word in proper_nouns: True')
        return True
    if word.lower() not in wordset_lower:
        info('word.lower() not in wordset_nocase: True')
        return True
    info(word + ": False")   
    return False
    
def sentence_case(text, lower=False):
    ''' Convert title to sentence case for APA like citations
    
    >>> sentence_case('My Defamation 2.0 Experience: a Story of Wikipedia')
    'My defamation 2.0 experience: A story of Wikipedia'
    
    '''
    text = text.strip().replace('  ', ' ')
    info("** %s text = '%s'" %(type(text), text))

    # create abbreviation sans BORING words
    info(set(text.split()).difference(BORING_WORDS))
    text_abbreviation = ''.join([word[0] for word in 
        set(text.split()).difference(BORING_WORDS)]) 
    info("text_abbreviation = %s " % text_abbreviation)
    text_is_titlecase = text_abbreviation.isupper()
    info("text_is_titlecase = '%s'" % text_is_titlecase)
    text_is_ALLCAPS = text.isupper()
    info("text_is_ALLCAPS = '%s'" % text_is_ALLCAPS)
    
    text = ': ' + text  # make first phrase consistent for processing below
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
            
        if is_proper_noun(first_word, text_is_ALLCAPS):
            first_word = first_word
        else:
            first_word = first_word.lower()
            
        new_text.append(safe_capwords(first_word))

        if text_is_titlecase or lower:    # down convert rest of phrase
            for word in rest_of_phrase:
                if is_proper_noun(word, text_is_ALLCAPS): 
                    pass    
                else:        
                    word = word.lower()
                new_text.append(word)
        else:                        # sentence case, so add rest of phrase
            new_text.extend(rest_of_phrase)
    return ' '.join(new_text[1:]).replace(' : ', ': ') \
                .replace(' . ', '. ') \
                .replace(' ? ', '? ')

def test(case_func, lower):
    '''Prints out sentence case for a number of test strings'''
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
        "Why Do People Write for Wikipedia? Incentives to Contribute",
        '<span class="pplri7t-x-x-120">Wikipedia:WikiLove</span>',
        'The Altruism Question: Toward a Social-Psychological Answer',
        '  Human Services:  Cambridge War Memorial Recreation Center',
        'Career Advice:     Stop Admitting Ph.D. Students - Inside Higher Ed',
        'THIS SENTENCE ABOUT AOL IS ALL CAPS',
        'Lessons I learned on the road as a Digital Nomad',
        )
            
    for test in TESTS:
        info("case_func = '%s'" %case_func)
        if case_func == sentence_case:
            print(case_func(test, lower))
        else:
            print(case_func(test))



if '__main__' == __name__:

    import argparse # http://docs.python.org/dev/library/argparse.html
    arg_parser = argparse.ArgumentParser(
        description='Change the case of some text, '
            ' defaulting to sentence case.')
    
    # positional arguments
    arg_parser.add_argument('text', nargs='*', metavar='TEXT')
    # optional arguments
    arg_parser.add_argument("-c", "--capwords",
                    action="store_true", default=False,
                    help="Capitalize via string.capwords()")
    arg_parser.add_argument("-s", "--safe",
                    action="store_true", default=False,
                    help="Capitalize safely, such as preserving abbreviations")
    arg_parser.add_argument("-l", "--lower",
                    action="store_true", default=False,
                    help="Even if it appears to be sentence case, "
                    "force it to be so")
    arg_parser.add_argument("-T", "--test",
                    action="store_true", default=False,
                    help="Test")
    arg_parser.add_argument("-o", "--out-filename",
                    help="output results to filename", metavar="FILE")
    arg_parser.add_argument('-L', '--log-to-file',
                    action="store_true", default=False,
                    help="log to file %(prog)s.log")
    arg_parser.add_argument('-V', '--verbose', action='count', default=0,
                    help="Increase verbosity (specify multiple times for more)")
    arg_parser.add_argument('--version', action='version', version='TBD')
    args = arg_parser.parse_args()



    log_level = 100  # default
    if args.verbose == 1: log_level = logging.CRITICAL
    elif args.verbose == 2: log_level = logging.INFO
    elif args.verbose >= 3: log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(filename='change_case.log', filemode='w',
            level=log_level, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=log_level, format = LOG_FORMAT)


    if args.capwords or args.safe:
        if args.safe:
            case_func = safe_capwords
        else:
            case_func = string.capwords
    else:
        case_func = sentence_case
    info("case_func = %s" %case_func)

    if args.test:
        test(case_func, args.lower)
    else:
        text = ' '.join(args.text)
        if case_func == sentence_case:
            print(case_func(text, args.lower))
        else:
            print(case_func(text))