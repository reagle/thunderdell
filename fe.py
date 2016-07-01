#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2015 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Extract a bibliography from a Freemind mindmap"""

# TODO
# *  use argparse; 

#20090519: bibformat_title and pull_citation each use about ~7%
#20120514: biblatex/biber doesn't accept BCE/negative, can use year

from cgi import escape, parse_qs
import codecs
from collections import OrderedDict
import datetime
import dateutil.parser    # http://labix.org/python-dateutil
import logging
from optparse import OptionParser
import os
import re
import string
from subprocess import call, Popen, STDOUT
import sys
import time
from urllib import quote, unquote
import unicodedata
import webbrowser

log_level = 100 # default
critical = logging.critical
info = logging.info
dbg = logging.debug

HOME = os.path.expanduser('~')
DEFAULT_MAPS = (HOME+'/joseph/readings.mm',)

TMP_DIR = HOME + '/tmp/.fe/'
if not os.path.isdir(TMP_DIR):
    os.makedirs(TMP_DIR)

from lxml.etree import parse, Element, SubElement, ElementTree
useLXML = True

#################################################################
# Constants and mappings
#################################################################

MONTH2DIGIT = {'jan' : '1', 'feb' : '2', 'mar' : '3',
        'apr' : '4', 'may' : '5', 'jun' : '6',
        'jul' : '7', 'aug' : '8', 'sep' : '9',
        'oct' : '10', 'nov' : '11', 'dec' : '12'}
DIGIT2MONTH = dict((v,k) for k, v in MONTH2DIGIT.iteritems())


# happy to keep using bibtex:address alias of bibtex:location
# keep t, ot, and et straight
BIBLATEX_SHORTCUTS = OrderedDict([
        ('id','identifier'), 
        ('a','address'),
        ('ad','addendum'),
        ('an','annotation'),
        ('au','author'),
        ('bt','booktitle'),
        ('ch','chapter'),
        ('doi','doi'),
        ('e','editor'),
        ('ed','edition'),
        ('et','eventtitle'),
        ('hp','howpublished'),
        ('in','institution'),
        ('i','isbn'),
        ('j','journal'),
        ('kw','keyword'),
        ('mm','custom2'),     # mindmap file name
        ('nt','note'),
        ('or','organization'), 
        ('ol','origlanguage'), ('od','origdate'), ('op','origpublisher'),
        ('ot','type'),        # org's manual or report subtype, eg W3C REC
        ('ps','pubstate'),    # in press, submitted
        ('pp','pages'),
        ('pa','pagination'),
        ('p','publisher'),
        ('r','custom1'),      # read date
        ('sc','school'),
        ('se','series'),
        ('t','entry_type'),   # bibtex type
        ('tr','translator'),
        ('ti','title'), ('st','shorttitle'),
        ('rt','retype'),
        ('v','volume'), ('is','issue'), ('n','number'),
        ('d','date'), ('y','year'), ('m','month'), ('da', 'day'),
        ('url','url'),
        ('urld','urldate'),
        ('ve','venue'),
        ('c3','catalog'), ('c4','custom4'), ('c5','custom5'),
        ])

CSL_SHORTCUTS = OrderedDict([
        # title (csl:container) fields that also give type 
        # hints towards the richer csl:types
        ('cj','c_journal'), #containing_journal
        ('cm','c_magazine'),
        ('cn','c_newspaper'),
        ('cd','c_dictionary'),
        ('cy','c_encyclopedia'),
        ('cf','c_forum'), # for post
        ('cb','c_blog'),
        ('cw','c_web'),
        ])

BIB_SHORTCUTS = BIBLATEX_SHORTCUTS.copy()
BIB_SHORTCUTS.update(CSL_SHORTCUTS)

BIB_FIELDS = dict([(field, short) for short, field in 
                BIB_SHORTCUTS.iteritems()])

CSL_FIELDS = dict([(field, short) for short, field in 
                CSL_SHORTCUTS.iteritems()])

CONTAINERS = CSL_SHORTCUTS.values()
CONTAINERS.append('organization')

BIBLATEX_TYPES = (
        'article',
        'book',
        'booklet',
        'collection',   # the larger mutli-author book with editor
        'inbook',       # chapter in a book by a single author
        'incollection', # chapter in multi-authored book with editor
        'inproceedings',   
        'manual',
        'mastersthesis',
        'misc',
        'phdthesis',
        'report',
        'unpublished',
        'patent',
        'periodical',
        'proceedings',
        'online',
        )

CSL_TYPES =  (
        'article', 
        'article-magazine', 
        'article-newspaper', 
        'article-journal', 
        'bill', 
        'book', 
        'broadcast', 
        'chapter', 
        'dataset', 
        'entry', 
        'entry-dictionary', 
        'entry-encyclopedia', 
        'figure', 
        'graphic', 
        'interview', 
        'legislation', 
        'legal_case', 
        'manuscript', 
        'map', 
        'motion_picture', 
        'musical_score', 
        'pamphlet', 
        'paper-conference', 
        'patent', 
        'post', 
        'post-weblog', 
        'personal_communication', 
        'report', 
        'review', 
        'review-book', 
        'song', 
        'speech', 
        'thesis', 
        'treaty', 
        'webpage', 
        )

BIB_TYPES = BIBLATEX_TYPES + CSL_TYPES

# http://reagle.org/joseph/2013/08/bib-mapping.html
CSL_BIBLATEX_TYPE_MAP = OrderedDict([
        # ordering is important so in the reverse mapping online => webpage
        ('article-journal',         'article'),
        ('article-magazine',        'article'),
        ('article-newspaper',       'article'),
        ('chapter',                 'incollection'),
        ('entry',                   'incollection'),
        ('entry-dictionary',        'inreference'),
        ('entry-encyclopedia',      'inreference'),
        ('legal_case',              'misc'),
        ('manuscript',              'unpublished'),
        ('thesis',                  'phdthesis'), 
        ('thesis',                  'mastersthesis'), 
        ('pamphlet',                'booklet'),
        ('paper-conference',        'inproceedings'),
        ('personal_communication',  'letter'),
        ('post',                    'online'),
        ('post-weblog',             'online'),
        ('webpage',                 'online'),
        ])

BIBLATEX_CSL_TYPE_MAP = OrderedDict((v,k) for k, v in 
                                   CSL_BIBLATEX_TYPE_MAP.items())

BIBLATEX_CSL_FIELD_MAP = OrderedDict([
        ('address',        'publisher-place'),         
        ('annotation',     'abstract'),                
        ('booktitle',      'container-title'),         
        ('chapter',        'chapter-number'),          
        ('doi',            'DOI'),                     
        ('eventtitle',     'event'),                   
        ('institution',    'publisher'),               
        ('isbn',           'ISBN'),    
        ('journal',        'container-title'),         
        ('organization',   'publisher'),   
        ('number',         'issue'),
        ('type',           'genre'),                    
        ('pages',          'page'),                   
        ('pagination',     'locators'),                
        ('school',         'publisher'),               
        ('series',         'collection-title'),        
        ('shorttitle',     'title-short'),             
        ('url',            'URL'),                     
        ('urldate',        'accessed'),                
        ('venue',          'event-place'),             
        ('catalog',        'call-number'),             
        ])

CSL_BIBLATEX_FIELD_MAP = OrderedDict((v,k) for k, v in 
                                   BIBLATEX_CSL_FIELD_MAP.items())


# https://en.wikipedia.org/wiki/Template:Citation
BIBLATEX_WP_FIELD_MAP = OrderedDict([
        ('c_journal',       'journal'),  
        ('c_magazine',      'magazine'),         
        ('c_newspaper',     'newspaper'),                
        ('c_dictionary',    'work'),
        ('c_encyclopedia',  'work'),
        ('c_forum',         'work'), 
        ('c_blog',          'work'),
        ('c_web',           'work'),
        ('urldate',         'accessdate'),
        ('address',         'publication-place'), 
        ('booktitle',       'title'), 
        ('origdate',        'orig-year'),
        ])

