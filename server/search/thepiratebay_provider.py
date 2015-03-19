from tornado.web import gen
from tornado.httpclient import HTTPRequest
from tornado.httpclient import AsyncHTTPClient
from bs4 import BeautifulSoup
from torrent_search_provider import TorrentSearchProvider
import bs4
import json
import urllib
import re
import sys
import os
sys.path.append(
        os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", ".."))
from server import torrent

class ThePirateBayProvider(TorrentSearchProvider):
    def search_torrent(self, query):
        #TODO: can we use the same async http client for all requests?
        http_client = AsyncHTTPClient()
        url = 'https://thepiratebay.se/search/' +\
              urllib.quote(query) +\
              '/0/7/100'
        print 'requesting', url
        request = HTTPRequest(url)
        result_future = http_client.fetch(request, raise_error=False)
        return result_future

    def parse_search(self, response, artist):
        if response.error:
            # 404 happens when there are no results
            print "Error:", response.error
            return []
        soup = BeautifulSoup(response.body, 'lxml')
        trs = soup.select('#searchResult tr')
        torrents = []
        for tr in trs[1:]:
            tds = tr.select('td')
            top_seeders =  int(tds[2].contents[0])
            if top_seeders == 0:
                continue
            title = tr.find_all('a', 'detLink')[0].get_text()
            # The name of the artist must be in the torrent name
            if title.lower().find(artist.lower()) == -1:
                continue
            # fuck flac (sorry for any artist or songs that include flac)
            # TODO: do this filter at the filename level
            if title.lower().find('flac') != -1:
                continue
            top_magnet = tr.findAll('a', {'title':re.compile('^Download this torrent using magnet$')})[0]['href']
            top_torrent_link = None
            torrent_links = tr.findAll('a', {'title':re.compile('^Download this torrent$')})
            if len(torrent_links) > 0:
                top_torrent_link = 'http:' + torrent_links[0]['href']
            top_info_hash = top_magnet[self.pfx_len : self.pfx_len + self.hash_len]
            torrents.append({
                'info_hash': top_info_hash,
                'info_link': top_info_hash, #this is the name of the param that gets passed on to file_list()
                'magnet': top_magnet,
                'torrent_link': top_torrent_link,
                'torrent_title': title,
                'seeders': top_seeders
            })
        return torrents

    def file_list(self, info_hash):
        # get the file listings for the torrent
        http_client = AsyncHTTPClient()
        info_link = 'http://torcache.net/torrent/' + info_hash + '.torrent'
        print 'requesting file list', info_link
        request = HTTPRequest(info_link)
        result_future = http_client.fetch(request, raise_error=False)
        return result_future

    def parse_file_list(self, response):
        results = []
        if response.error:
            print "Error:", response.error
            return []
        torrent_info = torrent.bytes_to_ti(response.body)
        file_list = []
        for i in range(torrent_info.num_files()):
            f = torrent_info.file_at(i)
            file_list.append(f.path.decode(sys.getfilesystemencoding()))
        return file_list

