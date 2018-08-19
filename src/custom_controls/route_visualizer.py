# History Logger widget
import gi
import random


gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
import cairo, time
from math import *

NODE_WIDTH = 120
NODE_HEIGHT = 150
NODE_SPACING = 70
DRAG_THRESHOLD = 10
LINE_START_WIDTH = 30
LINK_CURVE = 10
HALF_WIDTH = NODE_WIDTH * 0.5
HALF_HEIGHT = NODE_HEIGHT * 0.5
TRANSITION_LINK_TIME = 0.15
TRANSITION_NODE_TIME = 0.2

from .route_visualizer_path import RouteVisualizerLinkPath

class RouteVisualizerNode:
    def __init__(self, ip):
        self.ip = ip
        self.hostname = None
        self.asn = None
        self.posx = 0
        self.posy = 0
        self.selected = False
        self.links = {}
        self.add_time = None
        self.pixbuf = None
        self.transition_amount = None
        self.presented = False

    def update_link(self, link, other_node):
        self.links[link] = other_node

    def point_in_node(self, x, y):
        if self.posx - HALF_WIDTH < x < self.posx + HALF_WIDTH and self.posy - HALF_HEIGHT < y < self.posy + HALF_HEIGHT:
            return True

        return False


class RouteVisualizerModel(Gtk.DrawingArea):
    def __init__(self):
        self.nodes = []
        self.links = []
        self.new_node_position = [HALF_WIDTH + 10, HALF_HEIGHT + 10]


    def add_node(self, ip):
        new_node = RouteVisualizerNode(ip)
        new_node.add_time = time.time()
        new_node.posx = self.new_node_position[0]
        new_node.posy = self.new_node_position[1]
        self.new_node_position[0] = self.new_node_position[0] + NODE_WIDTH + NODE_SPACING

        self.nodes.append(new_node)

        return new_node

    def add_link(self, node_a, node_b, route_layer='default'):
        if type(node_a) is not RouteVisualizerNode or type(node_b) is not RouteVisualizerNode:
            print("Arguments must be direct node types")

        new_link = RouteVisualizerLinkPath(self, node_a, node_b)
        new_link.flow_last_seen = time.time()
        self.links.append(new_link)
        node_a.update_link(new_link, node_b)
        node_b.update_link(new_link, node_a)

        new_link.gen_path()

