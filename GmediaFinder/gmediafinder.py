#!/usr/bin/env python
#-*- coding: UTF-8 -*-

import sys
import glib
import pango
import os
import thread
import threading
import random
import time
import gobject
import pygtk
pygtk.require('2.0')
import gtk
import gtk.glade
import gtk.gdk
import urllib
import pygst
pygst.require("0.10")
import gst
import mechanize
import gdata
import math
## for win32...py2exe
import json
import gdata.youtube.service as yt_service
import gettext
import time
import locale
import Queue
import cairo
import pangocairo

if sys.platform == "win32":
    import win32api
## custom lib
try:
    import debrid as debrider
    from downloads import downloader
    from player.player import Player
    from config import *
    from engines import Engines
    from functions import *
    from playlist import Playlist
    if sys.platform != "win32":
        from pykey import send_string
    import checklinks as checkLink
except:
    from GmediaFinder.config import *
    from GmediaFinder.engines import Engines
    from GmediaFinder.functions import *
    from GmediaFinder.playlist import Playlist
    if sys.platform != "win32":
        from GmediaFinder.pykey import send_string
    import GmediaFinder.debrid as debrider
    import GmediaFinder.checklinks as checkLink

class GsongFinder(object):
    def __init__(self):
        ## default search options
        self.is_playing = False
        self.is_paused = False
        self.nbresults = 100
        self.user_search = ""
        self.fullscreen = False
        self.mini_player = True
        self.showed = True ## trayicon
        self.timer = 0
        self.settings_folder = None
        self.conf_file = None
        self.active_downloads = 0
        self.thread_num = 0
        self.engine_list = {}
        self.engine = None
        self.conf=conf
        self.latest_engine = ""
        self.change_page_request = False
        self.tray = None
        self.download_pool = []
        self.media_bitrate= None
        self.media_codec= None
        self.playlist_mode = False
        self.play = False
        self.draw_text = False
        self.url_checker = checkLink.CheckLinkIntegrity()
        self.url_debrid = debrider.Debrid(self)
        
        ## main gui
        self.gladeGui = gtk.glade.XML(glade_file, None ,APP_NAME)
        self.window = self.gladeGui.get_widget("main_window")
        self.window.set_title("Gmediafinder")
        self.window.set_resizable(1)
        self.set_window_position()
        self.show_thumbs_opt_toggle = self.gladeGui.get_widget("show_thumbs_opt")
        if self.conf['show_thumbs'] == "True" :
            self.show_thumbs_opt_toggle.set_active(1)
        self.img_path = img_path
        self.window.set_icon_from_file(os.path.join(self.img_path,'gmediafinder.png'))
        self.window.connect('key-press-event', self.onKeyPress)
    
        
        # options menu
        self.options_bar = self.gladeGui.get_widget("options_bar")
        self.search_box = self.gladeGui.get_widget("search_box")
        self.results_box = self.gladeGui.get_widget("results_box")
        self.quality_box = self.gladeGui.get_widget("quality_box")

        ## throbber
        self.throbber = self.gladeGui.get_widget("throbber_img")
        animation = gtk.gdk.PixbufAnimation(self.img_path+'/throbber.gif')
        self.throbber.set_from_animation(animation)

        ## notebooks
        self.notebook = self.gladeGui.get_widget("notebook")
        self.results_notebook = self.gladeGui.get_widget("results_notebook")
        self.video_cont = self.gladeGui.get_widget("video_cont")

        self.search_entry = self.gladeGui.get_widget("search_entry")
        self.stop_search_btn = self.gladeGui.get_widget("stop_search_btn")
        ## playlist
        self.playlists_xml = playlists_xml
        self.playlist_scrollbox = self.gladeGui.get_widget("playlist_scrollbox")
        ## history
        self.search_entry.connect('changed',self.__search_history)
        self.history_view = gtk.EntryCompletion()
        self.history_view.set_minimum_key_length(1)
        self.search_entry.set_completion(self.history_view)
        self.history_model = gtk.ListStore(gobject.TYPE_STRING)
        self.history_view.set_model(self.history_model)
        self.history_view.set_text_column(0)
        ## options box
        self.search_opt_box = self.gladeGui.get_widget("search_options_box")

        ## statbar
        self.statbar = self.gladeGui.get_widget("statusbar")
        ## info
        self.info_label = self.gladeGui.get_widget("info_label")

        ## visualisations
        try:
            self.vis = self.conf["visualisation"]
        except:
            self.conf["visualisation"] = vis
            self.vis = vis
            self.conf.write()
        combo = self.gladeGui.get_widget("vis_chooser")
        self.vis_selector = ComboBox(combo)
        self.vis_selector.setIndexFromString(self.vis)

        ##extras options
        self.downloads_check = self.gladeGui.get_widget("downloads_enabled")
        self.convert_check = self.gladeGui.get_widget("convert_enabled")
        self.warn_dialog = self.gladeGui.get_widget("warn_dialog")
        self.systray_check = self.gladeGui.get_widget("systray_enabled")
        self.down_dir = down_dir
        if downloads == 'True':
            self.downloads_check.set_active(1)
        if convert == 'True':
            self.convert_check.set_active(1)
        if systray == 'True':
            self.systray_check.set_active(1)

        ## SIGNALS
        dic = {"on_main_window_destroy_event" : self.exit,
        "on_quit_menu_activate" : self.exit,
        "on_nextpage_btn_clicked" : self.change_page,
        "on_pageback_btn_clicked" : self.change_page,
        "on_search_entry_activate" : self.prepare_search,
        "on_vis_chooser_changed" : self.change_visualisation,
        "on_about_menu_clicked" : self.on_about_btn_pressed,
        "on_settings_menu_clicked" : self.on_settings_btn_pressed,
        "on_main_window_configure_event" : self.save_position,
        "on_search_entry_icon_press" : self.clear_search_entry,
        "on_show_thumbs_opt_toggled" : self.on_gui_opt_toggled,
        "on_stop_search_btn_clicked": self.stop_threads,
        "on_downloads_enabled_toggled" : self.set_extras_options,
        "on_convert_enabled_toggled" : self.set_extras_options,
        "on_systray_enabled_toggled" : self.set_extras_options,
        "on_clear_history_btn_clicked" : self.clear_history,
         }
        self.gladeGui.signal_autoconnect(dic)
        self.window.connect('destroy', self.exit)

        ## create main results treeview
        self.model = gtk.ListStore(gtk.gdk.Pixbuf,str,object,object,object,str,str,gtk.gdk.Pixbuf)
        self.treeview = gtk.TreeView()
        self.window.realize()
        self.odd = gtk.gdk.color_parse(str(self.window.style.bg[gtk.STATE_NORMAL]))
        self.even = gtk.gdk.color_parse(str(self.window.style.base[gtk.STATE_NORMAL]))
        self.treeview.set_model(self.model)

        rendererp = gtk.CellRendererPixbuf()
        pixcolumn = gtk.TreeViewColumn("",rendererp,  pixbuf=0)
        self.treeview.append_column(pixcolumn)

        rendertxt = gtk.CellRendererText()
        txtcolumn = gtk.TreeViewColumn("txt",rendertxt, markup=1)
        txtcolumn.set_cell_data_func(rendertxt, self.alternate_color)
        txtcolumn.set_title(_(' Results : '))
        self.treeview.append_column(txtcolumn)

        renderer = gtk.CellRendererText()
        pathColumn = gtk.TreeViewColumn("Link", renderer)
        self.treeview.append_column(pathColumn)

        qualityColumn = gtk.TreeViewColumn("Quality", renderer)
        self.treeview.append_column(qualityColumn)
        
        nameColumn = gtk.TreeViewColumn("Name", renderer)
        self.treeview.append_column(nameColumn)

        plugnameColumn = gtk.TreeViewColumn("Name", renderer)
        self.treeview.append_column(plugnameColumn)
        
        
        ## setup the scrollview
        self.results_scroll = self.gladeGui.get_widget("results_scrollbox")
        self.columns = self.treeview.get_columns()
        if self.conf['show_thumbs'] == "False":
            self.columns[0].set_visible(0)
        self.columns[1].set_sort_column_id(1)
        self.columns[2].set_visible(0)
        self.columns[3].set_visible(0)
        self.columns[4].set_visible(0)
        self.columns[5].set_visible(0)
        self.results_scroll.add(self.treeview)
        self.results_scroll.connect_after('size-allocate', self.resize_wrap, self.treeview, self.columns[1], rendertxt)
        
        ## right click menu
        self.search_playlist_menu = gtk.Menu()
        getlink_item = gtk.ImageMenuItem(gtk.STOCK_COPY)
        getlink_item.get_children()[0].set_label(_('Copy file link'))
        addplaylist_item = gtk.ImageMenuItem(gtk.STOCK_EDIT)
        addplaylist_item.get_children()[0].set_label(_('Add to Library'))
        self.search_playlist_menu.append(getlink_item)
        self.search_playlist_menu.append(addplaylist_item)
        getlink_item.connect('activate', self._copy_link)
        addplaylist_item.connect('activate', self._add_to_playlist)
        ## connect treeview signals
        self.search_playlist_menu_active = False
        self.treeview.connect('row-activated',self.get_model)
        self.treeview.connect('cursor-changed',self.on_treeview_clicked)
        self.treeview.connect('button-press-event',self._show_search_playlist_menu)

        ## engines
        self.dlg = self.gladeGui.get_widget("settings_dialog")
        self.engines_box = self.gladeGui.get_widget("engines_box")

        ## mini player
        self.miniPlayer = self.gladeGui.get_widget("mini-player")
        self.miniPlayer.set_size_request(width,40)
        self.miniPlayer.move(0,height-42)
        self.miniPlayer_init = False
        self.miniPlayer.set_keep_above(True)
        self.miniPlayer.set_transient_for(self.window)
        self.infobox = self.gladeGui.get_widget("btn_info_box")
        self.infobox_cont = self.gladeGui.get_widget("btn_infobox_cont")
        self.mini_infobox_cont = self.gladeGui.get_widget("mini_infobox_cont")
        ## btn box
        self.btn_box = self.gladeGui.get_widget("btn_box")
        self.btn_box_cont = self.gladeGui.get_widget("btn_box_cont")
        self.mini_btn_box_cont = self.gladeGui.get_widget("mini_btn_box_cont")
        
        self.mini_seekbox = self.gladeGui.get_widget("mini_seekbox_cont")
        
        ## create engines selector combobox
        box = self.gladeGui.get_widget("engine_selector_box")
        self.active_engines = create_comboBox()
        self.active_engines.connect("changed", self.set_engine)
        box.pack_start(self.active_engines, False,False,5)
        self.engine_selector = ComboBox(self.active_engines)
        self.engine_selector.append("")
        ## load playlists
        self.Playlist = Playlist(self)
        ## init player
        self.player = Player(self)
        
        ## check extra options
        if downloads == 'False':            
            self.down_btn.hide()
            self.down_menu_btn.hide()
        else:
            ## init downloader
            self.downloader = downloader.Downloader(self)
            self.downloader.download_treeview.columns_autosize()
        
        ## tray icon
        if systray == 'True':
            self.__create_trayicon()
        
        ## start gui
        self.window.show_all()
        self.throbber.hide()
        ## start engines
        self.engines_client = Engines(self)

        ## engine selector (engines only with direct links)
        self.global_search = _("All")
        self.global_audio_search = _("All audios")
        self.global_video_search = _("All videos")

        for engine in sorted(self.engine_list):
            try:
                if getattr(self.engines_client, '%s' % engine).adult_content:
                    self.engine_selector.append(engine,True)
            except:
                self.engine_selector.append(engine)

        if ("Youtube" in self.engine_list):
            self.engine_selector.setIndexFromString("Youtube")
        else:
            self.engine_selector.select(0)
        self.engine_selector.append(self.global_search)
        self.engine_selector.append(self.global_audio_search)
        self.engine_selector.append(self.global_video_search)
        self.search_entry.grab_focus()
        self.statbar.hide()
        
        ## hide some icons by default
        self.stop_search_btn.set_sensitive(0)
            
        ## start main loop
        gobject.threads_init()
        #THE ACTUAL THREAD BIT
        self.manager = FooThreadManager(20)
        self.mainloop = gobject.MainLoop(is_running=True)
    
    
    
    def set_window_position(self):
        self.window.set_default_size(int(self.conf['window_state'][0]),int(self.conf['window_state'][1]))
        try:
            x,y = int(self.conf['window_state'][2]),int(self.conf['window_state'][3])
            if x == 0 or y == 0:
                self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
            else:
                self.window.move(x,y)
        except:
            self.window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
    
    def set_extras_options(self, widget):
        if ('convert' in widget.name):
            if widget.get_active():
                accept = warn_dialog(self.warn_dialog)
                if accept == 0:
                    convert = 'True'
                    self.conf['convert'] = True
                else:
                    widget.set_active(0)
            else:
                convert = 'False'
                self.conf['convert'] = False
                
        elif ('systray' in widget.name):
            if widget.get_active():
                systray = 'True'
                self.conf['systray'] = True
                if not self.tray:
                    self.__create_trayicon()
                else:
                    self.tray.set_visible(1)
            else:
                systray = 'False'
                self.conf['systray'] = False
                self.tray.set_visible(0)
        else:
            if widget.get_active():
                accept = warn_dialog(self.warn_dialog)
                if accept == 0:
                    self.down_btn.show()
                    self.down_menu_btn.show()
                    self.conf['downloads'] = True
                else:
                    widget.set_active(0)
            else:
                self.down_btn.hide()
                self.down_menu_btn.hide()
                self.conf['downloads'] = False
        ## save config
        self.conf.write()
    
    def on_gui_opt_toggled(self, widget):
        if widget.get_active():
            self.show_thumbs_opt = "True"
            self.columns[0].set_visible(1)
        else:
            self.show_thumbs_opt = "False"
            self.columns[0].set_visible(0)
        self.conf["show_thumbs"] = self.show_thumbs_opt
        self.conf.write()
    
    def clear_search_entry(self,widget,e,r):
        if e == gtk.ENTRY_ICON_SECONDARY:
            self.search_entry.set_text("")
        elif e == gtk.ENTRY_ICON_PRIMARY:
            self.prepare_search()
        self.search_entry.grab_focus()

    def alternate_color(self, column, cell, model, iter):
        if int((model.get_string_from_iter(iter).split(":")[0])) % 2:
            cell.set_property('background-gdk', self.odd)
            cell.set_property('cell-background-gdk', self.odd)
            cell.set_property('foreground-gdk', gtk.gdk.color_parse(str(self.window.style.fg[gtk.STATE_ACTIVE])))
        else:
            cell.set_property('background-gdk', self.even)
            cell.set_property('cell-background-gdk', self.even)
            cell.set_property('foreground-gdk', gtk.gdk.color_parse(str(self.window.style.fg[gtk.STATE_NORMAL])))

    def save_position(self,widget,e):
        self.x,self.y=self.window.get_position()

    def resize_wrap(self, scroll, allocation, treeview, column, cell):
        otherColumns = (c for c in treeview.get_columns() if c != column)
        newWidth = allocation.width - sum(c.get_width() for c in otherColumns)
        newWidth -= treeview.style_get_property("horizontal-separator") * 4
        if cell.props.wrap_width == newWidth or newWidth <= 0:
                return
        if newWidth < 250:
                newWidth = 225
        cell.props.wrap_width = newWidth
        column.set_property('min-width', newWidth + 10)
        column.set_property('max-width', newWidth + 10)
        store = treeview.get_model()
        iter = store.get_iter_first()
        while iter and store.iter_is_valid(iter):
                store.row_changed(store.get_path(iter), iter)
                iter = store.iter_next(iter)
                treeview.set_size_request(0,-1)

    def change_visualisation(self, widget=None):
        vis = self.vis_selector.getSelected()
        visi = self.vis_selector.getSelectedIndex()
        if vis != "goom" and visi != 0 :
            self.vis = "libvisual_"+vis
        else:
            self.vis = vis
        self.conf["visualisation"] = vis
        self.conf.write()
        return self.vis

    def set_engine(self,engine=None):
        self.quality_box.hide()
        global_search = False
        try:
            engine = engine.name
            self.engine = self.engine_selector.getSelected()
        except:
            self.engine = engine
            self.engine_selector.setIndexFromString(engine)
            global_search = True
        iter = self.engine_selector.getSelectedIndex()
        if iter == 0:
            self.engine = None
            return
        ## clean the gui options box and load the plugin gui
        for w in self.search_opt_box:
            self.search_opt_box.remove(w)
        ## do not set the engine if global search
        if self.engine == self.global_search or self.engine == self.global_video_search or self.engine == self.global_audio_search:
            return
        ## load the plugin
        self.search_engine = getattr(self.engines_client,'%s' % self.engine)
        #if not global_search:
        self.search_engine.load_gui()

    def get_model(self,widget=None,path=None,column=None):
        #if self.search_playlist_menu_active:
        #   return
        self.media_bitrate = ""
        self.media_codec = ""
        current_page = self.results_notebook.get_current_page()
        if int(current_page) == 1:
            self.playlist_mode = True
        else:
            self.playlist_mode = False
        if widget or not self.playlist_mode:
            selected = self.treeview.get_selection()
            self.selected_iter = selected.get_selected()[1]
            self.path = self.model.get_path(self.selected_iter)
            ## else extract needed metacity's infos
            self.media_thumb = self.model.get_value(self.selected_iter, 0)
            name = self.model.get_value(self.selected_iter, 4)
            self.media_name = decode_htmlentities(name)
            self.file_tags = {}
            self.media_markup = self.model.get_value(self.selected_iter, 1)
            self.media_plugname = self.model.get_value(self.selected_iter, 5)
            ## for global search
            if not self.engine_selector.getSelected() == self.media_plugname:
                self.set_engine(self.media_plugname)
            ## return only theme name and description then extract infos from hash
            self.media_link = self.model.get_value(self.selected_iter, 2)
            self.media_img = self.model.get_value(self.selected_iter, 0)
        else:
            selected = self.Playlist.treeview.get_selection()
            self.selected_iter = selected.get_selected()[1]
            self.path = self.Playlist.treestore.get_path(self.selected_iter)
            ## else extract needed metacity's infos
            self.media_thumb = self.Playlist.treestore.get_value(self.selected_iter, 0)
            name = self.Playlist.treestore.get_value(self.selected_iter, 0)
            self.media_name = decode_htmlentities(name)
            self.file_tags = {}
            self.media_markup = self.Playlist.treestore.get_value(self.selected_iter, 0)
            self.media_plugname = self.Playlist.treestore.get_value(self.selected_iter, 0)
            return self.Playlist.on_selected(self.Playlist.treeview)
        ## play in engine
        if not self.search_engine.engine_type == 'files':
            self.player.stop()
        thread.start_new_thread(self.search_engine.play,(self.media_link,))
        #self.search_engine.play(self.media_link)
        
    def prepare_search(self,widget=None):
        self.user_search = self.search_entry.get_text()
        self.latest_engine = self.engine_selector.getSelectedIndex()
        if self.latest_engine == 0:
            self.info_label.set_text(_("Please select a search engine..."))
            return
        if not self.user_search:
            if not self.search_engine.has_browser_mode:
                self.info_label.set_text(_("Please enter an artist/album or song name..."))
                return
        if not self.engine:
            self.info_label.set_text(_("Please select an engine..."))
            return
        self.change_page_request = False
        self.stop_threads()
        self.model.clear()
        self.player.changepage_btn.set_sensitive(0)
        self.player.pageback_btn.set_sensitive(0)
        self.__add_to_history()
        self.engine_list = self.engine_selector.get_list()
        if self.engine_selector.getSelected() == self.global_search:
            for engine in self.engine_list:
                try:
                    self.search_engine = getattr(self.engines_client,'%s' % engine)
                    self.search()
                except:
                    continue
            self.engine_selector.setIndexFromString(self.global_search)
        elif self.engine_selector.getSelected() == self.global_video_search:
            for engine in self.engine_list:
                try:
                    self.search_engine = getattr(self.engines_client,'%s' % engine)
                except:
                    continue
                if not self.search_engine.engine_type == "video":
                    continue
                try:
                    self.search()
                except:
                    continue
            self.engine_selector.setIndexFromString(self.global_video_search)
        elif self.engine_selector.getSelected() == self.global_audio_search:
            for engine in self.engine_list:
                try:
                    self.search_engine = getattr(self.engines_client,'%s' % engine)
                except:
                    continue
                if not self.search_engine.engine_type == "audio" or self.search_engine.name == "Jamendo":
                    continue
                try:
                    self.search()
                except:
                    continue
            self.engine_selector.setIndexFromString(self.global_audio_search)
        else:
            return self.search()

    def change_page(self,widget=None):
        if not self.player.changepage_btn.get_property("visible"):
            return
        try:
            name = widget.name
        except:
            name = ""
        self.model.clear()
        user_search = self.search_entry.get_text()
        engine = self.latest_engine
        if not user_search or user_search != self.user_search or not engine or engine != self.latest_engine:
            ## if engine doesn t have browser mode, start a new search
            if not self.search_engine.has_browser_mode:
                return self.prepare_search()
            else:
                return self.prepare_change_page(engine, user_search, name)
        else:
            return self.prepare_change_page(engine, user_search, name)
            
    def prepare_change_page(self, engine, user_search, name):
            self.engine_selector.select(self.latest_engine)
            if self.engine_selector.getSelected() == self.global_search:
                for engine in self.engine_list:
                    try:
                        self.search_engine = getattr(self.engines_client,'%s' % engine)
                    except:
                        continue
                    if self.search_engine.name == "Jamendo":
                        continue
                    try:
                        self.do_change_page(name)
                    except:
                        continue
            elif self.engine_selector.getSelected() == self.global_audio_search:
                for engine in self.engine_list:
                    try:
                        self.search_engine = getattr(self.engines_client,'%s' % engine)
                    except:
                        continue
                    if self.search_engine.engine_type == "video" or self.search_engine.name == "Jamendo":
                        continue
                    try:
                        self.do_change_page(name)
                    except:
                        continue
            elif self.engine_selector.getSelected() == self.global_video_search:
                for engine in self.engine_list:
                    try:
                        self.search_engine = getattr(self.engines_client,'%s' % engine)
                    except:
                        continue
                    if self.search_engine.engine_type == "audio":
                        continue
                    try:
                        self.do_change_page(name)
                    except:
                        continue
            return self.do_change_page(name)

    def do_change_page(self,name):
        if self.engine_selector.getSelected() == self.global_audio_search:
            if self.search_engine.engine_type == "video":
                return
        if name == "pageback_btn":
            if self.search_engine.current_page != 1:
                try:
                    self.search_engine.num_start = self.search_engine.num_start - self.search_engine.results_by_page
                except:
                    pass
                self.search_engine.current_page = self.search_engine.current_page - 1
        else:
            try:
                self.search_engine.num_start = self.search_engine.num_start + self.search_engine.results_by_page
            except:
                pass
            self.search_engine.current_page = self.search_engine.current_page + 1
        self.search(self.search_engine.current_page)

    def search(self,page=None):
        self.engine_selector.select(self.latest_engine)
        ## send request to the module, can pass type and order too...reset page start to inital state
        if not page:
            page = self.search_engine.main_start_page
            self.search_engine.current_page = self.search_engine.main_start_page
        ## check if first page then desactivate back page
        if page > 1:
            self.player.pageback_btn.set_sensitive(1)
        else:
            self.player.pageback_btn.set_sensitive(0)
            #thread.start_new_thread(self.search_engine.search,(self.user_search,page))
        self.add_thread(self.search_engine,self.user_search,page)

    def add_sound(self, name, media_link, img=None, quality_list=None, plugname=None,markup_src=None, synop=None):
        orig_pixbuf = img
        if not img:
            img = gtk.gdk.pixbuf_new_from_file_at_scale(os.path.join(self.img_path,'video.png'), 64,64, 1)
            orig_pixbuf = gtk.gdk.pixbuf_new_from_file(os.path.join(self.img_path,'video.png'))
        else:
			if img.get_width() != 100:
				img = self.update_image(img,100,100)
        if not name or not media_link or not img:
            return
        ## clean markup...
        try:
            n = decode_htmlentities(name)
            m = glib.markup_escape_text(n)
            markup = '<small><b>%s</b></small>' % m
        except:
            return
            
        if markup_src:
            markup = markup + markup_src
        iter = self.model.append()
        self.model.set(iter,
                        0, img,
                        1, markup,
                        2, media_link,
                        3, quality_list,
                        4, name,
                        5, plugname,
                        6, synop,
                        7, orig_pixbuf,
                        )

    def stop_play(self,widget=None):
        self.player.stop()
    
    def start_play(self,url):
        self.player.start_play(url)
		
    def load_new_page(self):
        self.change_page_request=True
        self.change_page()
            
    def set_fullscreen(self,widget=None):
        self.timer = 0
        if self.fullscreen :
            self.miniPlayer.hide()
            self.btn_box.reparent(self.btn_box_cont)
            self.infobox.reparent(self.infobox_cont)
            gobject.idle_add(self.search_box.show)
            gobject.idle_add(self.results_notebook.show)
            gobject.idle_add(self.player.control_box.show)
            gobject.idle_add(self.options_bar.show)
            self.window.window.set_cursor(None)
            gobject.idle_add(self.window.window.unfullscreen)
            gobject.idle_add(self.window.set_position,gtk.WIN_POS_CENTER)
            if sys.platform == 'win32':
                self.window.set_decorated(True)
            self.fullscreen = False
            gobject.idle_add(self.player.fullscreen_btn_pixb.set_from_pixbuf,self.player.fullscreen_pix)
            gobject.idle_add(self.player.fullscreen_btn_pixb.set_tooltip_text,_('enter fullscreen'))
        else:
            gobject.idle_add(self.search_box.hide)
            gobject.idle_add(self.results_notebook.hide)
            gobject.idle_add(self.options_bar.hide)
            self.btn_box.reparent(self.mini_btn_box_cont)
            self.infobox.reparent(self.mini_infobox_cont)
            pixmap = gtk.gdk.Pixmap(None, 1, 1, 1)
            color = gtk.gdk.Color()
            cursor = gtk.gdk.Cursor(pixmap, pixmap, color, color, 0, 0)
            self.window.window.set_cursor(cursor)
            gobject.idle_add(self.player.control_box.hide)
            gobject.idle_add(self.window.window.fullscreen)
            if sys.platform == 'win32':
                self.window.set_decorated(False)
            self.fullscreen = True
            self.mini_player = False
            gobject.idle_add(self.player.fullscreen_btn_pixb.set_from_pixbuf,self.player.leave_fullscreen_pix)
            gobject.idle_add(self.player.fullscreen_btn_pixb.set_tooltip_text,_('leave fullscreen'))
        
		
    def update_image(self,img, w, h):
		# Get the size of the source pixmap
		src_width, src_height = img.get_width(), img.get_height()
		# Scale preserving ratio
		scale = min(float(w)/src_width, float(h)/src_height)
		new_width = int(scale*src_width)
		new_height = int(scale*src_height)
		pixbuf = img.scale_simple(new_width, new_height, gtk.gdk.INTERP_BILINEAR)
		return pixbuf
    
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
                self.window.window.set_cursor(cursor)
            except:
                return
        else:
            if not visible:
                gobject.idle_add(self.miniPlayer.show)
            self.mini_player = True
            try:
                self.window.window.set_cursor(None)
            except:
                return

    def onKeyPress(self, widget, event):
        if self.search_entry.is_focus():
            return
        key = gtk.gdk.keyval_name(event.keyval)
        if key == 'f':
            return self.set_fullscreen()
        elif key == 'space':
            return self.pause_resume()
        elif key == 's':
            return self.stop_play()
        elif key == 'BackSpace':
            self.search_entry.set_text("")
            return self.search_entry.grab_focus()
        elif key == 'd':
            if self.notebook.get_current_page() == 0:
                gobject.idle_add(self.notebook.set_current_page,1)
                self.notebook.queue_draw()
            else:
                gobject.idle_add(self.notebook.set_current_page,0)

        # If user press Esc button in fullscreen mode
        if event.keyval == gtk.keysyms.Escape and self.fullscreen:
            return self.set_fullscreen()

    def on_treeview_clicked(self,widget):
        '''prepare media infos from engine if available'''
        try:
            self.search_engine.get_media_infos()
        except:
            return
    
    def download_file(self,widget=None, link=None, name=None, codec = None, data=None, engine_type=None, engine_name=None):
		if not link:
			link = self.active_link
		if not name:
			name = self.media_name
		if not codec:
			codec = self.media_codec
		download = downloader.FileDownloader(self, link, name, codec, data, engine_name, engine_type)
		download.start()
                
    def download_debrid(self, link):
        check = self.url_checker.check([link])
        if check != [link]:
            if check[0][1] == 0:
                self.info_label.set_text(_("This link has been removed or is expired...!"))
                return
            link   = check[0][0]
        thread = threading.Thread(target=self.url_debrid.debrid ,args=(link,))
        thread.start()

    def on_about_btn_pressed(self, widget):
        dlg = self.gladeGui.get_widget("aboutdialog")
        dlg.set_version(VERSION)
        response = dlg.run()
        if response == gtk.RESPONSE_DELETE_EVENT or response == gtk.RESPONSE_CANCEL:
            dlg.hide()

    def on_settings_btn_pressed(self, widget):
        self.dlg.set_position(gtk.WIN_POS_CENTER_ALWAYS)
        response = self.dlg.run()
        if response == False or response == True or response == gtk.RESPONSE_DELETE_EVENT:
            self.dlg.hide()

    def save_window_state(self):
        try:
            r,s,w,h = self.window.get_allocation()
            self.window.grab_focus()
            self.conf['window_state'] = (w,h,self.x,self.y)
            self.conf.write()
        except:
            return

    def exit(self,widget=None):
        """Stop method, sets the event to terminate the thread's main loop"""
        self.player.stop()
        ## save window state
        self.save_window_state()
        self.manager.stop_all_threads(block=True)
        for th in self.download_pool:
            if not th._stopevent.isSet():
                th.stop()
        self.mainloop.quit()

    def stop_threads(self, *args):
        #THE ACTUAL THREAD BIT
        self.manager.stop_all_threads()

    def add_thread(self, engine, query, page):
        #make a thread and start it
        thread_name = "Search thread %s,%s,%s" % (engine.name, query, page)
        args = (thread_name,self.info_label,engine,query,page,self.throbber,self.stop_search_btn)
        #THE ACTUAL THREAD BIT
        self.manager.make_thread(
                        self.thread_finished,
                        self.thread_progress,
                        *args)

    def thread_finished(self, thread):
        ## check automatic page change
        self.stop_search_btn.set_sensitive(0)
        if len(self.model) > 0:
            self.player.changepage_btn.set_sensitive(1)
            if self.change_page_request:
                ## wait for 10 seconds or exit
                try:
                    self.selected_iter = self.model.get_iter_first()
                    path = self.model.get_path(self.selected_iter)
                    self.treeview.set_cursor(path)
                    self.get_model()
                    self.change_page_request=False
                except:
                    self.change_page_request=False
                    return
        else:
            self.player.changepage_btn.set_sensitive(0)
        self.info_label.set_text("")


    def thread_progress(self, thread):
        pass
        
    
    def select_first_media(self):
        ## wait for 10 seconds or exit
        print len(self.model)
        try:
            self.selected_iter = self.model.get_iter_first()
            path = self.model.get_path(self.selected_iter)
            self.treeview.set_cursor(path)
            self.get_model()
        except:
            return
    
    def _show_search_playlist_menu(self,widget,event):
        if event.button == 3:
            self.search_playlist_menu_active = True
            self.search_playlist_menu.show_all()
            self.search_playlist_menu.popup(None, None, None, event.button, event.time)
        
    def _copy_link(self,widget=None,vid=None):
        self.search_playlist_menu_active = False
        link = self.media_link
        if self.search_engine.name == 'Youtube' and not vid:
            link = 'http://www.youtube.com/watch?v=%s' % self.media_link
        clipboard = gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
        clipboard.set_text(link)
        print '%s copied to clipboard' % link
        
    def _add_to_playlist(self,widget):
        self.search_playlist_menu_active = False
        link = self.media_link
        if self.search_engine.name == 'Youtube':
            link = 'http://www.youtube.com/watch?v=%s' % self.media_link
        self.Playlist.add(self.media_name, link, self.active_link, self.media_plugname)
    
    def __create_trayicon(self):
        if gtk.check_version(2, 10, 0) is not None:
            self.log.debug("Disabled Tray Icon. It needs PyGTK >= 2.10.0")
            return
        self.tray = gtk.StatusIcon()
        self.tray.set_from_file(os.path.join(self.img_path,'gmediafinder.png'))
        self.tray.set_tooltip('Gmediafinder')
        self.tray.connect("activate", self.__on_trayicon_click)
        self.tray.connect("popup-menu", self.__show_tray_menu)
  
  
    def __on_trayicon_click(self, widget):
        if(self.showed is True):
            self.showed = False
            self.window.hide()
            self.save_window_state()
        else:
            self.showed = True
            self.window.show()
            self.set_window_position()
  
    def __show_tray_menu(self, widget, button, activate_time):
        menu = gtk.Menu()
        exit_item = gtk.ImageMenuItem(gtk.STOCK_QUIT)
        menu.append(exit_item)
        exit_item.connect('activate', self.exit)
  
        menu.show_all()
        menu.popup(None, None, None, button, activate_time)
        
    def __add_to_history(self):
        search = self.search_entry.get_text()
        c = open(history_file,'r')
        t = c.readlines()
        c.close()
        inlist = False
        for i in t:
            if re.match(search, i.replace('\n','')):
                inlist = True
                break
        if inlist:
            return
        if len(t) >= int(max_history):
            u = open(history_file,'w')
            del t[0]
            u.writelines(t)
            u.close()
        f = open(history_file,'a')
        f.write("%s\n" % search)
        f.close()
    
    def __search_history(self, widget):
        search = self.search_entry.get_text()
        self.history_model.clear()
        for l in open(history_file,'r'):
            try:
                s = re.search('.*%s.*' % search,l).group()
                self.history_model.append([s])
            except:
                pass
    
    def clear_history(self, widget):
        search = self.search_entry.get_text()
        self.history_model.clear()
        f = open(history_file,'w')
        f.write(' ')
        f.close()

  
    def __close(self, widget, event=None):
        if self.minimize == 'on':
            self.showed = False
            self.hide()
            self.save_window_state()
        else:
            self.quit(widget)
        return True


