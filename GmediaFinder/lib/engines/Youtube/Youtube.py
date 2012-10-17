import re
import urllib
import gdata.youtube.service as yt_service
import gobject, thread
import os
import sys
from subprocess import Popen,PIPE,STDOUT

try:
    from lib.functions import *
    from lib.config import *
except:
    from GmediaFinder.lib.functions import *
    from GmediaFinder.lib.config import img_path,_

class Youtube(object):
    def __init__(self,gui):
        self.gui = gui
        self.current_page = 1
        self.main_start_page = 1
        self.engine_type = "video"
        self.num_start = 1
        self.results_by_page = 25
        self.name="Youtube"
        self.client = yt_service.YouTubeService()
        self.youtube_max_res = "320x240"
        self.media_codec = None
        self.thread_stop= False
        self.has_browser_mode = False
        self.vp8 = False
        self.updateBrowser=True
        self.qlist_checked=False
        ## the gui box to show custom filters/options
        self.opt_box = self.gui.gladeGui.get_widget("search_options_box")
        ## options labels
        self.order_label = _("Order by: ")
        self.category_label = _("Category: ")
        ## video quality combobox
        self.youtube_quality_box = self.gui.gladeGui.get_widget("quality_box")
        
        self.youtube_quality_model = gtk.ListStore(str)
        self.youtube_video_rate = gtk.ComboBox(self.youtube_quality_model)
        cell = gtk.CellRendererText()
        self.youtube_video_rate.pack_start(cell, True)
        self.youtube_video_rate.add_attribute(cell, 'text', 0)
        self.youtube_quality_box.add(self.youtube_video_rate)
        new_iter = self.youtube_quality_model.append()
        self.youtube_quality_model.set(new_iter,
                                0, _("Quality"),
                                )
        self.youtube_video_rate.connect('changed', self.on_youtube_video_rate_changed)

        ## youtube video quality choices
        self.res320 = self.gui.gladeGui.get_widget("res1")
        self.res640 = self.gui.gladeGui.get_widget("res2")
        self.res854 = self.gui.gladeGui.get_widget("res3")
        self.res1280 = self.gui.gladeGui.get_widget("res4")
        self.res1920 = self.gui.gladeGui.get_widget("res5")

        ## SIGNALS
        dic = {
        "on_res1_toggled" : self.set_max_youtube_res,
        "on_res2_toggled" : self.set_max_youtube_res,
        "on_res3_toggled" : self.set_max_youtube_res,
        "on_res4_toggled" : self.set_max_youtube_res,
        "on_res5_toggled" : self.set_max_youtube_res,
         }
        self.gui.gladeGui.signal_autoconnect(dic)
        ## start
        self.start_engine()

    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)

    def start_engine(self):
        self.gui.engine_list[self.name] = ''
        ## get default max_res for youtube videos
        try:
            self.youtube_max_res = self.gui.conf["youtube_max_res"]
        except:
            self.gui.conf["youtube_max_res"] = self.youtube_max_res

        if self.youtube_max_res == "320x240":
            self.res320.set_active(1)
        elif self.youtube_max_res == "640x360":
            self.res640.set_active(1)
        elif self.youtube_max_res == "854x480":
            self.res854.set_active(1)
        elif self.youtube_max_res == "1280x720":
            self.res1280.set_active(1)
        elif self.youtube_max_res == "1920x1080":
            self.res1920.set_active(1)

        gobject.idle_add(self.youtube_video_rate.hide)
        gobject.idle_add(self.youtube_video_rate.set_active,0)

    
    
    
    def load_gui(self):
        ## paste entry
        image = gtk.Image()
        image.set_from_stock(gtk.STOCK_PASTE,24) 
        button = gtk.Button()
        button.set_image(image)
        button.connect("clicked", self.on_paste)
        button.set_tooltip_text(_('Paste youtube link'))
        button.props.relief = gtk.RELIEF_NONE
        self.gui.search_opt_box.pack_start(button,False,False,10)
        
        ## create orderby combobox
        cb = create_comboBox()
        self.orderbyOpt = {self.order_label:{_("Most relevant"):"relevance",
                                             _("Most recent"):"published",_("Most viewed"):"viewCount",
                                             _("Most rated"):"rating",
            },
        }
        self.orderby = create_comboBox(self.gui, self.orderbyOpt)
        
        ## create categories combobox
        self.category = ComboBox(cb)
        self.catlist = {self.category_label:{"":"",_("Sport"):"Sports",
                                             _("Films"):"Film",_("Cars"):"Autos",
                                             _("Music"):"Music",_("Technology"):"Tech",_("Animals"):"Animals",
                                             _("Travel"):"Travel",_("Games"):"Games",_("Comedy"):"Comedy",
                                             _("Peoples"):"People",_("News"):"News",
                                             _("Entertainement"):"Entertainment",_("Trailers"):"Trailers",
            },
        }
        self.category = create_comboBox(self.gui, self.catlist)
        self.orderby.setIndexFromString(_("Most relevant"))
        
        gobject.idle_add(self.gui.search_opt_box.show_all)
        
        ## vp8 check
        if not sys.platform == 'win32':
            out,err = Popen('/usr/bin/gst-inspect-0.10| grep vp8',shell=True,stdout=PIPE,stderr=STDOUT).communicate()
            if 'vp8' in str(out):
                self.vp8 = True
            else:
                out,err = Popen('/usr/bin/gst-inspect | grep vp8',shell=True,stdout=PIPE,stderr=STDOUT).communicate()
                if 'vp8' in str(out):
                    self.vp8 = True
        else:
            self.vp8 = True
        
    def on_paste(self,widget=None,url=None):
        text = ''
        update=True
        if not url:
            clipboard = gtk.Clipboard(gtk.gdk.display_get_default(), "CLIPBOARD")
            data = clipboard.wait_for_contents('UTF8_STRING')
            try:
                text = data.get_text()
            except:
                gobject.idle_add(error_dialog,_("There's no link to paste..."))
                return
        else:
            text = url
        if text != '':
            vid=self.get_videoId(text)
            if vid == '':
                return
            yt = yt_service.YouTubeService()
            entry = yt.GetYouTubeVideoEntry(video_id='%s' % vid)
            self.filter(entry, '', update)
        else:
            return

    def get_videoId(self,text):
        vid=None
        try:
            vid = re.search('watch\?v=(.*?)&',text).group(1)
        except:
            try:
                vid = re.search('watch\?v=(.*)',text).group(1)
            except:
                try:
                    vid = os.path.basename(os.path.dirname(text))
                except:
                    error_dialog(_('Your link:\n\n%s\n\nis not a valid youtube link...' % text))
                    return
        if vid=='':
            error_dialog(_('Your link:\n\n%s\n\nis not a valid youtube link...' % text))
            return
        return vid
        
    def set_max_youtube_res(self, widget):
        if widget.get_active():
            self.youtube_max_res = widget.get_child().get_label()
            self.gui.conf["youtube_max_res"] = self.youtube_max_res
            ## return a dic as conf
            try:
                self.gui.conf.write()
            except:
                print "Can't write to the %s config file..." % self.gui.conf_file

    def get_search_url(self,user_search,page):
        return self.search(user_search,page)
    
    def search(self,user_search,page):
        self.thread_stop=False
        nlist = []
        link_list = []
        next_page = 0
        ## prepare query
        query = yt_service.YouTubeVideoQuery()
        query.vq = user_search # the term(s) that you are searching for
        query.max_results = '25'
        #query.lr = 'fr'
        orderby = self.orderby.getSelected()
        query.orderby = self.orderbyOpt[self.order_label][orderby]
        cat = self.category.getSelected()
        if self.category.getSelectedIndex() != 0:
            query.categories.append('/%s' % self.catlist[self.category_label][cat])

        if self.current_page == 1:
            self.num_start = 1
        query.start_index = self.num_start
        vquery = self.client.YouTubeQuery(query)
        return vquery

    def filter(self,vquery,user_search,direct_link=None):
        if not vquery :
            self.num_start = 1
            self.current_page = 1
            self.print_info(_("%s: No results for %s ...") % (self.name,user_search))
            time.sleep(5)
            self.thread_stop=True

        if direct_link is not None:
            #gobject.idle_add(self.gui.model.clear)
            self.thread_stop=True
            self.make_youtube_entry(vquery, True, direct_link)
        
        try:
            if len(vquery.entry) == 0:
                self.print_info(_("%s: No results for %s ...") % (self.name,user_search))
                time.sleep(5)
                self.thread_stop=True
                return
        except:
            self.thread_stop=True
            return

        for entry in vquery.entry:
            if not self.thread_stop:
                self.make_youtube_entry(entry)
            else:
                return
        self.thread_stop=True  
                

    def play(self,link):
        self.qlist_checked = False
        self.load_youtube_res(link)
        self.gui.media_link=link
        active = self.youtube_video_rate.get_active()
        try:
            if self.updateBrowser:
                print "updating browser"
                #self.update_media_infos(link)
            self.media_codec = self.quality_list[active].split('|')[1]
            #self.gui.player.play_toggled(self.media_link[active])
        except:
            self.gui.start_play('')

    def update_media_infos(self,link):
        link = 'http://www.youtube.com/watch?v=%s' % link
        self.gui.browser.load_uri(link)
    
    def make_youtube_entry(self,video,read=None, select=False):
        duration = video.media.duration.seconds
        calc = divmod(int(duration),60)
        seconds = int(calc[1])
        if seconds < 10:
            seconds = "0%d" % seconds
        duration = "%d:%s" % (calc[0],seconds)
        url = video.link[1].href
        thumb = video.media.thumbnail[-1].url
        count = 0
        try:
            count = video.statistics.view_count
        except:
            pass
        vid_id=self.get_videoId(url)
        if vid_id == '':
            return
        try:
            vid_pic = download_photo(thumb)
        except:
            return
        title = video.title.text
        if not count:
            count = 0

        
        values = {'name': title, 'count': count, 'duration': duration}
        markup = _("\n<small><b>view:</b> %(count)s        <b>Duration:</b> %(duration)s</small>") % values
        if not title or not url or not vid_pic:
            return
        gobject.idle_add(self.gui.add_sound,title, vid_id, vid_pic,None,self.name,markup,None,select)
                

    def get_codec(self, num):
        codec=None
        if re.match('5',num):
            codec = "flv"
        elif re.match('18|22|38|37|34|35',num):
            codec= "mp4"
        elif re.match('43|44|45',num):
            codec= "webm"
        elif re.match('17',num):
            codec= "3gp"
        return codec
    
    def load_youtube_res(self,link):
        gobject.idle_add(self.youtube_quality_model.clear)
        gobject.idle_add(self.youtube_video_rate.show)
        self.media_link = None
        self.quality_list = None
        #try:
        self.media_link,self.quality_list =self.get_quality_list(link)
        #except:
        #    return
        if not self.quality_list:
            return
        for rate in self.quality_list:
            try:
                new_iter = self.youtube_quality_model.append()
                self.youtube_quality_model.set(new_iter,
                                0, rate,
                                )
            except:
                continue
        self.set_default_youtube_video_rate()

    def set_default_youtube_video_rate(self,widget=None):
        active = self.youtube_video_rate.get_active()
        qn = 0
        ## if there s only one quality available, read it...
        if active == -1:
            if len(self.quality_list) == 1:
                self.youtube_video_rate.set_active(0)
            for frate in self.quality_list:
                try:
                    rate = frate.split('|')[0]
                    codec = frate.split('|')[1]
                    h = int(rate.split('x')[0])
                    dh = int(self.youtube_max_res.split('x')[0])
                    if h > dh:
                        qn += 1
                        continue
                    else:
                        if codec == 'mp4' and '%s|webm' % rate in str(self.quality_list):
                            #qn += 1
                            continue
                    self.youtube_video_rate.set_active(qn)
                except:
                    continue
            active = self.youtube_video_rate.get_active()
        else:
            if self.quality_list:
                active = self.youtube_video_rate.get_active()
        gobject.idle_add(self.gui.quality_box.show)

    def on_youtube_video_rate_changed(self,widget):
        if self.qlist_checked == False:
            return
        active = self.youtube_video_rate.get_active()
        print "Youtube: video rate changed -> %s" % active
        try:
            self.media_codec = self.quality_list[active].split('|')[1]
            self.gui.start_play(self.media_link[active])
        except:
            pass

    def get_quality_list(self,vid_id):
        links_arr = []
        quality_arr = []
        #try:
        req = urllib2.Request("http://www.youtube.com/get_video_info?video_id=%s" % vid_id)
        stream = urllib2.urlopen(req)
        contents = urllib.unquote(stream.read())
        if re.search('status=fail',contents):
            req = urllib2.Request("http://www.youtube.com/watch?v=%s" % vid_id)
            stream = urllib2.urlopen(req)
            contents = urllib.unquote(stream.read())
        ## links list
        try:
            matches = re.search("url_encoded_fmt_stream_map=(.*?)&length_seconds",contents).group(1)
        except:
            try:
                matches = re.search("url_encoded_fmt_stream_map=(.*?)\">",contents).group(1)
            except:
                matches = re.search("url_encoded_fmt_stream_map=(.*)",contents).group(1)
        fmt_arr = urllib.unquote(matches).split('&quality')
        ## quality_list
        regexp1 = re.compile("fmt_list=([^&]+)&")
        matches = regexp1.search(contents).group(1)
        quality_list = urllib.unquote(matches).split(',')
        stream.close()
        ##
        link_list = []
        for link in fmt_arr:
            try:
                res = re.search('url=(.*)', link).group(1)
                link=re.sub('sig','signature',res)
                link_list.append(link)
            except:
                continue
        ## remove flv links...
        i = 0
        if quality_list[0] == quality_list[1]:
            quality_list.remove(quality_list[0])
            fmt_arr.remove(fmt_arr[0])
        for quality in quality_list:
            try:
                #print quality
                codec = self.get_codec(quality)
                if codec == 'webm' and not self.vp8:
                    i+=1
                    continue
                if codec == "flv" and quality.split("/")[1] == "320x240" and re.search("18/320x240",str(quality_list)):
                    i+=1
                    continue
                elif codec == "flv" and quality.split("/")[1] != "320x240":
                    i+=1
                    continue
                elif quality == '18/640x360/9/0/115' and re.search("34/640x360/9/0/115",str(quality_list)):
                    i+=1
                    continue
                else:
                    links_arr.append(link_list[i])
                    q = quality.split("/")[1] + "|%s" % codec
                    quality_arr.append(quality.split("/")[1] + "|%s" % codec)
                    i+=1
            except:
                continue
        #except:
        #    return
        self.qlist_checked =True
        return links_arr, quality_arr
