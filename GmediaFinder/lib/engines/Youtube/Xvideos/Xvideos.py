import re
import urllib
import gobject

try:
    from lib.functions import *
except:
    from GmediaFinder.lib.functions import *

class Xvideos(object):
    def __init__(self,gui):
        self.gui = gui
        self.name = "Xvideos"
        self.engine_type = "video"
        self.current_page = 1
        self.main_start_page = 1
        self.thread_stop=False
        self.adult_content=True
        self.has_browser_mode = False
        self.search_url = "http://www.xvideos.com/?k=%s&sort=%s&p=%s"
        self.order_label = _("Order by: ")
        self.start_engine()
    
    def start_engine(self):
        self.gui.engine_list[self.name] = ''
    
    def load_gui(self):
        ## create orderby combobox
        self.orderbyOpt = {self.order_label:{_("Most recent"):"uploaddate",
                                            _("Most rated"):"rated",_("Most relevant"):"relevance",
            },
        }
        self.orderby = create_comboBox(self.gui, self.orderbyOpt)
        self.orderby.setIndexFromString(_("Most relevant"))
    
    def get_search_url(self,query,page):
        choice = self.orderby.getSelected()
        orderby = self.orderbyOpt[self.order_label][choice]
        return self.search_url % (query,orderby,page-1)
    
    def play(self, link):
        data = get_url_data('http://www.xvideos.com'+link)
        for line in data.readlines():
            if 'flv_url=' in line:
                link = urllib.unquote(re.search('flv_url=([^&]*)', line).group(1))
                self.gui.media_link = link
                break
        self.gui.start_play(link)
        
    def filter(self,data,user_search):
        flag_found = False      
        for line in data.readlines():
            if self.thread_stop == True:
                break
            ## search link
            if 'id="pic_' in line:
                img = re.search('src=\"(.*?)\"', line).group(1)
                img = download_photo(img)
                continue
            if '<a href="/video' in line:
                link = re.search('href=\"(.*?)\"', line).group(1)
                title = line.split('>')[2].split('<')[0]
                continue
            if 'class="duration"' in line:
                duration = '    <small>%s</small>' % line.split('>')[1].split('<')[0]
                try:
                    gobject.idle_add(self.gui.add_sound, title, link, img, None, self.name, duration)
                except:
                    continue
                flag_found = True
                continue
        if not flag_found:
            self.print_info(_("%s: No results for %s...") % (self.name,user_search))
            time.sleep(5)
        self.thread_stop=True
    
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
    
