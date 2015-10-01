#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2015 by Joseph Reagle
# Licensed under the GPLv3, see <http://www.gnu.org/licenses/gpl-3.0.html>
#

"""
BusySponge, by Joseph Reagle http://reagle.org/joseph/

BusySponge permits me to easily log and annotate a URL to various loggers
(e.g., mindmap, blogs) with meta/bibliographic data about the URL from
a scraping.

http://reagle.org/joseph/blog/technology/python/busysponge-0.5
"""

# TODO
# * archive URLs to f/old/`r=`

import argparse
from argparse import RawTextHelpFormatter
import codecs
from collections import Counter
from datetime import datetime
from dateutil.parser import parse
import fe
import logging
from lxml import etree
from os.path import expanduser, exists # abspath, basename, splitext
import re
import string
from subprocess import call, Popen 
import sys
import time
# personal Web utility module
from web_little import get_HTML, get_text, unescape_XML, escape_XML 
from change_case import sentence_case

log_level = 100 # default
critical = logging.critical
info = logging.info
dbg = logging.debug

from os import environ
EDITOR = environ.get('EDITOR')
HOME = expanduser("~")

# Expansions for common tags/activities

GENERAL_KEY_SHORTCUTS = {
        'con': 'conflict',
        'exi': 'exit',
        'for': 'fork',
        'hum': 'humor',
        'ide': 'identity',
        'lea': 'leadership',
        'leg': 'legal',
        'ope': 'open',
        'nor': 'norms',
        'pat': 'patience',
        'pol': 'policing',
        'pow': 'power',
        'pra': 'praxis',
        'pri': 'privacy',
        'spe': 'speech',
        'str': 'structure',
        'tea': 'teaching',
        'tec': 'technology',
        'tro': 'troll',
        'zei': 'zeitgeist',
        }

GF_KEY_SHORTCUTS = {
        # Geek Feminism
        'fem': 'feminism',
        'gen': 'gender',
        'gf' : 'gfem',
        'sex': 'sexism',
        'mer': 'meritocracy',
        'prv': 'privilege',
        }

LH_KEY_SHORTCUTS = {
        # Lifehack
        'lh' : 'lifehack',
        'his': 'history',
        'qs' : 'quantifiedself',
        'sh' : 'selfhelp',
        'too': 'tool',
        'min': 'minimalism',
        }

RTC_KEY_SHORTCUTS = {
        # Comments
        'ano' : 'anonymous',
        'ass' : 'assessment',
        'aut' : 'automated',
        'com' : 'competitive',
        'cri' : 'criticism',
        'est' : 'esteem',
        'fak' : 'fake',
        'fee' : 'feedback',
        'inf' : 'informed',
        'man' : 'manipulation',
        'mar' : 'market',
        'mea' : 'mean',
        'off' : 'offensive',
        'qua' : 'quant',
        'ran' : 'ranking',
        'rat' : 'rating',
        'rev' : 'review',
        'sel' : 'self',
        'soc' : 'social',
        'pup' : 'puppet',
        }

WP_KEY_SHORTCUTS = {
        # Wikipedia
        'alt': 'alternative',
        'aut': 'authority',
        'ana': 'analysis',
        'apo': 'apologize',
        'att': 'attack',
        'bia': 'bias',
        'blo': 'block',
        'cab': 'cabal',
        'col': 'collaboration',
        'con': 'consensus',
        'cit': 'citation',
        'coi': 'COI',
        'dep': 'deployment',
        'ecc': 'eccentric',
        'exp': 'expertise',
        'fai': 'faith',
        'fru': 'frustration',
        'gov': 'governance',
        'mot': 'motivation',
        'neu': 'neutrality',
        'not': 'notability',
        'par': 'participation',
        'phi': 'philosophy',
        'pol': 'policy',
        'qua': 'quality',
        'uni': 'universal',
        'ver': 'verifiability',
        }

LIST_OF_KEYSHORTCUTS = (GENERAL_KEY_SHORTCUTS, GF_KEY_SHORTCUTS,
    RTC_KEY_SHORTCUTS,WP_KEY_SHORTCUTS, LH_KEY_SHORTCUTS)

KEY_SHORTCUTS = LIST_OF_KEYSHORTCUTS[0].copy()
for short_dict in LIST_OF_KEYSHORTCUTS[1:]:
    KEY_SHORTCUTS.update(short_dict)

MONTHS = 'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec'

SITE_CONTAINER_MAP = (
    ('arstechnica.com', 'Ars Technica', 'c_newspaper'),
    ('atlantic.com', 'The Atlantic',  'c_magazine'),
    ('boingboing.net', 'Boing Boing',  'c_blog'),
    ('dailydot', 'The Daily Dot',  'c_newspaper'),
    ('engadget.com', 'Engadget',  'c_blog'),
    ('forbes.com', 'Forbes',  'c_magazine'),
    ('huffingtonpost', 'Huffington Post',  'c_newspaper'),
    ('lifehacker.com', 'Lifehacker',  'c_newspaper'),
    ('medium.com', 'Medium',  'c_blog'),
    ('newyorker.com', 'New Yorker',  'c_magazine'),
    ('nytimes.com', 'The New York Times', 'c_newspaper'),
    ('salon.com', 'Salon',  'c_magazine'),
    ('slate.com', 'Slate',  'c_magazine'),
    ('techcrunch.com', 'TechCrunch',  'c_newspaper'),
    ('thegaurdian', 'The Guardian',  'c_newspaper'),
    ('verge.com', 'The Verge',  'c_newspaper'),
    ('Wikipedia_Signpost', 'Wikipedia Signpost', 'c_web'),
    ('wired.com', 'Wired',  'c_magazine'),
    ('wsj.com', 'The Wall Street Journal',  'c_newspaper'),
    ('washingtonpost.com', 'The Washington Post',  'c_newspaper'),
    # ('', '',  'c_magazine'),
)


