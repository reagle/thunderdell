#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2011 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""Extract a bibliography from a Freemind mindmap"""

#20080509: tried to get authorless+editor entries to work.
    #1. author is often formatted differently, so no easy equivelent
    #2. editors currently have 'and' delimiters in mindmaps
    #3. author-year styles don't like anon authors anyway
#20090519: bibformat_title and pull_citation each use about ~7%
#20100401: should move to using biblatex 0.9 date fields

from cgi import escape, parse_qs
import codecs
from collections import OrderedDict
import datetime
import dateutil.parser    # http://labix.org/python-dateutil
import logging
from optparse import OptionParser
import os
import re
import sys
import time
from urllib import quote, unquote
import unicodedata

from os import environ
HOME = environ['HOME'] if 'HOME' in environ else '/home/reagle'
BROWSER = environ['BROWSER'] if 'BROWSER' in environ else None
DEFAULT_MAPS = (HOME+'/joseph/readings.mm',)

TMP_DIR = HOME + '/tmp/.fe/'
if not os.path.isdir(TMP_DIR):
    os.makedirs(TMP_DIR)

try:
    from lxml.etree import parse, Element, SubElement, ElementTree
    useLXML = True
except:
    from xml.etree.cElementTree import parse, Element, SubElement, ElementTree
    useLXML = False

MONTH2DIGIT = {'jan' : '1', 'feb' : '2', 'mar' : '3',
        'apr' : '4', 'may' : '5', 'jun' : '6',
        'jul' : '7', 'aug' : '8', 'sep' : '9',
        'oct' : '10', 'nov' : '11', 'dec' : '12'}
DIGIT2MONTH = dict((v,k) for k, v in list(MONTH2DIGIT.items()))

# happy to keep using bibtex:address alias of bibtex:location
# keep t, ot, and et straight
BIBLATEX_SHORTCUTS = {'id':'identifier', 
                'a':'address',
                'ad':'addendum',
                'an':'annotation',
                'au':'author',
                'bt':'booktitle',
                'ch':'chapter',
                'doi':'doi',
                'e':'editor',
                'ed':'edition',
                'et':'eventtitle',
                'hp':'howpublished',
                'in':'institution',
                'i':'isbn',
                'j':'journal',
                'kw':'keyword',
                'nt':'note',
                'or':'organization', 
                'ol':'origlanguage', 'od':'origdate', 'op':'origpublisher', 'oy':'origyear',
                'ot':'type', # organization's type
                'ps':'pubstate', #in press, submitted
                'pp':'pages',
                'pa':'pagination',
                'p':'publisher',
                'r':'custom1',
                'sc':'school',
                'se':'series',
                't':'entry_type', # bibtex type
                'tr':'translator',
                'ti':'title', 'st':'shorttitle',
                'rt':'retype',
                'v':'volume', 'is':'issue', 'n':'number',
                'd':'date', 'y':'year', 'm':'month', 'da': 'day',
                'url':'url',
                'urld':'urldate',
                've':'venue',
                'c2':'custom2', 'c3':'catalog', 'c4':'custom4', 'c5':'custom5'}

BIBLATEX_FIELDS = dict([(field, short) for short, field in list(BIBLATEX_SHORTCUTS.items())])

BIBLATEX_TYPES = ('article',
                'book',
                'booklet',
                'collection',# biblatex:collection replace conferece
                'inbook',
                'incollection',
                'inproceedings',    # bibtex:conference
                'manual',
                'mastersthesis',    # thesis type masters
                'misc',
                'phdthesis',        # thesis type phd
                'report',
                'unpublished',
                'patent',
                'periodical',
                'proceedings',
                'online')

BIBTEX_FIELDS = ['address', 'annote', 'author', 'booktitle', 'chapter', 
'crossref', 'edition', 'editor', 'howpublished', 'institution', 'journal', 
'key', 'month', 'note', 'number', 'organization', 'pages', 'publisher', 
'school', 'series', 'title', 'type', 'volume', 'year']
## url not original bibtex standard, but is common, 
## so I include it here and also include it in the note in emit_biblatex.
#BIBTEX_FIELDS.append('url')

