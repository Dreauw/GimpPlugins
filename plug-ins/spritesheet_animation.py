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
    AnimationPreview
    A widget that can play an animation from a spritesheet
"""
class AnimationPreview(gtk.DrawingArea):
    """
        Constructor
        img : The image of the spritesheet of the animation
        frames_per_row : Number of frames par row on the spritesheet
        frames_per_col : Number of frames per column on the spritesheet
    """
    def __init__(self, img, frames_per_row=4, frames_per_col=1):
        self.img = img
        self.set_number_frame(frames_per_row, frames_per_col)
        self.animationSequence = []

        for i in range(self.framesPerRow * self.framesPerCol):
            self.animationSequence.append(i)

        self.frameId = 0;
        self.started = True
        self.delay = int(1.0 / (50.0 / 10000.0))

        r =  gtk.DrawingArea.__init__(self)

        self.connect("expose-event", self.on_expose)

        self.timeout_id = gobject.timeout_add(self.delay, self.update, self)
        return r

    """
        Set the number of frames per row/column
        frames_per_row : Number of frames par row on the spritesheet
        frames_per_col : Number of frames per column on the spritesheet
    """
    def set_number_frame(self, frames_per_row, frames_per_col):
        self.framesPerRow = frames_per_row;
        self.framesPerCol = frames_per_col;
        exist, x1, y1, x2, y2 = pdb.gimp_selection_bounds(self.img)
        cwidth = self.img.width
        cheight = self.img.height
        self.sx = 0
        self.sy = 0
        if exist:
            cwidth = min(cwidth, x2 - x1)
            cheight = min(cheight, y2 - y1)
            self.sx = max(0, x1)
            self.sy = max(0, y1)

        self.frameWidth = cwidth / self.framesPerRow
        self.frameHeight = cheight / self.framesPerCol


    """
        Draw a part of layer and scale that part to fit perfectly in
        the DrawingArea (keep the aspect ratio)

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
        Called when the DrawingArea of the animation need to be re-drawn
        da : DrawingArea
        event : The event
    """
    def on_expose(self, da, event, *args):
        # Catch error because this method is called from gtk
        try:
            # Calculate the position of the frame to draw in the layer
            x = self.sx + self.frameWidth * (self.animationSequence[self.frameId] % self.framesPerRow)
            y = self.sy + self.frameHeight * int(math.floor((self.animationSequence[self.frameId] + 0.0) / self.framesPerRow))
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
                self.frameId = (self.frameId + 1) % len(self.animationSequence)
                # Ask to redraw
                self.queue_draw()

            # Call this function again later
            self.timeout_id = gobject.timeout_add(self.delay, self.update, self)

        except:
            pdb.gimp_message("Error : " + traceback.format_exc())




"""
    AnimationWindow
    A window playing a spritesheet animation
"""
class AnimationWindow(gtk.Window):
    """
        Constructor
        img : Image with the spritesheet
        anim_preview : Widget that play the animation
    """
    def __init__ (self, img, anim_preview=None, *args):
        self.img = img

        # Box to position the widgets
        self.vbox = gtk.VBox(False, 0)
        self.hbox = gtk.HBox(False, 5)

        # Drawing area of the animation
        self.preview = AnimationPreview(self.img)
        if anim_preview != None:
            self.preview.sx = anim_preview.sx
            self.preview.sy = anim_preview.sy

            self.preview.frameWidth = anim_preview.frameWidth
            self.preview.frameHeight = anim_preview.frameHeight

            self.preview.framesPerRow = anim_preview.framesPerRow
            self.preview.framesPerCol = anim_preview.framesPerCol

            self.preview.animationSequence = anim_preview.animationSequence

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


        self.delay_adjustement.connect("value_changed", self.on_delay_changed)

        self.connect("destroy", gtk.main_quit)
        self.control_btn.connect("clicked", self.on_control_click)

        self.set_title("Spritesheet animation")
        self.resize(150, 200)
        self.show()
        self.set_keep_above(True)

        return r

    """
        Called when the speed is modified
        adjustement : The adjustement of the modified spinner
    """
    def on_delay_changed(self, adjustement):
        self.preview.delay = int(1.0 / (adjustement.get_value() / 10000.0))

        # Needed to apply the modification immediately
        if self.preview.started:
            # Remove the active timeout
            gobject.source_remove(self.preview.timeout_id)
            # Start a new timeout with the new delay
            self.preview.timeout_id = gobject.timeout_add(self.preview.delay, self.preview.update, self)


    """
        Called when the control button is clicked
        btn : The button clicked
    """
    def on_control_click(self, btn):
        self.preview.started = not self.preview.started
        btn.set_label("Stop" if self.preview.started else "Start")


"""
    ConfigurationWindow
    A window to configure the spritesheet animation
