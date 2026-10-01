# Whey Station -- shared layout constants (game frame: X right, Y up, Z lateral, metres).
#  Cheddar base: base-local frame placed at x=-76 facing +x.  Bleu: same base rotated 180 deg at x=+76.
#  Middle: x -40..40 (Vat Hall -30..30 + Turbine-style hallways), point-symmetric about the origin.
#  Levels: -4 brine tunnels (LOW route), 0 ground (MAIN route), 6 conveyor galleries + hall catwalks (HIGH route).
import math
PI = math.pi
FLOORS = [-4.0, 0.0, 6.0]
BASE_FRAME = {'C': (-76.0, 0.0), 'B': (76.0, PI)}
SPAWNS = {'C': [-71.0, 0.1, 0.0], 'B': [71.0, 0.1, 0.0]}
FLAG_LOCAL = (21.0, 0.3, -15.0)          # flag plinth in base-local coords
FLAGS = {'C': [-55.0, 0.3, -15.0], 'B': [55.0, 0.3, 15.0]}
# timing waypoints (world) for the three routes, Cheddar attacking Bleu
ROUTES = {
    'main': [[-71, 0, 0], [-37, 0, 0], [-37, 0, 7], [-28, 0, 7], [0, 0, 11], [28, 0, -7], [37, 0, -7], [37, 0, 0],
             [62, 0, 0], [62, 0, 8], [55, 0.3, 15]],
    'high': [[-71, 0, 0], [-74.5, 6, 16], [-36, 6, 17.5], [-34, 6, 21], [-28, 6, 21], [29, 6, 21], [33, 6, 16],
             [35, 6, 14.5], [35, 0, 4.5], [38, 0, 11.5], [44, 0, 11.5], [55, 0.3, 15]],
    'low':  [[-71, 0, 0], [-72, -4, -9], [-30, -4, -14], [0, -4, 0], [30, -4, 14], [46, -4, 15], [51, -1, 15], [55, 0.3, 15]],
}
