"""Walkability + route timing for a code-built map (reads ws_data.json colliders: AABBs in game coords, Y up).
    python3 tools/walkcheck.py out/ws_data.json [--png out/walk.png]
Player: radius 0.36, height 1.8, step 0.5, falls allowed. Sprint 6.5 m/s. 2.5D multi-level grid, 0.25 m cells."""
import json, sys, math, heapq, collections
R, H, STEP, CELL, SPRINT = 0.36, 1.8, 0.5, 0.25, 6.5

d = json.load(open(sys.argv[1]))
cols = d['cols']
xs = [c[0] for c in cols] + [c[3] for c in cols]; zs = [c[2] for c in cols] + [c[5] for c in cols]
X0, X1, Z0, Z1 = min(xs) - 1, max(xs) + 1, min(zs) - 1, max(zs) + 1
NX, NZ = int((X1 - X0) / CELL) + 1, int((Z1 - Z0) / CELL) + 1
B = 2.0
buck = collections.defaultdict(list)
for i, c in enumerate(cols):
    for bx in range(int((c[0] - R - X0) // B), int((c[3] + R - X0) // B) + 1):
        for bz in range(int((c[2] - R - Z0) // B), int((c[5] + R - Z0) // B) + 1):
            buck[(bx, bz)].append(i)


def heights(ix, iz):
    x, z = X0 + (ix + 0.5) * CELL, Z0 + (iz + 0.5) * CELL
    near = buck.get((int((x - X0) // B), int((z - Z0) // B)), ())
    tops = sorted({round(cols[i][4], 3) for i in near if cols[i][0] <= x <= cols[i][3] and cols[i][2] <= z <= cols[i][5]})
    out = []
    for h in tops:
        ok = True
        for i in near:
            c = cols[i]
            if c[0] - R < x < c[3] + R and c[2] - R < z < c[5] + R:
                if c[4] > h + STEP and c[1] < h + H:      # something solid in the body volume above the step height
                    ok = False; break
        if ok:
            out.append(h)
    return out


nodes = {}
for ix in range(NX):
    for iz in range(NZ):
        hs = heights(ix, iz)
        if hs:
            nodes[(ix, iz)] = hs


def cell(p):
    return int((p[0] - X0) / CELL), int((p[2] - Z0) / CELL)


def nearest(p):
    ix, iz = cell(p)
    best = None
    for dx in range(-6, 7):
        for dz in range(-6, 7):
            for h in nodes.get((ix + dx, iz + dz), ()):
                dd = dx * dx + dz * dz + ((h - p[1]) / CELL) ** 2
                if best is None or dd < best[0]:
                    best = (dd, (ix + dx, iz + dz, h))
    return best[1] if best else None


def neigh(n):
    ix, iz, h = n
    for dx in (-1, 0, 1):
        for dz in (-1, 0, 1):
            if dx == 0 and dz == 0:
                continue
            for h2 in nodes.get((ix + dx, iz + dz), ()):
                if h2 <= h + STEP + 1e-6 and h2 >= h - 30:
                    # can't step DOWN through a floor: only allow a drop if no node at our height exists there
                    yield (ix + dx, iz + dz, h2), CELL * math.hypot(dx, dz) + abs(h2 - h) * 0.2
    # walking off a ledge: the landing cell can be up to 3 cells out (the body-clearance margin round the ledge)
    for dx in range(-3, 4):
        for dz in range(-3, 4):
            if max(abs(dx), abs(dz)) < 2:
                continue
            for h2 in nodes.get((ix + dx, iz + dz), ()):
                if h - 30 <= h2 < h - STEP:
                    yield (ix + dx, iz + dz, h2), CELL * math.hypot(dx, dz) + abs(h2 - h) * 0.2


def dijkstra(src, targets=None):
    dist = {src: 0.0}; pq = [(0.0, src)]; prev = {}
    while pq:
        dd, n = heapq.heappop(pq)
        if dd > dist.get(n, 1e18):
            continue
        for m, w in neigh(n):
            nd = dd + w
            if nd < dist.get(m, 1e18):
                dist[m] = nd; prev[m] = n; heapq.heappush(pq, (nd, m))
    return dist, prev


def path_len(pts):
    tot = 0.0
    for a, b in zip(pts, pts[1:]):
        na, nb = nearest(a), nearest(b)
        dist, _ = dijkstra(na)
        if nb not in dist:
            return None, (a, b)
        tot += dist[nb]
    return tot, None


S = d['spawns']; F = d['flags']
sC = nearest(S['C']); dist, prev = dijkstra(sC)
reach = set(dist)
total = sum(len(v) for v in nodes.values())
rep = {'nodes': total, 'reachable_from_C': len(reach)}
for k in ('C', 'B'):
    for kind, P in (('spawn', S[k]), ('flag', F[k])):
        n = nearest(P); rep['%s_%s_reachable' % (kind, k)] = n in reach
rep['C_to_flagB_m'] = round(dist.get(nearest(F['B']), -1), 1)
rep['C_to_flagB_s'] = round(rep['C_to_flagB_m'] / SPRINT, 1)
# areas: does each named area contain a reachable node?
miss = []
for a in d.get('areas', []):
    y = a['level']
    ok = any((ix, iz, h) in reach for (ix, iz), hs in nodes.items() for h in hs
             if a['x0'] <= X0 + (ix + .5) * CELL <= a['x1'] and a['z0'] <= Z0 + (iz + .5) * CELL <= a['z1'] and abs(h - y) < 1.0)
    if not ok:
        miss.append('%s(%s)' % (a['name'], a.get('team')))
rep['unreached_areas'] = miss
# route timings through waypoints
sys.path.insert(0, 'map')
try:
    import layout
    for name, wps in layout.ROUTES.items():
        L, bad = path_len(wps)
        rep['route_%s' % name] = (round(L, 1), round(L / SPRINT, 1)) if L else 'BROKEN between %s' % (bad,)
except Exception as e:
    rep['routes_err'] = str(e)
print(json.dumps(rep, indent=1))
if '--png' in sys.argv:
    from PIL import Image
    img = Image.new('RGB', (NX, NZ), (25, 25, 28))
    px = img.load()
    for (ix, iz), hs in nodes.items():
        h = max(hs); r = (ix, iz, h) in reach
        lv = max(hs)
        c = (90, 160, 255) if lv < -1 else ((240, 170, 60) if lv > 3 else (170, 170, 160))
        if not any((ix, iz, hh) in reach for hh in hs):
            c = (200, 40, 40)
        px[ix, NZ - 1 - iz] = c
    img = img.resize((NX * 2, NZ * 2), Image.NEAREST)
    img.save(sys.argv[sys.argv.index('--png') + 1])