"""
class ConfigurationWindow(gtk.Window):
    """
        Constructor
        img : Image with the spritesheet
    """
    def __init__ (self, img, *args):
        self.img = img

        # Box to position the widgets
        self.vbox = gtk.VBox(False, 10)
        self.hbox = gtk.HBox(False, 0)

        # Drawing area of the animation
        self.preview = AnimationPreview(self.img)

        # Buttons
        self.ok_btn = gtk.Button("OK")
        self.cancel_btn = gtk.Button("Cancel")
        self.ok_btn.set_size_request(100, 25)
        self.cancel_btn.set_size_request(100, 25)
        r =  gtk.Window.__init__(self, *args)
        self.preview.show()
        self.vbox.pack_start(self.preview)

        # Spinners
        self.frames_per_row_adjustement = gtk.Adjustment(4, 1, 200, 1, 1)
        self.frames_per_row_spinner = gtk.SpinButton(self.frames_per_row_adjustement)
        self.frames_per_row_spinner.set_value(4)

        self.frames_per_col_adjustement = gtk.Adjustment(1, 1, 200, 1, 1)
        self.frames_per_col_spinner = gtk.SpinButton(self.frames_per_col_adjustement)
        self.frames_per_col_spinner.set_value(1)

        # TextField for animation sequence
        self.sequence_entry = gtk.Entry()
        self.sequence_entry.set_text(" ".join(map(str, self.preview.animationSequence)))

        self.cancel_btn.show()
        self.ok_btn.show()
        self.hbox.pack_end(self.cancel_btn, True, False)
        self.hbox.pack_start(self.ok_btn, True, False)
        self.hbox.show()

        self.vbox.pack_end(self.hbox, False, False, 10)


        self.add_widget_line(self.vbox, "Animation sequence", self.sequence_entry)
        self.add_widget_line(self.vbox, "Number of frames per column", self.frames_per_col_spinner)
        self.add_widget_line(self.vbox, "Number of frames per row", self.frames_per_row_spinner)

        self.vbox.show()
        self.add(self.vbox)


        self.sequence_edited = False

        self.frames_per_row_adjustement.connect("value_changed", self.on_config_changed)
        self.frames_per_col_adjustement.connect("value_changed", self.on_config_changed)
        self.sequence_entry.connect("changed", self.on_sequence_changed)

        self.connect("destroy", gtk.main_quit)
        self.ok_btn.connect("clicked", self.on_ok_clicked)
        self.cancel_btn.connect("clicked", gtk.main_quit)

        self.set_title("Spritesheet animation")
        self.resize(150, 250)
        self.show()
        self.set_keep_above(True)

        return r

    def on_sequence_changed(self, entry):
        self.sequence_edited = True
        seq_str = entry.get_text()
        self.preview.animationSequence = map(int, seq_str.split(" "))
        # TODO : Check syntax and number range

    """
        Called when the OK button is clicked
        btn : The button clicked
    """
    def on_ok_clicked(self, btn):
        self.destroy()
        try:
            r = AnimationWindow(self.img, self.preview)
        except:
            pdb.gimp_message("Error : " + traceback.format_exc())
        gtk.main()

    """
        Called when the configuration has changed
        widget : The widget that has ben modified
    """
    def on_config_changed(self, widget):
        try:
            nb_row = self.frames_per_row_spinner.get_value_as_int()
            nb_col = self.frames_per_col_spinner.get_value_as_int()
            self.preview.set_number_frame(nb_row, nb_col)
            # Automatically generate the animation sequence
            if (not self.sequence_edited):
                seq_str = ""
                sequence = []
                for i in range(nb_row * nb_col):
                    seq_str += str(i) + " "
                    sequence.append(i)

                self.sequence_entry.set_text(seq_str)
                self.sequence_edited = False
                self.preview.animationSequence = sequence
        except:
            pdb.gimp_message("Error : " + traceback.format_exc())


    """
        Add a widget with a label

        vbox : The VBox of the window
        text : The label associated with the widget
        widget : The widget to add
    """
    def add_widget_line(self, vbox, text, widget):
        hbox = gtk.HBox(self, 5)
        label = gtk.Label(text)

        label.show()
        hbox.pack_start(label, padding=10)

        widget.show()
        hbox.pack_end(widget, padding=10)

        hbox.show()
        vbox.pack_end(hbox, False, False)



"""
    Start the plugin
    img : The image of the spritesheet of the animation
"""
def spritesheet_animation(img):
    try:
        r = ConfigurationWindow(img)
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
        (PF_IMAGE, "image",       "Input image", None)
    ],
    [],
    spritesheet_animation,
    menu="<Image>/Filters/Animation"
    )

main()
