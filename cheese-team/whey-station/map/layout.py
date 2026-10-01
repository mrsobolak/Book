# Whey Station v4 (simple) -- shared constants. Game frame: X right, Y up, Z lateral, metres.
#  Base (local d 0..36 toward the middle, z -16..16): FLAG ROOM d0-18 (spawn in its back corner) | FRONT ROOM d18-36.
#  Cheddar base at x=-64 facing +x; Bleu = same base rotated 180 deg at x=+64. Middle hall x -28..28, z -16..16.
#  Three lanes: MAIN ground doors, HIGH bridge (y 6) straight through the middle, LOW tunnel (y -4) under it, z -9..-5 / cross / 5..9.
import math
PI = math.pi
FLOORS = [-4.0, 0.0, 6.0]
BASE_FRAME = {'C': (-64.0, 0.0), 'B': (64.0, PI)}
SPAWNS = {'C': [-60.0, 0.1, 12.5], 'B': [60.0, 0.1, -12.5]}
FLAGS = {'C': [-56.0, 0.5, 0.0], 'B': [56.0, 0.5, 0.0]}
ROUTES = {   # Cheddar attacking the Bleu flag (Bleu base = Cheddar base rotated: world = (64 - d, -z))
    'main': [[-60, 0, 12.5], [-56.5, 0, 8], [-46, 0, -7.5], [-28, 0, -6], [-28, 0, 0], [28, 0, 0], [46, 0, 7.5], [56, 0.5, 0]],
    'high': [[-60, 0, 12.5], [-56.5, 0, 8], [-60, 0, 4], [-52, 6, 4], [-50, 6, 0], [28, 6, 0], [50, 6, 0], [52, 6, -4],
             [60, 0, -4], [56, 0.5, 0]],
    'low':  [[-60, 0, 12.5], [-56.5, 0, 8], [-55, 0, -5], [-55, 0, -7], [-48, -4, -7], [-28, -4, -7], [0, -4, -7],
             [0, -4, 7], [48, -4, 7], [55, 0, 7], [56, 0.5, 0]],
}
