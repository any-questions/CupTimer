#!/usr/bin/env python3
import cairo
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, Gdk, GLib

class MyApp (Gtk.Window):
    def __init__(self):
        super(MyApp,self).__init__()
        
        self.set_title("Puff")
        #self.resize(350,200)
        self.fullscreen()
        
        self.connect("destroy",Gtk.main_quit)
        
        self.drawArea = Gtk.DrawingArea()
        self.drawArea.connect("draw", self.expose)
        self.add(self.drawArea)
                width = self.get_size()[0]
        height = self.get_size()[1]
        self.timer = True
        self.alpha = 1.0
        self.size = 50
        
        GLib.timeout_add(10, self.on_timer)
        
        self.show_all()
    
    def on_timer(self):
        if not self.timer: return False
        
        self.drawArea.queue_draw()
        return True
    
    def expose(self,widget,cr):
        
        width = self.get_size()[0]
        height = self.get_size()[1]
         
        cr.set_source_rgb(1,1,1)
        cr.paint()
        
        cr.select_font_face("Ds-Digital", cairo.FONT_SLANT_NORMAL, cairo.FONT_WEIGHT_BOLD)
        
#        self.size += 2
        
#        if self.size > 40:
#            self.alpha -= 0.01
            
        cr.set_font_size(self.size)
        cr.set_source_rgb(0,0,0)
        
        (x,y,textWidth,textHeight,dx,dy) = cr.text_extents("5")
        
        cr.move_to(width/3 - textWidth/2, height/3)
        cr.text_path("5")
        cr.clip()
        cr.stroke()
        cr.paint_with_alpha(self.alpha)
        
        if self.alpha <= 0:
            self.timer = False
            
MyApp()
Gtk.main()