class _IdleObject(gobject.GObject):
    """
    Override gobject.GObject to always emit signals in the main thread
    by emmitting on an idle handler
    """
    def __init__(self):
        gobject.GObject.__init__(self)

    def emit(self, *args):
        gobject.idle_add(gobject.GObject.emit,self,*args)

class _FooThread(threading.Thread, _IdleObject):
    """
    Cancellable thread which uses gobject signals to return information
    to the GUI.
    """
    __gsignals__ =  {
            "completed": (
                gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, []),
            "progress": (
                gobject.SIGNAL_RUN_LAST, gobject.TYPE_NONE, [])        #percent complete
            }

    def __init__(self, *args):
        threading.Thread.__init__(self)
        _IdleObject.__init__(self)
        self.cancelled = False
        self.engine = args[2]
        self.query = args[3]
        self.page = args[4]
        self.name = args[0]
        self.info = args[1]
        self.throbber = args[5]
        self.stop_btn = args[6]
        self.setName("%s" % self.name)

    def cancel(self):
        """
        Threads in python are not cancellable, so we implement our own
        cancellation logic
        """
        self.cancelled = True

    def run(self):
        #print "Running %s" % str(self)
        gobject.idle_add(self.info.set_text,'')
        self.engine.thread_stop = False
        self.cancelled = False
        url = self.engine.get_search_url(self.query, self.engine.current_page)
        query = urlFetch(self.engine, url, self.query, self.engine.current_page)
        query.start()
        while 1:
            if self.engine.thread_stop == False and not self.cancelled:
                time.sleep(1)
                gobject.idle_add(self.throbber.show)
                gobject.idle_add(self.stop_btn.set_sensitive,1)
                values = {'engine': self.engine.name, 'query': self.query, 'page' : self.page}
                gobject.idle_add(self.info.set_text,_("Searching for %(query)s with %(engine)s (page: %(page)s)") % values)
                self.emit("progress")
            else:
                query.abort()
                self.engine.thread_stop = True
                break
        self.emit("completed")

