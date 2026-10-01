# Whey Station -- MIDDLE (world coords, point-symmetric: half() is built twice, the second time rotated 180 deg).
#  Vat Hall      x -30..30, z -24..24, floor 0, roof 16: six curd vats, brine pit (y -4) in the centre,
#                catwalks at y 6 along both long walls, a conveyor bridge across the pit.
#  Hallways      (Cheddar half, x -40..-30, Turbine-style L turns): main L-hallway z -4..10; gallery junction z 14..24
#                at y 6; brine-tank room z -24..-4 (ground + catwalk); brine tunnel x -40..-5 z -16..-12 at y -4 with a pump chamber halfway.
import math
import wsparts
PI = math.pi
WT = 0.4          # wall thickness


def vat(K, x, z, r=3.0, T='C'):
    """curd vat, clean TF2 look: concrete plinth, painted drum with a team-colour band, steel rims, cone lid"""
    K.box('TF_Conc', x - r - 0.3, 0, z - r - 0.3, x + r + 0.3, 0.5, z + r + 0.3)
    K.box('TF_Hazard', x - r - 0.32, 0.0, z - r - 0.32, x + r + 0.32, 0.12, z + r + 0.32)
    K.cyl('TF_Machine', x, 0.5, z, r, 5.0, seg=32)
    K.cyl('TF_Paint_' + T, x, 2.3, z, r + 0.04, 0.9, seg=32)
    for y in (0.5, 5.3):
        K.cyl('TF_Steel', x, y, z, r + 0.08, 0.2, seg=32)
    K.cyl('TF_Machine', x, 5.5, z, r, 1.3, seg=32, r2=0.9)
    K.cyl('TF_Steel', x, 6.8, z, 0.9, 0.15, seg=24)
    a, b = r * 0.94 + 0.3, r * 0.39 + 0.3
    for (u, v) in ((a, b), (b, a), (r * 0.72 + 0.25, r * 0.72 + 0.25)):
        K.col(x - u, 0, z - v, x + u, 6.8, z + v)


