#!/usr/bin/env python

import os,sys
import gtk
import re
from configobj import ConfigObj

## custom lib
try:
    import config
    import gui
except:
    from GmediaFinder import config
    
class Engines(object):
    def __init__(self,gui):
        self.engines_list = []
        self.local_engines_list = []
        self.engines_path = config.engines_path
        self.gui = gui
        self.load_engines()
    
    def load_engines(self):
        # local engines
        self.local_engines_list = []
        if sys.platform == "win32" and 'zip' in config.exec_path:
            self.engines_path.append(config.data_path+'\lib\engines')
            sys.path.append(config.data_path+'\lib\engines')
        elif sys.platform == "win32" and not 'zip' in config.exec_path:
            self.engines_path.append(config.exec_path+'\lib\engines')
            sys.path.append(config.exec_path+'\lib\engines')
        for path in self.engines_path:
            for engine in os.listdir(path):
                if os.path.isdir(os.path.join(path, engine)):
                    self.local_engines_list.append(engine)
        # activated plugins list in the gmf config file
        self.load_plugins_conf()
        
    def init_engine(self,engine):
        modstr = "%s.%s" % (engine,engine)
        module = __import__(modstr, globals(), locals(), ['*'])
        init = getattr(module, '%s' % engine)
        setattr(self, '%s' % engine, init(self.gui))
        getattr(self, '%s' % engine).load_gui()
                    
    def load_plugins_conf(self):
        try:
            for eng in self.gui.conf["engines"]:
                self.engines_list.append(eng)
                ## clean locally removed plugins
                for eng in self.engines_list:
                    if (eng not in self.local_engines_list):
                        self.engines_list.remove(eng)
                self.gui.conf["engines"] = self.engines_list
                self.gui.conf.write()
        except:
            ## add new engines key in the config file if not present
            ## disable YouPorn by default
            for eng in self.local_engines_list:
                if ('Jamendo' in eng or 'Youtube' in eng or 'DailyMotion' in eng):
                    self.engines_list.append(eng)
            self.gui.conf["engines"] = self.engines_list
            self.gui.conf.write()
        
        # create checkbtn of enabled plugins in the gui
        for engine in self.local_engines_list:
            checkbox = gtk.CheckButton(engine)
            checkbox.set_alignment(0, 0.5)
            self.gui.engines_box.pack_start(checkbox,False,False,5)
            checkbox.connect('toggled', self.change_engine_state)
            if any(x in engine for x in self.engines_list):
                checkbox.set_active(True)
                self.init_engine(engine)
            self.gui.engines_box.show_all()
            
            
    def change_engine_state(self,widget):
        checked = widget.get_active()
        name = widget.child.get_text()
        if checked:
            if not any(x in name for x in self.engines_list):
                print "activating %s engine" % name
                self.engines_list.append(name)
                self.gui.conf["engines"] = self.engines_list
                self.gui.conf.write()
                self.init_engine(name)
                try:
                    if getattr(self, '%s' % name).adult_content:
                        self.gui.engine_selector.append(name,True)
                except:
                    self.gui.engine_selector.append(name)
                self.gui.engine_selector.setIndexFromString(name)
        else:
            if any(x in name for x in self.engines_list):
                print "deactivating %s engine" % name
                self.engines_list.remove(name)
                self.gui.conf["engines"] = self.engines_list
                self.gui.conf.write()
                self.gui.engine_selector.setIndexFromString(name)
                self.gui.engine_selector.remove(self.gui.engine_selector.getSelectedIndex())
                self.gui.engine_selector.select(0)