WP_BIBLATEX_FIELD_MAP = OrderedDict((v,k) for k, v in 
                                   BIBLATEX_WP_FIELD_MAP.items())


BIBTEX_FIELDS = ['address', 'annote', 'author', 'booktitle', 'chapter', 
    'crossref', 'edition', 'editor', 'howpublished', 'institution', 'journal', 
    'key', 'month', 'note', 'number', 'organization', 'pages', 'publisher', 
    'school', 'series', 'title', 'type', 'volume', 'year']

BIBLATEX_FIELDS = BIBTEX_FIELDS + [
    'addendum', 'annotation', 
    'catalog', 'custom1', 'custom2', 'custom4', 'custom5', 
    'date', 'day', 'doi', 'entry_type', 'eventtitle', 
    'identifier', 'isbn', 'issue', 'keyword', 
    'origdate', 'origlanguage', 'origpublisher''origyear', 
    'pagination', 'pubstate', 'retype', 'shorttitle', 
    'translator', 'url', 'urldate', 'venue']


## url not original bibtex standard, but is common, 
## so I include it here and also include it in the note in emit_biblatex.
#BIBTEX_FIELDS.append('url')

#HTML class corresponding to Freemind color
CL_CO = {'annotation': '#999999', 'author': '#338800', 'title': '#090f6b',
    'cite': '#ff33b8', 'author': '#338800',
    'quote': '#166799', 'paraphrase': '#8b12d6',
    'default': '#000000', None: None}
CO_CL = dict([(label, color) for color, label in list(CL_CO.items())])

#################################################################
# Utility functions
#################################################################

def pretty_tabulate_list(mylist, cols=3):
    pairs = ["\t".join(
        ['%20s' %j for j in mylist[i:i+cols]]
            ) for i in range(0,len(mylist),cols)]
    print("\n".join(pairs))
    print("\n")

def pretty_tabulate_dict(mydict, cols=3):
    pretty_tabulate_list(sorted(['%s:%s' %(key, value) 
        for key, value in mydict.items()]), cols)
     
from xml.sax.saxutils import escape, unescape
def unescape_XML(o):
    '''Unescape XML character entities; & < > are defaulted'''
    extras = {"&apos;": "'", "&quot;": '"'}
    if isinstance(o, basestring):
        #info("%s is a string" % o)
        return(unescape(o, extras))
    elif isinstance(o, list): # it's a list of authors with name parts
        new_authors = []
        for author in o:
            new_author = []
            for name_part in author:
                new_author.append(unescape(name_part, extras))
            new_authors.append(new_author)
        return(new_authors)
    else:
        raise TypeError('o = %s; type = %s' % (o, 
            type(o)))

def escape_latex(text):
    text = text.replace('$', '\$') \
        .replace('&', r'\&') \
        .replace('%', r'\%') \
        .replace('#', r'\#') \
        .replace('_', r'\_') \
        .replace('{', r'\{') \
        .replace('}', r'\}') \
        .replace('~', r'\~{}') \
        .replace('^', r'\^{}') 
    return text

def strip_accents(text):
    #"""strip accents and those chars that can't be stripped"""
    ##>>> strip_accents(u'nôn-åscîî') # fails because of doctest bug
    ##u'non-ascii'
    try:    # test if ascii
        text.encode('ascii')
    except UnicodeEncodeError:    
        return ''.join(x for x in unicodedata.normalize('NFKD', text) 
            if unicodedata.category(x) != 'Mn')
            #if x in string.ascii_letters or x in string.digits)
    else:
        return text
    
def normalize_whitespace(text):
    """Remove redundant whitespace from a string, including before comma
    >>> normalize_whitespace('sally, joe , john')
    'sally, joe, john'

    """
    text = text.replace(" ,", ",")
    text = ' '.join(text.split())
    return text

def dict_sorted_by_keys(adict):
    """Return a list of values sorted by dict's keys"""
    for key in sorted(adict):
        dbg("key = '%s'" %(key))
        yield adict[key]

#################################################################
# Entry construction 
#################################################################

ARTICLES = ('a', 'an', 'the')
CONJUNCTIONS = ('and', 'but', 'nor', 'or')
SHORT_PREPOSITIONS = ('among', 'as', 'at', 'by', 'for', 'from', 'in',
    'of', 'on', 'out', 'per', 'to', 'upon', 'with', )
BORING_WORDS = ('', 're') + ARTICLES + CONJUNCTIONS + \
    SHORT_PREPOSITIONS

def identity_add_title(ident, title):
    """Return a non-colliding identity.

    Disambiguate keys by appending the first letter of first 
    3 significant words (i.e., no WP:namespace, articles, conjunctions
    or short prepositions). If only one word, use first, penultimate,
    and last character.

    >>> identity_add_title('Wikipedia 2008', 'Wikipedia:Neutral Point of View')
    'Wikipedia 2008npv'

    """

    suffix = ''
    clean_title = title.replace('Wikipedia:','').replace('Category:','').replace('WikiEN-l','').replace('Wikipedia-l','').replace('Wiki-l','').replace('Wiktionary-l','').replace('Foundation-l','').replace('Textbook-l','').replace('.0','').replace("'","")

    not_alphanum_pat = re.compile("[^a-zA-Z0-9']")
    title_words = not_alphanum_pat.split(clean_title.lower())

    if len(title_words) == 1:
        suffix = title_words[0][0] + title_words[0][-2] + title_words[0][-1]
    else:
        suffix = ''.join([word[0] for word in title_words if word not in BORING_WORDS])
        suffix = suffix[:3]
    ident = ident + suffix
    return ident

def identity_increment(ident, entries):
    """Increment numerical suffix of identity until no longer collides with
    pre-existing entry(s) in the entries dictionary.

    >>> identity_increment('Wikipedia 2008npv',\
    {'Wikipedia 2008npv': {'title': 'Wikipedia:No Point of View',\
    'author': [('', '', 'Wikipedia', '')], 'year': '2008'}})
    'Wikipedia 2008npv1'

    """

    while ident in entries:    # if it still collides
        dbg("\t trying     %s collides with %s" %(ident, entries[ident]['title']))
        if ident[-1].isdigit():
            suffix = int(ident[-1])
            suffix += 1
            ident = ident[0:-1] + str(suffix)
        else:
            ident += '1'
        dbg("\t yielded    %s" % ident)
    return ident

def get_ident(entry, entries, delim=u""):
    """Create an identifier (key) for the entry"""

    last_names = []
    for first, von, last, jr in entry['author']:
        last_names.append(von.replace(' ','') + last.replace(' ',''))
    if len(last_names) == 1: name_part = last_names[0]
    elif len(last_names) == 2: name_part = delim.join(last_names[0:2])
    elif len(last_names) == 3: name_part = delim.join(last_names[0:3])
    elif len(last_names) > 3:
        name_part = last_names[0] + 'Etal'

    if not 'year' in entry: entry['year'] = '0000'
    year_delim = ' ' if delim else ''
    ident = year_delim.join((name_part, entry['year']))
    info("ident = %s '%s'" %(type(ident), ident))
    # remove chars not permitted in xml name/id attributes
    ident = ident.replace(':','').replace("'","")
    # remove some punctuation and strong added by walk_freemind.query_highlight
    ident = ident.replace('.','').replace('<strong>','').replace('</strong>','')
    info("ident = %s '%s'" %(type(ident), ident))
    ident = strip_accents(ident) # bibtex doesn't handle unicode in keys well
    if ident[0].isdigit(): # pandoc forbids keys starting with digits
        ident = 'a' + ident

    ident = identity_add_title(ident, entry['title'])    # get title suffix
    if ident in entries:    # there is a collision
        ident = identity_increment(ident, entries)
    info("ident = %s '%s'" %(type(ident), ident))
    ident = ident.replace('@', '') # '@' is citation designator, so just remove
    return unicode(ident)

