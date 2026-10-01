# Whey Station -- one team base, base-local coords (d = x, 0 = back wall, 36 = front toward the middle; z -24..20).
#  Spawn d0-10 z-6..6 | North stair hall d0-10 z6..15 (up to the Conveyor Gallery, y 6) | South stair hall d0-10 z-14..-6
#  (down to the brine sump, y -4) | Loading Yard d10-24 z-6..15 (hub) | Aging Cellar = FLAG ROOM d12-30 z-24..-6
#  | Main corridor d24-36 z-4..4 | Packing corridor d30-36 z-24..-4 | Office d24-36 z4..15 (second stair to the gallery)
#  | Conveyor Gallery d0-36 z15.4..20 at y 6 | Brine sump + tunnel y -4 (z-16..-12) with a hatch stair into the flag room.
import math
import wsparts
PI = math.pi
WT = 0.4
RUN6 = 32 * 0.27        # stair run for a 6 m climb
RUN4 = 21 * 0.27        # stair run for a 4 m climb


def rack(K, P, d0, d1, z0, z1, rng, wheels=True):
    """cheese aging rack: steel posts, 4 plank shelves, wheels of cheese"""
    for d in (d0 + 0.05, d1 - 0.05):
        for z in (z0 + 0.05, z1 - 0.05):
            K.box('Steel', d - 0.04, 0, z - 0.04, d + 0.04, 3.2, z + 0.04)
    for y in (0.35, 1.15, 1.95, 2.75):
        K.box('Planks', d0, y, z0, d1, y + 0.05, z1)
        if wheels:
            d = d0 + 0.35
            while d < d1 - 0.3:
                if rng.random() < 0.8:
                    K.cyl('Plaster' if rng.random() < 0.6 else 'Rust', d, y + 0.05, (z0 + z1) / 2, 0.27, 0.17, seg=12)
                d += 0.62
    K.col(d0, 0, z0, d1, 3.2, z1)


def crates(K, d, z, n=2):
    for i in range(n):
        K.box('Planks', d - 0.6, i * 1.2, z - 0.6, d + 0.6, i * 1.2 + 1.15, z + 0.6)
        K.box('Steel', d - 0.62, i * 1.2 + 0.5, z - 0.62, d + 0.62, i * 1.2 + 0.6, z + 0.62)
    K.col(d - 0.62, 0, z - 0.62, d + 0.62, n * 1.2, z + 0.62)


