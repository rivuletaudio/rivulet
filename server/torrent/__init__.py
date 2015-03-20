__author__ = 'francis'

import libtorrent as lt
from Queue import Queue
from threading import Lock, Thread
import sys
import urllib2
import time
import json
import os
import base64
import errno
from tornado.httpclient import AsyncHTTPClient
from tornado.httpclient import HTTPRequest
from StringIO import StringIO
import gzip
from distutils.version import StrictVersion

DEFAULT_PRIVATE_DATA_PATH = '~/rivulet'
DEFAULT_TORRENT_DATA_PATH = "torrents"
DEFAULT_RESUME_DATA_PATH = 'resume_data'

DEFAULT_STORAGE_MODE = lt.storage_mode_t.storage_mode_sparse


def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else: raise

def get_torrent_info(th):
    version = '.'.join(lt.version.split('.')[:3])
    if StrictVersion(version) >= StrictVersion('1.0.2'):
        return th.torrent_file()
    else:
        return th.get_torrent_info()


# receives new torrent add requests on a queue and also listens on the libtorrent alerts
def session_thread(receive_queue, queue_poll_interval, torrents_by_hash, config, session_obj, session):
    # TODO make sure the torrent_handles are hashable
    def alert_to_torrent(alert):
        for torrent_handle, torrent in torrents.items():
            if torrent_handle == alert.handle:
                return torrent
        raise LibtorrentErrorException('Got alert for unknown torrent')

    def send_events(streamer_infos, alert):
        # Timeout
        # TODO: this code is unreachable
        if isinstance(alert, type(None)):
            for torrent in torrents:
                for si in streamer_infos:
                    si.time_waited += queue_poll_interval
                    if si.time_waited >= si.timeout:
                        err = "TorrentStream %d timed out waiting for data" % my_id
                        si.put(('kill', TorrentTimeoutException(err)))
        # Error
        elif alert.category() == lt.alert.category_t.error_notification:
            if isinstance(alert, lt.torrent_alert):
                torrent = alert_to_torrent(alert)
                # kill all streamers for this torrent
                for si in torrent.streamers.items().values():
                    si.put(('kill', LibtorrentErrorException(alert)))
            else:
                raise LibtorrentErrorException(alert)
        # Metadata
        elif isinstance(alert, lt.metadata_received_alert):
            torrent = alert_to_torrent(alert)
            for si in torrent.streamers:
                metadata = get_torrent_info(torrent.torrent_handle)
                print >> sys.stderr, 'XXXXXXXXMETADATA', metadata
                torrents_by_hash[str(metadata.info_hash())] = torrent.torrent_handle
                si.put(('metadata', metadata))
        # Data
        elif isinstance(alert, lt.read_piece_alert):
            print >> sys.stderr, 'received data', alert
            torrent = alert_to_torrent(alert)
            print >> sys.stderr, 'found streamers', torrent.streamers
            # TODO: figure out which streamer requested the piece and send the data only to that streamer
            for si in torrent.streamers:
                print >> sys.stderr, 'found streamer', si
                si.time_waited = 0
                # very important! duplicate the alert! Otherwise accessing the alert from another thread segfaults
                si.put(('data', {'piece': alert.piece, 'size': alert.size, 'buffer': alert.buffer[:]}))
        else:
            print >> sys.stderr, 'unknown alert', alert, type(alert), alert.category()

    root_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", os.path.expanduser(config.get('private_data_path', DEFAULT_PRIVATE_DATA_PATH)))
    resume_data_path = os.path.join(root_path, os.path.expanduser(config.get('resume_data_path', DEFAULT_RESUME_DATA_PATH)))
    mkdir_p(os.path.dirname(resume_data_path))
    session.listen_on(6881, 6891)
    session.set_alert_mask(lt.alert.category_t.status_notification)
    session.add_dht_router("dht.transmissionbt.com", 6881)
    session.add_dht_router("router.bittorrent.com", 6881)
    session.add_dht_router("router.utorrent.com", 6881)
    torrents = {}
    streamer_infos = {}

    # load resume data for each torrent if available
    try:
        with open(resume_data_path, 'r') as f:
            resume_data = json.load(f)
            for info_hash, resume_data in resume_data.items():
                params = session_obj.torrent_params_from_info_hash(info_hash)
                params['resume_data'] = base64.b64decode(resume_data)
                th = session.add_torrent(params)
                th.set_sequential_download(True)
                torrents_by_hash[str(get_torrent_info(th).info_hash())] = th
    except IOError:
        pass

    while True:
        # alert processing loop forever
        alert = session.wait_for_alert(queue_poll_interval)
        if alert:
          print >> sys.stderr, 'alert:', alert, type(alert), alert.category()
          send_events(streamer_infos, alert)
          session.pop_alert()
          #TODO: check if any recipients are done and remove them from the list


        # every X seconds or every alert check for requests from new callers
        if not receive_queue.empty():
            action, caller, data = receive_queue.get()
            print >> sys.stderr, 'action:', action, caller, data
            if action == 'subscribe_streamer':
                torrent_params, file_index_or_name, streamer_info = data
                streamer_infos[caller] = streamer_info

                #TODO check if this is safe to do on another thread so we can get rid of the queue
                torrent_handle = session.add_torrent(torrent_params)
                torrent_handle.set_sequential_download(True)

                # TODO: make this check work even if the metadata is not already available
                # if this torrent already exists, use the existing Torrent object instead of creating a new one
                torrent = None
                for th, t in torrents.items():
                    if torrent_handle == th:
                        torrent = t
                # we have to assume at first that this is a new torrent; if it turns out that it is not,
                # when we receive the alert telling us this, we merge it with the existing torrent
                if torrent is None:
                    torrent = Torrent(torrent_handle)
                torrents[torrent.torrent_handle] = torrent
                # this is done here so that metadata can be delivered to this streamer; the streamer removes itself
                torrent.add_streamer(streamer_info)

                # if the metadata is already available, there will be no event, so we have to do this here:
                torrent_info = None
                try:
                    torrent_info = get_torrent_info(torrent_handle)
                    torrents_by_hash[str(torrent_info.info_hash())] = torrent.torrent_handle
                except:
                    # and if the metadata is not available, it will come via an event
                    pass

                streamer_info.torrent = torrent
                streamer_info.put((torrent, torrent_info))

            elif action == 'unsubscribe_streamer':
                streamer_info = data
                last_user = streamer_info.torrent.remove_streamer(streamer_info)
                if last_user == True:
                    print >> sys.stderr, 'Torrent not needed any more, maybe we should remove it?'
                    del torrents_by_hash[str(get_torrent_info(streamer_info.torrent.torrent_handle).info_hash())]
                streamer_info.torrent = None

            elif action == 'quit':
                print 'shutting down gracefully and saving resume data'
                # go through each torrent and save their resume_data
                outstanding = 0
                for th, t in torrents.items():
                    if not th.is_valid():
                        continue
                    if not th.status().has_metadata:
                        continue
                    if not th.need_save_resume_data():
                        continue
                    th.save_resume_data(3)  # TODO: use the proper named flags
                    outstanding += 1

                save = {}
                try:
                    with open(resume_data_path, 'r') as old_f:
                        save = json.load(old_f)
                except IOError:
                    pass

                while outstanding > 0:
                    alert = session.wait_for_alert(10000) #wait extra long in this case
                    if not alert:
                        # give up if it times out
                        print 'timed out on shutdown'
                        break

                    if isinstance(alert, lt.save_resume_data_failed_alert):
                        print 'failed to save resume data'

                    elif isinstance(alert, lt.save_resume_data_alert):
                        th = alert.handle
                        hsh = str(get_torrent_info(th).info_hash())
                        # Sorry. If you feel like improving this, be my guest, but I didn't want to deal with it
                        save[hsh] = base64.b64encode(lt.bencode(alert.resume_data))

                    session.pop_alert()
                    outstanding -= 1

                print 'dumping resume_data'
                with open(resume_data_path, 'w') as f:
                    json.dump(save, f)
                print 'dumped resume_data'
                return
            else:
                raise Exception('WTF')

