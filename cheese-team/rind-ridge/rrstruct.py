# Track furniture (rails, sleepers, trestle, mine sheds, checkpoint markers, the cheese payload) and structures.
import math
import numpy as np
import rrlayout as L
import rrtrack
import rrterrain as T
PI = math.pi
GAUGE = 2.4
SPAWNS_OUT = {}


def ground(Hgrid, x, z):
    X, Z, H = Hgrid
    fx = (x - T.X0) / T.CELL; fz = (z - T.Z0) / T.CELL
    j = int(np.clip(math.floor(fx), 0, H.shape[1] - 2)); i = int(np.clip(math.floor(fz), 0, H.shape[0] - 2))
    u, v = fx - j, fz - i
    return float(H[i, j] * (1 - u) * (1 - v) + H[i, j + 1] * u * (1 - v) + H[i + 1, j] * (1 - u) * v + H[i + 1, j + 1] * u * v)


def frame(S, k):
    """position, yaw (kit ry), pitch, lateral unit vector at sample k"""
    a = S[max(0, k - 1)]['p']; b = S[min(len(S) - 1, k + 1)]['p']
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    hl = math.hypot(dx, dz) or 1.0
    yaw = math.atan2(-dz / hl, dx / hl); pitch = math.atan2(dy, hl)
    lat = (-dz / hl, dx / hl)
    return S[k]['p'], yaw, pitch, lat


def seg_box(K, mat, a, b, off, y0, y1, w, col=False):
    """box along the track from point a to b, lateral offset off, vertical y0..y1 above the rail line, width w"""
    dx, dy, dz = b[0] - a[0], b[1] - a[1], b[2] - a[2]
    hl = math.hypot(dx, dz)
    if hl < 1e-6:
        return
    lx, lz = -dz / hl, dx / hl
    cx = (a[0] + b[0]) / 2 + lx * off; cz = (a[2] + b[2]) / 2 + lz * off; cy = (a[1] + b[1]) / 2 + (y0 + y1) / 2
    L3 = math.sqrt(hl * hl + dy * dy)
    K.obox(mat, cx, cy, cz, L3 + 0.02, y1 - y0, w, (0, math.atan2(-dz, dx), math.atan2(dy, hl)), col=col)


