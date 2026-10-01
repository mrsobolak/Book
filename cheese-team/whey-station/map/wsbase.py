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
    K.slab('TF_Grate', 12, -24, 30, -6, -0.3, 0.0, holes=[(24.33, -15.8, 30.0, -12.2), (14.2, -21.8, 24.0, -8.2)])   # flag room walkway ring
    K.slab('TF_FloorWarm', 14.2, -21.8, 24.0, -8.2, -0.9, -0.6)                          # sunken flag floor
    K.slab('AntiSlip', 30, -24, 36, -6, -0.3, 0.0)                              # packing corridor
    K.slab('TF_Floor', 24, -6, 36, 20, -0.3, 0.0)                                  # main corridor + office
    K.slab('CorrWorn', 0, -24, 36, 20, 10.0, 10.3, holes=[(16.0, -18.0, 22.0, -12.0)], col=False)                   # roof
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
    for (a0, a1, top) in ((0, 14.2, -0.3), (14.2, 24.0, -0.9), (24.0, 36, -0.3)):     # lower under the sunken flag-room floor
        K.wall2('x', a0, a1, -16, WT, -4.0, top, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('z', -12, -6, 12, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    for (a0, a1, top) in ((12, 14.2, -0.3), (14.2, 24.0, -0.9), (24.0, 36, -0.3)):
        K.wall2('x', a0, a1, -12, WT, -4.0, top, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.box('TF_Grate', 12.4, -4.02, -13.6, 35.8, -3.98, -12.6)
    # tunnel ceilings (under the slabs above) -- with the stair openings left open
    K.slab('TF_Ceiling', 0, -16, 12, -6, -0.33, -0.3, holes=[(1.33, -10, 7.0, -8)], col=False)
    K.slab('TF_Ceiling', 12, -16, 14.2, -12, -0.33, -0.3, col=False)
    K.slab('TF_Ceiling', 14.2, -16, 24.0, -12, -0.93, -0.9, col=False)
    K.slab('TF_Ceiling', 24.0, -16, 36, -12, -0.33, -0.3, holes=[(24.33, -15.8, 30.0, -12.2)], col=False)
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
    K.wall2('x', 10, 30, -6, WT, 0, 10, holes=[(14, 18, 0, 3.2), (21.5, 27.5, 1.2, 3.0)])
    P.window('x', 21.5, 27.5, -6, WT, 1.2, 3.0, trim='TF_Steel', pane=1.5)
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
    # ---------------- FLAG ROOM (d 12-30, z -24..-6), Turbine-style: sunken warm floor ringed by a grated walkway with
    # railings and corner steps, team-colour lower walls under cream plaster, skylight with team-colour reveals + trusses,
    # flag pad in a hazard-marked corner of the sunken floor, window from the yard ----------------
    TP = tm('TF_Paint')
    K.wall2('z', -24, -6, 12, WT, 0, 8, lower=TP, upper='TF_Plaster', band=1.6)
    K.wall2('z', -24, -4, 30, WT, 0, 8, holes=[(-18, -14, 0, 3.2)], lower=TP, upper='TF_Plaster', band=1.6)
    P.opening('z', -18, -14, 30, WT, 0, 3.2, mat='TF_Steel')
    # the two shared walls get the same finish as overlay panels on their flag-room face
    def overlay(axis, s0, s1, c, f, cuts):
        """cream plaster + team dado + trim on one face of an existing wall (axis 'x': wall along d at z=c)"""
        c0 = c + f * WT / 2; c1 = c0 + f * 0.04          # thick enough to bury the wall's own trim strip
        for (y0, y1, mat) in ((0.0, 1.6, TP), (1.6, 8.0, 'TF_Plaster')):
            a = s0
            for (h0, h1, hy0, hy1) in sorted(cuts) + [(s1, s1, 0, 0)]:
                if h0 > a: K.box(mat, a, y0, min(c0, c1), h0, y1, max(c0, c1))
                if h1 > h0:
                    for (yy0, yy1) in ((y0, max(y0, min(y1, hy0))), (max(y0, min(y1, hy1)), y1)):
                        if yy1 > yy0 + 0.01: K.box(mat, h0, yy0, min(c0, c1), h1, yy1, max(c0, c1))
                a = max(a, h1)
        cc0 = c0 + f * 0.04; cc1 = cc0 + f * 0.025
        a = s0
        for (h0, h1, hy0, hy1) in sorted(cuts) + [(s1, s1, 0, 0)]:
            if hy0 > 1.65 or hy1 < 1.55:
                continue
            if h0 > a: K.box('TF_Steel', a, 1.55, min(cc0, cc1), h0, 1.65, max(cc0, cc1))
            a = max(a, h1)
        if s1 > a: K.box('TF_Steel', a, 1.55, min(cc0, cc1), s1, 1.65, max(cc0, cc1))
    overlay('x', 12.2, 29.8, -24, 1, [])
    overlay('x', 12.2, 29.8, -6, -1, [(13.85, 18.15, 0.0, 3.35), (21.4, 27.6, 1.1, 3.1)])
    # dark cove where walls meet the ceiling
    for (a0, b0, a1, b1) in ((12.2, -23.8, 29.8, -23.7), (12.2, -6.3, 29.8, -6.2), (12.2, -23.8, 12.3, -6.2), (29.7, -23.8, 29.8, -6.2)):
        K.box('TF_Steel', a0, 7.6, b0, a1, 8.0, b1)
    # ceiling + skylight: team-colour reveal up to the roof, three trusses across, glass in the roof
    K.slab('TF_Ceiling', 12, -24, 30, -6, 8.0, 8.3, holes=[(16.0, -18.0, 22.0, -12.0)], col=False)
    for (a0, b0, a1, b1) in ((16.0, -18.0, 22.0, -17.8), (16.0, -12.2, 22.0, -12.0), (16.0, -17.8, 16.2, -12.2), (21.8, -17.8, 22.0, -12.2)):
        K.box(TP, a0, 8.0, b0, a1, 10.0, b1)
    K.box('Glass', 16.0, 10.15, -18.0, 22.0, 10.2, -12.0)
    for d in (17.5, 19.0, 20.5):
        P.hbeam(-17.8, -12.2, d, 9.6, d=0.45, w=0.2, mat='TF_Steel', axis='z')
    # walkway edge round the sunken floor: steel face, hazard nosing, railings with gaps for the four corner steps
    for (a0, b0, a1, b1) in ((14.2, -21.8, 24.0, -21.65), (14.2, -8.35, 24.0, -8.2), (14.2, -21.65, 14.35, -8.35), (23.85, -21.65, 24.0, -8.35)):
        K.box('TF_Steel', a0, -0.6, b0, a1, 0.0, b1)
    for (a0, b0, a1, b1) in ((14.2, -21.95, 24.0, -21.8), (14.2, -8.2, 24.0, -8.05), (14.05, -21.95, 14.2, -8.05), (24.0, -21.95, 24.15, -8.05)):
        K.box('TF_Hazard', a0, 0.0, b0, a1, 0.015, b1, bevel=False)
    P.stairs(16.0, -9.01, -PI / 2, 2.0, -0.6, 0.0, kind='steel', rails=False)         # NW: down from the north walkway
    P.stairs(22.0, -9.01, -PI / 2, 2.0, -0.6, 0.0, kind='steel', rails=False)         # NE
    P.stairs(23.19, -20.0, 0.0, 2.0, -0.6, 0.0, kind='steel', rails=False)            # SE: down from the east landing
    P.stairs(15.01, -12.0, PI, 2.0, -0.6, 0.0, kind='steel', rails=False)             # SW: down from the west walkway
    for (x0, z0, x1, z1) in ((14.2, -21.9, 24.0, -21.9),                                  # south edge
                             (14.2, -8.1, 15.0, -8.1), (17.0, -8.1, 21.0, -8.1), (23.0, -8.1, 24.0, -8.1),   # north edge
                             (14.1, -21.8, 14.1, -13.0), (14.1, -11.0, 14.1, -8.2),        # west edge
                             (24.1, -21.8, 24.1, -21.0), (24.1, -19.0, 24.1, -16.0)):      # east edge (hatch side open to the landing)
        P.rail(x0, z0, x1, z1, 0.0, mat='TF_Steel')
    # flag pad in the south-west corner of the sunken floor, inside a hazard-striped square
    fx, fy, fz = 17.6, -0.6, -18.4
    for (a0, b0, a1, b1) in ((fx - 2.4, fz - 2.4, fx + 2.4, fz - 2.15), (fx - 2.4, fz + 2.15, fx + 2.4, fz + 2.4),
                             (fx - 2.4, fz - 2.15, fx - 2.15, fz + 2.15), (fx + 2.15, fz - 2.15, fx + 2.4, fz + 2.15)):
        K.box('TF_Hazard', a0, fy, b0, a1, fy + 0.015, b1, bevel=False)
    K.box('TF_Conc', fx - 2.15, fy, fz - 2.15, fx + 2.15, fy + 0.01, fz + 2.15, bevel=False)
    K.cyl('TF_Steel', fx, fy, fz, 1.45, 0.07, seg=48, col=True)
    K.cyl('TF_Steel', fx, fy + 0.07, fz, 1.3, 0.03, seg=48, r2=1.2)
    K.cyl(tm('TF_Glow'), fx, fy + 0.07, fz, 1.12, 0.035, seg=48)
    K.cyl('TF_Steel', fx, fy + 0.105, fz, 0.9, 0.012, seg=48)
    K.cyl(tm('TF_Glow'), fx, fy + 0.105, fz, 0.32, 0.03, seg=24)
    # light: warm daylight through the skylight, team light on the pad, fluorescents over the walkway
    K.light(19, 9.0, -15, '#fff1d6', 3.0, 20)
    K.light(fx, 2.5, fz, '#ff9a4a' if T == 'C' else '#6aa6ff', 1.6, 7)
    for (d, z) in ((13.2, -22.9), (13.2, -7.1), (28.9, -7.1), (28.9, -22.9)):
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