#######################################
# Utility functions

NOW = time.localtime()

def smart_punctuation_to_ascii(s):
    '''Convert unicode punctuation (i.e., "smart quotes") to simpler form.'''
    info("old %s s = '%s'" %(type(s), s))
    punctuation = { 
        0x2018:u"'",    #apostrophe
        0x2019:u"'", 
        0x201C:u'"',    # quotation
        0x201D:u'"' }
    if s:
        s = s.translate(punctuation)
        s = s.replace(u"—", "--")
        info("new %s s = '%s'" %(type(s), s))
    return s

    
#######################################
# Screen scrapers

class scrape_default(object):
    """
    Default and base class scraper.
    """
    def __init__(self, url, comment):
        print("Scraping default Web page;"),
        self.url = url
        self.comment = comment
        try:
            self.html_b, self.HTML_p, self.html_u, self.resp = get_HTML(
                url, cache_control = 'no-cache')
        except IOError:
            self.html_b, self.HTML_p, self.html_u, self.resp = (None, None, 
                None, None)
            
        self.text = None
        if self.html_b:
            self.text = get_text(url)

    def get_biblio(self):
        biblio = {
            'author' : self.get_author(),
            'date' : self.get_date(),
            'permalink' : self.get_permalink(),
            'excerpt' : self.get_excerpt(),
            'comment' : self.comment,
            'url' : self.url,
        }
        biblio['title'], biblio['c_web'] = self.split_title_org()
        for site, container, container_type in SITE_CONTAINER_MAP:
            if site in biblio['url']:
                info("container = %s" %(container))
                biblio[container_type] = container
                del biblio['c_web']
        return biblio

    def get_author(self):
        '''return guess of article author'''        

        # sadly, lxml doesn't support xpath 2.0 and lower-case()
        AUTHOR_XPATHS = (
            '''//meta[@name='DC.Contributor']/@content''',
            '''//meta[@name='author']/@content''',
            '''//meta[@name='Author']/@content''',
            '''//meta[@name='AUTHOR']/@content''',
            '''//meta[@name='authors']/@content''',
            '''//meta[@http-equiv='author']/@content''',
            '''//a[@rel='author']//text()''',
            '''//span[@class='author']/text()''', #WashingtonPost
            '''//*[@itemprop='author']//text()''', # engadget
            '''//*[contains(@class,'contributor')]/text()''',
            '''//span[@class='name']/text()''',
            '''//*[1][contains(@class, 'byline')]//text()''', # first of many
            '''//a[contains(@href, 'cm_cr_hreview_mr')]/text()''', # amazon
        )
        if self.HTML_p is not None:
            info('checking xpaths')
            for path in AUTHOR_XPATHS:
                info("trying = '%s'" % path)
                xpath_result = self.HTML_p.xpath(path)
                if xpath_result:
                    info("xpath_result = '%s'; xpath = '%s'" %(xpath_result, path))
                    author = string.capwords(''.join(xpath_result).strip())
                    info("author = '%s'; xpath = '%s'" %(author, path))
                    if author != '':
                        return author
                    else:
                        continue
                    
        AUTHOR_REGEXS = (
            "by ([a-z ]*?)(?:-|, |/ | at | on | posted ).{,35}?\d\d\d\d",
            "^\W*(?:posted )?by[:]? (.*)",
            "\d\d\d\d.{,6}? by ([a-z ]*)",
            "\s{3,}by[:]? (.*)",
        )
        if self.text:
            #info(self.text)
            info('checking regexs')
            for regex in AUTHOR_REGEXS:
                info("trying = '%s'" % regex)
                dmatch = re.search(regex, self.text, re.IGNORECASE | re.MULTILINE)
                if dmatch:
                    info('matched: "%s"' % regex)
                    author = dmatch.group(1).strip()
                    MAX_MATCH = 30
                    if ' and ' in author: 
                        MAX_MATCH += 35
                        if ', ' in author: 
                            MAX_MATCH += 35
                    info("author = '%s'" % dmatch.group())
                    if len(author) > 4 and len(author) < MAX_MATCH: 
                        return string.capwords(author)
                    else:
                        info('length %d is <4 or > %d' %(len(author), MAX_MATCH)) 
                else:
                    info('failed: "%s"' % regex)

        return 'UNKNOWN'

    def get_date(self):
        '''rough match of a date, then pass to dateutil's magic abilities'''

        from dateutil.parser import parse

        date_regexp = "(\d+,? )?(%s)\w*(,? \d+)?(,? \d+)" % MONTHS
        try:
            dmatch = re.search(date_regexp, self.text, re.IGNORECASE)
            return parse(dmatch.group(0)).strftime("%Y%m%d")
        except:
            NOW = time.gmtime()
            date = time.strftime('%Y%m%d', NOW)
            info("making date NOW = %s" % date)
            return date

    def split_title_org(self):
        '''Separate the title by a delimiter and test if latter half is the
        organization (if it has certain words (blog) or is too short)'''
        
        ORG_WORDS = ['blog', 'lab', 'center']
        
        title = title_ori = self.get_title()
        info("title_ori = '%s'" %(title_ori))
        org = org_ori = self.get_org()
        info("org_ori = '%s'" %(org_ori))
        STRONG_DELIMTERS = re.compile(u'\s[\|—«»]\s')
        WEAK_DELIMITERS = re.compile(u'[:;-]\s')
        if STRONG_DELIMTERS.search(title_ori):
            info("STRONG_DELIMTERS")
            parts = STRONG_DELIMTERS.split(title_ori)
        else:
            info("WEAK_DELIMITERS")
            parts = WEAK_DELIMITERS.split(title_ori)            
        info("parts = '%s'" %(parts))
        if len(parts) >= 2:
            beginning, end = parts[0], parts[-1]
            title, org = beginning, end
            title_c14n = title.replace(' ','').lower()
            org_c14n = org.replace(' ','').lower()
            if org_ori.lower() in org_c14n.lower(): 
                info("org_ori.lower() in org_c14n.lower(): pass")
                title, org = ' '.join(parts[0:-1]), parts[-1]
            elif org_ori.lower() in title_c14n: 
                info("org_ori.lower() in title_c14n: switch")
                title, org = parts[-1], ' '.join(parts[0:-1])
            else:
                info("beginning = %s, end = %s" %(beginning, end))
                end_ratio = float(len(end)) / len(beginning + end)
                info(" end_ratio: %d / %d = %.2f" %(
                    len(end), len(beginning + end), end_ratio))
                # if beginning has org_word or end is large (>50%): switch
                if end_ratio > 0.5 or \
                        any(word.lower() in beginning for word in ORG_WORDS):
                    info("ratio and org_word: switch")
                    title = end
                    org = beginning
            title = sentence_case(title.strip())
            org = org.strip()
        return title, org

    def get_title(self):

        title_regexps = (
            ('http://lists.w3.org/.*', u'<!-- subject="(.*?)" -->'),
            ('http://lists.kde.org/.*', ur"<title>MARC: msg '(.*?)'</title>"),
            ('', ur'<title>(.*?)</title>')    # default: make sure last
        )

        for prefix, regexp in title_regexps:
            if self.url.startswith(prefix):
                break 
        
        title = "UNKNOWN TITLE"
        if self.html_u:
            tmatch = re.search(regexp, self.html_u, re.DOTALL|re.IGNORECASE)
            if tmatch:
                title = tmatch.group(1).strip()
                title = unescape_XML(title)
                title = sentence_case(title)
                title = smart_punctuation_to_ascii(title)
        return title

    def get_org(self):
        from urlparse import urlparse

        org_chunks = urlparse(self.url)[1].split('.')
        if org_chunks[0] in ('www'):
            org = org_chunks[1]
        elif org_chunks[-2] in ('wordpress', 'blogspot', 'wikia'):
            org = org_chunks[-3]
        else:
            org = org_chunks[-2]
        return org.title()

    def get_excerpt(self):
        '''Select a paragraph if is is long enough and textual'''
        
        if self.text:
            lines = self.text.split('\n')
            for line in lines:
                line = ' '.join(line.split()) # removes redundant space
                if len(line) >= 250: 
                    line = smart_punctuation_to_ascii(line)
                    info("line = '%s'" %(line))
                    info("length = %s; 2nd_char = '%s'" %(len(line), line[1]))
                    if line[1].isalpha():
                        excerpt = line
                        return excerpt.strip()
        return ''

    def get_permalink(self):
        return self.url

