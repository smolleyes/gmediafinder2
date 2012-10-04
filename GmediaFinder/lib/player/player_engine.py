#-*- coding: UTF-8 -*-
#
# gmediafinder's player engine (python-mplayer)
import os, os.path
import gtk
import sys
import gobject
import math
import random
import time
import thread
from glib import markup_escape_text
import re
import tempfile

## gstreamer modules
import gst

## mplayer module
from mplayer.myplayer import MyPlayer
from mplayer.myplayer import convert_s
## import mplayer engine
from gplayer.gplayer import *
from gplayer.gplayer import Cache as make_cache

## vlc
from vlcplayer import vlc

if sys.platform != "win32":
    from lib.pykey import send_string


STATE_PLAYING = 1
STATE_PAUSED = 2
STATE_READY = 3
## custom
STATE_BUFFERING = 4
STATE_SEEKING = 5

class PlayerEngine(object):
    def __init__(self,mainGui,playerGui,engine='Gstreamer'):
	## init main engine
	if engine == 'Mplayer':
	    self.engine = Mplayer(mainGui,playerGui)
	    self.engine.name = 'Mplayer'
	elif engine == 'Gstreamer':
	    self.engine = GstPlayer(mainGui,playerGui)
	    self.engine.name = 'Gstreamer'
	else:
	    self.engine = VlcPlayer(mainGui,playerGui)
	    self.engine.name = 'Vlc'
    
    def play_file(self,path):
	print 'play'
    
    def play_url(self,url):
	self.engine.play_url(url)
	
    def play_cache(self,data,length=None):
	'''Use this to stream a fileobject'''
	self.engine.play_cache(data,length)
    
    def play(self):
	self.engine.play()
    
    def pause(self):
	self.engine.pause()
	
    def stop(self):
	print "stop 5"
	self.engine.stop()
	
    def shutdown(self):
	self.engine.shutdown()
	
    def get_state(self):
	return self.engine.state
	
    @property
    def state(self):
	return self.engine.state
	
    ######################## player
    def set_window_id(self,window_id):
	self.engine.attach_drawingarea(window_id)
	
    def on_seeker_release(self, value):
	self.engine.on_seeker_release(value)
	    
    def set_volume(self,value):
	self.engine.set_volume(value)
	
    def update_info_section(self):
	self.engine.update_info_section()


