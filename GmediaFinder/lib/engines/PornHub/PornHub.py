#-*- coding: UTF-8 -*-

import re
import urllib
import gobject

try:
    from lib.functions import *
    from lib.get_stream import Browser
except:
    from GmediaFinder.lib.functions import *
    from GmediaFinder.lib.get_stream import Browser

class PornHub(object):
    def __init__(self,gui):
        self.gui              = gui
        self.name             = "PornHub"
        self.engine_type      = "video"
        self.current_page     = 1
        self.main_start_page  = 1
        self.thread_stop      = False
        self.adult_content    = True
        self.has_browser_mode = False
        self.scrapper=self.gui.browser
        self.search_url       = "http://www.pornhub.com/video/search?search=%s&o=%s&page=%s"
        self.category_url     = "http://www.empflix.com/channels/new-%s-%s.html"
        ## options labels
        self.order_label      = _("Order by: ")
        self.cat_label        = _("Category: ")
        self.start_engine()
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        ## create orderby combobox
        self.orderbyOpt = {self.order_label:{  _("Most recent"):"mr",_("Most viewed"):"mv",
                                               _("Top rated"):"tr",_("Longest"):"lg",
                                            },
                           }
        self.orderby = create_comboBox(self.gui, self.orderbyOpt)
        self.orderby.setIndexFromString(_("Most recent"))
    
    def get_search_url(self,query,page):
        choice  = self.orderby.getSelected()
        orderby = self.orderbyOpt[self.order_label][choice]
        return self.search_url % (urllib.quote_plus(query),orderby,page)
    
    def play(self,link):
        data = self.scrapper.load_uri(link)
        
    def filter(self,data,user_search):
        flag_found = False
        end_flag   = True
        title      = ""
        markup     = ""
        link       = ""
        for line in data.readlines():
            if self.thread_stop == True:
                break
            if 'class="img"' in line:
                flag_found = True
                link       = line.split('"')[1]
            if 'class="rotating"' in line:
                title      = re.search('alt=\"(.*?)\"', line).group(1)
                img_link = re.search('data-smallthumb=\"(.*?)\"', line).group(1)
                img      = download_photo(img_link)
                gobject.idle_add(self.gui.add_sound, title, link, img, None, self.name)
                if 'Our Friends' in line:
                    break
        if not flag_found:
            self.print_info(_("%s: No results for %s...") % (self.name,user_search))
            time.sleep(5)
        self.thread_stop=True
    
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
    