class scrape_ISBN(scrape_default):
    
    def __init__(self, url, comment):
        print("Scraping ISBN;"),
        self.url = url
        self.comment = comment

    def get_biblio(self):

        import book_query
        
        info("url = %s" % self.url)
        json_bib = book_query.query(self.url)
        info("json_bib = '%s'" %json_bib)
        biblio = {
            'permalink' : self.url,
            'excerpt' : '',
            'comment' : self.comment,
        }
        info("### json_bib.items()")
        for key, value in json_bib.items():
            info("key = '%s'" %key)
            if key.startswith('subject'):
                continue
            info("key = '%s' value = '%s' type(value) = '%s'\n" %(
                key, value, type(value)))
            if value in (None, [], ''):
                pass
            elif key == 'author':
                biblio['author'] = self.get_author(json_bib)
            elif key == 'year':
                biblio['date'] = json_bib['year']
            elif key == 'pageCount':
                biblio['pages'] = json_bib['pageCount']
            elif key == 'publisher':
                biblio['publisher'] = json_bib['publisher']
            elif key == 'city':
                biblio['address'] = json_bib['city']
            elif key == 'url':
                biblio['url'] = json_bib['url'][0]
            else:
                biblio[key] = json_bib[key]
        if 'title' not in json_bib:
            biblio['title'] = 'UNKNOWN'
        else:
            title = biblio['title'].replace(' : ', ': ')
            biblio['title'] = sentence_case(title)
        return biblio
    
    def get_author(self, bib_dict):
        names = 'UNKNOWN'
        if 'author' in bib_dict:
            info("bib_dict['author'] = '%s'" %bib_dict['author'])
            names = bib_dict['author']
        return names

    def get_date(self, bib_dict):
        # "issued":{"date-parts":[[2007,3]]}
        date_parts = bib_dict['issued']['date-parts'][0]
        info("date_parts = %s" % date_parts)
        if len(date_parts) == 3:
            year, month, day = date_parts
            date = '%d%02d%02' %(int(year), int(month), int(day))
        elif len(date_parts) == 2:
            year, month = date_parts
            date = '%d%02d' % (int(year), int(month))
        elif len(date_parts) == 1:
            date = str(date_parts[0])
        else:
            date = '0000'
        info("date = %s" % date)
        return date

