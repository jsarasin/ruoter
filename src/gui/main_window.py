import os
import gi

gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
from custom_controls.route_visualizer import RouteVisualizerView, RouteVisualizerModel
import cairo


def get_pixbuf_from_filename_max_size(filename, width, height):
    # Nice wrapper to load a pixbuf with the specified image but you can specify a max width & height where it
    # will resize the image for you but maintain aspect ratio
    if not os.path.isfile(filename):
        return None

    pixbuf = GdkPixbuf.Pixbuf.new_from_file(filename)

    width_ratio = (width / pixbuf.get_width())
    height_ratio = (height / pixbuf.get_height())

    target_height_scaled_with_width = pixbuf.get_height() * width_ratio
    target_width_scaled_with_height = pixbuf.get_width() * height_ratio

    if target_height_scaled_with_width > width:
        scaled_pixbuf = pixbuf.scale_simple(pixbuf.get_width() * width_ratio, target_height_scaled_with_width,
                                            GdkPixbuf.InterpType.BILINEAR)
    else:
        scaled_pixbuf = pixbuf.scale_simple(target_width_scaled_with_height, pixbuf.get_height() * height_ratio,
                                            GdkPixbuf.InterpType.BILINEAR)

    return scaled_pixbuf


class TraceRouteNode:
    def __init__(self, ttl, address):
        self.ttl = ttl
        if address == "*":
            self.address = address + str(ttl)
        else:
            self.address = address

    def resolve_hostname(self):
        pass

    def resolve_asn(self):
        pass

    def find_device_type(self):
        pass


class TraceRoute:
    def __init__(self, target="56.115.13.54"):
        self.target = target
        self.nodes = []
        self.nodes.append(TraceRouteNode(0, "192.168.0.1"))
        self.nodes.append(TraceRouteNode(1, "43.121.23.2"))
        self.nodes.append(TraceRouteNode(2, "122.11.25.22"))
        self.nodes.append(TraceRouteNode(3, "64.24.4.235"))
        self.nodes.append(TraceRouteNode(4, "56.115.13.54"))

    def run_traceroute(self):
        pass


class MainWindow:
    def __init__(self):
        # User Interface elements

        self.icon_computer = cairo.ImageSurface.create_from_png("computer.png")
        self.icon_computer.set_device_scale(1.5, 1.5)
        self.icon_router = cairo.ImageSurface.create_from_png("router.png")
        self.icon_router.set_device_scale(1.5, 1.5)

        if self.icon_computer == None or self.icon_router == None:
            print("Failed to load icons.")

        self.connect_builder_objects()
        self.route_visualizer = RouteVisualizerView()

        self.visualizer_box.add(self.route_visualizer)

        self.window.show_all()

        self.route_model = RouteVisualizerModel()
        self.route_visualizer.set_model(self.route_model)
        self.route_visualizer.set_hexpand(True)
        self.route_visualizer.set_vexpand(True)

        self.trace_route = TraceRoute()

        self.update_route_model_from_traceroute()




        # self.route_model.add_node("192.168.0.1", {'hostname':'catsoup', 'ASN': None, 'pixbuf': self.icon_computer, 'selected':True} )
        # self.route_model.add_node("43.121.23.2", {'hostname':'dxf.trd.shaw.ca', 'ASN': 'AS434', 'pixbuf': self.icon_router} )
        # self.route_model.add_node("122.11.25.22", {'hostname':'f454d.cxau.ca', 'ASN': 'AS546', 'pixbuf': self.icon_router} )
        # self.route_model.add_node("64.24.4.235", {'hostname':'sn5.trd.dki.ca', 'ASN': None, 'pixbuf': self.icon_computer} )
        #
        # self.route_model.add_node("56.115.13.54", {'hostname':'fd4.fdd.ca', 'ASN': 'AS14', 'pixbuf': self.icon_router, 'posx': 550, 'posy':300} )

        # self.route_model.add_link('192.168.0.1', '43.121.23.2')
        # self.route_model.add_link('43.121.23.2', '122.11.25.22')
        # self.route_model.add_link('122.11.25.22', '64.24.4.235')
        #
        # self.route_model.add_link('43.121.23.2', '56.115.13.54', route_layer='1')
        # self.route_model.add_link('56.115.13.54', '64.24.4.235', route_layer='1')

    def update_route_model_from_traceroute(self):
        last_node = None
        for tnode in self.trace_route.nodes:
            if tnode.ttl == 0 or tnode.address == self.trace_route.target:
                pixbuf = self.icon_computer
            else:
                pixbuf = self.icon_router

            self.route_model.add_node(tnode.address, {'hostname': 'catsoup', 'ASN': None, 'pixbuf': pixbuf,
                                                      'selected': False})

            if last_node:
                self.route_model.add_link(last_node, tnode.address)

            last_node = tnode.address

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
