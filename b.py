#!/usr/bin/env python2.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2011 by Joseph Reagle
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
import codecs
from dateutil.parser import parse
import fe
import logging
from lxml import etree
from os.path import exists # abspath, basename, splitext
import re
import string
from subprocess import Popen 
import sys
import time
from web_little import get_HTML, unescape_XML, escape_XML # personal utility module
from change_case import sentence_case

log_level = 100 # default
critical = logging.critical
info = logging.info
dbg = logging.debug

from os import environ
EDITOR = environ.get('EDITOR')
try: 
    HOME = environ['HOME']
except KeyError, e:
    HOME = '/home/reagle'

# Expansions for common tags/activities

GENERAL_KEY_SHORTCUTS = {
        'con': 'conflict',
        'exi': 'exit',
        'for': 'fork',
        'gen': 'gender',
        'hum': 'humor',
        'ide': 'identity',
        'lea': 'leadership',
        'leg': 'legal',
        'ope': 'open',
        'nor': 'norms',
        'pat': 'patience',
        'pow': 'power',
        'pra' : 'praxis',
        'pri': 'privacy',
        'spe': 'speech',
        'str': 'structure',
        'tec' : 'technology',
        'tro': 'trolling',
        'zei': 'zeitgeist',
        }

CC_KEY_SHORTCUTS = {
        'ano' : 'anonymous',
        'ass' : 'assessment',
        'aut' : 'automated',
        'bou' : 'boundaries',
        'com' : 'competitive',
        'cri' : 'criticism',
        'est' : 'esteem',
        'fee' : 'feedback',
        'inf' : 'informed',
        'gam' : 'gaming',
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
        'his': 'history',
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

LIST_OF_KEYSHORTCUTS = (GENERAL_KEY_SHORTCUTS, 
    CC_KEY_SHORTCUTS,WP_KEY_SHORTCUTS)

KEY_SHORTCUTS = LIST_OF_KEYSHORTCUTS[0].copy()
for short_dict in LIST_OF_KEYSHORTCUTS[1:]:
    KEY_SHORTCUTS.update(short_dict)

MONTHS = 'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec'

#######################################
# Utility functions

NOW = time.localtime()

def get_text(url):
    '''Textual version of url'''

    import os

    return unicode(os.popen('w3m -O utf8 -cols 10000 '
        '-dump "%s"' %url).read().decode('utf-8', 'replace'))

def smart_punctuation_to_ascii(s):
    '''Convert unicode punctuation (i.e., "smart quotes") to simpler form.'''
    info("old %s s = '%s'" %(type(s), s))
    punctuation = { 
        0x2018:0x27, 
        0x2019:0x27, 
        0x201C:0x22, 
        0x201D:0x22 }
    s = s.translate(punctuation)
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
            self.html, resp = get_HTML(url, cache_control = 'no-cache')
        except IOError:
            self.html, resp = None, None
            
        self.text = None
        if self.html:
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
        biblio['title'], biblio['organization'] = self.split_title_org()
        return biblio

    def get_author(self):
        '''return guess of article author'''        

        # sadly, lxml doesn't support xpath 2.0 and lower-case()
        AUTHOR_XPATHS = (
            '''//meta[@name='author']/@content''',
            '''//meta[@name='Author']/@content''',
            '''//meta[@name='AUTHOR']/@content''',
            '''//meta[@name='authors']/@content''',
            '''//meta[@http-equiv='author']/@content''',
            '''//a[@rel='author']//text()''',
            '''//*[contains(@class,'contributor')]/text()''',
            '''//span[@class='name']/text()''',
            '''//*[contains(@class, 'byline')]//text()''',
            '''//a[contains(@href, 'cm_cr_hreview_mr')]/text()''', # amazon
        )
        if self.html:
            critical('checking xpaths')
            html_parser = etree.HTMLParser()
            self.doc = etree.fromstring(self.html, html_parser)
            for path in AUTHOR_XPATHS:
                critical("trying = '%s'" % path)
                xpath_result = self.doc.xpath(path)
                if xpath_result:
                    critical("xpath_result = '%s'; xpath = '%s'" %(xpath_result, path))
                    author = string.capwords(''.join(xpath_result).strip())
                    critical("author = '%s'; xpath = '%s'" %(author, path))
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
            critical('checking regexs')
            for regex in AUTHOR_REGEXS:
                critical("trying = '%s'" % regex)
                dmatch = re.search(regex, self.text, re.IGNORECASE | re.MULTILINE)
                if dmatch:
                    critical('matched: "%s"' % regex)
                    author = dmatch.group(1).strip()
                    MAX_MATCH = 30
                    if ' and ' in author: 
                        MAX_MATCH += 35
                        if ', ' in author: 
                            MAX_MATCH += 35
                    critical("author = '%s'" % dmatch.group())
                    if len(author) > 4 and len(author) < MAX_MATCH: 
                        return string.capwords(author)
                    else:
                        critical('length %d is <4 or > %d' %(len(author), MAX_MATCH)) 
                else:
                    critical('failed: "%s"' % regex)

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
        organization (if it has certain words (blog) or is it short)'''
        
        ORG_WORDS = ['blog']
        
        title = self.get_title()
        critical("title = '%s'" %(title))
        org = self.get_org()
        DELIMTER = re.compile('([-\|:;«])') # 
        parts = DELIMTER.split(title)
        if len(parts) >= 2:
            beginning, end = ''.join(parts[0:-2]), parts[-1]
            critical("beginning = %s, end = %s" %(beginning, end))
            title_lower = title.lower()
            if any(org_word in title_lower for org_word in ORG_WORDS):
                return sentence_case(beginning.strip()), end.strip().title()
            end_ratio = float(len(end)) / len(beginning + end)
            critical(" %d / %d = %.2f" %( len(end),  len(beginning + end), end_ratio))
            if end_ratio <= 0.35 or len(end) <= 20:
                return sentence_case(beginning.strip()), end.strip().title()
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
        if self.html:
            tmatch = re.search(regexp, self.html, re.DOTALL|re.IGNORECASE)
            if tmatch:
                title = tmatch.group(1).strip()
                title = unescape_XML(title)
                title = sentence_case(title)
                title = smart_punctuation_to_ascii(title)
        return title

    def get_org(self):
        from urlparse import urlparse

        org_chunks = urlparse(self.url)[1].split('.')
        if 'Wikipedia_Signpost' in self.url:
            org = 'Wikipedia Signpost'
        elif org_chunks[0] in ('www'):
            org = org_chunks[1]
        elif org_chunks[-2] in ('wordpress', 'blogspot', 'wikia'):
            org = org_chunks[-3]
        else:
            org = org_chunks[-2]
        return org.title()

    def get_excerpt(self):
        if self.text:
            lines = self.text.split('\n')
            for line in lines:
                line = line.strip()
                if len(line) > 280 and '__' not in line:
                    excerpt = line
                    return excerpt.strip()
        return None

    def get_permalink(self):
        return self.url

class scrape_photo_net(object):
    """
    Scrape photo.net postings
    e.g., http://photo.net/site-help-forum/00ajKF
    """
    def __init__(self, url, comment):
        print("Scraping photo.net;"),
        self.url = url
        self.comment = comment
        self.html, resp = get_HTML(url, cache_control = 'no-cache')        
        html_parser = etree.HTMLParser()
        self.doc = etree.fromstring(self.html, html_parser)

    def get_biblio(self):
        biblio = {
            'author' : self.get_author(),
            'title' : self.get_title(),
            'date' : self.get_date(),
            'permalink' : self.url,
            'excerpt' : self.get_excerpt(),
            'comment' : self.comment,
            'url' : self.url,
        }
        biblio['organization'] = "photo.net Site Help Forum &gt; Photo Critique and Rating"
        return biblio
        
    def get_author(self):

        author = self.doc.xpath(
            "//div[@class='originalpost']/p/a[@href]/text()")[0]
        return author.strip()

    def get_title(self):

        title = self.doc.xpath("//title/text()")[0]
        title = title.split('- Photo.net')[0]
        return title.strip()
        
    def get_date(self):

        date = self.doc.xpath(
            "//div[@class='originalpost']/p/text()")[1]
        date = parse(date).strftime("%Y%m%d")
        return date

    def get_excerpt(self):

        excerpt = self.doc.xpath(
            "//div[@class='originalpost']/div[@class='message']/p/text()")[0]
        return excerpt
        
        
class scrape_DOI(scrape_default):
    
    def __init__(self, url, comment):
        print("Scraping DOI;"),
        self.url = url
        self.comment = comment

    def get_biblio(self):

        import doi_query
        import json
        
        json_string = doi_query.query(self.url)
        info("json_string = %s" % json_string)
        json_bib = json.loads(json_string)
        biblio = {
            'permalink' : self.url,
            'excerpt' : '',
            'comment' : self.comment,
        }
        for key, value in json_bib.items():
            info("key = '%s' value = '%s' type(value) = '%s'" %(key,value,type(value)))
            if value in (None, [], ''):
                pass
            elif key == 'author':
                biblio['author'] = self.get_author(json_bib)
            elif key == 'issued':
                biblio['date'] = self.get_date(json_bib)
            elif key == 'page':
                biblio['pages'] = json_bib['page']
            elif key == 'container-title':
                biblio['jounal'] = json_bib['container-title']
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
        names = ''
        if 'author' in bib_dict:
            for name_dic in bib_dict['author']:
                info("name_dic.values() = %s" % name_dic.values())
                names = names + ', ' + ' '.join(name_dic.values())
            names = names[2:] # remove first comma
        else:
            names = 'UNKNOWN'
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
            date = date_parts
        else:
            date = '0000'
        info("date = %s" % date)
        return date
        
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
            permalink = self.url.split('/wiki/')[0] + re.search('''<li id="t-permalink"><a href="(.*?)"''', self.html).group(1)
            return unescape_XML(permalink)
        else:
            return self.url

    def get_date(self):
        '''find date within <span id="mw-revision-date">19:09, 1 April 2008</span>'''
        versioned_html, resp = get_HTML(self.get_permalink())
        time, day, month, year = re.search('''<span id="mw-revision-date">(.*?), (\d{1,2}) (\w+) (\d\d\d\d)</span>''', versioned_html).groups()
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
        return None

        
class scrape_Signpost(scrape_ENWP):
    def __init__(self, url, comment):
        print("Scraping en.Wikipedia Signpost;"),
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        '''guess author in: By Thomas888b and HaeB, 21 March 2011'''
        author_regexp3 = "By (.*?), \d\d"
        dmatch = re.search(author_regexp3, self.text, re.IGNORECASE)
        if dmatch:
            authors = dmatch.group(1)
            authors = authors.replace(' and ', ', ')
            return authors
        return 'UNKNOWN'

    def get_title(self):
        title = scrape_default.get_title(self)
        title = title.replace(' - Wikipedia, the free encyclopedia','')
        title = title.split('/', 1)[-1]
        return title

    def get_org(self):
        return 'Wikipedia Signpost'


class scrape_NupediaL(scrape_default):
    def __init__(self, url, comment):
        print("Scraping local Nupedia archive;"),
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        author = re.search('''<B>(.*)''', self.html).group(1)
        author = author.replace('</B>','')
        return author

    def get_title(self):
        title = re.search('''<H1>(.*)''', self.html).group(1)
        return title.replace('</H1>','').replace('nupedia-l','')\
            .replace('[Nupedia-l]','')

    def get_date(self):
        mdate = re.search('''<I>(.*?)</I>''', self.html).group(1)[:16].strip()
        date = time.strptime(mdate, "%a, %d %b %Y")
        return time.strftime('%Y%m%d', date)

    def get_org(self):
        return 'nupedia-l'

    def get_excerpt(self):
        return None

    def get_permalink(self):
        return 'http://web.archive.org/web/20030822044803/http://www.nupedia.com/pipermail/' + self.url[24:]


class scrape_WM_lists(scrape_default):

    def __init__(self, url, comment):
        print("Scraping Wikimedia Lists;"),
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        return re.search('''<B>(.*?)</B>''', self.html).group(1)

    def get_title(self):
        return re.search('''<H1>.*\](.*?)</H1>''', self.html).group(1) \
            .replace(' [Foundation-l] ','')

    def get_date(self):
        mdate = re.search('''<I>(.*?)</I>''', self.html).group(1).strip()
        date = time.strptime(mdate, "%a %b %d %H:%M:%S %Z %Y")
        return time.strftime('%Y%m%d', date)

    def get_org(self):
        return re.search('''<TITLE> \[(.*?)\]''', self.html).group(1)

    def get_excerpt(self):
        msg_body = '\n'.join(self.text.splitlines()[12:-10])
        msg_paras = msg_body.split('\n\n')
        for para in msg_paras:
            if len(para) > 240 and para.count('>') < 1:
                excerpt = para.replace('\n',' ')
                print(excerpt)
                return excerpt.strip()
        return None

    def get_permalink(self):
        return self.url


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
        cite_html, resp = get_HTML(citelink)
        day, month, year = re.search('''<li> Date of last revision: (\d{1,2}) (\w+) (\d\d\d\d)''', cite_html).groups()
        month = fe.MONTH2DIGIT[month[0:3].lower()]
        return '%d%02d%02d' %(int(year), int(month), int(day))

    def get_org(self):
        return 'Wikimedia'

    def get_excerpt(self):
        return None            # no good way to identify first paragraph at Meta

    def get_permalink(self):
        permalink = self.url.split('/wiki/')[0] + re.search('''<li id="t-permalink"><a href="(.*?)"''', self.html).group(1)
        return unescape_XML(permalink)


class scrape_MARC(scrape_default):
    def __init__(self, url, comment):
        print("Scraping MARC;"),
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        try:
            author = re.search('''From: *<a href=".*?">(.*?)</a>''', self.html)
        except AttributeError:
            author = re.search('''From: *(.*)''', self.html)
        author = author.group(1)
        author = author.replace(' () ','@').replace(' ! ','.')\
            .replace('&lt;', '<').replace('&gt;', '>')
        author = author.split(' <')[0]
        author = author.replace('"','')
        return author

    def get_title(self):
        subject = re.search('''Subject: *(.*)''', self.html).group(1)
        if subject.startswith('<a href'):
            subject = re.search('''<a href=".*?">(.*?)</a>''',subject).group(1)
        subject = subject.replace('[Wikipedia-l] ', '').replace('[WikiEN-l] ', '')
        return subject

    def get_date(self):
        mdate = re.search('''Date: *<a href=".*?">(.*?)</a>''', self.html).group(1)
        try:
            date = time.strptime(mdate, "%Y%m%d %I:%M:%S")
        except ValueError:
            date = time.strptime(mdate, "%Y%m%d %H:%M:%S")
        return time.strftime('%Y%m%d', date)

    def get_org(self):
        return re.search('''List: *<a href=".*?">(.*?)</a>''', self.html).group(1)

    def get_excerpt(self):
        excerpt = ''
        msg_body = '\n'.join(self.html.splitlines()[13:-17])
        msg_paras = msg_body.split('\n\n')
        for para in msg_paras:
            if para.count('\n') > 2:
                if not para.count('&gt;') >1:
                    excerpt = para.replace('\n',' ')
                    break
        return excerpt.strip()

    def get_permalink(self):
        return self.url

#######################################
# Output loggers

def log2mm(biblio):
    '''
    Log to bibliographic mindmap, see:
        http://reagle.org/joseph/2009/01/thunderdell.html
    '''

    print("to log2mm")
    biblio = do_console_annotation(biblio)
    
    #now = time.gmtime()
    this_week = time.strftime("%U", NOW)
    this_year = time.strftime('%Y', NOW)
    date_read = time.strftime("%Y%m%d %H:%M UTC", NOW)
    
    ofile = HOME+'/data/2web/reagle.org/joseph/2005/ethno/field-notes.mm'
    info("biblio = %s" %biblio)
    author = biblio['author']
    title = biblio['title']
    keyword, sep, abstract = biblio['comment'].partition(' ')
    excerpt = biblio['excerpt']
    permalink = biblio['permalink']

    # Create citation
    for token in ['author', 'title', 'url', 'permalink', 'type']:
        if token in biblio: # not needed in citation
            del biblio[token] 
    citation = ''
    for key, value in biblio.items():
        if key in fe.BIBLATEX_FIELDS:
            info("key = %s value = %s" %(key, value))
            citation += '%s=%s ' % (fe.BIBLATEX_FIELDS[key], value)
    citation += 'r=%s ' % date_read
    if keyword:
        keyword = KEY_SHORTCUTS.get(keyword, keyword)
        citation += 'kw=' + keyword
    try:
        from xml.etree.cElementTree import parse # fast C implementation
    except ImportError:
        from xml.etree.ElementTree import parse
    from xml.etree.ElementTree import ElementTree, Element, SubElement

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
            print("found week %s" % this_week)
            break
    else:
        print("creating %d" % this_week)
        week_node = SubElement(year_node, 'node', {'TEXT': this_week, 'POSITION': 'right'})

    author_node = SubElement(week_node, 'node', {'TEXT': author, 'COLOR': '#338800'})
    title_node = SubElement(author_node, 'node', {'TEXT': title, 'COLOR': '#090f6b',
        'LINK': permalink})
    cite_node = SubElement(title_node, 'node', {'TEXT': citation, 'COLOR': '#ff33b8'})
    if abstract:
        abstract_node = SubElement(title_node, 'node', {'TEXT': abstract, 'COLOR': '#999999'})
    if excerpt:
        excerpt_node = SubElement(title_node, 'node', {'TEXT': excerpt, 'COLOR': '#166799'})

    ElementTree(mindmap).write(ofile, encoding='utf-8')


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
    ofile = HOME+'/data/2web/reagle.org/joseph/plan/plans/index.html'

    title = biblio['title']
    tag, sep, comment = biblio['comment'].partition(' ')
    url = biblio['url']

    # Replace the line with the '^' character with a hypertext link
    html_comment = re.sub('(.*)\^(.*)',u'\\1<a href="%s">%s</a>\\2' %
        (escape_XML(url), title), comment)

    date_token = time.strftime("%y%m%d", NOW)
    digest = hashlib.md5(html_comment.encode('utf-8', 'replace')).hexdigest()
    uid = "e" + date_token + "-" + digest[:4]
    log_item = '<li class="event" id="%s">%s: %s] %s</li>' % \
        (uid, date_token, tag, html_comment)

    fd = codecs.open(ofile, 'r', 'utf-8', 'replace')
    content = fd.read()
    fd.close()

    insertion_regexp = re.compile('(<h2>Done Work</h2>\s*<ol>)')

    newcontent = insertion_regexp.sub(u'\\1 \n  %s' %
        log_item, content, re.DOTALL|re.IGNORECASE)
    if newcontent:
        fd = codecs.open(ofile, 'w', 'utf-8', 'replace')
        fd.write(newcontent)
        fd.close()
    else:
        print_usage("Sorry, output regexp subsitution failed.")

    if args.publish:
        yasn_publish(title, comment.replace('^', url), tag)


def log2console(biblio):
    '''
    Log to console.
    '''

    keyword, sep, abstract = biblio['comment'].partition(' ')
    del biblio['comment']
    if keyword:
        biblio['keyword'] = KEY_SHORTCUTS.get(keyword, keyword)
    
    print('\n')
    print("author = %s" % biblio['author']),
    print("title = %s" % biblio['title']),
    print("date = %s" % biblio['date']),
    SKIP_TOKENS = ('author', 'title', 'date', 'permalink', 'type', 'excerpt') 
    for key,value in biblio.items():
        if key not in SKIP_TOKENS:
            print("%s = %s" % (key, value.strip())),
    print('\n')
    print(biblio['excerpt']),
    print('\n')

def blog_at_opencodex(biblio):
    '''
    Start at a blog entry at opencodex
    '''

    CODEX_ROOT = '/home/reagle/data/2web/reagle.org/joseph/content/'
    keyword, sep, entry = biblio['comment'].partition(' ')
    blog_title, sep, blog_body = entry.partition('.')

    category = 'social'
    if keyword:
        category = KEY_SHORTCUTS.get(keyword, keyword)
    
    filename = blog_title.lower() \
        .replace(' ', '-') \
        .replace( "'", '')
    filename = CODEX_ROOT + '%s/' % category + filename + '.md'
    if exists(filename):
        print("\nfilename '%s' already exists'" % filename)
        sys.exit()
    fd = codecs.open(filename, 'w', 'utf-8', 'replace')
    fd.write('Title: %s\n' % blog_title)
    fd.write('Date: %s\n' % time.strftime("%Y-%m-%d", NOW))
    fd.write('Tags: \n')
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
    
    GOATEE_ROOT = '/home/reagle/data/2web/goatee.net/content/'
    blog_title, sep, blog_body = biblio['comment'].partition('. ')

    this_year, this_month = time.strftime("%Y %m", NOW).split()
    url = biblio.get('url', None)
    filename = blog_title.lower()
        
    PHOTO_RE = re.compile('.*/photo/web/(\d\d\d\d/\d\d)' \
                '/\d\d-\d\d\d\d-(.*)\.jpe?g')
    photo_match = False
    if 'goatee.net/photo/' in url:
        photo_match = re.match(PHOTO_RE, url)
        if photo_match:
            blog_date = re.match(PHOTO_RE, url).group(1).replace('/', '-')
            blog_title = re.match(PHOTO_RE, url).group(2)
            filename = blog_date + '-' + blog_title
            blog_title = blog_title.replace('-', ' ')
    filename = filename.replace(' ', '-').replace("'", '') 
    filename = GOATEE_ROOT + '%s/%s-%s.md' % (this_year, this_month, filename)
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
            thumb_url = url.replace('/web/', '/thumbs/')
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
        url = 'http://dx.doi.org/' + url[4:]
    
    dispatch_scraper = (
        ('file://%s/tmp/nupedia-l/' %HOME, scrape_NupediaL),
        ('http://lists.wikimedia.org/pipermail/', scrape_WM_lists),
        ('http://en.wikipedia.org/wiki/Wikipedia:Wikipedia_Signpost/', scrape_Signpost),
        ('http://en.wikipedia.org/w', scrape_ENWP),
        ('http://meta.wikimedia.org/w', scrape_WMMeta),
        ('http://marc.info/', scrape_MARC),
        ('http://dx.doi.org/', scrape_DOI),
        ('http://photo.net/site-help-forum/', scrape_photo_net),
        ('', scrape_default)     # default: make sure last
    )

    for prefix, scraper in dispatch_scraper:
        if url.startswith(prefix):
            info("scrape = %s " % scraper)
            return scraper(url, comment)    # creates instance


def get_logger(options={re.IGNORECASE}):
    """
    Matches the option string to grammar and output.
    """
    params = None
    dispatch_logger = (
        # nifty: b URL n DESCRIPTION
        (r'(?P<url>(\.|http)\S* )?(?P<scheme>n) (?P<comment>.*)',
            log2nifty),
        # work: b URL j KEYWORD MESSAGE [with ^ replaced by url]
        (r'(?P<url>(\.|http)\S* )?(?P<scheme>j) (?P<comment>.*)',
            log2work),
        # mindmap: b URL m KEYWORD. ABSTRACT
        (r'(?P<url>(\.|doi|http)\S* )?(?P<scheme>m) ?(?P<comment>.*)',
            log2mm),
        (r'(?P<url>(\.|doi|http)\S* )?(?P<scheme>c) ?(?P<comment>.*)',
            log2console),
        (r'(?P<url>(\.|doi|http)\S* )?(?P<scheme>o) ?(?P<comment>.*)',
            blog_at_opencodex),
        (r'(?P<url>(\.|doi|http)\S* )?(?P<scheme>g) ?(?P<comment>.*)',
            blog_at_goatee),
    )

    for regexp, logger in dispatch_logger:
        if re.match(regexp, options):
            function = logger
            params = re.match(regexp, options, re.DOTALL|re.IGNORECASE).groupdict()
            break
    if params:
        return function, params
    else:
        print_usage("Sorry, your scheme parameters were not correct.")
        print(params)
    sys.exit()

#######################################
# Miscellaneous
    
def print_usage(message):
    print(message)
    print("Usage: b [url]? scheme [scheme parameters]? comment")

def do_console_annotation(biblio):
    '''Augment biblio with console annotations'''

    tenative_ident = fe.get_ident(
        { 'author' : fe.parse_names(biblio['author']), 
        'title' : biblio['title'],
        'year' : biblio['date'][0:4]}, {})
    print('%s; annotate?' % tenative_ident)
    
    console_annotations = ''
    while True:
        line = raw_input('').decode(sys.stdin.encoding)
        if not line: break
        if re.search('a\w* ?= ?', line):
            biblio['author']=line.split('=', 1)[1].strip()
        else:
            console_annotations += '\n\n' + line
    biblio['excerpt'] += console_annotations
    
    return biblio
        
def yasn_publish(title, comment, tag):
    title_room = 134 - len(comment) - len(tag)
    info("%d < %d" %(len(title), title_room))
    if len(title) > title_room:
        title = title[0:title_room] + '...'
    message = "%s %s #%s" %(title, comment, tag)
    info(len(message))
    print("twitter set '%s'" %message)

#Check to see if the script is executing as main.
if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        prog='b', usage='%(prog)s [options] [URL] logger [keyword] [text]')
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
    comment = params['comment'].strip()
    #print ("logger = '%s', params = '%s', comment = '%s'" %(logger, params, comment))
    if params['url']:    # not all log2work entries have urls
        scraper = get_scraper(params['url'].strip(), comment)
        biblio = scraper.get_biblio()
    else:
        biblio = {'title' : '', 'url': '', 'comment' : comment}
    logger(biblio)

    #if args.publish:
        #yasn_publish(biblio)
        