def pull_citation(entry):
    """Modifies entry with parsed citation

    Uses this convention: "d=20030723 j=Research Policy v=32 n=7 pp=1217-1241"

    """
    
    entry['custom2'] = entry['_mm_file'].split('/')[-1]
    
    if 'cite' in entry:
        citation = entry['cite']
        dbg("citation = '%s'" %(citation))
        # split around tokens of length 1-3; get rid of first empty string of results

        EQUAL_PAT = re.compile(r'(\w{1,3})=')
        cites = EQUAL_PAT.split(citation)[1:]

        # 2 refs to an iterable are '*' unpacked and rezipped
        cite_pairs = list(zip(*[iter(cites)] * 2))
        for short, value in cite_pairs:
            try:
                entry[BIB_SHORTCUTS[short]] = value.strip()
            except KeyError as error:
                print(("Key error on ", error, entry['title'], entry['_mm_file']))
    else: 
        entry['date'] = '0000'

    ## If it's an URL and has a read date, insert text
    #if 'url' in entry and entry['url'] is not None:
        #if any([site in entry['url'] for site in ('books.google', 'jstor')]):
            #entry['url'] = entry['url'].split('&')[0]

    if 'custom1' in entry and 'url' in entry:
        try:
            urldate = time.strftime("%Y-%m-%d", time.strptime(entry['custom1'], "%Y%m%d"))
        except ValueError:
            urldate = time.strftime("%Y-%m-%d", time.strptime(entry['custom1'], "%Y%m%d %H:%M UTC"))
        entry['urldate'] = urldate
        del entry['custom1']

    if 'month' in entry:
        month_tmp = entry['month']
        if ' ' in month_tmp:
            month, day = month_tmp.split()
            entry['day'] = day
        else:
            month = month_tmp
        try:
            entry['month'] = MONTH2DIGIT[month[0:3].lower()]
        except KeyError:
            entry['issue'] = entry['month']
            del entry['month']

    # bibtex:year, month, day -> biblatex 0.9+:date 
    if 'year' in entry and 'date' not in entry:
        date = entry['year']
        if 'month' in entry:
            date += '-%02d' % int(entry['month'])
            if 'day' in entry:
                if not '-' in entry['day']:
                    date += '-%02d' % int(entry['day'])
                else: # a range
                    start_date, end_date = entry['day'].split('-')
                    date = date + '-%02d' % int(start_date) + \
                        '/' + date + '-%02d' % int(end_date)
        entry['date'] = date

    # biblatex 0.9+:date -> bibtex:year
    if 'date' in entry:
        date = entry['date']
        if '/' in date:
            # biblatex permits ranges delimited by '/', but I do not
            raise Exception("'/' should not be in date.")
        elif '-' in date:
            date_parts = date.split('-') # '2009-05-21'
        else:                            # '20090521'
            date_parts = filter(None, [date[0:4], date[4:6], 
                date[6:8]])  # filter drops empty strings
        if len(date_parts) == 3: 
            entry['year'], entry['month'], entry['day'] = date_parts
            date = '%s-%s-%s' %(date_parts[0], date_parts[1], date_parts[2])
        elif len(date_parts) == 2: 
            entry['year'], entry['month'] = date_parts
            date = '%s-%s' %(date_parts[0], date_parts[1])
        else:
            entry['year'] = date_parts[0]
            date = '%s' %(date_parts[0])
        entry['date'] = date
            
    if ': ' in entry['title']:
        if not entry['title'].startswith('Re:'):
            entry['shorttitle'] = entry['title'].split(':')[0].strip()

    if 'url' in entry and 'oldid' in entry['url']:
        url = entry['url']
        url = url.rsplit('#', 1)[0] # remove fragment
        query = url.split('?', 1)[1]
        queries = parse_qs(query)
        oldid = queries['oldid'][0]
        entry['shorttitle'] = '%s (oldid=%s)' % (entry['title'], oldid)
        if not opts.long_url: # short URLs
            base = 'http://' + url.split('/')[2]
            oldid = '/?oldid=' + oldid
            diff = '&diff=' + queries['diff'][0] if 'diff' in queries else ''
            entry['url'] = base + oldid + diff

    if 'editor' in entry:
        entry['editor'] = parse_names(entry['editor'])
    if 'translator' in entry:
        entry['translator'] = parse_names(entry['translator'])

#################################################################
# Bibtex utilities
#################################################################

def create_bibtex_author(names):
    """Return the parts of the name joined appropriately. 
    The BibTex name parsing is best explained in 
    http://www.tug.org/TUGboat/tb27-2/tb87hufflen.pdf

    >>> create_bibtex_author([('First Middle', 'von', 'Last', 'Jr.'),\
        ('First', '', 'Last', 'II')])
    'von Last, Jr., First Middle and Last, II, First'

    """
    full_names = []
    
    for name in names:
        full_name = ''
        first, von, last, jr = name[0:4]
        
        if all(s.islower() for s in (first, last)): # {{hooks}, {bell}}
            first = '{%s}' % first
            last = '{%s}' % last

        if von != '':
            full_name += von + ' '
        if last != '':
            full_name += last
        if jr != '':
            full_name += ', ' + jr
        if first != '':
            full_name += ', ' + first
        full_names.append(full_name)

    full_names = " and ".join(full_names)
    full_names = normalize_whitespace(full_names)
    return full_names

def guess_bibtex_type(entry):
    """Guess whether the type of this entry is book, article, etc.

    >>> guess_bibtex_type({'author': [('', '', 'Smith', '')],\
        'eventtitle': 'Proceedings of WikiSym 08',\
        'publisher': 'ACM',\
        'title': 'A Great Paper',\
        'venue': 'Porto, Portugal California',\
        'year': '2008'})
    'inproceedings'

    """
    if 'entry_type' in entry:         # already has a type
        et = entry['entry_type']
        if et in BIBLATEX_TYPES:
            pass
        elif et in CSL_TYPES:
            et = CSL_BIBLATEX_TYPE_MAP[et]
        else:
            print("Unknown entry_type = %s" %et)
            sys.exit()
        return et 

    if 'entry_type' in entry:         # already has a type
        return entry['entry_type']
    else:
        et = 'misc'
        if 'eventtitle' in entry:           
            if 'author' in entry:           et = 'inproceedings'
            else:                           et = 'proceedings'
        elif 'booktitle' in entry:          
            if not 'editor' in entry:       et = 'inbook'
            else:
                if 'author' in entry or \
                    'chapter' in entry:      et = 'incollection'
                else:                        et= 'collection'
        elif 'journal' in entry:             et = 'article'

        elif 'author' in entry and 'title' in entry and 'publisher' in entry:
                                            et = 'book'
        elif 'institution' in entry:
            et = 'report' 
            if 'type' in entry:
                if 'report' in entry['type'].lower(): et = 'report'
                if 'thesis' in entry['type'].lower(): et = 'mastersthesis'
                if 'dissertation' in entry['type'].lower(): et = 'phdthesis'
        elif 'url' in entry:                et = 'online'
        elif 'doi' in entry:                et = 'online'
        elif 'year' not in entry:            et = 'unpublished'

        return et


