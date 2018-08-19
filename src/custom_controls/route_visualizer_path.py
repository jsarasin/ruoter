from .route_visualizer import *

class RouteVisualizerLinkPath:
    def __init__(self, model, node_a, node_b):
        self.path = []
        self.model = model
        self.node_a = node_a
        self.node_b = node_b

        self.path_type = None       # An ID for which type of path is being used right now

        self.target_path_type = None
        self.target_path = None     # Used for specifying where the animation will ultimately go.
        self.old_path = None        # Used for where the animation is coming from
        self.old_path_type = None   # Same as before but the previous one
        self.transition_path = None # Used for where the animation is right now, Calculated from between the top two


        self.flow_last_seen = None

        self.build_path = []

    def add_straight(self, x, y):
        self.build_path.append((x, y))

    def add_curved(self, x, y, cx, cy):
        curved_tuple = (x, y, cx, cy)
        self.build_path.append(curved_tuple)

    def mouse_over_link(self, x, y):
        # TODO: Make this work with not vert/horz lines
        LINK_WIDTH = 3
        for index in range(len(self.path)-1):
            x1 = min(self.path[index][0], self.path[index+1][0]) - LINK_WIDTH
            x2 = max(self.path[index][0], self.path[index+1][0]) + LINK_WIDTH
            y1 = min(self.path[index][1], self.path[index+1][1]) - LINK_WIDTH
            y2 = max(self.path[index][1], self.path[index+1][1]) + LINK_WIDTH

            if x > x1 and x < x2 and y > y1 and y < y2:
                return True

        return False

    def gen_path(self):
        # Generate a path between two nodes that's pretty

        # There is another route finding option i have disabled here until the transitions are working nicer
        EDGE_ACCOMODATE_CURVE_PERCENT = 1.0
        # EDGE_ACCOMODATE_CURVE_PERCENT = 1.0

        if self.node_b.posx > self.node_a.posx:
            dx = 1
        else:
            dx = -1

        if self.node_b.posy > self.node_a.posy:
            dy = 1
        else:
            dy = -1

        horizontal_offset = abs(self.node_a.posx - self.node_b.posx)
        vertical_offset = abs(self.node_a.posy - self.node_b.posy)
        # TODO: Handle overlapping nodes nicely

        # If the nodes are horizontally aligned up to EDGE_ACCOMODATE_CURVE_PERCENT%: Straight line from center of node A
        if vertical_offset < HALF_HEIGHT * EDGE_ACCOMODATE_CURVE_PERCENT:
            self.build_path = []
            self.add_straight(self.node_a.posx + (HALF_WIDTH * dx), self.node_a.posy)
            self.add_straight(self.node_b.posx - (HALF_WIDTH * dx), self.node_a.posy)
            return (self.build_path, 1)

        # if the nodes are horizontally aligned over EDGE_ACCOMODATE_CURVE_PERCENT%: Offset line offset from center of node A
        if vertical_offset >= HALF_HEIGHT * EDGE_ACCOMODATE_CURVE_PERCENT and vertical_offset < HALF_HEIGHT and EDGE_ACCOMODATE_CURVE_PERCENT < 1.0:
            self.build_path = []
            vertical_offset_correct = (HALF_HEIGHT * EDGE_ACCOMODATE_CURVE_PERCENT - vertical_offset) * dy * -1
            self.add_straight(self.node_a.posx + (HALF_WIDTH * dx), self.node_a.posy + (vertical_offset_correct))
            self.add_straight(self.node_b.posx - (HALF_WIDTH * dx), self.node_a.posy + (vertical_offset_correct))
            return (self.build_path, 2)

        # If the nodes are vertically aligned up to EDGE_ACCOMODATE_CURVE_PERCENT%: Straight line from center of node A
        if horizontal_offset < HALF_WIDTH * EDGE_ACCOMODATE_CURVE_PERCENT:
            self.build_path = []
            self.add_straight(self.node_a.posx, self.node_a.posy + (HALF_HEIGHT * dy))
            self.add_straight(self.node_a.posx, self.node_b.posy- (HALF_HEIGHT * dy))
            return (self.build_path, 3)

        # if the nodes are vertically aligned over EDGE_ACCOMODATE_CURVE_PERCENT%: Offset line offset from center of node A
        if horizontal_offset >= HALF_WIDTH * EDGE_ACCOMODATE_CURVE_PERCENT and horizontal_offset < HALF_WIDTH and EDGE_ACCOMODATE_CURVE_PERCENT < 1.0:
            self.build_path = []
            horizontal_offset_correct = (HALF_WIDTH * EDGE_ACCOMODATE_CURVE_PERCENT - horizontal_offset) * dx * -1
            self.add_straight(self.node_a.posx + (horizontal_offset_correct), self.node_a.posy + (HALF_HEIGHT * dy))
            self.add_straight(self.node_a.posx + (horizontal_offset_correct), self.node_b.posy- (HALF_HEIGHT * dy))
            return (self.build_path, 4)

        # If the nodes are neither horz or vert aligned yet far enough apart on the horz plane to accommodate curves...
        # If the horizontal offset is greater than two curve sizes
        if horizontal_offset - NODE_WIDTH > LINK_CURVE * 2 and vertical_offset > HALF_HEIGHT:
            self.build_path = []
            middle_point = self.node_a.posx + (((horizontal_offset) / 2) * dx)
            self.add_straight(self.node_a.posx + (HALF_WIDTH * dx), self.node_a.posy)
            self.add_straight(middle_point + (LINK_CURVE * dx * -1), self.node_a.posy)
            self.add_curved(middle_point, self.node_a.posy,
                            middle_point, self.node_a.posy + (LINK_CURVE * dy))
            self.add_straight(middle_point, self.node_b.posy + (LINK_CURVE * dy * -1))
            self.add_curved(middle_point, self.node_b.posy,
                            middle_point + (LINK_CURVE * dx), self.node_b.posy)
            self.add_straight(self.node_b.posx + (HALF_WIDTH * dx * -1), self.node_b.posy)
            return (self.build_path, 5)

        # If the horizontal offset is smaller than two curve sizes
        if horizontal_offset - NODE_WIDTH <= LINK_CURVE * 2 and vertical_offset > HALF_HEIGHT:
            self.build_path = []
            self.add_straight(self.node_a.posx + (HALF_WIDTH * dx), self.node_a.posy)
            self.add_straight(self.node_b.posx + (LINK_CURVE * dx * -1), self.node_a.posy)
            self.add_curved(self.node_b.posx, self.node_a.posy,
                            self.node_b.posx, self.node_a.posy + (LINK_CURVE * dy))
            self.add_straight(self.node_b.posx, self.node_b.posy + (HALF_HEIGHT * dy * -1))
            return (self.build_path, 6)
