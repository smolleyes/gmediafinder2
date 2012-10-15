#-*- coding: UTF-8 -*-
import os
import gtk
import time
import re
import urllib2
import urllib
import threading
import time
import gobject
import tempfile
import pango

import sys
from time import sleep
from threading import Thread
from urllib import urlretrieve

import HTMLParser
import htmlentitydefs
import htmllib
from subprocess import Popen,PIPE

try:
    from lib.functions import *
    from lib.config import data_path
    from lib.config import _
except:
    from GmediaFinder.lib.functions import *
    from GmediaFinder.lib.config import data_path
    from GmediaFinder.lib.config import _

HTMLParser.attrfind = re.compile(r'\s*([a-zA-Z_][-.:a-zA-Z_0-9]*)(\s*=\s*'r'(\'[^\']*\'|"[^"]*"|[^\s>^\[\]{}\|\'\"]*))?')

def get_url_data(url):
    user_agent = 'Mozilla/5.0 (X11; U; Linux i686; en-US) AppleWebKit/534.15 (KHTML, like Gecko) Ubuntu/10.10 Chromium/10.0.608.0 Chrome/10.0.608.0 Safari/534.15'
    headers =  { 'User-Agent' : user_agent , 'Accept-Language' : 'fr-FR,fr;q=0.8,en-US;q=0.6,en;q=0.4' }
    ## start the request
    try:
        req = urllib2.Request(url,None,headers)
    except:
        return
    try:
        data = urllib2.urlopen(req)
    except:
        return
    return data
        
def download_photo(img_url):
    try:
        filename = os.path.basename(img_url)
        if sys.platform == "win32":
            file_path = os.path.join(tempfile.gettempdir(), filename)
        else:
            file_path = "/tmp/%s" % filename
        if os.path.exists(file_path) and not os.path.isdir(file_path):
            os.remove(file_path)
        p = urllib.urlretrieve(img_url, file_path)
        vid_pic = gtk.gdk.pixbuf_new_from_file(p[0])
        return vid_pic
    except:
        return None


def with_lock(func, args):
		gtk.gdk.threads_enter()
		try:
			return func(*args)
		finally:
			gtk.gdk.threads_leave()

def calc_eta(start, now, total, current):
		if total is None:
			return '--:--'
		dif = now - start
		if current == 0 or dif < 0.001: # One millisecond
			return '--:--'
		rate = float(current) / dif
		eta = long((float(total) - float(current)) / rate)
		(eta_mins, eta_secs) = divmod(eta, 60)
		if eta_mins > 99:
			return '--:--'
		values = {'min': eta_mins, 'sec': eta_secs}
		return _('%(min)02d:%(sec)02d') % values

import htmlentitydefs

def translate_html(text_html):
    code = htmlentitydefs.codepoint2name
    new_text = ""
    dict_code = dict([(unichr(key),value) for key,value in code.items()])
    for key in text_html:
#        key = unicode(key)
        if dict_code.has_key(key):
            new_text += "&%s;" % dict_code[key]
        else:
            new_text += key
    return new_text



def htmlentitydecode(s):
    # First convert alpha entities (such as &eacute;)
    # (Inspired from [url]http://mail.python.org/pipermail/python-list/2007-June/443813.html[/url])
    def entity2char(m):
        entity = m.group(1)
        if entity in htmlentitydefs.name2codepoint:
            return unichr(htmlentitydefs.name2codepoint[entity])
        return u" "  # Unknown entity: We replace with a space.
    expression = u'&(%s);' % u'|'.join(htmlentitydefs.name2codepoint)
    t = re.sub(expression, entity2char, s)


    # Then convert numerical entities (such as &#38;#233;)
    t = re.sub(u'&#38;#(d+);', lambda x: unichr(int(x.group(1))), t)

    # Then convert hexa entities (such as &#38;#x00E9;)
    return re.sub(u'&#38;#x(w+);', lambda x: unichr(int(x.group(1),16)), t)
		
def yesno(title,msg):
    dialog = gtk.MessageDialog(parent = None,
    buttons = gtk.BUTTONS_YES_NO,
    flags =gtk.DIALOG_DESTROY_WITH_PARENT,
    type = gtk.MESSAGE_QUESTION,
    message_format = msg
    )
    dialog.set_position("center")
    dialog.set_title(title)
    result = dialog.run()
    dialog.destroy()

    if result == gtk.RESPONSE_YES:
        return "Yes"
    elif result == gtk.RESPONSE_NO:
        return "No"
        
