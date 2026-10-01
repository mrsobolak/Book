# Rind Ridge -- payload map (game frame: X east, Y up, Z north; metres).
# CHEDDAR (orange) pushes a giant cheese wheel on a rail bogie from their bunker in the south canyon wall, past the
# ranch (A), through the Hogback cut to the mine yard (B), over the gully trestle to the sawmill (C), round the mesa's
# west face (D) and up the final switchbacks to the summit, where BLEU defends the Grater from a bunker built into
# the summit spire. Track heights are derived from the ground (max grade 9 %, never downhill); trestles appear
# wherever the ground falls away more than 3.5 m under the track.
MESA = (0.0, 15.0)                # mesa centre (x, z)
PLATEAU_R, PLATEAU_Y, FOOT_R = 42.0, 60.0, 172.0
SPIRE = (-6.0, 44.0, 14.0, 34.0)  # summit spire: centre x, z, radius, height above the plateau
# track control points (x, z, kind); kind applies to the stretch that follows
TRACK = [
    (-178, -128, 'ground'), (-150, -127, 'ground'), (-112, -121, 'ground'),
    (-74, -114, 'ground'),          # A  -- the ranch
    (-44, -110, 'cut'), (-14, -108, 'shed'), (16, -102, 'shed'), (42, -92, 'cut'),
    (64, -78, 'ground'),            # B  -- the mine yard
    (86, -58, 'ground'), (100, -34, 'ground'), (106, -8, 'ground'), (104, 18, 'ground'),
    (94, 44, 'ground'),             # C  -- the sawmill
    (74, 70, 'ground'), (46, 90, 'ground'), (12, 100, 'ground'), (-24, 96, 'ground'), (-56, 80, 'ground'),
    (-78, 54, 'ground'), (-88, 22, 'ground'),
    (-84, -10, 'ground'),           # D  -- the west face overlook
    (-66, -38, 'ground'), (-38, -56, 'ground'), (-4, -62, 'ground'), (30, -56, 'ground'), (56, -36, 'ground'),
    (68, -6, 'ground'), (64, 24, 'ground'), (46, 48, 'ground'), (18, 60, 'ground'),
    (-14, 58, 'ground'), (-38, 40, 'ground'), (-42, 14, 'ground'), (-24, -4, 'ground'),
    (4, -6, 'end'),                 # FINAL -- the Grater
]
CHECKPOINT_IDX = {'A': 3, 'B': 8, 'C': 13, 'D': 21, 'FINAL': len(TRACK) - 1}
TEAMS = {'attack': 'C', 'defend': 'B'}
MAX_GRADE = 0.09
# flattened pads for buildings: name -> (x0, z0, x1, z1, y or None = ground at the centre, alcove?)
#  alcove pads are cut straight into a cliff (no blend: the rock rises sheer round the building)
PADS = {
    'cheddar_spawn': (-196, -170, -168, -147, 2.3, True),     # Cheddar's bunker in the south canyon wall
    'ranch':         (-96, -102, -74, -86, None, False),       # Cheddar forward spawn after A (the barn)
    'mine':          (68, -108, 90, -93, None, False),         # Bleu forward spawn until B (mine head house)
    'sawmill':       (60, 26, 80, 44, None, False),            # Cheddar forward spawn after C
    'bleu_spawn':    (-16, 25, 4, 40, 60.0, True),             # Bleu's bunker in the summit spire
}
