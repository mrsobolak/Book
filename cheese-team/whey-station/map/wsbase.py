# Whey Station v4 -- one team base, kept simple (base-local: d = x, 0 = back wall, 36 = front wall shared with the middle).
#   FLAG ROOM  d 0-18, z -16..16   flag dais in the centre, big emblem behind it, skylight; SPAWN walled off in the
#              back-north corner (d0-10, z9-16) with its door facing the flag room (no line of sight from the middle)
#   FRONT ROOM d 18-36, z -16..16  main door to the middle (z -4..4); the HIGH bridge (y 6, z -2..2) crosses it and
#              enters the flag room as a balcony; LOW tunnel (y -4, z -9..-5) runs under it to a hatch in the flag room
# Furniture and clutter are library models (Poly Haven / Sketchfab) placed with K.prop; only architecture is built here.
import math
import wsparts
PI = math.pi
WT = 0.4
FLAG = (8.0, 0.0)


def door(P, axis, s0, s1, c, y1=3.0, y0=0.0):
    P.opening(axis, s0, s1, c, WT, y0, y1, mat=P.tm('TF_Paint'), w=0.16)


def sign(K, mat, axis, s, c, side, y, w, h):
    """flat sign panel on a wall face (side = +1 / -1 picks the face of the wall at c)"""
    c0 = c + side * WT / 2
    c1 = c0 + side * 0.04
    if axis == 'x':
        K.box(mat, s - w / 2, y, min(c0, c1), s + w / 2, y + h, max(c0, c1))
    else:
        K.box(mat, min(c0, c1), y, s - w / 2, max(c0, c1), y + h, s + w / 2)