def guess_csl_type(entry):
    """Guess whether the type of this entry is book, article, etc.

    >>> guess_csl_type({'author': [('', '', 'Smith', '')],\
        'eventtitle': 'Proceedings of WikiSym 08',\
        'publisher': 'ACM',\
        'title': 'A Great Paper',\
        'venue': 'Porto, Portugal California',\
        'year': '2008'})
    ('paper-conference', None)

    """
    genre = None
    if 'entry_type' in entry:         # already has a type
        et = entry['entry_type']
        if et in CSL_TYPES:
            return et, genre
        elif et in BIBLATEX_TYPES:
            if et == 'mastersthesis':
                return 'thesis', "Master's thesis"
            elif et == 'phdthesis':
                return 'thesis', "PhD thesis"
            else:
                return BIBLATEX_CSL_TYPE_MAP[et], genre
        else:
            print("Unknown entry_type = %s" %et)
            sys.exit()
    et = 'no-type'
    if any(c in entry for c in CSL_SHORTCUTS.values()):
        info("looking at containers for %s" %entry)
        if 'c_journal' in entry:            et = 'article-journal'
        if 'c_magazine' in entry:           et = 'article-magazine'
        if 'c_newspaper' in entry:          et = 'article-newspaper'
        if 'c_dictionary' in entry:         et = 'entry-dictionary'
        if 'c_encyclopedia' in entry:       et = 'entry-encyclopedia'
        if 'c_forum' in entry:              et = 'post'
        if 'c_blog' in entry:               et = 'post-weblog'
        if 'c_web' in entry:                et = 'webpage'
    else:
        if 'eventtitle' in entry:    
            if 'publisher' in entry:        et = 'paper-conference'
            else:                           et = 'speech'
        elif 'booktitle' in entry:
            if 'editor' in entry:           # collection or incollection
                if 'chapter' in entry:      et = 'chapter'
                else:                       et = 'book'   # ? collection
            elif 'organization' in entry:   et = 'paper-conference'
            else:                           et = 'chapter'
        elif 'journal' in entry:            et = 'article-journal'

        elif 'author' in entry and 'title' in entry and 'publisher' in entry:
                                            et = 'book'
        elif not 'author' in entry:
            if 'venue' in entry:            et = 'book'         # ? proceedings
            if 'editor' in entry:           et = 'book'         # ? collection
        elif 'institution' in entry:
            et = 'report'
            if 'type' in entry:
                org_subtype = entry['type'].lower()
                if 'report' in org_subtype: et = 'report'
                if 'thesis' in org_subtype or 'dissertation' in org_subtype:
                                            et = 'thesis'
        elif 'url' in entry:                et = 'webpage'
        elif 'doi' in entry:                et = 'article'
        elif 'year' not in entry:           et = 'manuscript'

    # APA specific strings for CSL
    # http://sourceforge.net/p/xbiblio/mailman/message/34324611/
    if et == 'post':
        genre = 'Online forum comment'
    elif et == 'post-weblog':
      genre = 'Web log message'
    if 'url' in entry:
        if any([site in entry['url'] for site in (
                'youtube.com', 'vimeo.com')]):
            genre = 'Video file'

    return et, genre

def bibformat_title(title):
    """Title case text, and preserve/bracket proper names/nouns
    See http://nwalsh.com/tex/texhelp/bibtx-24.html
    >>> bibformat_title("Wikirage: What's hot now on Wikipedia")
    "{Wikirage:} {What's} Hot Now on {Wikipedia}"
    >>> bibformat_title('Re: "Suicide methods" article')
    "{Re:} `{Suicide} Methods' Article"
    >>> bibformat_title('''"Am I ugly?": The "disturbing" teen YouTube trend''')
    "`Am {I} Ugly?': {The} `Disturbing' Teen {YouTube} Trend"

    """
    protected_title = cased_title = quoted_title = []

    articles = ['a', 'an', 'the']
    conjunctions = ['and', 'but', 'for', 'or', 'nor']
    contractions = ['s', 't', 've', 're']   # following apostrophe
    others = []
    prepositions = 'aboard about above across after against along among around as at before behind below beneath beside  between beyond but by concerning despite down during except for from in  into like near of off on onto out outside over past per regarding since through throughout till to toward under underneath until up  upon versus with within without'.split()

    words2ignore = articles + conjunctions + contractions + others + prepositions
    words2protect = ('vs.', 'oldid')

    whitespace_pat = re.compile(r"""(\s+['(`"]?)""", re.UNICODE) # \W+
    words = whitespace_pat.split(title)
    
    chunk_pat = re.compile(r"""([-:])""", re.UNICODE)
    def my_title(text):
        '''title case after some chars -- but not ['.] like .title()'''
    
        text_list = list(text)
        text_list[0] = text_list[0].upper()
        for chunk in chunk_pat.finditer(text):
            index = chunk.start()
            if index+1 < len(text_list):
                text_list[index+1] = text_list[index+1].upper()
        return ''.join(text_list)

    for word in words:
        if len(word) > 0:
            info("word = '%s'" %(word))
            if not (word[0].isalpha()):
                info("not (word[0].isalpha())")
                cased_title.append(word)
            elif word in words2ignore:
                info("word in words2ignore")
                cased_title.append(word)
            elif (word in words2protect):
                info("protecting lower '%s'" %(word))
                cased_title.append('{' + word + '}')                
            elif (word[0].isupper()):
                info("protecting title '%s'" %(word))
                cased_title.append('{' + my_title(word) + '}')
            else:
                info("else nothing")
                cased_title.append(my_title(word))
    quoted_title = ''.join(cased_title)

    # convert quotes to LaTeX then convert doubles to singles within the title
    if quoted_title[0] == '"': # First char is a quote
        quoted_title = '``' + quoted_title[1:]
    quoted_title = quoted_title.replace(' "',' ``').replace(" '"," `") # open quote
    quoted_title = quoted_title.replace('" ',"'' ") # close quote
    quoted_title = quoted_title.replace('"',"''") # left-over close quote
    quoted_title = quoted_title.replace('``','`').replace("''","'") # single quotes

    return quoted_title

#################################################################
# Emitters
#################################################################

EXCLUDE_URLS = ('search?q=cache', 'proquest', 'books.google', 
    'amazon.com/reader', 'amazon.com/gp/reader') 
ONLINE_JOURNALS = ('firstmonday.org', 'media-culture.org', 'salon.com', 
    'slate.com')

def emit_biblatex(entries):
    """Emit a biblatex file, with option to emit bibtex"""
    dbg("entries = '%s'" %(entries))

    for entry in dict_sorted_by_keys(entries):
        entry_type = guess_bibtex_type(entry)
        entry_type_copy = entry_type
        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        if entry['ori_author'] in container_values:
            del entry['author']

        # bibtex syntax accommodations
        if 'eventtitle' in entry and 'booktitle' not in entry:
            entry['booktitle'] = 'Proceedings of ' + entry['eventtitle'] 
        if opts.bibtex:
            if 'url' in entry: # most bibtex styles doesn't support url
                note = ' Available at: \url{%s}' % entry['url']
                if 'urldate' in entry:
                    urldate = dateutil.parser.parse(entry['urldate']).strftime(
                        "%d %B %Y")
                    note += ' [Accessed %s]' % urldate
                entry['note'] = entry.setdefault('note', '') + note
            if entry_type == 'online':
                entry_type_copy = 'misc'
            if entry_type == 'report':
                entry_type_copy = 'techreport'
        if opts.bibtex or opts.year:
            if 'date' in entry: 
                del entry['date']
        else: # remove bibtex fields from biblatex
            for token in ('year', 'month', 'day'):
                if token in entry:
                    del entry[token] 

        # if an edited collection, remove author and booktitle
        if all(f in entry for f in ('author', 'editor', 'title', 'booktitle')): 
            if entry['author'] == entry['editor'] and \
                entry['title'] == entry['booktitle']:
                    del entry['author']
                    del entry['booktitle']

        # CSL type and field conversions
        info("entry = %s" %entry)
        for field in ('c_blog', 'c_web', 'c_forum'):
            if field in entry:
                entry_type_copy = 'online'
                entry['organization'] = entry[field]
                del entry[field]
                continue
        for field in ('c_journal', 'c_magazine', 
                        'c_newspaper'):
            if field in entry:
                entry_type_copy = 'article'
                entry['journal'] = entry[field]
                del entry[field]
                continue
        for field in ('c_dictionary', 'c_encyclopedia'):
            if field in entry:
                entry_type_copy = 'inreference'
                entry['booktitle'] = entry[field]
                del entry[field]
                continue

        opts.outfd.write('@%s{%s,\n' % (entry_type_copy, entry['identifier']))

        for short, field in sorted(BIB_SHORTCUTS.items(), key=lambda t: t[1]):
            if field in entry and entry[field] is not None:
                critical("short, field = '%s , %s'" %(short, field))
                # skip these fields
                if field in ('identifier', 'entry_type', 'ori_author'): #'isbn'
                    continue
                if field == 'urldate' and 'url' not in entry:
                    continue # no url, no 'read on'
                if field in ('url'):  
                    critical("url = %s" %entry[field])
                    if any(ban for ban in EXCLUDE_URLS if ban in entry[field]):
                        critical("banned")
                        continue
                    # if online_only and not (online or online journal) then skip
                    if opts.online_urls_only and not (
                        entry_type == 'online' or
                        any(j for j in ONLINE_JOURNALS if j in entry['url'])):
                        critical("not online")
                        continue

                # skip fields not in bibtex
                if opts.bibtex and field not in BIBTEX_FIELDS:
                        continue

                # if entry[field] not a proper string, make it so
                value = unescape_XML(entry[field]) # remove xml entities
                info("value = %s; type = %s" %(value, type(value)))
                if field in ('author', 'editor', 'translator'):
                    value = create_bibtex_author(value)
                if opts.bibtex and field == 'month':
                    value = DIGIT2MONTH[str(int(value))] 

                # escape latex brackets. 
                #   url and howpublished shouldn't be changed
                #   author may have curly brackets that should not be escaped
                if field not in ('author', 'url', 'howpublished'):  # 'note', 
                    value = escape_latex(value) 

                # protect case in titles
                if field in ('title', 'shorttitle'):
                    value = bibformat_title(value)

                opts.outfd.write('   %s = {%s},\n' % (field, value))
        opts.outfd.write("}\n")