class scrape_DOI(scrape_default):
    
    def __init__(self, url, comment):
        print("Scraping DOI;"),
        self.url = url
        self.comment = comment

    def get_biblio(self):

        import doi_query
        
        info("url = %s" % self.url)
        json_bib = doi_query.query(self.url)
        biblio = {
            'permalink' : self.url,
            'excerpt' : '',
            'comment' : self.comment,
        }
        for key, value in json_bib.items():
            info("key = '%s' value = '%s' type(value) = '%s'" %(
                key, value, type(value)))
            if value in (None, [], ''):
                pass
            elif key == 'author':
                biblio['author'] = self.get_author(json_bib)
            elif key == 'issued':
                biblio['date'] = self.get_date(json_bib)
            elif key == 'page':
                biblio['pages'] = json_bib['page']
            elif key == 'container-title':
                biblio['journal'] = json_bib['container-title']
            elif key == 'issue':
                biblio['number'] = json_bib['issue']
            elif key == 'URL':
                biblio['url'] = json_bib['URL']
            else:
                biblio[key] = json_bib[key]
        if 'title' not in json_bib:
            biblio['title'] = 'UNKNOWN'
        else:
            biblio['title'] = sentence_case(' '.join(
                biblio['title'].split()))
        info("biblio = %s" % biblio)
        return biblio
    
    def get_author(self, bib_dict):
        names = 'UNKNOWN'
        if 'author' in bib_dict:
            names = ''
            for name_dic in bib_dict['author']:
                joined_name = ' '.join(
                    [item for item in name_dic.values() if item])
                info("joined_name = '%s'" %joined_name)
                names = names + ', ' + joined_name
            names = names[2:] # remove first comma
        return names

    def get_date(self, bib_dict):
        # "issued":{"date-parts":[[2007,3]]}
        date_parts = bib_dict['issued']['date-parts'][0]
        info("date_parts = %s" % date_parts)
        if len(date_parts) == 3:
            year, month, day = date_parts
            date = '%d%02d%02d' %(int(year), int(month), int(day))
        elif len(date_parts) == 2:
            year, month = date_parts
            date = '%d%02d' % (int(year), int(month))
        elif len(date_parts) == 1:
            date = str(date_parts[0])
        else:
            date = '0000'
        info("date = %s" % date)
        return date
        
        
class scrape_MARC(scrape_default):
    def __init__(self, url, comment):
        print("Scraping MARC;"),
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        try:
            author = re.search('''From: *<a href=".*?">(.*?)</a>''', self.html_u)
        except AttributeError:
            author = re.search('''From: *(.*)''', self.html_u)
        author = author.group(1)
        author = author.replace(' () ','@').replace(' ! ','.')\
            .replace('&lt;', '<').replace('&gt;', '>')
        author = author.split(' <')[0]
        author = author.replace('"','')
        return author

    def get_title(self):
        subject = re.search('''Subject: *(.*)''', self.html_u).group(1)
        if subject.startswith('<a href'):
            subject = re.search('''<a href=".*?">(.*?)</a>''',subject).group(1)
        subject = subject.replace('[Wikipedia-l] ', '').replace('[WikiEN-l] ', '')
        return subject

    def get_date(self):
        mdate = re.search('''Date: *<a href=".*?">(.*?)</a>''', self.html_u).group(1)
        try:
            date = time.strptime(mdate, "%Y-%m-%d %I:%M:%S")
        except ValueError:
            date = time.strptime(mdate, "%Y-%m-%d %H:%M:%S")
        return time.strftime('%Y%m%d', date)

    def get_org(self):
        return re.search('''List: *<a href=".*?">(.*?)</a>''', self.html_u).group(1)

    def get_excerpt(self):
        excerpt = ''
        msg_body = '\n'.join(self.html_u.splitlines()[13:-17])
        msg_paras = msg_body.split('\n\n')
        for para in msg_paras:
            if para.count('\n') > 2:
                if not para.count('&gt;') >1:
                    excerpt = para.replace('\n',' ')
                    break
        return excerpt.strip()

    def get_permalink(self):
        return self.url


class scrape_ENWP(scrape_default):
    def __init__(self, url, comment):
        print("Scraping en.Wikipedia;"),
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        return 'Wikipedia'

    def split_title_org(self):
        return self.get_title(),  self.get_org()

    def get_title(self):
        title = scrape_default.get_title(self)    # use super()?
        info("title = '%s'" %(title))
        return title.replace(' - Wikipedia, the free encyclopedia','')

    def get_permalink(self):
        if "oldid" not in self.url:
            permalink = self.url.split('/wiki/')[0] + re.search('''<li id="t-permalink"><a href="(.*?)"''', self.html_u).group(1)
            return unescape_XML(permalink)
        else:
            return self.url

    def get_date(self):
        '''find date within <span id="mw-revision-date">19:09, 1 April 2008</span>'''
        _, _, versioned_HTML_u, resp = get_HTML(self.get_permalink())
        time, day, month, year = re.search('''<span id="mw-revision-date">(.*?), (\d{1,2}) (\w+) (\d\d\d\d)</span>''', versioned_HTML_u).groups()
        month = fe.MONTH2DIGIT[month[0:3].lower()]        
        return '%d%02d%02d' %(int(year), int(month), int(day))

    def get_org(self):
        return 'Wikipedia'

    def get_excerpt(self):
        lines = self.text.split('\n')
        for line in lines:
            line = line.strip()
            if (len(line) > 280 and 'This page documents' not in line) or \
            ('This page in a nutshell' in line):
                return line
        return ''

class scrape_WMMeta(scrape_default):

    def __init__(self, url, comment):
        print("Scraping Wikimedia Meta;"),
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        return 'Wikimedia'

    def get_title(self):
        title = scrape_default.get_title(self)    # super()?
        return title.replace(' - Meta','')

    def get_date(self): # Meta is often foobar because of proxy bugs
        pre, po = self.get_permalink().split('?title=')
        citelink = pre + '?title=Special:Cite&page=' + po
        _, _, cite_HTML_u, resp = get_HTML(citelink)
        day, month, year = re.search('''<li> Date of last revision: (\d{1,2}) (\w+) (\d\d\d\d)''', cite_HTML_u).groups()
        month = fe.MONTH2DIGIT[month[0:3].lower()]
        return '%d%02d%02d' %(int(year), int(month), int(day))

    def get_org(self):
        return 'Wikimedia'

    def get_excerpt(self):
        return ''            # no good way to identify first paragraph at Meta

    def get_permalink(self):
        permalink = self.url.split('/wiki/')[0] + re.search('''<li id="t-permalink"><a href="(.*?)"''', self.html_u).group(1)
        return unescape_XML(permalink)

