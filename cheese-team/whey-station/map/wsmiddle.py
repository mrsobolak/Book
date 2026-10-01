# Whey Station v2 -- MIDDLE HALL (world coords, point-symmetric: half() is built twice, the 2nd time rotated 180 deg).
#   Big hall x -28..28, z -19..19, ceiling 14. Floor: two cheese vats, a crate stack per side, the central curd press
#   (blocks the spawn-to-spawn line). Catwalks (y 6): north one x -28..3 (Cheddar's), south one x -3..28 (Bleu's),
#   joined by a bridge x -2..2 over the press -> a Z-shaped high route with no straight sniper lane.
#   Under the floor (y -4): Cheddar's corridor z -13..-8 -> cross tunnel x -3..3 (z -13..13) -> Bleu's z 8..13.
#   Two hatch stairs link the cross tunnel with the hall floor.
import math
import wsparts
PI = math.pi
WT = 0.4


def vat(K, x, z, r=3.0, T='C'):
    K.cyl('TF_Conc', x, 0, z, r + 0.4, 0.4, seg=32, col=True)
    K.cyl('TF_Machine', x, 0.4, z, r, 4.6, seg=32)
    K.cyl('TF_Steel', x, 2.2, z, r + 0.06, 0.25, seg=32)
    K.cyl('TF_Machine', x, 5.0, z, r, 1.0, seg=32, r2=1.0)
    K.cyl('TF_Hazard', x, 6.0, z, 1.0, 0.35, seg=24)
    a, b = r * 0.94, r * 0.39
    for (u, v) in ((a, b), (b, a), (r * 0.72, r * 0.72)):
        K.col(x - u, 0, z - v, x + u, 6.3, z + v)


def crate_stack(K, x0, z0, T):
    """shipping crates: two big team-painted corrugated boxes, one on top of the other offset"""
    K.box(f'TF_Corr_{T}', x0, 0, z0, x0 + 6.0, 2.6, z0 + 2.5, col=True)
    K.box('TF_Steel', x0 - 0.04, 0, z0 - 0.04, x0 + 0.15, 2.64, z0 + 2.54)
    K.box('TF_Steel', x0 + 5.85, 0, z0 - 0.04, x0 + 6.04, 2.64, z0 + 2.54)
    K.box('TF_Wood', x0 + 0.6, 2.6, z0 + 0.3, x0 + 2.4, 3.8, z0 + 2.1, col=True)


