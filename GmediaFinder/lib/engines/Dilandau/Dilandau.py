import gobject
import urllib2
import urllib
import time
import os
import mechanize

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
        self.browser = mechanize.Browser()
        self.browser.addheaders = [('User-Agent','Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30')]
        self.search_url = "http://fr.dilandau.eu/telecharger-musiques-mp3/%s/%s.html"
        self.start_engine()
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        pass
    
    def get_search_url(self,query,page):
        values = {'name': self.name, 'query': query}
        self.print_info(_('%(name)s: Searching for %(query)s with dilandau...') % values)
        return self.search_url % (query,page)
        
    def filter(self, d, user_search):
        flag_found = False
        data = d.read().split('/>')
        for line in data:
            if self.thread_stop:
                break
            if '<a download="' in line:
                titre = decode_htmlentities(re.search('data-filename=\"(.*?)\"', line).group(1))
                href = re.search('<a download=(.*?)" href="(.*?)"',line).group(2)
                url= re.search('url=\"(.*?)\"', line).group(1)
                gobject.idle_add(self.gui.add_sound, titre, href+url, None, None, self.name)
                flag_found = True
                continue
        if not flag_found:
            values = {'name': self.name, 'query': query}
            self.print_info(_("%(name)s: No results for %(query)s...") % values)
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
   
