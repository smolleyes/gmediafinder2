#!/usr/bin/env python
import sys
import gtk
import webkit
import warnings
import urllib
import re
from time import sleep
import gobject
from optparse import OptionParser
 
warnings.filterwarnings('ignore')
 
class WebView(webkit.WebView):
	def get_html(self):
		self.execute_script('oldtitle=document.title;document.title=document.documentElement.innerHTML;')
		html = self.get_main_frame().get_title()
		self.execute_script('document.title=oldtitle;')
		return html
 
class Browser():
    def __init__(self, mainGui):
	self.mainGui = mainGui
	self.url_bar = self.mainGui.gladeGui.get_widget("browser_entry")
	self.url_bar.connect("activate", self.on_active)
	self.back_button = self.mainGui.gladeGui.get_widget("back_btn")
	self.forward_button = self.mainGui.gladeGui.get_widget("next_btn")
	self.view = WebView()
	## get requested pages
	self.view.connect('resource-request-starting', self.resource_cb)
	## update adress bar
	self.view.connect("load_committed", self.update_buttons)
	self.mainGui.browser_box.add(self.view)
	
	## opt
	self.homepage = 'http://www.google.com'
	
	## SIGNALS
	dic = {
	"on_back_btn_clicked" : self.go_back,
	"on_next_btn_clicked" : self.go_forward,
	"on_refresh_btn_clicked" : self.refresh,
	"on_search_btn_clicked" : self.on_active,
	"on_home_btn_clicked" : self.go_home,
	}
	self.mainGui.gladeGui.signal_autoconnect(dic)
	
    def load_uri(self,uri):
	gobject.idle_add(self.view.load_uri,uri)  
    
    def resource_cb(self, view, frame, resource, request, response):
	req = request.get_uri()
	#head = frame.get_network_response().get_property('message').get_property('response-headers')
	#response = resource.get_property('message').get_property('response-headers')
    	if 'megavideo.com/files/' in req:
	    print "MEGAVIDEO: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming Megavideo...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.go_back)
	elif 'videobb.com/s?v=' in req:
	    print "Videobb: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming Videobb...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.go_back)
	elif 'mixturecloud.com/streaming.php?key_stream=' in req and not 'player.mixturecloud' in req:
	    print "Videobb: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming mixture video...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.go_back)
	elif 'http://av.vimeo.com' in req and '?token=' in req:
	    print "Vimeo: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming Vimeo...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.go_back)
	elif 'dailymotion.com/video/' in req and 'proxy' in req:
	    print "Dailymotion: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming dailymotion...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.go_back)
	elif 'youtube.com/videoplayback?sparams' in req:
	    print "Youtube: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming Youtube...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.go_back)
	elif 'http://trailers-ak.gametrailers.com' in req:
	    print "Gametrailer: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming Gametrailer...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.go_back)
	    
    def on_active(self, widget, data=None):
        '''When the user enters an address in the bar, we check to make
           sure they added the http://, if not we add it for them.  Once
           the url is correct, we just ask webkit to open that site.'''
        url = self.url_bar.get_text()
        try:
            url.index("://")
        except:
            url = "http://"+url
        self.url_bar.set_text(url)
        self.view.open(url)

    def go_home(self,widget):
	self.view.open(self.homepage)
    
    def go_back(self, widget, data=None):
        '''Webkit will remember the links and this will allow us to go
           backwards.'''
        self.view.go_back()

    def go_forward(self, widget, data=None):
        '''Webkit will remember the links and this will allow us to go
           forwards.'''
        self.view.go_forward()

    def refresh(self, widget, data=None):
        '''Simple makes webkit reload the current back.'''
        self.view.reload()

    def update_buttons(self, widget, data=None):
        '''Gets the current url entry and puts that into the url bar.
           It then checks to see if we can go back, if we can it makes the
           back button clickable.  Then it does the same for the foward
           button.'''
        self.url_bar.set_text( widget.get_main_frame().get_uri() )
        self.back_button.set_sensitive(self.view.can_go_back())
        self.forward_button.set_sensitive(self.view.can_go_forward())

