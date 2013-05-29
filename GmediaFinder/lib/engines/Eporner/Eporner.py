import re
import urllib
import gobject

try:
    from lib.functions import *
except:
    from GmediaFinder.lib.functions import *

class Eporner(object):
    def __init__(self,gui):
        self.gui = gui
        self.name="Eporner"
        self.engine_type = "video"
        self.current_page = 1
        self.main_start_page = 1
        self.thread_stop=False
        self.adult_content=True
        self.has_browser_mode = False
        self.search_url = "http://mobile.eporner.com/keywords/%s/%s"
        self.category_url = "http://www.redtube.com/redtube/%s?sorting=%s&page=%s"
        ## options labels
        self.order_label = _("Order by: ")
        
        self.start_engine()
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        if self.gui.media_notebook.get_current_page() == 1:
            gobject.idle_add(self.gui.media_notebook.set_current_page,0)
        self.gui.browser.load_uri('http://eporner.com')
        ## create orderby combobox
        #self.orderbyOpt = {self.order_label:{_("Most recent"):"new",_("Most viewed"):"mostviewed",
         #                                   _("Most rated"):"top",_("Most relevant"):"",
         #   },
        #}
        #self.orderby = create_comboBox(self.gui, self.orderbyOpt)
        #self.orderby.setIndexFromString(_("Most relevant"))
    
    def get_search_url(self,query,page):
        return self.search_url % (query,page-1)
    
    def play(self,link):
        self.gui.start_play(link)
        
    def filter(self,data,user_search):
        flag_found = False
        end_flag=True
        title=""
        markup=""
        link=""
        for line in data.read().split('>'):
            if self.thread_stop == True:
                break
            ## search link
            if '<a href="/hd-porn/' in line:
                vid=re.search('/hd-porn/(.*?)/',line).group(1)
                link="http://mobile.eporner.com/dl2/%s/0" % vid
                title = re.search('title=\"(.*?)\"',line).group(1)
            elif '<img id="' in line and 'alt="%s' % title in line:
                img_link = re.search('src=\"(.*?)\"',line).group(1)
                img = download_photo(img_link)
                gobject.idle_add(self.gui.add_sound, title, link, img, None, self.name)
            ## check for next page
            elif 'id="navNext"' in line:
                end_flag=False
            continue
        if not flag_found:
            values = {'name': self.name, 'query': user_search}
            self.print_info(_("%(name)s: No results for %(query)s...") % values)
            time.sleep(5)
        self.thread_stop=True
    
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
    
