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
from lib.player.player_engine import *
## custom lib
try:
    import lib.config as config
    from lib.player.player_engine import *
    from lib.functions import *
except:
    from GmediaFinder.lib.functions import *
    from GmediaFinder.lib import config
    from GmediaFinder.lib.player.player_engine import *

class Player(object):
    def __init__(self,mainGui):
	self.timer = 0
        self.gladeGui = mainGui.gladeGui
        self.time_label = gtk.Label("00:00 / 00:00")
        self.media_name = ""
        self.media_link = ""
        self.mainGui = mainGui
	self.xsink = False
	self.media_codec = None
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
        self.seeker.set_update_policy(gtk.UPDATE_DISCONTINUOUS)
        self.seekbox.add(self.seeker)
        self.seeker.connect("button-release-event", self.on_seeker_release)
        self.seeker.connect("button-press-event", self.on_seeker_move)
	self.seekmove = None
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
        self.player = PlayerEngine(mainGui,self)
	self.radio_mode = False
	self.is_playing = False
	
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
	
    @property
    def state(self):
	return self.player.state
    
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
        self.fullscreen_btn.connect('clicked', self.set_fullscreen)
        self.fullscreen_btn.set_tooltip_text(_("enter fullscreen"))
        self.changepage_btn.set_sensitive(0)
        self.pageback_btn.set_sensitive(0)
	
	self.bitrate_label =_('Bitrate:')
        self.codec_label =_('Encoding:')
        self.play_label =_('Playing:')
	self.seekmove= False
         
    def start_stop(self,widget=None):
        if widget:
            if self.player.state == 3:
		try:
		    self.mainGui.get_model()
		except:
		    self.stop()
	    else:
		self.stop()
        else:
            if self.active_link:
                if self.player.state == 3:
                    self.start_play(self.active_link)
                else:
                    self.stop()

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
    
    def start_play(self,url):
	if self.state != 3:
	    self.stop()
        self.active_link = url
        self.file_tags = {}
	try:
	    gobject.idle_add(self.media_name_label.set_markup,'<small><b>%s</b> %s</small>' % (self.play_label,self.mainGui.media_name))
	except:
	    print ''
	self.play_thread_id = thread.start_new_thread(self.play_thread, ())

    def play_thread(self,cache=None,length=None):
	if not sys.platform == "win32":
            if not self.vis_selector.getSelectedIndex() == 0 and self.mainGui.search_engine.engine_type != "video":
		self.player.engine.player._player.set_property('flags', 0x00000008|0x00000002)
		self.vis = self.change_visualisation()
                self.visual = gst.element_factory_make(self.vis,'visual')
                self.player.engine.player._player.set_property('vis-plugin', self.visual)
	    else:
		self.player.engine.player._player.set_property('flags', 0x00000001|0x00000002)
	gobject.idle_add(self.pause_btn_pb.set_from_pixbuf,self.pause_icon)
	gobject.idle_add(self.play_btn_pb.set_from_pixbuf,self.stop_icon)
	self.is_playing = True
	gobject.idle_add(self.seeker.set_sensitive,1)
        play_thread_id = self.play_thread_id
	if cache:
	    self.player.play_cache(cache,length)
	else:
	    self.player.play_url(self.active_link)
        while play_thread_id == self.play_thread_id and self.is_playing:
            if play_thread_id == self.play_thread_id:
		if not self.seekmove:
		    self.player.update_info_section()
            time.sleep(1)
    
    def stop(self,widget=None):
	self.play_thread_id = None
	self.is_playing = False
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
	self.refresh_screen()
    
    
    def on_volume_changed(self, widget, value=10):
        self.player.set_volume(value)
    
    def pause_resume(self,widget=None):
        if not self.state == 2:
            self.pause_btn_pb.set_from_pixbuf(self.play_icon)
            self.player.pause()
        else:
            self.player.play()
        
    def shutdown(self):
	self.player.shutdown()
    
    def play_cache(self, data, size=None, name=None):
	if self.state != 3:
	    self.stop()
	cache = None
	markup = None
	if name is None:
	    try:
		markup = '<small><b>%s %s - %s </b></small>' % (self.play_label,data.artist.name, data.name)
	    except:
		markup = '<small><b>%s </b></small>' % (self.play_label)
	else:
	    markup = '<small><b>%s %s </b></small>' % (self.play_label, name)
	self.play_btn_pb.set_from_pixbuf(self.stop_icon)
	try:
	    gobject.idle_add(self.media_name_label.set_markup,'<small><b>%s</b> %s</small>' % (self.play_label,self.mainGui.media_name))
	except:
	    gobject.idle_add(self.media_name_label.set_markup,markup)
        gobject.idle_add(self.media_bitrate_label.set_markup,'<small><b>%s %s</b></small>' % (self.bitrate_label, ''))
        gobject.idle_add(self.media_codec_label.set_markup,'<small><b>%s %s</b></small>' % (self.codec_label, ''))
	self.play_thread_id = thread.start_new_thread(self.play_thread, (data,))
    
    
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
        if self.player.state == STATE_PLAYING and self.mainGui.search_engine.engine_type == 'video':
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
        visible =  self.miniPlayer.get_property("visible")
	self.timer = 0
        if self.fullscreen and not self.mini_player and not visible:
            self.show_mini_player()
    
    def on_drawingarea_clicked(self, widget, event):
        if event.type == gtk.gdk._2BUTTON_PRESS:
            self.set_fullscreen()
	    
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
	    
    def on_seeker_release(self, widget, event):
	self.seekmove = False
	value = widget.get_value()
	self.player.on_seeker_release(value)
	
    def on_seeker_move(self, widget, event):
	self.seekmove = True
	if not self.state == STATE_PAUSED:
            self.pause_resume()
	
    def set_fullscreen(self,widget=None):
        self.timer = 0
        if self.fullscreen :
            self.miniPlayer.hide()
            self.btn_box.reparent(self.btn_box_cont)
            self.infobox.reparent(self.infobox_cont)
            gobject.idle_add(self.mainGui.search_box.show)
            gobject.idle_add(self.mainGui.results_notebook.show)
	    gobject.idle_add(self.mainGui.media_notebook.set_show_tabs,1)
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
		
