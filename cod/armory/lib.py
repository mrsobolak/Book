"""
Shared hard-surface toolkit for the armory weapons (Blender 4.0, run headless).

Modelling axes: +X = muzzle, +Y = right side, +Z = up, bore axis on z = 0.
Units are metres at real scale.

Every part is a profile prism, a lathe, a rod or a lofted blade, optionally cut
with exact booleans. `finalize()` bevels, merges parts per group, bakes
per-vertex AO + convexity/concavity into COLOR_0 and exports a GLB.
"""
import bpy, bmesh, math, os
import numpy as np
from mathutils import Matrix, Vector

scene = None
COL = None
MAT = {}

MATERIALS = {
    "Paint":       ("#2c2e31", 0.0, 0.55),   # cerakote / anodising (takes camo)
    "Polymer":     ("#222325", 0.0, 0.60),   # glass-filled nylon (takes camo)
    "Grip":        ("#1e1f21", 0.0, 0.75),   # stippled polymer
    "Steel":       ("#3b3d40", 1.0, 0.45),   # phosphate / nitride steel
    "BrightSteel": ("#a0a4a8", 1.0, 0.25),
    "Rubber":      ("#161616", 0.0, 0.90),
    "Optic":       ("#1a1b1d", 0.2, 0.40),
    "Suppressor":  ("#2b2927", 0.1, 0.60),
    "Glass":       ("#a8c4d4", 0.0, 0.05),
    "Reticle":     ("#ff2a1a", 0.0, 0.50),
    "Marking":     ("#cfcec6", 0.0, 0.60),
    "Wood":        ("#6b3b1f", 0.0, 0.50),
    "Brass":       ("#b8913f", 1.0, 0.30),
    "Blade":       ("#b5b8bb", 1.0, 0.28),   # satin-ground edge
    "Stainless":   ("#8e9296", 1.0, 0.30),   # brushed stainless frames
    "Warhead":     ("#4a4f2a", 0.0, 0.65),   # olive drab ordnance paint
    "Stripe":      ("#d4ad1f", 0.0, 0.55),   # yellow HE band
    "ShellHull":   ("#9b1d1d", 0.0, 0.45),   # 12 ga plastic hull
    "Tritium":     ("#7dff5a", 0.0, 0.50),   # night-sight inserts
    "Copper":      ("#b36a3a", 1.0, 0.30),   # bullet jackets
    # ---- character palette (TF2 viewer re-shades these by name)
    "Cheese":      ("#f2c14e", 0.0, 0.55), "Rind": ("#e0902a", 0.0, 0.45), "Skin": ("#d99a74", 0.0, 0.6),
    "Team":        ("#b8383b", 0.0, 0.7),  "Team2": ("#7a2a28", 0.0, 0.7), "Pants": ("#7d6d52", 0.0, 0.8),
    "Boots":       ("#4a3222", 0.0, 0.6),  "Glove": ("#2e2723", 0.0, 0.6), "Leather": ("#6b4428", 0.0, 0.55),
    "GooglyWhite": ("#f4f1ea", 0.0, 0.3),  "Pupil": ("#111111", 0.0, 0.3), "Wax": ("#b8383b", 0.0, 0.35),
    "Cloth":       ("#d8cfbd", 0.0, 0.85), "Mouth": ("#5a1e14", 0.0, 0.6), "Teeth": ("#f3efe4", 0.0, 0.4),
}

def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def reset():
    global scene, COL
    bpy.ops.wm.read_factory_settings(use_empty=True)
    scene = bpy.context.scene
    COL = scene.collection
    MAT.clear()
    for name, (hexcol, metallic, rough) in MATERIALS.items():
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        b = m.node_tree.nodes["Principled BSDF"]
        r, g, bl = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
        b.inputs["Base Color"].default_value = (_lin(r), _lin(g), _lin(bl), 1)
        b.inputs["Metallic"].default_value = metallic
        b.inputs["Roughness"].default_value = rough
        MAT[name] = m