class scrape_geekfeminism_wiki(scrape_default):
    def __init__(self, url, comment):
        print("Scraping geekfeminism wiki"),
        scrape_default.__init__(self, url, comment)

    def get_biblio(self):
        biblio = {
            'author' : 'Geek Feminism',
            'date' : self.get_date(),
            'permalink' : self.get_permalink(),
            'excerpt' : self.get_excerpt(),
            'comment' : self.comment,
            'url' : self.url,
        }
        biblio['title'], biblio['organization'] = self.split_title_org()
        biblio['organization'] = 'Wikia'
        return biblio
    
class scrape_twitter(scrape_default):
    def __init__(self, url, comment):
        print("Scraping twitter"),
        scrape_default.__init__(self, url, comment)

    def get_biblio(self):
        biblio = {
            'author' : self.get_author(),
            'title' : self.get_title(),
            'date' : self.get_date(),
            'permalink' : self.get_permalink(),
            'excerpt' : self.get_excerpt(),
            'comment' : self.comment,
            'url' : self.url,
            'organization': 'Twitter',
        }
        return biblio

    def get_author(self):

        author = self.HTML_p.xpath(
            "//div[@data-user-id]/@data-name")[0]
        return author.strip()

    def get_title(self):

        authororg_title = self.HTML_p.xpath("//title/text()")[0]
        author_org, title = authororg_title.split(':', 1)
        #author = author_org.split('/', 1)[1]
        return title.strip()

    def get_date(self):

        date = self.HTML_p.xpath(
            "//a[contains(@class,'tweet-timestamp')]/span/@data-time")[0]
        date = datetime.fromtimestamp(int(date)).strftime('%Y%m%d')
        return date

    def get_excerpt(self):

        excerpt = self.HTML_p.xpath(
            "//p[contains(@class,'tweet-text')]/text()")[0]
        return excerpt

#######################################
# Output loggers

def log2mm(biblio):
    '''
    Log to bibliographic mindmap, see:
        http://reagle.org/joseph/2009/01/thunderdell.html
    '''

    from xml.etree.ElementTree import ElementTree, Element, SubElement, parse

    print("to log2mm")
    biblio, args.publish = do_console_annotation(biblio)
    
    #now = time.gmtime()
    this_week = time.strftime("%U", NOW)
    this_year = time.strftime('%Y', NOW)
    date_read = time.strftime("%Y%m%d %H:%M UTC", NOW)
    
    ofile = HOME+'/data/2web/reagle.org/joseph/2005/ethno/field-notes.mm'
    info("biblio = %s" %biblio)
    author = biblio['author']
    title = biblio['title']
    abstract = biblio['comment']
    excerpt = biblio['excerpt']
    permalink = biblio['permalink']

    # Create citation
    for token in ['author', 'title', 'url', 'permalink', 'type']:
        if token in biblio: # not needed in citation
            del biblio[token] 
    citation = ''
    for key, value in biblio.items():
        if key in fe.BIB_FIELDS:
            info("key = %s value = %s" %(key, value))
            citation += '%s=%s ' % (fe.BIB_FIELDS[key], value)
    citation += ' r=%s ' % date_read
    if biblio['tags']:
        tags = biblio['tags']
        for tag in tags.strip().split(' '):
            keyword = KEY_SHORTCUTS.get(tag, tag)
            citation += 'kw=' + keyword + ' '
        citation = citation.strip()
    else:
        tags = ''

    mindmap = parse(ofile).getroot()
    mm_years = mindmap[0]
    for mm_year in mm_years:
        if mm_year.get('TEXT') == this_year:
            year_node = mm_year
            break
    else:
        print("creating %s" % year)
        year_node = SubElement(mm_years, 'node', {'TEXT': this_year, 'POSITION': 'right'})
        week_node = SubElement(year_node, 'node', {'TEXT': this_week, 'POSITION': 'right'})

    for week_node in year_node:
        if week_node.get('TEXT') == this_week:
            print("week %s" % this_week)
            break
    else:
        print("creating %s" % this_week)
        week_node = SubElement(year_node, 'node', {'TEXT': this_week, 'POSITION': 'right'})

    author_node = SubElement(week_node, 'node', {'TEXT': author, 'COLOR': '#338800'})
    title_node = SubElement(author_node, 'node', {'TEXT': title, 'COLOR': '#090f6b',
        'LINK': permalink})
    cite_node = SubElement(title_node, 'node', {'TEXT': citation, 'COLOR': '#ff33b8'})
    if abstract:
        abstract_node = SubElement(title_node, 'node', {'TEXT': abstract, 'COLOR': '#999999'})
    if excerpt:
        for exc in excerpt.split('\n\n'):
            if exc.startswith(', '):
                attr_color = '#8b12d6' # paraphrase: purple
                exc = exc[2:]
            elif exc.startswith('. '):
                attr_color = '#999999' # summary: gray 
                exc = exc[2:]
            elif exc.startswith('-- '):
                attr_color = '#000000' # note: black
                exc = exc[3:]
            else:
                attr_color = '#166799' # blue excerpt
            excerpt_node = SubElement(title_node, 'node', {'TEXT': exc, 
                'COLOR': attr_color})     

    ElementTree(mindmap).write(ofile, encoding='utf-8')

    if args.publish: 
        yasn_publish('', title, permalink, tags)


def log2nifty(biblio):
    '''
    Log to personal blog.
    '''

    import codecs

    print("to log2nifty\n")
    ofile = HOME+'/data/2web/goatee.net/nifty-stuff.html'

    title = biblio['title']
    comment = biblio['comment']
    url = biblio['url']

    date_token = time.strftime("%y%m%d", NOW)

    log_item = '<dt><a href="%s">%s</a> (%s)</dt><dd>%s</dd>' % (url, title, date_token, comment)

    fd = open(ofile)
    content = fd.read()
    fd.close()

    insertion_regexp = re.compile('(<dl style="clear: left;">)')
    newcontent = insertion_regexp.sub('\\1 \n  %s' % log_item,content, re.DOTALL|re.IGNORECASE)
    if newcontent:
        fd = codecs.open(ofile, 'w', 'utf-8', 'replace')
        fd.write(newcontent)
        fd.close()
    else:
        print_usage("Sorry, output regexp subsitution failed.")


