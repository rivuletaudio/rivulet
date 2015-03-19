from tornado.web import gen
from tornado.httpclient import HTTPRequest
from tornado.httpclient import AsyncHTTPClient
from bs4 import BeautifulSoup
from kickass_provider import KickassProvider
from oldpiratebay_provider import OldPirateBayProvider
from thepiratebay_provider import ThePirateBayProvider
import bs4
import json
import urllib
import re

search_providers = [KickassProvider(), OldPirateBayProvider(), ThePirateBayProvider()]

@gen.coroutine
def search_metadata(query, api_key, num_results):
    url = ('http://ws.audioscrobbler.com/2.0/?method=track.search&track=' +
      urllib.quote(query.encode('utf8')) +
      '&api_key=' +  
      api_key +
      '&format=json')
    http_client = AsyncHTTPClient()
    response = yield http_client.fetch(url, raise_error=False)
    res = json.loads(response.body)['results']['trackmatches']
    if res == '\n':
      raise gen.Return([])
    tracks = res['track']
    if isinstance(tracks, dict):
        tracks = [tracks]
    track_data = []  
    for t in tracks: 
        if len(track_data) == num_results:
            break
        track = {'artist': t['artist'], 'title': t['name']}
        if 'image' in t.keys() and len(t['image']) > 0:
            track['image'] = {}
            for img in t['image']:
                track['image']['cover_url_' + img['size']] = img['#text']
        track_data.append(track)
    raise gen.Return(track_data)

def tnp_to_results(torrents_with_paths):
    ret = []
    for tnp in torrents_with_paths:
        torrent = tnp[0]
        for path in tnp[1]:
            ret.append({
                'info_hash': torrent['info_hash'].lower(),
                'magnet': torrent['magnet'] if ('magnet' in torrent.keys()) else None,
                'torrent_link': torrent['torrent_link'] if ('torrent_link' in torrent.keys()) else None,
                'path': path,
                'seeders': torrent['seeders'],
                'torrent_title': torrent['torrent_title']
            })
    return ret

#TODO: it would be nice to reduce the duplication, but coroutines make it hard

@gen.coroutine
def search_torrent(artist, title, provider_id):
    # select the provider
    provider = search_providers[provider_id]
    torrents_with_paths = []

    # initial guess: <artist> discography
    res = yield provider.search(artist.encode('utf8') + ' discography', artist, title)
    torrents_with_paths += res

    # backup plan: <artist>
    res = yield provider.search(artist.encode('utf8'), artist, title)
    torrents_with_paths += res

    raise gen.Return(tnp_to_results(torrents_with_paths))
