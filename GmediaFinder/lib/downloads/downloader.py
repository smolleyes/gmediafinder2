#-*- coding: UTF-8 -*-
#
# gmediafinder's downloader gui package
import gtk
import gobject
import pango

#custom lib
try:
    from lib.config import *
    from lib.functions import *
except:
    from GmediaFinder.lib.config import *
    from GmediaFinder.lib.functions import *
        
class Downloader(object):
    def __init__(self,mainGui):
        self.mainGui = mainGui
        self.gladeGui = mainGui.gladeGui
        
        ## custom download widget
        self.down_box = self.gladeGui.get_widget("down_box")
        self.down_menu_btn = self.gladeGui.get_widget("down_menu_btn")
        self.down_container = gtk.VBox(False, 5)
        self.down_scroll = gtk.ScrolledWindow()
        self.down_scroll.set_policy(gtk.POLICY_AUTOMATIC, gtk.POLICY_AUTOMATIC)
        self.down_scroll.add_with_viewport(self.down_container)
        self.down_box.add(self.down_scroll)
        self.active_down_label = self.gladeGui.get_widget("active_down_label")
        self.path_btn = self.gladeGui.get_widget("select_path_btn")
        self.down_dir = down_dir
        self.path_btn.set_current_folder(self.down_dir)
        self.path_btn.connect('current-folder-changed',self.update_down_path)
        
        ## download treeview
        self.download_treestore = gtk.TreeStore(str,int,str,str,str,
                                                str,
                                                str,
                                                str,
                                                str,
                                                str,object)
        #name
        self.download_treeview = gtk.TreeView(self.download_treestore)
        self.download_treeview.set_headers_visible(False)
        self.download_tvcolumn = gtk.TreeViewColumn('Name')
        self.download_tvcolumn.set_max_width(450)
        self.download_tvcolumn.set_min_width(450)
        self.download_treeview.append_column(self.download_tvcolumn)
        cellrenderer_text = gtk.CellRendererText()
        cellrenderer_text.props.wrap_width = 430
        cellrenderer_text.props.wrap_mode = pango.WRAP_WORD
        self.download_tvcolumn.pack_start(cellrenderer_text, False)
        self.download_tvcolumn.add_attribute(cellrenderer_text, "text", 0)
        #progress
        self.download_progresscolumn = gtk.TreeViewColumn("Progress")
        self.download_progresscolumn.set_spacing(10)
        self.download_progresscolumn.set_min_width(50)
        
        self.download_treeview.append_column(self.download_progresscolumn)
        cellrenderer_progress = gtk.CellRendererProgress()
        self.download_progresscolumn.pack_start(cellrenderer_progress, True)
        self.download_progresscolumn.add_attribute(cellrenderer_progress, "value", 1)
        #size
        self.download_sizecolumn = gtk.TreeViewColumn('Downloaded')
        self.download_sizecolumn.set_spacing(10)
        self.download_sizecolumn.set_min_width(150)
        self.download_treeview.append_column(self.download_sizecolumn)
        cellrenderer_text = gtk.CellRendererText()
        self.download_sizecolumn.pack_start(cellrenderer_text, False)
        self.download_sizecolumn.add_attribute(cellrenderer_text, "text", 2)
        #speed
        self.download_ratecolumn = gtk.TreeViewColumn('Rate')
        self.download_ratecolumn.set_spacing(10)
        self.download_ratecolumn.set_min_width(70)
        self.download_treeview.append_column(self.download_ratecolumn)
        cellrenderer_text = gtk.CellRendererText()
        self.download_ratecolumn.pack_start(cellrenderer_text, False)
        self.download_ratecolumn.add_attribute(cellrenderer_text, "text", 3)
        #eta
        self.download_etacolumn = gtk.TreeViewColumn('Eta')
        self.download_etacolumn.set_min_width(70)
        self.download_etacolumn.set_spacing(20)
        self.download_treeview.append_column(self.download_etacolumn)
        cellrenderer_text = gtk.CellRendererText()
        self.download_etacolumn.pack_start(cellrenderer_text, False)
        self.download_etacolumn.add_attribute(cellrenderer_text, "text", 4)
        ## pausebtn
        self.download_pausecolumn = gtk.TreeViewColumn('Pause/resume')
        self.download_pausecolumn.set_min_width(20)
        self.download_pausecolumn.set_spacing(40)
        self.download_treeview.append_column(self.download_pausecolumn)
        self.download_pixrenderer = gtk.CellRendererPixbuf()
        self.download_pausecolumn.pack_start(self.download_pixrenderer, False)
        self.download_pausecolumn.add_attribute(self.download_pixrenderer, "stock-id", 5)
        ## signals
        self.download_treeview.connect_after('cursor-changed',
                                            self.on_pause_download,
                                            self.download_pausecolumn)
        ## cancelbtn
        self.download_cancelcolumn = gtk.TreeViewColumn('Cancel')
        self.download_cancelcolumn.set_min_width(20)
        self.download_treeview.append_column(self.download_cancelcolumn)
        pixrenderer = gtk.CellRendererPixbuf()
        self.download_cancelcolumn.pack_start(pixrenderer, False)
        self.download_cancelcolumn.add_attribute(pixrenderer, "stock-id", 6)
        ## signals
        self.download_treeview.connect_after('cursor-changed',
                                            self.on_cancel_download,
                                            self.download_cancelcolumn)
        
        ## removebtn
        self.download_removecolumn = gtk.TreeViewColumn('remove')
        self.download_removecolumn.set_min_width(20)
        self.download_treeview.append_column(self.download_removecolumn)
        pixrenderer = gtk.CellRendererPixbuf()
        self.download_removecolumn.pack_start(pixrenderer, False)
        self.download_removecolumn.add_attribute(pixrenderer, "stock-id", 7)
        ## signals
        self.download_treeview.connect_after('cursor-changed', self.on_remove_download,
                                                    self.download_removecolumn)
                                                    
        ## viewbtn
        self.download_viewcolumn = gtk.TreeViewColumn('view')
        self.download_viewcolumn.set_min_width(20)
        self.download_treeview.append_column(self.download_viewcolumn)
        pixrenderer = gtk.CellRendererPixbuf()
        self.download_viewcolumn.pack_start(pixrenderer, False)
        self.download_viewcolumn.add_attribute(pixrenderer, "stock-id", 8)
        ## viewbtn
        self.download_treeview.connect_after('cursor-changed', self.on_view_download,
                                                    self.download_viewcolumn)
        
        ## convertbtn
        self.download_convertcolumn = gtk.TreeViewColumn('convert')
        self.download_convertcolumn.set_min_width(20)
        self.download_treeview.append_column(self.download_convertcolumn)
        pixrenderer = gtk.CellRendererPixbuf()
        self.download_convertcolumn.pack_start(pixrenderer, False)
        self.download_convertcolumn.add_attribute(pixrenderer, "stock-id", 9)
        ## viewbtn
        self.download_treeview.connect_after('cursor-changed', self.on_convert_download,
                                                    self.download_convertcolumn)
        
        ## finalize
        self.down_container.add(self.download_treeview)
        
        ## connect signals
        dic = {"on_down_btn_clicked" : self.mainGui.download_file,
               "on_down_menu_btn_clicked" : self.show_downloads,
               "on_backtohome_btn_clicked" : self.show_home,
               "on_select_path_btn_file_set" : self.update_down_path,
        }
        self.gladeGui.signal_autoconnect(dic)
        ## resume downloads if needed
        self.resume_downloads()
        
        
    ################################################################
    def on_pause_download(self, treeview, column):
        if self.download_treeview.get_cursor()[1] == column:
            # ici recup ligne selectionné
            l = self.return_selection(treeview)
            # get download instance
            download = l[-1]
            download.pause()
    
    ## retrieve colums clicked in the download widget
    def return_selection(self, treeview):
        sel              = self.download_treeview.get_selection()
        ( model,iter )   = sel.get_selected()
        return list(model[iter])
        
    def update_down_path(self,widget=None):
        self.mainGui.conf["download_path"] = widget.get_current_folder()
        self.mainGui.conf.write()
        self.down_dir = widget.get_current_folder()
    
    def show_downloads(self, widget):
        self.mainGui.notebook.set_current_page(1)
        
    def show_home(self, widget):
        self.mainGui.notebook.set_current_page(0)
        
    def on_cancel_download(self, treeview, column):
        if self.download_treeview.get_cursor()[1] == column:
            # ici recup ligne selectionné
            l = self.return_selection(treeview)
            # get download instance
            download = l[-1]
            download.cancel()
            
    def on_convert_download(self, treeview, column):
        if self.download_treeview.get_cursor()[1] == column:
            # ici recup ligne selectionné
            l = self.return_selection(treeview)
            # get download instance
            download = l[-1]
            download.convert()
            
    def on_remove_download(self, treeview, column):
        if self.download_treeview.get_cursor()[1] == column:
            # ici recup ligne selectionné
            l = self.return_selection(treeview)
            # get download instance
            download = l[-1]
            download.remove_download()
            
    def on_view_download(self, treeview, column):
        if self.download_treeview.get_cursor()[1] == column:
            # ici recup ligne selectionné
            l = self.return_selection(treeview)
            # get download instance
            return self.show_folder(self.down_dir)
            
    def show_folder(self,path):
        if sys.platform == "win32":
            os.system('explorer %s' % path)
        else:
            os.system('xdg-open %s' % path)
            
    def resume_downloads(self):
        for media in os.listdir(self.down_dir):
            try:
                if '.conf' in media:
                    conf = os.path.join(self.down_dir, media)
                    f = open('''%s''' % conf, 'r')
                    data = f.read()
                    f.close()
                    link = data.split(':::')[0]
                    name = data.split(':::')[1]
                    codec = data.split(':::')[2]
                    engine_type = data.split(':::')[3]
                    engine_name = data.split(':::')[4]
                    print engine_type
                    if str(engine_type) == 'files':
                        self.mainGui.download_debrid(link)
                    else:
                        self.mainGui.download_file(None,link, name, codec, None, engine_type, engine_name)
            except:
                continue
            

