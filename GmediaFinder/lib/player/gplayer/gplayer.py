# -*- coding:utf-8 -*-

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

from __future__ import print_function

import gtk
import os.path
import threading
import time
import sys
import gobject
import gst
import tempfile

if sys.platform == "win32":
    import win32api

STATE_PLAYING = 1
STATE_PAUSED = 2
STATE_READY = 3
## custom
STATE_BUFFERING = 4

STATE_READING = 0
STATE_FINISHED = 1
STATE_CANCELED = 2

_STATE_MAPPING = {gst.STATE_PLAYING : STATE_PLAYING,
                  gst.STATE_PAUSED : STATE_PAUSED,
                  gst.STATE_NULL : STATE_READY,
                  }

__version__ = '1.0'

class Cache(object):
    '''
    Reads out the whole file object to avoid for example stream timeouts.
    Use :class:`Player`'s :meth:`play_cache` method to play this object.
    
    Attention: This starts a new thread for reading.
    If you want to cancel this thread you have to call the :meth:`cancel` method.
    If you call :class:`Player`'s :meth:`stop` method the :meth:`cancel` method is automatically called.
    
    :param fileobj: file object to cache
    :param size: size to calculate state of caching (and playing)
    :param seekable: file object is seekable (not implemented yet)
    :param blocksize: size of blocks for reading and caching
    '''
    def __init__(self, player, fileobj, size=None, seekable=False, blocksize=2048):
        self._fileobj = fileobj
        self.size = size
        self.seekable = seekable # Not implemented yet
        self._blocksize = blocksize
        self.player = player
        self._memory = []
        self._current = 0
        self._active = True
        self.bytes_read = 0
        self._read_thread = threading.Thread(target=self._read)
        self._read_thread.start()
        self.state = STATE_READING
        
    def _read(self):
        data = self._fileobj.read(self._blocksize)
        try:
            self._active
        except:
            print('stop reading cacheeeeeeeeeeeeeeeeee')
            self.state = STATE_FINISHED
            self._fileobj.close()
            self.cancel()
            gobject.idle_add(self.player.emit, 'finished')
            return
        while data and self._active:
            self._memory.append(data)
            self.bytes_read += len(data)
            data = self._fileobj.read(self._blocksize)
        if self._active:
            self.state = STATE_FINISHED
        self._fileobj.close()
        return True
        
    def cancel(self):
        '''
        Cancels the reading thread.
        '''
        print('cancel cache')
        if self.state == STATE_READING:
            self._active = False
            self.state = STATE_CANCELED
        
    def read(self, size=None):
        '''
        Reads in the internal cache.
        This method should not be used directly.
        The :class:`Player` class uses this method to read data for playing.
        '''
        start_block, start_bytes = divmod(self._current, self._blocksize)
        if size:
            if size > self.size - self._current:
                size = self.size - self._current
            while self._current + size > self.bytes_read:
                time.sleep(0.01)
            self._current += size
            end_block, end_bytes = divmod(self._current, self._blocksize)
            result = self._memory[start_block:end_block]
        else:
            while self.size > self.bytes_read:
                time.sleep(0.01)
            self._current = self.size
            result = self._memory[start_block:]
        if size:
            if end_bytes > 0 :
                result.append(self._memory[end_block][:end_bytes])
        if start_bytes > 0 and result:
            result[0] = result[0][start_bytes:]
        return b''.join(result)    