class RouteVisualizerView(Gtk.DrawingArea):
    def __init__(self):
        super().__init__()
        self._model = None
        self._view_top = 0
        self._view_left = 0
        self.mouse_dragging_selection = False
        self.button1_down = False
        self.last_selected_node = None
        self.hover_over_node = False
        self.hover_over_link = False
        self.selected_nodes_count = 0

        self.last_time = time.time()
        self.transition_links = []
        self.transition_nodes = []
        self.calling_animation_enable = False
        self.running_animation = False
        self.dash_length = 10
        self.dash_offset = 0

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

        # Start the call back to animate working links
        # GObject.timeout_add(100, self.link_animation)

    def link_animation(self):
        self.dash_offset = self.dash_offset - 1
        if self.dash_offset < -self.dash_length * 2:
            self.dash_offset = -1
        self.queue_draw()
        GObject.timeout_add(35, self.link_animation)

    def point_in_node(self, x, y):
        for node in self._model.nodes:
            if node.point_in_node(x, y):
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

        if mouse_in_node:
            mouse_in_node.selected = True
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
        for node in self._model.nodes:
            if node == except_node:
                continue

            node.selected = False

    def mouse_leave(self, widget, event):
        self.queue_draw()

    def mouse_move(self, widget, event):
        if self.button1_down == True:
            self.hover_over_node = False
            if not self.mouse_dragging_selection:
                if abs(event.x - self.mouse_down_x) > DRAG_THRESHOLD or abs(event.y - self.mouse_down_y) > DRAG_THRESHOLD:
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
                self.hover_over_link = False
                return

            for link in self._model.links:
                if link.mouse_over_link(event.x, event.y):
                    if link != self.hover_over_link:
                        self.queue_draw()

                    self.hover_over_link = link
                    self.queue_draw()
                    return

            if self.hover_over_link:
                self.queue_draw()

            self.hover_over_link = False




    def move_selected_nodes(self, mx, my):
        for node in self._model.nodes:
            if node.selected:
                node.posx = node.posx + mx
                node.posy = node.posy + my

                for node_link in node.links:
                    is_transitioning_path_type = False
                    # print("Link", node_link)
                    # TODO: If a link is between two selected nodes, we dont need to recalc link but just translate
                    old_path_type = node_link.path_type

                    while self.running_animation:
                        pass
                    self.calling_animation_enable = False

                    if node_link.old_path_type != node_link.path_type:
                        print("This node is transitioning")
                        is_transitioning_path_type = True
                    else:
                        is_transitioning_path_type = False

                    if node_link.old_path_type == None:
                        is_transitioning_path_type = False

                    if is_transitioning_path_type:
                        target_path = node_link.target_path
                        old_path = node_link.old_path
                        node_link.gen_path()
                        node_link.old_path = self.granulate_path(node_link.transition_path, 10)
                        print("just hands!")
                    else:
                        print("Big time!")
                        node_link.gen_path()
                        self.generate_link_animation(node_link)
                    self.calling_animation_enable = True

                    # If the path type is the same, then the line locations have only been updated,
                    # that means if there's a transition in progress, we can change its target to match the new
                    # path.
                    # if old_path_type == node_link.path_type and node_link.target_path != None:
                    #     node_link.target_path = self.granulate_path(node_link.path, len(node_link.target_path))
                    #     node_link.old_path = self.granulate_path(node_link.old_path, 10)

        self.queue_draw()


    def set_default_font_colour(self, cr):
        cr.set_source_rgb(1.0, 1.0, 1.0)

    def set_default_font_size(self, cr):
        cr.set_font_size(12.0)

    def set_smaller_than_default_font_size(self, cr):
        cr.set_font_size(10.0)

    def draw(self, widget, cr):
        matrix = cr.get_matrix()
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        size_bounds = [self.get_size_request()[0], self.get_size_request()[1]]


        if self._model == None:
            return

        for node in self._model.nodes:
            if not node.presented:
                self.generate_node_animation(node)

            self.draw_node(cr, node)

            cr.set_matrix(matrix)

            if node.posx + NODE_WIDTH > size_bounds[0]:
                size_bounds[0] = node.posx + NODE_WIDTH

            if node.posy + NODE_HEIGHT > size_bounds[1]:
                size_bounds[1] = node.posy + NODE_HEIGHT

        self.set_size_request(size_bounds[0], size_bounds[1])


        ####################################################
        # Now draw the links

        cr.set_line_width(4.0)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        for index, link in enumerate(self._model.links):
            if len(link.path) == 0:
                continue

            if link.old_path is not None and link.old_path != []:
                if link.old_path_type != link.path_type:
                    self.generate_link_animation(link)

            if self.hover_over_link == link:
                link_color = (0.1, 1.0, 0.1, 1.0)
            else:
                link_color = (0.1, 0.7, 0.1, 1.0)


            if link.transition_path is None:
                self.now_drawing = (index, link.path)
                link_path = link.path
            else:
                self.now_drawing = (index, link.transition_path)
                link_path = link.transition_path

            cr.set_source_rgba(link_color[0], link_color[1], link_color[2], link_color[3])
            cr.set_dash([], 0)

            self.draw_link(cr, link_path)

            # cr.set_source_rgba(link_color[0] + 0.1, link_color[1] + 0.1, link_color[2] + 0.1, link_color[3])
            # cr.set_dash([self.dash_length, self.dash_length], self.dash_offset)
            # self.draw_link(cr, link_path)





    def draw_node(self, cr, node):
        if node.transition_amount is not None:
            if node.transition_amount != 1.0:
                # cr.transform_point(-node.posx, -node.posy)
                cr.translate(node.posx, node.posy)
                cr.scale(node.transition_amount, node.transition_amount)
                cr.translate(-node.posx, -node.posy)
            else:
                cr.identity_matrix

        # Draw the background
        if node.selected:
            cr.set_source_rgba(0.3, 0.3, 0.7, 1.0)
        else:
            cr.set_source_rgba(0.3, 0.3, 0.3, 1.0)

        self.rounded_rectangle(cr, node.posx - HALF_WIDTH, node.posy - HALF_HEIGHT, NODE_WIDTH, NODE_HEIGHT)
        cr.fill()

        # Draw the border
        if self.hover_over_node == node:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.2)
        else:
            cr.set_source_rgba(1.0, 1.0, 1.0, 0.1)

        self.rounded_rectangle(cr, node.posx - HALF_WIDTH, node.posy - HALF_HEIGHT, NODE_WIDTH, NODE_HEIGHT)
        cr.stroke()

        # Y Flow
        accumulator_y = 0

        # Render an image if one is selected
        if node.pixbuf is not None and 1 == 0:
            # desired_width = NODE_WIDTH * 0.75
            # ratio_width = desired_width / node.pixbuf.get_width()
            # desired_height = node.pixbuf.get_height() * ratio_width
            # image_width = node.pixbuf.get_width() / node.pixbuf.get_device_scale()[0]
            # image_height = node.pixbuf.get_height() / node.pixbuf.get_device_scale()[1]
            # node.pixbuf.scale(0.5, 0.5)
            # cr.save()
            cat = cr.get_group_target()
            # cr.translate(node.posx, node.posy)
            # cr.get_group_target().set_device_offset(node.posx, node.posy)
            # cr.scale(0.5, 0.5)
            # cr.rectangle(node.posx - HALF_WIDTH, node.posy - HALF_HEIGHT, node.pixbuf.get_width() - 10, node.pixbuf.get_height() - 10)
            # cr.clip()

            cr.set_source_surface(node.pixbuf, int(node.posx - HALF_WIDTH), int(node.posy - HALF_HEIGHT))
            cr.rectangle(node.posx - HALF_WIDTH, node.posy - HALF_HEIGHT, node.pixbuf.get_width() - 10, node.pixbuf.get_height() - 10)
            cr.fill()
            # cr.get_group_target().set_device_offset(node.posx, node.posy)

            # cr.paint()
            cr.set_source_surface(cat)
            # cr.fill()
            # cr.set_source_surface(self.default_source)

            # cr.restore()
            # cr.paint()

            accumulator_y = accumulator_y + node.pixbuf.get_height() / node.pixbuf.get_device_scale()[1]

        # Render the text
        cr.move_to(node.posx + 10 - HALF_WIDTH, node.posy - HALF_HEIGHT +  accumulator_y + 15)
        self.set_default_font_size(cr)
        self.set_default_font_colour(cr)
        cr.set_source_rgba(0.0, 1.0, 1.0, 1.0)
        cr.show_text(node.ip)
        accumulator_y = accumulator_y + 15

        #
        # cr.move_to(node.posx + 10 - HALF_WIDTH, accumy + 15 - HALF_HEIGHT)
        # self.set_default_font_size(cr)
        # self.set_default_font_colour(cr)
        # cr.show_text(node.hostname)
        # accumy = accumy + 15

        cr.identity_matrix

    def draw_link(self, cr, line_path):
        if line_path is None:
            return

        last_point = None
        car = 0.0
        the_dirty = [0,0,0,0]

        for line_node in line_path:
            if line_node[0] < 10:
                print("SDfJDFDLFJLSDF"*5)
                print(self.now_drawing)
                print("SDfJDFDLFJLSDF"*5)

            if line_node[0] < the_dirty[0]:
                the_dirty[0] = line_node[0]
            if line_node[0] > the_dirty[2]:
                the_dirty[2] = line_node[0] - the_dirty[0]

            if line_node[1] < the_dirty[1]:
                the_dirty[1] = line_node[1]
            if line_node[1] > the_dirty[3]:
                the_dirty[3] = line_node[1] - the_dirty[1]

            cr. get_group_target().mark_dirty_rectangle(int(the_dirty[0]), int(the_dirty[1]), int(the_dirty[2]), int(the_dirty[3]))

            # Move to the first point
            if last_point is None:
                last_point = (line_node[0], line_node[1])
                cr.move_to(line_node[0], line_node[1])
                continue

            # Render the first node
            if len(line_node) == 2:
                cr.line_to(line_node[0], line_node[1])
                last_point = (line_node[0], line_node[1])

            # Render a curve
            if len(line_node) == 4:
                cr.curve_to(last_point[0], last_point[1],
                            line_node[0], line_node[1],
                            line_node[2], line_node[3])
                last_point = (line_node[2], line_node[3])

        cr.stroke()


    def generate_link_animation(self, link):
        if link not in (n[0] for n in self.transition_links):
            # If there is already an ongoing transition with this node we need to update it
            self.calling_animation_enable = False
            while (self.running_animation):
                pass

            link.old_path_type = link.path_type
            link.target_path = self.granulate_path(link.path, 10)
            link.old_path = self.granulate_path(link.old_path, 10)

            link.transition_path = [(0, 0)] * len(link.old_path)
            self.transition_links.append((link, time.time()))
            self.calling_animation_enable = True
            self.transition_animate()
        # Or if we are working on it
        else:
            # There isn't an ongoing operation so let's create a new one
            self.calling_animation_enable = False
            while (self.running_animation):
                pass

            for index, trans in enumerate(self.transition_links):
                if trans[0] == link:
                    break

            link.old_path_type = link.path_type

            link.target_path = self.granulate_path(link.path, 10)
            link.old_path = self.granulate_path(link.transition_path, 10)

            self.transition_links[index] = (link, time.time())
            self.calling_animation_enable = True

    def generate_node_animation(self, node):
        self.calling_animation_enable = False
        while (self.running_animation):
            pass

        if node not in self.transition_nodes:
            self.transition_nodes.append((node, time.time()))
            self.calling_animation_enable = True
            self.transition_animate()

        self.calling_animation_enable = True

        self.queue_draw()

    def transition_node_animate(self):
        delete_node_animations = []
        tstart = time.time()

        for node, start_time in self.transition_nodes:
            time_delta = time.time() - start_time
            animation_completion_perc = (time_delta / TRANSITION_NODE_TIME)

            node.transition_amount = animation_completion_perc

            if animation_completion_perc >= 1.0:
                delete_node_animations.append((node, start_time))
                node.transition_amount = 1.0
                node.presented = True

        # Remove completed animations
        for item in delete_node_animations:
            self.transition_nodes.remove(item)


    def transition_link_animate(self):
        if 'cat' not in dir(self):
            self.cat = 0
        else:
            self.cat = self.cat +1

        if self.cat > 1:
            print ("Ffff" * 10, self.cat)

        delete_link_animations = []
        tstart = time.time()

        for link, start_time in self.transition_links:
            time_delta = time.time() - start_time
            animation_completion_perc = (time_delta / TRANSITION_LINK_TIME)
            # print("com", animation_completion_perc)
            for index in range(len(link.target_path)):
                tx = link.target_path[index][0]
                ty = link.target_path[index][1]
                # print("old path:", link.old_path)
                try:
                    sx = link.old_path[index][0]
                    sy = link.old_path[index][1]
                except:
                    print("FUCK")
                    print(index)
                    print(link)
                    print(link.old_path)
                    print(link.target_path)
                    print()
                    import os
                    Gtk.main_quit(1)


                movement_angle = atan2(tx - sx, (ty-sy))
                movement_length = hypot(abs(tx - sx), abs(ty-sy))

                dy = cos(movement_angle) * (movement_length * animation_completion_perc)
                dx = sin(movement_angle) * (movement_length * animation_completion_perc)

                link.transition_path[index] = (sx + dx, sy + dy)

            if animation_completion_perc >= 1.0:
                delete_link_animations.append((link, start_time))
                link.old_path_type = link.path_type

                link.transition_path = None

        # Remove completed animations
        for item in delete_link_animations:
            self.transition_links.remove(item)

        self.cat = self.cat - 1



    def transition_animate(self):
        tstart = time.time()
        # This is called via a Gtk Registered call back. This is what animates the transitions

        # GTK is multithreaded, and it is (almost?) certain that if this is called from a call back
        # it will be in a separate thread. We need to prevent simultaneous modification of the same vars
        while(not self.calling_animation_enable):
            pass
        self.running_animation = True


        self.transition_link_animate()
        self.transition_node_animate()

        self.queue_draw()


        if len(self.transition_links) > 0 or len(self.transition_nodes) > 0:
            GObject.timeout_add(40, self.transition_animate)

        self.running_animation = False

        # Below is useful for showing how long the animations take to process
        tend = time.time()
        # print("Animation Call took: %.2f %s"  % ((float(tend - tstart) * 1000), "*" * int((float(tend - tstart) * 100000))))


    def granulate_path(self, source_path, target_node_count):
        if len(source_path) == target_node_count:
            result = source_path.copy()
            assert(len(result) == target_node_count)
            return result
        if len(source_path) > target_node_count:
            result = source_path.copy()[:target_node_count]
            assert(len(result) == target_node_count)
            return result
        if len(source_path) < target_node_count:
            result = source_path.copy()
            for x in range(target_node_count - len(source_path)-1):
                result.append((source_path[len(source_path)-1][0], source_path[len(source_path)-1][1]))

            # assert(len(result) == target_node_count)
            return result

            new_path = []
            lengths = []
            previous_node = None

            # First we need to calculate the total pixel length of the entire link
            for node in source_path:
                if previous_node != None:
                    length = self.calc_distance(previous_node, node)
                    lengths.append(length)

                previous_node = node
            total_length = sum(lengths[:])


            # Now we need to iterate over each of the old nodes and break them up depending on their proportion
            previous_node = None
            for index, node in enumerate(source_path[:]):
                if previous_node is not None:
                    total_length_for_node = lengths[index-1] / total_length
                    subdivide_count = max((round(subdivide_percent * len(source_path)), 1))
                    subdivide_amount = subdivide_percent * total_length
                    print("Index", index, round(subdivide_percent*100), "%", subdivide_count)
                    #print("Index", index, "gets", subdivide_count, "length is:", lengths[index-1])
                    tx = previous_node[0]
                    ty = previous_node[1]
                    sx = node[0]
                    sy = node[1]

                    if tx == sx and ty < sy:
                        movement_angle = 0
                    elif tx == sx and ty > sy:
                        movement_angle = pi
                    elif ty == sy and tx < sx:
                        movement_angle = pi * 1.5
                    elif ty == sy and tx > sx:
                        movement_angle = pi * 0.5
                    else:
                        movement_angle = atan2(tx - sx, (ty - sy))

                    dx = 0
                    dy = 0
                    for index in range(int(subdivide_percent * target_node_count)):
                        dy = dy + cos(movement_angle) * (subdivide_amount)
                        dx = dx + sin(movement_angle) * (subdivide_amount)

                        new_path.append((dx, dy))


                previous_node = node


            return new_path


    def calc_distance(self, xy, xxyy):
        x = xy[0]
        y = xy[1]
        xx = xxyy[0]
        yy = xxyy[1]
        return sqrt((x-xx)*(x-xx) + (y-yy)*(y-yy))

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




