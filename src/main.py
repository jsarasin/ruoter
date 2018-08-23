#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib

import os

from gui.main_window import MainWindow

main_window = MainWindow()
Gtk.main()


# from net.traceroute import Traceroute
#
# cat = Traceroute()
# cat.start("1.1.1.1")
#
# while True:
#     cat.check()
