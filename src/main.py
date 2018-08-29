#!/usr/bin/python3

import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib

import os

from gui.main_window import MainWindow

main_window = MainWindow()
Gtk.main()


import sys

from snapins.traceroute_ping import SnapInTraceroutePing
import concurrent.futures

# def catsoup(future):
#     worker_data = future.result()
#     if worker_data:
#         print(worker_data)
#         sys.stdout.flush()
#
# executor =  concurrent.futures.ThreadPoolExecutor(max_workers=10)
# for ttl in range(1,20):
#     future = executor.submit(SnapInTraceroutePing.worker_tcpsyn, "1.1.1.1", ttl)
#     future.add_done_callback(catsoup)








quit()

from snapins.traceroute_ping import SnapInTraceroutePing
from snapins.snapin import Snapin

def catfood(task_id, cat):
    if cat == "TIMEOUT":
        print("*")
        return

    print("Hop[%s] %s" % (cat['ttl'], cat['responding_host']))

snappy = Snapin()
for ttl in range(1, 21):
    task_id = snappy.submit_task(catfood, SnapInTraceroutePing.worker_tcpsyn, ("1.1.1.1", ttl,))

SnapInTraceroutePing.worker_pool[0].join()