class FooThreadManager:
    """
    Manages many FooThreads. This involves starting and stopping
    said threads, and respecting a maximum num of concurrent threads limit
    """
    def __init__(self, maxConcurrentThreads):
        self.maxConcurrentThreads = maxConcurrentThreads
        #stores all threads, running or stopped
        self.fooThreads = {}
        #the pending thread args are used as an index for the stopped threads
        self.pendingFooThreadArgs = []
        self.running = 0

    def _register_thread_completed(self, thread, *args):
        """
        Decrements the count of concurrent threads and starts any
        pending threads if there is space
        """
        throbber = args[5]
        del(self.fooThreads[args])
        self.running = len(self.fooThreads) - len(self.pendingFooThreadArgs)

        #print "%s completed. %s running, %s pending" % (thread, self.running, len(self.pendingFooThreadArgs))

        if self.running < self.maxConcurrentThreads:
            try:
                args = self.pendingFooThreadArgs.pop()
                #print "Starting pending %s" % self.fooThreads[args]
                self.fooThreads[args].start()
            except IndexError: pass
        if self.running == 0:
            gobject.idle_add(throbber.hide)

    def make_thread(self, completedCb, progressCb, *args):
        """
        Makes a thread with args. The thread will be started when there is
        a free slot
        """
        self.info = args[1]
        self.engine = args[2]
        self.query = args[3]
        self.page = args[4]
        self.throbber = args[5]
        self.stop_btn = args[6]
        self.running = len(self.fooThreads) - len(self.pendingFooThreadArgs)
        if args not in self.fooThreads:
            thread = _FooThread(*args)
            #signals run in the order connected. Connect the user completed
            #callback first incase they wish to do something
            #before we delete the thread
            thread.connect("completed", completedCb)
            thread.connect("completed", self._register_thread_completed, *args)
            thread.connect("progress", progressCb)
            #This is why we use args, not kwargs, because args are hashable
            self.fooThreads[args] = thread

            if self.running < self.maxConcurrentThreads:
                #print "Starting %s" % thread
                gobject.idle_add(self.throbber.show)
                gobject.idle_add(self.stop_btn.set_sensitive,1)
                self.fooThreads[args].start()
                values = {'engine': self.engine.name, 'query': self.query, 'page' : self.page}
                gobject.idle_add(self.info.set_text,_("Searching for %(query)s with %(engine)s (page: %(page)s)") % values)
            else:
                #print "Queing %s" % thread
                self.pendingFooThreadArgs.append(args)

    def stop_all_threads(self, block=False):
        """
        Stops all threads. If block is True then actually wait for the thread
        to finish (may block the UI)
        """
        for thread in self.fooThreads.values():
            thread.cancel()
            if block:
                if thread.isAlive():
                    thread.join()
                    


if __name__ == "__main__":
    app = GsongFinder()
    try:
        app.mainloop.run()
    except KeyboardInterrupt, errmsg:
        app.exit()
