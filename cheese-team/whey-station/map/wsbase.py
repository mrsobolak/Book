# Whey Station -- one team base, base-local coords (d = x, 0 = back wall, 36 = front toward the middle; z -24..20).
#  Spawn d0-10 z-6..6 | North stair hall d0-10 z6..15 (up to the Conveyor Gallery, y 6) | South stair hall d0-10 z-14..-6
#  (down to the brine sump, y -4) | Loading Yard d10-24 z-6..15 (hub) | FLAG ROOM d12-30 z-24..-6
#  | Main corridor d24-36 z-4..4 | Packing corridor d30-36 z-24..-4 | Office d24-36 z4..15 (second stair to the gallery)
#  | Conveyor Gallery d0-36 z15.4..20 at y 6 | Brine sump + tunnel y -4 (z-16..-12) with a hatch stair into the flag room.
import math
import wsparts
PI = math.pi
WT = 0.4
RUN6 = 32 * 0.27        # stair run for a 6 m climb
RUN4 = 21 * 0.27        # stair run for a 4 m climb


def crates(K, d, z, n=2, ry=0.0):
    """stack of library crates (Sketchfab 'Stylized Wooden Crate', 1.2 m cube), each sitting exactly on the one below"""
    for i in range(n):
        K.prop('crate', d, i * 1.2, z, ry + 0.25 * i, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))