class Session:
    #TODO: make the methods that access torrent data work with a cached version instead of making
    # blocking calls to libtorrent for data; if libtorrent is busy it'll take a long time to respond
    # and block our server
    def __init__(self, config, queue_poll_interval = 100):
        self.receive_queue = Queue()
        self._torrents_by_hash = {}
        self._session = lt.session()
        #TODO: refactor this interface maybe
        #TODO: libtorrent is not very explicit about what is or isn't thread safe, so figure that out...
        self._session_thread = Thread(target = session_thread, args=[self.receive_queue, queue_poll_interval, self._torrents_by_hash, config, self, self._session])
        self._session_thread.start()
        self.root_path = os.path.join(os.path.abspath(os.path.dirname(__file__)), "..", "..", os.path.expanduser(config.get('private_data_path', DEFAULT_PRIVATE_DATA_PATH)))
        self.torrent_data_path = os.path.join(self.root_path, os.path.expanduser(config.get('torrent_data_path', DEFAULT_TORRENT_DATA_PATH)))
        mkdir_p(self.torrent_data_path)

        self._next_id_lock = Lock()
        self._next_id = 0

    def get_next_id(self):
        self._next_id_lock.acquire()
        my_id = self._next_id
        self._next_id += 1
        self._next_id_lock.release()
        return my_id

    def torrents_status(self, detailed):
        torrents = self._session.get_torrents()
        torrent_statuses = []
        for th in torrents:
            ts = th.status()
            pieces = ts.pieces
            ti = get_torrent_info(th)
            torrent_status = {}
            torrent_status['state'] = str(lt.torrent_status.states.values[ts.state])
            torrent_status['download_rate'] = ts.download_rate
            torrent_status['upload_rate'] = ts.upload_rate
            torrent_status['progress'] = round(ts.progress * 100, 2)
            torrent_status['peers'] = ts.num_peers
            torrent_status['num_pieces'] = ts.num_pieces
            torrent_status['num_complete'] = ts.num_complete
            torrent_status['files'] = []
            if ti == None:
                continue
            info_hash = str(ti.info_hash())
            torrent_status['total_done'] = round(float(ts.total_done) / ti.total_size() * 100, 2)
            torrent_status['info_hash'] = info_hash
            torrent_status['name'] = ti.name()
            if not detailed:
                torrent_statuses.append(torrent_status)
                continue
            for index in range(ti.num_files()):
                file_status = {}
                file_ = ti.file_at(index)

                path = file_.path.decode(sys.getfilesystemencoding())
                file_status['path'] = path

                file_status['requested'] = th.file_priority(index) != 0

                file_size = file_.size
                start = ti.map_file(index, 0, 0)
                # I don't know why we need -1; we shouldn't need it.
                end = ti.map_file(index, file_size-1, 0)

                file_status['pieces'] = pieces[start.piece:end.piece+1]

                torrent_status['files'].append(file_status)
            torrent_statuses.append(torrent_status)
        return torrent_statuses

    def available_sources(self):
        torrents = self._session.get_torrents()
        sources = {}
        for th in torrents:
            ts = th.status()
            pieces = ts.pieces
            ti = get_torrent_info(th)
            if ti == None:
                continue
            info_hash = str(ti.info_hash())
            for index in range(ti.num_files()):
                file_ = ti.file_at(index)

                #XXX: hack number two: case insensitive matching because kickass.to messes with the case
                path = file_.path.decode(sys.getfilesystemencoding()).lower()
                #XXX: hack to match filenames when torrent name is prepended TODO: figure out when it is and when it isn't
                path2 = '/'.join(path.split('/')[1:])

                file_size = file_.size
                start = ti.map_file(index, 0, 0)
                # I don't know why we need -1; we shouldn't need it.
                end = ti.map_file(index, file_size-1, 0)

                if reduce(lambda a,b: a and b, pieces[start.piece:end.piece+1], True):
                    if info_hash not in sources.keys():
                        sources[info_hash] = {}
                    sources[info_hash][path] = True
                    sources[info_hash][path2] = True
        return sources

    def status(self, info_hash, path):
        info_hash = info_hash.lower()
        if info_hash in self._torrents_by_hash.keys():
            torrent_handle = self._torrents_by_hash[info_hash]
            torrent_status = torrent_handle.status()
            torrent_info = get_torrent_info(torrent_handle)
            if torrent_info is None:
                # assume we are not downloading this file if we don't have metadata
                return {'status': torrent_status, 'progress': 0, 'pieces': [], 'requested': False}
            start_piece, end_piece = self._get_piece_range(torrent_handle, torrent_status, torrent_info, path)
            pieces = self._get_pieces(torrent_status, torrent_info, path, start_piece, end_piece)
            progress = self._get_progress(torrent_status, torrent_info, path, start_piece, end_piece)
            requested = self._get_requested(torrent_handle, torrent_status, torrent_info, path, start_piece, end_piece)
            return {'status': torrent_status, 'progress': progress, 'pieces': pieces, 'requested': requested}
        else:
            return None

    def _get_piece_range(self, torrent_handle, torrent_status, torrent_info, file_name):
        file_index = filename_to_file_index(torrent_info, file_name)
        file_ = torrent_info.file_at(file_index)
        file_size = file_.size

        start = torrent_info.map_file(file_index, 0, 0)
        # I don't know why we need -1; we shouldn't need it.
        end = torrent_info.map_file(file_index, file_size-1, 0)

        return (start.piece, end.piece)

    def _get_progress(self, torrent_status, torrent_info, file_name, start, end):
        pieces = torrent_status.pieces
        file_index = filename_to_file_index(torrent_info, file_name)
        file_ = torrent_info.file_at(file_index)

        n = 0
        for i in range(start, end+1):
            if pieces[i]:
                n += 1
        return float(n) / (end - start + 1)

    def _get_pieces(self, torrent_status, torrent_info, file_name, start, end):
        pieces = torrent_status.pieces
        file_index = filename_to_file_index(torrent_info, file_name)
        file_ = torrent_info.file_at(file_index)
        
        return pieces[start:end+1]

    def _get_requested(self, torrent_handle, torrent_status, torrent_info, file_name, start, end):
        # is this file being downloaded?
        file_index = filename_to_file_index(torrent_info, file_name)
        if torrent_handle.file_priority(file_index) == 0:
            return False
        return True

    def quit(self):
        self.receive_queue.put(('quit', None, None))

    # We need to know the info_hash before adding any torrents. This is
    # because otherwise we can't know which torrents are duplicates because
    # libtorrent is a piece of shit in python

    def torrent_params_from_torrent_file(self, file_path):
        # TODO: handle file read errors
        buf = ''
        with open(file_path, "rb") as f:
            buf = f.read()
        torrent_info = bytes_to_ti(buf)

        return {
            "storage_mode": DEFAULT_STORAGE_MODE,
            "source_feed_url": "",
            "ti": torrent_info,
            "url": "",
            "info_hash": ti_to_hash(torrent_info),
            "save_path": self.torrent_data_path,
            "trackers": [],
            "uuid": "",
            "dht_nodes": []
        }

    def torrent_params_from_magnet_link(self, mag_link):
        res = lt.parse_magnet_uri(mag_link)
        # DAMN YOU LIBTORRENT
        res['info_hash'] = hex_to_hash(str(res['info_hash']).decode('hex'))

        res["save_path"] = self.torrent_data_path
        return res

    def torrent_params_from_info_hash(self, info_hash_str):
        return {
            "storage_mode": DEFAULT_STORAGE_MODE,
            "source_feed_url": "",
            "ti": None,
            "url": "",
            "info_hash": hex_to_hash(info_hash_str.decode("hex")),
            "save_path": self.torrent_data_path,
            "trackers": [],
            "uuid": "",
            "dht_nodes": []
        }

    def torrent_params_from_torrent_url(self, torrent_url, on_result):
        http_client = AsyncHTTPClient()
        print 'requesting torrent file from', torrent_url
        request = HTTPRequest(torrent_url)

        def on_data(res):
            if (res.error):
                raise res.error

            torrent_info = bytes_to_ti(res.body)
            on_result({
                "storage_mode": DEFAULT_STORAGE_MODE,
                "source_feed_url": "",
                "ti": torrent_info,
                "url": '',
                "info_hash": ti_to_hash(torrent_info),
                "save_path": self.torrent_data_path,
                "trackers": [],
                "uuid": "",
                "dht_nodes": []
            })

        http_client.fetch(request, callback=on_data)