def base(K, T):
    P = wsparts.Parts(K, T)
    tm = P.tm
    PT = tm('TF_Paint')
    fx, fz = FLAG
    HATCH = (10.33, -8, 16, -6)
    # ---------------- floors / roof ----------------
    K.slab('TF_Floor', 0, -16, 36, 16, -0.3, 0.0, holes=[HATCH])
    K.box('TF_Tile', fx - 4.5, 0.0, fz - 4.5, fx + 4.5, 0.012, fz + 4.5, bevel=False)
    K.slab('TF_Ceiling', 0, -16, 36, 16, 10.0, 10.3, holes=[(fx - 3.5, fz - 3.5, fx + 3.5, fz + 3.5)], col=False)
    K.box('Glass', fx - 3.5, 10.05, fz - 3.5, fx + 3.5, 10.1, fz + 3.5)
    # ---------------- shell ----------------
    K.wall2('z', -16, 16, 0, WT, 0, 10)
    K.wall2('x', 0, 36, 16, WT, 0, 10)
    K.wall2('x', 0, 36, -16, WT, 0, 10)
    K.wall2('z', -16, 16, 36, WT, 0, 12, holes=[(-4, 4, 0, 4.0), (-2, 2, 6, 9.0)])        # front = middle hall end wall
    door(P, 'z', -4, 4, 36, 4.0)
    door(P, 'z', -2, 2, 36, 9.0, 6.0)
    sign(K, tm('TF_Emblem'), 'x', 30, 16, -1, 3.5, 4.0, 4.0)                               # team emblems in the front room
    sign(K, tm('TF_Emblem'), 'x', 30, -16, 1, 3.5, 4.0, 4.0)
    # flag room | front room: offset ground door + high opening for the bridge
    K.wall2('z', -16, 16, 18, WT, 0, 10, holes=[(-11, -6, 0, 3.2), (6, 11, 0, 3.2), (-2, 2, 6, 9.0)], lower=PT)
    door(P, 'z', -11, -6, 18, 3.2); door(P, 'z', 6, 11, 18, 3.2); door(P, 'z', -2, 2, 18, 9.0, 6.0)
    # ---------------- SPAWN (d0-10, z9-16) ----------------
    K.wall2('x', 0, 10, 9, WT, 0, 4.5, holes=[(6, 9, 0, 3)], lower=PT)
    K.wall2('z', 9, 16, 10, WT, 0, 4.5, lower=PT)
    door(P, 'x', 6, 9, 9)
    K.slab('TF_Ceiling', 0, 9, 10, 16, 4.5, 4.8)
    sign(K, tm('TF_Emblem'), 'x', 4, 16, -1, 1.4, 2.0, 2.0)
    K.prop('locker', 0.6, 0, 11.0, PI / 2, col=(-0.3, 0, -0.5, 0.3, 2.0, 0.5))
    K.prop('locker', 0.6, 0, 12.2, PI / 2, col=(-0.3, 0, -0.5, 0.3, 2.0, 0.5))
    K.prop('locker', 0.6, 0, 13.4, PI / 2, col=(-0.3, 0, -0.5, 0.3, 2.0, 0.5))
    K.prop('bench', 5.0, 0, 13.0, 0, col=(-1.0, 0, -0.25, 1.0, 0.5, 0.25))
    K.light(5, 4.0, 12.5, '#ffe7c2', 1.4, 10)
    K.area('Spawn', 0, 9, 10, 16, 0, team=T, kind='spawn')
    # ---------------- FLAG ROOM ----------------
    sign(K, tm('TF_Emblem'), 'z', fz, 0, 1, 2.8, 6.0, 6.0)                                 # big emblem behind the flag
    K.cyl(PT, fx, 0, fz, 2.6, 0.25, seg=32, col=True)                                      # dais
    K.cyl('TF_Conc', fx, 0.25, fz, 2.0, 0.25, seg=32, col=True)
    K.light(fx, 8.0, fz, '#fff6e0', 2.2, 18)
    K.label('FLAG', fx, 2.5, fz, team=T, kind='flag')
    # balcony (y 6) where the bridge comes in, stair down beside it
    K.box('TF_Conc', 12.0, 5.7, -2.0, 18.0, 6.0, 2.0, col=True, bevel=False)
    P.rail(12.0, -2.05, 18.0, -2.05, 6.0, mat='TF_Steel'); P.rail(11.95, -2.0, 11.95, 2.0, 6.0, mat='TF_Steel')
    K.box('TF_Conc', 12.0, 5.7, 2.0, 14.0, 6.0, 5.0, col=True, bevel=False)                # landing
    P.rail(14.05, 2.0, 14.05, 5.0, 6.0, mat='TF_Steel'); P.rail(12.0, 5.05, 14.0, 5.05, 6.0, mat='TF_Steel')
    P.stairs(4.0, 4.0, 0, 2.0, 0.0, 6.0, kind='steel', going=0.25)                         # d 4 -> 12 at z 3..5
    # hatch down to the tunnel
    P.stairs(16.0, -7.0, PI, 2.0, -4.0, 0.0, kind='conc')                                 # d 16 -> 10.33
    P.rail(10.4, -8.05, 16.0, -8.05, 0.0, mat='TF_Steel'); P.rail(10.4, -5.95, 16.0, -5.95, 0.0, mat='TF_Steel')
    P.rail(16.05, -8.0, 16.05, -6.0, 0.0, mat='TF_Steel')
    K.prop('crate', 3.0, 0, -12.0, 0.3, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('crate', 3.0, 1.2, -12.0, 0.9, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('barrel', 15.5, 0, 7.0, 0, col=(-0.35, 0, -0.35, 0.35, 0.9, 0.35))
    K.prop('barrel', 16.3, 0, 7.6, 0, col=(-0.35, 0, -0.35, 0.35, 0.9, 0.35))
    for (d, z) in ((4, -8), (13, 8)):
        K.lamp_prop(d, 7.5, z)
    K.area('Flag Room', 0, -16, 18, 16, 0, team=T, kind='flag')
    # ---------------- FRONT ROOM ----------------
    K.box('TF_Grate', 18.0, 5.8, -2.0, 36.0, 6.0, 2.0, col=True, bevel=False)            # bridge
    for s in (-1, 1):
        K.box('TF_Steel', 18.0, 5.45, s * 2.0 - 0.1, 36.0, 5.8, s * 2.0 + 0.1)
    P.rail(18.0, -2.05, 36.0, -2.05, 6.0, mat='TF_Steel', panel=PT)
    P.rail(28.6, 2.05, 36.0, 2.05, 6.0, mat='TF_Steel', panel=PT)
    K.box('TF_Conc', 26.6, 5.7, 2.0, 28.6, 6.0, 4.0, col=True, bevel=False)               # landing off the bridge
    P.rail(28.65, 2.0, 28.65, 4.0, 6.0, mat='TF_Steel'); P.rail(26.6, 4.05, 28.6, 4.05, 6.0, mat='TF_Steel')
    P.stairs(18.6, 3.0, 0, 2.0, 0.0, 6.0, kind='steel', going=0.25)                        # d 18.6 -> 26.6 at z 2..4
    K.prop('container', 27.0, 0, -11.5, 0, col=(-3.0, 0, -1.25, 3.0, 2.6, 1.25))          # cover
    K.prop('pallet_stack', 30.0, 0, 10.0, 0.4, col=(-0.7, 0, -0.6, 0.7, 1.0, 0.6))
    K.prop('crate', 22.0, 0, 12.5, 0.2, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    for (d, z) in ((27, -8), (27, 8)):
        K.lamp_prop(d, 7.5, z)
    K.area('Front Room', 18, -16, 36, 16, 0, team=T)
    K.area('Bridge', 12, -2, 36, 2, 6, team=T)
    # ---------------- LOW tunnel: y -4, z -9..-5, d 10..36 ----------------
    K.slab('TF_Conc', 10, -9, 36, -5, -4.3, -4.0)
    K.wall2('x', 10, 36, -9, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.wall2('x', 10, 36, -5, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.wall('TF_Tile', 'z', -9, -5, 10, WT, -4.0, -0.3, band=False)
    for d in (14, 24, 33):
        K.light(d, -0.8, -7, '#bfe0ff', 0.9, 10)
    K.area('Tunnel', 10, -9, 36, -5, -4, team=T, kind='tunnel')
