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

## gstreamer modules
import gst

## mplayer module
from mplayer.myplayer import MyPlayer

## import mplayer engine
from gplayer.gplayer import *

if sys.platform != "win32":
    from lib.pykey import send_string


STATE_PLAYING = 1
STATE_PAUSED = 2
STATE_READY = 3
## custom
STATE_BUFFERING = 4
STATE_SEEKING = 5

class PlayerEngine(object):
    def __init__(self,mainGui,playerGui,engine='mplayer'):
	## init main engine
	if engine == 'mplayer':
	    self.engine = Mplayer(mainGui,playerGui)
	else:
	    self.engine = GstPlayer(mainGui,playerGui)
	    
    def play_file(self,path):
	print 'play'
    
    def play_url(self,url):
	self.engine.play_url(url)
	
    def play_cache(self,data):
	'''Use this to stream a fileobject'''
	print 'play fileobject'
    
    def play(self):
	self.player.play()
    
    def pause(self):
	print 'here %s' % self.engine.state
	if self.engine.state == STATE_PAUSED:
            self.engine.play()
        else:
	    self.engine.pause()
	
    def stop(self):
	self.engine.stop()
	
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
	
	
class Mplayer(object):
    def __init__(self,mainGui,playerGui):
	self.mainGui = mainGui
	self.playerGui = playerGui
	self.state = STATE_READY
	wid = self.get_window_id()
	self.player = MyPlayer( ['-wid', str(wid)])
        #self.player.connect('eof', self.player_eof_cb)
        self.player.connect('media-info', self.player_media_info_cb)
        self.player.connect('position', self.player_position_cb)
        self.player.start()
	
    def get_window_id(self):
	self.playerGui.movie_window.realize()
	if sys.platform == "win32":
            window = self.playerGui.movie_window.get_window()
            window.ensure_native()
            return self.playerGui.movie_window.window.handle
        else:
            return self.playerGui.movie_window.window.xid
	    
    def update_info_section(self):
	pass
	    
    
    def player_eof_cb(self, player, uri):
        ''' Player calback
        @var player instance
        @var uri média lu
        @brief Appelé à l'arrêt du flux (fin du fichier/stream)
        '''
        gobject.idle_add(self.playerGui.seeker.set_value, 100)
        return
    
    def player_position_cb(self, player, dic):
        ''' Player calback
        @var player instance
        @var dic dictionnaire infos position
        @brief Appelé chaque seconde, infos progress
        '''
        #print dic
        if self.state == STATE_SEEKING:
	    return
	timeinf = '{format_pos}/{format_length}'.format(**dic)
	print '___________%s__________'% timeinf
	gobject.idle_add(self.playerGui.time_label.set_text,timeinf)
	gobject.idle_add(self.playerGui.seeker.set_value, dic['percent'])
        
    def player_media_info_cb(self, player, dic):
        ''' Player calback
        @var player instance
        @var dic dictionnaire infos media
        @brief Appelé au commencement de la lecture
        '''
        print dic
        audio = '''{audio-decoder}\n{audio-codec}\n{audio-info}\n{audio-output}'''.format(**dic)
        try:
            video = '''{video-decoder}\n{video-codec}\n{video-info}'''.format(**dic)
        except: video = 'No video'
	### get codec
	codec = None
	try:
	    codec = self.player.mediainfo['video-codec']
	except:
	    codec = self.player.mediainfo['audio-codec']
        ## get bitrate
	bitrate = None
	try:
	    bitrate = self.player.mediainfo['video-bitrate']
	except:
	    bitrate = self.player.mediainfo['audio-bitrate']
	
	self.playerGui.media_bitrate_label.set_markup('<small><b>%s </b> %s</small>' % (self.playerGui.bitrate_label,bitrate))
	self.playerGui.media_codec_label.set_markup('<small><b>%s </b> %s</small>' % (self.playerGui.codec_label,codec))
    
    def on_seeker_release(self, value):
        self.player.cmd.seek('%s 1' % value)
	self.state = STATE_PLAYING
    
    def set_volume(self,value):
	self.player.cmd.volume('%s' % round(value))
    
    def play_url(self,url):
	self.player.loadfile(url)
	
    def play(self):
	if self.state == STATE_PAUSED:
	    self.state = STATE_PLAYING
	    self.player.pause()
	    self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.pause_icon)
	
    def pause(self):
	self.player.pause()
	self.state = STATE_PAUSED
	self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.play_icon)
	
    def stop(self):
	self.player.cmd.stop()
	self.state = STATE_READY
    
	
