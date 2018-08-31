#!/usr/bin/python3


import os



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



def launch_gui():
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GdkPixbuf, GObject, GLib
    from gui.main_window import MainWindow

    main_window = MainWindow()
    Gtk.main()

def launch_cmd():
