import wsparts
def base(K, team):
    P = wsparts.Parts(K, team)
    K.slab('Epoxy', -20, -10, 0, 10, -0.3, 0.0)
    K.wall('TileW', 'x', -20, 0, -10, 0.3, 0, 6, holes=[(-12, -9, 0, 2.6)])
    K.wall('Brick', 'z', -20, -10, 10, 0, 0.3, 6) if False else K.wall('Brick', 'z', -10, 10, -20, 0.3, 0, 6)
    P.stairs(-15, 5, 0, 1.6, 0, 4)
    P.rail(-18, 8, -10, 8, 0)
    P.ibeam(-5, 0, 0, 6)