def base(K, T):
    P = wsparts.Parts(K, T)
    tm = P.tm
    # ---------------- floors (ground slab per zone; holes for the stair down and the flag-room hatch) ----------------
    K.slab('Epoxy', 0, -6, 10, 20, -0.3, 0.0)                                   # spawn + north stair hall
    K.slab('Conc', 0, -24, 12, -6, -0.3, 0.0, holes=[(1.33, -10, 7.0, -8)])     # south stair hall
    K.slab('Hangar', 10, -6, 24, 20, -0.3, 0.0)                                 # loading yard
    K.slab('TileFloor', 12, -24, 30, -6, -0.3, 0.0, holes=[(24.33, -16, 30.0, -14)])   # flag room
    K.slab('AntiSlip', 30, -24, 36, -6, -0.3, 0.0)                              # packing corridor
    K.slab('Epoxy', 24, -6, 36, 20, -0.3, 0.0)                                  # main corridor + office
    K.slab('CorrWorn', 0, -24, 36, 20, 10.0, 10.3, col=False)                   # roof
    # ---------------- outer shell ----------------
    K.wall('Brick', 'z', -24, 20, 0, WT, 0, 10)
    K.wall('Brick', 'x', 0, 36, 20, WT, 0, 10)
    K.wall('Brick', 'x', 0, 36, -24, WT, 0, 10)
    K.wall('Brick', 'z', -24, 20, 36, WT, 0, 10, holes=[(-4, 4, 0, 4.5), (-14, -9, 0, 3.2), (15.2, 19.8, 6, 9)])
    P.opening('z', -4, 4, 36, WT, 0, 4.5, mat=tm('SteelT'), w=0.18)
    P.opening('z', -14, -9, 36, WT, 0, 3.2, mat='Steel')
    P.opening('z', 15.2, 19.8, 36, WT, 6, 9, mat='Steel')
    # ---------------- spawn ----------------
    K.wall(tm('Paint'), 'x', 0, 10, 6, WT, 0, 10, holes=[(4, 7, 0, 2.8)])
    K.wall(tm('Paint'), 'x', 0, 10, -6, WT, 0, 10, holes=[(4, 7, 0, 2.8)])
    K.wall(tm('Paint'), 'z', -6, 6, 10, WT, 0, 10, holes=[(-2.5, 2.5, 0, 3.0)])
    K.slab('Conc', 0, -6, 10, 6, 5.0, 5.3, col=False)
    for (s0, s1, c, ax) in ((4, 7, 6, 'x'), (4, 7, -6, 'x'), (-2.5, 2.5, 10, 'z')):
        P.opening(ax, s0, s1, c, WT, 0, 3.0 if ax == 'z' else 2.8, mat=tm('SteelT'))
    K.box(tm('Shutter'), 0.2, 0, -4.6, 0.85, 2.3, 4.6, col=True)               # resupply lockers
    K.box('Steel', 0.2, 2.3, -4.7, 0.95, 2.4, 4.7)
    for z in (-3, 3):
        K.box('Planks', 4.2, 0.42, z - 1.5, 4.8, 0.48, z + 1.5)
        for zz in (z - 1.3, z + 1.3):
            K.box('Steel', 4.3, 0, zz - 0.04, 4.7, 0.42, zz + 0.04)
        K.col(4.2, 0, z - 1.5, 4.8, 0.48, z + 1.5)
    K.light(5, 4.6, 0, '#fff1d6', 1.4, 12)
    K.area('Spawn', 0, -6, 10, 6, 0, team=T, kind='spawn')
    # ---------------- north stair hall -> Conveyor Gallery (HIGH route) ----------------
    K.wall('CMU', 'z', 6, 15.2, 10, WT, 0, 10, holes=[(8, 11, 0, 3.0)])
    P.opening('z', 8, 11, 10, WT, 0, 3.0, mat='Steel')
    K.wall('CMU', 'x', 0, 10, 15.2, WT, 0, 6.0)
    P.stairs(1.5, 7.4, -PI / 2, 2.0, 0.0, 6.0, kind='steel', going=0.25)    # v1 started 0.16 m from the wall: unreachable from below
    P.rail(2.65, 15.2, 9.8, 15.2, 6.0)
    K.light(5, 9.3, 10, '#ffe6c0', 1.0, 12)
    K.area('Stair Hall', 0, 6, 10, 15, 0, team=T)
    # ---------------- Conveyor Gallery (y 6) ----------------
    K.box('Plate', 0, 5.8, 15.4, 36, 6.0, 19.8, col=True, bevel=False)
    K.box('SteelG', 3.0, 6.0, 18.4, 34.0, 6.85, 19.6, col=True)
    d = 3.4
    while d < 34:
        K.cyl('Steel', d, 6.75, 18.45, 0.06, 1.1, axis='z', seg=6); d += 1.0
    for d in (8, 16, 24, 32):
        K.light(d, 9.4, 17.5, '#ffe0b0', 0.9, 10)
    K.cyl('SteelG', 0.2, 8.9, 19.5, 0.18, 35.6, axis='x', seg=10)
    K.area('Conveyor Gallery', 0, 15.4, 36, 20, 6, team=T)
    # ---------------- south stair hall -> brine sump (LOW route) ----------------
    K.wall('CMU', 'x', 0, 10, -14, WT, 0, 5)
    K.wall('CMU', 'z', -14, -6, 10, WT, 0, 5)
    K.slab('Conc', 0, -14, 10, -6, 5.0, 5.3, col=False)
    P.stairs(1.33, -9, 0, 2.0, -4.0, 0.0, kind='conc')
    P.rail(1.33, -10.05, 7.0, -10.05, 0.0); P.rail(1.33, -7.95, 7.0, -7.95, 0.0); P.rail(1.28, -10, 1.28, -8, 0.0)
    K.light(6, 4.6, -10, '#d6ecff', 0.9, 9)
    # sump + brine tunnel (y -4)
    K.slab('FloorDmg', 0, -16, 12, -6, -4.3, -4.0)
    K.slab('FloorDmg', 12, -16, 36, -12, -4.3, -4.0)
    K.wall('Ribbed', 'z', -16, -6, 0, WT, -4.0, -0.3)
    K.wall('Ribbed', 'x', 0, 12, -6, WT, -4.0, -0.3)
    K.wall('Ribbed', 'x', 0, 36, -16, WT, -4.0, -0.3)
    K.wall('Ribbed', 'z', -12, -6, 12, WT, -4.0, -0.3)
    K.wall('Ribbed', 'x', 12, 36, -12, WT, -4.0, -0.3)
    K.cyl('SteelG', 0.2, -1.0, -15.5, 0.2, 35.8, axis='x', seg=10)
    K.box('Grate', 12.4, -4.02, -13.6, 35.8, -3.98, -12.6)
    for d in (5, 18, 30):
        K.light(d, -0.8, -13.5 if d > 12 else -11, '#9fd0ff', 0.8, 9)
    K.area('Brine Tunnel', 0, -16, 36, -6, -4, team=T, kind='tunnel')
    # hatch stair from the tunnel up into the flag room
    P.stairs(30.0, -15, PI, 2.0, -4.0, 0.0, kind='steel')
    P.rail(24.33, -14.0, 29.8, -14.0, 0.0); P.rail(24.33, -16.0, 29.8, -16.0, 0.0)
    # ---------------- Loading Yard (hub) ----------------
    K.wall('Brick', 'x', 10, 30, -6, WT, 0, 10, holes=[(14, 18, 0, 3.2)])
    P.opening('x', 14, 18, -6, WT, 0, 3.2, mat=tm('SteelT'))
    K.wall('CMU', 'z', -6, 15.2, 24, WT, 0, 10, holes=[(-4, 4, 0, 4.5), (8, 11, 0, 3.0), (11.6, 14.6, 1.0, 2.4)])
    P.opening('z', -4, 4, 24, WT, 0, 4.5, mat=tm('SteelT'), w=0.18)
    P.opening('z', 8, 11, 24, WT, 0, 3.0, mat='Steel')
    P.window('z', 11.6, 14.6, 24, WT, 1.0, 2.4)
    K.wall('Brick', 'x', 10, 24, 15.2, WT, 0, 10, holes=[(11.5, 15.5, 6.6, 8.6), (18.5, 22.5, 6.6, 8.6)])
    P.window('x', 11.5, 15.5, 15.2, WT, 6.6, 8.6, open_=True, bars=False)
    P.window('x', 18.5, 22.5, 15.2, WT, 6.6, 8.6, open_=True, bars=False)
    for z in (-3, 5, 12):
        P.hbeam(10, 24, z, 10.0, d=0.45, w=0.22)
    for (d, z) in ((17, 4.5), (17, -2.5)):
        P.ibeam(d, z, 0, 9.55, w=0.3)
    crates(K, 13.2, 3.4, 2); crates(K, 14.6, 3.4, 1); crates(K, 20.5, 10.5, 2); crates(K, 21.0, -3.6, 1)
    K.box(tm('Clad'), 11.0, 0, 12.6, 15.0, 2.4, 14.6, col=True)                   # whey tote stack
    K.light(17, 9.3, 4, '#ffe9c8', 1.6, 18)
    K.area('Loading Yard', 10, -6, 24, 15, 0, team=T)
    # ---------------- Aging Cellar = FLAG ROOM ----------------
    K.wall('Brick', 'z', -24, -6, 12, WT, 0, 8)
    K.wall('Brick', 'z', -24, -4, 30, WT, 0, 8, holes=[(-18, -14, 0, 3.2)])
    P.opening('z', -18, -14, 30, WT, 0, 3.2, mat='Steel')
    K.slab('Conc', 12, -24, 30, -6, 8.0, 8.3, col=False)
    for z in (-21, -15, -9):
        P.hbeam(12, 30, z, 8.0, d=0.4, w=0.2)
    fx, fy, fz = 20.0, 0.0, -19.0
    K.box('SteelPlate', fx - 1.2, 0, fz - 1.2, fx + 1.2, 0.3, fz + 1.2, col=True)
    K.cyl(tm('SteelT'), fx, 0.3, fz, 0.95, 0.05, seg=24)
    K.box('SafetyY', fx - 1.5, 0.0, fz - 1.5, fx + 1.5, 0.012, fz - 1.3)
    K.box('SafetyY', fx - 1.5, 0.0, fz + 1.3, fx + 1.5, 0.012, fz + 1.5)
    rng = K.rng
    rack(K, P, 13.0, 19.0, -23.6, -22.5, rng); rack(K, P, 22.0, 28.5, -23.6, -22.5, rng)
    rack(K, P, 15.0, 19.5, -12.6, -11.5, rng); rack(K, P, 12.4, 13.5, -20.5, -8.5, rng)
    rack(K, P, 22.5, 23.6, -12.0, -7.5, rng)
    P.ibeam(18, -15.5, 0, 7.6, w=0.3); P.ibeam(26, -21, 0, 7.6, w=0.3)
    K.light(17, 7.4, -15, '#cfe6ff', 1.3, 16); K.light(26, 7.4, -19, '#cfe6ff', 1.0, 12)
    K.area('Aging Cellar', 12, -24, 30, -6, 0, team=T, kind='flag')
    K.label('FLAG', fx, 2.0, fz, team=T, kind='flag')
    # ---------------- main corridor ----------------
    K.wall('TileW', 'x', 24, 36, 4, WT, 0, 10, holes=[(26, 29, 0, 3.0)])
    K.wall('TileW', 'x', 24, 36, -4, WT, 0, 5, holes=[(31, 35, 0, 3.2)])
    K.slab('Conc', 24, -4, 36, 4, 5.0, 5.3, col=False)
    P.opening('x', 26, 29, 4, WT, 0, 3.0, mat='Steel')
    P.opening('x', 31, 35, -4, WT, 0, 3.2, mat='Steel')
    K.cyl('SteelG', 24.2, 4.5, 3.4, 0.16, 11.6, axis='x', seg=10)
    K.light(30, 4.6, 0, '#ffe0b0', 1.0, 10)
    # ---------------- packing corridor ----------------
    K.slab('Conc', 30, -24, 36, -4, 5.0, 5.3, col=False)
    K.box('SteelG', 34.4, 0, -23.5, 35.6, 0.85, -15.5, col=True)
    z = -23.2
    while z < -15.6:
        K.cyl('Steel', 34.4, 0.78, z, 0.05, 1.2, axis='x', seg=6); z += 0.5
    K.light(33, 4.6, -14, '#ffe0b0', 1.0, 10)
    K.area('Packing Line', 30, -24, 36, -4, 0, team=T)
    # ---------------- office (second stair to the gallery) ----------------
    K.wall('Brick', 'x', 24, 36, 15.2, WT, 0, 10, holes=[(33.5, 35.5, 6.0, 9.0)])
    P.opening('x', 33.5, 35.5, 15.2, WT, 6.0, 9.0, mat='Steel')
    P.stairs(34.5, 15.0 - RUN6, -PI / 2, 2.0, 0.0, 6.0, kind='steel')
    K.box('SteelPlate', 25.0, 0, 12.8, 29.5, 1.05, 14.6, col=True)                 # control desk
    K.box('Glass', 25.2, 1.05, 14.3, 29.3, 1.6, 14.35)
    K.light(29, 9.3, 9, '#fff1d6', 1.0, 12)
    K.area('Control Office', 24, 4, 36, 15, 0, team=T)
