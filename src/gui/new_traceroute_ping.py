import os
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo

import cairo
from net.traceroute import TraceRouteNode, TraceRoute


class NewTraceroutePing:
    def __init__(self, transient_for):
        self.connect_builder_objects()
        self.configuration = dict()


        self.window.set_transient_for(transient_for)
        self.window.show_all()

    def connect_builder_objects(self):
        builder = Gtk.Builder()
        builder.add_from_file("gui/new_traceroute_ping.glade")

        self.window = builder.get_object("window_traceroute_ping")
        self.combo_interface = builder.get_object("combo_interface")
        self.input_host = builder.get_object("input_host")
        self.input_traceroute_freq = builder.get_object("input_traceroute_freq")
        self.input_ping_freq = builder.get_object("input_ping_freq")
        self.combo_traceroute_type = builder.get_object("combo_traceroute_type")
        self.combo_traceroute_target_port = builder.get_object("combo_traceroute_target_port")
        self.input_traceroute_target_port = builder.get_object("input_traceroute_target_port")
        self.combo_ping_type = builder.get_object("combo_ping_type")
        self.button_start = builder.get_object("button_start")
        self.button_cancel = builder.get_object("button_cancel")

        self.window.connect("delete-event", self.on_window_close)
        self.button_start.connect("clicked", self.start_ping)
        self.button_cancel .connect("clicked", self.close_cancel)

    def run(self):
        self.window.show_all();
        result = self.window.run()
        return result

    def start_ping(self, event):
        self.close_selected(1)

    def on_window_close(self, window, event):
        self.close_cancel(event)

    def close_cancel(self, event):
        self.window.response(-1)
        self.window.close()
        return False

    def close_selected(self, selected_id):
        self.configuration['target_host'] = self.input_host.get_text()

        self.window.response(1)
        self.window.close()

