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

BusySponge permit me to easily log and annotate a URL to various loggers
(e.g., mindmap, blogs) with meta/bibliographic data about the URL from
a scraping.

http://reagle.org/joseph/blog/technology/python/busysponge-0.5
"""

# TODO
# * archive URLs to e/old/`r=`

import argparse
import codecs
import fe
import re
import string
import sys
import time
from web_little import get_HTML, unescape_XML, escape_XML # personal utility module
from change_case import sentence_case

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

FB_KEY_SHORTCUTS = {
        'cri' : 'criticism',
        'fee' : 'feedback',
        'ass' : 'assessment',
        'aut' : 'automated',
        'rat' : 'rating',
        'ran' : 'ranking',
        'com' : 'comment',
        'est' : 'esteem',
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
        'mar': 'market',
        'mea': 'mean',
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
    FB_KEY_SHORTCUTS,WP_KEY_SHORTCUTS)

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
        self.zim = None

    def get_biblio(self):
        biblio = {
            'author' : self.get_author(),
            'title' : self.get_title(),
            'date' : self.get_date(),
            'org' : self.get_org(),
            'permalink' : self.get_permalink(),
            'excerpt' : self.get_excerpt(),
            'comment' : self.comment,
            'url' : self.url,
            'zim' : self.zim, # content from zim wiki
        }
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
            title = sentence_case(tmatch.group(1).strip())
        else:
            title = "UNKNOWN TITLE"
        return title

    def get_date(self):
        '''rough match of a date, then pass to dateutil's magic abilities'''

        from dateutil.parser import parse

        date_regexp = "(\d+,? )?(%s)\w*(,? \d+)?(,? \d+)" % MONTHS
        try:
            dmatch = re.search(date_regexp, self.text, re.IGNORECASE)
            return parse(dmatch.group(0)).strftime("%B %d, %Y").split(', ')
        except:
            now = time.gmtime()
            year = time.strftime('%Y', now)
            month = time.strftime('%B %d', now)
            return month, year

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
        return month + ' ' + day, year

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
        year = time.strftime('%Y', date)
        month = time.strftime('%B %d', date)
        return month, year

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
        year = time.strftime('%Y', date)
        month = time.strftime('%B %d', date)
        return month, year

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
        return month + ' ' + day, year

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
            date = time.strptime(mdate, "%Y-%m-%d %I:%M:%S")
        except ValueError:
            date = time.strptime(mdate, "%Y-%m-%d %H:%M:%S")
        month = time.strftime('%B %d', date)
        year = time.strftime('%Y', date)
        return month, year

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

    ofile = HOME+'/data/2web/reagle.org/joseph/2005/ethno/field-notes.mm'
    author = biblio['author']
    title = biblio['title']
    month, year = biblio['date']
    keyword, sep, abstract = biblio['comment'].partition(' ')
    excerpt = biblio['excerpt']
    org = biblio['org']
    permalink = biblio['permalink']

    now = time.gmtime()
    this_week = time.strftime("%U", now)
    this_year = time.strftime('%Y', now)
    day_read = time.strftime("%Y%m%d %H:%M UTC",now)

    citation = "or=%s m=%s y=%s r=%s" % (org, month, year, day_read)
    if keyword:
        keyword = KEY_SHORTCUTS.get(keyword, keyword)
        citation += ' kw=' + keyword

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

    #if biblio['zim']:
        #comment = biblio['zim']
        #activity = ...
    #else:
        #>>>
    ######################## this is traditional
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
    ########################

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

#######################################
# Dispatchers

def get_scraper(url, comment):
    '''
    Use the URL to specify a screenscraper.
    '''

    dispatch_scraper = (
        ('file://%s/tmp/nupedia-l/' %HOME, scrape_NupediaL),
        ('http://lists.wikimedia.org/pipermail/', scrape_WM_lists),
        ('http://en.wikipedia.org/wiki/Wikipedia:Wikipedia_Signpost/', scrape_Signpost),
        ('http://en.wikipedia.org/w', scrape_ENWP),
        ('http://meta.wikimedia.org/w', scrape_WMMeta),
        ('http://marc.info/', scrape_MARC),
        ('', scrape_default)     # default: make sure last
    )

    for prefix, scraper in dispatch_scraper:
        if url.startswith(prefix):
            return scraper(url, comment)    # creates instance


def get_logger(options={}):
    """
    Matches the option string to grammar and output.
    """
    params = None
    dispatch_logger = (
        (r'(?P<url>(\.|http)\S* )?(?P<scheme>g) (?P<comment>.*)',
            log2goatee),
        (r'(?P<url>(\.|http)\S* )?(?P<scheme>j) (?P<comment>.*)',
            log2work),
        (r'(?P<url>(\.|http)\S* )?(?P<scheme>m) ?(?P<comment>.*)',
            log2mm)
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
    sys.exit()


def print_usage(message):
    print message
    print "Usage: b [url]? scheme [scheme parameters]? comment"


#Check to see if the script is executing as main.
if __name__ == "__main__":

    parser = argparse.ArgumentParser(description="usage: %prog [options] [URL]")
    parser.add_argument("-t", "--tests",
                    action="store_true", default=False,
                    help="run doc tests")
    parser.add_argument("-K", "--keyword-shortcuts",
                action="store_true", default=False,
                help="show keyword shortcuts")
    args = parser.parse_args()

    if args.tests:
        print("Running doctests")
        import doctest
        doctest.testmod()
        sys.exit()
    if args.keyword_shortcuts:
        for dictionary in LIST_OF_KEYSHORTCUTS:
            fe.pretty_tabulate_dict(dictionary,3)
        sys.exit()

    logger, params = get_logger(' '.join(arguments))    # <- function, (url, scheme, comment)
    comment = params['comment'].strip()
    if params['url']:    # not all log2work entries have urls
        scraper = get_scraper(params['url'].strip(), comment)
        logger(scraper.get_biblio())
    else:
        logger({'title' : '', 'url': '', 'comment' : comment})