class Gplayer(gobject.GObject):
    '''
    Play media files, file objects and :class:`Cache` objects over GStreamer.
    Implemented as :class:`gobject.GObject`.
    
    GObject Signals:
    
    +------------+--------------------------------------------------------------------------------+
    | Signal     | Meaning                                                                        |
    +============+================================================================================+
    | started    | Source setup is completed and playing will start (not is playing!!!)           |
    +------------+--------------------------------------------------------------------------------+
    | finished   | Playing of the current file, file object or :class:`Cache` object finished     |
    +------------+--------------------------------------------------------------------------------+
    '''
    def __init__(self, engine):
        self._mainGui = engine.mainGui
        self._gui = engine.playerGui
        self._player = gst.element_factory_make("playbin2", "player")
        audiosink = gst.element_factory_make("autoaudiosink")
        audiosink.set_property('async-handling', True)
        if sys.platform == "win32":
            self.videosink = gst.element_factory_make('dshowvideosink')
        else:
            self.videosink = gst.element_factory_make('xvimagesink')
        #self.videosink.set_property('async', False)
        self._player.set_property("audio-sink", audiosink)
        self._player.set_property('video-sink', self.videosink)
        self._player.set_property('buffer-size', 1024000)
        self._bus = self._player.get_bus()
        self._bus.add_signal_watch()
        self._bus.enable_sync_message_emission()
        self._bus.connect("message", engine.on_message)
        self._bus.connect("sync-message::element", engine.on_sync_message)
        self._bus.connect("message::tag", engine.bus_message_tag)
        self._bus.connect('message::buffering', engine.on_message_buffering)
        try:
            self._player.connect('source-setup', self._source_setup)
        except:
            print('no source-setup signal available...')
        self._cache = None
        self.timer= 0 
        self.isStreaming = False
        gobject.GObject.__init__(self)
        
    def play_file(self, filename):
        '''
        Play a file by filename.
        
        :param filename: Filename of file to play. Could be absolute or relative.
        '''
        self._uri = 'file://%s' % (os.path.abspath(filename))
        self._setup()
	
    def play_url(self, url):
        '''
        Play a file by url.
        
        :param url: url of file to play.
        '''
        self._uri = url
        self._setup()
    
    def play_fileobj(self, fileobj, size=None, seekable=False):
        '''
        Play by file object.
        
        :param fileobj: File object to play.
        :param size: Size for duration calculation.
        '''
        self._fileobj = fileobj
        self._size = size
        self._seekable = seekable # Not implemented yet
        self._uri = 'appsrc://'
        self._setup()
    
    def play_cache(self, cache):
        '''
        Play by :class:`Cache` object.
        
        :param cache: Cache object to play.
        '''
        self._cache = cache
        self.play_fileobj(cache, cache.size, cache.seekable)
    
    def play(self):
        '''
        Set state to playing.
        '''
        self._player.set_state(gst.STATE_PLAYING)
	
    
    def pause(self):
        '''
        Set state to paused.
        '''
        self._player.set_state(gst.STATE_PAUSED)
        
    def stop(self, widget=None):
        self._reset()
    
    def stream(self,d):
        self.isStreaming = True
        output = tempfile.NamedTemporaryFile(suffix='.stream', prefix='tmp_')
        try:
            output.write(d.read(1048576))
            self.play_file(output.name)
            data = d.read(2048)
            while data and self.isStreaming:
                output.write(data)
                data = d.read(2048)
        except:
            sleep(1)
        output.close()
        self.isStreaming = False
        
    def stop_stream(self):
        self.timer = 0 
        self.isStreaming = False
    
    
    @property
    def state(self):
        '''
        States:
        
        +------------------------+-------------------------------------+
        | Constant               | Meaning                             |
        +========================+=====================================+
        | :const:`STATE_PLAYING` | Player is playing                   |
        +------------------------+-------------------------------------+
        | :const:`STATE_PAUSED`  | Player is paused                    |
        +------------------------+-------------------------------------+
        | :const:`STATE_READY`   | Player is ready to play a file      |
        +------------------------+-------------------------------------+
        '''
        state = self._player.get_state()[1]
        if state in _STATE_MAPPING:
            return _STATE_MAPPING[state]
    
    @property
    def duration(self):
        '''
        Duration of the current file, file object or :class:`Cache` object.
        
        :rtype: tuple with minutes, seconds, nanoseconds and total nanoseconds
        '''
        total_nanoseconds = self._player.query_duration(gst.FORMAT_TIME)[0]
        seconds, nanoseconds = divmod(total_nanoseconds, 1000000000)
        minutes, seconds = divmod(seconds, 60)
        return minutes, seconds, nanoseconds, total_nanoseconds
    
    @property
    def position(self):
        '''
        Current position in the current file, file object or :class:`Cache` object.
        You have to set this with nanoseconds to seek in the file.
        Please do not seek while playing a file object or a :class:`Cache` object (will be implemented later).
        
        :rtype: tuple with minutes, seconds, nanoseconds and total nanoseconds
        '''
        total_nanoseconds = self._player.query_position(gst.FORMAT_TIME, None)[0]
        seconds, nanoseconds = divmod(total_nanoseconds, 1000000000)
        minutes, seconds = divmod(seconds, 60)
        return minutes, seconds, nanoseconds, total_nanoseconds
    
    @position.setter
    def position(self, nanoseconds):
        self._player.seek_simple(gst.FORMAT_TIME, gst.SEEK_FLAG_ACCURATE, int(round(nanoseconds)))
    
    @property
    def volume(self):
        '''
        Volume of the Player. Set this to change volume.
        
        :rtype: float where 1 means full volume and 0 means mute.
        '''
        return self._player.get_property('volume')
    
    @volume.setter
    def volume(self, value):
        self._player.set_property('volume', value)
    
    def _source_setup(self, playbin, source):
        self._source = source
        if self._uri == 'appsrc://':
            self._source.connect('need-data', self._read_data)
            if self._size:
                self._source.set_property('size', self._size)
        gobject.idle_add(self.emit, 'started')
    
    def _seek_data(self, *args):
        print(args)
    
    def _read_data(self, appsrc, lenght):
        data = self._fileobj.read(lenght)
        if data:
            self._source.emit('push-buffer', gst.Buffer(data))
        else:
            self._source.emit('end-of-stream')
    
    def _setup(self):
        self._player.set_property('uri', self._uri)
        self.play()
    
    def _reset(self):
        if self._cache:
            self._cache.cancel()
            self._cache = None
        self._player.set_state(gst.STATE_NULL)
    
    def _on_message(self, bus, message):
        if message.type == gst.MESSAGE_EOS:
            self._reset()
        elif message.type == gst.MESSAGE_ERROR:
            print('Error: %s' % (str(message.parse_error())))
            
    def on_finished(self):
        self.stop()

gobject.type_register(Gplayer)
gobject.signal_new('finished',
                   Gplayer,
                   gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_BOOLEAN,
                   ())
gobject.signal_new('started',
                   Gplayer,
                   gobject.SIGNAL_RUN_LAST,
                   gobject.TYPE_BOOLEAN,
                   ())