def half(K, T):
    P = wsparts.Parts(K, T)
    # floor + roof (west half; the rotated pass builds the east half)
    K.slab('TF_Floor', -28, -19, 0, 19, -0.3, 0.0, holes=[(-3, 3.33, -1, 9.0)])
    K.slab('TF_Ceiling', -28, -19, 0, 19, 14.0, 14.3, holes=[(-22, -6, -8, 6)], col=False)
    K.box('Glass', -22, 14.05, -6, -8, 14.1, 6)
    for x in (-22, -15, -8):
        K.box('TF_Steel', x - 0.15, 13.4, -19, x + 0.15, 14.0, 19)                    # roof girders
    # long wall (north; rotated -> south) with tall windows
    WIN = [(-24, -20), (-14, -10), (-4, 0), (6, 10), (16, 20)]
    K.wall2('x', -28, 28, 19, WT, 0, 14, holes=[(a, b, 7.5, 12.5) for a, b in WIN])
    for a, b in WIN:
        P.window('x', a, b, 19, WT, 7.5, 12.5, trim='TF_Steel', pane=1.0, transom=True)
    # north catwalk (y 6): x -28..3, z 13..18.8
    K.box('TF_Grate', -27.8, 5.8, 13.0, 3.0, 6.0, 18.8, col=True, bevel=False)
    K.box('TF_Steel', -27.8, 5.5, 12.95, 3.0, 5.8, 13.1)
    for (a, b) in ((-27.8, -18.05), (-15.95, -2.05)):
        P.rail(a, 13.05, b, 13.05, 6.0, mat='TF_Steel')
    P.rail(3.05, 13.05, 3.05, 18.8, 6.0, mat='TF_Steel')
    for x in (-24, -10, 2.0):
        K.box('TF_Steel', x - 0.12, 0, 13.0, x + 0.12, 5.8, 13.25, col=True)           # catwalk hangers to floor
    P.stairs(-17.0, 5.0, -PI / 2, 2.0, 0.0, 6.0, kind='steel', going=0.25)              # floor -> catwalk, z 5..13
    # bridge x -2..2 over the press (north half z 0..13)
    K.box('TF_Grate', -2, 5.8, 0, 2, 6.0, 13.0, col=True, bevel=False)
    for s in (-1, 1):
        K.box('TF_Steel', s * 1.85 - 0.12, 5.4, 0, s * 1.85 + 0.12, 5.8, 13.0)
        P.rail(s * 2.03, 0, s * 2.03, 13.0, 6.0, mat='TF_Steel', panel=f'TF_Paint_{T}')
    # cover on the floor
    vat(K, -13, -8.5, 3.0, T)
    crate_stack(K, -25.5, 4.6, T)
    # hatch stair: hall floor <-> cross tunnel (west side x -3..-1, ascends -z from z 9 to 3.33)
    P.stairs(-2.0, 9.0, PI / 2, 2.0, -4.0, 0.0, kind='conc')
    P.rail(-3.05, 3.4, -3.05, 9.0, 0.0, mat='TF_Steel'); P.rail(-0.95, 3.4, -0.95, 9.0, 0.0, mat='TF_Steel')
    P.rail(-3.0, 9.05, -1.0, 9.05, 0.0, mat='TF_Steel')
    # bottom corridor under the hall (Cheddar side): z -17..-12 from x -28 to the cross tunnel at x -3
    K.slab('TF_Conc', -28, -17, -3, -12, -4.3, -4.0)
    K.wall2('x', -28, -3, -17, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.wall2('x', -28, -3, -12, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    # cross tunnel x -3..3, z -17..17 (west wall + north end wall; the rotated pass mirrors them)
    K.slab('TF_Conc', -3, -17, 0, 17, -4.3, -4.0)
    K.wall2('z', -17, 17, -3, WT, -4.0, -0.3, holes=[(-17, -12, -4.0, -0.3)], lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.wall2('x', -3, 3, 17, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    for (x, z) in ((-20, -14.5), (-9, -14.5), (0, -10)):
        K.light(x, -0.8, z, '#bfe0ff', 0.9, 10)
        K.cyl('TF_Bulb', x, -0.42, z, 0.25, 0.1, seg=12)
    # hanging lamps
    for (x, z) in ((-21, -9), (-21, 9), (-10, 0), (-10, -14)):
        K.lamp(x, 14.0, z, drop=3.5, intensity=1.8, dist=20)
    K.area('Vat Hall', -28, -19, 0, 19, 0, kind='middle')


def press(K):
    """the central curd press (self-symmetric): blocks the straight line between the main doors"""
    K.box('TF_Conc', -3.0, 0, -3.0, 3.0, 0.5, 3.0, col=True)
    K.box('TF_Machine', -2.4, 0.5, -2.4, 2.4, 3.6, 2.4, col=True)
    K.box('TF_Steel', -2.5, 3.6, -2.5, 2.5, 3.85, 2.5)
    K.box('TF_Machine', -1.6, 3.85, -1.6, 1.6, 5.2, 1.6)
    K.box('TF_Hazard', -2.42, 0.5, -2.42, 2.42, 0.85, 2.42)
    for s in (-1, 1):
        K.cyl('TF_Steel', s * 1.2, 5.2, 0, 0.2, 0.58, seg=12)                      # rams up to the bridge
    K.area('Curd Press', -3, -3, 3, 3, 0, kind='landmark')


def middle(K):
    for rot, T in ((0.0, 'C'), (PI, 'B')):
        K.at(0, 0, 0, rot); half(K, T); K.pop()
    press(K)
