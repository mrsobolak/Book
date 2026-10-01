# Terrain heightfield: a mesa with a summit plateau, a hogback hill (cut through by the track at B), a gully (crossed by
# the trestle), tall mesa walls on the south/west map edges and a drop into the canyon on the north/east edges.
# The track bench is carved in (cut and fill) everywhere except over the trestle.
import math
import numpy as np
import rrlayout as L

X0, X1, Z0, Z1, CELL = -232.0, 168.0, -192.0, 152.0, 2.0
BENCH, BLEND = 5.0, 9.0


def _smooth(e0, e1, x):
    t = np.clip((x - e0) / (e1 - e0), 0.0, 1.0)
    return t * t * (3 - 2 * t)


def _noise(x, z):
    return (np.sin(x * 0.037 + 1.3) * np.cos(z * 0.041 - 0.7) + 0.5 * np.sin(x * 0.091 - z * 0.073 + 2.1)
            + 0.25 * np.sin(x * 0.21 + 0.4) * np.sin(z * 0.19 + 1.9))


def natural(x, z):
    mx, mz = L.MESA
    r0 = np.hypot(x - mx, z - mz)
    ang = np.arctan2(z - mz, x - mx)
    # warped radius: lobes, spurs and gullies so the mountain outline is irregular
    warp = 12.0 * np.sin(3 * ang + 0.8) + 7.0 * np.sin(5 * ang - 1.2) + 5.0 * _noise(x * 0.8, z * 0.8)
    r = r0 + warp * _smooth(L.PLATEAU_R - 8, L.PLATEAU_R + 25, r0)
    h = L.PLATEAU_Y * _smooth(L.FOOT_R, L.PLATEAU_R, r) ** 1.5
    # broken strata: terraces with drifting phase, only partly blended -> ledges and red rock bands
    ph = 2.0 * _noise(x * 0.6 + 40, z * 0.6 - 20)
    t = (h + ph) / 7.0; terr = (np.floor(t) + _smooth(0.5, 0.95, t - np.floor(t))) * 7.0 - ph
    h = h + 0.55 * (terr - h) * _smooth(L.PLATEAU_R - 2, L.PLATEAU_R + 10, r)
    h += 1.6 * _noise(x, z) * _smooth(L.PLATEAU_R + 4, L.PLATEAU_R + 20, r)
    # the summit spire (Bleu's bunker is cut into its south face)
    sx, sz, sr, sh = L.SPIRE
    h += sh * _smooth(sr, sr * 0.45, np.hypot(x - sx, z - sz) + 2.5 * _noise(x * 3, z * 3))
    # foothills and buttes round the base
    for (bx, bz, br, bh) in ((-128, -40, 26, 16), (-155, 45, 30, 26), (-70, 125, 24, 20), (45, -158, 30, 14), (128, -125, 20, 22)):
        h += bh * _smooth(br, br * 0.5, np.hypot(x - bx, z - bz))
    h += 15.0 * np.exp(-(((x - 4) / 34.0) ** 2 + ((z + 104) / 20.0) ** 2))             # Hogback Hill
    h -= 15.0 * np.exp(-((z + 24) / 7.5) ** 2) * _smooth(76, 96, x)                    # the gully under the trestle
    h += 44.0 * _smooth(-150, -176, z) + 44.0 * _smooth(-196, -222, x)                 # canyon walls (S, W)
    h += 3.0 * _noise(x * 2.3, z * 2.1) * _smooth(-150, -170, z)
    h -= 70.0 * _smooth(126, 142, z) * _smooth(-40, 0, x)                              # canyon drop (N)
    h -= 70.0 * _smooth(140, 154, x)                                                   # canyon drop (E)
    return np.maximum(h, -60.0)


def grid():
    xs = np.arange(X0, X1 + 1e-6, CELL); zs = np.arange(Z0, Z1 + 1e-6, CELL)
    X, Z = np.meshgrid(xs, zs)          # [iz, ix]
    return X, Z


def carve(X, Z, H, S):
    """flatten a bench along the track; returns H, distance-to-track D, nearest sample index"""
    P = np.array([[s['p'][0], s['p'][2]] for s in S]); Y = np.array([s['p'][1] for s in S])
    bridge = np.array([s['kind'] == 'bridge' for s in S])
    flat = np.stack([X.ravel(), Z.ravel()], 1)
    D = np.full(flat.shape[0], 1e9); I = np.zeros(flat.shape[0], int)
    for k in range(0, len(P), 64):
        d = np.hypot(flat[:, None, 0] - P[None, k:k + 64, 0], flat[:, None, 1] - P[None, k:k + 64, 1])
        j = d.argmin(1); dm = d[np.arange(len(j)), j]
        m = dm < D; D[m] = dm[m]; I[m] = j[m] + k
    D = D.reshape(X.shape); I = I.reshape(X.shape)
    T = Y[I]
    w = 1.0 - _smooth(BENCH, BENCH + BLEND, D)
    w = np.where(bridge[I], 0.0, w)
    H2 = H * (1 - w) + T * w
    # building pads
    for name, (x0, z0, x1, z1, y, alcove) in L.PADS.items():
        if y is None:                                 # forward-spawn pads sit at the level of the nearest track
            cx, cz = (x0 + x1) / 2, (z0 + z1) / 2
            y = float(Y[np.argmin(np.hypot(P[:, 0] - cx, P[:, 1] - cz))])
        PAD_Y[name] = y
        dx = np.maximum(np.maximum(x0 - X, X - x1), 0); dz = np.maximum(np.maximum(z0 - Z, Z - z1), 0)
        dd = np.hypot(dx, dz)
        wp = (dd <= 0.01).astype(float) if alcove else 1.0 - _smooth(0.0, 10.0, dd)
        H2 = H2 * (1 - wp) + y * wp
    return H2, D, I


PAD_Y = {}


def pad_y(name):
    return PAD_Y[name]


def build(K, S, mats=('RR_Sand', 'RR_Rock', 'RR_Road', 'RR_Dirt')):
    """add the terrain mesh to the kit (one bmesh per material, flat-shaded quads split by slope)"""
    from wskit import T2B
    from mathutils import Vector
    X, Z = grid(); H0 = natural(X, Z); H, D, I = carve(X, Z, H0, S)
    nz, nx = H.shape
    sand, rock, road, dirt = mats
    bms = {m: K.bm(m + '~flat') for m in mats}
    vcache = {m: {} for m in mats}

    def V(m, i, j):
        c = vcache[m]; k = (i, j)
        v = c.get(k)
        if v is None:
            v = bms[m].verts.new(T2B((float(X[i, j]), float(H[i, j]), float(Z[i, j])))); c[k] = v
        return v
    for i in range(nz - 1):
        for j in range(nx - 1):
            h = (H[i, j], H[i, j + 1], H[i + 1, j + 1], H[i + 1, j])
            sx = ((h[1] - h[0]) + (h[2] - h[3])) / (2 * CELL); sz = ((h[3] - h[0]) + (h[2] - h[1])) / (2 * CELL)
            slope = math.hypot(sx, sz)
            d = D[i:i + 2, j:j + 2].min()
            if slope > 0.9:
                m = rock
            elif d < BENCH + 0.5:
                m = road
            elif slope > 0.45:
                m = dirt
            else:
                m = sand
            q = [V(m, i, j), V(m, i, j + 1), V(m, i + 1, j + 1), V(m, i + 1, j)]
            bms[m].faces.new(q[::-1])      # (x, -z) flips handedness
    return X, Z, H, D, I
