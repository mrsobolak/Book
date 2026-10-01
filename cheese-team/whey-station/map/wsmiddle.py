# Whey Station -- MIDDLE (world coords, point-symmetric: half() is built twice, the second time rotated 180 deg).
#  Vat Hall      x -24..24, z -20..20, floor 0, roof 14: four curd vats, brine pit (y -4) in the centre,
#                catwalks at y 6 along both long walls, a conveyor bridge across the pit.
#  Connectors    (Cheddar half) main corridor x -40..-24 z -4..4; conveyor gallery x -40..-24 z 15..20 at y 6;
#                brine-tank room x -40..-24 z -24..-4 (ground + catwalk); brine tunnel x -40..-5 z -16..-12 at y -4.
import math
import wsparts
PI = math.pi
WT = 0.4          # wall thickness


def vat(K, x, z, r=3.0):
    """curd vat: concrete plinth, stainless drum, cone lid, agitator motor, rim ring, legs of pipework"""
    K.box('Conc', x - r - 0.3, 0, z - r - 0.3, x + r + 0.3, 0.5, z + r + 0.3)
    K.cyl('Stainless', x, 0.5, z, r, 5.0, seg=28)
    K.cyl('Stainless', x, 5.5, z, r, 1.3, seg=28, r2=0.9)
    K.cyl('SteelG', x, 5.3, z, r + 0.08, 0.2, seg=28)
    K.cyl('SteelG', x, 1.0, z, r + 0.06, 0.12, seg=28)
    K.box('SteelPlate', x - 0.6, 6.8, z - 0.5, x + 0.6, 7.6, z + 0.5)
    K.cyl('Steel', x, 7.6, z, 0.12, 6.4, seg=8)                        # drive shaft up to the roof beams
    K.cyl('Stainless', x + r * 0.7, 0.5, z + r * 0.7, 0.18, 4.5, seg=10)   # outlet pipe
    # collision: octagon of three boxes
    a, b = r * 0.94 + 0.3, r * 0.39 + 0.3
    for (u, v) in ((a, b), (b, a), (r * 0.72 + 0.25, r * 0.72 + 0.25)):
        K.col(x - u, 0, z - v, x + u, 6.8, z + v)


def pump_skid(K, x, z):
    K.box('Conc', x - 1.6, 0, z - 2.0, x + 1.6, 0.25, z + 2.0, col=True)
    K.box('SteelPlate', x - 1.2, 0.25, z - 1.6, x + 1.2, 0.45, z + 1.6)
    K.cyl('SteelT_C' if x < 0 else 'SteelT_B', x, 0.45, z - 0.8, 0.55, 1.1, axis='y', seg=16)
    K.cyl('Steel', x - 0.9, 1.1, z + 0.6, 0.45, 1.8, axis='x', seg=16)
    K.box('Steel', x - 0.5, 0.45, z + 0.1, x + 0.5, 1.6, z + 1.4)
    K.col(x - 1.3, 0.25, z - 1.7, x + 1.3, 1.65, z + 1.7)


