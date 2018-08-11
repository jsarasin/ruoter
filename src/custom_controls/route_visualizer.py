# History Logger widget
import gi
import random


gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
import cairo
from math import *

class RouteVisualizerModel(Gtk.DrawingArea):
    def __init__(self):
        self.nodes = dict()
        self.links = dict()


    def add_node(self, key, initial_values_dict):
        if key in self.nodes.keys():
            print("Trying to add a node when one already exists with that key")

        self.nodes[key] = initial_values_dict

    def set_node_key_value(self, node_key, value_key, value_value):
        if node_key not in self.nodes.keys():
            print("Trying to set the value for a node that doesnt exist")
            return

        self.nodes[node_key][value_key] = value_value

    # as links do not have a direction, source and destination don't make sense, b sounds diminutive to a
    # the direction specified doesn't matter only the parties involved. This function will check if this connection
    # already exists in either direction and will error if it does

    # route_layer will allow the ability to represent routes that change. default would represent the first route
    # discovered
    def add_link(self, node_a, node_b, route_layer='default'):
        # TODO: I'd like to internally order node_a and node_b based on if the entered value were stripped of . and :
        # and just be a pure hex number, whichever address has a lower value would be listed first
        # for now we'll just manually do this in whichever function calls this

        if node_a not in self.links.keys():
            self.links[node_a] = dict()

        if node_b not in self.links[node_a]:
            self.links[node_a][node_b] = dict()

        if 'route_layer' not in self.links[node_a][node_b]:
            self.links[node_a][node_b]['route_layer'] = dict()
        else:
            print("This link already exists")
            return

        self.links[node_a][node_b]['route_layer']['quality'] = 1.0  # Best quality link