class VlcPlayer(object):
    def __init__(self,mainGui,playerGui):
	self.mainGui = mainGui
	self.playerGui = playerGui
	self.title = None
        self.artist = None
        self.album = None
        self.tracknumber = None
        self.url = None
        self.nowplaying = None
        self.position = None
        self.old_position = None
	self.trackinfo = vlc.MediaTrackInfo()
        self.instance=vlc.Instance()
        self.player = self.instance.media_player_new()
        self.mediastats = vlc.MediaStats()
        self.events = vlc.EventType
        self.manager = self.player.event_manager()
	#self.manager.event_attach(self.events.MediaPlayerTimeChanged,
                                  #self.update_info_section,self.player)
	self.manager.event_attach(self.events.MediaPlayerEndReached,
                                      self._on_finished)
				  
	self.timer = self.playerGui.timer
	self.state = STATE_READY
	
    #############
    def format_time(self, milliseconds):
        """formats milliseconds to h:mm:ss
        """
        self.position = milliseconds / 1000
        m, s = divmod(self.position, 60)
        h, m = divmod(m, 60)
	if m < 60:
            return "%02i:%02i" %(m,s)
	else:
            return "%i:%02i:%02i" %(h,m,s)
	
    
    def print_info(self,event=None):
        mstats = self.mediastats
        print "Stats:", self.media.get_stats(mstats), mstats
        print "State:", self.player.get_state()
        print "Time:", self.player.get_time(), self.player.get_position()
        print "Length:", self.player.get_length()
        print "Aspect:", self.player.video_get_aspect_ratio()
        print "Sub:", self.player.video_get_spu_count(), \
                      self.player.video_get_spu()
        print "Audio track:", self.player.audio_get_track_count(), \
                              self.player.audio_get_track()
        for id, name in self.player.audio_get_track_description():
          print "%10d  %s" % (id, name)
        print "Audio channel:", self.player.audio_get_channel()
	print "codec :", self.trackinfo
	self.media.parse()
	#self.stat = self.media.get_stats(mstats)
	print self.media.get_tracks_info()
	
	#print "%0.f kB/s" % (float(self.stat['demux_bitrate'])*8000)
        
    def _on_finished(self,event):
	print "media finished..."
	self.state = STATE_READY
	self.playerGui.check_play_options()
	
    def attach_drawingarea(self,window_id):
	if sys.platform == 'win32':
	    self.player.set_hwnd(window_id)
	else:
	    self.player.set_xwindow(window_id)
	    
    def stop(self):
	self.state = STATE_READY
	print "stop final"
	self.player.stop()
    
    def pause(self):
	if self.state == STATE_PAUSED:
	    self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.play_icon)
	    self.state = STATE_PAUSED
	else:
	    self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.pause_icon)
	    self.state = STATE_PLAYING
	self.player.pause()
	    
    def play_url(self,link):
	"""loads a file or stream
        """
        self.media = self.instance.media_new(link)
        self.player.set_media(self.media)
        self.mediaManager = self.media.event_manager()
	self.state = STATE_PLAYING
        self.player.play()
	
    def play_cache(self,d,length):
	output = tempfile.NamedTemporaryFile(suffix='.stream', prefix='tmp_')
        try:
            output.write(d.read(1048576))
            self.play_url(output.name)
            data = d.read(2048)
            while data:
                output.write(data)
                data = d.read(2048)
        except: 
            print 'waiting data'
        output.close()
	
    def play_file(self,media):
	pass
	
    def update_info_section(self):
        """
        Update the time_label to display the current location
        in the media file as well as update the seek bar
        """
	if self.playerGui.seekmove:
	    return
        ## update timer for mini_player and hide it if more than 5 sec
        ## without mouse movements
        self.timer += 1
        if self.playerGui.fullscreen and self.playerGui.mini_player and self.timer > 4:
	    self.playerGui.show_mini_player()
        
        ## disable screensaver
        #print self.mainGui.fullscreen, self.mainGui.mini_player, self.timer 
	if self.playerGui.fullscreen == True and self.playerGui.mini_player == False and self.timer > 55:
            if sys.platform == "win32":
                win32api.keybd_event(7,0,0,0)
            else:
                send_string('a')
            self.timer = 0
        
        self.length = self.media.get_duration()
	if self.length != -1:
          try:
            self.duration = self.format_time(self.length)
          except:
            self.duration = None
        
        if self.length > 0:
            try:
                self.current_position = self.player.get_time()
            except:
                return 0
            current_position_formated = self.format_time(self.current_position)
            gobject.idle_add(self.playerGui.time_label.set_text,current_position_formated + "/" + str(self.duration))
        
            # Update the seek bar
            # gtk.Adjustment(value=0, lower=0, upper=0, step_incr=0, page_incr=0, page_size=0)
	    percent = (float(self.current_position)/float(self.length))*100.0
            adjustment = gtk.Adjustment(percent, 0.00, 100.0, 0.1, 1.0, 1.0)
            self.playerGui.seeker.set_adjustment(adjustment)
	else:
	    try:
                self.current_position = self.player.get_time()
            except:
                return 0
	    current_position_formated = self.format_time(self.current_position)
            gobject.idle_add(self.playerGui.time_label.set_text,current_position_formated + "/-1:00:00")
	    if self.current_position > 2:
		gobject.idle_add(self.playerGui.seeker.set_sensitive,0)
	    
    def on_seeker_release(self, value):
	if self.player.is_seekable():
	    try:
		self.player.set_position(value / 100.0)
	    except:
		print "seek error..."
	else:
	    print "stream not seekable"
	
    def set_volume(self, value):
	self.player.audio_set_volume(int(value * 100))
	
	