def emit_yaml_csl(entries):
    """Emit citations in YAML/CSL for input to pandoc
    
    See: http://reagle.org/joseph/2013/08/bib-mapping.html 
        http://www.yaml.org/spec/1.2/spec.html
        http://jessenoller.com/blog/2009/04/13/yaml-aint-markup-language-completely-different
        
    """
    #import yaml
    
    def esc_yaml(s):
        if s: # faster to just quote than testing for YAML_INDICATORS
            s = s.replace('"', r'\"')
            s = s.replace("#", r"\\#") # pandoc md escaping
            s = s.replace("@", r"\\@") 
            s = '"' + s + '"'
        return s
        
    def emit_yaml_people(people):
        """yaml writer for authors and editors"""
                    
        for person in people:
            info("person = '%s'" %(' '.join(person)))
            #bibtex ('First Middle', 'von', 'Last', 'Jr.')
            #CSL ('family', 'given', 'suffix' 'non-dropping-particle', 'dropping-particle' 
            given, particle, family, suffix = [unescape_XML(chunk) 
                                               for chunk in person]
            opts.outfd.write('  - family: %s\n' % esc_yaml(family))
            if given:
                opts.outfd.write('    given: %s\n' % esc_yaml(given))
                # opts.outfd.write('    given:\n')
                # for given_part in given.split(' '):
                #     opts.outfd.write('    - %s\n' % esc_yaml(given_part))
            if suffix:
                opts.outfd.write('    suffix: %s\n' % esc_yaml(suffix))
            if particle:
                opts.outfd.write('    non-dropping-particle: %s\n' %
                                 esc_yaml(particle))

    def emit_yaml_date(date, season=None):
        """yaml writer for dates"""
        info("date '%s'" %date)
        year, month, day = (date.split('-') +3*[None])[0:3]
        if year:
            opts.outfd.write('    year: %s\n' %year)
        if month:
            opts.outfd.write('    month: %s\n' %month)
        if day:
            opts.outfd.write('    day: %s\n' %day)
        if season:
            opts.outfd.write('    season: %s\n' %season)
        
    # begin YAML file
    # http://blog.martinfenner.org/2013/07/30/citeproc-yaml-for-bibliographies/#citeproc-yaml
    opts.outfd.write('---\n')
    opts.outfd.write('references:\n')
    for entry in dict_sorted_by_keys(entries):
        entry_type, genre = guess_csl_type(entry)
        opts.outfd.write('- id: %s\n' % entry['identifier'])
        opts.outfd.write('  type: %s\n' % entry_type)
        if genre:
            opts.outfd.write('  genre: %s\n' % genre)
        
        # if authorless (replicated in container) then delete
        container_values = [entry[c] for c in CONTAINERS if c in entry]
        if entry['ori_author'] in container_values:
            if not opts.author_create:
                del entry['author']
            else:
                entry['author'] = [['', '', ''.join(entry['ori_author']), '']]
            
        for short, field in sorted(BIB_SHORTCUTS.items(), key=lambda t: t[1]):
            if field in entry and entry[field] is not None:
                value = unescape_XML(entry[field])
                info("short, field = '%s , %s'" %(short, field))
                # skipped fields
                if field in ('identifier', 'entry_type',
                             'day', 'month', 'year', 'issue'):
                    continue

                # special format fields
                if field in ('author', 'editor', 'translator'):
                    opts.outfd.write('  %s:\n' %field)
                    emit_yaml_people(entry[field])
                    continue
                if field in ('date', 'origdate', 'urldate'):
                    if entry[field] == '0000': continue
                    if field == 'date':
                        season = entry['issue'] if 'issue' in entry else None
                        opts.outfd.write('  issued:\n')
                        emit_yaml_date(entry[field], season)
                    if field == 'origdate':
                        opts.outfd.write('  original-date:\n')
                        emit_yaml_date(entry[field])
                    if field == 'urldate':
                        opts.outfd.write('  accessed:\n')
                        emit_yaml_date(entry[field])
                    continue

                if field == 'urldate' and 'url' not in entry:
                    continue # no url, no 'read on'
                if field == 'url':  
                    info("url = %s" %entry[field])
                    if any(ban for ban in EXCLUDE_URLS if ban in entry[field]):
                        info("banned")
                        continue
                    # skip URL articles with no pagination and other offline types
                    if opts.online_urls_only:
                        info("online_urls_only")
                        # don't skip online types
                        if entry_type in ('post', 'post-weblog', 'webpage'):
                            pass
                        # skip items that are paginated
                        elif 'pages' in entry:
                                info("  skipping url, paginated item")
                                continue
                if field == 'eventtitle' and 'container-title' not in entry:
                    opts.outfd.write('  container-title: "Proceedings of %s"\n'
                        %entry['eventtitle'])
                    # opts.outfd.write('  eventtitle: "%s"\n' %entry['eventtitle'])
                      
                info('field = %s' %(field))
                #info('CONTAINERS = %s' %(CONTAINERS))
                info(BIBLATEX_CSL_FIELD_MAP)
                if field in CONTAINERS:
                    field = 'container-title'
                # # containers already in titlecase, so protect from csl:lowercase+titlecase
                # if field == 'container-title':
                #     value = "<span class='nocase'>%s</span>" % value 
                if field in BIBLATEX_CSL_FIELD_MAP:
                    info("field FROM =  %s" %(field))
                    field = BIBLATEX_CSL_FIELD_MAP[field]
                    info("field TO   = %s" %(field))
                opts.outfd.write("  %s: %s\n" % (field, esc_yaml(value)))
    opts.outfd.write('...\n')


def emit_wp_citation(entries):
    """Emit citations in Wikipedia's {{citation}} template format.

    See: http://en.wikipedia.org/wiki/Template:Cite

    """

    def output_wp_names(field, names):
        """Rejigger names for WP odd author and editor conventions."""
        name_num = 0
        for name in names:
            name_num += 1
            if field == 'author':
                prefix = ''
                suffix = name_num
            elif field == 'editor':
                prefix = 'editor' + str(name_num) + '-'
                suffix = ''
            opts.outfd.write(
                '| %sfirst%s = %s\n' % (prefix, suffix, name[0]))
            opts.outfd.write(
                '| %slast%s = %s\n' % (prefix, suffix, ' '.join(name[1:])))
    
    for entry in dict_sorted_by_keys(entries):
        opts.outfd.write('{{ citation\n')
        if 'identifier' in entry:
            wp_ident = get_ident(entry, entries, delim=u" & ")
            opts.outfd.write('| ref = {{sfnref|%s}}\n' % wp_ident)
            
        for short, field in list(BIB_SHORTCUTS.items()):
            if field in entry and entry[field] is not None:
                value = entry[field]
                if field in ( 'annotation', 'custom1', 'custom2',
                    'day', 'entry_type', 'identifier', 'chapter',
                    'keyword', 'month', 'shorttitle', 'year'):
                    continue
                elif field == 'author':
                    output_wp_names(field, entry[field])
                    continue
                elif field == 'editor':
                    output_wp_names(field, entry[field])
                    continue
                elif field == 'title': # TODO: convert value to title case?
                    if 'booktitle' in entry:
                        field = 'chapter'
                elif field in BIBLATEX_WP_FIELD_MAP:
                    field = BIBLATEX_WP_FIELD_MAP[field]
                opts.outfd.write('| %s = %s\n' % (field, value))
        opts.outfd.write("}}\n")


