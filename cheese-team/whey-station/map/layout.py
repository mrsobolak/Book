# Whey Station -- shared layout constants (game frame: X right, Y up, Z lateral, metres).
#  Cheddar base: base-local frame placed at x=-76 facing +x.  Bleu: same base rotated 180 deg at x=+76.
#  Middle: x -40..40, point-symmetric about the origin.
#  Levels: -4 brine tunnels (LOW route), 0 ground (MAIN route), 6 conveyor galleries + hall catwalks (HIGH route).
import math
PI = math.pi
FLOORS = [-4.0, 0.0, 6.0]
BASE_FRAME = {'C': (-76.0, 0.0), 'B': (76.0, PI)}
SPAWNS = {'C': [-71.0, 0.1, 0.0], 'B': [71.0, 0.1, 0.0]}
FLAG_LOCAL = (20.0, 0.3, -19.0)          # flag plinth in base-local coords
FLAGS = {'C': [-56.0, 0.3, -19.0], 'B': [56.0, 0.3, 19.0]}
# timing waypoints (world) for the three routes, Cheddar attacking Bleu
ROUTES = {
    'main': [[-71, 0, 0], [-30, 0, 0], [0, 0, 11], [30, 0, 0], [62, 0, 0], [62, 0, 8], [56, 0, 19]],
    'high': [[-71, 0, 0], [-75, 6, 17], [-30, 6, 17.5], [0, 6, 17.5], [30, 6, -17.5]][:0] or
            [[-71, 0, 0], [-74.5, 6, 17], [-30, 6, 17.5], [20, 6, 17.5], [33, 0, 17.5], [44, 0, 16], [56, 0, 19]],
    'low':  [[-71, 0, 0], [-72, -4, -9], [-30, -4, -14], [0, -4, 0], [30, -4, 14], [46, -4, 15], [53, 0, 15], [56, 0, 19]],
}
