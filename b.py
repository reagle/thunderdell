#!/usr/bin/env python3.7
# -*- coding: utf-8 -*-
#
# This file is part of Thunderdell/BusySponge
# <http://reagle.org/joseph/2009/01/thunderdell>
# (c) Copyright 2009-2017 by Joseph Reagle
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
# get reddit timestamp from API (no scraping possible?)

import argparse
from argparse import RawTextHelpFormatter
from collections import Counter
from datetime import datetime
from dateutil.parser import parse
import fe
from io import StringIO, BytesIO
import logging
from lxml import etree
import os
import re
import string
from subprocess import call, Popen
import sys
import time

# personal Web utility module
from web_little import get_HTML, get_text, unescape_XML, escape_XML
from change_case import sentence_case, title_case

log_level = 100  # default
critical = logging.critical
info = logging.info
dbg = logging.debug

EDITOR = os.environ.get('EDITOR', 'nano')
VISUAL = os.environ.get('VISUAL', 'nano')
HOME = os.path.expanduser("~")
TMP_DIR = HOME + '/tmp/.fe/'
if not os.path.isdir(TMP_DIR):
    os.makedirs(TMP_DIR)

# Expansions for common tags/activities

GENERAL_KEY_SHORTCUTS = {
    'add': 'addiction',
    'exi': 'exit',
    'for': 'fork',
    'hum': 'humor',
    'ide': 'identity',
    'lea': 'leadership',
    'leg': 'legal',
    'lit': 'literacy',
    'ope': 'open',
    'nor': 'norms',
    'pat': 'patience',
    'pyt': 'python',
    'pow': 'power',
    'pra': 'praxis',
    'pri': 'privacy',
    'ske': 'skepticism',
    'spe': 'speech',
    'str': 'structure',
    'tea': 'teaching',
    'tec': 'technology',
    'tro': 'troll',
    'zei': 'zeitgeist',
}

TV_KEY_SHORTCUTS = {
    # Tech Prediction, Vision, and Utopia
    'nai': 'naive',
    'pre': 'prediction',
    'uni': 'universal',
    'uto': 'utopia',
    'vis': 'vision',
}

GF_KEY_SHORTCUTS = {
    # Geek Feminism
    'fem': 'feminism',
    'gen': 'gender',
    'gf': 'gfem',
    'sex': 'sexism',
    'mer': 'meritocracy',
    'prv': 'privilege',
}

LH_KEY_SHORTCUTS = {
    # Lifehack
    'com': 'complicity',
    'lh': 'lifehack',
    'his': 'history',
    'qs': 'quantifiedself',
    'sh': 'selfhelp',
    'too': 'tool',
    'mea': 'meaning',
    'min': 'minimalism',
}

RTC_KEY_SHORTCUTS = {
    # Comments
    'ano': 'anonymous',
    'ass': 'assessment',
    'aut': 'automated',
    'cri': 'criticism',
    'est': 'esteem',
    'fak': 'fake',
    'fee': 'feedback',
    'inf': 'informed',
    'man': 'manipulation',
    'mar': 'market',
    'off': 'offensive',
    'qua': 'quant',
    'ran': 'ranking',
    'rat': 'rating',
    'rev': 'review',
    'sel': 'self',
    'soc': 'social',
    'pup': 'puppet',
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
    'sil': 'siliconvalley',
    'ver': 'verifiability',
    'wp':  'wikipedia',
}

LIST_OF_KEYSHORTCUTS = (
    GENERAL_KEY_SHORTCUTS, GF_KEY_SHORTCUTS, RTC_KEY_SHORTCUTS,
    WP_KEY_SHORTCUTS, LH_KEY_SHORTCUTS, TV_KEY_SHORTCUTS)

KEY_SHORTCUTS = LIST_OF_KEYSHORTCUTS[0].copy()
for short_dict in LIST_OF_KEYSHORTCUTS[1:]:
    KEY_SHORTCUTS.update(short_dict)

MONTHS = 'jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec'

SITE_CONTAINER_MAP = (
    ('arstechnica.com', 'Ars Technica', 'c_newspaper'),
    ('atlantic.com', 'The Atlantic', 'c_magazine'),
    ('boingboing.net', 'Boing Boing', 'c_blog'),
    ('dailydot', 'The Daily Dot', 'c_newspaper'),
    ('engadget.com', 'Engadget', 'c_blog'),
    ('forbes.com', 'Forbes', 'c_magazine'),
    ('huffingtonpost', 'Huffington Post', 'c_newspaper'),
    ('lifehacker.com', 'Lifehacker', 'c_newspaper'),
    ('medium.com', 'Medium', 'c_blog'),
    ('newyorker.com', 'New Yorker', 'c_magazine'),
    ('nytimes.com', 'The New York Times', 'c_newspaper'),
    ('salon.com', 'Salon', 'c_magazine'),
    ('slate.com', 'Slate', 'c_magazine'),
    ('techcrunch.com', 'TechCrunch', 'c_newspaper'),
    ('theguardian', 'The Guardian', 'c_newspaper'),
    ('verge.com', 'The Verge', 'c_newspaper'),
    ('Wikipedia_Signpost', 'Wikipedia Signpost', 'c_web'),
    ('wired.com', 'Wired', 'c_magazine'),
    ('wsj.com', 'The Wall Street Journal', 'c_newspaper'),
    ('washingtonpost.com', 'The Washington Post', 'c_newspaper'),
    ('fourhourworkweek.com', '4-Hour Workweek', 'c_blog'),
    # ('', '',  'c_magazine'),
)

#######################################
# Utility functions

NOW = time.localtime()

def smart_punctuation_to_ascii(s):
    '''Convert unicode punctuation (i.e., "smart quotes") to simpler form.'''
    info(f"old {type(s)} s = '{s}'")
    punctuation = {
        0x2018: "'",    # apostrophe
        0x2019: "'",
        0x201C: '"',    # quotation
        0x201D: '"'}
    if s:
        s = s.translate(punctuation)
        s = s.replace("—", "--")
        info(f"new {type(s)} s = '{s}'")
    return s


