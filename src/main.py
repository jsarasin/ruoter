#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib

import os

from gui.main_window import MainWindow
from gui.new_traceroute_ping import NewTraceroutePing

main_window = MainWindow()
Gtk.main()


# newtp = NewTraceroutePing()
# Gtk.main()


quit()

from net.traceroute import TraceRoute

tr = TraceRoute("1.1.1.1")
tr.start_traceroute("1.1.1.1")

# tr.run_test()

print("TTL| IP              |")
print("---+-----------------+--------------")
for index, node in enumerate(tr.nodes):
    print("%-3i| %15s |" % (node.ttl, node.ip))
