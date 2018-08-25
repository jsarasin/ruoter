import sys
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel


from snapins.snapin import Snapin

from scapy.all import *

import scapy.layers.inet


class SnapInTraceroutePing(Snapin):
    def __init__(self, configuration):
        Snapin.__init__(self)
        self.main_box = None
        self.visualizer_box = None
        self.visualizer = None
        self.notebook_label = None
        self.route_model = None
        self.trace_route = None
        self.input_target_host = None
        self.configuration = configuration

        self.initialize_target_tab()

        self.highest_ttl_to_target = 0

        if len(configuration['target']) > 1:
            print("Only the first target will be tracerouted!")

        self.initialize_target_tab()

        # GObject.timeout_add(2.0, self.check_traceroutes)
        self.start_traceroute("1.1.1.1")
        sys.stdout.flush()

    def start_traceroute(self, address):
        print("I am", self)
        sys.stdout.flush()
        for ttl in range(1, 20):
            self.submit_task(self.worker_tcpsyn_complete_callback, SnapInTraceroutePing.worker_tcpsyn, ('1.1.1.1', ttl,))

    def worker_tcpsyn_complete_callback(self, request_id, worker_data):
        # result['responding_host'] = rcv.src
        # result['rtt'] = recv_time - sent_time
        # result['ttl'] = snd.ttl
        # result['syn'] = False
        new_node = self.route_model.add_node(worker_data['responding_host'])
        ttl = worker_data['ttl']
        new_node.posx = ttl * 200
        new_node.pixbuf = None
        new_node.presented = True

        # self.input_target_host.set_text(worker_data['responding_host'])

        # print("NEW:", worker_data)
        sys.stdout.flush()


        # self.update_route_model_from_traceroute()


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

    def initialize_target_tab(self):
        # This will populate whatever Gtk Box is passed to this function with all the controls required for this snapin
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
    def worker_tcpsyn(target, cttl):
        result = dict()
        sent_time = time.time()
        ans, unans = sr(IP(dst=target, ttl=(cttl), id=RandShort()) / TCP(flags=0x2), timeout=1, verbose=False)
        recv_time = time.time()

        for snd, rcv in ans:
            result['responding_host'] = rcv.src
            result['rtt'] = recv_time - sent_time
            result['ttl'] = snd.ttl
            result['syn'] = False

        return result



    @staticmethod
    def new_dialog(transient_parent):
        # Popup the new Traceroute Ping dialog and get a decision from the user
        new_traceroute_ping_dialog = DialogNewTraceroutePing(transient_parent)
        result = new_traceroute_ping_dialog.run()

        if result == -1:
            return None
        else:
            return new_traceroute_ping_dialog.configuration.copy()



class DialogNewTraceroutePing:
    # Logic for the New Traceroute Ping Dialog
    def __init__(self, transient_for):
        self.connect_builder_objects()
        self.configuration = dict()


        self.window.set_transient_for(transient_for)
        self.window.show_all()

    def connect_builder_objects(self):
        builder = Gtk.Builder()
        builder.add_from_file("snapins/new_traceroute_ping.glade")

        self.window = builder.get_object("window_traceroute_ping")
        self.combo_interface = builder.get_object("combo_interface")
        self.input_host = builder.get_object("input_host")
        self.input_traceroute_freq = builder.get_object("input_traceroute_freq")
        self.input_ping_freq = builder.get_object("input_ping_freq")
        self.combo_traceroute_type = builder.get_object("combo_traceroute_type")
        self.entry_traceroute_target_port = builder.get_object("entry_traceroute_target_port")
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
        # Apparently text returned from the following function requires manual freeing of the string?
        self.configuration['iterface'] = self.combo_interface.get_active_text()

        self.configuration['target'] = [self.input_host.get_text()]

        self.configuration['tr_freq'] = self.input_traceroute_freq.get_text()

        self.configuration['ping_freq'] = self.input_ping_freq.get_text()

        self.configuration['traceroute_type'] = self.combo_traceroute_type.get_active_text()

        self.configuration['traceroute_port'] = self.entry_traceroute_target_port.get_text()

        self.configuration['ping_type'] = self.combo_ping_type.get_active_text()

        self.window.response(1)
        self.window.close()

