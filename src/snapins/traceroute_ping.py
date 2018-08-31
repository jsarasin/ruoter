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

    def worker_tcpsyn_complete_callback(self, future):
        response = future.result()

        self.host_tracker.register_response(response)



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