def log2work(biblio):
    '''
    Log to work microblog
    '''
    import hashlib

    print("to log2work\n")
    info("biblio = '%s'" %(biblio))
    ofile = HOME+'/data/2web/reagle.org/joseph/plan/plans/index.html'

    title = biblio['title'].strip()
    url = biblio['url'].strip()
    comment = biblio['comment'].strip() if biblio['comment'] else ''
    if biblio['tags']:
        hashtags = ''
        for tag in biblio['tags'].strip().split(' '):
            hashtags += '#%s ' %KEY_SHORTCUTS.get(tag, tag)
        hashtags = hashtags.strip()
    else:
        hashtags = '#misc'
    info("hashtags = '%s'" %(hashtags))
    html_comment = comment + ' ' + '<a href="%s">%s</a>' % (escape_XML(url), 
                                                            title)

    date_token = time.strftime("%y%m%d", NOW)
    digest = hashlib.md5(html_comment.encode('utf-8', 'replace')).hexdigest()
    uid = "e" + date_token + "-" + digest[:4]
    log_item = '<li class="event" id="%s">%s: %s] %s</li>' % \
        (uid, date_token, hashtags, html_comment)
    info(log_item)

    fd = codecs.open(ofile, 'r', 'utf-8', 'replace')
    content = fd.read()
    fd.close()

    insertion_regexp = re.compile('(<h2>Done Work</h2>\s*<ol>)')

    newcontent = insertion_regexp.sub(u'\\1 \n  %s\n' %
        log_item, content, re.DOTALL|re.IGNORECASE)
    if newcontent:
        fd = codecs.open(ofile, 'w', 'utf-8', 'replace')
        fd.write(newcontent)
        fd.close()
    else:
        print_usage("Sorry, output regexp subsitution failed.")

    if args.publish:
        yasn_publish(comment, title, url, hashtags)


def log2console(biblio):
    '''
    Log to console.
    '''
      
    print('\n')
    TOKENS = ('author', 'title', 'subtitle', 'date', 'journal', 
        'volume', 'number', 'publisher', 'address', 'DOI', 'isbn',
        'tags', 'comment', 'excerpt', 'url', )
    info("biblio = '%s'" %biblio)
    if biblio['tags']:
        tags = biblio['tags'].strip().split(' ')
        tags_expanded = ''
        for tag in tags:
            tag = KEY_SHORTCUTS.get(tag, tag)
            tags_expanded += tag + ','
        biblio['tags'] = tags_expanded[0:-1] # removes last comma
    bib_in_single_line = ''
    for token in TOKENS:
        info("token = '%s'" %token)
        if token not in biblio: 
            if token == 'url': # I want these printed even if don't exist
                biblio['url'] = ''
            if token == 'title':
                biblio['title'] = ''
        if token in biblio and biblio[token]:
            if token == 'isbn':
                biblio[token] = biblio[token][0]
            print('%s = %s' % (token, biblio[token]))
            bib_in_single_line += '%s = %s ' % (token, biblio[token])
    print('\n%s\n' %bib_in_single_line)
    if 'identifiers' in biblio:
        for identifer, value in biblio['identifiers'].items():
            if identifer.startswith('isbn'):
                print('%s = %s' % (identifer, value[0]))

def blog_at_opencodex(biblio):
    '''
    Start at a blog entry at opencodex
    '''

    blog_title = blog_body = ''
    CODEX_ROOT = HOME+'/data/2web/reagle.org/joseph/content/'
    this_year, this_month, this_day = time.strftime("%Y %m %d", NOW).split()
    blog_title = ' '.join(biblio['title'].split(' ')[0:3])
    entry = biblio['comment']

    category = 'social'
    tags = ''
    if biblio['tags']:
        tags = biblio['tags'].strip().split(' ')
        category = KEY_SHORTCUTS.get(tags[0], tags[0])
        tags_expanded = ''
        for tag in tags:
            tag = KEY_SHORTCUTS.get(tag, tag)
            tags_expanded += tag + ','
        tags = tags_expanded[0:-1] # removes last comma

    if entry:
        blog_title, sep, blog_body = entry.partition('.')
        info("blog_title='%s' sep='%s' blog_body='%s'" %(
            blog_title.strip(), sep, blog_body.strip()))
    info("blog_title='%s'" %(blog_title))

    
    filename = blog_title.lower() \
        .replace(':', '') \
        .replace(' ', '-') \
        .replace( "'", '') \
        .replace("/", "-")
    filename = '%s%s/%s-%s.md' % (CODEX_ROOT, category, this_year, filename)
    info("filename = %s" %filename)
    if exists(filename):
        print("\nfilename '%s' already exists'" % filename)
        sys.exit()
    fd = codecs.open(filename, 'w', 'utf-8', 'replace')
    fd.write('Title: %s\n' % blog_title)
    fd.write('Date: %s\n' % time.strftime("%Y-%m-%d", NOW))
    fd.write('Tags: %s\n' % tags)
    fd.write('Category: %s\n\n' % category)
    fd.write(blog_body.strip())
    if 'url' in biblio and 'excerpt' in biblio:
        fd.write('\n\n[%s](%s)\n\n' %(biblio['title'], biblio['url']))
        fd.write('> %s\n' % biblio['excerpt'])
    fd.close()
    Popen([EDITOR, filename])
    
