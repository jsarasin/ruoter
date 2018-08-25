#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib

import os

from gui.main_window import MainWindow

# main_window = MainWindow()
# Gtk.main()


from snapins.traceroute_ping import SnapInTraceroutePing
from snapins.snapin import Snapin
# from net.traceroute import Traceroute
#
# cat = Traceroute()
# cat.start("1.1.1.1")
#
# while True:
#     cat.check()


def catfood(task_id, cat):
    if cat == "TIMEOUT":
        print("*")
        return

    print("Hop[%s] %s" % (cat['ttl'], cat['responding_host']))


snappy = Snapin()
for ttl in range(1, 20):
    task_id = snappy.submit_task(catfood, SnapInTraceroutePing.worker_tcpsyn, ("1.1.1.1", ttl,))
    # print("Started new task:", task_id)


Snapin.thread_handler.join()