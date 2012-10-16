import gobject
import urllib2
import urllib
import time
import os

try:
    from lib.functions import *
except:
    from GmediaFinder.lib.functions import *
    
class Dilandau(object):
    def __init__(self,gui):
        self.gui = gui
        self.engine_type = "audio"
        self.name="Dilandau"
        self.current_page = 1
        self.main_start_page = 1
        self.thread_stop=False
        self.has_browser_mode = False
        self.search_url = "http://fr.dilandau.eu/telecharger-mp3/%s-%s.html"
        self.start_engine()
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        pass
    
    def get_search_url(self,query,page):
        self.print_info(_('%s: Searching for %s with dilandau...') % (self.name,query))
        return self.search_url % (query,page)
        
    def filter(self, d, user_search):
        flag_found = False
        data=d.read().split('/>') 
        for line in data:
			if self.thread_stop:
				break
			if 'class="title_song"' in line:
				titre = decode_htmlentities(re.search('title=\"(.*?)\"', line).group(1))
			if '<a class="button tip download_button"' in line:
				url = re.search('href=\"(.*?)\"', line).group(1)
				gobject.idle_add(self.gui.add_sound, titre, url, None, None, self.name)
				flag_found = True
				continue
        if not flag_found:
            self.print_info(_("%s: No results for %s...") % (self.name,user_search))
            time.sleep(5)
        self.thread_stop=True
        
    def play(self,link):
        try:
            self.gui.media_link = link
            self.gui.start_play(link)
        except:
            return
        
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
   