def error_dialog(message, parent = None):
    """
    Displays an error message.
    """

    dialog = gtk.MessageDialog(parent = parent, type = gtk.MESSAGE_ERROR, buttons = gtk.BUTTONS_OK, flags = gtk.DIALOG_MODAL)
    dialog.set_markup(message)
    dialog.set_position('center')

    result = dialog.run()
    gobject.idle_add(dialog.destroy)

def sortDict(d):
    """ Returns the keys of dictionary d sorted by their values """
    items=d.items()
    backitems=[ [v[1],v[0]] for v in items]
    backitems.sort()
    return [ backitems[i][1] for i in range(0,len(backitems))]

def create_comboBox(gui=None,dic=None,combo=None,createLabel=True):
    model = gtk.ListStore(str,gtk.gdk.Color)
    combobox = gtk.ComboBox(model)
    cell = gtk.CellRendererText()
    combobox.pack_start(cell, True)
    combobox.add_attribute(cell, 'text', 0)
    combobox.add_attribute(cell, 'foreground-gdk', 1)
    cb=None
    
    if dic:
        target = gui.search_opt_box
        for key,values in dic.items():
            if createLabel:
                label = gtk.Label(key)
                target.pack_start(label,False,False,5)
            cb = ComboBox(combobox)
            dr = sorted(values.keys())
            for val in dr:
                cb.append(val)
            target.add(combobox)
            cb.select(0)
            gobject.idle_add(target.show_all)
        if combo:
            return cb, combobox
        else:
            return cb
    return combobox


class ComboBox(object):
    def __init__(self,combobox):
        self.combobox = combobox
        self.model = self.combobox.get_model()

    def append(self,what,warn=False):
        if warn:
            color = gtk.gdk.color_parse("red")
            self.model.append([what, color])
        else:
            self.combobox.append_text(what)

    def remove(self,what):
        gobject.idle_add(self.combobox.remove_text,what)

    def select(self,which):
        gobject.idle_add(self.combobox.set_active,which)

    def getSelectedIndex(self):
        return self.combobox.get_active()

    def getSelected(self):
        return self.model[self.getSelectedIndex()][0]

    def setIndexFromString(self,usr_search):
        found = 0
        for item in self.model:
            iter = item.iter
            path = item.path
            name = self.model.get_value(iter, 0)
            if name == usr_search:
                found = 1
                gobject.idle_add(self.select,path[0])
                break
            gobject.idle_add(self.combobox.set_active,-1)
            
    def get_list(self):
        l = {}
        for item in self.model:
            iter = item.iter
            path = item.path
            name = self.model.get_value(iter, 0)
            if not name == "":
                l[name] = ''
        return l
        

def decode_htmlentities(text):
    p = htmllib.HTMLParser(None)
    p.save_bgn()
    p.feed(text)
    try:
        text = p.save_end().decode('utf-8')
    except:
        return
    text = re.sub('&#_;','\'',text)
    text = re.sub('&# ;','\'',text)
    text = re.sub('&amp;','&',text)
    text = re.sub('_',' ',text)
    return text


# self._hook est appelé à chaque requete urllib
class Abort(Exception):
    pass

class urlFetch(Thread):
    def __init__(self, engine, url, query, page, local=tempfile.NamedTemporaryFile().name):
        #print engine, url, query, page, local
        Thread.__init__(self)
        self.url = url
        self.stop = False
        self.local = local
        self.engine = engine
        self.query = query
        self.page = page

    def _hook(self, *args):
        if self.stop:
            raise Abort
        #sys.stdout.write('search request stopped: %s,%s' % (self.engine,self.query))
        sys.stdout.flush()

    def run(self):
        if not isinstance(self.url, str):
            try:
                self.engine.filter(self.url,self.query)
            except:
                self.stop = True
                self.abort()
        else:
            print "instance"
            try:
                r= get_url_data(self.url)
                #t = urlretrieve(self.url, self.local, self._hook)
                #f = open(self.local)
                self.engine.filter(r,self.query)
            except Abort, KeyBoardInterrupt:
                e = sys.exc_info()[1]
                if e != "":
                    print "<p>Error: %s</p>" % e
                print 'Aborted'
            except:
                try:
                    t = get_url_data(self.url)
                    self.engine.filter(t, self.query)
                except:
                    self.stop = True
                    raise


    def abort(self):
        self.stop = True


def get_redirect_link(link):
    request = urllib2.Request(link)
    opener = urllib2.build_opener()
    f = opener.open(request)
    return f.url

def warn_dialog(dialog):
    result = dialog.run()
    dialog.hide()
    return result
    