# ------------------------------------------------------------------ 2D helpers
def path(cmds):
    """SVG-like: ('M',x,y) ('L',x,y) ('Q',(cx,cy),(x,y),n) ('A',cx,cy,r,deg0,deg1,n)"""
    pts, cur = [], None
    for c in cmds:
        k = c[0]
        if k in "ML":
            cur = (c[1], c[2]); pts.append(cur)
        elif k == "Q":
            (cx, cy), (x, y) = c[1], c[2]
            n = c[3] if len(c) > 3 else 8
            for i in range(1, n + 1):
                t = i / n
                a, b, d = (1 - t) ** 2, 2 * (1 - t) * t, t * t
                pts.append((a * cur[0] + b * cx + d * x, a * cur[1] + b * cy + d * y))
            cur = (x, y)
        elif k == "A":
            _, cx, cy, r, a0, a1, n = c
            for i in range(n + 1):
                a = math.radians(a0 + (a1 - a0) * i / n)
                cur = (cx + r * math.cos(a), cy + r * math.sin(a)); pts.append(cur)
    out = []
    for p in pts:
        if not out or math.dist(p, out[-1]) > 1e-7:
            out.append(p)
    if math.dist(out[0], out[-1]) < 1e-7:
        out.pop()
    return out

def rrect(x0, y0, x1, y1, r, n=4):
    r = min(r, (x1 - x0) / 2 - 1e-6, (y1 - y0) / 2 - 1e-6)
    return path([("A", x1 - r, y0 + r, r, -90, 0, n), ("A", x1 - r, y1 - r, r, 0, 90, n),
                 ("A", x0 + r, y1 - r, r, 90, 180, n), ("A", x0 + r, y0 + r, r, 180, 270, n)])

def circle(cx, cy, r, n=32):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]

def superellipse(a, b, cy=0.0, cz=0.0, e=4.0, n=72):
    pts = []
    for i in range(n):
        t = 2 * math.pi * i / n
        c, s = math.cos(t), math.sin(t)
        pts.append((cy + a * math.copysign(abs(c) ** (2 / e), c), cz + b * math.copysign(abs(s) ** (2 / e), s)))
    return pts

