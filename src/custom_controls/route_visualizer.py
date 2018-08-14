# History Logger widget
import gi
import random


gi.require_version('Gtk', '3.0')
from gi.repository import Gtk, GdkPixbuf, GObject, GLib, Gdk, cairo
import cairo, time
from math import *

NODE_WIDTH = 150
NODE_HEIGHT = 200
NODE_SPACING = 100
DRAG_THRESHOLD = 10
LINE_START_WIDTH = 30
LINK_CURVE = 10
HALF_WIDTH = NODE_WIDTH * 0.5
HALF_HEIGHT = NODE_HEIGHT * 0.5
TRANSITION_ANIMATION_TIME = 0.15


class RouteVisualizerLinkPath:
    def __init__(self, model, node_a, node_b):
        self.path = []
        self.model = model
        self.node_a = node_a
        self.node_b = node_b
        self.old_path_type = None # For transition animation
        self.old_path = None
        self.path_type = None
        self.transition_path = None
        self.target_path = None


    def add_straight(self, x, y):
        self.path.append((x, y))

    def add_curved(self, x, y, cx, cy):
        curved_tuple = (x, y, cx, cy)
        self.path.append(curved_tuple)

    def clear(self):
        self.path = []

    def get_path(self):
        if len(self.path) == 0:
            self.gen_path()

        return self.path

    def gen_path(self):
        # EDGE_ACCOMODATE_CURVE_PERCENT = 0.9
        EDGE_ACCOMODATE_CURVE_PERCENT = 1.0

        if self.node_b['posx'] > self.node_a['posx']:
            b_right_of = True
        else:
            b_right_of = False

        if self.node_b['posy'] > self.node_a['posy']:
            b_below_of = True
        else:
            b_below_of = False

        if b_right_of:
            dx = 1
        else:
            dx = -1

        if b_below_of:
            dy = 1
        else:
            dy = -1

        horizontal_offset = abs(self.node_a['posx'] - self.node_b['posx'])
        vertical_offset = abs(self.node_a['posy'] - self.node_b['posy'])
        # TODO: Handle overlapping nodes nicely

        # If the nodes are horizontally aligned up to EDGE_ACCOMODATE_CURVE_PERCENT%: Straight line from center of node A
        if vertical_offset < HALF_HEIGHT * EDGE_ACCOMODATE_CURVE_PERCENT:
            self.change_new_type(1)

            self.add_straight(self.node_a['posx'] + (HALF_WIDTH * dx), self.node_a['posy'])
            self.add_straight(self.node_b['posx'] - (HALF_WIDTH * dx), self.node_a['posy'])
            return

        # if the nodes are horizontally aligned over EDGE_ACCOMODATE_CURVE_PERCENT%: Offset line offset from center of node A
        if vertical_offset >= HALF_HEIGHT * EDGE_ACCOMODATE_CURVE_PERCENT and vertical_offset < HALF_HEIGHT and EDGE_ACCOMODATE_CURVE_PERCENT < 1.0:
            self.change_new_type(2)
            vertical_offset_correct = (HALF_HEIGHT * EDGE_ACCOMODATE_CURVE_PERCENT - vertical_offset) * dy * -1
            self.add_straight(self.node_a['posx'] + (HALF_WIDTH * dx), self.node_a['posy'] + (vertical_offset_correct))
            self.add_straight(self.node_b['posx'] - (HALF_WIDTH * dx), self.node_a['posy'] + (vertical_offset_correct))
            return

        # If the nodes are vertically aligned up to EDGE_ACCOMODATE_CURVE_PERCENT%: Straight line from center of node A
        if horizontal_offset < HALF_WIDTH * EDGE_ACCOMODATE_CURVE_PERCENT:
            self.change_new_type(3)
            self.add_straight(self.node_a['posx'], self.node_a['posy'] + (HALF_HEIGHT * dy))
            self.add_straight(self.node_a['posx'], self.node_b['posy']- (HALF_HEIGHT * dy))
            return

        # if the nodes are vertically aligned over EDGE_ACCOMODATE_CURVE_PERCENT%: Offset line offset from center of node A
        if horizontal_offset >= HALF_WIDTH * EDGE_ACCOMODATE_CURVE_PERCENT and horizontal_offset < HALF_WIDTH and EDGE_ACCOMODATE_CURVE_PERCENT < 1.0:
            self.change_new_type(4)
            horizontal_offset_correct = (HALF_WIDTH * EDGE_ACCOMODATE_CURVE_PERCENT - horizontal_offset) * dx * -1
            self.add_straight(self.node_a['posx'] + (horizontal_offset_correct), self.node_a['posy'] + (HALF_HEIGHT * dy))
            self.add_straight(self.node_a['posx'] + (horizontal_offset_correct), self.node_b['posy']- (HALF_HEIGHT * dy))
            return

        # If the nodes are neither horz or vert aligned yet far enough apart on the horz plane to accommodate curves...
        # If the horizontal offset is greater than two curve sizes
        if horizontal_offset - NODE_WIDTH > LINK_CURVE * 2 and vertical_offset > HALF_HEIGHT:
            self.change_new_type(5)
            middle_point = self.node_a['posx'] + (((horizontal_offset) / 2) * dx)

            self.add_straight(self.node_a['posx'] + (HALF_WIDTH * dx), self.node_a['posy'])
            self.add_straight(middle_point + (LINK_CURVE * dx * -1), self.node_a['posy'])
            self.add_curved(middle_point, self.node_a['posy'],
                            middle_point, self.node_a['posy'] + (LINK_CURVE * dy))
            self.add_straight(middle_point, self.node_b['posy'] + (LINK_CURVE * dy * -1))
            self.add_curved(middle_point, self.node_b['posy'],
                            middle_point + (LINK_CURVE * dx), self.node_b['posy'])
            self.add_straight(self.node_b['posx'] + (HALF_WIDTH * dx * -1), self.node_b['posy'])
            return

        # If the horizontal offset is smaller than two curve sizes
        if horizontal_offset - NODE_WIDTH <= LINK_CURVE * 2 and vertical_offset > HALF_HEIGHT:
            self.change_new_type(6)
            self.add_straight(self.node_a['posx'] + (HALF_WIDTH * dx), self.node_a['posy'])
            self.add_straight(self.node_b['posx'] + (LINK_CURVE * dx * -1), self.node_a['posy'])
            self.add_curved(self.node_b['posx'], self.node_a['posy'],
                            self.node_b['posx'], self.node_a['posy'] + (LINK_CURVE * dy))
            self.add_straight(self.node_b['posx'], self.node_b['posy'] + (HALF_HEIGHT * dy * -1))
            self.path_type = 6

    def change_new_type(self, type):
        if self.path_type != type:
            self.old_path = self.path.copy()
            self.old_path_type = self.path_type
            self.path_type = type
            self.clear()
            return True

        self.clear()
        return False