""" Inbox Files Downloader by maris@chown.lv. You are free do whatever You want with this code! """

import urllib2, urllib, cookielib, re, time, optparse, socket, os, sys

""" Poster lib for HTTP streaming upload, taken from http://atlee.ca/software/poster"""

import httplib, urllib2, socket

class FileDownloader(threading.Thread, Downloader):
    """ Files downloader class """
    createdir = False
    urlopen = urllib2.urlopen
    cj = cookielib.LWPCookieJar()
    Request = urllib2.Request
    
    post_data = None
    download_items = []
    TIMEOUT = 15
    
    localheaders = { 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.2) Gecko/2008092313 Ubuntu/8.04 (hardy) Firefox/3.1.6' }
    
    def __init__(self, gui, url, name, codec, data=None, engine_name=None, engine_type=None):
        threading.Thread.__init__(self)
        self.gui = gui
        self._stopevent = threading.Event()
        self.url = url
        self.data = data # urllib request reply
        ## filenames
        if codec is None:
            codec = '.mpeg'
        self.codec = codec
        if not '.' in codec:
            self.codec = '.'+self.codec
        bad_char = ['\\','@',',','\'','\"','/']
        for char in bad_char:
            if char in name:
                name = name.replace(char,' ')
        self.basename = name
        self.decoded_name = name+"%s" % self.codec
        self.encoded_name = urllib.quote(self.decoded_name.encode('utf-8'))
        self.target = os.path.join(self.gui.down_dir,self.decoded_name)
        self.temp_name = self.decoded_name
        self.temp_file = os.path.join(self.gui.down_dir,self.temp_name)
        self.conf_temp_name = '.'+self.decoded_name+'.conf'
        self.conf_temp_file = os.path.join(self.gui.down_dir,self.conf_temp_name)
        self.engine = self.gui.search_engine
        if not engine_type:
            self.engine_type = self.engine.engine_type
        else:
            self.engine_type = engine_type
        if not engine_name: 
            self.engine_name = self.engine.name
        else:
            self.engine_name = engine_name
        
        self.createdir = False
        self.paused = False
        self.stopped = False
        self.canceled = False
        self.failed = False
        self.completed = False
        self.download_response = None
        self.target_opener = None
        self.start_time = None
        size_local = None
        self.localheaders = { 'User-Agent' : 'Mozilla/5.0 (X11; U; Linux i686; en-US; rv:1.9.0.2) Gecko/2008092313 Ubuntu/8.04 (hardy) Firefox/3.1.6' }
        
        ## add thread to gui download pool
        self.gui.download_pool.append(self)
    
    def create_download_box(self):
        self.treeiter = self.gui.downloader.download_treestore.append(None, [self.decoded_name,0,_("Initializing download..."),'','','gtk-media-pause','gtk-cancel','gtk-clear','gtk-find','gtk-convert',self])
        # hide some icons
        self.gui.downloader.download_treestore.set_value(self.treeiter, 9, '')
        self.gui.downloader.download_treestore.set_value(self.treeiter, 7, '')
        
    def download(self, url, destination):
        self.increase_down_count()
        self.url = url
        self.target = destination
        self.gui.downloader.download_treestore.set_value(self.treeiter, 2,_("Starting download..."))
        resume = False
        if not self.data:
            try:
                req = urllib2.Request(url, headers = self.localheaders)
                self.gui.downloader.download_treestore.set_value(self.treeiter, 2,_("Sending download request..."))
                self.download_response = urllib2.urlopen(req, timeout=self.TIMEOUT)
            except :
                self.failed = True
                return False
        else:
            self.download_response = self.data
        headers = self.download_response.info()
        print "_____ Response Headers:\n %s" % headers
        if not headers.has_key('Content-Length'):
            print "content_length not available in headers..."
            self.failed = True
            return False
        elif int(headers['Content-Length']) == 0:
            print "content_length available but null..."
            self.failed = True
            return False
        ## response ok, start downloading checks
        if os.path.isfile(self.target) and float(headers['Content-Length']) == float(os.stat(self.target)[6]):
            self.gui.downloader.download_treestore.set_value(self.treeiter, 2,_("File already downloaded on disk..."))
            print "File already downloaded on disk...exit"
            self.completed = True
            return False
        elif os.path.isfile(self.temp_file):
            print "File is here but seems to be incomplete!"
            self.gui.downloader.download_treestore.set_value(self.treeiter, 2,_("File is here but seems to be incomplete!"))
            size_local = float(os.stat(self.temp_file)[6])
            size_on_server = float(headers['Content-Length'])
            print size_local, size_on_server
            if headers.has_key('Accept-Ranges') and headers['Accept-Ranges'] == 'bytes':
                print "Range request supported, trying to resume..."
                self.gui.downloader.download_treestore.set_value(self.treeiter, 2,_("Range request supported, trying to resume..."))
                try:
                    req = urllib2.Request(url, headers = self.localheaders)
                    req.add_header("range", "bytes=%d-%d"%(size_local,size_on_server))
                    self.download_response = urllib2.urlopen(req)
                    resume = True
                except:	
                    resume = False
                    self.temp_file += '.duplicate'
                    return False
            else:
                print "Range request not supported, redownloading file"
                self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Range request not supported, redownloading file..."))
                os.unlink(self.temp_file)
                return False
        try:
            self.target_opener = open(self.temp_file, "ab")
        except IOError, errmsg:
            print errmsg
            if not os.path.exists(self.temp_file):
                self.target_opener = open(self.temp_file, "wb")
            else:
                print "%s" %(errmsg)
                self.failed = True
                return True ## return true but failed
        self.start_time = time.time()
        try:
            if resume:
                current_bytes = size_local
            else:
                current_bytes = 0
            while True:
                try:
                    if self.canceled:
                        break
                    if self._stopevent.isSet():
                        self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("download stopped..."))
                        break
                    read_start = time.time()
                    if not self.paused:
                        try:
                            bytes = self.download_response.read(102400)
                        except:
                            self.failed = True
                            print "no more data...incomplete stream"
                            break
                        current_bytes += 102400
                        time_diff = time.time() - read_start
                        if time_diff == 0:
                            time_diff = 1
                        troughput = round((float(102400/time_diff)/1024)/1024*1024,2)
                        procents = float((float(current_bytes)/float(headers['Content-Length']))*100)
                        length = round((float(int(headers['Content-Length'])/1024))/1024,2)
                        current = round(float(current_bytes / (1024 * 1024)),2)
                        #current = float(int(current_bytes) / (1024 * 1024),2)
                        total = float(int(headers['Content-Length']) / (1024 * 1024))
                        mbs = '%.02f of %.02f MB' % (current, length)
                        e = '%d Kb/s ' % troughput
                        eta = calc_eta(self.start_time, time.time(), total, current)
                        if '-' in eta:
                            eta = "00:00"
                        if procents < 100 and not self.paused:
                            self.gui.downloader.download_treestore.set_value(self.treeiter, 1, procents)
                            self.gui.downloader.download_treestore.set_value(self.treeiter, 2, mbs)
                            self.gui.downloader.download_treestore.set_value(self.treeiter, 3, e)
                            self.gui.downloader.download_treestore.set_value(self.treeiter, 4, eta)
                        elif procents == 100:
                            self.gui.downloader.download_treestore.set_value(self.treeiter, 1, 100)
                            self.gui.downloader.download_treestore.set_value(self.treeiter, 3, '')
                            self.gui.downloader.download_treestore.set_value(self.treeiter, 4, '')
                        try:
                            self.target_opener.write(bytes)
                        except:
                            self.failed = True
                            break
                    else:
                        sleep(1)
                except IOError, (errno, strerror):
                    print "I/O error(%s): %s" % (errno, strerror)
                    self.failed = True
                    break
                except:
                    self.failed = True
                    break
                if bytes == "":
                    print "%s Finished" % (self.target)
                    ## clean conf file
                    self.completed = True
                    break
            sys.stdout.write("\n")
        except KeyboardInterrupt, errmsg:
            print "KeyboardInterrupt Caught: %s" % (errmsg)
            print "Cleaning up"
            self.canceled = True
        return True
    
    def remove_download(self, widget=None):
        self.gui.downloader.download_treestore.remove(self.treeiter)
    
    def run(self):
        self.create_download_box()
        while not self._stopevent.isSet():
            ## download...
            self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Starting download..."))
            try:
                self.start_time = time.time()
                self.check_target_file(self.temp_file)
                self.download(self.url, self.temp_file)
                if self.failed:
                    self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Download error..."))
                    self.download_finished()
                elif self.canceled:
                    self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Download canceled..."))
                    self.gui.downloader.download_treestore.set_value(self.treeiter, 8, '')
                    self.download_finished()
                ## already downloaded
                elif self.completed:
                    self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Download complete..."))
                    self.gui.downloader.download_treestore.set_value(self.treeiter, 1, 100)
                    if self.engine_type == 'video':
                        self.gui.downloader.download_treestore.set_value(self.treeiter, 9, 'gtk-convert')
                    self.download_finished()
                else:
                    continue
            except:
                print "failed"
                self.failed = True
                self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Download error..."))
                self.download_finished()
            
    def check_target_file(self,tmp_file):
        if not os.path.exists(self.conf_temp_file):
            f = open(self.conf_temp_file,'w')
            f.write(self.url+':::'+self.basename+':::'+self.codec+':::'+self.engine_type+':::'+self.engine_name)
            f.close()
        else:
            f = open(self.conf_temp_file,'r')
            data = f.read()
            f.close()
            link = data.split(':::')[0]
            name = data.split(':::')[1]
            codec = data.split(':::')[2]
            engine_type = data.split(':::')[3]
            engine_name = data.split(':::')[4]
            self.decoded_name = name+"%s" % codec
            self.encoded_name = urllib.quote(self.decoded_name.encode('utf-8'))
            self.target = os.path.join(self.gui.down_dir,self.decoded_name)
            self.temp_name = self.decoded_name
            self.temp_file = os.path.join(self.gui.down_dir,self.temp_name)
            self.conf_temp_name = '.'+self.decoded_name+'.conf'
            self.conf_temp_file = os.path.join(self.gui.down_dir,self.conf_temp_name)
            self.engine_type = engine_type
            self.engine_name = engine_name
            
    def download_finished(self):
        self.gui.downloader.download_treestore.set_value(self.treeiter, 5, '')
        self.gui.downloader.download_treestore.set_value(self.treeiter, 6, '')
        self.gui.downloader.download_treestore.set_value(self.treeiter, 7, 'gtk-clear')
        try:
            self.stop()
            self.engine.download_finished(self.url, self.target)
        except:
            self.stop()
        self.print_info('')
        self.gui.downloader.download_treestore.set_value(self.treeiter, 3, '')
        self.gui.downloader.download_treestore.set_value(self.treeiter, 4, '')
        gobject.idle_add(self.decrease_down_count)
    
    def cancel(self,widget=None):
        self.canceled = True
        self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Cancelling download..."))
        
    def stop(self,widget=None):
        self._stopevent.set()
        self.stopped = True
        try:
            self.target_opener.close()
            self.download_response.close()
        except:
            print "target file do not exist or closed..."
        if self.completed:
            if os.path.exists(self.conf_temp_file):
                os.remove(self.conf_temp_file)
        elif self.canceled or self.failed:
            if os.path.exists(self.conf_temp_file):
                os.remove(self.conf_temp_file)
            if os.path.exists(self.temp_file):
                os.remove(self.temp_file)
    
    def pause(self):
        if not self.paused:
            self.paused = True
            self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Download paused..."))
            self.decrease_down_count()
            self.gui.downloader.download_treestore.set_value(self.treeiter, 5, 'gtk-media-play')
        else:
            self.paused = False
            self.increase_down_count()
            self.gui.downloader.download_treestore.set_value(self.treeiter, 2, _("Resuming download..."))
            self.gui.downloader.download_treestore.set_value(self.treeiter, 5, 'gtk-media-pause')
    
    def convert(self):
        src = self.target
        target = src.replace(self.codec,'.mp3')
        if os.path.exists(target):
            os.remove(target)
        if sys.platform != "linux2":
            ffmpeg_path = os.path.join(os.path.dirname(os.path.dirname(config.exec_path)),'ffmpeg\\ffmpeg.exe').replace("\\","\\\\")
            target = target.replace("\\","\\\\")
            src = src.replace("\\","\\\\")
        else:
            ffmpeg_path = "/usr/bin/ffmpeg"
        self.print_info(_('Extracting audio...'))
        try:
            self.gui.throbber.show()
            (pid,t,r,s) = gobject.spawn_async([str(ffmpeg_path), '-i', str(src), '-f', 'mp3', '-ab', '192k', str(target)],flags=gobject.SPAWN_DO_NOT_REAP_CHILD,standard_output = True, standard_error = True)
            gobject.child_watch_add(pid, self.task_done)
        except:
            self.print_info(_('Extraction failed...'))
            sleep(4)
            self.print_info('')
            self.gui.throbber.hide()

    def task_done(self,pid,ret):
        self.gui.downloader.download_treestore.set_value(self.treeiter, 9, '')
        self.print_info('')
        self.gui.throbber.hide()

    
    def decrease_down_count(self):
        if self.gui.active_downloads > 0:
            self.gui.active_downloads -= 1
            gobject.idle_add(self.gui.downloader.active_down_label.set_text,str(self.gui.active_downloads))
            
    def increase_down_count(self):
        self.gui.active_downloads += 1
        gobject.idle_add(self.gui.downloader.active_down_label.set_text,str(self.gui.active_downloads))
        
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)
        
    

