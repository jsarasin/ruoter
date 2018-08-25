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

def catfood(task_id, cat):
    if cat == "TIMEOUT":
        print("*")
        return

    print("Hop[%s] %s" % (cat['ttl'], cat['responding_host']))

snappy = Snapin()
for ttl in range(1, 21):
    task_id = snappy.submit_task(catfood, SnapInTraceroutePing.worker_tcpsyn, ("1.1.1.1", ttl,))

SnapInTraceroutePing.worker_pool[0].join()

#
#
# Snapin.thread_handler.join()
#
# result = SnapInTraceroutePing.worker_tcpsyn("1.1.1.1", 9)
# print(result)
#
# target = '1.1.1.1'
# from scapy.all import *
# ans, unans = sr(IP(dst=target, ttl=(4,15),id=RandShort())/TCP(flags=0x2), timeout=1)
#



#
#
# from scapy.all import *
# import scapy.layers.inet
# target = "1.1.1.1"
#
# ans, unans = sr(IP(dst=target, ttl=(1,11),id=RandShort())/TCP(flags=0x2), timeout=1 )
# for snd,rcv in ans:
#     print(snd.ttl, rcv.src, isinstance(rcv.payload, TCP))
#
