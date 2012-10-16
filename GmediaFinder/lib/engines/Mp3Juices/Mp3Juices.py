import gobject
import urllib2
import urllib
import time
import os

try:
    from lib.functions import *
except:
    from GmediaFinder.lib.functions import *
    
class Mp3Juices(object):
    def __init__(self,gui):
        self.gui = gui
        self.engine_type = "audio"
        self.name="Mp3Juices"
        self.current_page = 1
        self.main_start_page = 1
        self.thread_stop=False
        self.has_browser_mode = False
        self.search_url = "http://mp3juices.com/search/%s/%s"
        self.start_engine()
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        pass
    
    def get_search_url(self,query,page):
        self.print_info(_('%s: Searching for %s...') % (self.name,query))
        return self.search_url % (query,page)
        
    def filter(self, d, user_search):
		flag_found = False
		data=d.read().split('loadPlayer')
		if len(data) == 0:
			self.print_info(_("%s: No results for %s...") % (self.name,user_search))
			time.sleep(5)
			self.thread_stop=True
		data.pop(0)
		data.pop(0)
		for line in data:
			if self.thread_stop:
				break
			titre=line.split(',')[2].replace('"','').strip()
			url=line.split(',')[1].replace('"','').strip()
			gobject.idle_add(self.gui.add_sound, titre, url, None, None, self.name)
		self.thread_stop=True
        
    def play(self,link):
        try:
            self.gui.media_link = link
            self.gui.start_play(link)
        except:
            return
        
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
   