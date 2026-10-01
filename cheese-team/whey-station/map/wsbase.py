# Whey Station v3 -- one team base (base-local: d = x, 0 = back wall, 44 = front wall shared with the middle hall).
# Turbine-like topology (spawn and flag in opposite back corners), original layout:
#   SPAWN       d 0-12,  z 9..19   back-north corner      doors: east -> North Hall, south -> Back Hall
#   NORTH HALL  d 12-44, z 9..19   stairs up to the UPPER CORRIDOR (y 6, z 13..19) -> hall catwalk (HIGH)
#   BACK HALL   d 0-26,  z -3..9   links spawn, flag room and lobby; the HIGH-route bridge crosses it at y 6
#   LOBBY       d 26-44, z -9..9   behind the main door (MAIN), blast wall inside the door
#   SOUTH HALL  d 26-44, z -19..-9 lobby -> flag room side door; the bottom corridor runs underneath (LOW)
#   FLAG ROOM   d 0-26,  z -19..-3 back-south corner: flag dais in the centre under a skylight, team emblem,
#               balcony (y 6) reached by the bridge (HIGH), hatch stair from the bottom corridor (LOW)
import math
import wsparts
PI = math.pi
WT = 0.4
FLAG = (12.0, -11.0)


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


def crates(K, d, z, T, n=2):
    K.box('TF_Wood', d - 0.7, 0, z - 0.7, d + 0.7, 1.4, z + 0.7, col=True)
    if n > 1:
        K.box('TF_Wood', d - 0.5, 1.4, z - 0.5, d + 0.5, 2.4, z + 0.5, col=True)


