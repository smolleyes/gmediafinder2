#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright (C) 2010-2011  Darwin M. Bautista <djclue917@gmail.com>
#
# This file is part of mplayer.py.
#
# mplayer.py is free software: you can redistribute it and/or modify
# it under the terms of the GNU Lesser General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# mplayer.py is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public License
# along with mplayer.py.  If not, see <http://www.gnu.org/licenses/>.

import sys

import subprocess
import threading
import time
import gtk
import gobject
import re

try:
    import queue
except ImportError:
    import Queue as queue

gobject.threads_init()

mplayer_cmd = ['mplayer','-slave','-idle','-msglevel','global=6', '-msglevel','all=6', '-cache', '2048']

dic_metadata = {
                'uri'     : None,
                'artist'  : None,
                'album'   : None,
                'year'    : None,
                'title'   : None,
                'comment' : None,
                'track'   : None,
                'genre'   : None,
}
dic_position = {
                'format_pos'    : '00:00:00',
                'pos'           : 0.0,
                'format_length' : '00:00:00',
                'length'        : 0.0,
                'percent'       : 0.0,
}

def convert_s(seconds):
    m, s = divmod(int(seconds), 60)
    h, m = divmod(m, 60)
    if h == 0:
        return "%02d:%02d" % (m, s)
    return "%02d:%02d:%02d" % (h, m, s)

class PlayerStdout(object):
    ''' # -------- MPLAYER STDOUT CB --------- # '''
    
    ''' --- starting --- '''
    def _Playing(self, arg):
        ''' file loaded 
        @var arg filename/uri
        '''
        print 'playing____'
        self.position  = dic_position
        self.mediainfo = {}
        self.metadata  = dic_metadata
        self.metadata['uri'] = arg[:-1]
    
    def _Starting(self, arg):
        ''' starting playing 
        @var arg str
        '''
        self.emit('media-info', self.mediainfo)
        self.emit('metadata', self.metadata)
        self.emit('starting', self.metadata['uri'])
        #time.sleep(5)
        #self.input_cmd('set_property percent_pos 90')
        
    ''' --- file informations --- '''
    def _Opening(self, arg):
        l = arg.split(' ')
        sub = '%s-%s' % (l[0], l[1][:-1])
        self.mediainfo[sub] = ' '.join(l[2:])
    
    def _Selected(self, arg):
        self._Opening(arg)
    
    def _AUDIO(self, arg):
        self.mediainfo['audio-info'] = arg
        try:
            bitrate = re.search('floatle, (.*)kbit',arg).group(1)
            self.mediainfo['audio-bitrate'] = bitrate
        except:
            pass
    
    def _AO(self, arg):
        self.mediainfo['audio-output'] = arg
        try:
            src = self.mediainfo['audio-codec']
            codec = self.get_codec_name(src)
            self.mediainfo['audio-codec-name'] = codec
        except:
            pass
    
    def _VIDEO(self, arg):
        self.isVideo = True
        self.mediainfo['video-info'] = arg
        try:
            src = self.mediainfo['video-info']
            codec = self.get_codec_name(src)
            self.mediainfo['video-codec-name'] = codec
            bitrate = re.search('fps  (.*?)kbps',self.mediainfo['video-info']).group(1)
            self.mediainfo['video-bitrate'] = bitrate
            self.input_cmd('get_time_length')
        except:
            pass
            
    def _Cache(self, arg):
            print '___Buffering___'
    
    ''' --- position --- '''
    def _ANS_TIME_POSITION(self, arg):
        ''' loop stdout callback
        @var arg str(float)
        '''
        self.time_position = round(arg, 2)
        percent = self.time_position / round(float(self.ANS_LENGTH), 2) * 100
        self.position = {
                'format_pos'    : convert_s(self.time_position),
                'pos'           : self.time_position,
                'format_length' : convert_s(self.ANS_LENGTH),
                'length'        : round(self.ANS_LENGTH, 2),
                'percent'       : round(percent, 2),
        }
        self.emit('position', self.position)
     
    
    def _A(self, arg):
        # un retour de commande declanche le stdout de la progress
        # dernier element le retour de commande.
        #time, retour = arg.split('\x1b[J\r')[-2:]
        #print 'time:',time,'retour:', retour
        sys.stdout.flush()
        l = arg.replace('A: ','').split()
        # si video, le timer est different
        if self.isVideo:
            self._ANS_TIME_POSITION(float(l[0]) )
        else:
            pos = float(l[0])
            length = float(l[3])
            sys.stdout.flush()
            percent = pos / length * 100
            self.position = {
                    'format_pos'    : convert_s(pos),
                    'pos'           : pos,
                    'format_length' : convert_s(length),
                    'length'        : length,
                    'percent'       : percent,
            }
            self.emit('position', self.position)
        if arg.startswith('ANS_'):
            if arg.startswith('ANS_AUDIO_SAMPLES'): return
            var, args = arg.split('=',1)
            try: args = eval(arg)
            except: pass
            setattr(self, var, args)
            self.my_queue.put_nowait(retour)
            #print var, arg
            sys.stdout.flush()


    ''' --- metadata --- '''
    def _Artist(self, arg):
        self.metadata['artist']  = arg
    
    def _Title(self, arg):
        self.metadata['title']   = arg

    def _Album(self, arg):
        self.metadata['album']   = arg

    def _Year(self, arg):
        self.metadata['year']    = arg
    
    def _Comment(self, arg):
        self.metadata['comment'] = arg
    
    def _Track(self, arg):
        self.metadata['track']   = arg
    
    def _Genre(self, arg):
        self.metadata['genre']   = arg