#HTML class corresponding to Freemind color
CL_CO = {'annotation': '#999999', 'author': '#338800', 'title': '#090f6b',
    'cite': '#ff33b8', 'author': '#338800',
    'quote': '#166799', 'paraphrase': '#8b12d6',
    'default': '#000000', None: None}
CO_CL = dict([(label, color) for color, label in list(CL_CO.items())])

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
def unescape_XML(s):
    '''Unescape XML character entities; & < > are defaulted'''
    extras = {"&apos;": "'", "&quot;": '"'}
    return(unescape(s, extras))

def escape_latex(text):
    text = text.replace('$', '\$') \
        .replace('&', '\&') \
        .replace('%', '\%') \
        .replace('#', '\#') \
        .replace('_', '\_') \
        .replace('{', '\{') \
        .replace('}', '\}') \
        .replace('~', '\~') \
        .replace('^', '\^') \
        .replace('^', '\textbackslash')
    return text

def not_combining(char):
    return unicodedata.category(char) != 'Mn'

def strip_accents(text, encoding='utf-8'):
    """Test if ascii, if not, remove accents."""
    #>>> strip_accents(u'nôn-åscîî') # fails because of doctest bug
    #u'non-ascii'

    try:    # test if ascii
        text.encode('ascii')
    except UnicodeEncodeError:
        normalized_text= unicodedata.normalize('NFD', text)
        return filter(not_combining, normalized_text).encode(encoding)
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

def sorted_dict_values(adict):
    """Return a list of values sorted by dict's keys"""
    return (adict[key] for key in sorted(adict))

def join_names(names):
    """Return the parts of the name joined approriately

    >>> join_names([('First Middle', 'von', 'Last', 'Jr.'),\
        ('First', '', 'Last', 'II')])
    'von Last, Jr., First Middle and Last, II, First'

    """
    full_names = []

    for name in names:
        first, von, last, jr = name[0:4]
        full_name = ''

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


ARTICLES = ('a', 'an', 'the')
CONJUNCTIONS = ('and', 'but', 'for', 'nor', 'or')
SHORT_PREPOSITIONS = ('on', 'in', 'out', 'to', 'from', 
    'for', 'of', 'with')
BORING_WORDS = ('', 're') + ARTICLES + CONJUNCTIONS + SHORT_PREPOSITIONS

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
        info("\t trying     %s collides with %s" %(ident, entries[ident]['title']))
        if ident[-1].isdigit():
            suffix = int(ident[-1])
            suffix += 1
            ident = ident[0:-1] + str(suffix)
        else:
            ident += '1'
        info("\t yielded    %s" % ident)
    return ident

def get_ident(entry, entries):
    """Create an identifier (key) for the entry"""

    last_names = []
    for first, von, last, jr in entry['author']:
        last_names.append(von + last)
    if len(last_names) == 1: name_part = last_names[0]
    elif len(last_names) == 2: name_part = last_names[0] + last_names[1]
    elif len(last_names) == 3: name_part = last_names[0] + \
        last_names[1] + last_names[2]
    elif len(last_names) > 3:
        name_part = last_names[0] + 'Etal'

    if not 'year' in entry: entry['year'] = '0000'
    ident = ''.join((name_part, entry['year']))
    # remove spaces and chars not permitted in xml name/id attributes
    ident = ident.replace(' ','').replace(':','').replace("'","")
    # remove some punctuation and strong added by walk_freemind.query_highlight
    ident = ident.replace('<strong>','').replace('</strong>','')
    ident = strip_accents(ident) # bibtex doesn't handle unicode in keys well

    ident = identity_add_title(ident, entry['title'])    # get title suffix
    if ident in entries:    # there is a collision
        ident = identity_increment(ident, entries)

    return ident


