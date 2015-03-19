from tornado.web import gen
from tornado.httpclient import HTTPRequest
from tornado.httpclient import AsyncHTTPClient
from bs4 import BeautifulSoup
from torrent_search_provider import TorrentSearchProvider
import bs4
import json
import urllib
import re

class OldPirateBayProvider(TorrentSearchProvider):
    def search_torrent(self, query):
        #TODO: can we use the same async http client for all requests?
        http_client = AsyncHTTPClient()
        url = 'https://oldpiratebay.org/search?q=' +\
          urllib.quote(query) +\
          '&iht=6&sort=-seeders'
        print 'requesting', url
        request = HTTPRequest(url)
        result_future = http_client.fetch(request, raise_error=False)
        return result_future

    def parse_search(self, response, artist):
        if response.error:
            print "Error:", response.error
            return []
        soup = BeautifulSoup(response.body, 'lxml')
        trs = soup.select('table.search-result tr')
        torrents = []
        for tr in trs[1:]:
            tds = tr.select('td')
            # Sometimes we get: [<td colspan="6"><div class="empty">Blimey! Nothing was found. Try to search again with a different query.</div></td>]
            if len(tds) == 1:
                return []
            top_seeders = int(tds[4].contents[0])
            if top_seeders == 0:
                continue
            title = tds[1].find_all('a')[0].get_text()
            # The name of the artist must be in the torrent name
            if title.lower().find(artist.lower()) == -1:
                continue
            top_magnet = tds[1].findAll('a', {'title':re.compile('^MAGNET LINK$')})[0]['href']
            top_torrent_link = tds[1].findAll('a', {'title':re.compile('^TORRENT LINK$')})[0]['href']
            top_info_hash = top_magnet[self.pfx_len : self.pfx_len + self.hash_len]
            top_info_link = 'https://oldpiratebay.org' + tds[1].find_all('a')[0]['href']
            torrents.append({
                'info_hash': top_info_hash,
                'magnet': top_magnet,
                'torrent_link': top_torrent_link,
                'info_link': top_info_link,
                'torrent_title': title,
                'seeders': top_seeders
            })
        return torrents

    def file_list(self, info_link):
        # get the file listings for the torrent
        http_client = AsyncHTTPClient()
        print 'requesting file list', info_link
        request = HTTPRequest(info_link)
        result_future = http_client.fetch(request, raise_error=False)
        return result_future 

    def parse_file_list(self, response):
        results = []
        if response.error:
            print "Error:", response.error
            return []
        files_container = BeautifulSoup(response.body, 'lxml')
        file_list = []
        rows = files_container.select('#w0 table tr')
        for row in rows:
            # skip the header
            tds = row.select('td')
            if len(tds) > 0:
                # Handle this case: <td colspan="3"><div class="empty">No results found.</div></td>
                if len(tds) == 1:
                    continue
                # get the full path
                file_list.append(tds[1].contents[0])
        return file_list