class StreamerInfo:
    def __init__(self, my_id, is_downloader=False):
        self.is_downloader = is_downloader
        self.my_id = my_id
        self.queue = Queue()
        self.torrent = None
        self.time_waited = 0

    def get(self):
        return self.queue.get()

    def put(self, data):
        if not self.is_downloader:
            self.queue.put(data)


class Torrent:
    def __init__(self, torrent_handle):
        self.torrent_handle = torrent_handle
        # dictionary from file id to number of times requested
        self.files_requested = {}
        # dictionary from streamer to file requested or None if no file was requested yet
        self.streamers = {}

    def merge(self, torrent):
        for k, v in torrent.files_requested:
            self.files_requested[k] = self.files_requested.get(k, 0) + v
        for s, f in torrent.streamers:
            if self.streamers[s] != None:
                raise Exception("Trying to merge with a torrent that has some of the same streamers: undefined behaviour")
            self.streamers[s] = f

    # in these methods streamer refers to streamer_info
    def add_streamer(self, streamer):
        self.streamers[streamer] = None

    def streamer_request_file(self, streamer, index):
        if self.streamers[streamer] != None:
            raise Exception("A TorrentStream has requested  more than one file.")
        self.streamers[streamer] = index
        self.files_requested[index] = self.files_requested.get(index, 0) + 1
        self._set_priorities()

    def remove_streamer(self, streamer):
        index = self.streamers[streamer]
        if index == None:
            return len(self.files_requested) == 0
        self.files_requested[index] = self.files_requested.get(index, 0) - 1
        if self.files_requested[index] < 0:
            raise Exception("Removed a streamer more times than it was added.")
        del self.streamers[streamer]
        self._set_priorities()
        return len(self.files_requested) == 0

    def _set_priorities(self):
        arr = [(0 if 0 == self.files_requested.get(x, 0) else 7) for x in range(get_torrent_info(self.torrent_handle).num_files())]
        print arr
        self.torrent_handle.prioritize_files(arr)