class RouteVisualizerView(Gtk.DrawingArea):
    NODE_WIDTH = 150
    NODE_HEIGHT = 200
    NODE_SPACING = 100
    DRAG_THRESHOLD = 10

    def __init__(self):
        super().__init__()
        self._model = None
        self._view_top = 0
        self._view_left = 0
        self.mouse_dragging_selection = False
        self.button1_down = False
        self.last_selected_node = None
        self.hover_over_node = False
        self.selected_nodes_count = 0

        self.set_size_request(900,500)

        # setup events
        self.add_events(Gdk.EventMask.POINTER_MOTION_MASK)
        self.add_events(Gdk.EventMask.LEAVE_NOTIFY_MASK)
        self.add_events(Gdk.EventMask.BUTTON1_MOTION_MASK)
        self.add_events(Gdk.EventMask.BUTTON_PRESS_MASK)
        self.add_events(Gdk.EventMask.BUTTON_RELEASE_MASK)
        self.add_events(Gdk.EventMask.POINTER_MOTION_HINT_MASK)
        self.connect("motion-notify-event", self.mouse_move)
        self.connect("leave-notify-event", self.mouse_leave)
        self.connect("button-press-event", self.mouse_button_press)
        self.connect("button-release-event", self.mouse_button_release)
        self.connect("draw", self.draw)

    def point_in_node(self, x, y):
        for node, node_keys in self._model.nodes.items():
            if x > node_keys['posx'] and x < node_keys['posx'] + self.NODE_WIDTH and y > node_keys['posy'] and y < node_keys['posy'] + self.NODE_HEIGHT:
                return node

        return False


    def mouse_button_press(self, widget, event):
        self.mouse_down_x = event.x
        self.mouse_down_y = event.y
        self.button1_down = True

        mouse_in_node = self.point_in_node(self.mouse_down_x, self.mouse_down_y)

        # if event.state & Gdk.ModifierType.SHIFT_MASK:
        #     shift_in = True
        # else:
        #     shift_in = False
        #
        # if event.state & Gdk.ModifierType.CONTROL_MASK:
        #     control_in = True
        # else:
        #     control_in = False

        self.clear_node_selections()

        if mouse_in_node != False:
            self._model.nodes[mouse_in_node]['selected'] = True
            self.selected_nodes_count = self.selected_nodes_count + 1
            self.last_selected_node = mouse_in_node

        self.queue_draw()
        pass


    def mouse_button_release(self, widget, event):
        self.button1_down = False
        self.mouse_dragging_selection = False

        hovering = self.point_in_node(event.x, event.y)
        if hovering != self.hover_over_node:
            self.hover_over_node = hovering
            self.queue_draw()

    def clear_node_selections(self, except_node=None):
        for node, node_keys in self._model.nodes.items():
            if node == except_node:
                continue

            if 'selected' in node_keys:
                if node_keys['selected'] == True:
                    node_keys['selected'] = False

    def mouse_leave(self, widget, event):
        self._mouse_in_cell = -1
        self.queue_draw()

    def mouse_move(self, widget, event):
        if self.button1_down == True:
            self.hover_over_node = False
            if self.mouse_dragging_selection == False:
                if abs(event.x - self.mouse_down_x) > self.DRAG_THRESHOLD or abs(event.y - self.mouse_down_y) > self.DRAG_THRESHOLD:
                    self.mouse_dragging_selection = True

        if self.mouse_dragging_selection:
            delta_x = event.x - self.mouse_down_x
            delta_y = event.y - self.mouse_down_y

            self.move_selected_nodes(delta_x, delta_y)

            self.mouse_down_x = event.x
            self.mouse_down_y = event.y

        if self.button1_down == False:
            hovering = self.point_in_node(event.x, event.y)
            if hovering != self.hover_over_node:
                self.hover_over_node = hovering
                self.queue_draw()


    def move_selected_nodes(self, mx, my):
        for node, node_keys in self._model.nodes.items():
            if 'selected' in node_keys:
                if node_keys['selected'] == True:
                    node_keys['posx'] = node_keys['posx'] + mx
                    node_keys['posy'] = node_keys['posy'] + my

        self.queue_draw()


    def set_default_font_colour(self, cr):
        cr.set_source_rgb(1.0, 1.0, 1.0)

    def set_default_font_size(self, cr):
        cr.set_font_size(15.0)

    def set_smaller_than_default_font_size(self, cr):
        cr.set_font_size(10.0)

    def draw(self, widget, cr):
        default_source_pattern = cr.get_source()
        draw_start_left = 50

        cr.show_page()
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        # cr.set_surface(cairo.SolidPattern)

        if self._model == None:
            return

        for node, node_keys in self._model.nodes.items():
            cr.set_source(default_source_pattern)

            # Each node needs a position in our diagram, if none has been provided we'll give it a rough position
            if 'posx' not in node_keys.keys():
                print("Previous X not set")
                self._model.nodes[node]['posx'] = draw_start_left
                self._model.nodes[node]['posy'] = 50
                draw_start_left += self.NODE_WIDTH + self.NODE_SPACING


            # Convenience
            posx = node_keys['posx']
            posy = node_keys['posy']
            accumy = posy # I build this view by accumulating the Y value of elements

            # Determine if this node is selected or not
            node_selected = False
            if 'selected' in node_keys.keys():
                if node_keys['selected'] == True:
                    node_selected = True

            if node_selected:
                cr.set_source_rgba(0.3, 0.3, 0.7, 0.8)
            else:
                cr.set_source_rgba(0.3, 0.3, 0.3)

            self.rounded_rectangle(cr, posx, posy, self.NODE_WIDTH, self.NODE_HEIGHT)
            cr.fill()
            if self.hover_over_node == node:
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.2)
            else:
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.1)
            self.rounded_rectangle(cr, posx, posy, self.NODE_WIDTH, self.NODE_HEIGHT)
            cr.stroke()

            cr.move_to(posx, posy)

            if node_keys['pixbuf'] is not None:
                (curpathx, curpathy) =  cr.get_current_point()
                imgsurf = node_keys['pixbuf']
                cr.set_source_surface(imgsurf, curpathx + ((self.NODE_WIDTH / 2) - (imgsurf.get_width() / 2)), curpathy)
                cr.paint()
                cr.set_source(default_source_pattern)
                accumy = accumy + imgsurf.get_height()

            cr.move_to(posx + 10, accumy + 15)
            self.set_default_font_size(cr)
            self.set_default_font_colour(cr)
            cr.show_text(node)
            accumy = accumy + 15

            cr.move_to(posx + 10, accumy + 15)
            self.set_default_font_size(cr)
            self.set_default_font_colour(cr)
            cr.show_text(node_keys['hostname'])
            accumy = accumy + 15

        #############
        # Now draw the links
        for node_a_name, node_b_dict in self._model.links.items():
            for node_b_name in node_b_dict.keys():
                # Some constants
                LINE_START_WIDTH = 30
                LINK_CURVE = 10

                cr.set_source(default_source_pattern)
                cr.set_source_rgb(0.0, 0.8, 0.0)
                cr.set_line_width(4.0)
                cr.set_line_cap(cairo.LINE_CAP_ROUND)

                node_a = self._model.nodes[node_a_name]
                node_b = self._model.nodes[node_b_name]

                half_width = self.NODE_WIDTH / 2
                half_height = self.NODE_HEIGHT / 2

                node_a_x = node_a['posx'] + self.NODE_WIDTH / 2
                node_a_y = node_a['posy'] + self.NODE_HEIGHT / 2

                node_b_x = node_b['posx'] + self.NODE_WIDTH / 2
                node_b_y = node_b['posy'] + self.NODE_HEIGHT / 2

                x_distance_between_nodes = abs(node_a_x - node_b_x) - half_width
                y_distance_between_nodes = abs(node_a_y - node_b_y)

                ax = 0  # X accumulator
                ay = 0  # Y Accumulator


                if y_distance_between_nodes < half_height * 0.5:
                    y_aligned = True
                else:
                    y_aligned = False


                # Draw a little nub out the side of node_a
                if node_b_x > node_a_x + half_width:
                    node_b_right = True
                else:
                    node_b_right = False

                if node_b_y > node_a_y:
                    node_b_below = True
                else:
                    node_b_below = False

                if node_b_right:
                    dx = 1
                else:
                    dx = -1


                if node_b_below:
                    dy = 1
                else:
                    dy = -1

                if node_b_right:
                    cr.move_to(node_a_x + half_width, node_a_y)
                    ax = node_a_x + half_width
                    ay = node_a_y
                else:
                    cr.move_to(node_a_x - half_width, node_a_y)
                    ax = node_a_x - half_width
                    ay = node_a_y

                # If the nodes are fairly aligned on he Y axis, then just draw the line right across
                if y_aligned:
                    if node_b_right:
                        cr.line_to(node_b_x - half_width, node_a_y)
                    else:
                        cr.line_to(node_b_x + half_width, node_a_y)

                if not y_aligned and x_distance_between_nodes - self.NODE_WIDTH > LINK_CURVE * 2:
                    ax = ax + (x_distance_between_nodes - (half_width * dx)) / 2
                    cr.line_to(ax, ay)
                    cr.curve_to(ax, ay,
                                ax + (LINK_CURVE * dx), ay,
                                ax + (LINK_CURVE * dx), ay + (LINK_CURVE * dy))

                    ax = ax + (LINK_CURVE * dx)
                    ay = node_b_y - (LINK_CURVE * dy)

                    cr.line_to(ax, ay)

                    cr.curve_to(ax, ay,
                                ax, ay + (LINK_CURVE * dy),
                                ax + (LINK_CURVE * dx), ay + (LINK_CURVE * dy))

                    ax = ax + (LINK_CURVE * dx)
                    ay = ay + (LINK_CURVE * dy)

                    cr.line_to(node_b_x - (half_width * dx), node_b_y)

                if not y_aligned and x_distance_between_nodes - self.NODE_WIDTH <= LINK_CURVE * 2:
                    cr.line_to(node_b_x - (LINK_CURVE * dx), ay)
                    ax = node_b_x - (LINK_CURVE *dx)

                    cr.curve_to(ax, ay,
                                ax + (LINK_CURVE * dx), ay,
                                ax + (LINK_CURVE * dx), ay + (LINK_CURVE * dy))
                    ax = ax + (LINK_CURVE * dx)
                    ay = ay + (LINK_CURVE * dy)
                    cr.line_to(ax, node_b_y - (half_height * dy))


                cr.stroke()

            # first draw a line coming out the side whichever node b is on

                # node_a_con_point = self.get_closest_connection_point_to(node_a, node_b)
                # node_b_con_point = self.get_closest_connection_point_to(node_b, node_a)
                #
                # cr.move_to(node_a_con_point[0], node_a_con_point[1])
                # cr.line_to(node_b_con_point[0], node_b_con_point[1])
                # cr.stroke()
                # print("connection %s, %s" % (l1, l2))

    def draw_link_horizontal(self):
        pass

    def draw_link_vertical(self):
        pass

    def draw_link_offset(self):
        pass


    def get_closest_connection_point_to(self, this_node_name, other_node_name):
        this_node = self._model.nodes[this_node_name]
        other_node = self._model.nodes[other_node_name]

        half_width = self.NODE_WIDTH / 2
        half_height = self.NODE_HEIGHT / 2

        this_node_x = this_node['posx'] + self.NODE_WIDTH / 2
        this_node_y = this_node['posy'] + self.NODE_HEIGHT / 2

        other_node_x = other_node['posx'] + self.NODE_WIDTH / 2
        other_node_y = other_node['posy'] + self.NODE_HEIGHT / 2

        # option[]

        # if this_node_x - half_height > other_node_x:
        #     option['top'] = this_node_x - half_height

        # a = self.calc_distance(this_node_x + half_width, this_node_y, other_node_x, other_node_y) # Right
        # b = self.calc_distance(this_node_x, this_node_y + half_height, other_node_x, other_node_y) # Bottom
        # c = self.calc_distance(this_node_x - half_width, this_node_y, other_node_x, other_node_y) # Left
        # d = self.calc_distance(this_node_x, this_node_y - half_height, other_node_x, other_node_y) # Top
        #
        # if a <= b and a <= c and a <= d:
        #     return (this_node_x - half_width, this_node_y)
        # if b <= a and b <= c and b <= d:
        #     return (this_node_x, this_node_y + half_height)
        # if c <= a and c <= b and c <= d:
        #     return (this_node_x + half_width, this_node_y)
        # if d <= a and d <= b and d <= c:
        #     return (this_node_x, this_node_y - half_height)


    def calc_distance(self, x, y, xx, yy):
        if x > xx:
            x, xx = xx, x
        if y > y:
            y, yy = yy, y

        x = xx - x
        y = yy - y

        angle = atan(y/x)
        return angle * y

    def get_closest_link_path(self, node_a, node_b, route_layer='default'):
        nodes = self._model.nodes

        NODE_A = 1 # Just some constants
        NODE_B = 2
        TOP = 1
        RIGHT = 2
        BOTTOM = 3
        LEFT = 4

        node_a_left = nodes[node_a]['posx']
        node_a_right = nodes[node_a]['posx'] + self.NODE_WIDTH
        node_a_top = nodes[node_a]['posy']
        node_a_bottom = nodes[node_a]['posy'] + self.NODE_HEIGHT

        node_b_left = nodes[node_b]['posx']
        node_b_right = nodes[node_b]['posx'] + self.NODE_WIDTH
        node_b_top = nodes[node_b]['posy']
        node_b_bottom = nodes[node_b]['posy'] + self.NODE_HEIGHT


        if node_a_right < node_b_left:
            node_a_line_point = self.get_node_right_side(node_a)
            node_b_line_point = self.get_node_left_side(node_b)
        else:
            node_a_line_point = self.get_node_left_side(node_a)
            node_b_line_point = self.get_node_right_side(node_b)


        return (node_a_line_point, node_b_line_point)

    def get_node_top_side(self, node):
        x = self._model.nodes[node]['posx'] + (self.NODE_WIDTH / 2)
        y = self._model.nodes[node]['posy']
        return (x, y)

    def get_node_right_side(self, node):
        x = self._model.nodes[node]['posx'] + self.NODE_WIDTH
        y = self._model.nodes[node]['posy'] + (self.NODE_HEIGHT / 2)
        return (x, y)

    def get_node_bottom_side(self, node):
        x = self._model.nodes[node]['posx'] + (self.NODE_WIDTH / 2)
        y = self._model.nodes[node]['posy'] + self.NODE_HEIGHT
        return (x, y)

    def get_node_left_side(self, node):
        x = self._model.nodes[node]['posx']
        y = self._model.nodes[node]['posy'] + (self.NODE_HEIGHT / 2)
        return (x, y)


    def rounded_rectangle(self, cr, x, y, w, h, r=20):
        # http://www.cairographics.org/cookbook/roundedrectangles/
        cr.move_to(x + r, y)  # Move to A
        cr.line_to(x + w - r, y)  # Straight line to B
        cr.curve_to(x + w, y, x + w, y, x + w, y + r)  # Curve to C, Control points are both at Q
        cr.line_to(x + w, y + h - r)  # Move to D
        cr.curve_to(x + w, y + h, x + w, y + h, x + w - r, y + h)  # Curve to E
        cr.line_to(x + r, y + h)  # Line to F
        cr.curve_to(x, y + h, x, y + h, x, y + h - r)  # Curve to G
        cr.line_to(x, y + r)  # Line to H
        cr.curve_to(x, y, x, y, x + r, y)  # Curve to A




    def set_model(self, model):
        self._model = model
        self.queue_draw()




