# Whey Station -- MIDDLE (world coords, point-symmetric: half() is built twice, the second time rotated 180 deg).
#  Vat Hall      x -30..30, z -24..24, floor 0, roof 16: six curd vats, brine pit (y -4) in the centre,
#                catwalks at y 6 along both long walls, a conveyor bridge across the pit.
#  Hallways      (Cheddar half, x -40..-30, Turbine-style L turns): main L-hallway z -4..10; gallery junction z 14..24
#                at y 6; brine-tank room z -24..-4 (ground + catwalk); brine tunnel x -40..-5 z -16..-12 at y -4.
import math
import wsparts
PI = math.pi
WT = 0.4          # wall thickness


def vat(K, x, z, r=3.0):
    """curd vat: concrete plinth, stainless drum, cone lid, rim ring, rim rings"""
    K.box('Conc', x - r - 0.3, 0, z - r - 0.3, x + r + 0.3, 0.5, z + r + 0.3)
    K.cyl('Stainless', x, 0.5, z, r, 5.0, seg=28)
    K.cyl('Stainless', x, 5.5, z, r, 1.3, seg=28, r2=0.9)
    K.cyl('SteelG', x, 5.3, z, r + 0.08, 0.2, seg=28)
    K.cyl('TF_Hazard', x, 1.0, z, r + 0.06, 0.25, seg=28)
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
    # ---------------- Vat Hall (west half; the rotated pass builds the east half): x -30..30, z -24..24, roof 16 ----------------
    K.slab('Epoxy', -30, -24, 0, 24, -0.3, 0.0, holes=[(-5, -8, 0, 8)])          # hall floor with the pit hole
    K.slab('CorrWorn', -30, -24, 0, 24, 16.0, 16.4, holes=[(-22, -6, -8, 6)], col=False)   # roof with skylight
    for x in (-22, -15):
        K.box('Glass', x, 16.05, -6, x + 7, 16.1, 6)
        P.hbeam(x, x + 7, 0, 16.0, d=0.25, w=0.12)
    for x in (-26, -19, -12, -5):
        P.hbeam(-24, 24, x, 15.9, d=0.6, w=0.3, axis='z')
    # long wall (north; rotated -> south), full length so both passes overlap cleanly
    WIN = (-26, -18, -10, -2, 6, 14, 22)
    K.wall2('x', -29.8, 29.8, 24, WT, 0, 16, holes=[(x0, x0 + 4, 11.5, 14.0) for x0 in WIN])
    for x0 in WIN:
        P.window('x', x0, x0 + 4, 24, WT, 11.5, 14.0, pane=1.0)
    for x in (-27.5, -20, -12, -4, 4, 12, 20, 27.5):
        K.box('TF_Conc', x - 0.35, 6.0, 23.4, x + 0.35, 16, 23.8)                    # pilasters
    # end wall (west; rotated -> east), full width z -24..24 (v1 stopped at +-20 and left a slot to the outside)
    K.wall2('z', -24, 24, -30, WT, 0, 16,
           holes=[(4, 10, 0, 4.5), (18.8, 23.5, 5.8, 9), (-23.5, -18.8, 5.8, 9), (-18, -14, 0, 3.2)])
    P.opening('z', 4, 10, -30, WT, 0, 4.5, mat=P.tm('SteelT'), w=0.18)
    P.opening('z', -18, -14, -30, WT, 0, 3.2, mat='Steel')
    P.opening('z', 18.8, 23.5, -30, WT, 6, 9, mat='Steel')
    P.opening('z', -23.5, -18.8, -30, WT, 6, 9, mat='Steel')
    # north catwalk (y 6), full length -- this is the Cheddar high route through the hall
    K.box('Plate', -30, 5.8, 18.8, 30, 6.0, 23.8, col=True, bevel=False)
    K.box('Steel', -30, 5.55, 18.75, 30, 5.8, 18.9)                                 # edge channel
    for (a, b) in ((-29.8, -9.1), (-6.9, -1.6), (1.6, 29.8)):
        P.rail(a, 18.85, b, 18.85, 6.0, panel=None)
    for x in (-24, -16, -3.5, 4.5, 16, 24):
        P.ibeam(x, 19.1, 0, 5.55, w=0.28)
    P.stairs(-8, 18.8 - 32 * 0.27, -PI / 2, 2.0, 0.0, 6.0, kind='steel')           # hall floor -> catwalk
    # conveyor bridge across the pit (x -1.5..1.5), north half z 0..18.8
    K.box('TF_Grate', -1.5, 5.8, 0, 1.5, 6.0, 18.8, col=True, bevel=False)
    for s in (-1, 1):
        K.box('Steel', s * 1.25 - 0.12, 5.25, 0, s * 1.25 + 0.12, 5.8, 18.8)
        P.rail(s * 1.55, 0, s * 1.55, 18.8, 6.0, panel=P.tm('TF_Paint'))
    P.ibeam(0, 10.0, 0, 5.25, w=0.3)
    # brine pit: channel x -5..5, z -16..16 at y -4 (open to the hall for |z|<8)
    K.slab('FloorDmg', -5, -16, 0, 16, -4.3, -4.0)
    K.wall('Precast', 'z', -16, 16, -5, WT, -4.0, 0.0, holes=[(-16, -12, -4.0, -1.0)])
    K.wall('Precast', 'x', -5, 5, 16, WT, -4.0, -0.3)
    K.box('Grate', -4.6, -4.02, -15.6, -0.2, -3.98, 15.6)
    P.stairs(-3.75, 8 - 21 * 0.27, -PI / 2, 2.0, -4.0, 0.0, kind='conc')            # clear of the pit wall
    P.rail(-5.05, -8, -5.05, 8, 0.0)
    P.rail(-3.0, 8.05, 5.0, 8.05, 0.0)
    K.box('TF_Hazard', -5.2, 0.0, -8.2, -4.95, 0.08, 8.2)
    K.box('TF_Hazard', -5.0, 0.0, 7.9, 5.0, 0.08, 8.2)
    # cover: vats and a pump skid
    vat(K, -18, 10.5); vat(K, -18, -10.5); vat(K, -10, -13.5, 2.4)
    # cover in the middle of each half: library barrels + crates (replaces the old home-made pump skid)
    for (x, z) in ((-13.0, -0.6), (-12.3, 0.2), (-13.4, 0.5)):
        K.prop('barrel', x, 0, z, 0, col=(-0.3, 0, -0.3, 0.3, 0.9, 0.3))
    K.prop('crate', -14.8, 0, -1.2, 0.2, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('crate', -14.8, 1.2, -1.2, 0.6, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('crate', -14.9, 0, 1.6, 0.9, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.light(-18, 14.5, 0, '#ffe7c4', 2.4, 34); K.light(-8, 4.5, 21, '#ffd9a8', 1.2, 14); K.light(0, -1.2, 0, '#bfe3ff', 1.0, 12)

    # ---------------- Cheddar-side hallways (x -40..-30), Turbine-style: nothing lines up with the base doors ----------------
    K.slab('Conc', -40, -24, -30, 24, 10.0, 10.3, col=False)                        # roof over the hallways
    K.wall2('x', -40, -30, -24, WT, 0, 10.0)                                 # outer walls
    K.wall2('x', -40, -30, 24, WT, 0, 10.0)
    K.wall2('z', 20, 24, -40, WT, 0, 10.0)                                   # closes the gap beside the base
    # MAIN: L-hallway. Base door (z -4..4) -> north leg -> hall door (z 4..10)
    K.slab('TF_Floor', -40, -4, -30, 10, -0.3, 0.0)
    K.slab('TF_Ceiling', -40, -4, -30, 10, 5.0, 5.3, col=False)
    K.wall2('x', -40, -30, -4, WT, 0, 10.0, holes=[(-39.5, -37, 0, 3.0)], lower='TF_Tile', band=1.4)
    P.opening('x', -39.5, -37, -4, WT, 0, 3.0, mat='Steel')
    K.wall2('z', -4, 4, -34, WT, 0, 10.0, lower='TF_Tile', band=1.4)                   # the corner that blocks the sightline
    K.wall2('x', -40, -30, 10, WT, 0, 10.0, lower='TF_Tile', band=1.4)
    K.light(-37, 4.6, 0, '#ffe0b0', 1.0, 10); K.light(-33, 4.6, 7, '#ffe0b0', 1.0, 10)
    K.area('Main Hallway', -40, -4, -30, 10, 0, team=T)
    # HIGH: gallery room (y 6) from the base conveyor gallery (z 15.2..19.8) to the hall catwalk (z 18.8..23.8)
    K.wall2('x', -40, -30, 14, WT, 0, 10.0)
    K.box('TF_Grate', -40, 5.8, 14.2, -30, 6.0, 23.8, col=True, bevel=False)
    K.light(-35, 9.4, 19, '#ffe0b0', 1.0, 10)
    K.area('Gallery Junction', -40, 14, -30, 24, 6, team=T)
    # brine-tank room (ground + catwalk), z -24..-4: Cheddar's own room on the way back from the high route
    K.slab('Epoxy', -40, -24, -30, -4, -0.3, 0.0)
    K.box('Plate', -36.2, 5.8, -23.8, -30, 6.0, -13.64, col=True, bevel=False)
    P.rail(-36.25, -23.8, -36.25, -13.64, 6.0)
    P.rail(-34.0, -13.6, -30.2, -13.6, 6.0)
    P.ibeam(-35.9, -16, 0, 5.8, w=0.28)
    P.stairs(-35, -5.0, PI / 2, 2.0, 0.0, 6.0, kind='steel')                         # z -5 -> -13.64 at x -36..-34
    for (x, z, r, h) in ((-38.2, -21.0, 1.4, 6.5), (-32.0, -8.0, 1.5, 7.0)):
        K.cyl('Conc', x, 0, z, r + 0.25, 0.4, seg=20)
        K.cyl('Stainless', x, 0.4, z, r, h, seg=20, col=True)
        K.cyl('Stainless', x, 0.4 + h, z, r, 0.6, seg=20, r2=0.4)
    K.light(-35, 8.8, -14, '#d8ecff', 1.1, 14)
    K.area('Brine Tanks', -40, -24, -30, -4, 0, team=T)
    # brine tunnel (LOW route) x -40..-5, z -16..-12, y -4 -- ceiling is the floor above
    K.slab('FloorDmg', -40, -16, -5, -12, -4.3, -4.0)
    K.wall('Ribbed', 'x', -40, -5, -16, WT, -4.0, -0.3)
    K.wall('Ribbed', 'x', -40, -5, -12, WT, -4.0, -0.3)
    K.box('Grate', -39.6, -4.02, -14.5, -5.4, -3.98, -13.5)
    for x in (-34, -22, -10):
        K.light(x, -0.8, -14, '#9fd0ff', 0.8, 9)


def middle(K):
    for rot, T in ((0.0, 'C'), (PI, 'B')):
        K.at(0, 0, 0, rot); half(K, T); K.pop()
