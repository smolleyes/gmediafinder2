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

try:
    import lib.config as config
    import lib.debrid as debrider
except:
    from GmediaFinder.lib import config
    from GmediaFinder.lib import debrid as debrider
 
class WebView(webkit.WebView):
    def __init__(self):
        webkit.WebView.__init__(self)
	settings = self.get_settings()
	settings.set_property("enable-developer-extras", True)
	
	# scale other content besides from text as well
	self.set_full_content_zoom(True)
	# make sure the items will be added in the en
	# hence the reason for the connect_after
	self.connect_after("populate-popup", self.populate_popup)
    
    def populate_popup(self, view, menu):
	# zoom buttons
	zoom_in = gtk.ImageMenuItem(gtk.STOCK_ZOOM_IN)
	zoom_in.connect('activate', zoom_in_cb, view)
	menu.append(zoom_in)
    
	zoom_out = gtk.ImageMenuItem(gtk.STOCK_ZOOM_OUT)
	zoom_out.connect('activate', zoom_out_cb, view)
	menu.append(zoom_out)
    
	zoom_hundred = gtk.ImageMenuItem(gtk.STOCK_ZOOM_100)
	zoom_hundred.connect('activate', zoom_hundred_cb, view)
	menu.append(zoom_hundred)
    
	printitem = gtk.ImageMenuItem(gtk.STOCK_PRINT)
	menu.append(printitem)
	printitem.connect('activate', print_cb, view)
    
	page_properties = gtk.ImageMenuItem(gtk.STOCK_PROPERTIES)
	menu.append(page_properties)
	page_properties.connect('activate', page_properties_cb, view)
    
	menu.append(gtk.SeparatorMenuItem())
    
	aboutitem = gtk.ImageMenuItem(gtk.STOCK_ABOUT)
	menu.append(aboutitem)
	aboutitem.connect('activate', about_pywebkitgtk_cb, view)
    
	menu.show_all()
	return False
	
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
	## debrider
	self.debrider = debrider.Debrid(self.mainGui)
	
	settings = webkit.WebSettings()
	settings.set_property('enable-scripts', True)
	settings.set_property('javascript-can-open-windows-automatically', True)
	self.view.connect('create-web-view',self.on_new_window_cb)
	self.view.connect("hovering-over-link", self._hovering_over_link_cb)
	self.view.connect("load-finished", self.load_finished)
	self._hovered_uri = None
	self.isLoading=False
	self.page_requests=[]
	
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
	
    def on_new_window_cb(self, web_view, frame, data=None):
	scrolled_window = gtk.ScrolledWindow()
        scrolled_window.props.hscrollbar_policy = gtk.POLICY_AUTOMATIC
        scrolled_window.props.vscrollbar_policy = gtk.POLICY_AUTOMATIC
        view = WebView()
        scrolled_window.add(view)
	scrolled_window.show_all()
  
        vbox = gtk.VBox(spacing=1)
        vbox.pack_start(scrolled_window, True, True)
  
        window = gtk.Window()
        window.add(vbox)
	view.connect("web-view-ready", self.new_web_view_ready)
        return view
  
    def new_web_view_ready (self, web_view):
        self.new_window_requested(web_view)
  
    def new_window_requested(self, view):
        features = view.get_window_features()
        window = view.get_toplevel()
        scrolled_window = view.get_parent()
        window.set_default_size(features.props.width, features.props.height)
	window.set_position(gtk.WIN_POS_CENTER_ALWAYS)
	gobject.idle_add(window.show_all)
        return True
	
    
    def _hovering_over_link_cb (self, view, title, uri):
        self._hovered_uri = uri
	
    def load_uri(self,uri,fromEngine=False):
	if fromEngine is True:
	    self.isLoading=True
	else:
	    self.isLoading=False
	gobject.idle_add(self.view.load_uri,uri)
	
    def load_finished(self,v,r):
	print "load finished...."
	print self.page_requests
	self.analyse_req()
	self.stop_player()
    
    def resource_cb(self, view, frame, resource, request, response):
	
	req = request.get_uri()
	self.page_requests.append(req)
	#head = frame.get_network_response().get_property('message').get_property('response-headers')
	#response = resource.get_property('message').get_property('response-headers')
	#print req
    
    def analyse_req(self):
	for req in self.page_requests:
	    if 'megavideo.com/files/' in req:
		print "MEGAVIDEO: Link detected"
		self.mainGui.media_name = 'Streaming Megavideo...'
		self.mainGui.start_play(req)
		gobject.idle_add(self.view.go_back)
		break
	    elif 'videobb.com/s?v=' in req:
		print "Videobb: Link detected"
		self.mainGui.media_name = 'Streaming Videobb...'
		self.mainGui.start_play(req)
		gobject.idle_add(self.view.go_back)
		break
	    elif 'http://www.mixturecloud.com/media/' in req and 'player.mixturecloud' in req:
		print "Mixture: Link detected"
		self.mainGui.media_name = 'Streaming mixture video...'
		vid=re.search('mixturecloud.com/media/(.*)&win',req).group(1)
		self.debrider.debridMixture(vid)
		break
		##gobject.idle_add(self.view.go_back)
	    elif 'http://av.vimeo.com' in req and '?token=' in req:
		print "Vimeo: Link detected"
		self.mainGui.media_name = 'Streaming Vimeo...'
		self.mainGui.start_play(req)
		gobject.idle_add(self.view.go_back)
		break
	    elif 'dailymotion.com/video/' in req and 'proxy' in req:
		print "Dailymotion: Link detected"
		self.mainGui.media_name = 'Streaming dailymotion...'
		self.mainGui.start_play(req)
		gobject.idle_add(self.view.go_back)
		break
	    elif 'putlocker.com/download/' in req:
		    self.mainGui.media_name = 'Streaming putlocker...'
		    self.mainGui.start_play(req)
		    gobject.idle_add(self.view.go_back)
		    break
	    elif 'lscache' in req and "youtube.com" in req:
		print "isLOADING : %s" % self.isLoading
		if self.isLoading:
		    self.stop_player()
		    self.isLoading=False
		    break
		    return
		## compare video ids
		reqid = None
		current_id = None
		url = self.url_bar.get_text()
		try:
		    reqid = re.search('\?v=(.*?)&',url).group(1)
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
		print "%s %s" % (current_id, reqid)
		if reqid != current_id:
		    self.mainGui.search_engine.on_paste(url=url)
		    self.mainGui.search_engine.updateBrowser=False
		break
		self.stop_player()
		    
		
	    elif 'http://trailers-ak.gametrailers.com' in req:
		print "Gametrailer: Link detected"
		self.mainGui.media_name = 'Streaming Gametrailer...'
		self.mainGui.start_play(req)
		gobject.idle_add(self.view.go_back)
		break
	self.page_requests=[]
	    
    def stop_player(self):
	print "Youtube: stop player"
	## hide/stop the flashplayer
	try:
	    script = "player = document.getElementById('movie_player');"
	    script += "player.mute();"
	    script += "player.stopVideo();"
	    gobject.idle_add(self.view.execute_script,script)
	except:
	    print "no player loaded"
    
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
	
    def load_default_page(self):
	icon = config.img_path+"/gmediafinder.png"
	html = '''
	<!DOCTYPE html>
	    <head>
	    <title>Gmediafinder</title>
	    </head>
	    <body style="background-color:black;color: white; font-size:12px;">
	    <div style="width:400px;position: absolute;left:%s ;margin-left:-150px;top:%s;">
		<h1><img style="vertical-align:middle;" src="file://%s" /> Gmediafinder</h1>
	    </div>
	    </body>
	</html>''' % ('50%','50%',icon)
	gobject.idle_add(self.view.load_html_string,html, "file:///#")
 