def guess_bibtex_type(entry):
    """Guess whether the type of this entry is book, article, etc.

    >>> guess_bibtex_type({'author': [('', '', 'Smith', '')],\
        'booktitle': 'Proceedings of WikiSym 08',\
        'publisher': 'ACM',\
        'title': 'A Great Paper',\
        'venue': 'Porto, Portugal California',\
        'year': '2008'})
    'inbook'

    """
    if 'entry_type' in entry:         # already has a type
        return entry['entry_type']
    else:
        et = 'misc'
        if 'eventtitle' in entry:           et = 'inproceedings'
        elif 'booktitle' in entry:
            if 'editor' in entry:             et = 'incollection'
            elif 'organization' in entry:    et = 'inproceedings'
            else:                            et = 'inbook'
        elif 'journal' in entry:             et = 'article'

        elif 'author' in entry and 'title' in entry and 'publisher' in entry:
                                            et = 'book'
        elif not 'author' in entry:
            if 'venue' in entry:             et = 'proceedings'
            if 'editor' in entry:             et = 'collection'
        elif 'institution' in entry:
            et = 'report' # if 'editor' in entry
            if 'type' in entry:
                if 'report' in entry['type'].lower(): et = 'report'
                if 'thesis' in entry['type'].lower(): et = 'mastersthesis'
                if 'dissertation' in entry['type'].lower(): et = 'phdthesis'
        elif 'url' in entry:                et = 'online'
        elif 'doi' in entry:                et = 'online'
        elif 'year' not in entry:            et = 'unpublished'

        return et

def pull_citation(entry):
    """Modifies entry with parsed citation

    Uses this convention: "y=2003 j=Research Policy v=32 n=7 m=July 23 pp=1217-1241"

    """
    
    if 'cite' in entry:
        citation = entry['cite']
        # split around tokens of length 1-3; get rid of first empty string of results

        equal_pat = re.compile(r'(\w{1,3})=')
        cites = equal_pat.split(citation)[1:]

        # 2 references to an iterable object are unpacked with '*' and rezipped
        cite_pairs = list(zip(*[iter(cites)] * 2))
        for short, value in cite_pairs:
            try:
                entry[BIBLATEX_SHORTCUTS[short]] = value.strip()
            except KeyError as error:
                print(("Key error on ", error, entry['title'], entry['_mm_file']))
    else: entry['year'] = '0000'

    ## If it's an URL and has a read date, insert text
    #if 'url' in entry and entry['url'] is not None:
        #if any([site in entry['url'] for site in ('books.google', 'jstor')]):
            #entry['url'] = entry['url'].split('&')[0]

    if 'custom1' in entry and 'url' in entry:
        try:
            date = time.strftime("%Y-%m-%d", time.strptime(entry['custom1'], "%Y%m%d"))
        except ValueError:
            date = time.strftime("%Y-%m-%d", time.strptime(entry['custom1'], "%Y%m%d %H:%M UTC"))
        entry['urldate'] = date

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
            date = date.split('/')[0]
        date_parts = date.split('-') # split '2009-05-21'
        if len(date_parts) == 3: 
            entry['year'], entry['month'], entry['day'] = date_parts
        elif len(date_parts) == 2: 
            entry['year'], entry['month'] = date_parts
        else:
            entry['year'] = date_parts[0]
            
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


def bibformat_title(title):
    """Title case text, and preserve/bracket proper names/nouns
    >>> bibformat_title("Wikirage: What's hot now on Wikipedia")
    "{Wikirage}: {What}'s Hot Now on {Wikipedia}"
    >>> bibformat_title('Re: "Suicide methods" article')
    "{Re}: `{Suicide} Methods' Article"

    """
    protected_title = cased_title = quoted_title = []

    articles = ['a', 'an', 'the']
    conjunctions = ['and', 'but', 'for', 'or', 'nor']
    contractions = ['s', 't', 've', 're']   # following apostrophe
    others = ['18th', '19th', '20th', '21st']
    prepositions = 'aboard about above across after against along among around as at before behind below beneath beside  between beyond but by concerning despite down during except for from in  into like near of off on onto out outside over past per regarding since through throughout till to toward under underneath until up  upon vs. versus with within without'.split()

    words2ignore = articles + conjunctions + contractions + others + prepositions
    words2do = ('oldid')

    whitespace_pat = re.compile(r'(\W+)', re.UNICODE)
    words = whitespace_pat.split(title)

    for word in words:
        if len(word) > 0 and (word[0].isupper() or word in words2do):
            cased_title.append('{' + word + '}')
        elif word in words2ignore:
            cased_title.append(word)
        else:
            cased_title.append(word.title())
    quoted_title = ''.join(cased_title)

    # convert quotes to LaTeX then convert doubles to singles within the title
    quoted_title = quoted_title.replace(' "',' ``').replace(" '"," `") # open quote
    quoted_title = quoted_title.replace('" ',"'' ") # close quote
    quoted_title = quoted_title.replace('"',"''") # left-over close quote
    quoted_title = quoted_title.replace('``','`').replace("''","'") # single quotes

    return quoted_title