def emit_results(entries, query, results_file):
    """Emit the results of the query"""

    def reverse_print(node, entry):
        """Move the locator number to the end of the text with the Bibtex key"""
        color, text = node.get('COLOR','#000000'), node.get('TEXT')
        prefix = '&gt; ' if color == CL_CO['quote'] else ''
        if len(text) < 50: # don't reverse short texts
            cite = ''
        else:
            locator = ''
            locator_pat = re.compile('^(?:<strong>)?([\d-]+)(?:</strong>)? (.*)')
            matches = locator_pat.match(text)
            if matches:
                text = matches.group(2)
                locator = matches.group(1)
                # http://ctan.mirrorcatalogs.com/macros/latex/contrib/biblatex/doc/biblatex.pdf
                # biblatex: page, column, line, verse, section, paragraph
                # kindle: location
                if 'pagination' in entry:
                    if entry['pagination'] == 'section':
                        locator = ', sec. ' + locator
                    elif entry['pagination'] == 'paragraph':
                        locator = ', para. ' + locator
                    elif entry['pagination'] == 'location':
                        locator = ', loc. ' + locator
                    elif entry['pagination'] == 'chapter':
                        locator = ', ch. ' + locator
                    elif entry['pagination'] == 'verse':
                        locator = ', vers. ' + locator
                    elif entry['pagination'] == 'column':
                        locator = ', col. ' + locator
                    else:
                        raise Exception("unknown locator '%s' for '%s' in '%s'" % (
                            entry['pagination'], entry['title'], 
                            entry['custom2']))
                else:
                    if '-' in locator:
                        locator = ', pp. ' + locator
                    else:
                        locator = ', p. ' + locator
            cite = ' [@%s%s]' %(entry['identifier'].replace(' ',''), locator)

        hypertext = text
        if 'LINK' in node.attrib:
            hypertext = '<a href="%s"> %s</a>' % (escape(node.get('LINK')), text)

        results_file.write('    <li class="%s">%s%s%s</li>\n' %
            (CO_CL[color], prefix, hypertext, cite))

    def pretty_print(node, entry=None, spaces='          '):
        """Pretty print a node and descendants into indented HTML"""
        # bug: nested titles are printed twice. 101217
        spaces = spaces + '  '  # indent the next list
        if node.get('TEXT') is not None:
            reverse_print(node, entry)
        # I should clean all of this up to use simpleHTMLwriter
        if len(node) > 0:     
            results_file.write('%s<ul class="container">\n' % spaces)
            for child in node:
                if CO_CL[child.get('COLOR')] == 'author': # title bug fixed? 110323
                    break
                pretty_print(child, entry, spaces)
            results_file.write('%s</ul>%s\n' % (spaces, spaces))

    def get_url_query(token):
        """Return the URL for an HTML link to the actual title"""
        token = token.replace('<strong>','').replace('</strong>','')
        token = quote(token.encode('utf-8')) # urllib won't accept unicode
        dbg("token = '%s' type = '%s'" %(token, type(token)))
        url_query = \
        escape("http://reagle.org/joseph/plan/search.cgi?query=%s") % token
        dbg("url_query = '%s' type = '%s'" %(url_query, type(url_query)))
        return url_query

    def get_url_MM(file_name):
        """Return the URL for the source MindMap basedon whether CGI or cmdline"""
        if __name__ == '__main__':
            return file_name
        else:                               # CGI
            return 'file://' + '/Users/' + file_name[6:] # change from /home/

    def print_entry(identifier, author, date, title, url, MM_mm_file, base_mm_file, close='</li>\n'):

        identifier_html = '<li class="identifier_html"><a href="%s">%s</a>' % (get_url_query(identifier), identifier)
        title_html = '<a href="%s">%s</a>' % (get_url_query(title), title)
        if url:
            link_html = '[<a href="%s">url</a>]' % url
        else:
            link_html = ''
        from_html =  'from <a href="%s">%s</a>' %(MM_mm_file, base_mm_file)
        results_file.write('  %s, <em>%s</em> %s [%s]%s'
            % (identifier_html, title_html, link_html, from_html, close))

    for entry in dict_sorted_by_keys(entries):
        identifier = entry['identifier']
        author = create_bibtex_author(entry['author'])
        title = entry['title']
        date = entry['date']
        url = entry.get('url','')
        base_mm_file = os.path.basename(entry['_mm_file'])
        MM_mm_file = get_url_MM(entry['_mm_file'])
        
        # if I am what was queried, print all of me
        if entry['identifier'] == opts.query:
            results_file.write('          <li class="li_entry_identifier">\n          <ul class="tit_child">\n'),
            results_file.write('<li style="text-align: right">[<a href="%s">%s</a>]</li>' %(MM_mm_file,base_mm_file),)
            fl_names = ', '.join(name[0] + ' ' + name[2] for name in entry['author'])
            title_mdn = "%s" % (title)
            if url:
                title_mdn = "[%s](%s)" % (title, url)
            results_file.write('<li class="mdn">[%s]: %s, %s, "%s".</li>'
                % (identifier, fl_names, date[0:4], title_mdn))
            results_file.write('<li class="author">%s</li>' % fl_names)
            pretty_print(entry['_title_node'], entry)
            results_file.write('\n          </ul>\n</li>\n'),

        # if I have some nodes that were matched, PP with citation info reversed
        if '_node_results' in entry:
            print_entry(identifier, author, date, title, url, MM_mm_file, base_mm_file,
                '<ul class="li_node_results">\n')
            for node in entry['_node_results']:
                reverse_print(node, entry)
            results_file.write( '  </ul></li>\n')

        # if my author or title matched, print biblio with link to complete entry
        elif '_author_result' in entry:
            author = entry['_author_result'].get('TEXT') + entry['year']
            print_entry(identifier, author, date, title, url, MM_mm_file, base_mm_file)
        elif '_title_result' in entry:
            title = entry['_title_result'].get('TEXT')
            print_entry(identifier, author, date, title, url, MM_mm_file, base_mm_file)

#################################################################
# Mindmap parsing and bib building
#################################################################

def parse_names(names):
    """Do author parsing magic to figure out name components.

    http://artis.imag.fr/~Xavier.Decoret/resources/xdkbibtex/bibtex_summary.html
    http://code.google.com/p/bibstuff/source/browse/trunk/bibname.py?r=6
        parse_raw_names_parts()

    >>> parse_names('First Middle von Last Jr.')
    [('First Middle', 'von', 'Last', 'Jr.')]

    >>> parse_names('First Last, Last')
    [('First', '', 'Last', ''), ('', '', 'Last', '')]

    >>> parse_names('First van der Last, First van der Last II, van Last')
    [('First', 'van der', 'Last', ''), ('First', 'van der', 'Last', 'II'), ('', 'van', 'Last', '')]

    """
    particles = ("al", "bin", "da", "de", "de la", "Du", "la",
                "van", "van den", "van der", "von",
                "Van", "Von")
    suffixes = ("Jr.", "Sr.", "II", "III", "IV")
    names_p = []
    
    info("names = '%s'" %(names))
    names_split = names.split(',')
    for name in names_split:
        info("name = '%s'" %(name))
        first = last = von = jr = ''
        chunks = name.strip().split()

        if 'van' in chunks and chunks[chunks.index('van')+1] in ('den', 'der'):
            chunks[chunks.index('van'):chunks.index('van')+2] = \
            ['van ' + chunks[chunks.index('van')+1]]

        if len(chunks) >1:
            if chunks[-1] in suffixes:
                jr = chunks.pop(-1)
            last = chunks.pop(-1)
            if len(chunks) >0:
                if chunks[-1] in particles:
                    von = chunks.pop(-1)
            first = ' '.join(chunks)
        else:
            last = chunks[0]

        names_p.append((first, von, last, jr))
    return names_p

