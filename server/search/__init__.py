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

re_prepositions = r'((\ba\b|\bthe\b)\s*)|(\s*\ba\b|\bthe\b)'
re_splitter = re.compile(r'[\W_]+')

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

def remove_prepositions(text):
    return re.sub(re_prepositions, '', text, flags=(re.IGNORECASE & re.UNICODE))

def clean_path(path):
    path = path.split('/')[-1].lower()
    # kill extension
    if '.' in path:
        path = '.'.join(path.split('.')[:-1])
    # kill track numbers
    path = re.sub(r'^[0-9]+\W+', '', path)
    return path

# A is the superset, B is the subset
def match_fraction(a, b):
    As = set(re_splitter.split(a))
    Bs = set(re_splitter.split(b))
    return float(len(As.intersection(Bs))) / len(As.union(Bs))

def exact_match(file_list, title):
    for f in file_list:
        if title == clean_path(f):
            return [f]
    return []

def all_words_match(file_list, title):
    for f in file_list:
        filename = clean_path(f)
        if match_fraction(filename, title) == 1:
            return [f]
    return []

def all_words_no_prep_match(file_list, title):
    title = remove_prepositions(title)
    for f in file_list:
        filename = remove_prepositions(clean_path(f))
        if match_fraction(filename, title) == 1:
            return [f]
    return []

def best_effort_match(file_list, title):
    # now we have to give up and guess by the highest overlap between words
    # TODO: there's probably a more pythonic way to do this
    best_file = None
    best_score = 0
    for f in file_list:
        filename = remove_prepositions(clean_path(f))
        frac = match_fraction(filename, title)
        if frac > best_score:
            best_file = f
            best_score = frac

    if best_score > 0:
        return [best_file]
    return []

def dedup(seq): 
    noDupes = []
    [noDupes.append(i) for i in seq if not noDupes.count(i)]
    return noDupes

#TODO: extension filtering
def file_list_search(file_list, title):
    title = title.lower()
    return dedup(
        exact_match(file_list, title) +
        all_words_match(file_list, title) +
        all_words_no_prep_match(file_list, title) +
        best_effort_match(file_list, title)
    )

def parse_file_list_and_find_paths(provider, response, title):
    # parse file lists
    file_list = provider.parse_file_list(response)
    # find the song in the file list
    return file_list_search(file_list, title.lower())

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

    # Attempt #1

    # initial guess: <artist> discography
    response = yield provider.search(artist.encode('utf8') + ' discography')

    # parse initial search results
    torrents = provider.parse_search(response, artist)
    torrents_with_paths = []

    while len(torrents) > 0:
        torrent = torrents.pop(0)

        # get the file listings for the torrent
        response = yield provider.file_list(torrent)
        # find the song in the file list
        paths = parse_file_list_and_find_paths(provider, response, title)

        if len(paths) > 0:
            torrents_with_paths.append((torrent, paths))
            # we don't need more than one source torrent
            break

    # we don't need more than one source torrent
    if len(torrents_with_paths) > 0:
        raise gen.Return(tnp_to_results(torrents_with_paths))

    # Attempt #2

    # backup plan: <artist>
    response = yield provider.search(artist.encode('utf8'))

    # parse the backup search results
    torrents = provider.parse_search(response, artist)

    # give up if we can't even find any torrents for the artist
    if len(torrents) == 0:
        raise gen.Return([])

    while len(torrents):
        torrent = torrents.pop(0)

        # get the file listings for the torrent
        response = yield provider.file_list(torrent)
        # find the song in the file list
        paths = parse_file_list_and_find_paths(provider, response, title)

        if len(paths) > 0:
            torrents_with_paths.append((torrent, paths))
            # we don't need more than one source torrent
            break

    raise gen.Return(tnp_to_results(torrents_with_paths))
