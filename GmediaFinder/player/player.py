#-*- coding: UTF-8 -*-
#
# gmediafinder's player gui package
import gtk
import sys
import pango
import gobject
import math
import gst
from glib import markup_escape_text
import random
import time
import gobject
import thread

## custom lib
try:
    import config
    if sys.platform != "win32":
	from pykey import send_string
except:
    from GmediaFinder import config
    if sys.platform != "win32":
	from Gmediafinder.pykey import send_string
    
from gplayer import *

class Player(object):
    def __init__(self,mainGui):
        self.gladeGui = mainGui.gladeGui
        self.duration = None
        self.time_label = gtk.Label("00:00 / 00:00")
        self.media_name = ""
        self.media_link = ""
        self.mainGui = mainGui
        self._cbuffering = -1
	self.xsink = False
        self.file_tags = {}
	self.media_codec = None
	## time
        self.timeFormat = gst.Format(gst.FORMAT_TIME)
	self.status = STATE_READY
	## play mode options
	self.play_options = "continue"
	## seek
	self.seeker_move = None
        
        # video drawing
        self.video_box = self.gladeGui.get_widget("video_box")
        self.movie_window = self.gladeGui.get_widget("drawingarea")
        self.movie_window.set_flags(gtk.CAN_FOCUS)
        self.movie_window.unset_flags(gtk.DOUBLE_BUFFERED)
        self.movie_window.connect('realize', self.on_drawingarea_realized)
        self.mainGui.window.connect('motion-notify-event', self.on_motion_notify)
        self.movie_window.connect('configure-event', self.on_configure_event)
        self.movie_window.connect('expose-event', self.on_expose_event)
        self.movie_window.connect('button-press-event', self.on_drawingarea_clicked)
        self.movie_window.add_events(gtk.gdk.BUTTON_PRESS_MASK)
        self.pic_box = self.gladeGui.get_widget("picture_box")
        
        # seekbar and signals
        self.control_box = self.gladeGui.get_widget("control_box")
        self.seekbox = self.gladeGui.get_widget("seekbox")
        self.adjustment = gtk.Adjustment(0.0, 0.00, 100.0, 0.1, 1.0, 1.0)
        self.seeker = gtk.HScale(self.adjustment)
        self.seeker.set_draw_value(False)
        self.seeker.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.seekbox.add(self.seeker)
        self.seeker.connect("button-release-event", self.seeker_button_release_event)
        self.seeker.connect("button-press-event", self.seeker_block)
        #timer
        self.timerbox = self.gladeGui.get_widget("timer_box")
        self.timerbox.add(self.time_label)
        ## seekbar infos
        self.media_name_label = self.gladeGui.get_widget("media_name")
        self.media_name_label.set_property('ellipsize', pango.ELLIPSIZE_END)
        self.media_codec_label = self.gladeGui.get_widget("media_codec")
        self.media_bitrate_label = self.gladeGui.get_widget("media_bitrate")
	
        ## SIGNALS
        dic = {
        "on_pause_btn_clicked" : self.pause,
        "on_shuffle_btn_toggled" : self.set_play_options,
        "on_repeat_btn_toggled" : self.set_play_options,
        "on_vol_btn_value_changed" : self.on_volume_changed,
        }
        self.gladeGui.signal_autoconnect(dic)
        #### load buttons and pixbufs
        self.load_gui_icons()
        #### init gst gplayer engine
        self.player = Gplayer(mainGui,self)
	
    def load_gui_icons(self):
        ## try to load and use the current gtk icon theme,
        ## if not possible, use fallback icons
        default_icon_theme = gtk.icon_theme_get_default()
        ## load desired icons if possible
        play_icon = default_icon_theme.lookup_icon("player_play",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        if play_icon:
            self.play_icon = play_icon.load_icon()

        stop_icon = default_icon_theme.lookup_icon("player_stop",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        if stop_icon:
            self.stop_icon = stop_icon.load_icon()

        pause_icon = default_icon_theme.lookup_icon("stock_media-pause",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        if pause_icon:
            self.pause_icon = pause_icon.load_icon()

        shuffle_icon = default_icon_theme.lookup_icon("stock_shuffle",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        if shuffle_icon:
            self.shuffle_icon = shuffle_icon.load_icon()

        loop_icon = default_icon_theme.lookup_icon("stock_repeat",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        if loop_icon:
            self.loop_icon = loop_icon.load_icon()

        pagen_icon = default_icon_theme.lookup_icon("next",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        if pagen_icon:
            self.page_next_icon = pagen_icon.load_icon()

        pagep_icon = default_icon_theme.lookup_icon("previous",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        if pagep_icon:
            self.page_prev_icon = pagep_icon.load_icon()
            
        clear_icon = default_icon_theme.lookup_icon("gtk-clear",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        if clear_icon:
            self.clear_icon = clear_icon.load_icon()
            
        fullscreen_pix = default_icon_theme.lookup_icon("gtk-fullscreen",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        self.fullscreen_pix = fullscreen_pix.load_icon()
        leave_fullscreen_pix = default_icon_theme.lookup_icon("gtk-leave-fullscreen",24,gtk.ICON_LOOKUP_USE_BUILTIN)
        self.leave_fullscreen_pix = leave_fullscreen_pix.load_icon()

        ## play
        self.play_btn = self.gladeGui.get_widget("play_btn")
        self.play_btn_pb = self.gladeGui.get_widget("play_btn_img")
        self.play_btn_pb.set_from_pixbuf(self.play_icon)
        self.play_btn.connect('clicked', self.start_stop)
        ## pause
        self.pause_btn = self.gladeGui.get_widget("pause_btn")
        self.pause_btn_pb = self.gladeGui.get_widget("pause_btn_img")
        self.pause_btn_pb.set_from_pixbuf(self.pause_icon)
        ## pages next/back
        self.changepage_btn = self.gladeGui.get_widget("nextpage_btn")
        self.changepage_pixb = self.gladeGui.get_widget("nextpage_pixb")
        self.changepage_pixb.set_from_pixbuf(self.page_next_icon)
        self.pageback_btn = self.gladeGui.get_widget("pageback_btn")
        self.pageback_pixb = self.gladeGui.get_widget("backpage_pixb")
        self.pageback_pixb.set_from_pixbuf(self.page_prev_icon)
        ## loop/shuffle
        self.shuffle_btn = self.gladeGui.get_widget("shuffle_btn")
        self.shuffle_pixb = self.gladeGui.get_widget("shuffle_btn_pixb")
        self.shuffle_pixb.set_from_pixbuf(self.shuffle_icon)
        self.loop_btn = self.gladeGui.get_widget("repeat_btn")
        self.loop_pixb = self.gladeGui.get_widget("repeat_btn_pixb")
        self.loop_pixb.set_from_pixbuf(self.loop_icon)
        ## paypalsupport img
        self.support_pixb = self.gladeGui.get_widget("paypal_img")
        pb = gtk.gdk.pixbuf_new_from_file(config.img_path+"/paypal.gif")
        self.support_pixb.set_from_pixbuf(pb)
        ## donate btn
        self.donate_pixb = self.gladeGui.get_widget("donate_img")
        pb = gtk.gdk.pixbuf_new_from_file(config.img_path+"/donate.gif")
        self.donate_pixb.set_from_pixbuf(pb)
        ## fullscreen btn
        self.fullscreen_btn = self.gladeGui.get_widget("fullscreen_btn")
        self.fullscreen_btn_pixb = self.gladeGui.get_widget("fullscreen_pix")
        self.fullscreen_btn_pixb.set_from_pixbuf(self.fullscreen_pix)
        self.fullscreen_btn.connect('clicked', self.mainGui.set_fullscreen)
        self.fullscreen_btn.set_tooltip_text(_("enter fullscreen"))
        self.changepage_btn.set_sensitive(0)
        self.pageback_btn.set_sensitive(0)
	
	self.bitrate_label =_('Bitrate:')
        self.codec_label =_('Encoding:')
        self.play_label =_('Playing:')
         
    def start_stop(self,widget=None):
        if widget:
            if not self.player.state == STATE_PLAYING:
                return self.mainGui.get_model()
            else:
                return self.stop()
        else:
            if self.active_link:
                if not self.player.state == STATE_PLAYING:
                    return self.start_play(self.active_link)
                else:
                    return self.stop_play()

    def start_play(self,url):
        self.stop()
        self.active_link = url
        self.duration = None
        self.file_tags = {}
        #if not sys.platform == "win32":
            #if not self.vis_selector.getSelectedIndex() == 0 and not self.search_engine.engine_type == "video":
                #self.player.set_property('flags', "Render visualisation when no video is present")
                #self.vis = self.change_visualisation()
                #self.visual = gst.element_factory_make(self.vis,'visual')
                #self.player.set_property('vis-plugin', self.visual)
            #else:
                #if self.search_engine.engine_type == "video":
                    #self.player.set_property('flags', "Render the video stream")
                #else:
                    #self.player.set_property('flags', "Render the audio stream")
        self.play_btn_pb.set_from_pixbuf(self.stop_icon)
        self.pause_btn_pb.set_from_pixbuf(self.pause_icon)
        self.player.play_url(self.active_link)
	try:
	    gobject.idle_add(self.media_name_label.set_markup,'<small><b>%s</b> %s</small>' % (self.play_label,self.mainGui.media_name))
	except:
	    print ''
        self.play_thread_id = thread.start_new_thread(self.play_thread, ())

    def play_thread(self):
        play_thread_id = self.play_thread_id
        while play_thread_id == self.play_thread_id:
            if play_thread_id == self.play_thread_id:
                self.update_info_section()
            time.sleep(1)
    
    def stop(self,widget=None):
        self.player.stop()
        self.play_btn_pb.set_from_pixbuf(self.play_icon)
        self.pause_btn_pb.set_from_pixbuf(self.pause_icon)
        self.duration = None
        self.play_thread_id = None
        self.active_link = None
        self.movie_window.queue_draw()
        bit=_('Bitrate:')
        enc=_('Encoding:')
        play_label=_('Playing:')
        gobject.idle_add(self.media_name_label.set_markup,'<small><b>%s</b></small>' % self.play_label)
        gobject.idle_add(self.media_bitrate_label.set_markup,'<small><b>%s </b></small>' % self.bitrate_label)
        gobject.idle_add(self.media_codec_label.set_markup,'<small><b>%s </b></small>' % self.codec_label)
    
    def on_volume_changed(self, widget, value=10):
        self.player._player.set_property("volume", float(value))
        return True
    
    def pause(self,widget=None):
	if self.player.state == STATE_PAUSED:
            self.player.play()
	    self.pause_btn_pb.set_from_pixbuf(self.pause_icon)
        else:
	    self.player.pause()
	    self.pause_btn_pb.set_from_pixbuf(self.play_icon)
        
    def play_cache(self, data, size=None, name=None):
	cache = None
	markup = None
	try:
	    cache = Cache(data.stream.data, data.stream.size)
	except:
	    #cache = Cache(data, size)
	    self.test_mplayer(data)
	if name is None:
	    markup = '<small><b>%s %s - %s </b></small>' % (self.play_label,data.artist.name, data.name)
	else:
	    markup = '<small><b>%s %s </b></small>' % (self.play_label, name)
	self.player.play_cache(cache)
	self.play_btn_pb.set_from_pixbuf(self.stop_icon)
        gobject.idle_add(self.media_name_label.set_markup,markup)
        gobject.idle_add(self.media_bitrate_label.set_markup,'<small><b>%s %s</b></small>' % (self.bitrate_label, '...'))
        gobject.idle_add(self.media_codec_label.set_markup,'<small><b>%s %s</b></small>' % (self.codec_label, 'mp3'))
    
    
    def test_mplayer(self,d):
	import tempfile, subprocess
	output = tempfile.NamedTemporaryFile(suffix='.mp3', prefix='grooveshark_')
	process = None
	try:
	    output.write(d.read(524288))
	    process = subprocess.Popen(['/usr/bin/mplayer',output.name], stdout=None, stderr=None)
	    data = d.read(2048)
	    while data:
		output.write(data)
		data = d.read(2048)
	    process.wait()
	except KeyboardInterrupt:
	    if process:
		process.kill()
	output.close()
    
    
    def on_drawingarea_realized(self, sender):
        if sys.platform == "win32":
            window = self.movie_window.get_window()
            window.ensure_native()
            self.videosink.set_xwindow_id(self.movie_window.window.handle)
        else:
            gobject.idle_add(self.player.videosink.set_xwindow_id,self.movie_window.window.xid)

    def on_expose_event(self, widget, event):
        if self.player.state == STATE_PLAYING:
            return
        x , y, self.area_width, self.area_height = event.area
        widget.window.draw_drawable(widget.get_style().fg_gc[gtk.STATE_NORMAL],
                                      pixmap, x, y, x, y, self.area_width, self.area_height)
        if self.mainGui.draw_text:
            try:
                self.mainGui.search_engine.print_media_infos()
            except:
                return False
        return False
    
    def on_configure_event(self, widget, event):         
		global pixmap
		x, y, width, height = widget.get_allocation()
		pixmap = gtk.gdk.Pixmap(widget.window, width, height)
		pixmap.draw_rectangle(widget.get_style().black_gc,
								True, 0, 0, width, height)
		
		return True
    
    def on_motion_notify(self, widget, event):
        visible =  self.mainGui.miniPlayer.get_property("visible")
        self.timer = 0
        if self.mainGui.fullscreen and not self.mainGui.mini_player and not visible:
            self.mainGui.show_mini_player()
    
    def on_drawingarea_clicked(self, widget, event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            return self.mainGui.set_fullscreen()
    
    def on_message(self, bus, message):
        if self.mainGui.search_engine.engine_type == "video":
            self.player.videosink.set_property('force-aspect-ratio', True)
        
        t = message.type
        if t == gst.MESSAGE_EOS:
            self.play_thread_id = None
            self.pause_btn_pb.set_from_pixbuf(self.pause_icon)
            self.play_btn_pb.set_from_pixbuf(self.stop_icon)
	    gobject.idle_add(self.player.emit, 'finished')
            self.check_play_options()
        elif t == gst.MESSAGE_ERROR:
            err, debug = message.parse_error()
            print "Error: %s" % err, debug
            self.play_thread_id = None
            self.pause_btn_pb.set_from_pixbuf(self.pause_icon)
            self.play_btn_pb.set_from_pixbuf(self.stop_icon)
            ## continue if continue option selected...
            if self.play_options == "continue":
                self.check_play_options()
    
    def on_message_buffering(self, bus, message):
	percent = message.parse_buffering()
	if math.floor(percent/5) > self._cbuffering:
	    self._cbuffering = math.floor(percent/5)
	    buffering = _('Buffering :')
	    self.status = STATE_BUFFERING
	    gobject.idle_add(self.media_name_label.set_markup,'<small><b>%s</b> %s%s</small>' % (buffering,percent,'%'))
	
	if percent == 100:
	    if self.player.state == STATE_PAUSED:
		self.mainGui.info_label.set_text('')
		name = markup_escape_text(self.mainGui.media_name)
		gobject.idle_add(self.media_name_label.set_markup,'<small><b>%s</b> %s</small>' % (self.play_label,name))
		self.media_bitrate_label.set_markup('<small><b>%s </b> %s</small>' % (self.bitrate_label,self.media_bitrate))
		self.media_codec_label.set_markup('<small><b>%s </b> %s</small>' % (self.codec_label,self.media_codec))
		self.status = STATE_PLAYING
		self.pause()
	    self._cbuffering = -1
	elif self.status == STATE_BUFFERING:
	    if not self.player.state == STATE_PAUSED:
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
		self.old_name = self.media_name
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
			self.model.set_value(self.selected_iter, 1, self.media_markup)
			self.file_tags = tags
		except:
			return
				
    def on_sync_message(self, bus, message):
        if message.structure is None:
            return
        win_id = None
        message_name = message.structure.get_name()
        if message_name == "prepare-xwindow-id":
            if sys.platform == "win32":
                win_id = self.movie_window.window.handle
            else:
                win_id = self.movie_window.window.xid
            self.player.videosink.set_xwindow_id(win_id)
	    
	    
    def set_play_options(self,widget):
	wname = widget.name
	wstate = widget.get_active()
	if wname == "shuffle_btn":
		if wstate:
		    self.play_options = "shuffle"
		    if not self.shuffle_btn.get_active():
			self.shuffle_btn.set_active(1)
		    if self.loop_btn.get_active():
			self.loop_btn.set_active(0)
		else:
		    if self.loop_btn.get_active():
			self.play_options = "loop"
		    else:
			self.play_options = "continue"
	elif wname == "repeat_btn":
	    if wstate:
		self.play_options = "loop"
		if not self.loop_btn.get_active():
			self.loop_btn.set_active(1)
		if self.shuffle_btn.get_active():
			self.shuffle_btn.set_active(0)
	    else:
		if self.shuffle_btn.get_active():
			self.play_options = "shuffle"
		else:
			self.play_options = "continue"
	else:
	    self.play_options = "continue"
		
    def check_play_options(self):
	self.player.stop()
	self.selected_iter = self.mainGui.selected_iter
	path = self.mainGui.model.get_path(self.selected_iter)
	self.path = self.mainGui.path
	model = None
	treeview = None
	if path:
	    model = self.mainGui.model
	    treeview = self.mainGui.treeview
	else:
	    model = self.mainGui.Playlist.treestore
	    path = model.get_path(self.selected_iter)
	    treeview = self.mainGui.Playlist.treeview
			
	if self.play_options == "loop":
	    path = model.get_path(self.selected_iter)
	    if path:
		treeview.set_cursor(path)
		self.mainGui.get_model()
	elif self.play_options == "continue":
	    ## first, check if iter is still available (changed search while
	    ## continue mode for exemple..)
	    ## check for next iter
	    try:
		if not model.get_path(self.selected_iter) == self.path:
		    try:
			self.selected_iter = model.get_iter_first()
			if self.selected_iter:
			    path = model.get_path(self.selected_iter)
			    treeview.set_cursor(path)
			    self.mainGui.get_model()
		    except:
			    return
		else:
		    try:
			self.selected_iter = model.iter_next(self.selected_iter)
			path = model.get_path(self.selected_iter)
			treeview.set_cursor(path)
			self.mainGui.get_model()
		    except:
			if not self.mainGui.playlist_mode:
			    self.mainGui.load_new_page()
	    except:
		if not self.mainGui.playlist_mode:
		    self.mainGui.load_new_page()
	
	elif self.play_options == "shuffle":
	    num = random.randint(0,len(model))
	    self.selected_iter = model[num].iter
	    path = model.get_path(self.selected_iter)
	    treeview.set_cursor(path)
	    self.mainGui.get_model()
	    
    def update_info_section(self):
        """
        Update the time_label to display the current location
        in the media file as well as update the seek bar
        """
	if self.seeker_move == 1 or self.status == STATE_BUFFERING:
	    return
	    
        if self.player.state != STATE_PLAYING:
            adjustment = gtk.Adjustment(0, 0.00, 100.0, 0.1, 1.0, 1.0)
            self.seeker.set_adjustment(adjustment)
            gobject.idle_add(self.time_label.set_text,"00:00 / 00:00")
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
            gobject.idle_add(self.time_label.set_text,current_position_formated + "/" + self.duration)
        
            # Update the seek bar
            # gtk.Adjustment(value=0, lower=0, upper=0, step_incr=0, page_incr=0, page_size=0)
            percent = (float(self.current_position)/float(self.length))*100.0
            adjustment = gtk.Adjustment(percent, 0.00, 100.0, 0.1, 1.0, 1.0)
            self.seeker.set_adjustment(adjustment)
        
        return True
	

    def seeker_button_release_event(self, widget, event):
        value = widget.get_value()
	duration = self.player._player.query_duration(self.timeFormat, None)[0]
	time = value * (duration / 100)
	self.player._player.seek_simple(self.timeFormat, gst.SEEK_FLAG_FLUSH, time)
	self.seeker_move = None
	#self.pause()

    def seeker_block(self,widget,event):
        self.seeker_move = 1
	#~ if not self.player.state == gplayer.STATE_PAUSED:
            #~ self.pause()
