import os
import gi
from random import randint

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel
import cairo
from net.traceroute import TraceRouteNode, TraceRoute

from gui.new_traceroute_ping import NewTraceroutePing


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

        # self.visualizer_box = builder.get_object("visualizer_box")
        # self.add_note_button = builder.get_object("add_node")
        # self.add_note_button.connect("clicked", self.add_node)

    def add_new_traceroute_ping_children(self, configuration):
        ntrp = TraceroutePingInterface()
        self.traceroute_ping_interfaces.append(ntrp)

        notebook_label = Gtk.Label("Catsoup")

        builder = Gtk.Builder()
        builder.add_from_file("gui/main.glade")

        ntrp.notebook_label = notebook_label
        ntrp.main_box = builder.get_object("traceroute_ping")
        ntrp.visualizer_box = builder.get_object("visualizer_box")
        ntrp.input_target_host = builder.get_object("input_target_host")

        ntrp.input_target_host.set_text(configuration['target_host'])

        ntrp.route_model = RouteVisualizerModel()
        ntrp.route_model.new_node_position = [75, 250]

        ntrp.visualizer = RouteVisualizerView()
        ntrp.visualizer.set_model(ntrp.route_model)
        ntrp.visualizer.set_hexpand(True)
        ntrp.visualizer.set_vexpand(True)
        ntrp.visualizer_box.add(ntrp.visualizer)
        ntrp.visualizer.show()



        ntrp.trace_route = TraceRoute(configuration['target_host'])
        ntrp.trace_route.run_test()
        ntrp.update_route_model_from_traceroute()

        new_page = self.notebook_tasks.append_page(ntrp.main_box, notebook_label)
        self.notebook_tasks.set_current_page(new_page)


    def new_traceroute_ping(self, event):
        new_traceroute_ping_dialog = NewTraceroutePing(self.window)
        result = new_traceroute_ping_dialog.run()

        if result == -1:
            return
        self.add_new_traceroute_ping_children(new_traceroute_ping_dialog.configuration)




class TraceroutePingInterface:
    def __init__(self):
        self.main_box = None
        self.visualizer_box = None
        self.visualizer = None
        self.notebook_label = None
        self.route_model = None
        self.trace_route = None
        self.input_target_host = None

    def update_route_model_from_traceroute(self):
        previous_node = None
        for tnode in self.trace_route.nodes:
            # if tnode.ttl == 0 or tnode.ip == self.trace_route.target:
            #     pixbuf = self.icon_computer
            # else:
            #     pixbuf = self.icon_router

            node = self.route_model.add_node(tnode.ip)
            node.pixbuf = None
            node.presented = True

            if previous_node is not None:
                self.route_model.add_link(previous_node, node)
            previous_node = node