# uses a torrent_info object to do buffer operations correctly
class BufferThing:
    def __init__(self, torrent_info, file_index, start_offset, end_offset):
        self._torrent_info = torrent_info
        self._file_index = file_index
        self._piece_length = self._torrent_info.piece_length()
        self._file = self._torrent_info.file_at(self._file_index)
        if end_offset is not None and end_offset <= self._file.size:
            self._file_length = end_offset
        else:
            self._file_length = self._file.size
        if start_offset > self._file_length:
            raise Exception('Invalid start offset')
        self._first_piece, self._first_piece_start = self._file_byte_to_piece_and_byte(0)
        self._last_piece, self._last_piece_end = self._file_byte_to_piece_and_byte(self._file_length)
        self._num_pieces = self._last_piece - self._first_piece + 1

        self._start_offset = start_offset
        self._current_piece = self._file_byte_to_piece_and_byte(start_offset)[0]
        self._current_piece_offset = self._file_byte_to_piece_and_byte(start_offset)[1]
        self.done = False

    def accept_piece(self, alert):
#        for f in self._torrent_info.files():
#            print >> sys.stderr, f.offset, f.size
        print >> sys.stderr, self.__dict__
        if alert['piece'] == self._current_piece:
            if alert['size'] != 0:
                # handle the final piece
                if self._current_piece == self._last_piece:
                    self.done = True
                    ret = alert['buffer'][self._current_piece_offset:self._last_piece_end]
                # handle a first or middle piece
                else:
                    ret = alert['buffer'][self._current_piece_offset:]

                self._current_piece += 1
                if self._current_piece_offset != 0:
                    self._current_piece_offset = 0

                return ret
            else:
                # the first time we receive a piece it 'fails', so we just ignore it
                raise FailedPieceException()
        else:
            raise NotMyPieceException()


    def _file_byte_to_piece_and_byte(self, byte):
        prq = self._torrent_info.map_file(self._file_index, byte, 0)
        return (prq.piece, prq.start)

