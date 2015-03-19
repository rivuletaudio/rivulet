from tornado.web import gen
import re

re_prepositions = r'((\ba\b|\bthe\b)\s*)|(\s*\ba\b|\bthe\b)'
re_splitter = re.compile(r'[\W_]+')

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

class TorrentSearchProvider:
    pfx_len = len('magnet:?xt=urn:btih:')
    hash_len = 40

    def __init__(self):
        self.search_cache = {}
        self.file_cache = {}

    @gen.coroutine
    def search(self, query, artist, title):
        torrents_with_paths = []

        torrents = []

        # fist check the cache for the torrent
        if self.search_cache.has_key(query):
            torrents = self.search_cache[query]
        else:
            response = yield self.search_torrent(query)

            # parse initial search results
            torrents = self.parse_search(response, artist)

            self.search_cache[query] = torrents

        while len(torrents) > 0:
            torrent = torrents.pop(0)

            paths = []

            # first check the cache for the list of paths for this torrent
            info_link = torrent['info_link']
            if self.file_cache.has_key(info_link):
                paths = self.file_cache[info_link]
            else:
                # get the file listings for the torrent
                response = yield self.file_list(info_link)
                # find the song in the file list
                paths = parse_file_list_and_find_paths(self, response, title)

                self.file_cache[info_link] = paths

            if len(paths) > 0:
                torrents_with_paths.append((torrent, paths))
                # we don't need more than one source torrent
                break

        raise gen.Return(torrents_with_paths)

    def search_torrent(self, query):
        raise NotImplemented()

    def parse_search(self, response, artist):
        raise NotImplemented()

    def file_list(self, torrent):
        raise NotImplemented()

    def parse_file_list(self, response):
        raise NotImplemented()
