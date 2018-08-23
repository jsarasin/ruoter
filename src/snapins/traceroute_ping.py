import os
import gi
from random import randint

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel
import cairo
from net.traceroute import Traceroute

from snapins.new_traceroute_ping import NewTraceroutePing

import sys
from net.data import *



class TraceroutePingSnapIn:
    def __init__(self, configuration):
        self.main_box = None
        self.visualizer_box = None
        self.visualizer = None
        self.notebook_label = None
        self.route_model = None
        self.trace_route = None
        self.input_target_host = None
        self.configuration = configuration

        self.initialize_control()

        self.highest_ttl_to_target = 0

        self.traceroutes = []
        for target in configuration['target']:
            trace_route = Traceroute()
            trace_route.start(target)
            self.traceroutes.append(trace_route)

        # self.update_route_model_from_traceroute()

        self.initialize_control()
        GObject.timeout_add(2.0, self.check_traceroutes)

    def check_traceroutes(self):
        sys.stdout.flush()
        for traceroute in self.traceroutes:
            messages = traceroute.check()

            for message in messages:
                if type(message) == TracerouteHop:
                    # Set the last thingy
                    # if message.ack > self.highest_ttl_to_target and message.address == self.target and message.ttl < 12:
                    #     self.highest_ttl_to_target = message.ack
                    print("Adding node: ", message.address)
                    self.route_model.add_node(message.address)

        GObject.timeout_add(1.0, self.check_traceroutes)

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


    def initialize_control(self):
        builder = Gtk.Builder()
        builder.add_from_file("snapins/traceroute_ping.glade")

        self.main_box = builder.get_object("traceroute_ping")
        self.visualizer_box = builder.get_object("visualizer_box")
        self.input_target_host = builder.get_object("input_target_host")

        self.input_target_host.set_text('n'.join(self.configuration['target']))

        self.route_model = RouteVisualizerModel()
        self.route_model.new_node_position = [0, 0]

        self.visualizer = RouteVisualizerView()
        self.visualizer.set_model(self.route_model)
        self.visualizer.set_hexpand(True)
        self.visualizer.set_vexpand(True)
        self.visualizer_box.add(self.visualizer)
        self.visualizer.show()


    @staticmethod
    def new_dialog(transient_parent):
        new_traceroute_ping_dialog = NewTraceroutePing(transient_parent)
        result = new_traceroute_ping_dialog.run()

        if result == -1:
            return None
        else:
            return new_traceroute_ping_dialog.configuration.copy()