class Mplayer(object):
    def __init__(self,mainGui,playerGui):
	self.mainGui = mainGui
	self.playerGui = playerGui
	self.state = STATE_READY
	wid = self.get_window_id()
	self.player = MyPlayer( ['-wid', str(wid)])
        self.player.connect('eof', self.player_eof_cb)
        self.player.connect('media-info', self.player_media_info_cb)
        self.player.connect('position', self.player_position_cb)
        self.player.start()
	self.duration = None
	self.timer = 0
	
    def get_window_id(self):
	self.playerGui.movie_window.realize()
	if sys.platform == "win32":
            window = self.playerGui.movie_window.get_window()
            window.ensure_native()
            return self.playerGui.movie_window.window.handle
        else:
            return self.playerGui.movie_window.window.xid
	    
    def update_info_section(self):
	if self.state == STATE_READY:
	    adjustment = gtk.Adjustment(0, 0.00, 100.0, 0.1, 1.0, 1.0)
	    self.playerGui.seeker.set_adjustment(adjustment)
	#gobject.idle_add(self.playerGui.time_label.set_text,timeinf)
	#gobject.idle_add(self.playerGui.seeker.set_value, dic['percent'])
	    
    
    def player_eof_cb(self, player, code):
        ''' Player calback
        @var player instance
        @var uri média lu
        @brief Appelé à l'arrêt du flux (fin du fichier/stream)
        '''
	self.timer = 0
	print code
	if 'code: 1' in code:
	    try:
		self.playerGui.check_play_options()
	    except:
		self.stop()
	elif 'code: 4' in code:
	    self.stop()
    
    def player_position_cb(self, player, dic):
        ''' Player calback
        @var player instance
        @var dic dictionnaire infos position
        @brief Appelé chaque seconde, infos progress
        '''
        if self.state == STATE_SEEKING or self.state == STATE_PAUSED:
	    return
	if self.player.isStreaming:
	    if self.duration and int(self.duration) > 0:
		pos = convert_s(self.timer)
		timeinf = '%s/%s' % (pos,convert_s(self.duration))
		percent = int(self.timer) / round(float(self.duration), 2) * 100
		gobject.idle_add(self.playerGui.seeker.set_value, percent)
		self.timer += 1
	    else:
		timeinf = '{format_pos}/-1:00'.format(**dic)
	else:
	    timeinf = '{format_pos}/{format_length}'.format(**dic)
	    gobject.idle_add(self.playerGui.seeker.set_value, dic['percent'])
	#print '___________%s__________'% timeinf
	gobject.idle_add(self.playerGui.time_label.set_text,timeinf)
        
    def player_media_info_cb(self, player, dic):
        ''' Player calback
        @var player instance
        @var dic dictionnaire infos media
        @brief Appelé au commencement de la lecture
        '''
        audio = '''{audio-codec}\n{audio-info}\n{audio-output}'''.format(**dic)
        try:
            video = '''{video-decoder}\n{video-codec}\n{video-info}'''.format(**dic)
        except: video = 'No video'
	### get codec
	codec = None
	try:
	    codec = dic['video-codec-name']
	except:
	    codec = dic['audio-codec-name']
        ## get bitrate
	bitrate = None
	try:
	    bitrate = dic['video-bitrate']
	except:
	    bitrate = dic['audio-bitrate']
	
	self.playerGui.media_bitrate_label.set_markup('<small><b>%s </b> %s Kbps</small>' % (self.playerGui.bitrate_label,bitrate))
	self.playerGui.media_codec_label.set_markup('<small><b>%s </b> %s</small>' % (self.playerGui.codec_label,codec))
    
    def on_seeker_release(self, value):
	self.state = STATE_PLAYING
        self.player.cmd.seek('%s 1' % value)
    
    def set_volume(self,value):
	self.player.cmd.volume('%s 1' % (value * 100))
    
    def play_url(self,url):
	self.state = STATE_PLAYING
	self.player.loadfile(url)
	
    def play_cache(self, data, length=None):
	self.state = STATE_PLAYING
	if length:
	    self.duration = length
	print data, length
	self.player.stream(data)
	
    def play(self):
	if self.state == STATE_PAUSED:
	    self.state = STATE_PLAYING
	self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.pause_icon)
	
    def pause(self):
	self.player.pause()
	self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.play_icon)
	self.state = STATE_PAUSED
	
    def stop(self):
	if self.state != STATE_READY:
	    self.player.cmd.stop()
	try:
	    self.player.stop_stream()
	except:
	    print ''
	self.state = STATE_READY
	
    def shutdown(self):
	self.player.cmd.exit()
	self.player.isRunning = False
        os.kill(self.player.PID, 3)
    
	