def blog_at_goatee(biblio):
    '''
    Start at a blog entry at goatee
    '''
    
    GOATEE_ROOT = HOME+'/data/2web/goatee.net/content/'
    info("biblio['comment'] = '%s'" %(biblio['comment']))
    blog_title, sep, blog_body = biblio['comment'].partition('. ')

    this_year, this_month, this_day = time.strftime("%Y %m %d", NOW).split()
    url = biblio.get('url', None)
    filename = blog_title.lower()
    info("blog_title = %s" % blog_title)
    info("filename = %s" % filename)
        
    PHOTO_RE = re.compile('.*/photo/gallery/(\d\d\d\d/\d\d)' \
                '/\d\d-\d\d\d\d-(.*)\.jpe?g')
    photo_match = False
    if 'goatee.net/photo/' in url:
        photo_match = re.match(PHOTO_RE, url)
        if photo_match:
            blog_date = re.match(PHOTO_RE, url).group(1).replace('/', '-')
            blog_title = re.match(PHOTO_RE, url).group(2)
            filename = blog_title
            blog_title = blog_title.replace('-', ' ')
    filename = filename.replace(' ', '-').replace("'", '') 
    info("blog_title = %s" % blog_title)
    info("filename = %s" % filename)
    filename = GOATEE_ROOT + '%s/%s%s-%s.md' % (this_year, this_month, this_day, filename)
    if exists(filename):
        print("\nfilename '%s' already exists'" % filename)
        sys.exit()
    fd = codecs.open(filename, 'w', 'utf-8', 'replace')
    fd.write('Title: %s\n' % blog_title.title())
    fd.write('Date: %s\n' % time.strftime("%Y-%m-%d", NOW))
    fd.write('Tags: \n')
    fd.write('Category: \n\n')
    fd.write(blog_body.strip())
    
    if 'url':
        if biblio.get('excerpt', False):
            fd.write('\n\n[%s](%s)\n\n' %(biblio['title'], biblio['url']))
            fd.write('> %s\n' % biblio['excerpt'])
        if photo_match:
            path, jpg = url.rsplit('/', 1)
            thumb_url = path + '/thumbs/' + jpg
            #thumb_url = url.replace('/web/', '/thumbs/')
            alt_text = blog_title.replace('-', ' ')
            fd.write(
                '''<p><a href="%s"><img alt="%s" class="thumb right" src="%s"/></a></p>\n\n''' 
                % (url, alt_text, thumb_url, ))
            fd.write(
                '''<p><a href="%s"><img alt="%s" class="view" src="%s"/></a></p>''' 
                % (url, alt_text, url))
    fd.close()
    Popen([EDITOR, filename])
    
#######################################
# Dispatchers

def get_scraper(url, comment):
    '''
    Use the URL to specify a screenscraper.
    '''

    info("url = '%s'" %(url))
    if url.lower().startswith('doi:'):
        return scrape_DOI(url, comment)
    elif url.lower().startswith('isbn:'):
        return scrape_ISBN(url, comment)
    else:
        host_path = url.split('//')[1]
    
        dispatch_scraper = (
            ('en.wikipedia.org/w', scrape_ENWP),
            ('meta.wikimedia.org/w', scrape_WMMeta),
            ('marc.info/', scrape_MARC),
            ('geekfeminism.wikia.com/', scrape_geekfeminism_wiki),
            ('twitter.com/', scrape_twitter),
            ('', scrape_default)     # default: make sure last
        )

        for prefix, scraper in dispatch_scraper:
            if host_path.startswith(prefix):
                info("scrape = %s " % scraper)
                return scraper(url, comment)    # creates instance

def get_logger(text):
    """
    Given the argument return a function and parameters.
    """
    LOG_REGEX = re.compile(
        r'(?P<scheme>\w) (?P<tags>(?:\w+ )+)?(?P<url>(\.|doi|isbn|http)\S*)?(?P<comment> .*)?', re.IGNORECASE)

    if LOG_REGEX.match(text):
        params = LOG_REGEX.match(text).groupdict()
        info("params = '%s'" %(params))
        function = None
        if params['scheme'] == 'n':   function = log2nifty
        elif params['scheme'] == 'j': function = log2work
        elif params['scheme'] == 'm': function = log2mm
        elif params['scheme'] == 'c': function = log2console
        elif params['scheme'] == 'o': function = blog_at_opencodex
        elif params['scheme'] == 'g': function = blog_at_goatee
        if function:
            return function, params
        else:
            print_usage("Sorry, unknown scheme: '%s'." % params['scheme'])
    else:
        print_usage("Sorry, I can't parse the argument: '%s'." % text)
    sys.exit()

#######################################
# Miscellaneous
    
def print_usage(message):
    print(message)
    print("Usage: b scheme [tags ]?[url ]?[comment ]?")