def base(K, T):
    P = wsparts.Parts(K, T)
    tm = P.tm
    PT = tm('TF_Paint')
    fx, fz = FLAG
    # ---------------- floors / roof ----------------
    K.slab('TF_Floor', 0, -3, 44, 19, -0.3, 0.0)                                          # spawn, north hall, back hall, lobby (north part)
    K.slab('TF_Floor', 26, -19, 44, -3, -0.3, 0.0)                                        # lobby south part + south hall
    K.slab('TF_Floor', 0, -19, 26, -3, -0.3, 0.0, holes=[(20.33, -17, 26.0, -15)])        # flag room (+ hatch)
    K.box('TF_Tile', fx - 5, 0.0, fz - 5, fx + 5, 0.012, fz + 5, bevel=False)
    K.slab('TF_Ceiling', 0, -19, 44, 19, 10.0, 10.3, holes=[(fx - 4, fz - 4, fx + 4, fz + 4)], col=False)
    K.box('Glass', fx - 4, 10.05, fz - 4, fx + 4, 10.1, fz + 4)
    for z in (fz - 2, fz, fz + 2):
        K.box('TF_Steel', fx - 4, 10.0, z - 0.06, fx + 4, 10.3, z + 0.06)
    # ---------------- outer shell ----------------
    K.wall2('z', -19, 19, 0, WT, 0, 10)
    K.wall2('x', 0, 44, 19, WT, 0, 10)
    K.wall2('x', 0, 44, -19, WT, 0, 10)
    K.wall2('z', -19, 19, 44, WT, 0, 14, holes=[(-4, 4, 0, 4.5), (13.2, 18.8, 6, 9.5)])   # front = hall end wall
    door(P, 'z', -4, 4, 44, 4.5)
    door(P, 'z', 13.2, 18.8, 44, 9.5, 6.0)
    sign(K, tm('TF_Emblem'), 'z', 0, 44, 1, 6.0, 5.0, 5.0)                                # big emblem facing the hall
    # ---------------- interior walls ----------------
    K.wall2('x', 0, 12, 9, WT, 0, 10, holes=[(3, 6, 0, 3)], lower=PT)                   # spawn | back hall
    K.wall2('z', 9, 19, 12, WT, 0, 10, holes=[(12, 15, 0, 3)], lower=PT)                # spawn | north hall
    K.wall2('x', 12, 44, 9, WT, 0, 10, holes=[(21, 25, 6, 9.2), (34, 38, 0, 3)])        # north hall | back hall + lobby
    K.wall2('x', 0, 26, -3, WT, 0, 10, holes=[(9, 12, 0, 3), (21, 25, 6, 9.2)], lower=PT)   # back hall | flag room
    K.wall2('z', -3, 9, 26, WT, 0, 10, holes=[(4, 8, 0, 3)])                            # back hall | lobby
    K.wall2('z', -19, -3, 26, WT, 0, 10, holes=[(-16, -12, 0, 3)], lower=PT)            # flag room | south hall + lobby
    K.wall2('x', 26, 44, -9, WT, 0, 10, holes=[(34, 38, 0, 3)])                         # lobby | south hall
    for (ax, s0, s1, c) in (('x', 3, 6, 9), ('z', 12, 15, 12), ('x', 34, 38, 9), ('x', 9, 12, -3), ('z', 4, 8, 26),
                            ('z', -16, -12, 26), ('x', 34, 38, -9)):
        door(P, ax, s0, s1, c)
    for (ax, s0, s1, c) in (('x', 21, 25, 9), ('x', 21, 25, -3)):
        door(P, ax, s0, s1, c, 9.2, 6.0)
    # ---------------- SPAWN ----------------
    K.slab('TF_Ceiling', 0, 9, 12, 19, 5.0, 5.3, col=False)
    K.box(tm('TF_Corr'), 0.2, 0, 10.5, 0.9, 2.4, 17.5, col=True)                         # resupply lockers
    K.box('TF_Steel', 0.2, 2.4, 10.4, 1.0, 2.5, 17.6)
    for zz in (11.9, 13.3, 14.7, 16.1):
        K.box('TF_Steel', 0.9, 0.2, zz - 0.04, 0.95, 2.2, zz + 0.04)
    sign(K, tm('TF_Emblem'), 'x', 6, 19, -1, 2.6, 2.0, 2.0)
    K.box('TF_Wood', 5.0, 0.42, 12.5, 7.0, 0.5, 13.1); K.col(5.0, 0, 12.5, 7.0, 0.5, 13.1)
    K.box('TF_Wood', 5.0, 0.42, 15.9, 7.0, 0.5, 16.5); K.col(5.0, 0, 15.9, 7.0, 0.5, 16.5)
    K.lamp(6, 5.0, 14, drop=0.6, intensity=1.6)
    K.area('Spawn', 0, 9, 12, 19, 0, team=T, kind='spawn')
    # ---------------- NORTH HALL + upper corridor (HIGH) ----------------
    P.stairs(24.0, 11.0, 0, 2.0, 0.0, 6.0, kind='steel', going=0.25)                      # d 24..32, z 10..12
    K.box('TF_Conc', 32.0, 5.7, 9.6, 34.0, 6.0, 13.0, col=True, bevel=False)              # landing
    P.rail(32.0, 9.65, 34.0, 9.65, 6.0, mat='TF_Steel'); P.rail(34.05, 9.6, 34.05, 13.0, 6.0, mat='TF_Steel')
    K.box('TF_Conc', 18.0, 5.7, 13.0, 44.0, 6.0, 18.8, col=True, bevel=False)             # upper corridor floor
    K.box('TF_Steel', 18.0, 5.5, 12.95, 44.0, 5.7, 13.1)
    P.rail(25.0, 13.05, 32.0, 13.05, 6.0, mat='TF_Steel'); P.rail(34.0, 13.05, 43.8, 13.05, 6.0, mat='TF_Steel')
    P.rail(18.0, 13.05, 21.0, 13.05, 6.0, mat='TF_Steel'); P.rail(17.95, 13.0, 17.95, 18.8, 6.0, mat='TF_Steel')
    for d in (20, 30, 40):
        K.box('TF_Steel', d - 0.12, 0, 13.0, d + 0.12, 5.7, 13.25, col=True)
    sign(K, 'TF_Arrow', 'x', 30, 19, -1, 7.0, 1.2, 1.2)
    K.lamp(22, 10.0, 11, drop=2.0); K.lamp(38, 10.0, 11, drop=2.0)
    K.area('North Hall', 12, 9, 44, 19, 0, team=T)
    K.area('Upper Corridor', 18, 13, 44, 19, 6, team=T)
    # bridge over the back hall (y 6): corridor -> flag room balcony
    K.box('TF_Grate', 21.0, 5.8, -3.0, 25.0, 6.0, 13.0, col=True, bevel=False)
    for s in (21.0, 25.0):
        K.box('TF_Steel', s - 0.12, 5.4, -3.0, s + 0.12, 5.8, 13.0)
        P.rail(s + (-0.05 if s < 23 else 0.05), -2.8, s + (-0.05 if s < 23 else 0.05), 8.8, 6.0, mat='TF_Steel', panel=PT)
    # ---------------- BACK HALL ----------------
    crates(K, 15.0, 3.0, T); crates(K, 8.5, -0.5, T, 1)
    K.lamp(8, 10.0, 3, drop=2.5); K.lamp(18, 10.0, 3, drop=4.2, intensity=1.0)
    sign(K, 'TF_Arrow', 'x', 13.5, -3, 1, 2.0, 1.0, 1.0)
    K.area('Back Hall', 0, -3, 26, 9, 0, team=T)
    # ---------------- LOBBY ----------------
    K.wall2('z', -5, 5, 40.3, 0.6, 0, 4.0, lower=PT)                                      # blast wall
    K.box('TF_Steel', 40.0, 4.0, -5.05, 40.6, 4.15, 5.05)
    crates(K, 30.0, -5.5, T); crates(K, 31.5, 5.8, T, 1)
    K.lamp(32, 10.0, 0, drop=2.5); K.lamp(40, 10.0, -7, drop=2.5, intensity=1.0)
    K.area('Lobby', 26, -9, 44, 9, 0, team=T)
    # ---------------- SOUTH HALL ----------------
    K.box(tm('TF_Corr'), 38.0, 0, -18.6, 43.6, 2.6, -16.2, col=True)                      # parked crate
    K.lamp(35, 10.0, -14, drop=2.5)
    sign(K, 'TF_Arrow', 'x', 30, -19, 1, 2.0, 1.0, 1.0)
    K.area('South Hall', 26, -19, 44, -9, 0, team=T)
    # ---------------- bottom corridor (LOW): y -4, z -17..-12, d 18..44, hatch into the flag room ----------------
    K.slab('TF_Conc', 18, -17, 44, -12, -4.3, -4.0)
    K.wall2('x', 18, 44, -17, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.wall2('x', 18, 44, -12, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.wall('TF_Tile', 'z', -17, -12, 18, WT, -4.0, -0.3, band=False)
    K.wall('TF_Conc', 'z', -17, -14.6, 35, 0.6, -4.0, -0.3, band=False)                  # baffle: breaks the long lane
    for d in (22, 31, 40):
        K.light(d, -0.8, -13.5, '#bfe0ff', 0.9, 10)
        K.cyl('TF_Bulb', d, -0.42, -13.5, 0.25, 0.1, seg=12)
    P.stairs(26.0, -16, PI, 2.0, -4.0, 0.0, kind='conc')                                  # d 26 -> 20.33, z -17..-15
    P.rail(20.4, -17.05, 26.0, -17.05, 0.0, mat='TF_Steel'); P.rail(20.4, -14.95, 25.8, -14.95, 0.0, mat='TF_Steel')
    K.area('Bottom Corridor', 18, -17, 44, -12, -4, team=T, kind='tunnel')
    # ---------------- FLAG ROOM ----------------
    sign(K, tm('TF_Emblem'), 'z', fz, 0, 1, 3.0, 5.5, 5.5)                                # emblem behind the flag
    K.cyl(PT, fx, 0, fz, 2.8, 0.25, seg=32, col=True)                                     # dais
    K.cyl('TF_Conc', fx, 0.25, fz, 2.2, 0.25, seg=32, col=True)
    K.cyl(PT, fx, 0.5, fz, 0.6, 0.06, seg=20)
    K.light(fx, 8.0, fz, '#fff6e0', 2.2, 18)
    K.label('FLAG', fx, 2.5, fz, team=T, kind='flag')
    # balcony (y 6) along the north wall + stair down
    K.box('TF_Conc', 12.0, 5.7, -7.0, 25.8, 6.0, -3.2, col=True, bevel=False)
    K.box('TF_Steel', 12.0, 5.5, -7.05, 25.8, 5.7, -6.9)
    P.rail(12.0, -7.0, 25.8, -7.0, 6.0, mat='TF_Steel')
    P.stairs(4.0, -5.5, 0, 2.0, 0.0, 6.0, kind='steel', going=0.25)                       # d 4..12, z -6.5..-4.5
    for (d0, z0) in ((19.5, -12.5),):
        K.box('TF_Wood', d0, 0, z0, d0 + 1.0, 2.2, z0 + 3.0, col=True)
    crates(K, 4.0, -16.0, T)
    for (d, z) in ((6, -11), (19, -11)):
        K.lamp(d, 10.0, z, drop=2.5)
    K.area('Flag Room', 0, -19, 26, -3, 0, team=T, kind='flag')
