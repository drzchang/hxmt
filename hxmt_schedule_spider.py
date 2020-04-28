#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Created Date: 20:59 2019-05-08
License:
    +++ DO NOT DISTRIBUTE WITHOUT PERMISSION +++

Description:

Note:
1.
2.

"""
__author__ = 'Zhi Chang <changzhi@ihep.ac.cn>'
__version__ = 'v1r0p0'
__date__ = '2019-xx-xx'

import urllib.request
import urllib.parse
from bs4 import BeautifulSoup
from astropy.time import Time
import re
import os
import sys
import numpy as np


class Source(object):
    def __init__(self, obsid, name, isot, ra, dec, exp):
        self.obsid = obsid
        self.name = name
        self.isot = Time(isot, format='isot').isot
        self.mjd = Time(isot, format='isot').mjd
        self.ra = ra
        self.dec = dec
        self.exp = exp


class UrlManager(object):
    """
    class to hanlde urls during the process, excluding the urls which
    have been crawed.
    """

    def __init__(self):
        self.new_urls = set()
        self.old_urls = set()

    def add_new_url(self, url):
        if url is None:
            return
        if url not in self.new_urls and url not in self.old_urls:
            self.new_urls.add(url)

    def add_new_urls(self, urls):
        if urls is None or len(urls) == 0:
            return
        for url in urls:
            self.add_new_url(url)

    def has_new_url(self):
        return len(self.new_urls) != 0

    def get_new_url(self):
        new_url = self.new_urls.pop()
        self.old_urls.add(new_url)
        return new_url


class HtmlDownloader(object):
    """
    download the html page for analysis.
    """

    def download(self, url):
        if url is None:
            return None
        response = urllib.request.urlopen(url)
        if response.getcode() != 200:
            return None
        return response.read()


exclude_source_list = ['0817_c', 'craboffset', 'crab_offset', 'cosmosfield',
                       '8hr', 'antlia', 'tycho', '9hr', 'decam', 'cdfs',
                       'burst']


class HtmlParser(object):

    def parser(self, page_url, html_cont):
        if page_url is None or html_cont is None:
            return
        soup = BeautifulSoup(html_cont, 'html.parser', from_encoding='utf-8')
        new_urls = self._get_new_urls(page_url, soup)
        new_data = self._get_new_data(soup)
        return new_urls, new_data

    def _get_new_urls(self, page_url, soup):
        new_urls = set()
        links = soup.findAll('a', class_=re.compile(r'hy_doc_more'))
        for link in links:
            new_url = link['href']
            new_full_url = urllib.parse.urljoin(page_url, new_url)
            new_urls.add(new_full_url)
        return new_urls

    def _get_new_data(self, soup):
        sources = set()
        try:
            trs = soup.find('tbody').find_all('tr')
        except AttributeError:
            return
        for tr in trs[2:]:
            tds = tr.find_all('td')
            if tds[3].get_text().strip() == 'Point':  # only point mode
                name = tds[1].get_text().strip()
                name = ''.join(list(filter(str.isalnum, name))).lower()
                #name = name.replace(' ', '').lower()

                if name.startswith('blank') or \
                        name.startswith('dusty') or \
                        name.startswith('field'):
                    continue
                if name in exclude_source_list:
                    continue

                obsid = tds[0].get_text().strip()
                t = tds[2].get_text().strip()
                isot = t.replace('/', '-')
                isot = 'T'.join(isot.split())
                ra = tds[4].get_text().strip()
                dec = tds[5].get_text().strip()
                exp = tds[6].get_text().strip()
                src = Source(obsid, name, isot, ra, dec, exp)
                sources.add(src)
            else:
                continue
        return sources


class Outputer(object):
    """
    output file handler
    """

    def __init__(self):
        self.srcs = []

    def collect_data(self, data):
        if data is None:
            return
        self.srcs += data

    def output_txt(self, pathout):
        """txt file handler
        """
        _s = '{:12s} {:20s} {:9s} {:9s} {:>24s} {:20s} {:7s}\n'

        _txt = os.path.join(pathout, 'schedule.txt')
        fout = open(_txt, 'w', encoding='utf8')
        fout.write('#' + _s.format('obsid',
                                   'name',
                                   'ra',
                                   'dec',
                                   'time(isot)',
                                   'time(mjd)',
                                   'exp(ks)'))

        srcs = sorted(self.srcs, key=lambda t: t.mjd)
        for src in srcs:
            fout.write(_s.format(str(src.obsid),
                                 str(src.name),
                                 str(src.ra),
                                 str(src.dec),
                                 str(src.isot),
                                 str(src.mjd),
                                 str(src.exp)))

        fout.close()

    def output_csv(self, pathout):
        """ csv file handler
        """
        _s = '{},{},{},{},{},{},{}\n'

        _csv = os.path.join(pathout, 'schedule.csv')
        fout = open(_csv, 'w', encoding='utf8')
        fout.write('#' + _s.format('obsid',
                                   'name',
                                   'ra',
                                   'dec',
                                   'time(isot)',
                                   'time(mjd)',
                                   'exp(ks)'))
        srcs = sorted(self.srcs, key=lambda t: t.mjd)
        for src in srcs:
            fout.write(_s.format(str(src.obsid),
                                 str(src.name),
                                 str(src.ra),
                                 str(src.dec),
                                 str(src.isot),
                                 str(src.mjd),
                                 str(src.exp)))

        fout.close()


class SpiderMain(object):
    def __init__(self):
        self.urls = UrlManager()
        self.downloader = HtmlDownloader()
        self.parser = HtmlParser()
        self.outputer = Outputer()

    def craw(self, root_url, pathout='./'):
        count = 1
        self.urls.add_new_url(root_url)
        while self.urls.has_new_url():
            new_url = self.urls.get_new_url()
            print('craw %2d : %s' % (count, new_url))
            html_cont = self.downloader.download(new_url)
            new_urls, new_data = self.parser.parser(new_url, html_cont)
            self.urls.add_new_urls(new_urls)
            self.outputer.collect_data(new_data)
            count += 1

        self.outputer.output_txt(pathout)
        self.outputer.output_csv(pathout)


def craw_hxmt():
    obj_spider = SpiderMain()
    root_url = 'http://www.hxmt.org/dqjh_{}.jhtml'
    for i in np.arange(1, 3):
        try:
            obj_spider.craw(root_url.format(i))
        except Exception as e:
            print(e)
            print('craw failed')


if __name__ == '__main__':
    craw_hxmt()
