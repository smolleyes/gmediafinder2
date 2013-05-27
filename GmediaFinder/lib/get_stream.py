#!/usr/bin/env python
#-*- coding: UTF-8 -*-

import sys
import gtk
import webkit
import warnings
import urllib, urllib2, json
import re, thread
from time import sleep
import gobject
from optparse import OptionParser
from inspector import Inspector
from lxml import html as Html
 
#warnings.filterwarnings('ignore')

try:
    import lib.config as config
    import lib.debrid as debrider
    from lib.functions import * 
except:
    from GmediaFinder.lib import config
    from GmediaFinder.lib import debrid as debrider
    from GmediaFinder.lib.functions import * 
 
class WebView(webkit.WebView):
    def __init__(self):
	gobject.threads_init()
	webkit.WebView.__init__(self)
	settings = self.get_settings()
	
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
	gobject.threads_init()
	self.mainGui = mainGui
	self.url_bar = self.mainGui.gladeGui.get_widget("browser_entry")
	self.url_bar.connect("activate", self.on_active)
	self.back_button = self.mainGui.gladeGui.get_widget("back_btn")
	self.forward_button = self.mainGui.gladeGui.get_widget("next_btn")
	self.view = WebView()
	self.stream_name=''
	## get requested pages
	self.view.connect('resource-request-starting', self.resource_cb)
	## update adress bar
	self.view.connect("load_committed", self.update_buttons)
	self.mainGui.browser_box.add(self.view)
	## debrider
	self.debrider = debrider.Debrid(self.mainGui)
	
	self.settings = self.view.get_settings()
	self.settings.set_property('enable-plugins', False)
	self.settings.set_property('enable-scripts', True)
	self.settings.set_property('javascript-can-open-windows-automatically', True)
	self.settings.set_property("enable-developer-extras", True)
	#self.settings.set_property('user-agent', 'Mozilla/5.0 (Linux; webOS/2.2.4; U; en-US) AppleWebKit/534.6 (KHTML like Gecko) webOSBrowser/221.56 Safari/534.6 Pre/3.0; iPhone; Safari/7534.48.3; AppleWebKit/534.46; Version/5.1; Mobile/9A334; CPUiPhoneOS5_0likeMacOSX')
	self.view.connect('create-web-view',self.on_new_window_cb)
	#self.view.connect("navigation-policy-decision-requested",self._nav_request_policy_decision_cb)
	#self.view.connect("hovering-over-link", self._hovering_over_link_cb)
	self.view.connect("load-finished", self.load_finished)
	#self.view.connect("navigation-requested", self.on_click_link)
	self.console_response = self.view.connect('console-message', self.on_console_message)
	#self.view.connect('resource-response-received', self.on_response_received)
	self._hovered_uri = None
	self.isLoading=False
	self.page_requests=[]
	self.source_code = None
	self.analyzed=False
	self.ytid=''
	self.l_uri=''
	self.origin=''
	self.view.set_settings(self.settings)
	## opt
	self.homepage = 'http://www.google.com'
	inspector = Inspector(self.view.get_web_inspector())
	## SIGNALS
	dic = {
	"on_back_btn_clicked" : self.go_back,
	"on_next_btn_clicked" : self.go_forward,
	"on_refresh_btn_clicked" : self.refresh,
	"on_search_btn_clicked" : self.on_active,
	"on_home_btn_clicked" : self.go_home,
	}
	self.mainGui.gladeGui.signal_autoconnect(dic)
    
    def on_console_message(self, *args):
        """ callback on 'console-message' webkit.WebView signal """
        #print ('Myconsole:' + str(args))
        self.view.stop_emission('console-message')
	#return True
	
    def on_response_received(self,view,frame,resource,response):
	pass
	#print response.get_uri()
	
    
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
	
    def load_uri(self,uri,name=None,origin=None):
	self.origin=None
	try:
	    if self.mainGui.search_engine.name=='Youtube' or self.mainGui.search_engine.name=='DailyMotion' or self.mainGui.search_engine.name=='Vimeo':
		self.settings.set_property('user-agent','Mozilla/5.0 (X11; Linux i686) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/28.0.1500.5 Safari/537.36')
	    else:
		self.settings.set_property('user-agent', 'Mozilla/5.0 (Linux; webOS/2.2.4; U; en-US) AppleWebKit/534.6 (KHTML like Gecko) webOSBrowser/221.56 Safari/534.6 Pre/3.0; iPhone; Safari/7534.48.3; AppleWebKit/534.46; Version/5.1; Mobile/9A334; CPUiPhoneOS5_0likeMacOSX')
	    if self.mainGui.search_engine.name=='Streamiz' or self.mainGui.search_engine.name=='DpStream':
		self.settings.set_property('enable-plugins',True)
	    else:
		self.settings.set_property('enable-plugins',False)
	    self.view.set_settings(self.browser.settings)
	except:
	    pass
	if name:
	    self.stream_name=name
	if origin:
	    self.origin=origin
	self.analyzed=False
	print "loading uri: %s" % uri
	gobject.idle_add(self.view.load_uri,uri)
    
    def load_finished(self,v,r):
	print "load finished"
	self.analyse_req()
	
    def on_click_link(view, frame, networkRequest,data=None):
	# get uri from request object
	uri=networkRequest.get_uri()
	print "request to go to %s" % uri
	# load the page somehow.....
	page=urllib.urlopen(networkRequest.get_uri())
	# load into associated view, passing in uri
	print page
	# return 1 to stop any other handlers running
	# eg. the default uri handler...
    
    def _nav_request_policy_decision_cb(self,view,frame,net_req,nav_act,pol_dec):
        pass
    
    def resource_cb(self, view, frame, resource, request, response):
	req = request.get_uri()
	if 'http://www.debrideurstreaming.com/stats.php' in req:
		html=self.view.get_html()
		if 'purevid.com/get' in html:
		    link=re.search('Actualiser</div><a href="(.*?)start=',html).group(1).replace('&amp;','&')+'&start='
		    if self.stream_name != '':
			self.mainGui.media_name=self.stream_name
		    else:
			self.mainGui.media_name='streaming Dpstream'
		    gobject.idle_add(self.mainGui.info_label.set_text,'')
		    print link
		    self.mainGui.start_play(link)
		    return
		elif 'uploadhero.co/v.php?s' in html:
		    link=re.search('Actualiser</div><a href="(.*?)start=',html).group(1).replace('&amp;','&')+'&start='
		    if self.stream_name != '':
			self.mainGui.media_name=self.stream_name
		    else:
			self.mainGui.media_name='streaming streamiz'
		    gobject.idle_add(self.mainGui.info_label.set_text,'')
		    print link
		    self.mainGui.start_play(link)
		    return
	elif 'http://www.youtube.com/watch?v=' in req or 'http://m.youtube.com/watch?' in req:
		ytid=''
		try:
		    ytid = re.search('\?v=(.*?)&',req).group(1)
		except:
		    try:
			ytid = re.search('\?v=(.*)',req).group(1)
		    except:
			try:
			    ytid = re.search('&v=(.*?)&',req).group(1)
			except:
			    try:
				ytid = re.search('?&v=(.*)',req).group(1)
			    except:
				ytid=None
		if ytid:
		    if self.ytid == '' or ytid != self.ytid:
			self.ytid = ytid
		## if not match read new video
		if self.ytid != self.mainGui.media_link:
		    self.mainGui.media_link = self.ytid
		    self.mainGui.search_engine.on_paste(url=req)
		    
	elif 'http://www.dailymotion.com/embed/video/' in req:
		print "Dailymotion: Link detected, loading page...."
		code = Html.fromstring(urllib2.urlopen(req).read()).text_content()
		link=None
		title=None
		## get tile
		try:
		    title=urllib.unquote(re.search('(;*)title":"(.*?)",', code).group(2)).replace('\\','').replace('\'','')
		except:
		    title='Streaming dailymotion video...'
		self.mainGui.media_name=self.mainGui.clean_markup(title)
		try:
		    link = urllib.unquote(re.search('(;*)stream_h264_url\":\"(.*?)",', code).group(2)).replace('\\','')
		except:
		    try:
			link = urllib.unquote(re.search('(;*)stream_h264_ld_url\":\"(.*?)",', code).group(2)).replace('\\','')
		    except:
			print 'can t find video url...'
			try:
			     f=open('/tmp/truc',"w")
			     f.writelines(code)
			     f.close()
			     u=re.search('http://dailymotion.com(.*)&cache=0',code).group()
			except:
			    print ''
			link=''
		self.analyzed=True
		self.mainGui.start_play(link)
	elif 'vimeo.com' in req:
		if 'aksessionid' in req:
		    self.load_uri(self.origin)
		    self.mainGui.start_play(req)
		    self.analyzed=True
		else:
		    try:
			re.search("http://vimeo.com/[1-9].*/",req).group()
		    except:
			try:
			    if self.analyzed:
				return
			    vid=re.search("http://vimeo.com/([1-9].*)",req).group(1)
			    print vid
			    user_agent = 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.15 (KHTML, like Gecko) Ubuntu/10.10 Chromium/10.0.608.0 Chrome/10.0.608.0 Safari/534.15'
			    headers =  { 'User-Agent' : user_agent , 'Accept-Language' : 'fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4' }
			    request = urllib2.Request('http://player.vimeo.com/video/'+vid, None, headers)
			    try:
				webpage = urllib2.urlopen(request).read()
			    except (urllib2.URLError, httplib.HTTPException, socket.error), err:
				print "ERROR: Unable to retrieve video webpage: %s" % link
				return
				
			    # Extract the config JSON
			    config = webpage.split(' = {config:')[1].split(',assets:')[0]
			    try:
				config = json.loads(config)
			    except:
				print 'ERROR: unable to extract info section'
				return
			    
			    # Extract title
			    video_title = config["video"]["title"]
			    self.mainGui.media_name=video_title
			    
			    # Vimeo specific: extract request signature and timestamp
			    sig = config['request']['signature']
			    timestamp = config['request']['timestamp']
			    
			    # Vimeo specific: extract video codec and quality information
			    # TODO bind to format param
			    codecs = [('h264', 'mp4'), ('vp8', 'flv'), ('vp6', 'flv')]
			    for codec in codecs:
				if codec[0] in config["video"]["files"]:
				    video_codec = codec[0]
				    video_extension = codec[1]
				    if 'hd' in config["video"]["files"][codec[0]]: 
					quality = 'hd'
				    else: 
					quality = 'sd'
				    break
			    else:
				print 'ERROR: no known codec found'
				return
			    
			    video_url = "http://player.vimeo.com/play_redirect?clip_id=%s&sig=%s&time=%s&quality=%s&codecs=%s&type=moogaloop_local&embed_location=" %( vid, sig, timestamp, quality, video_codec.upper())
			    print video_url
			    self.analyzed=True
			    self.load_uri(video_url,origin=req)
			except:
			    pass
		    
	self.page_requests.append(req)
    
    def analyse_req(self):
	if self.analyzed:
	    return
	for req in self.page_requests:
	    if 'drtuber.com' in req and not 'mp4' in req:
		print "drtuber link detected: %s" % req
		code=None
		link=None
		code = self.view.get_html()
		link = re.search('/mp4/(.*?)video_bottom(.*?)"',code).group().replace('"','')
		self.load_uri('http://mobile.drtuber.com%s' % link)
		break
	    elif 'drtuber.com/mp4' in req:
		code=None
		link=None
		code = self.view.get_html()
		link = re.search('(.*)a href="((.*).mp4(.*?))"',code).group(2)
		self.analyzed=True
		self.mainGui.start_play(link)
		break
	    elif 'http://m.pornhub.com/video/show' in req:
		html=self.view.get_html()
		try:
		    link=re.search('.*(http://.*?mobile.pornhub.com/videos.*?mp4.*?)"',html).group(1).replace('"','').replace('&amp;','&')
		    print link
		    self.mainGui.start_play(link)
		    break
		except:
		    print 'can t find video link....'
		    break
	    elif 'http://mobile.youporn.com/video/show' in req:
		print req
		html=self.view.get_html()
		try:
		    link=re.search('.*(http://.*?mobile.youporn.*?mp4.*?)"',html).group(1).replace('"','').replace('&amp;','&')
		    print link
		    self.mainGui.start_play(link)
		    break
		except:
		    print 'can t find video link....'
		    break
	self.page_requests=[]
	    
    def stop_player(self):
	## hide/stop the flashplayer
	return
	try:
	    script = "player = document.getElementById('movie_player');"
	    script += "player.mute();"
	    script += "player.stopVideo();"
	    self.view.execute_script(script)
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
        self.url_bar.set_text(widget.get_main_frame().get_uri())
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