class GstPlayer(object):
    def __init__(self,mainGui,playerGui):
	self.mainGui = mainGui
	self.playerGui = playerGui
	self.player = Gplayer(self)
	self.player.connect('finished', self.on_finished)
	self.state = STATE_READY
	## time
        self.timeFormat = gst.Format(gst.FORMAT_TIME)
	self.timer = self.playerGui.timer
	self.duration = None
	self.cache_duration = None
	## seek
	self._cbuffering = -1
	## media infos
	self.file_tags = {}
	self.media_codec = None
	self.status= None
    
    def on_finished(self,widget):
	print 'finish in player_engine.py'
	try:
	    if self.playerGui.radio_mode:
		self.mainGui.search_engine.play_next()
	    else:
		self.playerGui.check_play_options()
	except:
	    self.playerGui.stop()
    
    def attach_drawingarea(self,window_id):
	self.player.videosink.set_xwindow_id(window_id)
	
    def set_volume(self,value):
	self.player._player.set_property("volume", float(value))
    
    def play_url(self,url):
	self.state = STATE_PLAYING
	self.player.play_url(url)
	
    def play(self):
	self.duration = None
	name = markup_escape_text(self.mainGui.media_name)
	gobject.idle_add(self.playerGui.media_name_label.set_markup,'<small><b>%s</b> %s</small>' % (self.playerGui.play_label,name))
	self.state = STATE_PLAYING
	gobject.idle_add(self.playerGui.pause_btn_pb.set_from_pixbuf,self.playerGui.pause_icon)
	self.player.play()
	
    def play_cache(self, stream, length=None):
	self.state = STATE_PLAYING
	try:
	    self.cache_duration = stream.size
	except:
	    self.cache_duration = None
	self.player.play_cache(Cache(self.player,stream.data,stream.size))
    
    def pause(self):
	self.player.pause()
	self.state = STATE_PAUSED
	gobject.idle_add(self.playerGui.pause_btn_pb.set_from_pixbuf,self.playerGui.play_icon)
	
    def stop(self):
	self.playerGui.stop()

	
    def reset(self):
	self.player.stop()
	self.duration = None
	self.state = STATE_READY
	
    def update_info_section(self):
        """
        Update the time_label to display the current location
        in the media file as well as update the seek bar
        """
	#print "---------------update_info-----------------"
	#print "state : %s" % self.state
	if self.state != 1:
	    return
	    
        if self.player.state == STATE_READY:
            adjustment = gtk.Adjustment(0, 0.00, 100.0, 0.1, 1.0, 1.0)
            self.playerGui.seeker.set_adjustment(adjustment)
            gobject.idle_add(self.playerGui.time_label.set_text,"00:00 / 00:00")
            return False
	    
	try:
	    self.playerGui.media_codec = self.media_codec
	    gobject.idle_add(self.playerGui.media_bitrate_label.set_markup,'<small><b>%s </b> %s</small>' % (self.playerGui.bitrate_label,self.media_bitrate))
	    gobject.idle_add(self.playerGui.media_codec_label.set_markup,'<small><b>%s </b> %s</small>' % (self.playerGui.codec_label,self.media_codec))
	except:
	    gobject.idle_add(self.playerGui.media_bitrate_label.set_markup,'<small><b>%s </b> %s</small>' % (self.playerGui.bitrate_label,'unknown'))
	    gobject.idle_add(self.playerGui.media_codec_label.set_markup,'<small><b>%s </b> %s</small>' % (self.playerGui.codec_label,'unknown'))

        ## update timer for mini_player and hide it if more than 5 sec
        ## without mouse movements
        self.playerGui.timer += 1
        if self.playerGui.fullscreen and self.playerGui.mini_player and self.playerGui.timer > 4:
            self.playerGui.show_mini_player()
        
        ## disable screensaver
        if self.playerGui.fullscreen == True and self.playerGui.mini_player == False and self.playerGui.timer > 55:
            if sys.platform == "win32":
                win32api.keybd_event(7,0,0,0)
            else:
                send_string('a')
            self.timer = 0

	if self.duration == None:
          try:
              self.length = self.player._player.query_duration(self.timeFormat, None)[0]
              self.duration = self.convert_ns(self.length)
          except gst.QueryError:
	      self.duration = None
        elif self.cache_duration and not self.duration:
	    self.length = int(self.cache_duration)
	    self.duration = self.format_time(int(self.cache_duration))

	
	if self.duration != None:
	    self.current_position = 0
            try:
                self.current_position = self.player._player.query_position(self.timeFormat, None)[0]
            except gst.QueryError:
                return 0
            current_position_formated = self.convert_ns(self.current_position)
            gobject.idle_add(self.playerGui.time_label.set_text,current_position_formated + "/" + str(self.duration))
        
            # Update the seek bar
            # gtk.Adjustment(value=0, lower=0, upper=0, step_incr=0, page_incr=0, page_size=0)
            percent = (float(self.current_position)/float(self.length))*100.0
            adjustment = gtk.Adjustment(percent, 0.00, 100.0, 0.1, 1.0, 1.0)
            self.playerGui.seeker.set_adjustment(adjustment)
	    if percent == 100:
		gobject.idle_add(self.player.emit, 'finished')
        
        return True
	
	
    def on_message(self, bus, message):
        if self.mainGui.search_engine.engine_type == "video":
            self.player.videosink.set_property('force-aspect-ratio', True)
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.play_thread_id = None
            self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.pause_icon)
            self.playerGui.play_btn_pb.set_from_pixbuf(self.playerGui.stop_icon)
	    gobject.idle_add(self.player.emit, 'finished')
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error Gstreamer: %s" % err, debug
            self.play_thread_id = None
            self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.pause_icon)
            self.playerGui.play_btn_pb.set_from_pixbuf(self.playerGui.stop_icon)
	    gobject.idle_add(self.player.emit, 'finished')
    
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        win_id = None
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            if sys.platform == "win32":
                win_id = self.playerGui.movie_window.window.handle
            else:
                win_id = self.playerGui.movie_window.window.xid
            self.attach_drawingarea(win_id)
    
    def on_message_buffering(self, bus, message):
	percent = 0
	percent = message.parse_buffering()
	if math.floor(percent/5) > self._cbuffering:
	    self._cbuffering = math.floor(percent/5)
	    buffering = _('Buffering :')
	    self.status = STATE_BUFFERING
	    gobject.idle_add(self.playerGui.media_name_label.set_markup,'<small><b>%s</b> %s%s</small>' % (buffering,percent,'%'))

	if percent == 100:
	    self._cbuffering = -1
	    if self.state == STATE_PAUSED:
		self.mainGui.info_label.set_text('')
		gobject.idle_add(self.playerGui.media_name_label.set_markup,'<small><b>%s</b></small>' % self.mainGui.media_name)
		self.play()
	elif self.status == STATE_BUFFERING:
	    if not self.state == STATE_PAUSED:
		self.pause()
    
    def convert_ns(self, t):
        # This method was submitted by Sam Mason.
        # It's much shorter than the original one.
        s,ns = divmod(t, 1000000000)
        m,s = divmod(s, 60)
        if m < 60:
            return "%02i:%02i" %(m,s)
        else:
            h,m = divmod(m, 60)
            return "%i:%02i:%02i" %(h,m,s)
	    
    def format_time(self, sec):
        """formats milliseconds to h:mm:ss
        """
        self.position = sec
        m, s = divmod(self.position, 60)
        h, m = divmod(m, 60)
	if m < 60:
            return "%02i:%02i" %(m,s)
	else:
            return "%i:%02i:%02i" %(h,m,s)
    
    def bus_message_tag(self, bus, message):
	codec = None
	self.audio_codec = None
	self.media_bitrate = None
	self.mode = None
	self.media_codec = None
	#we received a tag message
	taglist = message.parse_tag()
	self.old_name = self.mainGui.media_name
	#put the keys in the dictionary
	for key in taglist.keys():
		#print key, taglist[key]
		if key == "preview-image" or key == "image":
			ipath="/tmp/temp.png"
			img = open(ipath, 'w')
			img.write(taglist[key])
			img.close()
			self.media_thumb = gtk.gdk.pixbuf_new_from_file_at_scale(ipath, 64,64, 1)
			try:
			    self.mainGui.model.set_value(self.mainGui.selected_iter, 0, self.media_thumb)
			except:
			    thumb = None
		elif key == "bitrate":
			r = int(taglist[key]) / 1000
			self.file_tags[key] = "%sk" % r
		elif key == "channel-mode":
			self.file_tags[key] = taglist[key]
		elif key == "audio-codec":
			k = str(taglist[key])
			if not self.file_tags.has_key(key) or self.file_tags[key] == '':
				self.file_tags[key] = k
		elif key == "video-codec":
			k = str(taglist[key])
			if not self.file_tags.has_key(key) or self.file_tags[key] == '':
				self.file_tags[key] = k
		elif key == "container-format":
			k = str(taglist[key])
			if not self.file_tags.has_key(key) or self.file_tags[key] == '':
				self.file_tags[key] = k
		#print self.file_tags
	try:
		if self.file_tags.has_key('video-codec') and self.file_tags['video-codec'] != "":
			codec = self.file_tags['video-codec']
		else:
			codec = self.file_tags['audio-codec']
		if codec == "" and self.file_tags['container-format'] != "":
			codec = self.file_tags['container-format']
		if ('MP3' in codec or 'ID3' in codec):
				self.media_codec = 'mp3'
		elif ('XVID' in codec):
				self.media_codec = 'avi'
		elif ('MPEG-4' in codec or 'H.264' in codec or 'MP4' in codec):
				self.media_codec = 'mp4'
		elif ('WMA' in codec or 'ASF' in codec or 'Microsoft Windows Media 9' in codec):
				self.media_codec = 'wma'
		elif ('Quicktime' in codec):
				self.media_codec = 'mov'
		elif ('Vorbis' in codec or 'Ogg' in codec):
				self.media_codec = 'ogg'
		elif ('Sorenson Spark Video' in codec or 'On2 VP6/Flash' in codec):
				self.media_codec = 'flv'
		elif ('VP8' in codec):
			self.media_codec = 'webm'
		self.media_bitrate = self.file_tags['bitrate']
		self.mode = self.file_tags['channel-mode']
		#self.model.set_value(self.selected_iter, 1, self.media_markup)
		self.file_tags = tags
		self.playerGui.media_codec = self.media_codec
	except:
		return

    def on_seeker_release(self, value):
	duration = self.player._player.query_duration(self.timeFormat, None)[0]
	time = value * (duration / 100)
	self.player._player.seek_simple(self.timeFormat, gst.SEEK_FLAG_FLUSH, time)
	self.seekmove = False
