#-*- coding: UTF-8 -*-

import mechanize
import re
import urllib, urllib2
import gtk
import time
import gobject

try:
    from lib.functions import *
    from lib.get_stream import Browser
except:
    from GmediaFinder.lib.functions import *
    from GmediaFinder.lib.get_stream import Browser

URL = "http://drtuber.com"
SEARCH_URL = "%s/search/videos/%s/%s" % (URL, "%s", "%s")

class DrTuber(object):
    def __init__(self,gui):
        self.gui = gui
        self.name ="DrTuber"
        self.engine_type = "video"
        self.current_page = 1
        self.main_start_page = 1
        self.thread_stop=False
        self.adult_content=True
        self.search_url = SEARCH_URL
        self.initialized=False
        self.has_browser_mode = False
        ## options labels
        self.browser = mechanize.Browser()
        self.browser.addheaders = []
        self.scrapper=Browser(gui)
        self.start_engine()
    
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        pass
    
    def filter(self, data, query):
        flag_found = False
        title=""
        markup=""
        link=""
        for line in data.readlines():
            if self.thread_stop == True:
                break
            ## search link
            if '/media/videos/tmb' in line and 'jpg' in line:
                flag_found = True
                img_link = re.search('src=\"(.*?)\"',line).group(1)
                img = download_photo(img_link)
                #print img_link
            elif 'class="item_title"' in line:
                title = re.search('>(.*?)<',line).group(1)
                #print title
            elif 'href="/video/' in line:
                link = re.search('href=\"(.*?)\"',line).group(1)
                #print link
                try:
                    gobject.idle_add(self.gui.add_sound, title, link, img, None, self.name)
                except:
                    continue
            
        if not flag_found:
            self.print_info(_("%s: No results for %s...") % (self.name,query))
            time.sleep(5)
        self.thread_stop=True
    
    def get_search_url(self,query,page):
        #print SEARCH_URL % (query,page)
        return SEARCH_URL % (query,page)
    
    def search(self, data, query, page):
        try:
            print data
            self.filter(data, query)
        except:
            self.print_info(_("%s: Connexion failed...") % self.name)
            time.sleep(5)
            self.thread_stop=True
            
    def play(self,link):
        self.scrapper.load_uri(URL + link)

    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
    
