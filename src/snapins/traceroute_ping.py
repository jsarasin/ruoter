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
        super.__init__()
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

        if len(configuration['target']) > 1:
            print("Only the first target will be tracerouted!")

        self.initialize_target_tab()

        GObject.timeout_add(2.0, self.check_traceroutes)
        GObject.timeout_add(1.0, self.check_traceroutes)
        sys.stdout.flush()

    def start_traceroute(self, address, completion_callback):
        for ttl in range(1, 20):
            self.submit_task(SnapInTraceroutePing.worker_tcpsyn, ttl, SnapInTraceroutePing.worker_tcpsyn_complete_callback)

    def worker_tcpsyn_complete_callback(self, worker_data):
        pass

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
    def worker_tcpsyn(address, ttl):


        TIMEOUT = 3
        sent_time = time.time()
        ans, unans = sr(IP(dst=address, ttl=ttl, id=RandShort()) / TCP(flags=0x2, seq=RandInt(),sport=RandShort(), dport=2000+ttl), timeout=TIMEOUT, verbose=0)

        if ttl == 8:
            print("\n\n8 unanswered:\n", unans[0], "\n\n")
            sys.stdout.flush()

        recv_time = time.time()
        result = dict()

        # Explanation of result:
        # the scapy function sr = send receive, this is blocking until it receives a response.
        # The IP and TCP classes overload the / operator to encapsulate the right hand class in the left hand
        # ans: list containing all the responses, we only sent one packet
        # ans[0]: This is the entire response which is an Ethernet Frame & IP packet from local router containing
        #         a ICMP response (Time to live exceeded) from the router at hop <ttl> which itself contains the
        #         original request we sent out
        # ans[0][1].src: The source IP of the TTL exceeded message
        # ans[0][1][1].flags.S   Connected with target TCP Flag SYN is set
        # >>> type(ans[0][1][1])   # TTL Exceeded
        # <class 'scapy.layers.inet.ICMP'>
        # >>> type(anst[0][1][1])  # TCP SYN response to our ACK
        # <class 'scapy.layers.inet.TCP'>

        if len(ans) == 1:
            # We received a TTL exceeded
            if type(ans[0][1][1]) == scapy.layers.inet.ICMP:
                # Should be certain, but we'll check just to make sure
                if ans[0][1][1].type != 11:
                    print("Thought we received a ICMP TTL exceeded but we didn't!")
                    raise ValueError
                    return None
                result['responding_host'] = ans[0][1].src
                result['rtt'] = recv_time - sent_time
                result['ttl'] = ttl
                result['syn'] = False
                return result

            # The destination hosted responded with a SYN to our TCP packet
            if type(ans[0][1][1]) == scapy.layers.inet.TCP:
                # This should be certain, but we'll check just to make sure
                if not ans[0][1][1].flags.A:
                    print("thought we got a ACK but we didnt!")
                    raise ValueError
                    return None
                result['responding_host'] = ans[0][1].src
                result['rtt'] = recv_time - sent_time
                result['ttl'] = ttl
                result['syn'] = True
                return result

        if len(unans) == 1:
            return "TIMEOUT"

        print("Unhandled Traceroute response")
        raise ValueError
        return "FUCK"


    @staticmethod
    def new_dialog(transient_parent):
        # Popup the new Traceroute Ping dialog and get a decision from the user
        new_traceroute_ping_dialog = NewTraceroutePing(transient_parent)
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

