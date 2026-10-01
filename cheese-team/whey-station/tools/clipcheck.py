# clipcheck: find visible coplanar overlapping wall faces (z-fighting) in the built map -- python3 tools/clipcheck.py
import sys, os, collections
os.chdir('/home/user/Book/cheese-team/whey-station'); sys.path.insert(0, '.')
import build, bpy
build.run('/none', 'out', export=False)
faces = collections.defaultdict(list)
for o in bpy.data.objects:
    if o.type != 'MESH': continue
    mw = o.matrix_world
    for p in o.data.polygons:
        n = mw.to_3x3() @ p.normal
        ax = max(range(3), key=lambda i: abs(n[i]))
        if abs(n[ax]) < 0.999 or p.area < 0.02: continue
        vs = [mw @ o.data.vertices[i].co for i in p.vertices]
        c = round(vs[0][ax], 3)
        if ax == 2: continue
        u, v = [i for i in range(3) if i != ax]
        r = (min(x[u] for x in vs), min(x[v] for x in vs), max(x[u] for x in vs), max(x[v] for x in vs))
        faces[(ax, c)].append((r, o.name, n[ax] > 0, p.index))
hits = collections.Counter(); where = collections.defaultdict(list)
from mathutils import Vector
dg = bpy.context.evaluated_depsgraph_get(); sc = bpy.context.scene
def visible(ax, c, u, v, pos):
    q = [0, 0, 0]; q[ax] = c; uu, vv = [i for i in range(3) if i != ax]; q[uu] = u; q[vv] = v
    n = Vector((0, 0, 0)); n[ax] = 1 if pos else -1
    o = Vector(q) + n * 0.01
    hit, loc, nor, idx, ob, mx = sc.ray_cast(dg, o, n, distance=50)
    if not hit: return True
    return nor.dot(n) < 0
for key, fs in faces.items():
    if len(fs) < 2: continue
    fs.sort()
    for i in range(len(fs)):
        a = fs[i]
        for j in range(i + 1, len(fs)):
            b = fs[j]
            if b[0][0] >= a[0][2]: break
            if a[2] != b[2]: continue          # opposite normals touching = fine
            ou = min(a[0][2], b[0][2]) - max(a[0][0], b[0][0]); ov = min(a[0][3], b[0][3]) - max(a[0][1], b[0][1])
            if ou > 0.05 and ov > 0.05 and visible(key[0], key[1], (max(a[0][0], b[0][0]) + min(a[0][2], b[0][2])) / 2, (max(a[0][1], b[0][1]) + min(a[0][3], b[0][3])) / 2, a[2]):
                k = tuple(sorted((a[1].split('__')[-1], b[1].split('__')[-1])))
                hits[k] += 1
                if len(where[k]) < 4:
                    ax, c = key; cen = [0, 0, 0]; uu, vv = [i for i in range(3) if i != ax]
                    cen[ax] = c; cen[uu] = round((max(a[0][0], b[0][0]) + min(a[0][2], b[0][2])) / 2, 1); cen[vv] = round((max(a[0][1], b[0][1]) + min(a[0][3], b[0][3])) / 2, 1)
                    where[k].append((a[1].split('__')[0], cen))
for k, n in hits.most_common(40):
    print(n, k, where[k])
