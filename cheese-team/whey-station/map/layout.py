# Whey Station (v2, simple TF2-style layout) -- shared constants. Game frame: X right, Y up, Z lateral, metres.
#  Base (local d 0..44 toward the middle, z -19..19): Spawn d0-12 | vestibule d12-16 | FLAG ROOM d16-44 z-13..13.
#  Cheddar base at x=-72 facing +x; Bleu = same base rotated 180 deg at x=+72. Middle hall x -28..28, z -19..19.
#  Levels: -4 bottom corridor (LOW), 0 ground (MAIN), 6 upper corridor / catwalks (HIGH).
import math
PI = math.pi
FLOORS = [-4.0, 0.0, 6.0]
BASE_FRAME = {'C': (-72.0, 0.0), 'B': (72.0, PI)}
SPAWNS = {'C': [-66.0, 0.1, 14.0], 'B': [66.0, 0.1, -14.0]}
FLAGS = {'C': [-60.0, 0.5, -11.0], 'B': [60.0, 0.5, 11.0]}
ROUTES = {   # Cheddar attacking the Bleu flag (Bleu base = Cheddar base rotated: world = (72 - d, -z))
    'main': [[-66, 0, 14], [-58, 0, 13.5], [-36, 0, 11], [-34, 0, 7], [-29, 0, 6], [-27, 0, 0], [0, 0, 5.5], [27, 0, 0],
             [31, 0, 6.5], [36, 0, 11], [44, 0, 14], [60, 0.5, 11]],
    'high': [[-66, 0, 14], [-58, 0, 13.5], [-46, 0, 11], [-38, 6, 11.5], [-30, 6, 16], [0, 6, 16], [0, 6, -16],
             [28, 6, -16], [49, 6, -16], [49, 6, 0], [49, 6, 5], [60, 0.5, 11]],
    'low':  [[-66, 0, 14], [-67.5, 0, 9], [-61.5, 0, -3], [-50, 0, -10], [-46, -4, -16], [-28, -4, -14.5], [0, -4, -14.5],
             [0, -4, 14.5], [28, -4, 14.5], [46, -4, 14.5], [52, 0, 16], [60, 0.5, 11]],
}
