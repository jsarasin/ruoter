#!/usr/bin/python3


def launch_gui():
    import gi
    gi.require_version('Gtk', '3.0')
    from gi.repository import Gtk, GdkPixbuf, GObject, GLib
    from gui.main_window import MainWindow

    main_window = MainWindow()
    Gtk.main()

def launch_cmd():
    from traceroute import MutliTraceroute

launch_gui()