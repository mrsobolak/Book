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
    K.slab('TileFloor', 12, -24, 30, -6, -0.3, 0.0, holes=[(24.33, -15.8, 30.0, -13.6)])   # flag room
    K.slab('AntiSlip', 30, -24, 36, -6, -0.3, 0.0)                              # packing corridor
    K.slab('TF_Floor', 24, -6, 36, 20, -0.3, 0.0)                                  # main corridor + office
    K.slab('CorrWorn', 0, -24, 36, 20, 10.0, 10.3, col=False)                   # roof
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
    K.slab('TF_Ceiling', 12, -16, 36, -12, -0.33, -0.3, holes=[(24.33, -15.8, 30.0, -13.6)], col=False)
    K.box('TF_Hazard', 0.2, -4.0, -15.8, 11.8, -3.99, -15.6)                           # floor edge stripes
    K.box('TF_Hazard', 12.0, -4.0, -15.8, 35.8, -3.99, -15.6)
    for (d, z) in ((4, -11), (17, -14), (24, -14), (33, -14)):
        K.lamp_prop(d, -0.33, z, color='#e8f2ff', intensity=1.1, dist=11)
    K.prop('barrel', 1.0, -4.0, -15.0, 0, col=(-0.3, 0, -0.3, 0.3, 0.9, 0.3))       # sump cover
    K.prop('barrel', 1.0, -4.0, -14.2, 0, col=(-0.3, 0, -0.3, 0.3, 0.9, 0.3))
    K.prop('crate', 9.5, -4.0, -15.0, 0.3, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.area('Brine Tunnel', 0, -16, 36, -6, -4, team=T, kind='tunnel')
    # hatch stair from the tunnel up into the flag room
    P.stairs(30.0, -14.7, PI, 2.0, -4.0, 0.0, kind='steel')                       # clear of the tunnel wall (face at -15.8)
    P.rail(24.33, -13.5, 29.8, -13.5, 0.0); P.rail(24.33, -15.95, 29.8, -15.95, 0.0)
    # ---------------- Loading Yard (hub) ----------------
    K.wall2('x', 10, 30, -6, WT, 0, 10, holes=[(14, 18, 0, 3.2)])
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
    K.prop('barrel', 11.2, 0, 11.6, 0, col=(-0.3, 0, -0.3, 0.3, 0.9, 0.3))
    K.light(17, 9.3, 4, '#ffe9c8', 1.6, 18)
    K.area('Loading Yard', 10, -6, 24, 15, 0, team=T)
    # ---------------- Aging Cellar = FLAG ROOM ----------------
    K.wall2('z', -24, -6, 12, WT, 0, 8)
    K.wall2('z', -24, -4, 30, WT, 0, 8, holes=[(-18, -14, 0, 3.2)])
    P.opening('z', -18, -14, 30, WT, 0, 3.2, mat='Steel')
    K.slab('TF_Ceiling', 12, -24, 30, -6, 8.0, 8.3, holes=[(16.5, -18, 22.5, -12)], col=False)
    for z in (-21.5, -8.5):
        P.hbeam(12, 30, z, 8.0, d=0.4, w=0.2)
    # flag capture pad: stepped round platform with a team-coloured light ring, hazard border, skylight + team spot
    fx, fy, fz = 19.5, 0.0, -15.0          # clear of the hatch stair (d 24.3..30)
    K.cyl('TF_Hazard', fx, 0.0, fz, 3.45, 0.012, seg=48)
    K.cyl('TF_Conc', fx, 0.0, fz, 3.0, 0.15, seg=48, col=True)
    K.cyl(tm('TF_Glow'), fx, 0.15, fz, 2.78, 0.14, seg=48)
    K.cyl('TF_Tile', fx, 0.15, fz, 2.6, 0.15, seg=48, col=True)
    K.cyl('TF_Conc', fx, 0.3, fz, 0.55, 0.12, seg=24, col=True)
    K.cyl(tm('TF_Glow'), fx, 0.42, fz, 0.38, 0.02, seg=24)
    K.box('Glass', fx - 3, 8.05, fz - 3, fx + 3, 8.1, fz + 3)
    K.light(fx, 7.5, fz, '#ffb070' if T == 'C' else '#8ab8ff', 2.6, 14)
    K.light(fx, 5.0, fz, '#fff4e0', 1.2, 10)
    rng = K.rng
    rack(K, P, 13.0, 19.0, -23.6, -22.5, rng); rack(K, P, 22.0, 28.5, -23.6, -22.5, rng)
    rack(K, P, 12.4, 13.5, -20.5, -8.5, rng)
    P.ibeam(27, -21, 0, 7.6, w=0.3)
    K.light(15, 7.4, -9, '#cfe6ff', 1.0, 12)
    K.area('Aging Cellar', 12, -24, 30, -6, 0, team=T, kind='flag')
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
