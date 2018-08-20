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
ANIMATION_TICK = 1
GRANULATED_ANIMATION_PATH_SIZE = 20

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
        new_link.path, new_link.path_type = new_link.gen_path()

        self.links.append(new_link)
        node_a.update_link(new_link, node_b)
        node_b.update_link(new_link, node_a)


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
        self.transition_links = []  # List of links which are undergoing an animation
        self.transition_nodes = []  # Blah nodes
        self.calling_animation_enable = True # For Multithreaded protection
        self.running_animation = False # For Multithreaded protection
        self.animation_tick_enabled = False

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
            if not node.selected:
                continue

            # Move the selected node(s)
            node.posx = node.posx + mx
            node.posy = node.posy + my

            # TODO: Possible optimization: build a list of selected nodes during the initial iteration,
            # then with that, iterate again just over them to deal with the links. This will allow translation of
            # links instead of having to completely recalculate the route for each one if both ends of the link
            # is part of a selected node

            # Update the links connected to that node
            while self.running_animation:
                pass
            self.calling_animation_enable = False

            for node_link in node.links:
                new_path, new_path_type = node_link.gen_path()

                # Different states our link can be in, in regards to animations:
                # 1 - Same path type - just immediately change to the new path
                # 2 - New path type, start an animations
                # 3 - There is an animation currently:
                #      - The new new path type is the same as the target, just a different end point
                #      - The new path type is different than the animations end point
                #      - Either way, we need to update the target animation data

                # No current animations
                if node_link.target_path_type is None:
                    # The new location has the same type of path
                    if new_path_type == node_link.path_type:
                        node_link.path = new_path
                    # The new location requires an animation to transition
                    else:
                        print("New Animation")
                        self.generate_link_animation(new_path, new_path_type, node_link)

                # There is an existing animation that we need to update
                elif node_link.target_path is not None:
                    # Same type of path, just move the end point and don't reset the animation
                    if node_link.target_path_type == new_path_type:
                        # print("Update Animation")
                        node_link.target_path = self.granulate_path(new_path, len(node_link.target_path))
                    # Different type of path, reset the animation
                    else:
                        print("Reset Animation")
                        self.reset_link_animation(new_path, new_path_type, node_link)

            self.calling_animation_enable = True


        # TODO: Does this totally redraw everything? How does mark dirty work?
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

            if self.hover_over_link == link:
                link_color = (0.1, 1.0, 0.1, 1.0)
            else:
                link_color = (0.1, 0.7, 0.1, 1.0)


            if link.transition_path is None:
                link_path = link.path
            else:
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
        the_dirty = [0,0,0,0]

        for line_node in line_path:
            # Determine the area of this control which needs updating
            if line_node[0] < the_dirty[0]:
                the_dirty[0] = line_node[0]
            if line_node[0] > the_dirty[2]:
                the_dirty[2] = line_node[0] - the_dirty[0]

            if line_node[1] < the_dirty[1]:
                the_dirty[1] = line_node[1]
            if line_node[1] > the_dirty[3]:
                the_dirty[3] = line_node[1] - the_dirty[1]

            cr.get_group_target().mark_dirty_rectangle(int(the_dirty[0]), int(the_dirty[1]), int(the_dirty[2]), int(the_dirty[3]))

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


    def reset_link_animation(self, new_path, new_path_type, link):

        self.calling_animation_enable = False
        while (self.running_animation):
            pass

        assert (link.target_path_type is not None)
        link.target_path = self.granulate_path(new_path,GRANULATED_ANIMATION_PATH_SIZE)
        link.target_path_type = new_path_type
        link.old_path = self.granulate_path(link.transition_path, GRANULATED_ANIMATION_PATH_SIZE)
        link.old_path_type = "GARRY"

        # Find the index of the animation for this link and then reset the timer
        update_index = None
        for index, animation_item in enumerate(self.transition_links):
            if animation_item[0] == link:
                update_index = index
                break
        assert (update_index is not None)

        self.transition_links[update_index] = (link, time.time())

        assert(len(self.transition_links) != 0)

    def generate_link_animation(self, new_path, new_path_type, link):

        self.calling_animation_enable = False
        while (self.running_animation):
            pass

        assert(link.target_path is None)

        link.target_path = self.granulate_path(new_path, GRANULATED_ANIMATION_PATH_SIZE)
        link.target_path_type = new_path_type
        link.old_path = self.granulate_path(link.path, GRANULATED_ANIMATION_PATH_SIZE)
        link.old_path_type = link.path_type

        link.transition_path = [(0, 0)] * GRANULATED_ANIMATION_PATH_SIZE

        self.transition_links.append((link, time.time()))

        self.calling_animation_enable = True

        # The animation callback will stop if it runs out of work to do, call it directly to kick it off
        if self.animation_tick_enabled == False:
            self.animation_tick()


    def generate_node_animation(self, node):
        self.calling_animation_enable = False
        while (self.running_animation):
            pass

        assert(node not in self.transition_nodes)

        self.transition_nodes.append((node, time.time()))

        self.calling_animation_enable = True

        if self.animation_tick_enabled == False:
            self.animation_tick()

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
        # TODO: Remove when debugging is done
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

            start = 0
            end = len(link.target_path)

            if link.node_a.selected:
                link.transition_path[0] = link.target_path[0]
                start = start + 1

            if link.node_b.selected:
                link.transition_path[-1] = link.target_path[-1]
                end = end - 1

            for index in range(start, end):
                tx = link.target_path[index][0]
                ty = link.target_path[index][1]
                sx = link.old_path[index][0]
                sy = link.old_path[index][1]


                movement_angle = atan2(tx - sx, (ty-sy))
                movement_length = hypot(abs(tx - sx), abs(ty-sy))

                dy = cos(movement_angle) * (movement_length * animation_completion_perc)
                dx = sin(movement_angle) * (movement_length * animation_completion_perc)

                link.transition_path[index] = (sx + dx, sy + dy)

            # We can't modify the list while we're iterating over it, so add it to another list of items to
            # delete later on
            if animation_completion_perc >= 1.0:
                delete_link_animations.append((link, start_time))
                self.queue_draw()

        # Remove completed animations
        for link, ttime in delete_link_animations:
            link.path = link.target_path
            link.path_type = link.target_path_type
            link.old_path_type = None
            link.old_path = None
            link.transition_path = None
            link.target_path = None
            link.target_path_type = None
            self.transition_links.remove((link, ttime))

        # TODO: Remove when debugging is done
        self.cat = self.cat - 1


    def animation_tick(self):
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
            GObject.timeout_add(ANIMATION_TICK, self.animation_tick)
            self.animation_tick_enabled = True
        else:
            self.animation_tick_enabled = False

        self.running_animation = False

        # Below is useful for showing how long the animations take to process
        tend = time.time()
        tdiff = float(tend - tstart) * 1000
        # print("Animation Call took: %.2fms %s"  % (tdiff, 0))


    def granulate_path(self, source_path, target_node_count):
        source_path_count = len(source_path)
        if source_path_count == target_node_count:
            result = source_path.copy()
            assert(len(result) == target_node_count)
            return result
        if source_path_count > target_node_count:
            result = source_path.copy()[:target_node_count]
            assert(len(result) == target_node_count)
            return result
        if source_path_count < target_node_count:
            original_lengths = []
            node_shares = []
            previous_node = None

            # First we need to calculate the total pixel length of the entire link
            for node in source_path:
                if previous_node != None:
                    length = self.calc_distance(previous_node, node)
                    original_lengths.append(length)
                    node_shares.append(None)

                previous_node = node
            total_length = sum(original_lengths[:])

            # Every node in the original list is going to have at least 1 node. Therefore we will
            # split the remaining nodes (target_node_count - original_node_count) up amongst those who
            # deserve more
            starting_free_nodes = target_node_count - len(original_lengths)
            remaining_free_nodes = target_node_count - len(original_lengths) - 1
            for index, node in enumerate(original_lengths):
                node_perc = node/total_length

                node_share = round(starting_free_nodes * node_perc)

                if node_share > remaining_free_nodes:
                    node_share = remaining_free_nodes

                remaining_free_nodes = remaining_free_nodes - node_share

                node_shares[index] = 1 + node_share

            # If we have any remaining nodes, distribute them evenly
            if remaining_free_nodes > 0:
                rangy = range(0, len(node_shares), int(len(node_shares) / remaining_free_nodes))

                for index in rangy:
                    node_shares[index] = node_shares[index] + 1
                    remaining_free_nodes = remaining_free_nodes - 1

            assert(remaining_free_nodes == 0)

            # Now build the new granulated line
            new_path = []
            for index in range(source_path_count-1):
                start = source_path[index]
                end = source_path[index+1]
                segments = node_shares[index]
                original_length = None

                new_path = new_path + self.interpolate_line(start, end, segments, original_length, True)

            new_path = new_path + [source_path[-1]]


            # print()
            # print("Source        | New")
            # print("%2i            | %2i" % (len(source_path), len(new_path)))
            # print("--------------|----------------")
            # new_index = 0
            # for index in range(len(source_path)-1):
            #     print("%7.0f%7.0f|%7.0f%7.0f" % (source_path[index][0],source_path[index][1], new_path[new_index][0], new_path[new_index][1]))
            #     new_index = new_index + 1
            #     for cat in range(node_shares[index]-1):
            #         print("              |%7.0f%7.0f" % (new_path[new_index][0], new_path[new_index][1]))
            #         new_index = new_index + 1
            #     print("              |")
            #
            # print("%7.0f%7.0f|%7.0f%7.0f" % (source_path[-1][0],source_path[-1][1], new_path[-1][0], new_path[-1][1]))

            return new_path

    def interpolate_line(self, p1, p2, segments, original_length=None, skip_last=False):
        # Take two source coordinates and break it up into separate segments.
        # @param skip_last: Don't add p2 onto the end of this node, this makes
        #                   it suitable for a line path.
        if segments < 1:
            raise ValueError
        if segments == 1:
            if skip_last:
                return [p1]
            else:
                return [p1, p2]


        new_line_path = []

        tx = p1[0]
        ty = p1[1]
        sx = p2[0]
        sy = p2[1]

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

        if original_length is None:
            original_length = hypot(abs(tx - sx), abs(ty-sy))

        movement_amount = original_length / segments

        dx = tx
        dy = ty
        new_line_path.append((dx, dy))

        for _ in range(segments - 1):
            dx = dx - sin(movement_angle) * (movement_amount)
            dy = dy + cos(movement_angle) * (movement_amount)

            new_line_path.append((dx, dy))

        if not skip_last:
            new_line_path.append(p2)

        return new_line_path


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




