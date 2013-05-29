import re
import urllib2,urllib
import gobject,glib
import json

try:
    from lib.functions import *
    from lib.get_stream import Browser
except:
    from GmediaFinder.lib.functions import *
    from GmediaFinder.lib.get_stream import Browser

class DailyMotion(object):
    def __init__(self,gui):
        self.gui = gui
        self.name = 'DailyMotion'
        self.engine_type = "video"
        self.options_dic = {}
        self.current_page = 1
        self.main_start_page = 1
        self.thread_stop=False
        self.has_browser_mode = False
        ## options labels
        self.order_label = _("Order by: ")
        self.filters_label = _("Filters: ")
        self.search_url = 'https://api.dailymotion.com/videos?%ssort=%s&page=%s&limit=25&search=%s&fields=embed_url,thumbnail_medium_url,title,views_total,duration'
        
        self.start_engine()
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        self.order_list = {self.order_label:{_("Most recent"):"recent",_("Most viewed"):"visited",_("Most rated"):"rated",_("Most relevant"):"relevance"}}
        self.orderby = create_comboBox(self.gui, self.order_list)
        self.filters_list = {self.filters_label:{"":"",_("HD"):"hd"}}
        self.filters = create_comboBox(self.gui, self.filters_list)
        self.orderby.setIndexFromString(_("Most relevant"))
        
    def get_search_url(self,query,page):
        choice = self.orderby.getSelected()
        orderby = self.order_list[self.order_label][choice]
        choice = self.filters.getSelected()
        f=''
        if choice != "":
            filters = self.filters_list[self.filters_label][choice]
            f = 'filters=%s&' % filters
        return self.search_url % (f,orderby,page,urllib.quote(query))
    
    def play(self,link):
        try:
            return self.gui.browser.load_uri(link)
        except:
            return
        
    def filter(self,data,user_search):
        js = json.load(data)
        l = js['list']
        for dic in l:
            if self.thread_stop == True:
                break
            title = dic['title']
            link = 'http://www.dailymotion.com/video/' + dic['embed_url'].rsplit('/',1)[1]
            img_link = dic['thumbnail_medium_url']
            duration = dic['duration']
            calc = divmod(int(duration),60)
            seconds = int(calc[1])
            if seconds < 10:
                seconds = "0%d" % seconds
            duration = "%d:%s" % (calc[0],seconds)
            total = dic['views_total']
            img = download_photo(img_link)
            values = {'total': total, 'duration': duration}
            markup = _("\n<small><b>views:</b> %(total)s        <b>Duration:</b> %(duration)s</small>") % values
            gobject.idle_add(self.gui.add_sound, title, link, img, None, self.name, markup)
        if js['has_more'] != 'true':
            values = {'name': self.name, 'query': user_search}
            self.print_info(_("%(name)s: No more results for %(query)s...") % values)
            time.sleep(5)
        self.thread_stop=True
        
    
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)