def half(K, T):
    P = wsparts.Parts(K, T)
    # ---------------- Vat Hall (west half; the rotated pass builds the east half) ----------------
    K.slab('Epoxy', -24, -20, 0, 20, -0.3, 0.0, holes=[(-5, -8, 0, 8)])          # hall floor with the pit hole
    K.slab('CorrWorn', -24, -20, 0, 20, 14.0, 14.4, holes=[(-19, -6, -13, 6)], col=False)   # roof with skylight
    for x in (-19, -13):
        K.box('Glass', x, 14.05, -6, x + 6, 14.1, 6)
        P.hbeam(x, x + 6, 0, 14.0, d=0.25, w=0.12)
    for x in (-21, -15, -9, -3):
        P.hbeam(-20, 20, x, 13.9, d=0.6, w=0.3, axis='z')
    # long wall (north; rotated -> south)
    WIN = (-21, -13, -5, 3, 11, 19)
    K.wall('Brick', 'x', -23.8, 23.8, 20, WT, 0, 14, holes=[(x0, x0 + 4, 10.4, 12.6) for x0 in WIN])
    for x0 in WIN:
        P.window('x', x0, x0 + 4, 20, WT, 10.4, 12.6, pane=1.0)
    # end wall (west; rotated -> east)
    K.wall('Brick', 'z', -20, 20, -24, WT, 0, 14,
           holes=[(-4, 4, 0, 4.5), (15.2, 19.8, 6, 9), (-19.8, -15.2, 6, 9), (-12, -8, 0, 3.2)])
    P.opening('z', -4, 4, -24, WT, 0, 4.5, mat=P.tm('SteelT'), w=0.18)
    P.opening('z', -12, -8, -24, WT, 0, 3.2, mat='Steel')
    P.opening('z', 15.2, 19.8, -24, WT, 6, 9, mat='Steel')
    P.opening('z', -19.8, -15.2, -24, WT, 6, 9, mat='Steel')
    # pilasters on the long wall
    for x in (-22.5, -14.5, -7.5, 0.5, 8.5, 16.5):
        K.box('Brick', x - 0.35, 6.0, 19.4, x + 0.35, 14, 19.8)
    # north catwalk (y 6), full length -- this is the Cheddar high route through the hall
    K.box('Plate', -24, 5.8, 15, 24, 6.0, 19.8, col=True, bevel=False)
    K.box('Steel', -24, 5.55, 14.95, 24, 5.8, 15.1)                                 # edge channel
    for (a, b) in ((-23.8, -9.1), (-6.9, -1.6), (1.6, 23.8)):
        P.rail(a, 15.05, b, 15.05, 6.0, panel=None)
    for x in (-20, -13, -3.5, 4.5, 13, 20):
        P.ibeam(x, 15.3, 0, 5.55, w=0.28)
    # stair hall floor -> north catwalk (ascends +z, top end lands on the catwalk edge at z=15)
    P.stairs(-8, 15 - 32 * 0.27, -PI / 2, 2.0, 0.0, 6.0, kind='steel')
    # conveyor bridge across the pit (x -1.5..1.5), north half z 0..15
    K.box('Plate', -1.5, 5.8, 0, 1.5, 6.0, 15, col=True, bevel=False)
    for s in (-1, 1):
        K.box('Steel', s * 1.25 - 0.12, 5.25, 0, s * 1.25 + 0.12, 5.8, 15)               # girders
        P.rail(s * 1.55, 0, s * 1.55, 15, 6.0, panel='Plate')
    K.box('SteelG', -0.55, 6.0, 0, 0.55, 6.35, 15, col=True)                          # conveyor belt bed (low cover)
    for z in range(1, 15, 2):
        K.cyl('Steel', -0.5, 6.25, z, 0.07, 1.0, axis='x', seg=8)
    P.ibeam(0, 9.0, 0, 5.25, w=0.3)
    # brine pit: channel x -5..5, z -16..16 at y -4 (open to the hall for |z|<8)
    K.slab('FloorDmg', -5, -16, 0, 16, -4.3, -4.0)
    K.wall('Precast', 'z', -16, 16, -5, WT, -4.0, 0.0, holes=[(-16, -12, -4.0, -1.0)])
    K.wall('Precast', 'x', -5, 5, 16, WT, -4.0, -0.3)
    K.box('Grate', -4.6, -4.02, -15.6, -0.2, -3.98, 15.6)                             # drain gratings in the bed
    P.stairs(-4, 8 - 21 * 0.27, -PI / 2, 2.0, -4.0, 0.0, kind='conc')                    # pit stair -> hall floor (top at z=8)
    P.rail(-5.05, -8, -5.05, 8, 0.0)
    P.rail(-3.0, 8.05, 5.0, 8.05, 0.0)
    K.box('SafetyY', -5.2, 0.0, -8.2, -4.9, 0.08, 8.2)
    K.box('SafetyY', -5.0, 0.0, 7.9, 5.0, 0.08, 8.2)
    # cover: vats and a pump skid
    vat(K, -14, 8.5); vat(K, -14, -8.5)
    pump_skid(K, -11, 0)
    K.light(-14, 12.5, 0, '#ffe7c4', 2.2, 30); K.light(-6, 4.5, 17.5, '#ffd9a8', 1.2, 14); K.light(0, -1.2, 0, '#bfe3ff', 1.0, 12)

    # ---------------- Cheddar-side connectors (x -40..-24) ----------------
    # main corridor
    K.slab('Epoxy', -40, -4, -24, 4, -0.3, 0.0)
    K.slab('Conc', -40, -4, -24, 4, 5.0, 5.3, col=False)
    K.wall('TileW', 'x', -40, -24, 4, WT, 0, 5.0)
    K.wall('TileW', 'x', -40, -24, -4, WT, 0, 10.0, holes=[(-34, -31, 0, 3.0)])
    P.opening('x', -34, -31, -4, WT, 0, 3.0, mat='Steel')
    for x in (-38, -31, -27):
        K.cyl('Steel', x, 4.55, -3.4, 0.16, 0.0001 + 0.0, axis='y', seg=6) if False else None
    K.cyl('SteelG', -40, 4.5, 3.3, 0.18, 16, axis='x', seg=10)
    K.cyl('Steel', -40, 4.5, 2.7, 0.12, 16, axis='x', seg=8)
    K.light(-32, 4.6, 0, '#ffe0b0', 1.0, 10)
    # conveyor gallery (y 6)
    K.box('Plate', -40, 5.8, 15, -24, 6.0, 20, col=True, bevel=False)
    K.wall('Brick', 'x', -40, -24, 15, WT, 0, 10.0)
    K.wall('Brick', 'x', -40, -24, 20, WT, 0, 10.0)
    K.box('SteelG', -40, 6.0, 18.3, -24, 6.85, 19.6, col=True)                       # conveyor = low cover
    for x in range(-39, -24, 2):
        K.cyl('Steel', x, 6.75, 18.35, 0.06, 1.2, axis='z', seg=6)
    K.light(-32, 9.4, 17.5, '#ffe0b0', 1.0, 10)
    K.slab('Conc', -40, -24, -24, 20, 10.0, 10.3, col=False)                        # roof over the connectors
    # brine-tank room (ground + catwalk): Cheddar's own room on the way back from the high route
    K.slab('Epoxy', -40, -24, -24, -4, -0.3, 0.0)
    K.wall('Brick', 'x', -40, -24, -24, WT, 0, 10.0)
    K.box('Plate', -29, 5.8, -20, -24, 6.0, -15, col=True, bevel=False)
    P.rail(-29, -15.05, -24, -15.05, 6.0)
    P.rail(-29.05, -20, -29.05, -18.6, 6.0); P.rail(-29.05, -16.4, -29.05, -15, 6.0)
    P.ibeam(-28.8, -15.3, 0, 5.8, w=0.28)
    P.stairs(-29 - 32 * 0.27, -17.5, 0, 2.0, 0.0, 6.0, kind='steel')
    for (x, z, r, h) in ((-35, -21.4, 1.6, 6.5), (-28.6, -8.2, 1.8, 7.0)):
        K.cyl('Conc', x, 0, z, r + 0.25, 0.4, seg=20)
        K.cyl('Stainless', x, 0.4, z, r, h, seg=20, col=True)
        K.cyl('Stainless', x, 0.4 + h, z, r, 0.6, seg=20, r2=0.4)
        K.cyl('Steel', x, 0.4 + h + 0.6, z, 0.1, 9.5 - h - 1.0, seg=8)
    K.light(-32, 8.8, -14, '#d8ecff', 1.1, 14)
    # brine tunnel (LOW route) x -40..-5, z -16..-12, y -4 -- ceiling is the floor above
    K.slab('FloorDmg', -40, -16, -5, -12, -4.3, -4.0)
    K.wall('Ribbed', 'x', -40, -5, -16, WT, -4.0, -0.3)
    K.wall('Ribbed', 'x', -40, -5, -12, WT, -4.0, -0.3)
    K.cyl('SteelG', -40, -1.0, -15.5, 0.2, 35, axis='x', seg=10)
    K.cyl('Rust', -40, -1.5, -15.4, 0.12, 35, axis='x', seg=8)
    K.box('Grate', -39.6, -4.02, -14.5, -5.4, -3.98, -13.5)
    for x in (-34, -22, -10):
        K.light(x, -0.8, -14, '#9fd0ff', 0.8, 9)


def middle(K):
    for rot, T in ((0.0, 'C'), (PI, 'B')):
        K.at(0, 0, 0, rot); half(K, T); K.pop()
