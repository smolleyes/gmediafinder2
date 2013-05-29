#-*- coding: UTF-8 -*-

import re,os
import urllib
import gobject
import json
try:
    from lib.functions import *
    from lib.get_stream import Browser
except:
    from GmediaFinder.lib.functions import *
    from GmediaFinder.lib.get_stream import Browser

class Vimeo(object):
    def __init__(self,gui):
        self.gui              = gui
        self.name             = "Vimeo"
        self.engine_type      = "video"
        self.current_page     = 1
        self.main_start_page  = 1
        self.thread_stop      = False
        self.adult_content    = True
        self.has_browser_mode = False
        self.scrapper=self.gui.browser
        self.search_url       = "http://vimeo.com/search/page:%s/sort:%s/format:thumbnail?q=%s"
        ## options labels
        self.order_label      = _("Order by: ")
        self.start_engine()
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        ## create orderby combobox
        self.orderbyOpt = {self.order_label:{  _("Relevant"):"relevant",_("Date"):"date",
                                               _("Alphabetical"):"alphabetical",_("Plays"):"plays",
                                               _("Likes"):"likes",_("Comments"):"comments",
                                               _("Duration"):"duration",
                                            },
                           }
        self.orderby = create_comboBox(self.gui, self.orderbyOpt)
        self.orderby.setIndexFromString(_("Relevant"))
        self.scrapper.load_uri('http://vimeo.com/search')
    
    def get_search_url(self,query,page):
        choice  = self.orderby.getSelected()
        orderby = self.orderbyOpt[self.order_label][choice]
        print self.search_url % (page,orderby,urllib.quote_plus(query))
        return self.search_url % (page,orderby,urllib.quote_plus(query))
    
    def play(self,link):
        user_agent = 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.15 (KHTML, like Gecko) Ubuntu/10.10 Chromium/10.0.608.0 Chrome/10.0.608.0 Safari/534.15'
        headers =  { 'User-Agent' : user_agent , 'Accept-Language' : 'fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4' }
        request = urllib2.Request(link, None, headers)
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
        
        video_url = "http://player.vimeo.com/play_redirect?clip_id=%s&sig=%s&time=%s&quality=%s&codecs=%s&type=moogaloop_local&embed_location=" %( os.path.basename(link), sig, timestamp, quality, video_codec.upper())
        print video_url
        self.scrapper.load_uri(video_url,origin=link)
        
    def filter(self,data,user_search):
        flag_found = False
        end_flag   = True
        title      = ""
        markup     = ""
        link       = ""
        img=""
        for line in data.readlines():
            if self.thread_stop == True:
                break
            if 'id="clip_' in line:
                flag_found = True
                link = re.search('id=\"(.*?)\"', line).group(1).replace('clip_','')
            if 'class="thumbnail thumbnail_lg_wide"' in line:
                img_link = re.search('src=\"(.*?)\"', line).group(1)
                img      = download_photo(img_link)
            if 'a href="/%s' % link in line and 'title=' in line and not 'data-' in line:
                title=re.search('title="(.*)"', line).group(1)
                gobject.idle_add(self.gui.add_sound, title, 'http://vimeo.com/'+link, img, None, self.name)

        if not flag_found:
            values = {'name': self.name, 'query': user_search}
            self.print_info(_("%(name)s: No results for %(query)s...") % values)
            time.sleep(5)
        self.thread_stop=True
    
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
    
