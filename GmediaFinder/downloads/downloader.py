#-*- coding: UTF-8 -*-
#
# gmediafinder's downloader gui package
import gtk
import gobject
import pango

#custom lib
try:
    from config import *
    from functions import *
except:
    from GmediaFinder.config import *
    from GmediaFinder.functions import *
        
class Downloader(object):
    def __init__(self,mainGui):
        self.mainGui = mainGui
        self.gladeGui = gtk.glade.XML(glade_file, None ,APP_NAME)
        
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
        self.path_btn.set_current_folder(down_dir)
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
        dic = {"on_down_menu_btn_clicked" : self.show_downloads,
               "on_backtohome_btn_clicked" : self.show_home,
               "on_select_path_btn_file_set" : self.update_down_path,
        }
        self.gladeGui.signal_autoconnect(dic)
        
        
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
        self.notebook.set_current_page(0)
        
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