def zoom_in_cb(menu_item, web_view):
    """Zoom into the page"""
    web_view.zoom_in()
  
def zoom_out_cb(menu_item, web_view):
    """Zoom out of the page"""
    web_view.zoom_out()
  
def zoom_hundred_cb(menu_item, web_view):
    """Zoom 100%"""
    if not (web_view.get_zoom_level() == 1.0):
        web_view.set_zoom_level(1.0)

def print_cb(menu_item, web_view):
    mainframe = web_view.get_main_frame()
    mainframe.print_full(gtk.PrintOperation(), gtk.PRINT_OPERATION_ACTION_PRINT_DIALOG);
    
def page_properties_cb(menu_item, web_view):
    mainframe = web_view.get_main_frame()
    datasource = mainframe.get_data_source()
    main_resource = datasource.get_main_resource()
    window = gtk.Window()
    window.set_default_size(100, 60)
    vbox = gtk.VBox()
    hbox = gtk.HBox()
    hbox.pack_start(gtk.Label("MIME Type :"), False, False)
    hbox.pack_end(gtk.Label(main_resource.get_mime_type()), False, False)
    vbox.pack_start(hbox, False, False)
    hbox2 = gtk.HBox()
    hbox2.pack_start(gtk.Label("URI : "), False, False)
    hbox2.pack_end(gtk.Label(main_resource.get_uri()), False, False)
    vbox.pack_start(hbox2, False, False)
    hbox3 = gtk.HBox()
    hbox3.pack_start(gtk.Label("Encoding : "), False, False)
    hbox3.pack_end(gtk.Label(main_resource.get_encoding()), False, False)
    vbox.pack_start(hbox3, False, False)
    window.add(vbox)
    window.show_all()
    window.present()
  
  
def view_source_mode_requested_cb(widget, is_active, content_pane):
    currentTab = content_pane.get_nth_page(content_pane.get_current_page())
    childView = currentTab.get_child()
    childView.set_view_source_mode(is_active)
    childView.reload()
    
# context menu item callbacks
def about_pywebkitgtk_cb(menu_item, web_view):
    web_view.open("http://live.gnome.org/PyWebKitGtk")
