# Rind Ridge -- payload map (game frame: X east, Y up, Z north... as three.js; metres).
# BLEU pushes a giant cheese wheel on a rail bogie from the canyon floor (SW) up and around the mesa to the summit,
# where CHEDDAR defends the Grater. One round, 4 checkpoints + the final (A ranch, B mine yard, C sawmill, D north-face switchback, FINAL the Grater).
import math
MESA = (0.0, 15.0)            # mesa centre (x, z); summit plateau radius 40 at y 37
PLATEAU_R, PLATEAU_Y, FOOT_R = 40.0, 37.0, 150.0
# track control points (x, z, y) and segment kinds for what follows each point
TRACK = [
    (-172, -122, 0.0, 'ground'),     # Bleu start (barn yard)
    (-135, -126, 0.4, 'ground'),
    (-98, -120, 2.2, 'ground'),
    (-70, -114, 3.6, 'ground'),      # A  -- the ranch
    (-42, -110, 5.4, 'cut'),
    (-12, -108, 7.6, 'shed'),        # rock cut through Hogback Hill, timber sheds over the deep part
    (18, -102, 9.6, 'shed'),
    (44, -92, 11.4, 'cut'),
    (66, -78, 12.8, 'ground'),       # B  -- the mine yard
    (88, -58, 14.6, 'ground'),
    (102, -38, 16.4, 'bridge'),      # Gully trestle
    (108, -12, 18.6, 'bridge'),
    (106, 14, 20.8, 'ground'),
    (96, 40, 22.8, 'ground'),        # C  -- the sawmill
    (74, 66, 24.8, 'ground'),
    (44, 86, 27.0, 'ground'),        # the spiral up the north face
    (8, 92, 29.2, 'ground'),
    (-26, 80, 31.4, 'ground'),
    (-50, 56, 33.4, 'ground'),
    (-58, 26, 35.2, 'ground'),
    (-46, 0, 36.6, 'ground'),
    (-20, -8, 37.4, 'ground'),
    (6, -2, 37.4, 'end'),           # D  -- the Grater
]
CHECKPOINT_IDX = {'A': 3, 'B': 8, 'C': 13, 'D': 18, 'FINAL': 22}
TEAM = {'attack': 'B', 'defend': 'C'}
