import sys
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel
import concurrent.futures

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
        self.configuration['targets'] = ["216.58.193.67", "1.1.1.1", "microsoft.com", "asdf.com","telus.net"]
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=5)
        self.last_y = 100
        self.initialize_target_tab()

        self.highest_ttl_to_target = 0

        if len(configuration['targets']) > 1:
            print("Only the first target will be tracerouted!")

        self.initialize_target_tab()

        # GObject.timeout_add(2.0, self.check_traceroutes)
        self.hops = dict()
        self.start_traceroute(self.configuration['targets']) #
        sys.stdout.flush()

    def initialize_target_tab(self):
        # This will populate whatever Gtk Box is passed to this function with all the controls required for this snapin
        builder = Gtk.Builder()
        builder.add_from_file("snapins/traceroute_ping.glade")

        self.main_box = builder.get_object("traceroute_ping")
        self.visualizer_box = builder.get_object("visualizer_box")
        self.input_target_host = builder.get_object("input_target_host")

        self.input_target_host.set_text('n'.join(self.configuration['targets']))

        self.route_model = RouteVisualizerModel()
        self.route_model.new_node_position = [0, 0]

        self.visualizer = RouteVisualizerView()
        self.visualizer.set_model(self.route_model)
        self.visualizer.set_hexpand(True)
        self.visualizer.set_vexpand(True)
        self.visualizer_box.add(self.visualizer)
        self.visualizer.show()

    def get_target_y(self, target):
        for index, etarget in enumerate(self.configuration['targets']):
            if target == etarget:
                return (index * 200) + 100
        return 500
        # if 'y' not in self.targets[host]:
        #     self.last_y += 200
        #     self.hops[host]['y'] = self.last_y
        # return self.hops[host]['y']

    def start_traceroute(self, addresses):
        for ttl in range(1,20):
            for address in addresses:
                future = self.executor.submit(SnapInTraceroutePing.worker_tcpsyn, address, ttl)
                future.add_done_callback(self.worker_tcpsyn_complete_callback)


    def worker_tcpsyn_complete_callback(self, future):
        worker_data = future.result()

        if worker_data['unanswered'] == True:
            host = "* -> " + worker_data['target']
        else:
            host = worker_data['host']

        if host in self.hops:
            print("hop has a second target: ", self.hops[host]['targets'], "adding:", worker_data['target'])
            if worker_data['target'] not in self.hops[host]['targets']:
                self.hops[host]['targets'].append(worker_data['target'])
                self.hops[host]['node']['targets'] = self.hops[host]['targets']

        else:
            self.add_hop(worker_data)

        print("\n"* 2)
        sys.stdout.flush()


    def add_hop(self, worker_data):
        if worker_data['unanswered'] == True:
            host = "* -> " + worker_data['target']
        else:
            host = worker_data['host']

        if 'ttl' in worker_data:
            ttl = worker_data['ttl']
        else:
            ttl = 1

        if 'rtt' in worker_data:
            rtt = str(round(worker_data['rtt'] * 1000)) + "ms"
            worker_data['rtt'] = rtt
        else:
            rtt = None

        target = worker_data['target']

        self.hops[host] = dict()

        new_node = self.route_model.add_node(host)
        new_node.attributes.update(worker_data)
        new_node.posx = ((ttl) * 200) - 100
        new_node.posy = self.get_target_y(target)
        new_node.pixbuf = None
        new_node.presented = True

        self.hops[host]['raw'] = worker_data
        self.hops[host]['ttl'] = ttl
        self.hops[host]['rtt'] = rtt
        self.hops[host]['node'] = new_node
        self.hops[host]['targets'] = [target]

        self.build_links(host, target, ttl, new_node)

    def build_links(self, host, target, ttl, new_node):
        last_hop = None
        for key in self.hops:
            if target in self.hops[key]['targets'] and (self.hops[key]['ttl'] == ttl - 1 or self.hops[key]['ttl'] == ttl + 1):
                self.hops[host]['previous'] = self.hops[key]
                self.hops[host]['previous_node'] = self.hops[key]['node']
                self.route_model.add_link(self.hops[key]['node'], new_node)



    @staticmethod
    def worker_tcpsyn(target, cttl):
        result = dict()
        sent_time = time.time()
        cork = 33434 + (cttl)

        filter = ""
        ddata = b"\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f"
        answered, unanswered_sent = sr(IP(dst=target, ttl=(cttl), id=RandShort()) / UDP(dport=cork) / Raw(ddata), verbose=False, timeout=10, filter=filter )

        recv_time = time.time()
        rtt = recv_time - sent_time

        result['target'] = target

        if len(unanswered_sent):
            result['ttl'] = unanswered_sent[0].ttl
            result['unanswered'] = True
            return result

        answered_sent = answered[0][0]
        answered_received = answered[0][1]

        result['unanswered'] = False

        if type(answered_received[1]) == scapy.layers.inet.ICMP:
            result['response'] = "icmp/" + icmptypes[answered_received[1].type]
            # ICMP TTL Exceeded
            if answered_received[1].type == 11:
                result['ttl'] = answered_sent.ttl
                result['host'] = answered_received[0].src
                result['rtt'] = rtt
                return result
            elif answered_received[1].type == 3:
                assert(answered_received[1].code == 3)
                result['ttl'] = answered_sent.ttl
                result['host'] = answered_received[0].src
                result['rtt'] = rtt
                result['response'] = result['response'] + "/" + icmpcodes[answered_received[1].type][answered_received[1].code]
                return result
            else:
                print("Unhandled ICMP response type:", answered_received[1].type)
                return answered_received[1].summary()

        if type(answered_received[1]) == scapy.layers.inet.TCP:
            return answered_received.show()



        return None



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

        self.configuration['targets'] = [self.input_host.get_text()]

        self.configuration['tr_freq'] = self.input_traceroute_freq.get_text()

        self.configuration['ping_freq'] = self.input_ping_freq.get_text()

        self.configuration['traceroute_type'] = self.combo_traceroute_type.get_active_text()

        self.configuration['traceroute_port'] = self.entry_traceroute_target_port.get_text()

        self.configuration['ping_type'] = self.combo_ping_type.get_active_text()

        self.window.response(1)
        self.window.close()