class InvalidFileIndexException(Exception):
    pass


class TorrentTimeoutException(Exception):
    pass


class LibtorrentErrorException(Exception):
    def __init__(self, error):
        self.error = error

# takes a session, a torrent to stream and an offset and returns pieces of it as you call data()
class TorrentStream:

    #TODO: stop command
    #TODO: wire up timeout
    def __init__(self, session, torrent_params, file_index_or_name, start_offset=0, end_offset=None, timeout=0, stream=True):
        print >> sys.stderr, 'Starting torrent with bounds:', start_offset, end_offset
        if not "save_path" in torrent_params:
            err = "Invalid torrent_params passed to TorrentStream. " \
                  "torrent_params dict should contain save_path entry."
            raise RuntimeError(err)

        if not "url" in torrent_params and not "info_hash" in torrent_params and not "ti" in torrent_params:
            err = "Invalid torrent_params passed to TorrentStream. " \
                  "torrent_params dict should contain save_path entry " \
                  "as well as one of url, info_hash, or ti entries. " \
                  "These represent the url of a torrent file, the " \
                  "info_hash of a torrent, or a torrent_info object. " \
                  "Use torrent.torrent_params_from_X to get this information"
            raise RuntimeError(err)

        if not isinstance(file_index_or_name, int) and not isinstance(file_index_or_name, str) and not isinstance(file_index_or_name, unicode):
            err = "Invalid type of file_index_or name passed to Stream(). " \
                  "Expected unicode, str or int. Got %s" % type(file_index_or_name).__name__
            raise RuntimeError(err)
        self._stream = stream
        self._file_index_or_name = file_index_or_name
        self._session = session
        self._start_offset = start_offset
        self._end_offset = end_offset

        self.my_id = self._session.get_next_id()
        self._streamer_info = StreamerInfo(self.my_id, (not stream))
        self._torrent_info = None

        self._session.receive_queue.put(("subscribe_streamer", self.my_id, (torrent_params, file_index_or_name, self._streamer_info)))
        # mainly for synchronization because add_torrent is blocking
        self.torrent, torrent_info = self._streamer_info.get()
        self._torrent_handle = self.torrent.torrent_handle
        if not self._torrent_handle.is_valid():
            raise RuntimeError("Invalid torrent handle in TorrentStream")

        self.state = 'new'

        if torrent_info:
            self._populate_info_from_metadata(torrent_info)
        elif 'ti' in torrent_params and torrent_params['ti'] is not None:
            self._populate_info_from_metadata(torrent_params['ti'])
        else:
            # TODO: not sure if this case is possible
            # in this case we might already have fetched the metadata and we won't get an event for it
            try:
                torrent_info = self._torrent_handle.get_torrint_info()
                self._populate_info_from_metadata(torrent_info)
            except:
                # else it will start to fetch it, the session will receive and queue it and the first data() call will get it from the session
                pass

    def _populate_info_from_metadata(self, torrent_info):
        self._torrent_info = torrent_info

        self._populate_file_index_and_name()
        self._buffer_thing = BufferThing(torrent_info, self._file_index, self._start_offset, self._end_offset)

        self.torrent.streamer_request_file(self._streamer_info, self._file_index)

        # Start streaming data
        self._request_current_piece()

        self.state = 'started'

    def _populate_file_index_and_name(self):
        file_index_or_name = self._file_index_or_name

        if isinstance(file_index_or_name, int):
            self._file_index = file_index_or_name
            self._file_name = self._torrent_info.file_at(self._file_index).path

            if self._file_index >= self._torrent_info.num_files():
                err = "Invalid file index, %d, passed to TorrentStreamer.stream()" % self._file_index
                raise InvalidFileIndexException(err)

        elif isinstance(file_index_or_name, str) or isinstance(file_index_or_name, unicode):
            self._file_name = file_index_or_name
            self._file_index = filename_to_file_index(self._torrent_info, self._file_name)
        else:
            raise Exception('impossible')


    def _request_current_piece(self):
        # "If the piece is already downloaded when this call is made, nothing happens, unless the alert_when_available flag is set, in which case it will do the same thing as calling read_piece() for index."
        # TODO set the time to a useful guess about how many ms from now we'll need the piece
        if self._stream:
            print >> sys.stderr, 'request current piece', self._buffer_thing._current_piece
            start = self._buffer_thing._current_piece
            for i in range(start, self._buffer_thing._last_piece+1):
                flags = lt.deadline_flags.alert_when_available if i == self._buffer_thing._current_piece else 0
                self._torrent_handle.set_piece_deadline(i, i-start+1, flags)

    def data(self):
        if self._torrent_info is not None:
            yield ('metadata', {'ti': self._torrent_info, 'file_index': self._file_index})
        # this loops for pieces received, metadata, error pieces, etc.
        while True:
            if self.state == 'terminating':
                return
            elif self.state != 'new' and self._buffer_thing.done:
                # done streaming, tell the session that we are done and quit
                self._session.receive_queue.put(("unsubscribe_streamer", self.my_id, self._streamer_info))
                #TODO if we haven't already, tell the session to clean us up (remove the torrent if necessary)
                #TODO unset any deadlines we've set on our torrent
                self.state = 'terminating'
                return 

            print >> sys.stderr, "getting event..."
            kind, data = self._streamer_info.get()
            print >> sys.stderr, "got event for", self.my_id, kind

            if kind == 'metadata':
                self._populate_info_from_metadata(data)
                yield ('metadata', {'ti': self._torrent_info, 'file_index': self._file_index})
            elif kind == 'kill':
                self.torrent.remove_streamer(self, self._file_index)
                raise data
            elif kind == 'data':
                try:
                    result = self._buffer_thing.accept_piece(data)
                    print >> sys.stderr, 'done', self._buffer_thing.done
                    if not self._buffer_thing.done:
                        self._request_current_piece()
                    yield ('data', result)
                except FailedPieceException, e:
                    self._request_current_piece()
                    pass
                except NotMyPieceException, e:
                    pass

