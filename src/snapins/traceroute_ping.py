import sys
import os
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo, Gio
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel
import concurrent.futures

from snapins.snapin import Snapin

from scapy.all import *

from get_root_path import get_root_path

import scapy.layers.inet


class ResponseType:
    TIMEOUT = 0
    ICMP_TTL_EXCEEDED = 1
    ICMP_PORT_UNREACH = 2

class RequestType:
    UDP_SYN = 0 # First traceroute discovery. There will be multiple of these sent out at the same time.
    TCP_SYN_SEQUENTIAL = 1     # Fallback, initialize connection to tcp/80
    ICMP_ECHO = 2   # Vanilla Echo


class MultiTraceroute:
    def __init__(self, targets):
        self.requests = {}


    def register_request(self, request_type, ip_id, target, ttl):
        if ip_id in self.requests:
            print("Registered a second request for the same ip.id")
            return

        self.requests[ip_id] = (request_type, target, ttl)

    def register_response(self, response):
        request = self.requests[response['request_id']]

        if response['type'] == ResponseType.TIMEOUT:
            assert(request[1] == response['target'])
            assert(request[2] == response['ttl'])

        if response['type'] == ResponseType.ICMP_PORT_UNREACH:
            assert(request[1] == response['target'])
            assert(request[2] == response['ttl'])

        if response['type'] == ResponseType.ICMP_TTL_EXCEEDED:
            assert(request[1] == response['target'])
            assert(request[2] == response['ttl'])

    # cat = getaddrinfo("microsoft.com", None, AddressFamily.AF_INET, SocketKind.SOCK_STREAM)



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
        self.executor = concurrent.futures.ThreadPoolExecutor(max_workers=15)
        self.last_y = 100
        self.initialize_target_tab()
        self.host_tracker = MultiTraceroute()

        self.highest_ttl_to_target = 0

        if len(configuration['targets']) > 1:
            print("Only the first target will be tracerouted!")

        self.initialize_target_tab()


        self.hops = dict()
        if self.configuration['start_immediately']:
            self.start_traceroute(self.configuration['targets']) #
        sys.stdout.flush()

    def initialize_target_tab(self):
        # This will populate whatever Gtk Box is passed to this function with all the controls required for this snapin
        builder = Gtk.Builder()
        builder.add_from_file(get_root_path() + "snapins/traceroute_ping.glade")

        self.main_box = builder.get_object("traceroute_ping")
        self.visualizer_box = builder.get_object("visualizer_box")
        self.button_targets = builder.get_object("button_targets")
        self.button_targets.connect("clicked", self.show_targets_popover)
        self.popover_targets = builder.get_object("popover_targets")

        self.revealer_detailed_info = builder.get_object("revealer_detailed_info")
        self.togglebutton_details = builder.get_object("togglebutton_details")
        self.togglebutton_details.connect("toggled", self.togglebutton_details_clicked)

        self.treeview_targets = builder.get_object("treeview_targets")
        self.treestore_targets = Gtk.TreeStore(str)
        cell_renderer = Gtk.CellRendererText()
        column_id = Gtk.TreeViewColumn("Hostname", cell_renderer, text=0)
        column_id.set_visible(True)
        self.treeview_targets.append_column(column_id)
        # Setup targets Popup treestore
        for address in self.configuration['targets']:
            self.treestore_targets.append(None, [address])
        self.treeview_targets.set_model(self.treestore_targets)

        self.route_model = RouteVisualizerModel()
        self.route_model.new_node_position = [0, 0]

        self.visualizer = RouteVisualizerView()
        self.visualizer.set_model(self.route_model)
        self.visualizer.set_hexpand(True)
        self.visualizer.set_vexpand(True)
        self.visualizer_box.add(self.visualizer)
        self.visualizer.show()

        self.entry_average_ping = builder.get_object("entry_average_ping")

    def togglebutton_details_clicked(self, button):
        self.revealer_detailed_info.set_reveal_child(self.togglebutton_details.get_active())


    def show_targets_popover(self, button):
        self.popover_targets.show()

    def get_target_y(self, target):
        for index, etarget in enumerate(self.configuration['targets']):
            if target == etarget:
                return (index * 200) + 100
        return 500

    def start_traceroute(self, addresses):
        custom_id = random.randint(1000, 20000)

        for ttl in range(1,20):
            custom_id = custom_id + 1
            for address in addresses:
                custom_id = custom_id + 1
                future = self.executor.submit(SnapInTraceroutePing.worker_tcpsyn, address, ttl, custom_id)
                future.add_done_callback(self.worker_tcpsyn_complete_callback)
                self.host_tracker.register_request(RequestType.UDP_SYN, custom_id, target, ttl)


    def worker_tcpsyn_complete_callback(self, future):
        response = future.result()

        self.host_tracker.register_response(response)


    def register_hop(self, worker_data):
        if worker_data['unanswered']:
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
        new_node.presented = False
        self.visualizer.generate_node_animation(new_node)

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
    def worker_tcpsyn(target, cttl, custom_id, include_raw=False):
        response = dict()
        sent_time = time.time()
        cork = 33434 + (cttl)

        myfilter = ""
        ddata = b"\x40\x41\x42\x43\x44\x45\x46\x47\x48\x49\x4a\x4b\x4c\x4d\x4e\x4f\x50\x51\x52\x53\x54\x55\x56\x57\x58\x59\x5a\x5b\x5c\x5d\x5e\x5f"
        answered, unanswered_sent = sr(IP(dst=target, ttl=(cttl), id=custom_id) / UDP(dport=cork) / Raw(ddata), verbose=False, timeout=10, filter=myfilter )

        recv_time = time.time()
        rtt = recv_time - sent_time


        if len(unanswered_sent):
            response['target'] = target
            response['ttl'] = unanswered_sent[0].ttl
            response['type'] = ResponseType.TIMEOUT
            if include_raw:
                response['raw_sent'] = unanswered_sent
                response['raw_recv'] = None
            return response

        answered_sent = answered[0][0]
        answered_received = answered[0][1]

        if include_raw:
            response['raw_sent'] = answered_sent
            response['raw_recv'] = answered_received

        if type(answered_received[1]) == scapy.layers.inet.ICMP:
            if answered_received[1].type == 11:
                # ICMP TTL Exceeded
                response['target'] = target
                response['ttl'] = answered_received[2].ttl # answered_sent.ttl
                response['host'] = answered_received[0].src
                response['rtt'] = rtt
                response['request_id'] = answered_received[2].id
                response['type'] = ResponseType.ICMP_TTL_EXCEEDED
                return response
            elif answered_received[1].type == 3:
                # ICMP Destination Unreachable/Port Unreachable
                assert(answered_received[1].code == 3)
                response['target'] = target
                response['ttl'] = answered_received[2].ttl # answered_sent.ttl
                response['host'] = answered_received[0].src
                response['rtt'] = rtt
                response['request_id'] = answered_received[2].id
                response['type'] = ResponseType.ICMP_PORT_UNREACH
                return response
            else:
                print("Unhandled ICMP response type:", answered_received[1].type)
                return answered_received[1].summary()

        print("Unhandled response:\n", answered_received.show())
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
        self.additional_targets = []

        # self.add_new_target("1.1.1.1")
        # self.add_new_target("microsoft.com")
        # self.add_new_target("asdf.com")
        # self.add_new_target("shaw.ca")

        # cat = getaddrinfo("microsoft.com", None, AddressFamily.AF_INET, SocketKind.SOCK_STREAM)

        self.window.set_transient_for(transient_for)
        self.window.show_all()

    def connect_builder_objects(self):
        builder = Gtk.Builder()
        builder.add_from_file(get_root_path() + "snapins/new_traceroute_ping2.glade")

        self.window = builder.get_object("window_traceroute_ping")
        self.combo_interface = builder.get_object("combo_interface")
        self.input_target1 = builder.get_object("input_target1")
        self.input_traceroute_freq = builder.get_object("input_traceroute_freq")
        self.input_ping_freq = builder.get_object("input_ping_freq")
        self.combo_traceroute_type = builder.get_object("combo_traceroute_type")
        self.combo_ping_type = builder.get_object("combo_ping_type")
        self.button_start = builder.get_object("button_start")
        self.button_cancel = builder.get_object("button_cancel")
        self.button_add_target = builder.get_object("button_add_target")
        self.box_target_list = builder.get_object("box_target_list")
        self.image_remove = builder.get_object("image_remove")
        self.switch_start_immediately = builder.get_object("switch_start_immediately")

        self.window.connect("delete-event", self.on_window_close)
        self.button_start.connect("clicked", self.start_ping)
        self.button_cancel.connect("clicked", self.close_cancel)
        self.button_add_target.connect("clicked", self.add_target_gui)

    def add_target_gui(self, event):
        self.add_new_target("")

    def add_new_target(self, target):
        new_box = Gtk.Box(Gtk.Orientation.HORIZONTAL, 3)
        new_entry_target = Gtk.Entry()
        new_entry_target.set_text(target)
        new_entry_target.set_activates_default(True)
        new_button_image = Gtk.Image.new_from_icon_name("gtk-remove",  Gtk.IconSize.BUTTON)
        new_button_delete = Gtk.Button()
        new_button_delete.set_image(new_button_image)
        new_button_delete.connect("clicked", self.button_click_remove_target)
        new_box.pack_start(new_entry_target, True, True, 0)
        new_box.pack_start(new_button_delete, False, True, 0)
        self.box_target_list.pack_start(new_box, False, False, 0)
        new_box.show_all()

        self.additional_targets.append((new_box, new_entry_target, new_button_delete, new_button_image))

    def button_click_remove_target(self, button):
        parent_box = button.get_parent()
        for index, box in enumerate(self.box_target_list.get_children()):
            if parent_box == box:
                break
        del self.additional_targets[index-1]
        self.box_target_list.remove(parent_box)
        sys.stdout.flush()


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

        targets = [self.input_target1.get_text()]
        for box, entry, button, image in self.additional_targets:
            targets.append(entry.get_text())

        self.configuration['targets'] = targets

        self.configuration['tr_freq'] = self.input_traceroute_freq.get_text()

        self.configuration['ping_freq'] = self.input_ping_freq.get_text()

        self.configuration['traceroute_type'] = self.combo_traceroute_type.get_active_text()

        self.configuration['ping_type'] = self.combo_ping_type.get_active_text()

        self.configuration['start_immediately'] = self.switch_start_immediately.get_state()

        self.window.response(1)
        self.window.close()

