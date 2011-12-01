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
        self.view = WebView()
        self.view.connect('resource-request-starting', self.resource_cb)
	self.mainGui.browser_box.add(self.view)    
	
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
	    gobject.idle_add(self.view.stop_loading)
	elif 'videobb.com/s?v=' in req:
	    print "Videobb: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming Videobb...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.stop_loading)
	    return self.mainGui.start_play(req)
	elif 'mixturecloud.com/streaming.php?key_stream=' in req and not 'player.mixturecloud' in req:
	    print "Videobb: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming mixture video...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.stop_loading)
	elif 'http://av.vimeo.com' in req and '?token=' in req:
	    print "Vimeo: Link %s detected" % req
	    self.mainGui.media_name = 'Streaming Vimeo...'
	    self.mainGui.start_play(req)
	    gobject.idle_add(self.view.stop_loading)
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