class InvalidTorrentParamsException(Exception):
    pass


class FailedPieceException(Exception):
    pass

class NotMyPieceException(Exception):
    pass

def filename_to_file_index(torrent_info, file_name):
    # no leading slash in filename plox
    if len(file_name) > 0 and file_name[0] == '/':
      file_name = file_name[1:]

    if file_name != "":
        for i in range(torrent_info.num_files()):
            f = torrent_info.file_at(i)
            path = f.path.decode(sys.getfilesystemencoding())
            path_elements = path.split('/')
            #XXX: hack to match filenames when torrent name is prepended TODO: figure out when it is and when it isn't
            #XXX: hack number two: case insensitive matching because kickass.to messes with the case
            if path.lower() == file_name.lower() or file_name.lower() == ('/'.join(path_elements[1:])).lower():
                return i
    raise RuntimeError("Invalid file name specified")

def get_torrent_status(torrent_handle):
    state_str = ['queued', 'checking', 'downloading metadata',
                 'downloading', 'finished', 'seeding', 'allocating',
                 'checking resume data']
    s = torrent_handle.status()
    return '%.2f%% complete (down: %.1f kb/s up: %.1f kB/s peers: %d) %s' % \
           (s.progress * 100, s.download_rate / 1000, s.upload_rate / 1000,
           s.num_peers, state_str[s.state])


