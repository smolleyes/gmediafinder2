#-*- coding: UTF-8 -*-
import urllib
import urllib2
import urlparse
import os
import sys
import re
import gobject
import time
import checklinks as checkLink

class Debrid(object):
    def __init__(self, gui):
        self.gui = gui
        self.rapid_serveurs   = { 'megaupload'   : '5adldc11',
                                  'rapidshare'   : '5adldc11',
                                  'megavideo'    : '5adldc11',
                                  'megaporn'     : '5adldc11',
                                  'megashares'   : '3dljy11', 
                                  'mediafire'    : '3dljy11',
                                  'depositfiles' : '3dljy11',
                                  'easy-share'   : '3dljy11', 
                                  'fileserve'    : '5adldc11', 
                                  'filesonic'    : '3dl098', 
                                  'filefactory'  : '5adldc11', 
                                  'freakshare'   : '3dljy11',
                     	          'hotfile'      : '5adldc11', 
                                  'turbobit'     : '5adldc11',
                                  'uploading'    : '5adldc11', 
                                  #'uploaded'     : '3dljy11', 
                                  'wupload'      : '5adldc11', 
                                  '4shared'      : '3dljy11',
				  'videobb'      : '3dl098',
                     		    }
        
           
    def return_uri_rapid(self, link):
    	if 'megashares' in link:
    		return '3dljy11'
    	else:
    		serveur = re.search('(http://www.|http://)(.*?)\..*',link).group(2)
    		print self.rapid_serveurs[serveur]
    		return self.rapid_serveurs[serveur]
    	   
    def debrid(self, link):
        print '____lancement________', link
        text = _("Add link in debrider:")
        text = '%s %s' % (text, link)
        self.print_info(text)
        url    = 'http://%s.rapid8.com/download/index.php' % self.return_uri_rapid(link)
        values = {'dlurl' : link,
                  'x' : '68',
                  'y' : '12' }
        data   = urllib.urlencode(values)
        req    = urllib2.Request(url, data)
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30')
        req.add_header('Origin','http://www.rapid8.com')
        req.add_header('Referer','http://www.rapid8.com/stage2.php')
        n=0
        while True:
            try:
                response = urllib2.urlopen(req, timeout=30)
            except urllib2.HTTPError, e:
                print e, n, "essai(s)", link
                if e.code == 503:
                    n+=1
                    if n == 3:
	    				print '3 essais, service down, link: ', link
	    				text = _("Error 503")
	    				self.print_info('%s, %s ...' % (text, link[0:30]) )
	    				try:
	    				    self.gui.search_engine.error_http(link)
	    				except:
	    				    pass
	    				return
                    time.sleep(2)
                    continue
                raise
            except urllib2.URLError, e:
                print e
                try:
                    self.gui.search_engine.error_http(link)
                except:
                    pass
                return
            except:
                raise
            else:
                resp     = response.info()
                resp_url = response.geturl()
                break

        if 'invalidurl' in resp_url or 'noaccount' in resp_url or 'faq.php' in resp_url:
            print 'invalide link', resp_url
            self.print_info(_("Invalide link or no account ..."))
            try:
                self.gui.search_engine.error_http(link)
            except: pass
	    self.print_info('')
            return
        try:
            filename = resp['Content-Disposition'].split('filename=')[1].replace('"','')
            self.filename, self.ext = os.path.splitext(filename)
            #print self.filename, self.ext.replace(';?=','')
        except:
            self.filename = os.path.basename(link)
            self.ext = 'unknow'
            pass
	self.print_info('')
        self.gui.download_file(self.gui, link, self.filename, self.ext.replace(';?=',''), response, 'files')
    
def debridMixture(self,vid):
    print "debridage du lien %s" % vid
    url    = 'http://enstreaming.com/mixture/telecharger.php'
    values = { 'link' : 'http://www.mixturecloud.com/media/download/%s' % vid }
    data   = urllib.urlencode(values)
    req    = urllib2.Request(url, data)
    req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux i686) AppleWebKit/534.30 (KHTML, like Gecko) Ubuntu/11.04 Chromium/12.0.742.112 Chrome/12.0.742.112 Safari/534.30')
    req.add_header('Origin','http://enstreaming.com/mixture/index.php')
    req.add_header('Referer','http://enstreaming.com/mixture/index.php')
    response = urllib2.urlopen(req, timeout=30)
    txt = response.readlines()
    print txt
    for line in txt:
	print line
	if 'id="download_unlimited"' in line:
	    link = urllib.unquote(re.search('href="(.*?)"',line).group(1))
	    print link
	    self.print_info('lien streaming %s, ouverture cours...' % link)
	    self.gui.start_play(link)
    
    def print_info(self,msg):
        gobject.idle_add(self.gui.info_label.set_text,msg)