def do_console_annotation(biblio):
    '''Augment biblio with console annotations'''
    
    import readline # gives raw_input cursor and history support

    def get_tentative_ident(bibio):
        info(biblio)
        return fe.get_ident(
            { 'author' : fe.parse_names(biblio['author']), 
            'title' : biblio['title'],
            'year' : biblio['date'][0:4]}, {})

    def print_console_msg():
        print('''\tHELP: Enter annotations, excerpt is default\n''' 
            '''\t '. ' begins summary \n'''
            '''\t ', ' begins paraphrase \n'''
            '''\t '-- ' begins note \n'''
            '''\t 'key=value' for metadata; e.g., \n'''
            '''\t\t\tau=John Smith ti=Greatet Book Ever d=2001 et=cb\n'''
            '''\t\tEntry types (et) values must be typed as shortcut:''')
        for key, value in fe.CSL_SHORTCUTS.items():
            print('\t\t\t%s = %s' % (key, value))
        print('''\n\tEnd with CTRL-D.\n''')

    info("biblio['author'] = '%s'" %(biblio['author']))
    tentative_id = get_tentative_ident(biblio)
    print('''@%s : au=%s ti=%s\n''' % (tentative_id, 
                                  biblio['author'], biblio['title'])),
    for key in biblio:
        if key.startswith('c_'):
            print("    %s=%s" %(fe.CSL_FIELDS[key], biblio[key]))

    EQUAL_PAT = re.compile(r'(\w{1,3})=')
    console_annotations = ''
    do_publish = args.publish
    while True:
        try:
            line = raw_input('').decode(sys.stdin.encoding)
            if line == '-p':
                do_publish = True
            elif line == '?':
                print_console_msg()
            elif '=' in line:
                cites = EQUAL_PAT.split(line)[1:]
                # 2 refs to an iterable are '*' unpacked and rezipped
                cite_pairs = list(zip(*[iter(cites)] * 2))
                for short, value in cite_pairs:
                    if short == 'et': # 'et=cj' -> cj = 'Nature'
                        biblio[fe.BIB_SHORTCUTS[value]] = biblio['c_web']
                        del biblio['c_web']
                    else:
                        biblio[fe.BIB_SHORTCUTS[short]] = value.strip()
            else:
                if line:
                    console_annotations += '\n\n' + line
        except EOFError:    # catch ctrl-D
            break
        except KeyError as e:
            print("Bad type shorcut: %s", e)
            print_console_msg()
        except Exception as e:             # trap all other errors
            print("Bad input: %s: '%s'" %(e, line))
    info("biblio.get('excerpt', '') = '%s'" %(biblio.get('excerpt', '')))
    info("console_annotations = '%s'" %(console_annotations))
    biblio['excerpt'] = biblio.get('excerpt', '') + console_annotations
    
    tweaked_id = get_tentative_ident(biblio)
    if tweaked_id != tentative_id:
        print('logged: %s to' % get_tentative_ident(biblio)),
    return biblio, do_publish
        
def yasn_publish(comment, title, url, tags):
    "Send annotated URL to social networks, at this point: twitter via twidge."
    if tags and tags[0] != '#': # they've not yet been hashified
        tags = ' '.join(['#'+KEY_SHORTCUTS.get(tag, tag) 
            for tag in tags.strip().split(' ')])
    comment, title, url, tags = [v.strip() for v in [comment, title, url, tags]]
    comment_delim = ": " if comment else ""
    comment = comment + comment_delim +  '"' + title +  '"'

    TWEET_LEN = 140
    SHORTENER_LEN = 19 # twidge uses is.gd
    tweet_room = TWEET_LEN - len(comment) - len(tags) - len(url)
    shortened_room = 'n/a'
    info("length_comment = %s; tweet_room = %s" %(len(comment), tweet_room))
    if tweet_room < 0:    # the comment is too big
        shortened_room = TWEET_LEN - len(comment) - len(tags) - SHORTENER_LEN
        info("length_comment = %s; shortened_room = %s" %(
            len(comment), shortened_room))
        if shortened_room < 0:
            comment = comment[0:shortened_room-3] + '...'
    tweet = "%s %s %s" %(comment, url, tags)
    info('tweet length = %s' %len(tweet))
    print("tweeted '%s' %s %s" %(tweet, tweet_room, shortened_room))
    call(['twidge', 'update', '%s' %tweet]) # TODO: unicode

#Check to see if the script is executing as main.
if __name__ == "__main__":
    DESCRIPTION = '''
    nifty:         b n TAGS URL|DOI COMMENT
    work plan:     b j TAGS URL|DOI COMMENT
    mindmap:       b m TAGS URL|DOI ABSTRACT
    console:       b c TAGS URL|DOI COMMENT
    blog codex:    b o [pra|soc|tec] TAGS URL|DOI TITLE. BODY
    blog goatee:   b g URL|DOI TITLE. BODY'''
    
    arg_parser = argparse.ArgumentParser(
        prog='b', usage='%(prog)s [options] [URL] logger [keyword] [text]',
        description=DESCRIPTION, formatter_class=RawTextHelpFormatter)
    arg_parser.add_argument("-T", "--tests",
                    action="store_true", default=False,
                    help="run doc tests")
    arg_parser.add_argument("-K", "--keyword-shortcuts",
                action="store_true", default=False,
                help="show keyword shortcuts")
    arg_parser.add_argument('-p', '--publish',
        action="store_true", default=False,
        help="publish to social networks")
    arg_parser.add_argument('text', nargs='*')
    arg_parser.add_argument('-L', '--log-to-file',
        action="store_true", default=False,
        help="log to file %(prog)s.log")
    arg_parser.add_argument('-V', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    arg_parser.add_argument('--version', action='version', version='0.1')

    args = arg_parser.parse_args()

    if args.verbose == 1: log_level = logging.CRITICAL
    elif args.verbose == 2: log_level = logging.INFO
    elif args.verbose >= 3: log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(filename='doi_query.log', filemode='w',
            level=log_level, format = LOG_FORMAT)
    else:
        logging.basicConfig(level=log_level, format = LOG_FORMAT)

    if args.tests:
        print("Running doctests")
        import doctest
        doctest.testmod()
        sys.exit()
    if args.keyword_shortcuts:
        for dictionary in LIST_OF_KEYSHORTCUTS:
            fe.pretty_tabulate_dict(dictionary,3)
        sys.exit()

    logger, params = get_logger(' '.join(args.text)) 
    info("-------------------------------------------------------")
    info("-------------------------------------------------------")
    info("params = '%s'" %(params))
    comment = '' if not params['comment'] else params['comment']
    if params['url']:    # not all log2work entries have urls
        scraper = get_scraper(params['url'].strip(), comment)
        biblio = scraper.get_biblio()
    else:
        biblio = {'title' : '', 'url': '', 'comment': comment}
    biblio['tags'] = params['tags']
    info("biblio = '%s'" %(biblio))
    logger(biblio)