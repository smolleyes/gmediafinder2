#!/usr/bin/env python
#-*- coding: UTF-8 -*-

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
	
	settings = webkit.WebSettings()
	settings.set_property('enable-scripts', True)
	settings.set_property('javascript-can-open-windows-automatically', False)
	
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
	    
	    ## hide/stop the flashplayer
	    new = "<p>TA RACE FLASH</p>"
	    script = "div_content = document.getElementById('movie_player');"
	    script += "div_content.style.display='None';"
	    script += "div_content.innerHTML='%s';" % new
	    gobject.idle_add(self.view.execute_script,script)
	    
	    ## compare video ids
	    reqid = None
	    current_id = None
	    url = self.url_bar.get_text()
	    print url
	    try:
		reqid = re.search('\?v=(.*)&',url).group(1)
	    except:
		try:
		    reqid = re.search('\?v=(.*)',url).group(1)
		except:
		    reqid = None
	    try:
		current_id = self.mainGui.media_link
	    except:
		curent_id = None
	    ## if not match read new video
	    if reqid != current_id:
		self.mainGui.search_engine.on_paste(url=url)
	    
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
	
    def load_code(self,like_link=None,html=None):
	if not html:
	    html = '''
	    <!DOCTYPE html>
		<head>
		<title>youtube page</title>
		</head>
		<body>
		<div id="fb-root"></div>
		    <script>
			window.fbAsyncInit = function() {
			  FB.init({
			    appId      : '241809072559194',
			    status     : true, 
			    cookie     : true,
			    xfbml      : true,
			    oauth      : true,
			  });
			};
			(function(d){
			   var js, id = 'facebook-jssdk'; if (d.getElementById(id)) {return;}
			   js = d.createElement('script'); js.id = id; js.async = true;
			   js.src = "http://connect.facebook.net/fr_FR/all.js";
			   d.getElementsByTagName('head')[0].appendChild(js);
			 }(document));
		      </script>
			
		    <div class="fb-login-button" data-show-faces="true" data-width="200" data-max-rows="1"></div>
		    <div class="fb-like" data-send="true" data-width="450" data-href="http://www.youtube.com/watch?v=%s" data-show-faces="true" data-colorscheme="dark"></div>
		</body>
	    </html>''' % like_link
	gobject.idle_add(self.view.load_html_string,html, "file:///")  