function_cmd = '''
def {0}(self, arg=None):
    if arg:
        self.input_cmd('{0} %s' % arg)
        return 1
    else:
        self.input_cmd('{0}')
        return self.return_value('{0}')
'''
function_prop = '''
def {0}(self, arg=None):
    if arg:
        self.input_cmd('set_property {0} %s' % arg)
        return 1
    else:
        self.input_cmd('get_property {0}')
        return self.return_value('{0}')
'''

#~FIXME un petit coup de meta necessaire ...
class PlayerProps(object):
    arg = ['mplayer', '-list-properties']
    for i in subprocess.Popen(arg, stdout=subprocess.PIPE).communicate()[0].split('\n'):
        i = i.strip().split(' ')[0]
        try:
            if i[0] == i[0].upper(): continue
        except:
            continue
        exec(function_prop.format(i))

    def __init__(self, player):
        self.input_cmd = player.input_cmd
        self.return_value = player.return_value


class PlayerCommands(object):
    arg = ['mplayer', '-input', 'cmdlist']
    for i in subprocess.Popen(arg, stdout=subprocess.PIPE).communicate()[0].split('\n'):
        i = i.strip().split(' ')[0]
        try:
            if i[0] == i[0].upper(): continue
        except:
            continue
        exec(function_cmd.format(i))

    def __init__(self, player):
        self.input_cmd = player.input_cmd
        self.return_value = player.return_value