class GstPlayer(object):
    def __init__(self,mainGui,playerGui):
	self.mainGui = mainGui
	self.playerGui = playerGui
	self.player = Gplayer(self)
	self.state = STATE_READY
	## time
        self.timeFormat = gst.Format(gst.FORMAT_TIME)
	self.timer = 0
	self.duration = None
	## seek
	self._cbuffering = -1
	## media infos
	self.file_tags = {}
	self.media_codec = None
	self.status= None
    
    def attach_drawingarea(self,window_id):
	self.player.videosink.set_xwindow_id(window_id)
	
    def set_volume(self,value):
	self.player._player.set_property("volume", float(value))
    
    def play_url(self,url):
	self.player.play_url(url)
	
    def play(self):
	name = markup_escape_text(self.mainGui.media_name)
	gobject.idle_add(self.playerGui.media_name_label.set_markup,'<small><b>%s</b> %s</small>' % (self.playerGui.play_label,name))
	self.playerGui.media_bitrate_label.set_markup('<small><b>%s </b> %s</small>' % (self.playerGui.bitrate_label,self.media_bitrate))
	self.playerGui.media_codec_label.set_markup('<small><b>%s </b> %s</small>' % (self.playerGui.codec_label,self.media_codec))
	self.player.play()
	self.state = STATE_PLAYING
	self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.pause_icon)
	
    def pause(self):
	self.player.pause()
	self.state = STATE_PAUSED
	self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.play_icon)
	
    def stop(self):
	self.player.stop()
	self.duration = None
	self.state = STATE_READY
	
    def update_info_section(self):
        """
        Update the time_label to display the current location
        in the media file as well as update the seek bar
        """
	if self.state == STATE_SEEKING or self.state == STATE_BUFFERING or self.state == STATE_PAUSED:
	    return
	    
        if self.player.state == STATE_READY:
            adjustment = gtk.Adjustment(0, 0.00, 100.0, 0.1, 1.0, 1.0)
            self.playerGui.seeker.set_adjustment(adjustment)
            gobject.idle_add(self.playerGui.time_label.set_text,"00:00 / 00:00")
            return False
        
        ## update timer for mini_player and hide it if more than 5 sec
        ## without mouse movements
        self.timer += 1
        if self.mainGui.fullscreen and self.mainGui.mini_player and self.timer > 4:
            self.mainGui.show_mini_player()
        
        ## disable screensaver
        if self.mainGui.fullscreen == True and self.mainGui.mini_player == False and self.timer > 55:
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
        
        if self.duration != None:
            try:
                self.current_position = self.player._player.query_position(self.timeFormat, None)[0]
            except gst.QueryError:
                return 0
            current_position_formated = self.convert_ns(self.current_position)
            gobject.idle_add(self.playerGui.time_label.set_text,current_position_formated + "/" + self.duration)
        
            # Update the seek bar
            # gtk.Adjustment(value=0, lower=0, upper=0, step_incr=0, page_incr=0, page_size=0)
            percent = (float(self.current_position)/float(self.length))*100.0
            adjustment = gtk.Adjustment(percent, 0.00, 100.0, 0.1, 1.0, 1.0)
            self.playerGui.seeker.set_adjustment(adjustment)
        
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
            self.playerGui.check_play_options()
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.play_thread_id = None
            self.playerGui.pause_btn_pb.set_from_pixbuf(self.playerGui.pause_icon)
            self.playerGui.play_btn_pb.set_from_pixbuf(self.playerGui.stop_icon)
            ## continue if continue option selected...
            if self.playerGui.play_options == "continue":
                self.playerGui.check_play_options()
    
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
	percent = message.parse_buffering()
	if math.floor(percent/5) > self._cbuffering:
	    self._cbuffering = math.floor(percent/5)
	    buffering = _('Buffering :')
	    self.status = STATE_BUFFERING
	    gobject.idle_add(self.playerGui.media_name_label.set_markup,'<small><b>%s</b> %s%s</small>' % (buffering,percent,'%'))
	
	if percent == 100:
	    if self.state == STATE_PAUSED:
		self.mainGui.info_label.set_text('')
		self.play()
	    self._cbuffering = -1
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
			print key, taglist[key]
			if key == "preview-image" or key == "image":
				ipath="/tmp/temp.png"
				img = open(ipath, 'w')
				img.write(taglist[key])
				img.close()
				self.media_thumb = gtk.gdk.pixbuf_new_from_file_at_scale(ipath, 64,64, 1)
				self.mainGui.model.set_value(self.mainGui.selected_iter, 0, self.media_thumb)
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
	self.state = STATE_PLAYING
	duration = self.player._player.query_duration(self.timeFormat, None)[0]
	time = value * (duration / 100)
	self.player._player.seek_simple(self.timeFormat, gst.SEEK_FLAG_FLUSH, time)