def smoothstep(e0, e1, v):
    t = min(max((v - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)

def rounded_lathe_end(x0, x1, r, n=6):
    """(a, r) profile for a rod with hemispherical ends."""
    rr = min(r, (x1 - x0) / 2)
    prof = [(x0, 0.0)]
    for i in range(1, n + 1):
        a = math.pi / 2 * i / n
        prof.append((x0 + rr - rr * math.cos(a), rr * math.sin(a)))
    for i in range(0, n):
        a = math.pi / 2 * i / n
        prof.append((x1 - rr + rr * math.sin(a), rr * math.cos(a)))
    prof.append((x1, 0.0))
    return prof

# ------------------------------------------------------------------ bmesh builders (return new verts)
def _P(plane, u, v, w):
    if plane == "XZ": return (u, w, v)
    if plane == "YZ": return (w, u, v)
    return (u, v, w)  # XY

def bm_prism(bm, pts, offset, thick, plane="XZ", taper=None):
    lo, hi = [], []
    for u, v in pts:
        s = taper(u, v) if taper else 1.0
        lo.append(bm.verts.new(_P(plane, u, v, offset - thick / 2 * s)))
        hi.append(bm.verts.new(_P(plane, u, v, offset + thick / 2 * s)))
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
    return lo + hi

def bm_tube(bm, outer, inner, a0, a1, plane="YZ"):
    n = len(outer)
    O0 = [bm.verts.new(_P(plane, u, v, a0)) for u, v in outer]
    O1 = [bm.verts.new(_P(plane, u, v, a1)) for u, v in outer]
    I0 = [bm.verts.new(_P(plane, u, v, a0)) for u, v in inner]
    I1 = [bm.verts.new(_P(plane, u, v, a1)) for u, v in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([O0[i], O0[j], O1[j], O1[i]])
        bm.faces.new([I0[j], I0[i], I1[i], I1[j]])
        bm.faces.new([O0[j], O0[i], I0[i], I0[j]])
        bm.faces.new([O1[i], O1[j], I1[j], I1[i]])
    return O0 + O1 + I0 + I1

def bm_lathe(bm, prof, seg=48, axis="X", c=(0, 0, 0), closed=False, phase=0.0):
    def pt(a, u, v):
        if axis == "X": return (c[0] + a, c[1] + u, c[2] + v)
        if axis == "Y": return (c[0] + u, c[1] + a, c[2] + v)
        return (c[0] + u, c[1] + v, c[2] + a)
    rings, new = [], []
    for a, r in prof:
        if r < 1e-9:
            ring = [bm.verts.new(pt(a, 0, 0))]
        else:
            ring = [bm.verts.new(pt(a, r * math.cos(phase + 2 * math.pi * i / seg), r * math.sin(phase + 2 * math.pi * i / seg)))
                    for i in range(seg)]
        rings.append(ring); new += ring
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for A, B in pairs:
        for i in range(seg):
            j = (i + 1) % seg
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                bm.faces.new([A[0], B[j], B[i]])
            elif len(B) == 1:
                bm.faces.new([A[i], A[j], B[0]])
            else:
                bm.faces.new([A[i], A[j], B[j], B[i]])
    return new

def bm_loft(bm, stations, seg=32, caps=True, up=(0, 0, 1)):
    """Elliptical tube lofted through stations: [(center(3), rx, ry), ...] (>= 2).
    rx lies along the sideways axis (cross(up, spine)), ry along the local up. Returns verts."""
    cs = [Vector(st[0]) for st in stations]
    rings = []
    upv = Vector(up)
    for i, (c, rx, ry) in enumerate(stations):
        p, n = cs[max(i - 1, 0)], cs[min(i + 1, len(cs) - 1)]
        d = (n - p).normalized()
        side = upv.cross(d)
        if side.length < 1e-6:
            side = Vector((1, 0, 0)).cross(d)
        side.normalize()
        u = d.cross(side).normalized()
        rings.append([bm.verts.new(Vector(c) + side * (rx * math.cos(2 * math.pi * k / seg)) + u * (ry * math.sin(2 * math.pi * k / seg)))
                      for k in range(seg)])
    for A, B in zip(rings, rings[1:]):
        for k in range(seg):
            j = (k + 1) % seg
            bm.faces.new([A[k], A[j], B[j], B[k]])
    if caps:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    return [v for r in rings for v in r]

def bm_ellipsoid(bm, c, rx, ry, rz, seg=32, rings=16):
    """Axis-aligned ellipsoid centred at c."""
    prof = [(-rz, 0.0)] + [(-rz * math.cos(math.pi * i / rings), math.sin(math.pi * i / rings)) for i in range(1, rings)] + [(rz, 0.0)]
    vs = bm_lathe(bm, prof, seg, "Z", (0, 0, 0))
    for v in vs:
        v.co = Vector((c[0] + v.co.x * rx, c[1] + v.co.y * ry, c[2] + v.co.z))
    return vs

def bm_box(bm, x0, x1, y0, y1, z0, z1):
    return bm_prism(bm, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], (y0 + y1) / 2, y1 - y0, "XZ")

def bm_place(bm, verts, p0, p1):
    """Take geometry built along +X from x=0..L at origin and align it to the segment p0->p1."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    rot = Vector((1, 0, 0)).rotation_difference(d).to_matrix()
    for v in verts:
        v.co = rot @ v.co + p0

def bm_rod(bm, p0, p1, r, seg=20, rounded=False, prof=None):
    """Cylinder (or custom (a, r) profile along the segment length) between two points."""
    L = (Vector(p1) - Vector(p0)).length
    if prof is None:
        prof = rounded_lathe_end(0, L, r) if rounded else [(0, 0), (0, r), (L, r), (L, 0)]
    vs = bm_lathe(bm, prof, seg, "X", (0, 0, 0))
    bm_place(bm, vs, p0, p1)
    return vs

def rotate_verts(bm, verts, deg, axis, center):
    bmesh.ops.rotate(bm, verts=verts, cent=center, matrix=Matrix.Rotation(math.radians(deg), 3, axis))

def mirror_y(verts):
    for v in verts:
        v.co.y = -v.co.y

# ------------------------------------------------------------------ objects
def mk(name, bm, mat, group="base", bev=None, segs=2, bang=30, smooth=35, mats=None, subsurf=0):
    """subsurf=N adds a Catmull-Clark subdivision (N levels) before any boolean cut; such parts skip densify."""
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in (mats or [mat]):
        me.materials.append(MAT[m])
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    me.use_auto_smooth = True
    me.auto_smooth_angle = math.radians(smooth)
    ob["group"] = group
    if bev:
        ob["bev"], ob["segs"], ob["bang"] = bev, segs, bang
    if subsurf:
        md = ob.modifiers.new("subsurf", "SUBSURF")
        md.levels = md.render_levels = subsurf
        ob["nodensify"] = True
    return ob

def loft(name, stations, mat, group="base", seg=32, caps=True, up=(0, 0, 1), **kw):
    bm = bmesh.new(); bm_loft(bm, stations, seg, caps, up)
    return mk(name, bm, mat, group, **kw)

def ellipsoid(name, c, rx, ry, rz, mat, group="base", seg=32, rings=16, **kw):
    bm = bmesh.new(); bm_ellipsoid(bm, c, rx, ry, rz, seg, rings)
    return mk(name, bm, mat, group, **kw)

def cut(ob, bm):
    c = mk("cutter", bm, "Steel", group="__cutter")
    c.hide_render = True
    md = ob.modifiers.new("cut", "BOOLEAN")
    md.operation, md.solver, md.object = "DIFFERENCE", "EXACT", c
    md.use_self = True

def prism(name, pts, offset, thick, mat, plane="XZ", group="base", taper=None, **kw):
    bm = bmesh.new(); bm_prism(bm, pts, offset, thick, plane, taper)
    return mk(name, bm, mat, group, **kw)

def lathe(name, prof, mat, group="base", seg=48, axis="X", c=(0, 0, 0), closed=False, **kw):
    bm = bmesh.new(); bm_lathe(bm, prof, seg, axis, c, closed)
    return mk(name, bm, mat, group, **kw)

def rod(name, p0, p1, r, mat, group="base", seg=20, rounded=False, prof=None, **kw):
    bm = bmesh.new(); bm_rod(bm, p0, p1, r, seg, rounded, prof)
    return mk(name, bm, mat, group, **kw)

def text(body, size, x, z, y_face, name, group="base", mat="Marking"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body, cu.size, cu.extrude, cu.align_x = body, size, 0.00012, "CENTER"
    cu.materials.append(MAT[mat])
    ob = bpy.data.objects.new(name, cu)
    COL.objects.link(ob)
    ob.rotation_euler = (math.radians(90), 0, 0) if y_face < 0 else (math.radians(90), 0, math.radians(180))
    ob.location = (x, y_face, z)
    ob["group"] = group
    return ob

def rail(name, x0, x1, zb, zt=0.0285, mat="Paint", group="base", flip=False):
    """MIL-STD-1913 rail from x0..x1; top at zt, stem down to zb. flip=True hangs it upside down."""
    s = -1 if flip else 1
    sec = [(-0.0078, zt), (0.0078, zt), (0.0106, zt - s * 0.0028), (0.0106, zt - s * 0.0038), (0.0080, zt - s * 0.0062),
           (0.0080, zb), (-0.0080, zb), (-0.0080, zt - s * 0.0062), (-0.0106, zt - s * 0.0038), (-0.0106, zt - s * 0.0028)]
    ob = prism(name, sec, (x0 + x1) / 2, x1 - x0, mat, plane="YZ", group=group, bev=0.0004, segs=1)
    bm = bmesh.new()
    x = x0 + 0.0055
    while x + 0.0026 < x1 - 0.002:
        z0, z1 = (zt - 0.0030, zt + 0.002) if not flip else (zt - 0.002, zt + 0.0030)
        bm_box(bm, x - 0.00262, x + 0.00262, -0.013, 0.013, z0, z1)
        x += 0.01001
    cut(ob, bm)
    return ob

def pins(name, spots, y_face, mat="Steel", group="base"):
    """Flush pin heads on both sides: spots = [(x, z, r), ...]."""
    bm = bmesh.new()
    for x, z, r in spots:
        for side in (1, -1):
            vs = bm_lathe(bm, [(0, 0), (0, r), (0.0006, r), (0.0009, r * 0.8), (0.0009, 0)], 24, "Y", (x, y_face - 0.0002, z))
            if side < 0:
                mirror_y(vs)
    return mk(name, bm, mat, group, bev=0.0002, segs=1)

def cartridge(bm, x0, y, z, case_r, case_l, bullet_l, neck_r=None):
    """Bottlenecked cartridge along +X (case in brass, bullet added separately by caller if needed)."""
    neck_r = neck_r or case_r * 0.62
    prof = [(x0, 0), (x0, case_r * 0.92), (x0 + 0.0012, case_r * 0.92), (x0 + 0.0016, case_r * 0.78),
            (x0 + 0.0030, case_r * 0.78), (x0 + 0.0036, case_r), (x0 + case_l * 0.78, case_r * 0.95),
            (x0 + case_l * 0.86, neck_r), (x0 + case_l, neck_r), (x0 + case_l, 0)]
    bm_lathe(bm, prof, 20, "X", (0, y, z))
    bprof = [(x0 + case_l - 0.002, 0), (x0 + case_l - 0.002, neck_r * 0.97)]
    for i in range(1, 7):
        t = i / 6
        bprof.append((x0 + case_l + bullet_l * t, neck_r * 0.97 * math.cos(t * math.pi / 2) ** 0.7 + 0.0002 * (1 - t)))
    bprof.append((x0 + case_l + bullet_l, 0))
    return bprof

def blade(name, stations, mats=("Paint", "Blade"), group="base", bev=None):
    """Loft a knife blade. stations: list of (x, z_edge, z_grind, z_spine, t_grind, t_spine);
    the final station is collapsed to the tip point. Grind faces get material 1."""
    bm = bmesh.new()
    rings = []
    for i, (x, ze, zg, zs, tg, ts) in enumerate(stations):
        if i == len(stations) - 1:
            p = bm.verts.new((x, 0, ze))
            rings.append([p] * 5 + [p])
            continue
        e = bm.verts.new((x, 0, ze))
        gl, gr = bm.verts.new((x, -tg, zg)), bm.verts.new((x, tg, zg))
        sl, sr = bm.verts.new((x, -ts, zs)), bm.verts.new((x, ts, zs))
        rings.append([e, gr, sr, sl, gl, e])
    faces = []
    for A, B in zip(rings, rings[1:]):
        for k in range(5):
            quad = [A[k], A[k + 1], B[k + 1], B[k]]
            uniq = []
            for v in quad:
                if v not in uniq:
                    uniq.append(v)
            if len(uniq) >= 3:
                f = bm.faces.new(uniq)
                f.material_index = 1 if k in (0, 4) else 0
    # butt cap
    A = rings[0]
    f = bm.faces.new([A[0], A[4], A[3], A[2], A[1]])
    return mk(name, bm, mats[0], group, mats=list(mats), bev=bev, segs=2, smooth=25)

# ------------------------------------------------------------------ finalize
def _curvature(me):
    n = len(me.vertices)
    co = np.empty(n * 3); me.vertices.foreach_get("co", co); co = co.reshape(-1, 3)
    nr = np.empty(n * 3); me.vertex_normals.foreach_get("vector", nr); nr = nr.reshape(-1, 3)
    e = np.empty(len(me.edges) * 2, dtype=np.int64); me.edges.foreach_get("vertices", e); e = e.reshape(-1, 2)
    d = co[e[:, 1]] - co[e[:, 0]]
    d /= (np.linalg.norm(d, axis=1) + 1e-12)[:, None]
    acc, cnt = np.zeros(n), np.zeros(n)
    np.add.at(acc, e[:, 0], -(nr[e[:, 0]] * d).sum(1)); np.add.at(acc, e[:, 1], (nr[e[:, 1]] * d).sum(1))
    np.add.at(cnt, e[:, 0], 1); np.add.at(cnt, e[:, 1], 1)
    return acc / np.maximum(cnt, 1)

def densify(ob, max_len=0.010):
    """Split long edges so per-vertex AO / wear masks are not smeared along long faces."""
    bm = bmesh.new(); bm.from_mesh(ob.data)
    for _ in range(4):
        long_edges = [e for e in bm.edges if e.calc_length() > max_len * 1.5]
        if not long_edges:
            break
        bmesh.ops.subdivide_edges(bm, edges=long_edges, cuts=1, use_grid_fill=True)
    bm.to_mesh(ob.data); bm.free()

def finalize(out_path, bake=True, ao_distance=0.035, samples=48):
    for o in list(scene.objects):
        if o.type == "MESH" and o.get("group") != "__cutter" and not o.get("nodensify"):
            densify(o)
    for o in list(scene.objects):
        if o.type == "MESH" and o.get("bev"):
            md = o.modifiers.new("bev", "BEVEL")
            md.width, md.segments, md.profile = o["bev"], o["segs"], 0.5
            md.limit_method, md.angle_limit = "ANGLE", math.radians(o["bang"])
            md.use_clamp_overlap = True
            md.harden_normals = True
            md.miter_outer = "MITER_ARC"
    parts = [o for o in scene.objects if o.get("group") != "__cutter"]
    bpy.ops.object.select_all(action="DESELECT")
    for o in parts:
        o.select_set(True)
    bpy.context.view_layer.objects.active = parts[0]
    bpy.ops.object.convert(target="MESH")
    for o in [o for o in scene.objects if o.get("group") == "__cutter"]:
        bpy.data.objects.remove(o, do_unlink=True)
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.object.transform_apply(location=True, rotation=True, scale=True)

    groups = {}
    for o in scene.objects:
        groups.setdefault(o["group"], []).append(o)
    merged = {}
    for g, obs in groups.items():
        bpy.ops.object.select_all(action="DESELECT")
        for o in obs:
            o.select_set(True)
        bpy.context.view_layer.objects.active = obs[0]
        if len(obs) > 1:
            bpy.ops.object.join()
        ob = bpy.context.view_layer.objects.active
        ob.name = ob.data.name = g
        ob.data.use_auto_smooth = True
        merged[g] = ob

    ao = {}
    if bake:
        scene.render.engine = "CYCLES"
        scene.cycles.device = "CPU"
        scene.cycles.samples = samples
        scene.world = bpy.data.worlds.new("W")
        scene.world.light_settings.distance = ao_distance
        scene.render.bake.target = "VERTEX_COLORS"
        for g, ob in merged.items():
            vis = {g, "base"}
            for o in merged.values():
                o.hide_render = o.name not in vis
            attr = ob.data.color_attributes.new("ao", "FLOAT_COLOR", "POINT")
            ob.data.color_attributes.active_color = attr
            bpy.ops.object.select_all(action="DESELECT")
            ob.select_set(True); bpy.context.view_layer.objects.active = ob
            bpy.ops.object.bake(type="AO", target="VERTEX_COLORS")
            a = np.empty(len(ob.data.vertices) * 4, dtype=np.float32); attr.data.foreach_get("color", a)
            ao[g] = a.reshape(-1, 4)[:, 0].copy()
            ob.data.color_attributes.remove(attr)
        for o in merged.values():
            o.hide_render = False

    tris = 0
    for g, ob in merged.items():
        me = ob.data
        c = _curvature(me)
        n = len(me.vertices)
        data = np.ones((n, 4), dtype=np.float32)
        data[:, 0] = ao.get(g, np.ones(n))
        data[:, 1] = np.clip((c - 0.05) / 0.22, 0, 1)
        data[:, 2] = np.clip((-c - 0.05) / 0.22, 0, 1)
        attr = me.color_attributes.new("data", "FLOAT_COLOR", "POINT")
        attr.data.foreach_set("color", data.ravel())
        me.color_attributes.active_color = attr
        me.color_attributes.render_color_index = me.color_attributes.find("data")
        me.calc_loop_triangles(); tris += len(me.loop_triangles)

    scene.render.engine = "BLENDER_EEVEE"
    os.makedirs(os.path.dirname(out_path), exist_ok=True)
    bpy.ops.wm.save_as_mainfile(filepath=out_path.replace(".glb", ".blend"))
    bpy.ops.object.select_all(action="SELECT")
    bpy.ops.export_scene.gltf(filepath=out_path, export_format="GLB", export_apply=True, export_yup=True,
                              export_normals=True, export_colors=True, export_texcoords=False,
                              export_materials="EXPORT")
    print(f"EXPORTED {os.path.basename(out_path)} groups={sorted(merged)} tris={tris}")


# ------------------------------------------------------------------ shared parts
def ar_grip(name, dx, dz, mat="Grip", group="base"):
    """Rifle-style pistol grip; (dx, dz) moves its top-front corner from (-0.066, -0.034)."""
    g = path([
        ("M", -0.066, -0.034), ("L", -0.104, -0.034), ("Q", (-0.118, -0.034), (-0.118, -0.044), 4), ("L", -0.112, -0.050),
        ("L", -0.131, -0.122), ("Q", (-0.135, -0.140), (-0.118, -0.141), 6), ("L", -0.094, -0.139),
        ("Q", (-0.084, -0.138), (-0.086, -0.126), 4), ("Q", (-0.074, -0.108), (-0.080, -0.096), 6),
        ("Q", (-0.068, -0.080), (-0.070, -0.066), 6), ("Q", (-0.066, -0.050), (-0.066, -0.034), 4),
    ])
    g = [(x + dx, z + dz) for x, z in g]
    return prism(name, g, 0.0, 0.026, mat, group=group,
                 taper=lambda x, z: 1.0 + 0.16 * smoothstep(-0.045 + dz, -0.125 + dz, z), bev=0.0022, segs=3)

def ar_trigger(name, dx, dz, group="base"):
    t = path([("M", -0.028, -0.037), ("L", -0.022, -0.037), ("Q", (-0.019, -0.050), (-0.021, -0.063), 6),
              ("Q", (-0.023, -0.067), (-0.026, -0.064), 3), ("L", -0.028, -0.052), ("Q", (-0.029, -0.043), (-0.028, -0.037), 3)])
    return prism(name, [(x + dx, z + dz) for x, z in t], 0.0, 0.0045, "Steel", group=group, bev=0.0005, segs=2)

def selector(x, z, y_face, group="base"):
    lathe("SelectorHub", [(0, 0), (0, 0.0055), (-0.0022, 0.0055), (-0.0028, 0.0046), (-0.0028, 0)], "Steel", group=group,
          seg=28, axis="Y", c=(x, y_face, z), bev=0.0003, segs=1)
    prism("SelectorLever", rrect(x - 0.001, z - 0.0025, x + 0.019, z + 0.0025, 0.0024), y_face - 0.0028, 0.0016, "Steel",
          group=group, bev=0.0003, segs=1)
