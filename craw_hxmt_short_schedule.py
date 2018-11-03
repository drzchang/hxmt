#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created Date: Jul 20, 2018
License:
    +++ DO NOT DISTRIBUTE WITHOUT PERMISSION +++

Description:

Note:
1.
2.

"""
from __future__ import division, print_function

__author__ = 'Zhi Chang <changzhi@ihep.ac.cn>'
__version__ = 'v1r0p0'
__date__ = '2018-xx-xx'

import urllib
from bs4 import BeautifulSoup
from astropy.time import Time
import time
import re
import numpy as np


class Source(object):
    def __init__(self, obsid, name, time1, mode, ra, dec, exp, r, v, step):
        self.obsid = ''.join(obsid.split()).replace(',', '_')
        name = ''.join(name.split())
        self.name = name.lower().replace('_', '')
        tt = time1.split()
        isot = 'T'.join(['-'.join(tt[0].split('/')), tt[-1]])
        isot1 = time.strptime(isot, '%Y-%m-%dT%H:%M:%S')
        self.isot = time.strftime("%Y-%m-%dT%H:%M:%S", isot1)
        self.time = Time(isot, format='isot').mjd
        self.mode = mode.split()[0]
        self.ra = ra.split()[0]
        self.dec = dec.split()[0]
        self.exp = ''.join(exp.split())
        self.r = r.replace(' ', '')
        self.v = v.replace(' ', '')
        self.step = step.replace(' ', '')

    def __str__(self):
        return '<{src} {t}>'.format(src=self.name, t=self.time)

    __repr__ = __str__


class UrlManager(object):
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

    def download(self, url):
        if url is None:
            return None
        response = urllib.request.urlopen(url)
        if response.getcode() != 200:
            return None
        return response.read()


class HtmlParser(object):

    def parser(self, page_url, html_cont):
        if page_url is None or html_cont is None:
            return
        soup = BeautifulSoup(html_cont, 'html.parser', from_encoding='utf-8')
        new_urls = self._get_new_urls(page_url, soup)
        new_data = self._get_new_data(page_url, soup)
        return new_urls, new_data

    def _get_new_urls(self, page_url, soup):
        new_urls = set()
        links = soup.findAll('li', class_=re.compile(r'pagenav'))
        for link in links:
            new_url = link.find('a')['href']
            new_full_url = urllib.parse.urljoin(page_url, new_url)
            new_urls.add(new_full_url)
        return new_urls

    def _get_new_data(self, page_url, soup):
        res_data = set()
        obs_node = soup.findAll('td')
        obs = []
        for j in obs_node:
            obs.append(j.get_text().replace('\n', ''))
        obs = obs[11:]
        for iid in range(int(len(obs)/10)):
            src = Source(obs[10*iid+0],
                         obs[10*iid+1],
                         obs[10*iid+2],
                         obs[10*iid+3],
                         obs[10*iid+4],
                         obs[10*iid+5],
                         obs[10*iid+6],
                         obs[10*iid+7],
                         obs[10*iid+8],
                         obs[10*iid+9])
            res_data.add(src)
            del src
        return res_data


class TxtOutputer(object):
    def __init__(self):
        self.datas = []

    def collect_data(self, data):
        if data is None:
            return
        self.datas += data

    def output_txt(self):
        timeStruct = time.localtime(time.time())
        strTime = time.strftime("%Y-%m-%d", timeStruct)
        fout = open('hxmt-schedule-%s.txt' % strTime, 'w', encoding='utf8')
        fout.write('#%12s %20s %9s %9s %20s %20s %7s\n' % ('obsid',
                                                           'name',
                                                           'ra',
                                                           'dec',
                                                           'time(isot)',
                                                           'time(mjd)',
                                                           'exp(ks)'))
        ts = sorted(self.datas, key=lambda t: t.time)
        for data in ts:
            if data.mode.lower() == 'point' and data.name[:5] != 'blank':
                fout.write('%12s %20s %9s %9s %20s %20s %7s\n' % (str(data.obsid),
                                                                  str(data.name),
                                                                  str(data.ra),
                                                                  str(data.dec),
                                                                  str(data.isot),
                                                                  str(data.time),
                                                                  str(data.exp)))
            else:
                pass
        fout.close()

    def output_csv(self):
        timeStruct = time.localtime(time.time())
        strTime = time.strftime("%Y-%m-%d", timeStruct)
        fout = open('hxmt-schedule-%s.csv' % strTime, 'w', encoding='utf8')
        fout.write('#%s,%s,%s,%s,%s,%s,%s\n' % (
                    'obsid', 'name', 'ra', 'dec',
                    'time(isot)', 'time(mjd)', 'exp(ks)'))
        ts = sorted(self.datas, key=lambda t: t.time)
        for data in ts:
            if data.mode.lower() == 'point':
                fout.write('%s,%s,%s,%s,%s,%s,%s\n' % (str(data.obsid),
                                                       str(data.name),
                                                       str(data.ra),
                                                       str(data.dec),
                                                       str(data.isot),
                                                       str(data.time),
                                                       str(data.exp)))
            else:
                pass
        fout.close()


class SpiderMain(object):
    def __init__(self):
        self.urls = UrlManager()
        self.downloader = HtmlDownloader()
        self.parser = HtmlParser()
        self.outputer = TxtOutputer()

    def craw(self, root_url):
        count = 1
        self.urls.add_new_url(root_url)
        while self.urls.has_new_url():
            try:
                new_url = self.urls.get_new_url()
                print('craw %d : %s' % (count, new_url))
                html_cont = self.downloader.download(new_url)
                new_urls, new_data = self.parser.parser(new_url, html_cont)
                self.urls.add_new_urls(new_urls)
                self.outputer.collect_data(new_data)
#                 if count == 100:
#                     break
                count += 1
                sleep_t = np.random.randint(5)
                print('sleep %d seconds ...' % sleep_t)
                time.sleep(sleep_t)
            except Exception as e:
                print(e)
                print('craw failed .')

        self.outputer.output_txt()
        self.outputer.output_csv()


if __name__ == '__main__':
    root_url = 'http://www.hxmt.org/index.php/plan/splan/256-hxmt-short-term-schedule-2017-6-25-30'
    obj_spider = SpiderMain()
    obj_spider.craw(root_url)