def commit_entry(entry, entries):
    """Place an entry in the entries dictionary with default values if need be"""
    if entry != {}:
        entry.setdefault('author', [('','John', 'Doe', '')])
        entry.setdefault('title', 'Unknown')
        entry.setdefault('year', '0000')
        entry.setdefault('_mm_file', '')

        # pull the citation, create an identifier, and enter in entries
        try:
            pull_citation(entry)    # break the citation up
        except:
            print ("pull_citation error on %s: %s" %(entry['author'], entry['_mm_file']))
            raise
        entry['identifier'] = get_ident(entry, entries)
        entries[entry['identifier']] = entry

def purge_entries(entries):
    """Delete Null entries"""
    for entry in list(entries.keys()):
        dbg("%s %s" % (type(entry), entry))
        if entries[entry]['identifier'] == 'Null':
            dbg("   deleting %s" % entry)
            del entries[entry]

def walk_freemind(node, mm_file, entries, links):
    """Walk the freemind XML tree and build:
    1. a dictionary of bibliographic entries.
    2. (optionally) for any given entry, lists of author, title, or
        other nodes that match a query.

    This function had originally been implemented recursively, but now
    iterates over a depth-first order list of tree nodes in order to
    satisfy the two requirements:
    1. a single author may have more than one title, and
    2. references without a year should end up in entries with year='0000'.
    Consequently, an entry is only committed when a new title
    is encountered or it is the last entry.

    """
    author = author_node = title = cite = annotation = results = None
    entry = {}

    if useLXML == False:
        parent_map = dict((c, p) for p in node.getiterator() for c in p)
        def get_parent(node):
            return parent_map[node]
    elif useLXML == True:
        def get_parent(node):
            return node.getparent()

    def query_highlight(node, query_c):
        """ Return a modified node with matches highlighted"""
        if query_c and node.get('TEXT'):
            if query_c.search(node.get('TEXT')):
                result = query_c.sub(lambda m:"<strong>" + m.group() + "</strong>",
                    node.get('TEXT'))
                node.set('TEXT', result)
                return node
            else:
                return None
        else:
            return None

    def get_author_node(node):
        """ Return the nearest author node ancestor """
        ancestor = get_parent(node)
        while ancestor.get('COLOR') != CL_CO['author']:
            ancestor = get_parent(ancestor)
        return ancestor

    for d in node.getiterator():
        if 'LINK' in d.attrib:                  # found a local reference link
            if not d.get('LINK').startswith('http:') and d.get('LINK').endswith('.mm'):
                links.append(d.get('LINK'))
        if 'COLOR' in d.attrib: # don't pick up structure nodes and my comments
            if d.get('COLOR') == CL_CO['author']:
                # pass author as it will be fetched upon new title
                pass
            elif d.get('COLOR') == CL_CO['title']:

                commit_entry(entry,entries)     # new entry, so store previous
                entry = {}                      # and create new one

                # because entries are based on unique titles, author processing
                # is deferred until now when a new title is found
                author_node = get_author_node(d)
                entry['ori_author'] = author_node.get('TEXT')
                entry['author'] = parse_names(entry['ori_author'])
                author_highlighted = query_highlight(author_node, opts.query_c)
                if author_highlighted is not None:
                    entry['_author_result'] = author_highlighted

                entry['title'] = d.get('TEXT')
                entry['_mm_file'] = mm_file
                entry['_title_node'] = d
                title_highlighted = query_highlight(d, opts.query_c)
                if title_highlighted is not None:
                    entry['_title_result'] = title_highlighted
                if 'LINK' in d.attrib:
                    entry['url'] = d.get('LINK')
            else:
                if d.get('COLOR') == CL_CO['cite']:
                    entry['cite'] = d.get('TEXT')
                elif d.get('COLOR') == CL_CO['annotation']:
                    entry['annotation'] = d.get('TEXT').strip()
                node_highlighted = query_highlight(d, opts.query_c)
                if node_highlighted is not None:
                    entry.setdefault('_node_results', []).append(node_highlighted)

    commit_entry(entry,entries)  # commit the last entry as no new titles left
    purge_entries(entries)

    return entries, links


RESULT_FILE_HEADER = """<!DOCTYPE html PUBLIC "-//W3C//DTD HTML 4.01 Transitional//EN"
      "http://www.w3.org/TR/html4/loose.dtd">
    <html>
    <head>
    <meta http-equiv="Content-Type"
    content="text/html; charset=UTF-8" />
    <link href="http://reagle.org/joseph/2005/01/mm-print.css"
    rel="stylesheet" type="text/css" />
"""

RESULT_FILE_QUERY_BOX = """    <title>Results for '%s'</title>
    </head>
    <body>
        <div>
            <form method="get" action="http://reagle.org/joseph/plan/search.cgi">
            <input type="submit" value="Go" name="Go" /> <input type="text" size="25"
            name="query" maxlength="80" /> <input type="radio" name="sitesearch"
            value="BusySponge" /> BS <input type="radio" name="sitesearch"
            checked="checked" value="MindMap" /> MM</form>
        </div>
        <h2>Results for '%s'</h2>
        <ul>
"""

def build_bib(file_name, output):
    """Collect the files to walk and invoke functions to build a bib"""

    links = []          # list of other files encountered in the mind map
    done = []           # list of files processed, kept to prevent loops
    entry = {}          # dict of bibliographic data
    entries = OrderedDict() # dict of {id : {entry}}, by insertion order
    mm_files = []
    mm_files.append(file_name)  # list of file encountered (e.g., chase option)
    dbg("   mm_files = %s" % mm_files)
    for mm_file in mm_files:
        if mm_file in done:
            continue
        else:
            dbg("   processing %s" % mm_file)
            try:
                doc = parse(mm_file).getroot()
            except IOError as err:
                dbg("    failed to parse %s" % mm_file)
                continue
            dbg("    successfully parsed %s" % mm_file)
            entries, links = walk_freemind(doc, mm_file, entries, links=[])
            if opts.chase:
                for link in links:
                    link = os.path.abspath(os.path.dirname(mm_file) + '/' +link)
                    if link not in done:
                        if not any([word in link for word in ('syllabus', 'readings')]):
                            dbg("    placing %s in mm_files" %link)
                            mm_files.append(link)
            done.append(os.path.abspath(mm_file))

    if opts.query:
        results_file_name = TMP_DIR + 'query-thunderdell.html'
        if os.path.exists(results_file_name): os.remove(results_file_name)
        try:
            results_file = codecs.open(results_file_name, "w", "utf-8")
        except IOError:
            print(("There was an error writing to", results_file_name))
            sys.exit()
        results_file.write(RESULT_FILE_HEADER)
        results_file.write(RESULT_FILE_QUERY_BOX % (opts.query,opts.query))
        emit_results(entries, opts.query, results_file)
        results_file.write('</ul></body></html>\n')
        results_file.close()
        if not opts.cgi:
            webbrowser.open('file://' + results_file_name.encode('utf-8'))
    elif opts.pretty:
        results_file_name = TMP_DIR + 'pretty-print.html'
        try:
            results_file = codecs.open(results_file_name, "w", "utf-8")
        except IOError:
            print(("There was an error writing to", results_file_name))
            sys.exit()
        results_file.write(RESULT_FILE_HEADER)
        results_file.write('    <title>Pretty Mind Map</title></head><body>\n<ul class="top">\n')
        for entry in list(entries.values()):
            opts.query = entry['identifier']
            emit_results(entries, opts.query, results_file)
        results_file.write('</ul></body></html>\n')
        results_file.close()
        if not opts.cgi:
            webbrowser.open('file://' + results_file_name.encode('utf-8'))
    else:
        output(entries)
    return