class RouteVisualizerModel(Gtk.DrawingArea):
    def __init__(self):
        self.nodes = dict()
        self.links = dict()
        self.new_node_position = [150, 150]


    def add_node(self, key, initial_values_dict):
        if key in self.nodes.keys():
            print("Trying to add a node when one already exists with that key")

        initial_values_dict['posx'] = self.new_node_position[0]
        initial_values_dict['posy'] = self.new_node_position[1]
        initial_values_dict['links'] = []

        self.new_node_position[0] = self.new_node_position[0] + NODE_WIDTH + NODE_SPACING
        self.nodes[key] = initial_values_dict

        return self.nodes[key]

    def add_link(self, node_a, node_b, route_layer='default'):
        # TODO: I'd like to internally order node_a and node_b based on if the entered value were stripped of . and :
        # and just be a pure hex number, whichever address has a lower value would be listed first
        # for now we'll just manually do this in whichever function calls this

        if node_a not in self.links.keys():
            self.links[node_a] = dict()

        if node_b not in self.links[node_a]:
            self.links[node_a][node_b] = dict()
            self.links[node_a][node_b]['path'] = RouteVisualizerLinkPath(self, self.nodes[node_a], self.nodes[node_b])

            if self.links[node_a][node_b]['path'] not in self.nodes[node_a]['links']:
                self.nodes[node_a]['links'].append(self.links[node_a][node_b]['path'])

            if self.links[node_a][node_b]['path'] not in self.nodes[node_b]['links']:
                self.nodes[node_b]['links'].append(self.links[node_a][node_b]['path'])

            return

        print("Link Already exists")


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
        self.selected_nodes_count = 0

        self.last_time = time.time()
        self.transition_links = []
        self.calling_animation_enable = False
        self.running_animation = False


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
            if x > node_keys['posx'] - HALF_WIDTH and x < node_keys['posx'] + HALF_WIDTH and y > node_keys['posy'] - HALF_HEIGHT and y < node_keys['posy'] + HALF_HEIGHT:
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


    def move_selected_nodes(self, mx, my):
        for node, node_keys in self._model.nodes.items():
            if 'selected' in node_keys:
                if node_keys['selected'] == True:
                    node_keys['posx'] = node_keys['posx'] + mx
                    node_keys['posy'] = node_keys['posy'] + my

                    for link in self._model.nodes[node]['links']:
                        old_path_type = link.path_type
                        link.gen_path()

                        # If the path type is the same, then the line locations have only been updated,
                        # that means if there's a transition in progress, we can change its target to match the new
                        # path.
                        if old_path_type == link.path_type:
                            link.get_path()
                            link.target_path = self.granulate_path(link.get_path(), len(link.target_path))




        self.queue_draw()


    def set_default_font_colour(self, cr):
        cr.set_source_rgb(1.0, 1.0, 1.0)

    def set_default_font_size(self, cr):
        cr.set_font_size(15.0)

    def set_smaller_than_default_font_size(self, cr):
        cr.set_font_size(10.0)

    def draw(self, widget, cr):
        default_source_pattern = cr.get_source()

        cr.show_page()
        width = self.get_allocated_width()
        height = self.get_allocated_height()
        # cr.set_surface(cairo.SolidPattern)

        if self._model == None:
            return

        for node, node_keys in self._model.nodes.items():
            cr.set_source(default_source_pattern)

            # Convenience
            posx = node_keys['posx'] - HALF_WIDTH
            posy = node_keys['posy'] - HALF_HEIGHT
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

            self.rounded_rectangle(cr, posx, posy, NODE_WIDTH, NODE_HEIGHT)
            cr.fill()
            if self.hover_over_node == node:
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.2)
            else:
                cr.set_source_rgba(1.0, 1.0, 1.0, 0.1)
            self.rounded_rectangle(cr, posx, posy, NODE_WIDTH, NODE_HEIGHT)
            cr.stroke()

            cr.move_to(posx, posy)

            if node_keys['pixbuf'] is not None:
                (curpathx, curpathy) =  cr.get_current_point()
                imgsurf = node_keys['pixbuf']
                cr.set_source_surface(imgsurf, curpathx + ((NODE_WIDTH / 2) - (imgsurf.get_width() / 2)), curpathy)
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

        cr.set_source(default_source_pattern)
        cr.set_line_width(4.0)
        cr.set_line_cap(cairo.LINE_CAP_ROUND)

        for node_a_name, node_b_dict in self._model.links.items():
            for node_b_name in node_b_dict.keys():
                link = self._model.links[node_a_name][node_b_name]['path']
                line_path = link.get_path()
                if len(line_path) == 0:
                    continue

                # If a transition animation is possible...
                if link.old_path is not None and link.old_path != []:
                    # And the current nodes we're working on have link types which have just changed
                    if link.old_path_type != link.path_type:
                        # And we're not already working on it
                        if link not in (n[0] for n in self.transition_links):
                            self.calling_animation_enable = False
                            while(self.running_animation):
                                pass

                            link.old_path_type = link.path_type
                            (link.target_path, link.old_path) = self.convert_path_node_count(line_path, link.old_path)
                            link.transition_path = [(0,0)] * len(link.old_path)
                            print("new")
                            self.transition_links.append((link, time.time()))
                            self.calling_animation_enable = True
                            self.transition_animate()
                        # Or if we are working on it
                        else:
                            self.calling_animation_enable = False
                            while(self.running_animation):
                                pass

                            for index, trans in enumerate(self.transition_links):
                                if trans[0] == link:
                                    break
                            if index > len(self.transition_links):
                                print("DIDNT asffd")

                            print("Transfer")
                            link.old_path_type = link.path_type
                            (link.target_path, link.old_path) = self.convert_path_node_count(line_path, link.target_path)
                            link.transition_path = [(0,0)] * len(link.old_path)

                            self.transition_links[index] = (link, time.time())
                            self.calling_animation_enable = True




                cr.set_source_rgb(0.8, 0.8, 0.1)

                cr.set_source_rgba(0.1, 0.8, 0.1, 1.0)
                if link.transition_path is None:
                    self.draw_path(cr, line_path)
                else:
                    self.draw_path(cr, link.transition_path)



    def draw_path(self, cr, line_path):
        if line_path is None:
            return

        last_point = None
        car = 0.0

        for line_node in line_path:
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

    def transition_animate(self):
        delete_animations = []

        # As this function is likely to be called from a separate thread, we need to disable its execution
        # while the other thread is manipulating data
        # TODO: There is the possibility of some multithreaded bugs here... Fixing would require a more complicated system
        # Let's hope for the best eh?
        while(not self.calling_animation_enable):
            pass

        self.running_animation = True

        for link, start_time in self.transition_links:
            time_delta = time.time() - start_time
            animation_completion_perc = (time_delta / TRANSITION_ANIMATION_TIME)

            for index in range(len(link.target_path)):
                tx = link.target_path[index][0]
                ty = link.target_path[index][1]
                sx = link.old_path[index][0]
                sy = link.old_path[index][1]

                movement_angle = atan2(tx - sx, (ty-sy))
                movement_length = hypot(abs(tx - sx), abs(ty-sy))
                dy = cos(movement_angle) * (movement_length * animation_completion_perc)
                dx = sin(movement_angle) * (movement_length * animation_completion_perc)

                link.transition_path[index] = (sx + dx, sy + dy)

            if animation_completion_perc >= 1.0:
                delete_animations.append((link, start_time))
                link.transition_path = None

        for item in delete_animations:
            self.transition_links.remove(item)
            print("Delete")

        self.queue_draw()

        if len(self.transition_links) > 0:
            GObject.timeout_add(10, self.transition_animate)

        self.running_animation = False

    def convert_path_node_count(self, new_path, old_path):
        translate_new_path = []
        translate_old_path = []
        if len(new_path) > len(old_path):
            translate_new_path = new_path.copy()
            translate_old_path = old_path.copy()
            while len(translate_old_path) < len(new_path):
                translate_old_path.append(old_path[len(old_path)-1])

        elif len(new_path) < len(old_path):
            translate_old_path = old_path.copy()
            translate_new_path = new_path.copy()
            while len(translate_new_path) < len(old_path):
                translate_new_path.append(new_path[len(new_path) - 1])

        else:
            translate_new_path = new_path.copy()
            translate_old_path = old_path.copy()

        return (translate_new_path, translate_old_path)

    def granulate_path(self, source_path, target_node_count):
        source_path_length = len(source_path)
        if len(source_path) == target_node_count:
            return source_path
        if len(source_path) > target_node_count:
            result = source_path[:target_node_count]
            print("Granulate shrink result: %s, target %s" %(len(result), target_node_count) )
        if len(source_path) < target_node_count:
            for x in range(target_node_count - len(source_path)):
                source_path.append((source_path[source_path_length-1][0], source_path[source_path_length-1][1]))

            return source_path

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




