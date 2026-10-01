# Track spline: centripetal Catmull-Rom through rrlayout.TRACK, resampled every 1 m.
import math
import rrlayout as L


def _cr(p0, p1, p2, p3, t):
    def tj(ti, a, b):
        return ti + max(1e-6, math.dist(a, b)) ** 0.5
    t0 = 0.0; t1 = tj(t0, p0, p1); t2 = tj(t1, p1, p2); t3 = tj(t2, p2, p3)
    tt = t1 + (t2 - t1) * t
    def lerp(a, b, ta, tb):
        w = (tt - ta) / (tb - ta)
        return [a[i] + (b[i] - a[i]) * w for i in range(3)]
    A1 = lerp(p0, p1, t0, t1); A2 = lerp(p1, p2, t1, t2); A3 = lerp(p2, p3, t2, t3)
    B1 = lerp(A1, A2, t0, t2); B2 = lerp(A2, A3, t1, t3)
    return lerp(B1, B2, t1, t2)


def samples(step=1.0):
    """list of dicts: p (x,y,z), dir (dx,dz unit), s (arc length), kind, seg (control index)"""
    pts = [(x, y, z) for (x, z, y, k) in L.TRACK]
    kinds = [k for (_, _, _, k) in L.TRACK]
    P = [pts[0]] + pts + [pts[-1]]
    dense = []
    for i in range(len(pts) - 1):
        for j in range(40):
            dense.append((_cr(P[i], P[i + 1], P[i + 2], P[i + 3], j / 40.0), kinds[i], i))
    dense.append((list(pts[-1]), kinds[-2], len(pts) - 2))
    out = []; acc = 0.0; nxt = 0.0
    for k in range(len(dense) - 1):
        a, kind, seg = dense[k]; b = dense[k + 1][0]
        L2 = math.dist((a[0], a[2]), (b[0], b[2]))
        while nxt <= acc + L2 and L2 > 1e-9:
            w = (nxt - acc) / L2
            p = [a[i] + (b[i] - a[i]) * w for i in range(3)]
            dx, dz = (b[0] - a[0]) / L2, (b[2] - a[2]) / L2
            out.append({'p': p, 'dir': (dx, dz), 's': nxt, 'kind': kind, 'seg': seg})
            nxt += step
        acc += L2
    return out


def checkpoints(S):
    res = {}
    for name, idx in L.CHECKPOINT_IDX.items():
        x, z, y, _ = L.TRACK[idx]
        best = min(S, key=lambda s: (s['p'][0] - x) ** 2 + (s['p'][2] - z) ** 2)
        res[name] = round(best['s'], 1)
    return res
