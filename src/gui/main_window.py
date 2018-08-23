import os
import gi
from random import randint

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel
import cairo

# from net.traceroute import TraceRouteNode, TraceRoute
from snapins.traceroute_ping import TraceroutePingSnapIn


class MainWindow:
    def __init__(self):
        self.traceroute_ping_interfaces = []
        self.new_node = None


        self.connect_builder_objects()

        # User Interface elements

        # self.icon_computer = cairo.ImageSurface.create_from_png("computer.png")
        # self.icon_router = cairo.ImageSurface.create_from_png("router.png")
        # self.icon_computer.set_device_scale(1.5, 1.5)
        # self.icon_router.set_device_scale(1.5, 1.5)
        #
        # if self.icon_computer == None or self.icon_router == None:
        #     print("Failed to load icons.")
        #
        # self.route_visualizer = RouteVisualizerView()
        #
        # self.visualizer_box.add(self.route_visualizer)
        #
        # self.window.show_all()
        #
        # self.route_model = RouteVisualizerModel()
        # self.route_visualizer.set_model(self.route_model)
        # self.route_visualizer.set_hexpand(True)
        # self.route_visualizer.set_vexpand(True)
        #
        # self.trace_route = TraceRoute("1.1.1.1")
        # self.trace_route.run_test()
        #
        # self.update_route_model_from_traceroute()
        # self.route_model.new_node_position = [75, 250]





    def connect_builder_objects(self):
        builder = Gtk.Builder()
        builder.add_from_file("gui/main.glade")

        self.window = builder.get_object("main_window")
        self.notebook_tasks = builder.get_object("notebook_tasks")
        self.button_welcome_new_traceroute_ping = builder.get_object("button_welcome_new_traceroute_ping")

        self.button_welcome_new_traceroute_ping.connect("clicked", self.new_traceroute_ping)


        self.window.connect("delete-event", Gtk.main_quit)

        self.window.show_all()

    def add_new_traceroute_ping_children(self, configuration):
        ntrp = TraceroutePingSnapIn(configuration)
        self.traceroute_ping_interfaces.append(ntrp)

        notebook_label = Gtk.Label(configuration['target'])
        new_page = self.notebook_tasks.append_page(ntrp.main_box, notebook_label)
        self.notebook_tasks.set_current_page(new_page)

    def new_traceroute_ping(self, event):
        config = TraceroutePingSnapIn.new_dialog(self.window)

        if config is not None:
            self.add_new_traceroute_ping_children(config)




