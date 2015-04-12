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
        self.framesPerRow = 8;
        self.framesPerCol = 2;
        # TODO: Use the size of the selection
        # pdb.gimp_selection_bounds(self.img)

        self.frameWidth = self.img.width / self.framesPerRow
        self.frameHeight = self.img.height / self.framesPerCol
        self.animationSequence = []

        for i in range(self.framesPerRow * self.framesPerCol):
            self.animationSequence.append(i)

        # Drawing area of the animation
        self.preview = gtk.DrawingArea()
        r =  gtk.Window.__init__(self, *args)
        self.preview.show()
        self.add(self.preview)

        self.preview.connect("expose-event", self.on_expose)

        self.connect("destroy", gtk.main_quit)

        self.show()
        self.set_keep_above(True)

        gobject.timeout_add(200, self.update, self)
        return r


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
        gc = wnd.new_gc()
        preview_x = (da_width - preview_width) / 2
        preview_y = (da_height - preview_height) / 2

        # Select the drawing function depending on the number of bytes per pixel
        if bpp == 1:
            wnd.draw_gray_image(gc, preview_x, preview_y, preview_width, preview_height, gtk.gdk.RGB_DITHER_NONE, buf, preview_width * bpp)
        elif bpp == 3:
            wnd.draw_rgb_image(gc, preview_x, preview_y, preview_width, preview_height, gtk.gdk.RGB_DITHER_NONE, buf, preview_width * bpp)
        elif bpp == 4:
            wnd.draw_rgb_32_image(gc, preview_x, preview_y, preview_width, preview_height, gtk.gdk.RGB_DITHER_NONE, buf, preview_width * bpp)


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

            self.draw_part_of_layer(da, self.img.active_layer, x, y, self.frameWidth, self.frameHeight)
        except:
            pdb.gimp_message("Error : " + traceback.format_exc())

    """
        Called automatically to update the animation
    """
    def update(self, *args):
        # Catch error because this method is called from gtk
        try:
            # Increment the frameId
            self.frameId = (self.frameId + 1) % (self.framesPerRow * self.framesPerCol)
            # Ask to redraw
            self.preview.queue_draw()

            # Call this function again later
            gobject.timeout_add(200, self.update, self)

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
