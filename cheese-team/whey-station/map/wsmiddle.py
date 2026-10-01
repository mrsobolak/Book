# Whey Station v4 -- MIDDLE HALL (world coords, point-symmetric: half() is built twice, the 2nd time rotated 180 deg).
#   One big plain hall x -28..28, z -16..16, ceiling 12, tall windows on both long walls.
#   MAIN: the ground floor between the two main doors, cover = library props (containers, crates, barrels).
#   HIGH: the bridge (y 6, z -2..2) runs straight from base to base; one stair up to it per side.
#   LOW: tunnel (y -4) z -9..-5 under the Cheddar half -> cross tunnel x -2..2 -> z 5..9 under the Bleu half.
import math
import wsparts
PI = math.pi
WT = 0.4


def half(K, T):
    P = wsparts.Parts(K, T)
    PT = P.tm('TF_Paint')
    K.slab('TF_Floor', -28, -16, 0, 16, -0.3, 0.0)
    K.slab('TF_Ceiling', -28, -16, 0, 16, 12.0, 12.3, holes=[(-20, -8, -6, 6)], col=False)
    K.box('Glass', -20, 12.05, -6, -8, 12.1, 6)
    WIN = [(-23, -19), (-13, -9), (-3, 1), (9, 13), (19, 23)]
    K.wall2('x', -28, 28, 16, WT, 0, 12, holes=[(a, b, 6.5, 10.5) for a, b in WIN])
    for a, b in WIN:
        P.window('x', a, b, 16, WT, 6.5, 10.5, trim='TF_Steel', pane=1.0, transom=True)
    # bridge (y 6, z -2..2), x -28..0
    K.box('TF_Grate', -28, 5.8, -2, 0, 6.0, 2, col=True, bevel=False)
    for s in (-1, 1):
        K.box('TF_Steel', -28, 5.45, s * 2.0 - 0.1, 0, 5.8, s * 2.0 + 0.1)
    P.rail(-28, -2.05, 0, -2.05, 6.0, mat='TF_Steel', panel=PT)
    P.rail(-28, 2.05, -12, 2.05, 6.0, mat='TF_Steel', panel=PT); P.rail(-10, 2.05, 0, 2.05, 6.0, mat='TF_Steel', panel=PT)
    K.box('TF_Conc', -12, 5.7, 2.0, -10, 6.0, 4.0, col=True, bevel=False)
    P.rail(-12.05, 2.0, -12.05, 4.0, 6.0, mat='TF_Steel'); P.rail(-12, 4.05, -10, 4.05, 6.0, mat='TF_Steel')
    P.stairs(-2.0, 3.0, PI, 2.0, 0.0, 6.0, kind='steel', going=0.25)                      # x -2 -> -10 at z 2..4
    for x in (-20, -6):
        K.box('TF_Steel', x - 0.15, 0, -2.0, x + 0.15, 5.45, -1.7, col=True)               # bridge posts
        K.box('TF_Steel', x - 0.15, 0, 1.7, x + 0.15, 5.45, 2.0, col=True)
    # cover: library props
    K.prop('container', -18, 0, -9.0, 0.0, col=(-3.0, 0, -1.25, 3.0, 2.6, 1.25))
    K.prop('container', -7, 0, 10.5, PI / 2, col=(-3.0, 0, -1.25, 3.0, 2.6, 1.25))
    K.prop('crate', -23, 0, 7.0, 0.3, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('crate', -22, 0, 8.3, 1.1, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('crate', -22.5, 1.2, 7.6, 0.6, col=(-0.6, 0, -0.6, 0.6, 1.2, 0.6))
    K.prop('barrel', -10, 0, -5.0, 0, col=(-0.35, 0, -0.35, 0.35, 0.9, 0.35))
    K.prop('barrel', -9.2, 0, -5.6, 0, col=(-0.35, 0, -0.35, 0.35, 0.9, 0.35))
    K.prop('pallet_stack', -2.5, 0, -10.0, 0.2, col=(-0.7, 0, -0.6, 0.7, 1.0, 0.6))
    # tunnel: Cheddar side z -9..-5 x -28..-2, cross tunnel x -2..2 z -9..9
    K.slab('TF_Conc', -28, -9, -2, -5, -4.3, -4.0)
    K.wall2('x', -28, -2, -9, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.wall2('x', -28, -2, -5, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.slab('TF_Conc', -2, -9, 0, 9, -4.3, -4.0)
    K.wall2('z', -9, 9, -2, WT, -4.0, -0.3, holes=[(-9, -5, -4.0, -0.3)], lower='TF_Hazard', band=0.3, upper='TF_Tile')
    K.wall2('x', -2, 2, 9, WT, -4.0, -0.3, lower='TF_Hazard', band=0.3, upper='TF_Tile')
    for (x, z) in ((-21, -7), (-11, -7), (0, -3)):
        K.light(x, -0.8, z, '#bfe0ff', 0.9, 10)
    for (x, z) in ((-21, -8), (-21, 8), (-8, -8), (-8, 8)):
        K.lamp_prop(x, 9.5, z, intensity=1.8, dist=20)
    K.area('Hall', -28, -16, 0, 16, 0, kind='middle')


def middle(K):
    for rot, T in ((0.0, 'C'), (PI, 'B')):
        K.at(0, 0, 0, rot); half(K, T); K.pop()