class MyPlayer(threading.Thread, gobject.GObject, PlayerStdout):
    __gsignals__ = {
            'eof': (
                    gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    (gobject.TYPE_STRING, ),
                    ),
        'position': (
                    gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    (gobject.TYPE_PYOBJECT, ),
                    ),
        'metadata': (
                    gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    (gobject.TYPE_PYOBJECT, ),
                    ),
      'media-info': (
                    gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    (gobject.TYPE_PYOBJECT, ),
                    ),
        'starting': (
                    gobject.SIGNAL_RUN_LAST,
                    gobject.TYPE_NONE,
                    (gobject.TYPE_STRING, ),
                    ),
    }
    def __init__(self, args=[]):
        threading.Thread.__init__(self)
        gobject.GObject.__init__(self)
        self.ANS_LENGTH = 1
        self.isRunning  = True
        self.isPaused   = False
        self.isVideo    = False
        self.sup_args   = args
        self.my_queue   = queue.Queue()
        self.cmd        = PlayerCommands(self)
        self.prop       = PlayerProps(self)
        self.isStreaming = False
        
    def return_value(self, key):
        while True:
            try:
                res = self.my_queue.get(timeout=1.0)
                print 'queue', res
            except queue.Empty:
                print 'empty'
                return
            #print 'in retrun', res, key
            resU = res.replace('ANS_','').upper()
            keyU = key.replace('get_time_length','LENGTH')
            keyU = keyU.replace('get_','').upper()
            #print 'in retrun', resU, keyU
            # si le retour de queue commence par la key
            if resU.startswith(keyU):
                break
            if res.startswith('ANS_ERROR='):
                return
        ans = res.partition('=')[2].strip('\'"')
        if ans == '(null)':
            ans = None
        #print 'return___%s___' % ans
        return ans

    ''' # ------------ THREAD LOOP ----------- # '''
    def run(self):
        cmd = mplayer_cmd + self.sup_args
        self.sb  = subprocess.Popen(cmd, stderr=subprocess.PIPE,
                                stdout=subprocess.PIPE, stdin=subprocess.PIPE)
        self.PID = self.sb.pid
        gobject.timeout_add(1000, self.loop_time)
        time.sleep(0.5)
        n=0
        while self.isRunning:
            sortie = self.sb.stdout.readline().decode('utf-8', 'ignore').strip()
            #print '_', [sortie]
            for sep in [': ',' ']:
                try:
                    func, arg = sortie.split(sep, 1)
                    self.try_function(func, arg)
                    continue
                except: pass
            # la sortie ne commence pas tjrs par A: , si retour de commande
            if sortie.startswith('ANS_'):
                var, arg = sortie.split('=',1)
                try: arg = eval(arg)
                except: pass
                setattr(self, var, arg)
                self.my_queue.put_nowait(sortie)
                #print var, arg
                sys.stdout.flush()
                continue
            if sortie.startswith('EOF code:'):
                print '___eof___'
                self.emit('eof', sortie)
                #gobject.idle_add(self.emit, 'eof', self.metadata['uri'])
                self.isVideo = False
                continue
            if sortie == '': n += 1
            else: n = 0
            if n == 10: self.isRunning = False
        
    def try_function(self, func, arg):
        fonction = getattr(self, '_'+func)
        t = threading.Thread(target=fonction, args=(arg,))
        t.daemon = True
        t.start()
    
    def loop_time(self, arg=None):
        #print 'llop'
        if not self.isPaused:
            cmd='''get_audio_samples'''
            self.input_cmd(cmd)
            #self.sb.stdin.flush()
        return self.isRunning
        
    ''' # -------- COMMANDE -------- # '''
    def loadfile(self, arg):
        cmd='''loadfile "%s" 0''' % arg
        self.input_cmd(cmd)
        #self.input_cmd('get_time_length')
        
    def stream(self,d):
        import tempfile
        self.isStreaming = True
        output = tempfile.NamedTemporaryFile(suffix='.stream', prefix='tmp_')
        try:
            output.write(d.read(1048576))
            self.loadfile(output.name)
            data = d.read(2048)
            while data and self.isStreaming:
                output.write(data)
                data = d.read(2048)
            self.sb.wait()
        except:
            print 'waiting data'
        output.close()
        self.isStreaming = False
        
    def stop_stream(self):
        self.timer = 0 
        self.isStreaming = False
    
    def pause(self):
        if self.isPaused:
            self.isPaused = False
        else:
            self.isPaused = True
        self.input_cmd('pause')
        
    
    def input_cmd(self, cmd):
        #print 'in input'
        if self.isRunning:
            self.sb.stdin.write('''pausing_keep %s\n''' % cmd)
            self.sb.stdin.flush()
    
    def get_codec_name(self,codec):
        if ('MP3' in codec or 'ID3' in codec or 'ffmp3' in codec):
            codec = 'mp3'
        elif ('XVID' in codec):
            codec = 'avi'
        elif ('MPEG-4' in codec or 'H.264' in codec or 'MP4' in codec or 'H264' in codec):
            codec = 'mp4'
        elif ('MPEG-2' in codec):
            codec = 'mpeg 2'
        elif ('WMA' in codec or 'wma' in codec or 'ASF' in codec or 'Microsoft Windows Media 9' in codec):
            codec = 'wma'
        elif ('Quicktime' in codec):
            codec = 'mov'
        elif ('Vorbis' in codec or 'Ogg' in codec):
            codec = 'ogg'
        elif ('Sorenson Spark Video' in codec or 'On2 VP6/Flash' in codec or 'FLV' in codec):
            codec = 'flv'
        elif ('VP8' in codec):
            codec = 'webm'
        return codec


# Register PyGTK type
gobject.type_register(MyPlayer)

if __name__ == '__main__':
    def eof_cb(th, arg):
        ''' EOF callback
        @var th thread instance
        @var arg string uri
        '''
        print '___eof_cb', arg

    def position_cb(th, pos):
        ''' position callback
        @var th thread instance
        @var pos dict
        '''
        return
        print '___position_cb', pos

    def metadata_cb(th, meta):
        ''' metadata callback
        @var th thread instance
        @var meta dict
        '''
        return
        print 'metadta_____', meta
    
    def mediainfo_cb(th, info):
        ''' mediainfo callback
        @var th thread instance
        @var info dict
        '''
        return
        print 'mediainfo_____', info
    
    def starting_cb(th, uri):
        ''' starting callback
        @var th thread instance
        @var uri uri filename
        '''
        print 'starting_____', th.mediainfo['audio-codec']
        print 'artist___%s____' % th.cmd.get_meta_artist()
        th.cmd.volume( '%s %s'%(50,1) )
        time.sleep(5)
        print th.prop.volume()
        th.prop.volume('100')

    player = MyPlayer(['-input','nodefault-bindings'])
    player.start()
    player.connect('eof', eof_cb)
    player.connect('position', position_cb)
    # dictionnaires accessible qd starting est lancé.
    player.connect('starting', starting_cb)
    # ou se conecter séparemment.
    player.connect('metadata', metadata_cb)
    player.connect('media-info', mediainfo_cb)
    time.sleep(1)
    print 'exec cmd'
    #url='''http://scfire-ntc-aa07.stream.aol.com:80/stream/1017'''
    #url='''/home/smo/Musique/13 Victim.mp3'''
    url='/home/smo/gmediafinder-downloads/'
    player.loadfile(url)

    gtk.main()