def get_file_names(torrent_params):
    if "save_path" not in torrent_params:
        raise InvalidTorrentParamsException(
            "Invalid torrent params passed to torrent.get_file_names(params")

    if "ti" in torrent_params and torrent_params["ti"] is not None:
        info = lt.torrent_info(torrent_params["ti"])
    elif "url" in torrent_params and torrent_params["url"] is not "":
        info = lt.torrent_info(torrent_params["url"])
    elif "info_hash" in torrent_params and torrent_params["info_hash"] is not None:
        info = lt.torrent_info(torrent_params["info_hash"])
    else:
        raise InvalidTorrentParamsException(
            "Invalid torrent params passed to torrent.get_file_names(params")
    return info.files()

def hash_is_bytes():
    version = '.'.join(lt.version.split('.')[:3])
    if StrictVersion(version) >= StrictVersion('0.16.19') and\
        StrictVersion(version) < StrictVersion('1.0.0') or\
        StrictVersion(version) >= StrictVersion('1.0.3'):
        return True
    return False

def constructor_is_new():
    version = '.'.join(lt.version.split('.')[:3])
    if StrictVersion(version) >= StrictVersion('0.16.19') and\
        StrictVersion(version) < StrictVersion('1.0.0') or\
        StrictVersion(version) >= StrictVersion('1.0.2'):
        return True
    return False

def hex_to_hash(hex_):
    if hash_is_bytes():
        return hex_
    else:
        return lt.big_number(hex_)


def ti_to_hash(ti):
    if hash_is_bytes():
        return str(ti.info_hash()).decode('hex')
    else:
        return ti.info_hash()

def bytes_to_ti(bytes_):
    if constructor_is_new():
        return lt.torrent_info(bytes_, len(bytes_), 0)
    else:
        return lt.torrent_info(lt.bdecode(bytes_))

