import os
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel
import cairo


class MainWindow:
    def __init__(self):
        # User Interface elements

        self.icon_computer = cairo.ImageSurface.create_from_png("computer.png")
        self.icon_router = cairo.ImageSurface.create_from_png("router.png")

        if self.icon_computer == None or self.icon_router == None:
            print("Failed to load icons.")

        self.connect_builder_objects()
        self.route_visualizer = RouteVisualizerView()

        self.visualizer_box.add(self.route_visualizer)

        self.window.show_all()

        self.route_model = RouteVisualizerModel()
        self.route_visualizer.set_model(self.route_model)

        self.route_model.add_node("192.168.0.1", {'hostname':'catsoup', 'ASN': None, 'pixbuf': self.icon_computer, 'selected':True} )
        self.route_model.add_node("43.121.23.2", {'hostname':'dxf.trd.shaw.ca', 'ASN': 'AS434', 'pixbuf': self.icon_router} )
        self.route_model.add_node("122.11.25.22", {'hostname':'f454d.cxau.ca', 'ASN': 'AS546', 'pixbuf': self.icon_router} )
        self.route_model.add_node("64.24.4.235", {'hostname':'sn5.trd.dki.ca', 'ASN': None, 'pixbuf': self.icon_computer} )

        self.route_model.add_node("56.115.13.54", {'hostname':'fd4.fdd.ca', 'ASN': 'AS14', 'pixbuf': self.icon_router, 'posx': 550, 'posy':300} )

        self.route_model.add_link('192.168.0.1', '43.121.23.2')
        self.route_model.add_link('43.121.23.2', '122.11.25.22')
        self.route_model.add_link('122.11.25.22', '64.24.4.235')

        self.route_model.add_link('43.121.23.2', '56.115.13.54', route_layer='1')
        self.route_model.add_link('56.115.13.54', '64.24.4.235', route_layer='1')



        # self.route_visualizer.add_hop("192.168.0.1")
        # self.route_visualizer.add_hop("43.121.23.2")
        # self.route_visualizer.add_hop("122.11.25.22")
        # self.route_visualizer.add_hop("64.24.4.235")

    def connect_builder_objects(self):
        builder = Gtk.Builder()
        builder.add_from_file("gui/main.glade")

        self.window = builder.get_object("main_window")
        self.visualizer_box = builder.get_object("visualizer_box")

        self.window.connect("delete-event", Gtk.main_quit)
