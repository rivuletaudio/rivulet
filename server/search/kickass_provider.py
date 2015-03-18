from tornado.web import gen
from tornado.httpclient import HTTPRequest
from tornado.httpclient import AsyncHTTPClient
from bs4 import BeautifulSoup
from torrent_search_provider import TorrentSearchProvider
import bs4
import json
import urllib
import re

class KickassProvider(TorrentSearchProvider):
    def __init__(self):
        self.search_cache = {}
        self.file_cache = {}

    def search(self, query):
        if self.search_cache.has_key(query):
            return self.search_cache[query]
        #TODO: can we use the same async http client for all requests?
        http_client = AsyncHTTPClient()
        url = 'https://kickass.to/usearch/' +\
          urllib.quote(query) +\
          '%20category:music%20seeds:1/'
        print 'requesting', url
        request = HTTPRequest(url)
        result_future = http_client.fetch(request, raise_error=False)
        self.search_cache[query] = result_future
        return result_future

    def parse_search(self, response, artist):
        if response.error:
            # 404 happens when there are no results
            print "Error:", response.error
            return []
        soup = BeautifulSoup(response.body, 'lxml')
        trs = soup.select('table#mainSearchTable table tr')
        torrents = []
        for tr in trs[1:]:
            tds = tr.select('td')
            top_seeders =  int(tds[4].contents[0])
            if top_seeders == 0:
                continue
            title = tr.find_all('a', 'cellMainLink')[0].get_text()
            # The name of the artist must be in the torrent name
            if title.lower().find(artist.lower()) == -1:
                continue

            # fuck flac (sorry for any artist or songs that include flac)
            # TODO: do this filter at the filename level
            #if title.lower().find('flac') != -1:
            #    continue

            top_magnet = tr.findAll('a', {'title':re.compile('^Torrent magnet link$')})[0]['href']
            top_torrent_link = tr.findAll('a', {'title':re.compile('^Download torrent file$')})[0]['href']
            top_info_hash = top_magnet[self.pfx_len : self.pfx_len + self.hash_len]
            top_info_link = 'https://kickass.to/torrents/getfiles/' + top_info_hash + '/'
            torrents.append({
                'info_hash': top_info_hash,
                'magnet': top_magnet,
                'torrent_link': top_torrent_link,
                'info_link': top_info_link,
                'torrent_title': title,
                'seeders': top_seeders
            })
        return torrents

    def file_list(self, song):
        info_link = song['info_link']
        if self.file_cache.has_key(info_link):
            return self.file_cache[info_link]
        # get the file listings for the torrent
        http_client = AsyncHTTPClient()
        print 'requesting file list', info_link
        request = HTTPRequest(info_link, method='POST', body='all=1')
        result_future = http_client.fetch(request, raise_error=False)
        self.file_cache[info_link] = result_future
        return result_future

    def parse_file_list(self, response):
        results = []
        if response.error:
            print "Error:", response.error
            return []
        files_container = BeautifulSoup(response.body, "lxml")
        file_list = []
        stack = [('', files_container.select('table')[0])]
        # search of the table for file names
        while len(stack) > 0:
            prefix, curr_table = stack.pop()
            for tr in curr_table.children:
                if type(tr) is bs4.element.NavigableString:
                  continue
                # is a folder or a file?
                tds = list(tr.children)
                if len(tds) > 6:
                    #file
                    filename = tds[5].string
                    if filename:
                        if prefix != '':
                            file_list.append(prefix + '/' + filename)
                        else:
                            file_list.append(filename)
                elif len(tds) == 5:
                    #folder
                    folder_name = '???????'
                    if tds[3].a and tds[3].a.span:
                        folder_name = tds[3].a.span.string
                    elif tds[3].span and tds[3].span.a:
                        folder_name = tds[3].span.a.string
                    folder_table = tds[3].table
                    if folder_table is None:
                        folder_table = tds[3].span.table
                    if folder_table is None:
                        raise Exception('wtf')
                    if prefix != '':
                        stack.append((prefix + '/' + folder_name, folder_table))
                    else:
                        stack.append((folder_name, folder_table))
        return file_list