def half(K, T):
    P = wsparts.Parts(K, T)
    # ---------------- Vat Hall (west half; the rotated pass builds the east half): x -30..30, z -24..24, roof 16 ----------------
    TP = P.tm('TF_Paint')
    # floor: dark tile, a concrete work apron around the pit with hazard border, a team line across the hall near the end wall
    K.slab('TF_Floor', -30, -24, 0, 24, -0.3, 0.0, holes=[(-4.8, -8, 0, 8), (-24, -21, -20, -18)])
    for (a0, b0, a1, b1) in ((-11, -12, -5.2, 12), (-5.2, -12, 0, -8.2), (-5.2, 8.2, 0, 12)):
        K.box('TF_Conc', a0, 0.0, b0, a1, 0.012, b1, bevel=False)
    for (a0, b0, a1, b1) in ((-11.2, -12.2, -11, 12.2), (-11, 12, 0, 12.2), (-11, -12.2, 0, -12)):
        K.box('TF_Hazard', a0, 0.0, b0, a1, 0.016, b1, bevel=False)
    K.box(TP, -28.6, 0.0, -24, -28.0, 0.016, 24, bevel=False)
    # roof: clean ceiling panels with a long skylight down the middle
    K.slab('TF_Ceiling', -30, -24, 0, 24, 16.0, 16.4, holes=[(-27, -4, -3, 4)], col=False)
    K.box('Glass', -27, 16.05, -4, -3, 16.1, 3)
    for x in (-27, -23, -19, -15, -11, -7, -3):
        P.hbeam(-24, 24, x, 15.9, d=0.6, w=0.3, axis='z')
    # long wall (north; rotated -> south), full length so both passes overlap cleanly; bigger windows
    WIN = (-26, -18, -10, -2, 6, 14, 22)
    K.wall2('x', -29.8, 29.8, 24, WT, 0, 16, holes=[(x0, x0 + 4, 10.5, 14.5) for x0 in WIN])
    for x0 in WIN:
        P.window('x', x0, x0 + 4, 24, WT, 10.5, 14.5, pane=1.0, transom=True)
    for x in (-27.5, -20, -12, -4, 4, 12, 20, 27.5):
        K.box('TF_Conc', x - 0.35, 6.0, 23.4, x + 0.35, 16, 23.8)                    # pilasters
    K.box(TP, -29.8, 8.6, 23.75, 0, 9.4, 23.8)                                        # team colour band along the wall
    # end wall (west; rotated -> east), full width z -24..24
    K.wall2('z', -24, 24, -30, WT, 0, 16,
           holes=[(4, 10, 0, 4.5), (18.8, 23.5, 5.8, 9), (-23.5, -18.8, 5.8, 9), (-18, -14, 0, 3.2)])
    P.opening('z', 4, 10, -30, WT, 0, 4.5, mat='TF_Steel', w=0.18)
    P.opening('z', -18, -14, -30, WT, 0, 3.2, mat='TF_Steel')
    P.opening('z', 18.8, 23.5, -30, WT, 6, 9, mat='TF_Steel')
    P.opening('z', -23.5, -18.8, -30, WT, 6, 9, mat='TF_Steel')
    K.box(TP, -29.8, 9.6, -23.8, -29.75, 10.4, 23.8)                                  # team band on the end wall
    K.box(TP, -29.8, 4.9, 3.8, -29.75, 5.7, 10.2)                                     # team header over the main door
    # north catwalk (y 6), full length -- grate deck, team-colour fascia
    K.box('TF_Grate', -30, 5.8, 18.8, 30, 6.0, 23.8, col=True, bevel=False)
    K.box(TP, -30, 5.45, 18.7, 30, 5.8, 18.85)                                        # fascia
    for (a, b) in ((-29.8, -9.1), (-6.9, -1.6), (1.6, 29.8)):
        P.rail(a, 18.85, b, 18.85, 6.0, panel=None, mat='TF_Steel')
    for x in (-24, -16, -3.5, 4.5, 16, 24):
        P.ibeam(x, 19.1, 0, 5.45, w=0.28)
    for x in (-26, -20, -14, -8):
        K.lamp_prop(x, 5.45, 21.3, color='#fff2dc', intensity=1.2, dist=12)          # lights under the catwalk
    P.stairs(-8, 18.8 - 32 * 0.27, -PI / 2, 2.0, 0.0, 6.0, kind='steel')           # hall floor -> catwalk
    # bridge across the pit (x -1.5..1.5), north half z 0..18.8: open rails, team fascia
    K.box('TF_Grate', -1.5, 5.8, 0, 1.5, 6.0, 18.8, col=True, bevel=False)
    for s_ in (-1, 1):
        K.box(TP, s_ * 1.5 - 0.06, 5.45, 0, s_ * 1.5 + 0.06, 5.8, 18.8)
        P.rail(s_ * 1.55, 0, s_ * 1.55, 18.8, 6.0, panel=None, mat='TF_Steel')
    P.ibeam(0, 10.0, 0, 5.45, w=0.3)
    # brine pit: channel x -5..5, z -16..16 at y -4 (open to the hall for |z|<8)
    K.slab('TF_Floor', -5, -16, 0, 16, -4.3, -4.0)
    K.wall2('z', -16, 16, -5, WT, -4.0, -0.3, holes=[(-16, -12, -4.0, -1.0)], lower='TF_Tile', upper='TF_Conc', band=1.3)   # top stays under the floor slab
    K.wall2('x', -5, 5, 16, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.box('TF_Grate', -4.6, -4.02, -15.6, -0.2, -3.98, 15.6)
    P.stairs(-3.75, 8 - 21 * 0.27, -PI / 2, 2.0, -4.0, 0.0, kind='conc')            # clear of the pit wall
    P.rail(-5.05, -8, -5.05, 8, 0.0, mat='TF_Steel')
    P.rail(-3.0, 8.05, 5.0, 8.05, 0.0, mat='TF_Steel')
    # cover: vats and stacked crates (library props)
    vat(K, -18, 10.5, T=T); vat(K, -18, -10.5, T=T); vat(K, -10, -13.5, 2.4, T=T)
    K.prop('crate', -9.0, 0, 1.6, 0.2, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('crate', -9.0, 1.2, 1.6, 0.2, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    for x in (-24, -12):
        K.light(x, 13.5, 0, '#fff0d8', 2.2, 30)
    K.light(-18, 9.0, 16, '#ffe9cc', 1.2, 16); K.light(-18, 9.0, -16, '#ffe9cc', 1.2, 16); K.light(0, -1.2, 0, '#bfe3ff', 1.0, 12)

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
    # brine tunnel (LOW route) x -40..-5, z -16..-12, y -4, with a pump chamber (x -27..-17, z -22..-16) halfway:
    # a wider room with cover and a grate window up into the Vat Hall floor, so the long tube is broken up
    K.slab('TF_Floor', -40, -16, -5, -12, -4.3, -4.0)
    K.slab('TF_Floor', -27, -22, -17, -16, -4.3, -4.0)
    K.wall2('x', -40, -5, -16, WT, -4.0, -0.3, holes=[(-27, -17, -4.0, -0.3)], lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('x', -40, -5, -12, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('x', -27, -17, -22, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('z', -22, -16, -27, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    K.wall2('z', -22, -16, -17, WT, -4.0, -0.3, lower='TF_Tile', upper='TF_Conc', band=1.3)
    for x in (-27, -17):                                                               # hazard-striped columns at the chamber mouth
        K.box('TF_Hazard', x - 0.3, -4.0, -16.3, x + 0.3, -0.3, -15.7, col=True)
    K.box('TF_Ceiling', -40, -0.33, -16, -5, -0.3, -12)
    K.box('TF_Ceiling', -27, -0.33, -22, -24, -0.3, -16); K.box('TF_Ceiling', -20, -0.33, -22, -17, -0.3, -16)
    K.box('TF_Ceiling', -24, -0.33, -18, -20, -0.3, -16); K.box('TF_Ceiling', -24, -0.33, -22, -20, -0.3, -21)
    K.box('TF_Grate', -24, -0.08, -21, -20, 0.0, -18, col=True, bevel=False)            # walkable grate window in the hall floor
    K.box('TF_Grate', -39.6, -4.02, -14.5, -5.4, -3.98, -13.5)                            # drain channel
    K.box('TF_Hazard', -40, -4.0, -15.8, -27.3, -3.99, -15.6); K.box('TF_Hazard', -16.7, -4.0, -15.8, -5.2, -3.99, -15.6)
    for (x, z) in ((-36, -14), (-30, -14), (-25.5, -19), (-18.5, -19), (-12, -14)):   # chamber lamps on the ceiling either side of the grate window
        K.lamp_prop(x, -0.33, z, color='#e8f2ff', intensity=1.1, dist=11)
    K.light(-22, -2.0, -19.5, '#fff0d0', 0.9, 8)
    # chamber cover (library props)
    K.prop('crate', -25.8, -4.0, -20.8, 0.2, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('crate', -25.8, -2.8, -20.8, 0.3, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('crate', -24.4, -4.0, -20.9, 1.1, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('pallet_stack', -21.5, -4.0, -17.2, 0.0, col=(-0.7, 0, -0.47, 0.7, 0.8, 0.47))
    K.area('Pump Chamber', -27, -22, -17, -16, -4, kind='tunnel')
    # brine pit dressing
    K.box('TF_Ceiling', -5, -0.33, -16, 0, -0.3, -8); K.box('TF_Ceiling', -5, -0.33, 8, 0, -0.3, 16)
    for z in (-12, 12):
        K.lamp_prop(-2.5, -0.33, z, color='#e8f2ff', intensity=1.0, dist=10)


def middle(K):
    for rot, T in ((0.0, 'C'), (PI, 'B')):
        K.at(0, 0, 0, rot); half(K, T); K.pop()