def track(K, S, Hg):
    n = len(S)
    for k in range(n - 1):
        a, b = S[k]['p'], S[k + 1]['p']
        kind = S[k]['kind']
        for off in (-GAUGE / 2, GAUGE / 2):
            seg_box(K, 'TF_Steel', a, b, off, 0.30, 0.46, 0.12)                    # rails
        p, yaw, pitch, lat = frame(S, k)
        K.obox('RR_Timber', p[0], p[1] + 0.15, p[2], 0.28, 0.16, 3.4, (0, yaw, pitch))   # sleeper (across the track)
        if kind == 'bridge':
            seg_box(K, 'RR_Planks', a, b, 0, -0.10, 0.07, 5.6, col=True)            # deck
            for off in (-2.75, 2.75):
                seg_box(K, 'RR_Timber', a, b, off, 0.07, 0.17, 0.12)                # toe boards
            if k % 4 == 0:
                g = min(ground(Hg, p[0] + lat[0] * s, p[2] + lat[1] * s) for s in (-2.6, 0, 2.6))
                top = p[1] - 0.1
                for s in (-2.6, -1.0, 1.0, 2.6):
                    x, z = p[0] + lat[0] * s, p[2] + lat[1] * s
                    K.cyl('RR_Timber', x, g - 0.5, z, 0.16, top - g + 0.5, seg=8, col=True)
                K.obox('RR_Timber', p[0], top - 0.15, p[2], 0.3, 0.3, 5.8, (0, yaw, 0))         # cap
                hgt = top - g
                for lvl in range(int(hgt // 4)):
                    yb = g + 1.5 + lvl * 4.0
                    K.obox('RR_Timber', p[0], yb, p[2], 0.2, 0.2, 5.6, (0, yaw, 0))          # girts
                    ang = math.atan2(3.0, 5.2)
                    K.obox('RR_Timber', p[0], yb + 1.5, p[2], 0.15, 6.0, 0.15, (ang * (1 if lvl % 2 else -1), yaw, 0))
            if k % 3 == 0:
                for off in (-2.8, 2.8):
                    x, z = p[0] + lat[0] * off, p[2] + lat[1] * off
                    K.box('RR_Timber', x - 0.06, p[1] + 0.07, z - 0.06, x + 0.06, p[1] + 1.1, z + 0.06)
            for off in (-2.8, 2.8):
                seg_box(K, 'RR_Timber', a, b, off, 1.0, 1.1, 0.1)                   # handrail
        if kind == 'shed' and k % 3 == 0:
            for s in (-3.6, 3.6):
                x, z = p[0] + lat[0] * s, p[2] + lat[1] * s
                K.box('RR_Timber', x - 0.15, p[1], z - 0.15, x + 0.15, p[1] + 5.4, z + 0.15, col=True)
            K.obox('RR_Timber', p[0], p[1] + 5.55, p[2], 0.3, 0.3, 7.8, (0, yaw, 0))
        if kind == 'shed':
            seg_box(K, 'RR_Planks', a, b, 0, 5.7, 5.8, 8.2)                          # plank roof
            seg_box(K, 'RR_Tin', a, b, 0, 5.8, 5.9, 8.6)
    # checkpoint markers: a painted line across the track + a signal post with a team disc
    cps = rrtrack.checkpoints(S)
    for name, s in cps.items():
        k = min(range(n), key=lambda i: abs(S[i]['s'] - s))
        p, yaw, pitch, lat = frame(S, k)
        K.obox('TF_Hazard', p[0], p[1] + 0.02, p[2], 0.6, 0.04, 6.0, (0, yaw, 0))
        x, z = p[0] + lat[0] * 4.2, p[2] + lat[1] * 4.2
        K.cyl('TF_Steel', x, p[1], z, 0.1, 3.4, seg=10, col=True)
        K.cyl('TF_Paint_C', x, p[1] + 3.4, z, 0.55, 0.12, axis='y', seg=24)
        K.label('CP ' + name, x, p[1] + 4.0, z, kind='checkpoint')
    payload(K, S, 0)


def payload(K, S, k):
    """the giant cheese wheel on its rail bogie, parked at sample k"""
    p, yaw, pitch, lat = frame(S, k)
    K.at(p[0], p[1], p[2], yaw)
    K.box('TF_Steel', -1.9, 0.46, -1.35, 1.9, 0.8, 1.35)                               # bogie deck
    K.box('TF_Paint_B', -1.95, 0.8, -1.4, 1.95, 0.95, 1.4)                             # team-painted rim
    for x in (-1.3, 1.3):
        for z in (-GAUGE / 2, GAUGE / 2):
            K.cyl('TF_Steel', x, 0.55, z, 0.32, 0.14, axis='z', seg=16)                # wheels on the rails
    for x in (-1.2, 1.2):
        K.box('RR_Timber', x - 0.35, 0.95, -0.9, x + 0.35, 1.35, 0.9)                  # chocks the wheel sits in
    # the cheese: rind band round a yellow wheel, red wax seal on both faces
    K.cyl('RR_Rind', 0, 2.75, -0.7, 1.75, 1.4, axis='z', seg=40)
    K.cyl('RR_Cheese', 0, 2.75, -0.71, 1.62, 1.42, axis='z', seg=40)
    K.cyl('RR_Wax', 0, 2.75, -0.72, 0.6, 1.44, axis='z', seg=24)
    K.label('PAYLOAD', 0, 5.0, 0, kind='payload')
    K.pop()


def structures(K, S, Hg):
    pass
