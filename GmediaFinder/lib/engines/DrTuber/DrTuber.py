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
            elif 'class="score_up"' in line:
                link = re.search('href=\"(.*?)\"',line).group(1)
                title = re.search('title=\"(.*?)\"',line).group(1)
                gobject.idle_add(self.gui.add_sound, title, link, img, None, self.name)
                continue
            
        if not flag_found:
            self.print_info(_("%s: No results for %s...") % (self.name,query))
            time.sleep(5)
        self.thread_stop=True
    
    def get_search_url(self,query,page):
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
        res = None
        print URL + link
        data = self.scrapper.load_uri(URL + link)
        #for line in data.readlines():
            #if 'config=/player/config.php' in line:
                #print line
                #config = re.search('(.*)config=(.*?)&id=player',line).group(2)
                #res = self.scrapper.load_uri(URL + config)
                #break
        #for line in res.readlines():
            #if '<video_file>' in line:
                #link = re.search('<video_file>(.*?)</video_file>',line).group(1)
                #self.gui.media_link = link
                #break
        #return self.gui.start_play(link)
            
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
    