def base(K, T):
    P = wsparts.Parts(K, T)
    tm = P.tm
    # ---------------- floors (ground slab per zone; holes for the stair down and the flag-room hatch) ----------------
    K.slab('TF_Floor', 0, -6, 10, 20, -0.3, 0.0)                                   # spawn + north stair hall
    K.slab('Conc', 0, -24, 12, -6, -0.3, 0.0, holes=[(1.33, -10, 7.0, -8)])     # south stair hall
    K.slab('Hangar', 10, -6, 24, 20, -0.3, 0.0)                                 # loading yard
    K.slab('TF_FloorWarm', 12, -24, 30, -6, -0.3, 0.0, holes=[(24.33, -15.8, 30.0, -12.2)])   # flag room
    K.slab('AntiSlip', 30, -24, 36, -6, -0.3, 0.0)                              # packing corridor
    K.slab('TF_Floor', 24, -6, 36, 20, -0.3, 0.0)                                  # main corridor + office
    K.slab('CorrWorn', 0, -24, 36, 20, 10.0, 10.3, holes=[(17.5, -19.0, 23.5, -13.0)], col=False)                   # roof
    # ---------------- outer shell ----------------
    K.wall2('z', -24, 20, 0, WT, 0, 10)
    K.wall2('x', 0, 36, 20, WT, 0, 10)
    K.wall2('x', 0, 36, -24, WT, 0, 10)
    K.wall2('z', -24, 20, 36, WT, 0, 10, holes=[(-4, 4, 0, 4.5), (-14, -9, 0, 3.2), (15.2, 19.8, 5.8, 9)])
    P.opening('z', -4, 4, 36, WT, 0, 4.5, mat=tm('SteelT'), w=0.18)
    P.opening('z', -14, -9, 36, WT, 0, 3.2, mat='Steel')
    P.opening('z', 15.2, 19.8, 36, WT, 6, 9, mat='Steel')
    # ---------------- spawn ----------------
    K.wall2('x', 0, 10, 6, WT, 0, 10, holes=[(4, 7, 0, 2.8)], lower=tm('TF_Paint'))
    K.wall2('x', 0, 10, -6, WT, 0, 10, holes=[(4, 7, 0, 2.8)], lower=tm('TF_Paint'))
    K.wall2('z', -6, 6, 10, WT, 0, 10, holes=[(-2.5, 2.5, 0, 3.0)], lower=tm('TF_Paint'))
    K.slab('TF_Ceiling', 0, -6, 10, 6, 5.0, 5.3, col=False)
    for (s0, s1, c, ax) in ((4, 7, 6, 'x'), (4, 7, -6, 'x'), (-2.5, 2.5, 10, 'z')):
        P.opening(ax, s0, s1, c, WT, 0, 3.0 if ax == 'z' else 2.8, mat=tm('SteelT'))
    K.box(tm('TF_Corr'), 0.2, 0, -4.6, 0.85, 2.3, 4.6, col=True)               # resupply lockers
    K.box('Steel', 0.2, 2.3, -4.7, 0.95, 2.4, 4.7)
    for z in (-3, 3):
        K.box('Planks', 4.2, 0.42, z - 1.5, 4.8, 0.48, z + 1.5)
        for zz in (z - 1.3, z + 1.3):
            K.box('Steel', 4.3, 0, zz - 0.04, 4.7, 0.42, zz + 0.04)
        K.col(4.2, 0, z - 1.5, 4.8, 0.48, z + 1.5)
    K.light(5, 4.6, 0, '#fff1d6', 1.4, 12)
    K.area('Spawn', 0, -6, 10, 6, 0, team=T, kind='spawn')
    # ---------------- north stair hall -> Conveyor Gallery (HIGH route) ----------------
    K.wall2('z', 6, 15.2, 10, WT, 0, 10, holes=[(8, 11, 0, 3.0)])
    P.opening('z', 8, 11, 10, WT, 0, 3.0, mat='Steel')
    K.wall2('x', 0, 10, 15.2, WT, 0, 5.8)                                       # stops under the gallery floor (stair top passes over)
    P.stairs(1.5, 7.4, -PI / 2, 2.0, 0.0, 6.0, kind='steel', going=0.25)    # v1 started 0.16 m from the wall: unreachable from below
    P.rail(2.65, 15.2, 9.8, 15.2, 6.0)
    K.light(5, 9.3, 10, '#ffe6c0', 1.0, 12)
    K.area('Stair Hall', 0, 6, 10, 15, 0, team=T)
    # ---------------- Conveyor Gallery (y 6) ----------------
    K.box('Plate', 0, 5.8, 15.4, 36, 6.0, 19.8, col=True, bevel=False)
    for d in (8, 16, 24, 32):
        K.light(d, 9.4, 17.5, '#ffe0b0', 0.9, 10)
    K.area('Conveyor Gallery', 0, 15.4, 36, 20, 6, team=T)
    # ---------------- south stair hall -> brine sump (LOW route) ----------------
    K.wall2('x', 0, 10, -14, WT, 0, 5)
    K.wall2('z', -14, -6, 10, WT, 0, 5)
    K.slab('Conc', 0, -14, 10, -6, 5.0, 5.3, col=False)
    P.stairs(1.33, -9, 0, 2.0, -4.0, 0.0, kind='conc')
    P.rail(1.33, -10.05, 7.0, -10.05, 0.0); P.rail(1.33, -7.95, 7.0, -7.95, 0.0); P.rail(1.28, -10, 1.28, -8, 0.0)
    K.light(6, 4.6, -10, '#d6ecff', 0.9, 9)
    # sump + brine tunnel (y -4)
    K.slab('TF_Floor', 0, -16, 12, -6, -4.3, -4.0)
    K.slab('TF_Floor', 12, -16, 36, -12, -4.3, -4.0)
    K.wall2('z', -16, -6, 0, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('x', 0, 12, -6, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('x', 0, 36, -16, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('z', -12, -6, 12, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('x', 12, 36, -12, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.box('TF_Grate', 12.4, -4.02, -13.6, 35.8, -3.98, -12.6)
    # tunnel ceilings (under the slabs above) -- with the stair openings left open
    K.slab('TF_Ceiling', 0, -16, 12, -6, -0.33, -0.3, holes=[(1.33, -10, 7.0, -8)], col=False)
    K.slab('TF_Ceiling', 12, -16, 36, -12, -0.33, -0.3, holes=[(24.33, -15.8, 30.0, -12.2)], col=False)
    K.box('TF_Hazard', 0.2, -4.0, -15.8, 11.8, -3.99, -15.6)                           # floor edge stripes
    K.box('TF_Hazard', 12.0, -4.0, -15.8, 35.8, -3.99, -15.6)
    for (d, z) in ((4, -11), (16, -14), (22, -14), (33, -14)):
        K.lamp_prop(d, -0.33, z, color='#e8f2ff', intensity=1.1, dist=11)
    K.prop('crate', 9.5, -4.0, -15.0, 0.3, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.area('Brine Tunnel', 0, -16, 36, -6, -4, team=T, kind='tunnel')
    # hatch stair from the tunnel up into the flag room
    P.stairs(30.0, -14.7, PI, 2.0, -4.0, 0.0, kind='steel')                       # clear of the tunnel wall (face at -15.8)
    P.rail(24.33, -12.1, 29.8, -12.1, 0.0); P.rail(29.9, -15.8, 29.9, -12.2, 0.0); P.rail(24.33, -15.95, 29.8, -15.95, 0.0)
    # ---------------- Loading Yard (hub) ----------------
    K.wall2('x', 10, 30, -6, WT, 0, 10, holes=[(14, 18, 0, 3.2), (19.0, 24.0, 1.2, 3.0)])
    P.window('x', 19.0, 24.0, -6, WT, 1.2, 3.0, trim='TF_Steel', pane=1.25)
    P.opening('x', 14, 18, -6, WT, 0, 3.2, mat=tm('SteelT'))
    K.wall2('z', -6, 15.2, 24, WT, 0, 10, holes=[(-4, 4, 0, 4.5), (8, 11, 0, 3.0), (11.6, 14.6, 1.0, 2.4)])
    P.opening('z', -4, 4, 24, WT, 0, 4.5, mat=tm('SteelT'), w=0.18)
    P.opening('z', 8, 11, 24, WT, 0, 3.0, mat='Steel')
    P.window('z', 11.6, 14.6, 24, WT, 1.0, 2.4)
    K.wall2('x', 10, 24, 15.2, WT, 0, 10, holes=[(11.5, 15.5, 6.6, 8.6), (18.5, 22.5, 6.6, 8.6)])
    P.window('x', 11.5, 15.5, 15.2, WT, 6.6, 8.6, open_=True, bars=False)
    P.window('x', 18.5, 22.5, 15.2, WT, 6.6, 8.6, open_=True, bars=False)
    for z in (-3, 5, 12):
        P.hbeam(10, 24, z, 10.0, d=0.45, w=0.22)
    for (d, z) in ((17, 4.5), (17, -2.5)):
        P.ibeam(d, z, 0, 9.55, w=0.3)
    crates(K, 13.2, 3.4, 2); crates(K, 14.6, 3.4, 1); crates(K, 20.5, 10.5, 2); crates(K, 21.0, -3.6, 1)
    K.prop('pallet_stack', 12.0, 0, 13.6, 0.0, col=(-0.7, 0, -0.47, 0.7, 0.8, 0.47))
    K.prop('pallet_stack', 14.0, 0, 13.6, 0.1, col=(-0.7, 0, -0.47, 0.7, 0.8, 0.47))
    K.light(17, 9.3, 4, '#ffe9c8', 1.6, 18)
    K.area('Loading Yard', 10, -6, 24, 15, 0, team=T)
    # ---------------- FLAG ROOM (d 12-30, z -24..-6): "the curing vault" -- the flag sits on a stepped round dais in the
    # middle under a skylight, four tall team-banded whey tanks stand in the corners (cover + the same family as the
    # Vat Hall vats), cream block walls over a team-colour dado, warm concrete floor with a painted team ring ----------------
    TP = tm('TF_Paint')
    K.wall2('z', -24, -6, 12, WT, 0, 8, lower=TP)
    K.wall2('z', -24, -4, 30, WT, 0, 8, holes=[(-18, -14, 0, 3.2)], lower=TP)
    P.opening('z', -18, -14, 30, WT, 0, 3.2, mat='TF_Steel')
    # team dado on the flag-room face of the two shared walls (thick enough to bury their own trim strip)
    for (c, f, cuts) in ((-24, 1, []), (-6, -1, [(13.85, 18.15)])):
        c0 = c + f * WT / 2; c1 = c0 + f * 0.04; cc1 = c1 + f * 0.025
        a = 12.2
        for (h0, h1) in cuts + [(29.8, 29.8)]:
            if h0 > a:
                K.box(TP, a, 0.0, min(c0, c1), h0, 1.2, max(c0, c1))
                K.box('TF_Steel', a, 1.15, min(c1, cc1), h0, 1.25, max(c1, cc1))
            a = max(a, h1)
    K.slab('TF_Ceiling', 12, -24, 30, -6, 8.0, 8.3, holes=[(17.5, -19.0, 23.5, -13.0)], col=False)
    for (a0, b0, a1, b1) in ((17.5, -19.0, 23.5, -18.8), (17.5, -13.2, 23.5, -13.0), (17.5, -18.8, 17.7, -13.2), (23.3, -18.8, 23.5, -13.2)):
        K.box('TF_Conc', a0, 8.0, b0, a1, 10.0, b1)                                       # skylight shaft
    K.box('Glass', 17.5, 10.15, -19.0, 23.5, 10.2, -13.0)
    for d in (19.5, 21.5):
        P.hbeam(-18.8, -13.2, d, 9.7, d=0.4, w=0.18, mat='TF_Steel', axis='z')
    # floor: painted team ring round the dais
    fx, fy, fz = 20.5, 0.0, -16.0
    K.cyl(TP, fx, 0.0, fz, 4.6, 0.012, seg=64)
    K.cyl('TF_FloorWarm', fx, 0.0, fz, 4.3, 0.016, seg=64)
    # the dais: three round steps, steel lips, team glow inlay, flat flag pad on top
    for (r, y0, h, mat) in ((3.2, 0.0, 0.2, 'TF_Conc'), (2.6, 0.2, 0.2, 'TF_Conc'), (2.0, 0.4, 0.2, 'TF_Tile')):
        K.cyl(mat, fx, y0, fz, r, h, seg=64, col=True)
        K.cyl('TF_Steel', fx, y0 + h - 0.05, fz, r + 0.03, 0.044, seg=64)             # lip sits just under the step top (no z-fight)
    K.cyl(tm('TF_Glow'), fx, 0.6, fz, 1.7, 0.012, seg=64)
    K.cyl('TF_Tile', fx, 0.6, fz, 1.55, 0.016, seg=64)
    K.cyl('TF_Steel', fx, 0.6, fz, 1.0, 0.05, seg=48)
    K.cyl(tm('TF_Glow'), fx, 0.65, fz, 0.35, 0.012, seg=24)
    # whey tanks in the corners: concrete plinth, painted drum with a team band and steel rims, collar into the ceiling
    for (x, z) in ((14.7, -21.6), (27.3, -21.6), (14.7, -11.0), (27.3, -8.7)):
        r = 1.8
        K.box('TF_Conc', x - r - 0.25, 0, z - r - 0.25, x + r + 0.25, 0.4, z + r + 0.25, col=True)
        K.cyl('TF_Machine', x, 0.4, z, r, 6.2, seg=32)
        K.cyl(TP, x, 1.6, z, r + 0.03, 0.7, seg=32)
        for y in (0.4, 3.9, 6.4):
            K.cyl('TF_Steel', x, y, z, r + 0.06, 0.16, seg=32)
        K.cyl('TF_Machine', x, 6.6, z, r, 0.9, seg=32, r2=0.6)
        K.cyl('TF_Steel', x, 7.5, z, 0.6, 0.5, seg=24)
        a, b = r * 0.94, r * 0.39
        for (u, v) in ((a, b), (b, a), (r * 0.72, r * 0.72)):
            K.col(x - u, 0, z - v, x + u, 8.0, z + v)
    # light: daylight down the shaft, team light on the dais, fluorescents
    K.light(fx, 9.0, fz, '#fff1d6', 3.0, 20)
    K.light(fx, 3.0, fz, '#ff9a4a' if T == 'C' else '#6aa6ff', 1.4, 7)
    for (d, z) in ((20.5, -22.6), (20.5, -8.4), (13.6, -16.0), (28.2, -16.0)):
        K.lamp_prop(d, 8.0, z, color='#fff2dc', intensity=1.1, dist=12)
    K.area('Flag Room', 12, -24, 30, -6, 0, team=T, kind='flag')
    K.label('FLAG', fx, 2.0, fz, team=T, kind='flag')
    # ---------------- main corridor ----------------
    K.wall2('x', 24, 36, 4, WT, 0, 10, holes=[(26, 29, 0, 3.0)], lower='TF_Tile', band=1.4)
    K.wall2('x', 24, 36, -4, WT, 0, 5, holes=[(31, 35, 0, 3.2)], lower='TF_Tile', band=1.4)
    K.slab('TF_Ceiling', 24, -4, 36, 4, 5.0, 5.3, col=False)
    P.opening('x', 26, 29, 4, WT, 0, 3.0, mat='Steel')
    P.opening('x', 31, 35, -4, WT, 0, 3.2, mat='Steel')
    K.light(30, 4.6, 0, '#ffe0b0', 1.0, 10)
    # ---------------- packing corridor ----------------
    K.slab('Conc', 30, -24, 36, -4, 5.0, 5.3, col=False)
    K.light(33, 4.6, -14, '#ffe0b0', 1.0, 10)
    K.area('Packing Line', 30, -24, 36, -4, 0, team=T)
    # ---------------- office (second stair to the gallery) ----------------
    K.wall2('x', 24, 36, 15.2, WT, 0, 10, holes=[(33.5, 35.5, 5.8, 9.0)])
    K.box('Plate', 33.5, 5.8, 14.95, 35.5, 6.0, 15.45, col=True, bevel=False)         # floor through the doorway
    P.opening('x', 33.5, 35.5, 15.2, WT, 6.0, 9.0, mat='Steel')
    P.stairs(34.5, 14.95 - RUN6, -PI / 2, 2.0, 0.0, 6.0, kind='steel')
    K.light(29, 9.3, 9, '#fff1d6', 1.0, 12)
    K.area('Control Office', 24, 4, 36, 15, 0, team=T)
