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



class SnapInPathMTUDiscovery(Snapin):
	def __init__(self, configuration):
		pass

	@staticmethod
	def new_dialog(transient_parent):
		# Popup the new Traceroute Ping dialog and get a decision from the user
		new_traceroute_ping_dialog = DialogNewPathMTUDiscovery(transient_parent)
		result = new_traceroute_ping_dialog.run()

		if result == -1:
			return None
		else:
			return new_traceroute_ping_dialog.configuration.copy()

class DialogNewPathMTUDiscovery:
	def __init__(self, transient_for):
		self.connect_builder_objects()
		self.configuration = dict()
		self.additional_targets = []

		self.window.set_transient_for(transient_for)
		self.window.show_all()

	def connect_builder_objects(self):
		builder = Gtk.Builder()
		builder.add_from_file(get_root_path() + "snapins/new_pmtud.glade")

		self.window = builder.get_object("window_pmtud")
		self.combo_interface = builder.get_object("combo_interface")
		self.entry_target = builder.get_object("entry_target")
		self.combo_pmtud_type = builder.get_object("combo_type")
		self.button_start = builder.get_object("button_start")
		self.button_cancel = builder.get_object("button_cancel")

		self.window.connect("delete-event", self.on_window_close)
		self.button_start.connect("clicked", self.start_pmtud)
		self.button_cancel.connect("clicked", self.close_cancel)

	def run(self):
		self.window.show_all();
		result = self.window.run()
		return result

	def start_pmtud(self, event):
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

		self.configuration['target'] = self.entry_target.get_text()
		self.configuration['pmtud_type'] = self.combo_pmtud_type.get_active_text()

		self.window.response(1)
		self.window.close()

