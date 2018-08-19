import os
import gi
from random import randint

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel
import cairo
from net.traceroute import TraceRouteNode, TraceRoute

class MainWindow:
    def __init__(self):
        self.new_node = None
        # User Interface elements

        self.icon_computer = cairo.ImageSurface.create_from_png("computer.png")
        self.icon_router = cairo.ImageSurface.create_from_png("router.png")
        self.icon_computer.set_device_scale(1.5, 1.5)
        self.icon_router.set_device_scale(1.5, 1.5)

        if self.icon_computer == None or self.icon_router == None:
            print("Failed to load icons.")

        self.connect_builder_objects()
        self.route_visualizer = RouteVisualizerView()

        self.visualizer_box.add(self.route_visualizer)

        self.window.show_all()

        self.route_model = RouteVisualizerModel()
        self.route_visualizer.set_model(self.route_model)
        self.route_visualizer.set_hexpand(True)
        self.route_visualizer.set_vexpand(True)

        self.trace_route = TraceRoute("cat")

        self.update_route_model_from_traceroute()
        self.route_model.new_node_position = [75, 250]


    def update_route_model_from_traceroute(self):
        previous_node = None
        for tnode in self.trace_route.nodes:
            if tnode.ttl == 0 or tnode.ip == self.trace_route.target:
                pixbuf = self.icon_computer
            else:
                pixbuf = self.icon_router

            last_node = self.route_model.add_node(tnode.ip)
            last_node.pixbuf = pixbuf

            # last_node.presented = True

            if previous_node:
                self.route_model.add_link(previous_node, last_node)

            previous_node = last_node


    def connect_builder_objects(self):
        builder = Gtk.Builder()
        builder.add_from_file("gui/main.glade")

        self.window = builder.get_object("main_window")
        self.visualizer_box = builder.get_object("visualizer_box")

        self.window.connect("delete-event", Gtk.main_quit)
        self.add_note_button = builder.get_object("add_node")
        self.add_note_button.connect("clicked", self.add_node)

    def add_node(self, event):
        self.trace_route.run_traceroute()
        self.new_node = self.route_model.add_node("2334", {'hostname':'catcat', 'pixbuf': self.icon_computer})
        self.route_visualizer.queue_draw()