#######################################
# Screen scrapers


class scrape_default(object):
    """
    Default and base class scraper.
    """
    def __init__(self, url, comment):
        print(("Scraping default Web page;"), end='\n')
        self.url = url
        self.comment = comment
        try:
            self.html_b, self.HTML_p, self.html_u, self.resp = get_HTML(
                url, cache_control='no-cache')
        except IOError:
            self.html_b, self.HTML_p, self.html_u, self.resp = (
                None, None, None, None)

        self.text = None
        if self.html_b:
            self.text = get_text(url)

    def get_biblio(self):
        biblio = {
            'author': self.get_author(),
            'date': self.get_date(),
            'permalink': self.get_permalink(),
            'excerpt': self.get_excerpt(),
            'comment': self.comment,
            'url': self.url,
        }
        biblio['title'], biblio['c_web'] = self.split_title_org()
        for site, container, container_type in SITE_CONTAINER_MAP:
            if site in biblio['url']:
                info(f"container = {container}")
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
            '''//meta[@name='sailthru.author']/@content''',
            '''//a[@rel='author']//text()''',
            '''//span[@class='author']/text()''',   # WashingtonPost
            '''//*[@itemprop='author']//text()''',  # engadget
            '''//*[contains(@class,'contributor')]/text()''',
            '''//span[@class='name']/text()''',
            # tynan w/ bogus space
            '''(//span[@class='dynamic-display_name-user-1 '])[1]/text()''',
            # amazon
            '''//a[contains(@href, 'cm_cr_hreview_mr')]/text()''',
            # first of many
            '''//*[1][contains(@class, 'byline')][1]//text()''',
        )
        if self.HTML_p is not None:
            info('checking author xpaths')
            for path in AUTHOR_XPATHS:
                info(f"trying = '{path}'")
                xpath_result = self.HTML_p.xpath(path)
                if xpath_result:
                    info(f"xpath_result = '{xpath_result}'; xpath = '{path}'")
                    # 20171204 added space to join below
                    author = string.capwords(' '.join(xpath_result).strip())
                    if author.lower().startswith('by '):
                        author = author[3:]
                    info(f"author = '{author}'; xpath = '{path}'")
                    if author != '':
                        return author
                    else:
                        continue

        if self.text:
            AUTHOR_REGEXS = (
                r"by ([a-z ]*?)(?:-|, |/ | at | on | posted ).{,35}?\d\d\d\d",
                r"^\W*(?:posted )?by[:]? (.*)",
                r"\d\d\d\d.{,6}? by ([a-z ]*)",
                r"\s{3,}by[:]? (.*)",
            )
            # info(self.text)
            info('checking regexs')
            for regex in AUTHOR_REGEXS:
                info(f"trying = '{regex}'")
                dmatch = re.search(regex, self.text,
                                   re.IGNORECASE | re.MULTILINE)
                if dmatch:
                    info(f'matched: "{regex}"')
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
                        info(f"length {len(author)} is <4 or > {MAX_MATCH}")
                else:
                    info(f'failed: "{regex}"')

        return 'UNKNOWN'

    def get_date(self):
        '''rough match of a date, then pass to dateutil's magic abilities'''

        from dateutil.parser import parse

        DATE_XPATHS = ('''//li/span[@class="byline_label"]'''
                       '''/following-sibling::span/@title''',)  # tynan.com
        if self.HTML_p is not None:
            info('checking date xpaths')
            for path in DATE_XPATHS:
                info(f"trying = '{path}'")
                xpath_result = self.HTML_p.xpath(path)
                if xpath_result:
                    info(f"xpath_result = '{xpath_result}'; xpath = '{path}'")
                    date = parse(xpath_result[0]).strftime("%Y%m%d")
                    info(f"date = '{date}'; xpath = '{path}'")
                    if date != '':
                        return date
                    else:
                        continue

        date_regexp = r"(\d+,? )?(%s)\w*(,? \d+)?(,? \d+)" % MONTHS
        try:
            dmatch = re.search(date_regexp, self.text, re.IGNORECASE)
            return parse(dmatch.group(0)).strftime("%Y%m%d")
        except (AttributeError, TypeError, ValueError):
            NOW = time.gmtime()
            date = time.strftime('%Y%m%d', NOW)
            info(f"making date NOW = {date}")
            return date

    def get_title(self):

        title_regexps = (
            ('http://lists.w3.org/.*', '<!-- subject="(.*?)" -->'),
            ('http://lists.kde.org/.*', r"<title>MARC: msg '(.*?)'</title>"),
            ('https://www.youtube.com', r'''"title":"(.*?)"'''),
            ('', r'<title[^>]*>([^<]+)</title>')    # default: make sure last
        )

        for prefix, regexp in title_regexps:
            if self.url.startswith(prefix):
                info(f"prefix = {prefix}")
                break

        title = "UNKNOWN TITLE"
        if self.html_u:
            tmatch = re.search(regexp, self.html_u, re.DOTALL | re.IGNORECASE)
            if tmatch:
                title = tmatch.group(1).strip()
                title = unescape_XML(title)
                title = sentence_case(title)
                title = smart_punctuation_to_ascii(title)
        return title

    def split_title_org(self):
        '''Separate the title by a delimiter and test if latter half is the
        organization (if it has certain words (blog) or is too short)'''

        ORG_WORDS = ['blog', 'lab', 'center']

        title = title_ori = self.get_title()
        info(f"title_ori = '{title_ori}'")
        org = org_ori = self.get_org()
        info(f"org_ori = '{org_ori}'")
        STRONG_DELIMTERS = re.compile(r'\s[\|—«»]\s')
        WEAK_DELIMITERS = re.compile(r'[:;-]\s')
        if STRONG_DELIMTERS.search(title_ori):
            info("STRONG_DELIMTERS")
            parts = STRONG_DELIMTERS.split(title_ori)
        else:
            info("WEAK_DELIMITERS")
            parts = WEAK_DELIMITERS.split(title_ori)
        info(f"parts = '{parts}'")
        if len(parts) >= 2:
            beginning, end = ' : '.join(parts[0:-1]), parts[-1]
            title, org = beginning, end
            title_c14n = title.replace(' ', '').lower()
            org_c14n = org.replace(' ', '').lower()
            if org_ori.lower() in org_c14n.lower():
                info("org_ori.lower() in org_c14n.lower(): pass")
                title, org = ' '.join(parts[0:-1]), parts[-1]
            elif org_ori.lower() in title_c14n:
                info("org_ori.lower() in title_c14n: switch")
                title, org = parts[-1], ' '.join(parts[0:-1])
            else:
                info(f"beginning = {beginning}, end = {end}")
                end_ratio = float(len(end)) / len(beginning + end)
                info(" end_ratio: %d / %d = %.2f" % (
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

    def get_org(self):
        from urllib.parse import urlparse

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
                line = ' '.join(line.split())  # removes redundant space
                if len(line) >= 250:
                    line = smart_punctuation_to_ascii(line)
                    info(f"line = '{line}'")
                    info(f"length = {len(line)}; 2nd_char = '{line[1]}'")
                    if line[1].isalpha():
                        excerpt = line
                        return excerpt.strip()
        return ''

    def get_permalink(self):
        return self.url


class scrape_ISBN(scrape_default):

    def __init__(self, url, comment):
        print(("Scraping ISBN;"), end='\n')
        self.url = url
        self.comment = comment

    def get_biblio(self):

        import book_query
        info(f"url = {self.url}")
        json_bib = book_query.query(self.url)
        info(f"json_bib = '{json_bib}'")
        biblio = {
            'permalink': self.url,
            'excerpt': '',
            'comment': self.comment,
        }
        info("### json_bib.items()")
        for key, value in list(json_bib.items()):
            info(f"key = '{key}'")
            if key.startswith('subject'):
                continue
            info("key = '%s' value = '%s' type(value) = '%s'\n" % (
                key, value, type(value)))
            if value in (None, [], ''):
                pass
            elif key == 'author':
                biblio['author'] = self.get_author(json_bib)
            elif key == 'year':
                biblio['date'] = json_bib['year']
            elif key == 'isbn':
                biblio['isbn'] = json_bib['isbn']
            elif key == 'pageCount':
                biblio['pages'] = json_bib['pageCount']
            elif key == 'publisher':
                biblio['publisher'] = json_bib['publisher']
            elif key == 'city':
                biblio['address'] = json_bib['city']
            elif key == 'url':
                biblio['url'] = json_bib['url']
                biblio['permalink'] = json_bib['url']
            else:
                biblio[key] = json_bib[key]
        if 'title' in json_bib:
            title = biblio['title'].replace(': ', ': ')
            biblio['title'] = sentence_case(title)
            if 'subtitle' in json_bib:
                biblio['subtitle'] = sentence_case(json_bib['subtitle'])
        else:
            biblio['title'] = 'UNKNOWN'
        return biblio

    def get_author(self, bib_dict):
        names = 'UNKNOWN'
        if 'author' in bib_dict:
            info("bib_dict['author'] = '%s'" % bib_dict['author'])
            names = bib_dict['author']
        return names

    def get_date(self, bib_dict):
        # "issued":{"date-parts":[[2007,3]]}
        date_parts = bib_dict['issued']['date-parts'][0]
        info(f"date_parts = {date_parts}")
        if len(date_parts) == 3:
            year, month, day = date_parts
            date = '%d%02d%02' % (int(year), int(month), int(day))
        elif len(date_parts) == 2:
            year, month = date_parts
            date = '%d%02d' % (int(year), int(month))
        elif len(date_parts) == 1:
            date = str(date_parts[0])
        else:
            date = '0000'
        info(f"date = {date}")
        return date


class scrape_DOI(scrape_default):

    def __init__(self, url, comment):
        print(("Scraping DOI;"), end='\n')
        self.url = url
        self.comment = comment

    def get_biblio(self):

        import doi_query
        info(f"url = {self.url}")
        json_bib = doi_query.query(self.url)
        biblio = {
            'permalink': self.url,
            'excerpt': '',
            'comment': self.comment,
        }
        for key, value in list(json_bib.items()):
            info(f"key = '{key}' value = '{value}' type(value) = '{type(value)}'")
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
                biblio['permalink'] = biblio['url'] = json_bib['URL']
            else:
                biblio[key] = json_bib[key]
        if 'title' not in json_bib:
            biblio['title'] = 'UNKNOWN'
        else:
            biblio['title'] = sentence_case(' '.join(
                biblio['title'].split()))
        info(f"biblio = {biblio}")
        return biblio

    def get_author(self, bib_dict):
        names = 'UNKNOWN'
        if 'author' in bib_dict:
            names = ''
            for name_dic in bib_dict['author']:
                info(f"name_dic = '{name_dic}'")
                joined_name = f"{name_dic['given']} {name_dic['family']}"
                info(f"joined_name = '{joined_name}'")
                names = names + ', ' + joined_name
            names = names[2:]  # remove first comma
        return names

    def get_date(self, bib_dict):
        # "issued":{"date-parts":[[2007,3]]}
        date_parts = bib_dict['issued']['date-parts'][0]
        info(f"date_parts = {date_parts}")
        if len(date_parts) == 3:
            year, month, day = date_parts
            date = '%d%02d%02d' % (int(year), int(month), int(day))
        elif len(date_parts) == 2:
            year, month = date_parts
            date = '%d%02d' % (int(year), int(month))
        elif len(date_parts) == 1:
            date = str(date_parts[0])
        else:
            date = '0000'
        info(f"date = {date}")
        return date


class scrape_MARC(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping MARC;"), end='\n')
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        try:
            author = re.search(
                '''From: *<a href=".*?">(.*?)</a>''', self.html_u)
        except AttributeError:
            author = re.search('''From: *(.*)''', self.html_u)
        author = author.group(1)
        author = author.replace(' () ', '@').replace(' ! ', '.')\
            .replace('&lt;', '<').replace('&gt;', '>')
        author = author.split(' <')[0]
        author = author.replace('"', '')
        return author

    def get_title(self):
        subject = re.search('''Subject: *(.*)''', self.html_u).group(1)
        if subject.startswith('<a href'):
            subject = re.search(
                '''<a href=".*?">(.*?)</a>''', subject).group(1)
        subject = subject.replace(
            '[Wikipedia-l] ', '').replace('[WikiEN-l] ', '')
        return subject

    def get_date(self):
        mdate = re.search(
            '''Date: *<a href=".*?">(.*?)</a>''', self.html_u).group(1)
        try:
            date = time.strptime(mdate, "%Y-%m-%d %I:%M:%S")
        except ValueError:
            date = time.strptime(mdate, "%Y-%m-%d %H:%M:%S")
        return time.strftime('%Y%m%d', date)

    def get_org(self):
        return re.search(
            '''List: *<a href=".*?">(.*?)</a>''', self.html_u).group(1)

    def get_excerpt(self):
        excerpt = ''
        msg_body = '\n'.join(self.html_u.splitlines()[13:-17])
        msg_paras = msg_body.split('\n\n')
        for para in msg_paras:
            if para.count('\n') > 2:
                if not para.count('&gt;') > 1:
                    excerpt = para.replace('\n', ' ')
                    break
        return excerpt.strip()

    def get_permalink(self):
        return self.url


class scrape_ENWP(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping en.Wikipedia;"), end='\n')
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        return 'Wikipedia'

    def split_title_org(self):
        return self.get_title(), self.get_org()

    def get_title(self):
        title = scrape_default.get_title(self)    # use super()?
        info(f"title = '{title}'")
        return title.replace(' - Wikipedia', '')

    def get_permalink(self):
        if "oldid" not in self.url:
            permalink = self.url.split('/wiki/')[0] + re.search(
                '''<li id="t-permalink"><a href="(.*?)"''',
                self.html_u).group(1)
            return unescape_XML(permalink)
        else:
            return self.url

    def get_date(self):
        '''find date within span'''
        _, _, versioned_HTML_u, resp = get_HTML(self.get_permalink())
        time, day, month, year = re.search(
            r'''<span id="mw-revision-date">(.*?), (\d{1,2}) (\w+) '''
            r'''(\d\d\d\d)</span>''',
            versioned_HTML_u).groups()
        month = fe.MONTH2DIGIT[month[0:3].lower()]
        return '%d%02d%02d' % (int(year), int(month), int(day))

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
        print(("Scraping Wikimedia Meta;"), end='\n')
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        return 'Wikimedia'

    def get_title(self):
        title = scrape_default.get_title(self)    # super()?
        return title.replace(' - Meta', '')

    def get_date(self):  # Meta is often foobar because of proxy bugs
        _, _, cite_HTML_u, resp = get_HTML(self.get_permalink())
        # in browser, id="lastmod", but python gets id="footer-info-lastmod"
        day, month, year = re.search(
            r'''<li id="footer-info-lastmod"> This page was last edited on (\d{1,2}) (\w+) (\d\d\d\d)''',
            cite_HTML_u).groups()
        month = fe.MONTH2DIGIT[month[0:3].lower()]
        return '%d%02d%02d' % (int(year), int(month), int(day))

    def get_org(self):
        return 'Wikimedia'

    def get_excerpt(self):
        return ''            # no good way to identify first paragraph at Meta

    def get_permalink(self):
        permalink = self.url.split('/wiki/')[0] + re.search(
            '''<li id="t-permalink"><a href="(.*?)"''', self.html_u).group(1)
        return unescape_XML(permalink)


class scrape_geekfeminism_wiki(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping geekfeminism wiki"), end='\n')
        scrape_default.__init__(self, url, comment)

    def get_biblio(self):
        biblio = {
            'author': 'Geek Feminism',
            'date': self.get_date(),
            'permalink': self.get_permalink(),
            'excerpt': self.get_excerpt(),
            'comment': self.comment,
            'url': self.url,
        }
        biblio['title'], biblio['organization'] = self.split_title_org()
        biblio['organization'] = 'Wikia'
        return biblio


class scrape_twitter(scrape_default):
    def __init__(self, url, comment):
        print(("Scraping twitter"), end='\n')
        scrape_default.__init__(self, url, comment)

    def get_biblio(self):
        biblio = {
            'author': self.get_author(),
            'title': self.get_title(),
            'date': self.get_date(),
            'permalink': self.get_permalink(),
            'excerpt': self.get_excerpt(),
            'comment': self.comment,
            'url': self.url,
            'organization': 'Twitter',
        }
        return biblio

    def get_author(self):

        author = self.HTML_p.xpath(
            "//div[@data-user-id]/@data-name")[0]
        return author.strip()

    def get_title(self):

        authororg_title = self.HTML_p.xpath("//title/text()")[0]
        info(f"authororg_title = {authororg_title}")
        author_org, title = authororg_title.split(':', 1)
        # author_org, title = authororg_title.split('|', 1)
        # author = author_org.split('/', 1)[1]
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
    info(f'{biblio}')

    # now = time.gmtime()
    this_week = time.strftime("%U", NOW)
    this_year = time.strftime('%Y', NOW)
    date_read = time.strftime("%Y%m%d %H:%M UTC", NOW)

    ofile = HOME + '/data/2web/reagle.org/joseph/2005/ethno/field-notes.mm'
    info(f"biblio = {biblio}")
    author = biblio['author']
    title = biblio['title']
    subtitle = biblio['subtitle'] if 'subtitle' in biblio else ''
    abstract = biblio['comment']
    excerpt = biblio['excerpt']
    permalink = biblio['permalink']

    # Create citation
    for token in ['author', 'title', 'url', 'permalink', 'type']:
        if token in biblio:  # not needed in citation
            del biblio[token]
    citation = ''
    for key, value in list(biblio.items()):
        if key in fe.BIB_FIELDS:
            info(f"key = {key} value = {value}")
            citation += f"{fe.BIB_FIELDS[key]}={value} "
    citation += f" r={date_read} "
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
        print(f"creating {year}")
        year_node = SubElement(
            mm_years, 'node',
            {'TEXT': this_year, 'POSITION': 'right'})
        week_node = SubElement(
            year_node, 'node',
            {'TEXT': this_week, 'POSITION': 'right'})

    for week_node in year_node:
        if week_node.get('TEXT') == this_week:
            print(f"week {this_week}")
            break
    else:
        print(f"creating {this_week}")
        week_node = SubElement(
            year_node, 'node',
            {'TEXT': this_week, 'POSITION': 'right'})

    author_node = SubElement(
        week_node, 'node',
        {'TEXT': author, 'STYLE_REF': 'author'})
    title_node = SubElement(
        author_node, 'node',
        {'TEXT': title, 'STYLE_REF': 'title', 'LINK': permalink})
    cite_node = SubElement(
        title_node, 'node',
        {'TEXT': citation, 'STYLE_REF': 'cite'})
    if abstract:
        abstract_node = SubElement(
            title_node, 'node',
            {'TEXT': abstract, 'STYLE_REF': 'annotation'})
    if excerpt:
        for exc in excerpt.split('\n\n'):
            info(f"exc = {exc}")
            if exc.startswith(', '):
                style_ref = 'paraphrase'
                exc = exc[2:]
            elif exc.startswith('. '):
                style_ref = 'annotation'
                exc = exc[2:]
            elif exc.startswith('-- '):
                style_ref = 'default'
                exc = exc[3:]
            else:
                style_ref = 'quote'
            excerpt_node = SubElement(title_node, 'node', {'TEXT': exc,
                                      'STYLE_REF': style_ref})

    ElementTree(mindmap).write(ofile, encoding='utf-8')

    if args.publish:
        yasn_publish(abstract, title, subtitle, permalink, tags)


def log2nifty(biblio):
    '''
    Log to personal blog.
    '''

    print("to log2nifty\n")
    ofile = HOME + '/data/2web/goatee.net/nifty-stuff.html'

    title = biblio['title']
    comment = biblio['comment']
    url = biblio['url']

    date_token = time.strftime("%y%m%d", NOW)
    log_item = (
        f'<dt><a href="{url}">{title}</a> '
        '({date_token})</dt><dd>{comment}</dd>')

    fd = open(ofile)
    content = fd.read()
    fd.close()

    insertion_regexp = re.compile('(<dl style="clear: left;">)')
    newcontent = insertion_regexp.sub(
        '\\1 \n  %s' % log_item, content, re.DOTALL | re.IGNORECASE)
    if newcontent:
        fd = open(ofile, 'w', encoding='utf-8', errors='replace')
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
    info(f"biblio = '{biblio}'")
    ofile = HOME + '/data/2web/reagle.org/joseph/plan/plans/index.html'
    info(f"ofile = {ofile}")
    subtitle = biblio['subtitle'].strip() if 'subtitle' in biblio else ''
    title = biblio['title'].strip() + subtitle
    url = biblio['url'].strip()
    comment = biblio['comment'].strip() if biblio['comment'] else ''
    if biblio['tags']:
        hashtags = ''
        for tag in biblio['tags'].strip().split(' '):
            hashtags += '#%s ' % KEY_SHORTCUTS.get(tag, tag)
        hashtags = hashtags.strip()
    else:
        hashtags = '#misc'
    info(f"hashtags = '{hashtags}'")
    html_comment = comment + ' ' + '<a href="%s">%s</a>' % (escape_XML(url),
                                                            escape_XML(title))

    date_token = time.strftime("%y%m%d", NOW)
    digest = hashlib.md5(html_comment.encode('utf-8', 'replace')).hexdigest()
    uid = "e" + date_token + "-" + digest[:4]
    log_item = (f'<li class="event" id="{uid}">{date_token}: '
                f'{hashtags}] {html_comment}</li>')
    info(log_item)

    plan_fd = open(ofile, 'r', encoding='utf-8', errors='replace')
    plan_content = plan_fd.read()
    plan_fd.close()

    # parsing as XML needs namespaces in XPATH
    plan_tree = etree.parse(StringIO(plan_content),
                            etree.XMLParser(ns_clean=True, recover=True))
    # plan_tree = etree.parse(StringIO(plan_content), etree.HTMLParser())
    ul_found = plan_tree.xpath(
        '''//x:div[@id='Done']/x:ul''',
        namespaces={'x': 'http://www.w3.org/1999/xhtml'})
    # ul_found = plan_tree.xpath('''//div[@id='Done']/ul''')
    info("ul_found = %s" % (ul_found))
    if ul_found:
        ul_found[0].text = '\n      '
        log_item_xml = etree.XML(log_item)
        log_item_xml.tail = '\n\n      '
        ul_found[0].insert(0, log_item_xml)
        new_content = etree.tostring(
            plan_tree, pretty_print=True, encoding="unicode", method="xml")
        new_plan_fd = open(ofile, 'w', encoding='utf-8', errors='replace')
        new_plan_fd.write(new_content)
        new_plan_fd.close()
    else:
        print_usage("Sorry, XML insertion failed.")

    if args.publish:
        yasn_publish(comment, title, subtitle, url, hashtags)


def log2console(biblio):
    '''
    Log to console.
    '''

    TOKENS = (
        'author', 'title', 'subtitle', 'date', 'journal',
        'volume', 'number', 'publisher', 'address', 'DOI', 'isbn',
        'tags', 'comment', 'excerpt', 'url', )
    info(f"biblio = '{biblio}'")
    if biblio['tags']:
        tags = biblio['tags'].strip().split(' ')
        tags_expanded = ''
        for tag in tags:
            tag = KEY_SHORTCUTS.get(tag, tag)
            tags_expanded += tag + ' '
        # biblio['keywords'] = tags_expanded[0:-1]  # removes last space
    bib_in_single_line = ''
    for token in TOKENS:
        info(f"token = '{token}'")
        if token not in biblio:
            if token == 'url':  # I want these printed even if don't exist
                biblio['url'] = ''
            elif token == 'title':
                biblio['title'] = ''
            elif token == 'subtitle':
                biblio['subtitle'] = ''
        if token in biblio and biblio[token]:
            if token == 'tags':
                for value in tags_expanded.strip().split(' '):
                    # print('keyword = %s' % value)
                    bib_in_single_line += 'keyword = %s ' % value
            else:
                # print(('%s = %s' % (token, biblio[token])))
                bib_in_single_line += '%s = %s ' % (token, biblio[token])
    print(f'{bib_in_single_line}')
    if 'identifiers' in biblio:
        for identifer, value in list(biblio['identifiers'].items()):
            if identifer.startswith('isbn'):
                print(f"{identifer} = {value[0]}")

    if args.publish:
        yasn_publish(biblio['comment'],
                     biblio['title'], biblio['subtitle'],
                     biblio['url'], biblio['tags'])


def blog_at_opencodex(biblio):
    '''
    Start at a blog entry at opencodex
    '''

    blog_title = blog_body = ''
    CODEX_ROOT = HOME + '/data/2web/reagle.org/joseph/content/'
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
        tags = tags_expanded[0:-1]  # removes last comma

    if entry:
        blog_title, sep, blog_body = entry.partition('.')
        info(f"blog_title='{blog_title.strip()}' sep='{sep}' "
             f"blog_body='{blog_body.strip()}'")
    info(f"blog_title='{blog_title}'")

    filename = blog_title.lower() \
        .replace(':', '') \
        .replace(' ', '-') \
        .replace("'", '') \
        .replace("/", "-")
    filename = f"{CODEX_ROOT}{category}/{this_year}-{filename}.md"
    info(f"filename = {filename}")
    if os.path.exists(filename):
        print(("\nfilename '%s' already exists'" % filename))
        sys.exit()
    fd = open(filename, 'w', encoding='utf-8', errors='replace')
    fd.write('Title: %s\n' % blog_title)
    fd.write('Date: %s\n' % time.strftime("%Y-%m-%d", NOW))
    fd.write('Tags: %s\n' % tags)
    fd.write('Category: %s\n\n' % category)
    fd.write(blog_body.strip())
    if 'url' in biblio and 'excerpt' in biblio:
        fd.write('\n\n[%s](%s)\n\n' % (biblio['title'], biblio['url']))
        fd.write('> %s\n' % biblio['excerpt'])
    fd.close()
    Popen([VISUAL, filename])


def blog_at_goatee(biblio):
    '''
    Start at a blog entry at goatee
    '''

    GOATEE_ROOT = HOME + '/data/2web/goatee.net/content/'
    info("biblio['comment'] = '%s'" % (biblio['comment']))
    blog_title, sep, blog_body = biblio['comment'].partition('. ')

    this_year, this_month, this_day = time.strftime("%Y %m %d", NOW).split()
    url = biblio.get('url', None)
    filename = blog_title.lower()

    PHOTO_RE = re.compile(r'.*/photo/gallery/(\d\d\d\d/\d\d)'
                          r'/\d\d-\d\d\d\d-(.*)\.jpe?g')
    photo_match = False
    if 'goatee.net/photo/' in url:
        photo_match = re.match(PHOTO_RE, url)
        if photo_match:
            blog_date = re.match(PHOTO_RE, url).group(1).replace('/', '-')
            blog_title = re.match(PHOTO_RE, url).group(2)
            filename = blog_title
            blog_title = blog_title.replace('-', ' ')
    filename = filename.strip().replace(' ', '-').replace("'", '')
    filename = GOATEE_ROOT + '%s/%s%s-%s.md' % (
        this_year, this_month, this_day, filename)
    info(f"blog_title = {blog_title}")
    info(f"filename = {filename}")
    if os.path.exists(filename):
        print(("\nfilename '%s' already exists'" % filename))
        sys.exit()
    fd = open(filename, 'w', encoding='utf-8', errors='replace')
    fd.write('Title: %s\n' % blog_title.title())
    fd.write('Date: %s\n' % time.strftime("%Y-%m-%d", NOW))
    fd.write('Tags: \n')
    fd.write('Category: \n\n')
    fd.write(blog_body.strip())

    if 'url':
        if biblio.get('excerpt', False):
            fd.write('\n\n[%s](%s)\n\n' % (biblio['title'], biblio['url']))
            fd.write('> %s\n' % biblio['excerpt'])
        if photo_match:
            path, jpg = url.rsplit('/', 1)
            thumb_url = path + '/thumbs/' + jpg
            alt_text = blog_title.replace('-', ' ')
            fd.write(
                '''<p><a href="%s"><img alt="%s" class="thumb right" '''
                '''src="%s"/></a></p>\n\n'''
                % (url, alt_text, thumb_url, ))
            fd.write(
                f'<p><a href="{url}"><img alt="{alt_text}" '
                'class="view" src="{url}"/></a></p>')
    fd.close()
    Popen([VISUAL, filename])


#######################################
# Dispatchers


def get_scraper(url, comment):
    '''
    Use the URL to specify a screenscraper.
    '''
    info(f"url = '{url}'")
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
                info(f"scrape = {scraper} ")
                return scraper(url, comment)    # creates instance


def get_logger(text):
    """
    Given the argument return a function and parameters.
    """

    # tags must be prefixed by dot; URL no longer required
    LOG_REGEX = re.compile(
        r'(?P<scheme>\w) (?P<tags>(\.\w+ )+)?'
        r'(?P<url>(doi|isbn|http)\S* ?)?(?P<comment>.*)', re.IGNORECASE)

    if LOG_REGEX.match(text):
        params = LOG_REGEX.match(text).groupdict()
        if 'tags' in params and params['tags']:
            params['tags'] = params['tags'].replace('.', '')
        if 'url' in params and params['url']:
            # unescape zshell safe pasting/bracketing
            params['url'] = params['url'].replace(r'\#', '#')\
                                         .replace(r'\&', '&')\
                                         .replace(r'\?', '?')\
                                         .replace(r'\=', '=')
        info(f"params = '{params}'")
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
        print_usage(f"Sorry, I can't parse the argument: '{text}'.")
    sys.exit()


#######################################
# Miscellaneous


def print_usage(message):
    print(message)
    print("Usage: b scheme [tags ]?[url ]?[comment ]?")


def do_console_annotation(biblio):
    '''Augment biblio with console annotations'''

    # import readline # gives raw_input cursor and history support

    def get_tentative_ident(bibio):
        info(biblio)
        return fe.get_ident({
            'author': fe.parse_names(biblio['author']),
            'title': biblio['title'],
            'year': biblio['date'][0:4],
            '_mm_file': 'CONSOLE'}, {}
        )

    def print_console_msg():
        print(
            '''\tHELP: Enter annotations, excerpt is default\n'''
            '''\t '. ' begins summary \n'''
            '''\t ', ' begins paraphrase \n'''
            '''\t '-- ' begins note \n'''
            '''\t '# ' ignorable comment \n'''
            '''\t 'key=value' for metadata; e.g., \n'''
            '''\t\t\tau=John Smith ti=Greatet Book Ever d=2001 et=cb\n'''
            '''\t\tEntry types (et) values must be typed as shortcut:''')
        for key, value in list(fe.CSL_SHORTCUTS.items()):
            print(f'\t\t\t{key} = {value}')
        print('''\n\tEnd with CTRL-D.\n''')

    def edit_annotation(initial_text, resume_edit=False):
        '''Write initial bib info to a tmp file, edit and return'''

        annotation_file_name = TMP_DIR + 'b-annotation.txt'
        if not resume_edit:
            if os.path.exists(annotation_file_name):
                os.remove(annotation_file_name)
            annotation_file = open(annotation_file_name, "w", encoding="utf-8")
            annotation_file.write(initial_text)
            annotation_file.close()
        call([EDITOR, annotation_file_name])
        annotation_file = open(annotation_file_name, "r", encoding="utf-8")
        return(annotation_file.readlines())

    def parse_bib(biblio, edited_text):
        '''Parse the bib assignments'''

        # biblio['tags'] and whether to yasn publish are overwritten by
        # pre-populated and edited console annotation
        biblio['tags'] = ''
        do_publish = False
        console_annotations = ''
        print(('@%s\n' % (tentative_id)))
        EQUAL_PAT = re.compile(r'(\w{1,3})=')
        for line in edited_text:
            line = line.strip()
            if line == '':
                continue
            if line.startswith('#'):  # ignore comment line
                continue
            elif line == '-p':
                do_publish = True
            elif line == '?':
                print_console_msg()
            elif line.startswith('. '):
                biblio['comment'] = line[2:].strip()
            elif '=' in line[0:3]:  # citation only if near start of line
                cites = EQUAL_PAT.split(line)[1:]
                # 2 refs to an iterable are '*' unpacked and rezipped
                cite_pairs = list(zip(*[iter(cites)] * 2))
                info(f"cite_pairs = {cite_pairs}")
                for short, value in cite_pairs:
                    info(f"short,value = {short},{value}")
                    if short == 't':  # 't=cj' -> cj = 'Nature'
                        biblio[fe.BIB_SHORTCUTS[value]] = biblio['c_web']
                        del biblio['c_web']
                    elif short == 'kw':  # 'kw=complicity
                        biblio['tags'] += ' ' + value.strip()
                    else:
                        biblio[fe.BIB_SHORTCUTS[short]] = value.strip()
            else:
                if line:
                    console_annotations += '\n\n' + line.strip()

        info("biblio.get('excerpt', '') = '%s'" % (biblio.get('excerpt', '')))
        info(f"console_annotations = '{console_annotations}'")
        biblio['excerpt'] = biblio.get('excerpt', '') + console_annotations

        # See if there is a container/fe.CSL_SHORTCUTS redundant with 'c_web'
        if 'c_web' in biblio and \
            len(list(biblio[c] for c in list(fe.CSL_SHORTCUTS.values())
                if c in biblio)) > 1:
            del biblio['c_web']
        return biblio, do_publish

    # code of do_console_annotation
    info("biblio['author'] = '%s'" % (biblio['author']))
    tentative_id = get_tentative_ident(biblio)
    initial_text = [f"d={biblio['date']} au={biblio['author']} ti={biblio['title']}"]
    for key in biblio:
        if key.startswith('c_'):
            initial_text.append(f"{fe.CSL_FIELDS[key]}={title_case(biblio[key])}")
        if key is 'tags' and biblio['tags']:
            tags = ' '.join(['kw=' + KEY_SHORTCUTS.get(tag, tag)
                            for tag in biblio['tags'].strip().split(' ')])
            initial_text.append(tags)
    if args.publish:
        initial_text.append('-p')
    if 'comment' in biblio and biblio['comment'].strip():
        initial_text.append('. ' + biblio['comment'])
    initial_text = '\n'.join(initial_text) + '\n'
    edited_text = edit_annotation(initial_text)
    try:
        biblio, do_publish = parse_bib(biblio, edited_text)
    except (TypeError, KeyError) as e:
        print(('Error parsing biblio assignments: %s\nTry again.' % e))
        time.sleep(2)
        edited_text = edit_annotation('', resume_edit=True)
        biblio, do_publish = parse_bib(biblio, edited_text)

    tweaked_id = get_tentative_ident(biblio)
    if tweaked_id != tentative_id:
        print(('logged: %s to' % get_tentative_ident(biblio)), end='\n')
    return biblio, do_publish


def shrink_tweet(comment, title, url, tags):
    """Shrink tweet to fit into limit"""

    # TWEET_LIMIT = 280 - 6 # API throws an error for unknown reason
    TWEET_LIMIT = 279 - 6  # 6 = comment_delim + title quotes + spaces
    SHORTENER_LEN = 23     # twitter uses t.co

    info(f"TWEET_LIMIT = {TWEET_LIMIT}")
    tweet_room = TWEET_LIMIT - len(tags)
    info(f"tweet_room - len(tags) = {tweet_room}")

    info(f"len(url) = {len(url)}")
    if len(url) > SHORTENER_LEN:
        tweet_room = tweet_room - SHORTENER_LEN
        info(f"  shortened to {SHORTENER_LEN}")
    else:
        tweet_room = tweet_room - len(url)
    info(f"tweet_room after url = {tweet_room}")

    info(f"len(title) = {len(title)}")
    if len(title) > tweet_room:
        info("title is too long")
        title = title[0:tweet_room - 1] + '…'
        info(f"  truncated to {len(title)}")
    tweet_room = tweet_room - len(title)
    info(f"tweet_room after title = {tweet_room}")

    info(f"len(comment) = {len(comment)}")
    if len(comment) > tweet_room:
        info("comment is too long")
        if tweet_room > 5:
            info(" truncating")
            comment = comment[0:tweet_room - 1] + '…'
            info(f"  truncated to {len(comment)}")
            info(f"{comment}")
        else:
            info(" skipping")
            comment = ''
    tweet_room = tweet_room - len(comment)
    info(f"tweet_room after comment = {tweet_room}")

    comment_delim = ": " if comment and title else ""
    title = f'“{title}”' if title else ""
    tweet = f'{comment}{comment_delim}{title} {url} {tags}'
    return(tweet.strip())


def yasn_publish(comment, title, subtitle, url, tags):
    "Send annotated URL to social networks"
    info(f"comment = '{comment}', title = {title}, "
         "subtitle = {subtitle}, url = {url}, tags = {tags}")
    if tags and tags[0] != '#':  # they've not yet been hashified
        tags = ' '.join(['#' + KEY_SHORTCUTS.get(tag, tag)
                        for tag in tags.strip().split(' ')])
    comment, title, subtitle, url, tags = [
        v.strip() if isinstance(v, str) else ''
        for v in [comment, title, subtitle, url, tags]]
    if subtitle:
        title = f'{title}: {subtitle}'
    if 'goatee.net/photo' in url and url.endswith('.jpg'):
        title = ''
        tags = '#photo #' + url.rsplit('/')[-1][8:-4].replace('-', ' #')
        photo = open(HOME + '/f/' + url[19:], 'rb')
    else:
        photo = None
    total_len = len(comment) + len(tags) + len(title) + len(url)
    info(f"""comment = {len(comment)}: {comment}
         title = {len(title)}: {title}
         url = {len(url)}: {url}
         tags = {len(tags)}: {tags}
         total_len = {total_len}""")

    # https://twython.readthedocs.io/en/latest/index.html
    from twython import Twython, TwythonError
    # load keys, tokens, and secrets from twitter_token.py
    from web_api_tokens import TW_CONSUMER_KEY, TW_CONSUMER_SECRET, \
        TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET
    twitter = Twython(TW_CONSUMER_KEY, TW_CONSUMER_SECRET,
                      TW_ACCESS_TOKEN, TW_ACCESS_TOKEN_SECRET)
    try:
        if photo:
            tweet = shrink_tweet(comment, title, '', tags)
            response = twitter.upload_media(media=photo)
            twitter.update_status(status=tweet,
                                  media_ids=[response['media_id']])
        else:
            tweet = shrink_tweet(comment, title, url, tags)
            twitter.update_status(status=tweet)
    except TwythonError as e:
        print(e)
    finally:
        print(f"tweeted {len(tweet)}: {tweet}")


# Check to see if the script is executing as main.
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
    arg_parser.add_argument(
        "-T", "--tests",
        action="store_true", default=False,
        help="run doc tests")
    arg_parser.add_argument(
        "-K", "--keyword-shortcuts",
        action="store_true", default=False,
        help="show keyword shortcuts")
    arg_parser.add_argument(
        '-p', '--publish',
        action="store_true", default=False,
        help="publish to social networks")
    arg_parser.add_argument('text', nargs='*')
    arg_parser.add_argument(
        '-L', '--log-to-file',
        action="store_true", default=False,
        help="log to file %(prog)s.log")
    arg_parser.add_argument(
        '-V', '--verbose', action='count', default=0,
        help="Increase verbosity (specify multiple times for more)")
    arg_parser.add_argument('--version', action='version', version='0.1')

    args = arg_parser.parse_args()

    if args.verbose == 1: log_level = logging.CRITICAL
    elif args.verbose == 2: log_level = logging.INFO
    elif args.verbose >= 3: log_level = logging.DEBUG
    LOG_FORMAT = "%(levelno)s %(funcName).5s: %(message)s"
    if args.log_to_file:
        logging.basicConfig(filename='doi_query.log', filemode='w',
                            level=log_level, format=LOG_FORMAT)
    else:
        logging.basicConfig(level=log_level, format=LOG_FORMAT)

    if args.tests:
        print("Running doctests")
        import doctest
        doctest.testmod()
        sys.exit()
    if args.keyword_shortcuts:
        for dictionary in LIST_OF_KEYSHORTCUTS:
            fe.pretty_tabulate_dict(dictionary, 3)
        sys.exit()

    logger, params = get_logger(' '.join(args.text))
    info("-------------------------------------------------------")
    info("-------------------------------------------------------")
    info(f"params = '{params}'")
    comment = '' if not params['comment'] else params['comment']
    if params['url']:    # not all log2work entries have urls
        scraper = get_scraper(params['url'].strip(), comment)
        biblio = scraper.get_biblio()
    else:
        biblio = {'title': '', 'url': '', 'comment': comment}
    biblio['tags'] = params['tags']
    info(f"biblio = '{biblio}'")
    logger(biblio)