def emit_wp_citation(entries):
    """Emit citations in Wikipedia's {{Citation}} template format.

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
    
    for entry in sorted_dict_values(entries):
        opts.outfd.write('{{ Citation\n')
        if 'booktitle' in entry:
            opts.outfd.write('| ref = %s\n' % entry['title'])
            entry['title'] = entry['booktitle']
        if 'identifier' in entry:
            opts.outfd.write('| ref = %s\n' % entry['title'])
            
        for short, field in list(BIBLATEX_SHORTCUTS.items()):
            if field in entry and entry[field] is not None:
                value = entry[field]
                if field in ( 'annotation', 'custom1', 'day', 'entry_type', 
                    'booktitle', 'identifier', 'keyword', 'month', 
                    'shorttitle'):
                    continue
                elif field == 'author':
                    output_wp_names(field, entry[field])
                    continue
                elif field == 'editor':
                    output_wp_names(field, parse_names(entry[field]))
                    continue
                elif field == 'urldate':
                    field = 'accessdate'
                elif field == 'address':
                    field = 'place'
                opts.outfd.write('| %s = %s\n' % (field, value))
        opts.outfd.write("}}\n")


def emit_biblatex(entries):
    """Emit a biblatex file, with option to emit bibtex"""
    EXCLUDE = ('.amazon', 'search?q=cache', 'proquest') # 'books.google',
    ONLINE_JOURNALS = ('firstmonday.org', 'media-culture.org')

    for entry in sorted_dict_values(entries):
        entry_type_copy = entry['entry_type']
        if opts.bibtex:
            if 'url' in entry: # most bibtex styles doesn't support url
                note = ' Available at: \url{%s}' % entry['url']
                if 'urldate' in entry:
                    urldate = dateutil.parser.parse(entry['urldate']).strftime(
                        "%d %B %Y")
                    note += ' [Accessed %s]' % urldate
                entry['note'] = entry.setdefault('note', '') + note
            if 'eventtitle' in entry and 'booktitle' not in entry:
               entry['booktitle'] = 'Proceedings of the ' + entry['eventtitle'] 
            if entry['entry_type'] == 'online':
                entry_type_copy = 'misc'
            if entry['entry_type'] == 'report':
                entry_type_copy = 'techreport'
        if opts.bibtex or opts.year:
            if 'date' in entry: 
                del entry['date']
        else: # remove bibtex fields from biblatex
            for token in ('year', 'month', 'day'):
                if token in entry:
                    del entry[token] 

        opts.outfd.write('@%s{%s,\n' % (entry_type_copy, entry['identifier']))

        for short, field in list(BIBLATEX_SHORTCUTS.items()):
            if field in entry and entry[field] is not None:

                # skip these conditions
                if field in ('identifier', 'entry_type', 'isbn'):
                    continue
                if field in ('note', 'url'):
                    if any(ban for ban in EXCLUDE if ban in entry[field]):
                        continue
                if field in ('urldate', 'url'):
                    if field == 'urldate' and 'url' not in entry:
                        continue # no url, no 'read on'
                    # if online_only and not (online or online journal) then skip
                    if opts.online_urls_only and not (
                    entry['entry_type'] == 'online' or
                    any(j for j in ONLINE_JOURNALS if j in entry['url'])):
                        continue
                if opts.bibtex and field not in BIBTEX_FIELDS: # skip fields not in bibtex
                        continue

                # if entry[field] not a proper string, make it so
                if field == 'author':
                    value = join_names(entry[field])
                    #if value == 'Wikipedia':
                        #value = 'Wikipedia contributors'
                    #if 'url' in entry and 'meta.wikimedia' in entry['url']:
                        #value = 'Meta contributors'
                else:
                    value = entry[field]
                if field in ('editor', 'translator'):
                    value = value.replace(', ', ' and ')
                if field == 'month':
                    value = DIGIT2MONTH[str(int(entry[field]))] # str(int(...)) drops 0s

                # remove xml entities and escape for latex
                value = unescape_XML(value)
                if field not in ('note', 'url', 'howpublished'):
                    value = escape_latex(value) # escape latex except brackets of \url{}

                # protect case in titles
                if field in ('title', 'shorttitle'):
                    value = bibformat_title(value)
                    #if opts.bibtex and entry['entry_type'] == 'online':
                        #value += ' [online]'
                opts.outfd.write('   %s = {%s},\n' % (field, value))
        opts.outfd.write("}\n")


def emit_bibtex_html(file_name, opts):
    """Emit a bibtex file, use bibtex2html, open result in browser

    see bibtex2html http://www.lri.fr/~filliatr/bibtex2html/

    """
    fileName, extension = os.path.splitext(file_name)
    citeFileName = fileName + '.rl'
    if os.path.exists(citeFileName):
        expr = ('bibtex2html -q -i -a %s -nokeywords '
            '-rawurl %s --nobibsource -s %s -citefile %s -o %s %s'
            % (opts.keys, opts.abstract, opts.style, citeFileName,
            fileName +'.bib', fileName + '.bib'))
    else:
        expr = ('bibtex2html -d -q -i -a %s -nokeywords '
            '-rawurl %s --nobibsource -s %s -o %s %s'
            % (opts.keys, opts.abstract, opts.style,
            fileName + '.bib', fileName + '.bib'))
    print(expr)
    os.putenv('TMPDIR', '.')
    os.system(expr)

    fdi = codecs.open(fileName +'.bib.html', "r", "utf-8", "replace")
    fdo = codecs.open(fileName +'.bib.html.tmp', "w", "utf-8", "replace")
    old_text = fdi.read()
    link_str = r"""from\..*?\[(.*?)\]"""
    link_obj = re.compile(link_str, re.MULTILINE| re.DOTALL)
    new_text = link_obj.sub(r"""from <\1>.""", old_text)
    fdo.write(new_text)
    fdi.close()
    fdo.close()

    os.rename(fileName +'.bib.html.tmp', fileName +'.bib.html')
    os.system(opts.browser % (fileName + '.bib.html'))


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

def emit_results(entries, query, results_file):
    """Emit the results of the query"""

    def reverse_print(node, entry):
        """Move the locator number to the end of the text with the Bibtex key"""
        strong_pat = re.compile('^(?:<strong>)?([\d-]+)(?:</strong>)? (.*)')
        color, text = node.get('COLOR','#000000'), node.get('TEXT')
        matches = strong_pat.match(text)
        if matches:
            text = matches.group(2)
            locator = matches.group(1)
            if 'pagination' in entry:
                if entry['pagination'] == 'section':
                    locator = ', sec. ' + locator
                else:
                    print("unknown locator %s" % entry['pagination'])
                    sys.exit
            else:
                if '-' in locator:
                    locator = ', pp. ' + locator
                else:
                    locator = ', p. ' + locator
        else:
            locator = ''
        if 'LINK' in node.attrib:
            hypertext = '<a href="%s"> %s</a>' % (escape(node.get('LINK')), text)
        else:
            hypertext = text
        if color == CL_CO['quote']:
            results_file.write('    <li class="%s">&gt; %s [@%s%s]</li>\n' %
                (CO_CL[color], hypertext, entry['identifier'].replace(' ',''), locator))
        elif color not in (CL_CO['default'], CL_CO['cite']):
            results_file.write('    <li class="%s">%s [@%s%s]</li>\n' %
                (CO_CL[color], hypertext, entry['identifier'].replace(' ',''), locator))
        else:
            results_file.write('    <li class="%s">%s</li>\n' %
                (CO_CL[color], hypertext))

    def pretty_print(node, entry=None, spaces='          '):
        """Pretty print a node and descendents into indented HTML"""
        # bug: nested titles are printed twice. 101217
        spaces = spaces + '  '  # indent the next list
        if len(node) == 0:      # print only a child spinster node
            if node.get('TEXT') is not None:
                reverse_print(node, entry)
        else:
            # print a parent node
            text = node.get('TEXT')
            if 'LINK' in node.attrib:
                hypertext = '<a href="%s"> %s</a>' % (escape(node.get('LINK')), text)
            else:
                hypertext = text
            results_file.write('%s<li class="%s parent">%s\n'
                % (spaces, CO_CL[node.get('COLOR','#000000')], hypertext))
            # I should clean all of this up to use simpleHTMLwriter
            results_file.write('%s<ul class="container">\n' % spaces)
            for child in node:
                if CO_CL[child.get('COLOR')] == 'author': # title bug fixed? 110323
                    break
                pretty_print(child, entry, spaces)
            results_file.write('%s</ul>%s</li>\n' % (spaces, spaces))

    def get_url_query(token):
        """Return the URL for an HTML link to the actual title"""
        token = token.replace('<strong>','').replace('</strong>','')
        token = quote(token.encode('utf-8')) # urllib won't accept unicode
        info("token = '%s' type = '%s'" %(token, type(token)))
        url_query = \
        escape("http://reagle.org/joseph/plan/search.cgi?query=%s") % token
        info("url_query = '%s' type = '%s'" %(url_query, type(url_query)))
        return url_query

    def get_url_MM(file_name):
        """Return the URL for the source MindMap basedon whether CGI or cmdline"""
        if __name__ == '__main__':
            return file_name
        else:                               # CGI
            return 'file://' + file_name

    def print_entry(identifier, author, title, url, MM_mm_file, base_mm_file, close='</li>\n'):

        identifier_html = '<li><a href="%s">%s</a>' % (get_url_query(identifier), identifier)
        title_html = '<a href="%s">%s</a>' % (get_url_query(title), title)
        if url:
            link_html = '[<a href="%s">url</a>]' % url
        else:
            link_html = ''
        from_html =  'from <a href="%s">%s</a>' %(MM_mm_file, base_mm_file)
        results_file.write('  %s, <em>%s</em> %s [%s]%s'
            % (identifier_html, title_html, link_html, from_html, close))

    for entry in sorted_dict_values(entries):
        identifier = entry['identifier']
        author = join_names(entry['author'])
        title = entry['title']
        url = entry.get('url','')
        base_mm_file = os.path.basename(entry['_mm_file'])
        MM_mm_file = get_url_MM(entry['_mm_file'])

        # if I am what was queried, print all of me
        if entry['identifier'] == opts.query:
            results_file.write('          <li>\n          <ul class="tit_child">\n'),
            results_file.write('<li style="text-align: right">[<a href="%s">%s</a>]</li>' %(MM_mm_file,base_mm_file),)
            fl_names = ', '.join(name[0] + ' ' + name[2] for name in entry['author'])
            results_file.write('<li class="author">%s</li>' % fl_names)
            pretty_print(entry['_title_node'], entry)
            results_file.write('          </ul>\n         </li>\n'),

        # if I have some nodes that were matched, PP with citation info reversed
        if '_node_results' in entry:
            print_entry(identifier, author, title, url, MM_mm_file, base_mm_file,
                '<ul>\n')
            for node in entry['_node_results']:
                reverse_print(node, entry)
            results_file.write( '  </ul></li>\n')

        # if my author or title matched, print biblio with link to complete entry
        elif '_author_result' in entry:
            author = entry['_author_result'].get('TEXT') + entry['year']
            print_entry(identifier, author, title, url, MM_mm_file, base_mm_file)
        elif '_title_result' in entry:
            title = entry['_title_result'].get('TEXT')
            print_entry(identifier, author, title, url, MM_mm_file, base_mm_file)

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
    particles = ("al", "bin", "da", "de", "de la", "la",
                "van", "van den", "van der", "von",
                "Van", "Von")
    suffixes = ("Jr.", "Sr.", "II", "III", "IV")
    names_p = []
    
    names_split = names.split(',')
    for name in names_split:
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
            pull_citation(entry)    # break the citation into more bibliographic keys
        except:
            print ("pull_citation error on %s: %s" %(entry['author'], entry['_mm_file']))
            raise
        entry['entry_type'] = guess_bibtex_type(entry) # guess the bibliographic type
        entry['identifier'] = get_ident(entry, entries)
        entries[entry['identifier']] = entry

def purge_entries(entries):
    """Delete Null entries"""
    for entry in list(entries.keys()):
        info("%s %s" % (type(entry), entry))
        if entries[entry]['identifier'] == 'Null':
            info("   deleting %s" % entry)
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
                entry['author'] = parse_names(author_node.get('TEXT'))
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
                    entry['annotation'] = d.get('TEXT')
                node_highlighted = query_highlight(d, opts.query_c)
                if node_highlighted is not None:
                    entry.setdefault('_node_results', []).append(node_highlighted)

    commit_entry(entry,entries)  # commit the last entry as no new titles left
    purge_entries(entries)

    return entries, links


def build_bib(file_name, output):
    """Collect the files to walk and invoke functions to build a bib"""

    links = []          # list of other files encountered in the mind map
    done = []           # list of files processed, kept to prevent loops
    entry = {}          # dict of bibliographic data
    entries = OrderedDict() # dict of {id : {entry}}, by insertion order
    mm_files = []
    mm_files.append(file_name)  # list of file encountered (e.g., chase option)
    info("   mm_files = %s" % mm_files)
    for mm_file in mm_files:
        if mm_file in done:
            continue
        else:
            info("   processing %s" % mm_file)
            try:
                doc = parse(mm_file).getroot()
            except IOError as err:
                info("    failed to parse %s" % mm_file)
                continue
            info("    successfully parsed %s" % mm_file)
            entries, links = walk_freemind(doc, mm_file, entries, links=[])
            if opts.chase:
                for link in links:
                    link = os.path.abspath(os.path.dirname(mm_file) + '/' +link)
                    if 'syllabus' not in link and link not in done:
                        info("    placing %s in mm_files" %link)
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
            command = opts.browser.encode('utf-8') % results_file_name.encode('utf-8')
            os.system(command)
    elif opts.pretty:
        results_file_name = TMP_DIR + 'pretty-print.html'
        try:
            results_file = codecs.open(results_file_name, "w", "utf-8")
        except IOError:
            print(("There was an error writing to", results_file_name))
            sys.exit()
        results_file.write(RESULT_FILE_HEADER)
        results_file.write('    <title>Pretty Mind Map></title></head><body><ul>\n')
        for entry in list(entries.values()):
            opts.query = entry['identifier']
            emit_results(entries, opts.query, results_file)
        results_file.write('</ul></body></html>\n')
        results_file.close()
        if not opts.cgi:
            command = opts.browser.encode('utf-8') % results_file_name.encode('utf-8')
            os.system(command)
    else:
        output(entries)
    return

def _test_results():
    """
    Tests the overall parsing of Mindmap XML and the relationships between authors with multiple titles and nested authors.

    >>> os.system('fe ~/bin/fe/tests/author-child.mm > \
    /tmp/author-child.txt; \
    diff ~/bin/fe/tests/author-child.txt /tmp/author-child.txt')
    0
    >>> os.system('fe ~/bin/fe/tests/author-descendent.mm > \
    /tmp/author-descendent.txt; \
    diff ~/bin/fe/tests/author-descendent.txt /tmp/author-descendent.txt')
    0
    >>> os.system('fe ~/bin/fe/tests/date.mm > /tmp/date.txt; \
    diff ~/bin/fe/tests/date.txt /tmp/date.txt')
    0
    >>> os.system('fe ~/bin/fe/tests/online.mm > /tmp/online.txt; \
    diff ~/bin/fe/tests/online.txt /tmp/online.txt')
    0
    >>> os.system('fe ~/bin/fe/tests/title-escapes.mm > \
    /tmp/title-escapes.txt; \
    diff ~/bin/fe/tests/title-escapes.txt /tmp/title-escapes.txt')
    0
    >>> os.system('fe ~/bin/fe/tests/title-title.mm > \
    /tmp/title-title.txt; \
    diff ~/bin/fe/tests/title-title.txt /tmp/title-title.txt')
    0
    >>> os.system('fe ~/bin/fe/tests/von.mm > /tmp/von.txt; \
    diff ~/bin/fe/tests/von.txt /tmp/von.txt')
    0

    """

if __name__ == '__main__':
    parser = OptionParser(usage="""usage: %prog [options] [FILE.mm]\n
    Note: Keys are created by appending the first letter of first 
    3 significant words (i.e., no WP:namespace, articles, conjunctions
    or short prepositions). If only one word, use first, penultimate,
    and last character.""")
    parser.add_option("-a", "--abstract", default='-noabstract',
                    action="store_const", const='-note annotation',
                    help="include abstracts in bibtex2html HTML")
    parser.add_option("-b", "--bibtex", default=False,
                    action="store_true",
                    help="emit bibtex fields rather than biblatex")
    parser.add_option("-c", "--chase",
                    action="store_true", default=False,
                    help="chase links between MMs")
    parser.add_option("-d", "--display",
                    action="store_true", default=False,
                    help="emit bibtex, convert to HTML, display in browser")
    parser.add_option("-D", "--defaults",
                    action="store_true", default=False,
                    help="chase, use default map and output file")
    parser.add_option("-k", "--keys", default='-no-keys',
                    action="store_const", const='-use-keys',
                    help="show bibtex keys in displayed HTML")
    parser.add_option("-f", "--file-out",
                    action="store_true", default=False,
                    help="output goes to FILE.bib")
    parser.add_option("-F", "--fields",
                    action="store_true", default=False,
                    help="show biblatex shortcuts, fields, and types used by fe")
    parser.add_option("-l", "--long_url",
                    action="store_true", default=False,
                    help="use long URLs")
    parser.add_option("-o", "--online_urls_only",
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
    parser.add_option("-t", "--tests",
                    action="store_true", default=False,
                    help="run tests")
    parser.add_option('-v', '--verbose', dest='verbose', action='count',
                    help="Increase verbosity (specify multiple times for more)")
    parser.add_option("-w", "--WP-citation", default=False,
                    action="store_true",
                    help="emit Wikipedia {{Citation}} format")
    parser.add_option("-y", "--year", default=False,
                    action="store_true",
                    help="use year (instead of date) even with biblatex")
    opts, files = parser.parse_args()

    log_level = 100 # default
    if opts.verbose == 1: log_level = logging.CRITICAL
    elif opts.verbose == 2: log_level = logging.INFO
    elif opts.verbose >= 3: log_level = logging.DEBUG
    logging.basicConfig(level=log_level, format = "%(levelno)s %(funcName).5s: %(message)s")
    critical = logging.critical
    info = logging.info
    dbg = logging.debug
    
    opts.cgi = False
    opts.browser = BROWSER + " '%s'"
    opts.outfd = codecs.getwriter('UTF-8')(sys.__stdout__, errors='replace')

    if len(files) == 0:     # Default file
        files = DEFAULT_MAPS
    elif len(files) > 1:
        print("Warning: ignoring all files but the first")
    file_name = os.path.abspath(files[0])

    if opts.defaults:
        opts.chase = True
        opts.file_out = True
    if opts.file_out:
        output_fn = os.path.splitext(file_name)[0] + '.bib'
        opts.outfd = codecs.open(output_fn, "w", "utf-8")
    if opts.WP_citation:
        output = emit_wp_citation
    else:
        output = emit_biblatex
    if opts.tests:
        print("Running doctests")
        import doctest
        doctest.testmod()
    if opts.fields:
        pretty_tabulate_list(BIBLATEX_TYPES)
        pretty_tabulate_dict(BIBLATEX_SHORTCUTS)
        sys.exit()
    if opts.display:
        opts.bibtex = True
        fileName, extension = os.path.splitext(file_name)
        opts.outfd = codecs.open(fileName + '.bib', 'w', 'utf-8', 'replace')
    if opts.query:
        #u'Péña' == unquote(quote(u'Péña'.encode('utf-8'))).decode('utf-8')
        opts.query = unquote(opts.query).decode('utf-8')
        opts.query_c = re.compile(re.escape(opts.query), re.IGNORECASE)
        output = emit_results

    build_bib(file_name, output)

    if opts.display:
        emit_bibtex_html(file_name, opts)
    opts.outfd.close()
else:
    class opts:
        cgi = True              # called from cgi
        chase = True            # Follow freemind links to other local maps
        web = False             # Generate a html page using bibtex2html
        long_url = False        # Use short 'oldid' URLs for mediawikis
        online_urls_only = False # Emit urls for @online only
        pretty = False          # Print as HTML with citation at end
        query = None            # Query the bibliographies
        query_c = None          # Query re.compiled