def _test_results():
    """
    Tests the overall parsing of Mindmap XML and the relationships between authors with multiple titles and nested authors.

    >>> call('fe ~/bin/fe/tests/authorless.mm > \
    /tmp/authorless.txt; \
    diff ~/bin/fe/tests/authorless.txt /tmp/authorless.txt', shell=True)
    0
    >>> call('fe ~/bin/fe/tests/author-child.mm > \
    /tmp/author-child.txt; \
    diff ~/bin/fe/tests/author-child.txt /tmp/author-child.txt', shell=True)
    0
    >>> call('fe ~/bin/fe/tests/author-descendent.mm > \
    /tmp/author-descendent.txt; \
    diff ~/bin/fe/tests/author-descendent.txt /tmp/author-descendent.txt', shell=True)
    0
    >>> call('fe ~/bin/fe/tests/date.mm > /tmp/date.txt; \
    diff ~/bin/fe/tests/date.txt /tmp/date.txt', shell=True)
    0
    >>> call('fe ~/bin/fe/tests/online.mm > /tmp/online.txt; \
    diff ~/bin/fe/tests/online.txt /tmp/online.txt', shell=True)
    0
    >>> call('fe ~/bin/fe/tests/title-escapes.mm > \
    /tmp/title-escapes.txt; \
    diff ~/bin/fe/tests/title-escapes.txt /tmp/title-escapes.txt', shell=True)
    0
    >>> call('fe ~/bin/fe/tests/title-title.mm > \
    /tmp/title-title.txt; \
    diff ~/bin/fe/tests/title-title.txt /tmp/title-title.txt', shell=True)
    0
    >>> call('fe ~/bin/fe/tests/von.mm > /tmp/von.txt; \
    diff ~/bin/fe/tests/von.txt /tmp/von.txt', shell=True)
    0

    """

if __name__ == '__main__':
    parser = OptionParser(usage="""usage: %prog [options] [FILE.mm]\n
    Outputs YAML/CSL bibliography.\n
    Note: Keys are created by appending the first letter of first 
    3 significant words (i.e., no WP:namespace, articles, conjunctions
    or short prepositions). If only one word, use first, penultimate,
    and last character.""")
    parser.add_option("-a", "--author-create", default=False,
                    action="store_true",
                    help="create author for anon entries using container")
    parser.add_option("-b", "--biblatex", default=False,
                    action="store_true",
                    help="emit biblatex fields")
    parser.add_option("--bibtex", default=False,
                    action="store_true",
                    help="emit bibtex fields rather than biblatex")
    parser.add_option("-c", "--chase",
                    action="store_true", default=False,
                    help="chase links between MMs")
    parser.add_option("-D", "--defaults",
                    action="store_true", default=False,
                    help="chase, output YAML/CSL, use default map and output file")
    parser.add_option("-k", "--keys", default='-no-keys',
                    action="store_const", const='-use-keys',
                    help="show bibtex keys in displayed HTML")
    parser.add_option("-f", "--file-out",
                    action="store_true", default=False,
                    help="output goes to FILE.bib")
    parser.add_option("-F", "--fields",
                    action="store_true", default=False,
                    help="show biblatex shortcuts, fields, and types used by fe")
    parser.add_option("-l", "--long-url",
                    action="store_true", default=False,
                    help="use long URLs")
    parser.add_option("-o", "--online-urls-only",
                    action="store_true", default=False,
                    help="emit URLs for online resources only")
    parser.add_option("-p", "--pretty",
                    action="store_true", default=False,
                    help="pretty print")
    parser.add_option("-q", "--query",
                    help="query the mindmaps", metavar="QUERY")
    parser.set_defaults(query_c=None)
    parser.add_option("-s", "--style", default="apalike",
                    help="use bibtex stylesheet (default: %default)", metavar="BST")
    parser.add_option("-T", "--tests",
                    action="store_true", default=False,
                    help="run tests")
    parser.add_option('-V', '--verbose', dest='verbose', action='count',
                    help="Increase verbosity (specify multiple times for more)")
    parser.add_option("-w", "--WP-citation", default=False,
                    action="store_true",
                    help="emit Wikipedia {{citation}} format which can be "
                    "cited via {{sfn|Author2004|loc=p. 45}}. "
                    "See: http://en.wikipedia.org/wiki/Template:Cite")
    parser.add_option("-y", "--YAML-CSL", default=False,
                    action="store_true",
                    help="emit YAML/CSL for use with pandoc [default]")
    ## Defaulting to true because hs-citeproc (via bibutils) 
    ## doesn't grok partial dates such as d=2012
    #parser.add_option("-y", "--year", default=False,
                    #action="store_true",
                    #help="use year (instead of date) even with biblatex")
    opts, files = parser.parse_args()
    opts.year = True
    
    if opts.verbose == 1: log_level = logging.CRITICAL
    elif opts.verbose == 2: log_level = logging.INFO
    elif opts.verbose >= 3: log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format = "%(levelno)s %(funcName).5s: %(message)s")
    
    opts.cgi = False
    opts.outfd = codecs.getwriter('UTF-8')(sys.__stdout__, errors='replace')

    if len(files) == 0:     # Default file
        files = DEFAULT_MAPS
    elif len(files) > 1:
        print("Warning: ignoring all files but the first")
    file_name = os.path.abspath(files[0])


    if opts.WP_citation:
        output = emit_wp_citation
    elif opts.bibtex or opts.biblatex:
        output = emit_biblatex
    else:
        opts.YAML_CSL = True
        output = emit_yaml_csl
    if opts.defaults:
        opts.chase = True
        opts.file_out = True
    if opts.file_out:
        if opts.YAML_CSL:
            extension = '.yaml'
        elif opts.bibtex or opts.biblatex:
            extension = '.bib'
        elif opts.WP_citation:
            extension = '.wiki'
        output_fn = os.path.splitext(file_name)[0] + extension
        opts.outfd = codecs.open(output_fn, "w", "utf-8")
    if opts.tests:
        print("Running doctests")
        import doctest
        doctest.testmod()
    if opts.fields:
        print("                           _BIBTEX_TYPES_ (deprecated)")
        print("                   http://intelligent.pe.kr/LaTex/bibtex2.htm\n")
        pretty_tabulate_list(BIBLATEX_TYPES)
        print("                            _CSL_TYPES_ (preferred)\n")
        print("                   http://aurimasv.github.io/z2csl/typeMap.xml\n")
        pretty_tabulate_list(BIB_TYPES)
        print("                             _EXAMPLES_\n")
        print("         d=2013 in=MIT t=mastersthesis")
        print("         d=2013 in=MIT t=phdthesis")
        print("         d=2014 p=ACM et=Conference on FOO ve=Boston")
        print("\n\n")
        print("                               _FIELD_SHORTCUTS_\n")
        pretty_tabulate_dict(BIB_SHORTCUTS)
        print("         t=bibtex or CSL type")
        print("         ot=organization's subtype (e.g., W3C REC)\n\n")

        sys.exit()
    if opts.query:
        #u'Péña' == unquote(quote(u'Péña'.encode('utf-8'))).decode('utf-8')
        opts.query = unquote(opts.query).decode('utf-8')
        opts.query_c = re.compile(re.escape(opts.query), re.IGNORECASE)
        output = emit_results

    build_bib(file_name, output)

    opts.outfd.close()
else:
    class opts:
        cgi = True              # called from cgi
        chase = True            # Follow freemind links to other local maps
        long_url = False        # Use short 'oldid' URLs for mediawikis
        online_urls_only = False # Emit urls for @online only
        pretty = False          # Print as HTML with citation at end
        query = None            # Query the bibliographies
        query_c = None          # Query re.compiled
