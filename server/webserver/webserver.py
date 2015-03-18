from tornado.web import RequestHandler, Application, url
from tornado.ioloop import IOLoop
from tornado.web import gen
import json
import sys
import os
import tornado
from tornado.web import gen
from tornado.web import asynchronous
import threading
import thread
import traceback
import yaml
import argparse
sys.path.append(
    os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", ".."))
from server import torrent
from server import search
from server.audiotranscode import AudioTranscode

#TODO: make this work on more operating systems?
if 'XDG_CONFIG_HOME' in os.environ.keys():
    config_dir = os.environ['XDG_CONFIG_HOME']
else:
    config_dir = os.path.join(os.environ['HOME'], '.config')
try:
    f = open(os.path.join(config_dir, 'rivulet', 'config.yaml'))
except:
    f = open(os.path.join(os.path.abspath(os.path.dirname(__file__)), 'config.yaml'))

config = yaml.safe_load(f)
f.close()

session = torrent.Session(config)


class HelloHandler(RequestHandler):
    def get(self):
        with open(os.path.join(os.path.dirname(__file__), './public/index.html')) as f:
            self.write(f.read())


class StreamWorker(threading.Thread):
    def __init__(self, tparams, path, done_cb=None, data_cb=None, error_cb=None, length_cb=None, start=0, end=None, *args, **kwargs):
        super(StreamWorker, self).__init__(*args, **kwargs)
        self.tparams = tparams
        self.path = path
        self.done_cb = done_cb
        self.data_cb = data_cb
        self.error_cb = error_cb
        self.length_cb = length_cb
        self.start_offset = start
        self.end_offset = end
        

    def is_flac(self, filename):
        return filename.endswith(".flac")
    
    def run(self):
        audiotranscoder = AudioTranscode()
        try:
            print "About to start stream:", self.path
            stream = torrent.TorrentStream(session, self.tparams, self.path, self.start_offset, self.end_offset)
            print "Starting stream:", self.path

            def process_data(kind, data):
                if kind == 'data':
                    if not self.data_cb(data):
                        print "browser gave up"
                        #stream.stop()
                        self.done_cb()
                        return True
                    else:
                        return False
                else:
                    raise Error("Unexpected result from generator. Expected data.")
                return False
                    

            # We need to way for metadata before we can get the filename to check if it's flac
            gen = stream.data()
            kind, metadata = gen.next()
            if kind != 'metadata':
                raise Error("Unexpected result from generator. Expected metadadata.")

            if self.is_flac(stream._file_name):
                for kind, data in audiotranscoder.transcode_stream_from_generator(gen, 'flac', 'mp3'):
                    if process_data(kind, data):
                        return
            else:
                filesize = metadata['ti'].file_at(metadata['file_index']).size
                print "filesize", filesize
                self.length_cb(filesize)

                for kind, data in gen:
                    if process_data(kind, data):
                        return


            print "Done streaming:", self.path
            self.done_cb()
        except Exception as e:
            self.error_cb(e)


class PlayHandler(RequestHandler):
    # ?[torrent_link= and/or magnet= and/or info_hash=]&path=
    @asynchronous
    def get(self):
        #TODO: don't assume mp3?
        self.set_header('Content-Type', 'audio/mpeg')
        self.set_header('Accept-Ranges', 'bytes')
        torrent_link = self.get_argument('torrent_link', None)
        infohash = self.get_argument('info_hash', None)
        magnet = self.get_argument('magnet', None)
        if torrent_link is None and infohash is None and magnet is None:
            self.set_status(400)
            self.finish()
            return
        #Range:bytes=657748-
        start = 0
        end = None
        if 'Range' in self.request.headers.keys():
            range_str = self.request.headers['Range'][6:]
            range_parts = range_str.split('-')
            start = int(range_parts[0])
            try:
                end = int(range_parts[1])
            except ValueError:
                end = None
        if start == 0 and end is None:
            self.set_status(200) #the whole file
        else:
            self.set_status(206) #partial content
        path = self.get_argument('path')
        self.start_offset = start
        self.end_offset = end
        try:
            tparams = None
            if torrent_link is not None:
                # TODO: fix this blocking network call
                tparams = session.torrent_params_from_torrent_url(torrent_link)
            elif magnet is not None:
                tparams = session.torrent_params_from_magnet_link(magnet)
            elif infohash is not None:
                tparams = session.torrent_params_from_info_hash(infohash)
            StreamWorker(tparams, path, self.on_done, self.on_data, self.on_error, self.on_length, start, end).start()
        except Exception as e:
            self.on_error(e)

    def on_length(self, length):
        end = length-1
        if self.end_offset is not None:
            end = self.end_offset
        self.set_header('Content-Range', 'bytes '+str(self.start_offset)+'-'+str(end)+'/'+str(length))
        content_length = length - self.start_offset
        if self.end_offset is not None:
            content_length = self.end_offset - self.start_offset
        self.set_header('Content-Length', content_length)
        self.flush()

    def on_data(self, data):
        self.write(data)
        self.flush()
        return not self.request.connection.stream.closed()

    def on_done(self):
        if not self.request.connection.stream.closed():
            self.finish()

    def on_error(self, e):
        print traceback.format_exc(e)
        self.set_status(500)
        self.finish()


class DownloadHandler(RequestHandler):
    # ?[torrent_link= and/or magnet= and/or info_hash=]&path=
    def get(self):
        torrent_link = self.get_argument('torrent_link', None)
        infohash = self.get_argument('info_hash', None)
        magnet = self.get_argument('magnet', None)
        if torrent_link is None and infohash is None and magnet is None:
            self.set_status(400)
            self.finish()
            return

        self.set_status(200) #the whole file
                
        path = self.get_argument('path')

        # We don't need to create a StreamWorker in a seperate thread, just add a TorrentStream
        try:
            tparams = None
            if torrent_link is not None:
                # TODO: fix this blocking network call
                tparams = session.torrent_params_from_torrent_url(torrent_link)
            elif magnet is not None:
                tparams = session.torrent_params_from_magnet_link(magnet)
            elif infohash is not None:
                tparams = session.torrent_params_from_info_hash(infohash)
            #TODO: unicode safety
            try:
                print "About to start download:", path

                thread.start_new_thread(lambda: torrent.TorrentStream(session, tparams, path, 0, None, False), ())

            except Exception as e:
                self.on_error(e)
        except Exception as e:
            self.on_error(e)
        self.write(json.dumps({"status": "ok"}))
        self.finish()

    def on_error(self, e):
        print traceback.format_exc(e)
        self.set_status(500)
        self.finish()

        
class StatusHandler(RequestHandler):
    # ?info_hash=&path=
    def get(self):
        import random
        info_hash = self.get_argument('info_hash', None)
        path = self.get_argument('path', None)
        if info_hash is None:
            self.write(json.dumps({'status': 'error'}))
        else:
            status = session.status(info_hash, path)
            if status:
                self.write(json.dumps({'status': 'ok', 'result': {'state': 'downloading', 'size': 100, 'progress': status['progress'], 'pieces': status['pieces'], 'requested': status['requested'], 'peers': random.randrange(10), 'up_speed': random.randrange(10000), 'down_speed': random.randrange(10000)}}))
            else:
                self.write(json.dumps({'status': 'ok', 'result': {'state': 'nothing', 'progress': 0, 'pieces': []}}))
        self.finish()


class TorrentsStatusHandler(RequestHandler):
    # ?detailed=true
    def get(self):
        detailed = self.get_argument('detailed', False)
        status = session.torrents_status(detailed)
        self.write(json.dumps({'status': 'ok', 'result': status}))
        self.finish()


class AvailableSourcesHandler(RequestHandler):
    def get(self):
        status = session.available_sources()
        self.write(json.dumps({'status': 'ok', 'result': status}))
        self.finish()


class SearchHandler(RequestHandler):
    api_key = config.get('lastfm_api_key', '112bceb16f3441a10fc4b4694548372f')
    search_results_max = config.get('search_results_per_page', 20)

    # ?q=
    @gen.coroutine
    def get(self):
        print 'search'
        query = self.get_argument('q')
        try:
            results = yield search.search_metadata(query, SearchHandler.api_key, SearchHandler.search_results_max)
        except Exception as e:
            # Network is down if errno is -1
            if 'errno' in dir(e) and e.errno != -2:
                print traceback.format_exc(e)
            if 'errno' in dir(e):
                self.write(json.dumps({"status": "error", "error": e.strerror}))
                self.finish()
                return
            print traceback.format_exc(e)
            self.write(json.dumps({"status": "error", "error": e.message}))
            self.finish()
            return
        self.write(json.dumps({"status": "ok","result": results}))
        self.finish()

class SourcesHandler(RequestHandler):
    search_results_max = 10

    # ?artist=&title=&provider_id=
    @gen.coroutine
    def get(self):
        print 'sources'
        artist = self.get_argument('artist')
        title = self.get_argument('title')
        provider_id = int(self.get_argument('provider_id'))
        try:
            results = yield search.search_torrent(artist, title, provider_id)
        except Exception as e:
            # Network is down if errno is -1
            if 'errno' in dir(e) and e.errno != -2:
                print traceback.format_exc(e)
            if 'errno' in dir(e):
                self.write(json.dumps({"status": "error", "error": e.strerror}))
                self.finish()
                return
            print traceback.format_exc(e)
            self.write(json.dumps({"status": "error", "error": e.message}))
            self.finish()
            return
        self.write(json.dumps({"status": "ok","result": results}))
        self.finish()

def make_app():
    return Application([
        url(r'/static/(.*)', tornado.web.StaticFileHandler, {'path': os.path.join(os.path.dirname(__file__), './public/static')}),
        url(r"/", HelloHandler),
        url(r"/search", SearchHandler),
        url(r"/sources", SourcesHandler),
        url(r"/play", PlayHandler),
        url(r"/status", StatusHandler),
        url(r"/torrents_status", TorrentsStatusHandler),
        url(r"/available_sources", AvailableSourcesHandler),
        url(r"/download", DownloadHandler)
        ])

if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument("-p", "--port", help="port number to bind to", type=int, default=9074)
    parser.add_argument("--host", help="host/ip to bind to", default='127.0.0.1')
    args = parser.parse_args()


    app = make_app()
    app.listen(args.port, args.host)
    print "Listening on port", args.port
    try:
        IOLoop.current().start()
    except KeyboardInterrupt, e:
        session.quit()
        raise e

