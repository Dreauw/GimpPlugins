#!/usr/bin/env python
"""
    SpriteSheet Animator

    A plugin to preview the animation of a spritesheet in Gimp
"""

from gimpfu import *
import time
import threading
import gtk
import traceback
import gobject
import math
import array
import cairo

"""
    AnimationWindow
    A window playing a spritesheet animation
"""
class AnimationWindow(gtk.Window):
    """
        Constructor
        img : Image with the spritesheet
    """
    def __init__ (self, img, *args):
        self.img = img
        #self.animationSequence = [0, 1, 2, 3, 2, 1]
        self.frameId = 0;
        self.framesPerRow = 9;
        self.framesPerCol = 4;
        # TODO: Use the size of the selection
        # pdb.gimp_selection_bounds(self.img)

        self.frameWidth = self.img.width / self.framesPerRow
        self.frameHeight = self.img.height / self.framesPerCol
        self.animationSequence = []
        self.started = True
        self.delay = int(1.0 / (50.0 / 10000.0))

        for i in range(self.framesPerRow * self.framesPerCol):
            self.animationSequence.append(i)

        # Box to position the widgets
        self.vbox = gtk.VBox(False, 0)
        self.hbox = gtk.HBox(False, 5)

        # Drawing area of the animation
        self.preview = gtk.DrawingArea()
        # Button to start/stop the animation
        self.control_btn = gtk.Button("Stop")
        # Spinner to control the speed of the animation
        self.delay_label = gtk.Label("   Speed")
        self.delay_adjustement = gtk.Adjustment(50, 1, 500, 1, 10)
        self.delay_spinner = gtk.SpinButton(self.delay_adjustement)
        self.delay_spinner.set_value(50)

        r =  gtk.Window.__init__(self, *args)
        self.preview.show()
        self.vbox.pack_start(self.preview)

        self.control_btn.show()
        self.hbox.pack_start(self.control_btn)

        self.delay_spinner.show()
        self.hbox.pack_end(self.delay_spinner)

        self.delay_label.show()
        self.hbox.pack_end(self.delay_label, False, False)

        self.hbox.show()
        self.vbox.pack_end(self.hbox, False, False)

        self.vbox.show()
        self.add(self.vbox)

        self.preview.connect("expose-event", self.on_expose)

        self.delay_adjustement.connect("value_changed", self.on_delay_changed)

        self.connect("destroy", gtk.main_quit)
        self.control_btn.connect("clicked", self.on_control_click)

        self.set_title("Spritesheet animation")
        self.resize(150, 200)
        self.show()
        self.set_keep_above(True)

        self.timeout_id = gobject.timeout_add(self.delay, self.update, self)
        return r

    """
        Draw a part of layer and scale that part to fit perfectly in
        the DrawingArea (keeping the aspect ratio)

        da : The DrawingArea to draw the layer on
        layer : The layer to draw
        x : Position x of the part of the layer to draw
        y : Position y of the part of the layer to draw
        width : The width of the part of the layer to draw
        height : The height of the part of the layer to draw
    """
    def draw_part_of_layer(self, da, layer, x, y, width, height):
        # Calculate a size that fit and keep the aspect ratio of the animation
        da_width = da.get_allocation().width
        da_height = da.get_allocation().height
        size = min(da_width, da_height)
        # Create a scaled drawable (and keep the aspect ratio)
        thumbnail = pdb.gimp_drawable_sub_thumbnail(layer, x, y, width, height, size, size)
        # Convert the byte array into string
        buf = array.array('B', thumbnail[4]).tostring()

        bpp = thumbnail[2]
        preview_width = thumbnail[0]
        preview_height = thumbnail[1]
        wnd = da.window
        preview_x = (da_width - preview_width) / 2
        preview_y = (da_height - preview_height) / 2

        # Select the drawing function depending on the number of bytes per pixel
        if bpp == 1:
            wnd.draw_gray_image(wnd.new_gc(), preview_x, preview_y, preview_width, preview_height, gtk.gdk.RGB_DITHER_NONE, buf, preview_width * bpp)
        elif bpp == 3:
            wnd.draw_rgb_image(wnd.new_gc(), preview_x, preview_y, preview_width, preview_height, gtk.gdk.RGB_DITHER_NONE, buf, preview_width * bpp)
        elif bpp == 4:
            # Use cairo because draw_rgb_32_image doesn't handle transparency
            pixbuf = gtk.gdk.pixbuf_new_from_data(buf, gtk.gdk.COLORSPACE_RGB, True, 8, preview_width, preview_height, preview_width * bpp)
            cr = wnd.cairo_create()
            cr.set_source_pixbuf(pixbuf, preview_x, preview_y)
            cr.paint()
            #wnd.draw_rgb_32_image(gc, preview_x, preview_y, preview_width, preview_height, gtk.gdk.RGB_DITHER_NONE, buf, preview_width * bpp)

    """
        Called when the speed is modified
        adjustement : The adjustement of the modified spinner
    """
    def on_delay_changed(self, adjustement):
        self.delay = int(1.0 / (adjustement.get_value() / 10000.0))

        # Needed to apply the modification immediately
        if self.started:
            # Remove the active timeout
            gobject.source_remove(self.timeout_id)
            # Start a new timeout with the new delay
            self.timeout_id = gobject.timeout_add(self.delay, self.update, self)


    """
        Called when the control button is clicked
        btn : The button clicked
    """
    def on_control_click(self, btn):
        self.started = not self.started
        btn.set_label("Stop" if self.started else "Start")

    """
        Called when the DrawingArea of the animation need to be re-drawn
        da : DrawingArea
        event : The event
    """
    def on_expose(self, da, event, *args):
        # Catch error because this method is called from gtk
        try:
            # Calculate the position of the frame to draw in the layer
            x = self.frameWidth * (self.animationSequence[self.frameId] % self.framesPerRow)
            y = self.frameHeight * int(math.floor((self.animationSequence[self.frameId] + 0.0) / self.framesPerRow))
            # Draw all the visible layer to make the animation
            for layer in reversed(self.img.layers):
                if layer.visible and layer.width >= x + self.frameWidth and layer.height >= y + self.frameHeight:
                    self.draw_part_of_layer(da, layer, x, y, self.frameWidth, self.frameHeight)
        except:
            pdb.gimp_message("Error : " + traceback.format_exc())

    """
        Called automatically to update the animation
    """
    def update(self, *args):
        # Catch error because this method is called from gtk
        try:
            if self.started:
                # Increment the frameId
                self.frameId = (self.frameId + 1) % (self.framesPerRow * self.framesPerCol)
                # Ask to redraw
                self.preview.queue_draw()

            # Call this function again later
            self.timeout_id = gobject.timeout_add(self.delay, self.update, self)

        except:
            pdb.gimp_message("Error : " + traceback.format_exc())

"""
    Start the plugin
    img : The image of the spritesheet of the animation
"""
def spritesheet_animation(img):
    try:
        r = AnimationWindow(img)
        gtk.main()
    except:
        # Open a popup and show the error
        pdb.gimp_message("Error : " + traceback.format_exc())
        message = gtk.MessageDialog(type=gtk.MESSAGE_ERROR)
        message.set_markup("Error : " + traceback.format_exc())
        message.connect("destroy", gtk.main_quit)
        message.show()
        gtk.main()


register(
    "python-fu-spritesheet-animation",
    "Preview the animation of a spritesheet",
    "Preview the animation of a spritsheet",
    "Dreauw",
    "Dreauw",
    "2015",
    "_Spritesheet...",
    "RGB*, GRAY*",
    [
        (PF_IMAGE, "image",       "Input image", None),
    ],
    [],
    spritesheet_animation,
    menu="<Image>/Filters/Animation"
    )

main()
