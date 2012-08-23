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
# * archive URLs to e/old/`r=`

import argparse
import codecs
import fe
import logging
from lxml import etree
import re
import string
import sys
import time
from web_little import get_HTML, unescape_XML, escape_XML # personal utility module
from change_case import sentence_case

log_level = 100 # default
critical = logging.critical
info = logging.info
dbg = logging.debug

from os import environ
try: 
    HOME = environ['HOME']
except KeyError, e:
    HOME = '/home/reagle'

# Expansions for common tags/actitivies
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
        'pri': 'privacy',
        'spe': 'speech',
        'str': 'structure',
        'tro': 'trolling',
        'zei': 'zeitgeist',
        }

CC_KEY_SHORTCUTS = {
        'ass' : 'assessment',
        'aut' : 'automated',
        'bou' : 'boundaries',
        'com' : 'competitive',
        'cri' : 'criticism',
        'est' : 'esteem',
        'fee' : 'feedback',
        'inf' : 'informed',
        'mar': 'market',
        'mea' : 'mean',
        'off' : 'offensive',
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

def get_Now_YMD():
    '''
    Now in YearMonthDay format
    '''

    now = time.localtime()

    date_token = time.strftime("%y%m%d", now)
    return date_token

def get_text(url):
    '''Textual version of url'''

    import os

    return unicode(os.popen('lynx -display_charset=utf-8 -width=10000 '
        '-nolist -dump "%s"' %url).read().decode('utf-8', 'replace'))


#######################################
# Screen scrapers

class scrape_default(object):
    """
    Default and base class scraper.
    """
    def __init__(self, url, comment):
        print "Scraping default Web page;",
        self.url = url
        self.comment = comment
        self.html, resp = get_HTML(url, cache_control = 'no-cache')
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
        '''test against two conditions, return guess of article author'''

        # blogs: "By John Smith at 15:55 September, 03 2009"
        author_regexp1 = "by ([a-z ]*?)(?:-|, | at | on ).{,17}?\d\d\d\d"
        dmatch = re.search(author_regexp1, self.text, re.IGNORECASE)
        if dmatch:
            #print("*** dmatch1 = '%s'" % dmatch.group())
            if len(dmatch.group(1)) > 4: # no 0 len "by at least"
                return string.capwords(dmatch.group(1))
        # newspapers: "By John Smith"
        author_regexp2 = "^ *By (.*)"
        dmatch = re.search(author_regexp2, self.text, re.MULTILINE)
        if dmatch:
            #print("*** dmatch2 = '%s'" % dmatch.group())
            if len(dmatch.group(1).split()) < 6: # if short byline
                return string.capwords(dmatch.group(1))
        print('*** UNKNOWN')
        return 'UNKNOWN'

    def get_date(self):
        '''rough match of a date, then pass to dateutil's magic abilities'''

        from dateutil.parser import parse

        date_regexp = "(\d+,? )?(%s)\w*(,? \d+)?(,? \d+)" % MONTHS
        try:
            dmatch = re.search(date_regexp, self.text, re.IGNORECASE)
            return parse(dmatch.group(0)).strftime("%Y%m%d")
        except:
            now = time.gmtime()
            date = time.strftime('%Y%m%d', now)
            info("making date now = %s" % date)
            return date

    def split_title_org(self):
        '''Often the publishing org is in the title.
        See if there is a short bit of text (<=35%) at the end of 
        the string and if so assume that is the org.'''
        
        title = self.get_title()
        org = self.get_org()

        DELIMTER = re.compile('([-\|:;])') # 
        parts = DELIMTER.split(title)
        if len(parts) >= 2:
            beginning, end = ''.join(parts[0:-2]), parts[-1]
            info("beginning = %s, end = %s" %(beginning, end))
            end_ratio = float(len(end)) / len(beginning + end)
            info(" %d / %d = %.2f" %( len(end),  len(beginning + end), end_ratio))
            if end_ratio <= 0.35 or len(end) <= 20:
                return sentence_case(beginning.strip()), end.strip().title()
        return title, org

    def get_title(self):

        title_regexps = (
            ('http://lists.w3.org/.*', '<!-- subject="(.*?)" -->'),
            ('http://lists.kde.org/.*', r"<title>MARC: msg '(.*?)'</title>"),
            ('', r'<title>(.*?)</title>')    # default: make sure last
        )

        for prefix, regexp in title_regexps:
            if self.url.startswith(prefix):
                break

        tmatch = re.search(regexp, self.html, re.DOTALL|re.IGNORECASE)
        if tmatch:
            title = unescape_XML(tmatch.group(1).strip())
            title = sentence_case(title)
        else:
            title = "UNKNOWN TITLE"
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
        print "Scraping photo.net;",
        self.url = url
        self.comment = comment
        self.html, resp = get_HTML(url, cache_control = 'no-cache')        
        print(self.html)
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
        biblio['organization'] = "photo.net"
        return biblio
        
    def get_author(self):

        author = self.doc.xpath(
            "//div[@class='originalpost']/p/a[@href]/text()")[0]
        print("author = %s" % author)
        return author.strip()

    def get_title(self):

        title = self.doc.xpath("//title/text()")[0]
        title = title.split('- Photo.net')[0]
        print("title = %s" % title)
        return title.strip()
        
    def get_date(self):
        from dateutil.parser import parse

        date = self.doc.xpath(
            "//div[@class='originalpost']/p/text()")[1]
        date = parse(date).strftime("%Y%m%d")
        print("date = %s" % date)
        return date

    def get_excerpt(self):
        excerpt = self.doc.xpath(
            "//div[@class='originalpost']/div[@class='message']/p/text()") 
        print("excerpt = %s" % excerpt)
        return excerpt
        
        
class scrape_DOI(scrape_default):
    
    def __init__(self, url, comment):
        print "Scraping DOI;",
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
        print "Scraping en.Wikipedia;",
        scrape_default.__init__(self, url, comment)

    def get_author(self):
        return 'Wikipedia'

    def get_title(self):
        title = scrape_default.get_title(self)    # use super()?
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
        print "Scraping en.Wikipedia Signpost;",
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
        print "Scraping local Nupedia archive;",
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
        print "Scraping Wikimedia Lists;",
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
                print excerpt
                return excerpt.strip()
        return None

    def get_permalink(self):
        return self.url


class scrape_WMMeta(scrape_default):

    def __init__(self, url, comment):
        print "Scraping Wikimedia Meta;",
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
        print "Scraping MARC;",
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

    print "to log2mm"

    now = time.gmtime()
    this_week = time.strftime("%U", now)
    this_year = time.strftime('%Y', now)
    date_read = time.strftime("%Y%m%d %H:%M UTC",now)
    
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
        print "creating", year
        year_node = SubElement(mm_years, 'node', {'TEXT': this_year, 'POSITION': 'right'})
        week_node = SubElement(year_node, 'node', {'TEXT': this_week, 'POSITION': 'right'})

    for week_node in year_node:
        if week_node.get('TEXT') == this_week:
            print "found week", this_week
            break
    else:
        print "creating", this_week
        week_node = SubElement(year_node, 'node', {'TEXT': this_week, 'POSITION': 'right'})

    author_node = SubElement(week_node, 'node', {'TEXT': author, 'COLOR': '#338800'})
    title_node = SubElement(author_node, 'node', {'TEXT': title, 'COLOR': '#090f6b',
        'LINK': permalink})
    cite_node = SubElement(title_node, 'node', {'TEXT': citation, 'COLOR': '#ff33b8'})
    if abstract:
        abstract_node = SubElement(title_node, 'node', {'TEXT': abstract, 'COLOR': '#999999'})
    if excerpt:
        excerpt_node = SubElement(title_node, 'node', {'TEXT': excerpt, 'COLOR': '#166799'})

    ElementTree(mindmap).write(ofile)


def log2goatee(biblio):
    '''
    Log to personal blog.
    '''

    import codecs

    print "to log2goatee"
    ofile = HOME+'/data/2web/goatee.net/nifty-stuff.html'

    title = biblio['title']
    comment = biblio['comment']
    url = biblio['url']

    date_token = get_Now_YMD()
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

    print "to log2work"
    ofile = HOME+'/data/2web/reagle.org/joseph/plan/plans/index.html'

    title = biblio['title']
    activity, sep, comment = biblio['comment'].partition(' ')
    url = biblio['url']

    # Replace the line with the '^' character with a hypertext link
    comment = re.sub('(.*)\^(.*)',u'\\1<a href="%s">%s</a>\\2' %
        (escape_XML(url), title), comment)

    date_token = get_Now_YMD()
    digest = hashlib.md5(comment.encode('utf-8', 'replace')).hexdigest()
    uid = "e" + date_token + "-" + digest[:4]
    log_item = '<li class="event" id="%s">%s: %s] %s</li>' % \
        (uid, date_token, activity, comment)

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

def log2console(biblio):
    '''
    Log to console.
    '''
    
    print('\n')
    print("author=%s" % biblio['author']),
    print("title=%s" % biblio['title']),
    print("date=%s" % biblio['date']),
    for token in ('author', 'title', 'date', 'permalink', 'type'):
        if token in biblio:
            del biblio[token]
    for key,value in biblio.items():
        print("%s=%s" % (key, value)),
    print('\n')

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
        ('http://photo.net/', scrape_photo_net),
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
        (r'(?P<url>(\.|http)\S* )?(?P<scheme>g) (?P<comment>.*)',
            log2goatee),
        (r'(?P<url>(\.|http)\S* )?(?P<scheme>j) (?P<comment>.*)',
            log2work),
        (r'(?P<url>(\.|doi|http)\S* )?(?P<scheme>m) ?(?P<comment>.*)',
            log2mm),
        (r'(?P<url>(\.|doi|http)\S* )?(?P<scheme>c) ?(?P<comment>.*)',
            log2console),
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


def print_usage(message):
    print message
    print "Usage: b [url]? scheme [scheme parameters]? comment"


#Check to see if the script is executing as main.
if __name__ == "__main__":
    arg_parser = argparse.ArgumentParser(
        prog='b', usage='%(prog)s [options] [URL] logger [keyword] [text]')
    arg_parser.add_argument("-t", "--tests",
                    action="store_true", default=False,
                    help="run doc tests")
    arg_parser.add_argument("-K", "--keyword-shortcuts",
                action="store_true", default=False,
                help="show keyword shortcuts")
    arg_parser.add_argument('text', nargs='*')
    arg_parser.add_argument('-l', '--log-to-file',
        action="store_true", default=False,
        help="log to file %(prog)s.log")
    arg_parser.add_argument('-v', '--verbose', action='count', default=0,
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
    if params['url']:    # not all log2work entries have urls
        scraper = get_scraper(params['url'].strip(), comment)
        logger(scraper.get_biblio())
    else:
        logger({'title' : '', 'url': '', 'comment' : comment})
