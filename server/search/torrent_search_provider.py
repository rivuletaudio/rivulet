class TorrentSearchProvider:
    pfx_len = len('magnet:?xt=urn:btih:')
    hash_len = 40

    def search(query):
        raise NotImplemented()

    def parse_result(results):
        raise NotImplemented()
