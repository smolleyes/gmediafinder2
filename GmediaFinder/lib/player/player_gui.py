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
gobject.threads_init()
import thread

## custom lib
try:
    import lib.config as config
    from lib.player.player_engine import *
    from lib.functions import *
    from lib.pykey import send_string
    from lib.player.player_engine import *
except:
    from GmediaFinder.lib.functions import *
    from GmediaFinder.lib import config
    from GmediaFinder.lib.player.player_engine import *
    from GmediaFinder.lib.pykey import send_string
    from GmediaFinder.lib.player.player_engine import *
    
GST_STATE_VOID_PENDING        = 0
GST_STATE_NULL                = 1
GST_STATE_READY               = 2
GST_STATE_PAUSED              = 3
GST_STATE_PLAYING             = 4

gtk.gdk.threads_init()

class Player(gobject.GObject):
    UPDATE_INTERVAL = 500
    
    def __init__(self,mainGui):
	self.timer = 0
        self.gladeGui = mainGui.gladeGui
        self.time_label = gtk.Label("00:00 / 00:00")
        self.media_name = ""
        self.media_link = ""
        self.mainGui = mainGui
	self.xsink = False
	self.media_codec = ""
	self.old_link = None
	self.play_thread_id = None
	## play mode options
	self.play_options = "continue"
        
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
	self.movie_window.realize()
        
        # seekbar and signals
        self.control_box = self.gladeGui.get_widget("control_box")
        self.seekbox = self.gladeGui.get_widget("seekbox")
        self.adjustment = gtk.Adjustment(0.0, 0.00, 100.0, 0.1, 1.0, 1.0)
        self.seeker = gtk.HScale(self.adjustment)
        self.seeker.set_draw_value(False)
        self.seeker.set_update_policy(gtk.UPDATE_CONTINUOUS)
        self.seekbox.add(self.seeker)
        self.seeker.connect("button-release-event", self.scale_button_release_cb)
        self.seeker.connect("button-press-event", self.scale_button_press_cb)
	self.seeker.connect('format-value', self.scale_format_value_cb)
	self.seekmove = False
        #timer
        self.timerbox = self.gladeGui.get_widget("timer_box")
        self.timerbox.add(self.time_label)
        ## seekbar infos
        self.media_name_label = self.gladeGui.get_widget("media_name")
        self.media_name_label.set_property('ellipsize', pango.ELLIPSIZE_END)
        self.media_codec_label = self.gladeGui.get_widget("media_codec")
        self.media_bitrate_label = self.gladeGui.get_widget("media_bitrate")
	
	## mini player
	width = gtk.gdk.screen_width()
	height = gtk.gdk.screen_height()
        self.miniPlayer = self.gladeGui.get_widget("mini-player")
        self.miniPlayer.set_size_request(width,40)
        self.miniPlayer.move(0,height-42)
        self.miniPlayer_init = False
        self.miniPlayer.set_keep_above(True)
        #self.miniPlayer.set_transient_for(self.mainGui.window)
        self.infobox = self.gladeGui.get_widget("btn_info_box")
        self.infobox_cont = self.gladeGui.get_widget("btn_infobox_cont")
        self.mini_infobox_cont = self.gladeGui.get_widget("mini_infobox_cont")
	self.fullscreen = False
        self.mini_player = False
        ## btn box
        self.btn_box = self.gladeGui.get_widget("btn_box")
        self.btn_box_cont = self.gladeGui.get_widget("btn_box_cont")
        self.mini_btn_box_cont = self.gladeGui.get_widget("mini_btn_box_cont")
        
        self.mini_seekbox = self.gladeGui.get_widget("mini_seekbox_cont")
	
        ## SIGNALS
        dic = {
        "on_pause_btn_clicked" : self.pause_resume,
        "on_shuffle_btn_toggled" : self.set_play_options,
        "on_repeat_btn_toggled" : self.set_play_options,
        "on_vol_btn_value_changed" : self.on_volume_changed,
	"on_media_notebook_switch_page" : self.refresh_screen,
	"on_vis_chooser_changed" : self.change_visualisation,
        }
        self.gladeGui.signal_autoconnect(dic)
        #### load buttons and pixbufs
        self.load_gui_icons()
        #### init gst gplayer engine
        self.player = GstPlayer(mainGui,self)
	self.radio_mode = False
	self.media_codec = None
	
	## visualisations
        vis = 'goom'
	try:
            self.vis = self.mainGui.conf["visualisation"]
        except:
            self.mainGui.conf["visualisation"] = vis
            self.vis = vis
            self.mainGui.conf.write()
        combo = self.gladeGui.get_widget("vis_chooser")
        self.vis_selector = ComboBox(combo)
	if self.vis:
	    self.vis_selector.setIndexFromString(self.vis)
	else:
	    self.vis_selector.select(1)
	    
	##gplayer
	self.active_link=None
	def on_eos():
            self.player.seek(0L)
            self.play_toggled()
        self.player.on_eos = lambda *x: on_eos()
        
        self.update_id = -1
        self.changed_id = -1
        self.seek_timeout_id = -1

        self.p_position = gst.CLOCK_TIME_NONE
        self.p_duration = gst.CLOCK_TIME_NONE
	
	self.player.connect("fill-status-changed", self._fill_status_changed)
	self.player.connect('finished', self.on_finished)
	
    @property
    def state(self):
	return self.player.get_state()
    
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
        self.play_btn.set_property('can-default', True)
        self.play_btn.set_focus_on_click(False)
        self.play_btn.set_property('has-default', True)
        self.play_btn.connect('clicked', lambda *args: self.play_toggled())
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
        self.fullscreen_btn.connect('clicked', self.set_fullscreen)
        self.fullscreen_btn.set_tooltip_text(_("enter fullscreen"))
        self.changepage_btn.set_sensitive(0)
        self.pageback_btn.set_sensitive(0)
	
	self.bitrate_label =_('Bitrate:')
        self.codec_label =_('Encoding:')
        self.play_label =_('Playing:')
	self.seekmove= False
	

    def change_visualisation(self, widget=None):
        vis = self.vis_selector.getSelected()
        visi = self.vis_selector.getSelectedIndex()
        if vis != "goom" and visi != 0 :
            self.vis = "libvisual_"+vis
        else:
            self.vis = vis
        self.mainGui.conf["visualisation"] = vis
        self.mainGui.conf.write()
        return self.vis
    
    def play_toggled(self,url=None):
        if self.player.get_state() == GST_STATE_PLAYING:
            self.stop()
        else:
            self.start_play(url)
    
    def stop(self,widget=None):
	self.play_thread_id = None
	self.radio_mode = False
	self.active_link = None
	self.player.stop()
        gobject.idle_add(self.play_btn_pb.set_from_pixbuf,self.play_icon)
        gobject.idle_add(self.pause_btn_pb.set_from_pixbuf,self.pause_icon)
        bit=_('Bitrate:')
        enc=_('Encoding:')
        play_label=_('Playing:')
        gobject.idle_add(self.media_name_label.set_markup,'<small><b>%s</b></small>' % self.play_label)
        gobject.idle_add(self.media_bitrate_label.set_markup,'<small><b>%s </b></small>' % self.bitrate_label)
        gobject.idle_add(self.media_codec_label.set_markup,'<small><b>%s </b></small>' % self.codec_label)
	gobject.idle_add(self.seeker.set_value,0)
	gobject.idle_add(self.time_label.set_text,"00:00 / 00:00")
	gobject.idle_add(self.refresh_screen)
	gobject.idle_add(self.play_btn_pb.set_from_pixbuf,self.play_icon)
	gobject.idle_add(self.seeker.set_fill_level,0.0)
	self.seeker.set_show_fill_level(True)
    

    def pause_resume(self,widget=None):
        if self.player.get_state() == GST_STATE_PLAYING:
	    self.player.pause()
            gobject.idle_add(self.pause_btn_pb.set_from_pixbuf,self.play_icon)
        else:
            self.player.play()
	    gobject.idle_add(self.pause_btn_pb.set_from_pixbuf,self.pause_icon)
        
    def shutdown(self):
	self.player.shutdown()
    
    
    def on_drawingarea_realized(self, sender):
        if sys.platform == "win32":
            window = self.movie_window.get_window()
            window.ensure_native()
	    try:
		gobject.idle_add(self.player.set_window_id,self.movie_window.window.handle)
	    except:
		return
        else:
	    try:
		gobject.idle_add(self.player.set_window_id,self.movie_window.window.xid)
	    except:
		return

    def refresh_screen(self, widget=None, page_num=None, param=None):
	x , y = self.movie_window.get_size_request()
        try:
	    gobject.idle_add(self.movie_window.window.draw_drawable,self.movie_window.get_style().fg_gc[gtk.STATE_NORMAL],
                                      pixmap, x, y, x, y, x,y)
	    gobject.idle_add(self.mainGui.media_notebook.queue_draw_area,0,0,-1,-1)
	except:
	    return
    
    def on_expose_event(self, widget, event):
        if self.player.get_state == gst.STATE_PLAYING and self.mainGui.search_engine.engine_type == 'video':
            return
        x , y, self.area_width, self.area_height = event.area
        gobject.idle_add(widget.window.draw_drawable,widget.get_style().fg_gc[gtk.STATE_NORMAL],
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
		gobject.idle_add(pixmap.draw_rectangle,widget.get_style().black_gc,
								True, 0, 0, width, height)
		
		return True
    
    def on_motion_notify(self, widget, event):
        visible =  self.miniPlayer.get_property("visible")
	self.timer = 0
        if self.fullscreen and not self.mini_player and not visible:
            self.show_mini_player()
    
    def on_drawingarea_clicked(self, widget, event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.set_fullscreen()
	    
    def on_finished(self,widget):
	print 'file finished'
	self.stop()
	try:
	    self.check_play_options()
	except:
	    return
    
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
	print "play option : %s" % self.play_options
	try:
	    self.selected_iter = self.mainGui.selected_iter
	    path = self.mainGui.model.get_path(self.selected_iter)
	except:
	    return
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
			self.stop()
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
			else:
			    self.stop()
	    except:
		if not self.mainGui.playlist_mode:
		    self.mainGui.load_new_page()
		else:
		    self.stop()
	
	elif self.play_options == "shuffle":
	    num = random.randint(0,len(model))
	    self.selected_iter = model[num].iter
	    path = model.get_path(self.selected_iter)
	    treeview.set_cursor(path)
	    self.mainGui.get_model()
	
    def set_fullscreen(self,widget=None):
        self.timer = 0
        if self.fullscreen :
            gobject.idle_add(self.miniPlayer.hide)
            self.btn_box.reparent(self.btn_box_cont)
            self.infobox.reparent(self.infobox_cont)
            gobject.idle_add(self.mainGui.search_box.show)
            gobject.idle_add(self.mainGui.results_notebook.show)
	    gobject.idle_add(self.mainGui.media_notebook.set_show_tabs,0)
            gobject.idle_add(self.control_box.show)
            gobject.idle_add(self.mainGui.options_bar.show)
            self.mainGui.window.window.set_cursor(None)
            gobject.idle_add(self.mainGui.window.window.unfullscreen)
            gobject.idle_add(self.mainGui.window.set_position,gtk.WIN_POS_CENTER)
            if sys.platform == 'win32':
                self.mainGui.window.set_decorated(True)
            self.fullscreen = False
            gobject.idle_add(self.fullscreen_btn_pixb.set_from_pixbuf,self.fullscreen_pix)
            gobject.idle_add(self.fullscreen_btn_pixb.set_tooltip_text,_('enter fullscreen'))
        else:
            gobject.idle_add(self.mainGui.search_box.hide)
            gobject.idle_add(self.mainGui.results_notebook.hide)
	    gobject.idle_add(self.mainGui.media_notebook.set_show_tabs,0)
            gobject.idle_add(self.mainGui.options_bar.hide)
            self.btn_box.reparent(self.mini_btn_box_cont)
            self.infobox.reparent(self.mini_infobox_cont)
            pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
            color = gtk.gdk.Color()
            cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
            self.mainGui.window.window.set_cursor(cursor)
            gobject.idle_add(self.control_box.hide)
            gobject.idle_add(self.mainGui.window.window.fullscreen)
            if sys.platform == 'win32':
                self.mainGui.window.set_decorated(False)
            self.fullscreen = True
            self.mini_player = False
            gobject.idle_add(self.fullscreen_btn_pixb.set_from_pixbuf,self.leave_fullscreen_pix)
            gobject.idle_add(self.fullscreen_btn_pixb.set_tooltip_text,_('leave fullscreen'))
	    
    def show_mini_player(self):
	self.timer = 0
        visible =  self.miniPlayer.get_property("visible")
        if self.mini_player and visible :
            gobject.idle_add(self.miniPlayer.hide)
            self.mini_player = False
            pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
            color = gtk.gdk.Color()
            cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
            try:
                self.mainGui.window.window.set_cursor(cursor)
            except:
                return
        else:
            if not visible:
                gobject.idle_add(self.miniPlayer.show)
            self.mini_player = True
            try:
		self.mainGui.window.window.set_cursor(None)
            except:
                return
		
    def start_play(self, location):
	if not sys.platform == "win32":
            if not self.vis_selector.getSelectedIndex() == 0 and self.mainGui.search_engine.engine_type != "video":
		self.player.player.set_property('flags', 0x00000008|0x00000002|0x80)
		self.vis = self.change_visualisation()
                self.visual = gst.element_factory_make(self.vis,'visual')
                self.player.player.set_property('vis-plugin', self.visual)
	    else:
		self.player.player.set_property('flags', 0x00000001|0x00000002|0x80)
	self.player.file_tags = {}
	self.active_link = location
	gobject.idle_add(self.play_btn_pb.set_from_pixbuf,self.stop_icon)
	gobject.idle_add(self.pause_btn_pb.set_from_pixbuf,self.pause_icon)

	if self.update_id == -1:
	    self.update_id = gobject.timeout_add(self.UPDATE_INTERVAL,
                                                     self.update_scale_cb)
	try:
	    gobject.idle_add(self.media_name_label.set_markup,'<small><b>%s</b> %s</small>' % (self.play_label,self.mainGui.media_name))
	except:
	    print ''
	try:
	    self.play_thread.stop()
	except:
	    print ''
	self.player.set_location(location)
	self.player.play()
	self.play_thread_id = thread.start_new_thread(self.play_thread, ())
    
    def play_thread(self):
	play_thread_id = self.play_thread_id
	while play_thread_id == self.play_thread_id:
	    if play_thread_id == self.play_thread_id:
		if not self.seekmove:
			self.update_infos()
	    time.sleep(1)
	    
    def update_infos(self):
        """
        Update the time_label to display the current location
        in the media file as well as update the seek bar
        """
	#print "---------------update_info-----------------"
	#print "state : %s" % self.state
	if self.player.get_state() != GST_STATE_PLAYING:
	    return
	    
        if self.player.get_state() == GST_STATE_READY:
            adjustment = gtk.Adjustment(0, 0.00, 100.0, 0.1, 1.0, 1.0)
            self.seeker.set_adjustment(adjustment)
            gobject.idle_add(self.time_label.set_text,"00:00 / 00:00")
            return False
	    
	try:
	    self.media_codec = self.media_codec
	    gobject.idle_add(self.media_bitrate_label.set_markup,'<small><b>%s </b> %s</small>' % (self.bitrate_label,self.player.media_bitrate))
	    gobject.idle_add(self.media_codec_label.set_markup,'<small><b>%s </b> %s</small>' % (self.codec_label,self.player.media_codec))
	except:
	    gobject.idle_add(self.media_bitrate_label.set_markup,'<small><b>%s </b> %s</small>' % (self.bitrate_label,'unknown'))
	    gobject.idle_add(self.media_codec_label.set_markup,'<small><b>%s </b> %s</small>' % (self.codec_label,'unknown'))

        ## update timer for mini_player and hide it if more than 5 sec
        ## without mouse movements
        self.timer += 1
        if self.fullscreen and self.mini_player and self.timer > 4:
            self.show_mini_player()
        
        ## disable screensaver
        if self.fullscreen == True and self.mini_player == False and self.timer > 55:
            if sys.platform == "win32":
                win32api.keybd_event(7,0,0,0)
            else:
                send_string('a')
            self.timer = 0
	## update seekbar timer label
	f_duration = self.convert_ns(self.p_duration)
	f_position = self.convert_ns(self.p_position)
	gobject.idle_add(self.time_label.set_text,f_position + "/" + f_duration)
    
	return True
    
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
    
    def scale_format_value_cb(self, scale, value):
        if self.p_duration == -1:
            real = 0
        else:
            real = value * self.p_duration / 100
        
        seconds = real / gst.SECOND
	return "%02d:%02d" % (seconds / 60, seconds % 60)

    def scale_button_press_cb(self, widget, event):
        # see seek.c:start_seek
        gst.debug('starting seek')
        self.seekmove = True
        self.was_playing = self.player.is_playing()
        if self.was_playing:
            self.pause_resume()

        # don't timeout-update position during seek
        if self.update_id != -1:
            gobject.source_remove(self.update_id)
            self.update_id = -1

        # make sure we get changed notifies
        if self.changed_id == -1:
            self.changed_id = self.seeker.connect('value-changed',
                self.scale_value_changed_cb)
            
    def scale_value_changed_cb(self, scale):
        # see seek.c:seek_cb
        real = long(scale.get_value() * self.p_duration / 100) # in ns
        gst.debug('value changed, perform seek to %r' % real)
        self.player.seek(real)
        # allow for a preroll
        self.player.get_state(timeout=50*gst.MSECOND,full=True) # 50 ms

    def scale_button_release_cb(self, widget, event):
        # see seek.cstop_seek
        widget.disconnect(self.changed_id)
        self.changed_id = -1
	self.seekmove = False
        if self.seek_timeout_id != -1:
            gobject.source_remove(self.seek_timeout_id)
            self.seek_timeout_id = -1
        else:
            gst.debug('released slider, setting back to playing')
            if self.was_playing:
                self.pause_resume()

        if self.update_id != -1:
            self.error('Had a previous update timeout id')
        else:
            self.update_id = gobject.timeout_add(self.UPDATE_INTERVAL,
                self.update_scale_cb)

    def update_scale_cb(self):
        self.p_position, self.p_duration = self.player.query_position()
        if self.p_position != gst.CLOCK_TIME_NONE:
            value = self.p_position * 100.0 / self.p_duration
            self.adjustment.set_value(value)
	
        return True


    def on_volume_changed(self,widget,value):
	self.player.player.set_property("volume", float(value))
    
    def _fill_status_changed(self, player, fill_value):
        gobject.idle_add(self.seeker.set_fill_level,fill_value)
        self.seeker.set_show_fill_level(True)
		
