# CheeseTeam class accessories -- geometry + material toolkit (runs inside Blender, headless or desktop).
# World frame of the base model at rest: Z up, the cheese faces -Y, the character's LEFT is +X.
import bpy, bmesh, math, random, os
from mathutils import Vector, Matrix, Euler, Quaternion, noise
from mathutils.bvhtree import BVHTree

HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.environ.get('CLS_SRC', '.')
TEX = os.path.join(HERE, 'tex')
PI = math.pi
FRONT_Y = -0.112          # flat front face of the wedge (rest pose)


# ------------------------------------------------------------------ scene helpers
def body():
    return bpy.data.objects['SK_CheeseTP']


def armature():
    return bpy.data.objects['Armature']


def coll():
    c = bpy.data.collections.get('ACC')
    if c is None:
        c = bpy.data.collections.new('ACC'); bpy.context.scene.collection.children.link(c)
    return c


class Probe:
    """ray casts against the body in its rest pose (world metres)"""
    def __init__(self):
        arm = armature(); arm.data.pose_position = 'REST'
        bpy.context.view_layer.update()
        dg = bpy.context.evaluated_depsgraph_get()
        ob = body().evaluated_get(dg)
        me = ob.to_mesh()
        mw = ob.matrix_world
        verts = [mw @ v.co for v in me.vertices]
        polys = [tuple(p.vertices) for p in me.polygons]
        self.bvh = BVHTree.FromPolygons(verts, polys)
        ob.to_mesh_clear()

    def hit(self, origin, direction, dist=5.0):
        loc, nor, idx, d = self.bvh.ray_cast(Vector(origin), Vector(direction).normalized(), dist)
        return (loc, nor) if loc is not None else (None, None)

    def surf(self, origin, direction, off=0.0):
        """surface point along a ray, pushed `off` back toward the ray origin"""
        loc, nor = self.hit(origin, direction)
        if loc is None:
            return None, None
        return loc - Vector(direction).normalized() * off, nor


def top_frame(P):
    """least-squares plane through the wedge top (avoiding the bite and holes): returns Matrix (cols u, v, n, origin)"""
    pts = []
    for x in [i * 0.02 - 0.17 for i in range(18)]:
        for y in [j * 0.02 - 0.09 for j in range(12)]:
            loc, nor = P.hit((x, y, 2.0), (0, 0, -1))
            if loc is not None and nor.z > 0.85 and loc.z > 0.8:
                pts.append(loc)
    import numpy as np
    A = np.array([[p.x, p.y, 1.0] for p in pts]); z = np.array([p.z for p in pts])
    # robust: iterate dropping points far below the plane (holes)
    for _ in range(4):
        c, *_ = np.linalg.lstsq(A, z, rcond=None)
        r = z - A @ c; keep = r > -0.006
        A, z = A[keep], z[keep]
    a, b, c0 = c
    n = Vector((-a, -b, 1.0)).normalized()
    o = Vector((0.0, 0.015, a * 0.0 + b * 0.015 + c0))
    u = (Vector((1, 0, 0)) - n * n.x).normalized()
    v = n.cross(u)
    M = Matrix.Identity(4)
    M.col[0][:3] = u; M.col[1][:3] = v; M.col[2][:3] = n; M.col[3][:3] = o
    return M


def bone_frame(name):
    """rest-pose bone frame in world space: origin at head, Y along the bone"""
    arm = armature(); b = arm.data.bones[name]
    return arm.matrix_world @ b.matrix_local, (arm.matrix_world @ b.head_local), (arm.matrix_world @ b.tail_local)


# ------------------------------------------------------------------ mesh builders (return bmesh)
def bm_from(verts, faces):
    bm = bmesh.new(); V = [bm.verts.new(v) for v in verts]
    for f in faces:
        try:
            bm.faces.new([V[i] for i in f])
        except ValueError:
            pass
    return bm


def rings(ring_list, cap_bottom=True, cap_top=True):
    """loft through rings (lists of Vector, same count); caps fan to centroid"""
    n = len(ring_list[0]); verts = []; faces = []
    for r in ring_list:
        verts += list(r)
    for k in range(len(ring_list) - 1):
        for i in range(n):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    if cap_bottom:
        c = sum(ring_list[0], Vector()) / n; verts.append(c); ci = len(verts) - 1
        for i in range(n):
            faces.append((ci, (i + 1) % n, i))
    if cap_top:
        base = (len(ring_list) - 1) * n
        c = sum(ring_list[-1], Vector()) / n; verts.append(c); ci = len(verts) - 1
        for i in range(n):
            faces.append((ci, base + i, base + (i + 1) % n))
    return bm_from(verts, faces)


def superellipse(a, b, e=2.0, n=48, phase=0.0):
    pts = []
    for i in range(n):
        t = 2 * PI * i / n + phase
        c, s = math.cos(t), math.sin(t)
        x = a * math.copysign(abs(c) ** (2.0 / e), c); y = b * math.copysign(abs(s) ** (2.0 / e), s)
        pts.append((x, y))
    return pts


def lathe(profile, a=1.0, b=1.0, e=2.0, n=48, cap_bottom=True, cap_top=True, shape=None):
    """profile [(scale, z)] applied to a superellipse outline of half-sizes a, b; shape(i, t, x, y, z)->(x, y, z) optional"""
    base = superellipse(a, b, e, n)
    R = []
    for k, (s, z) in enumerate(profile):
        ring = []
        for i, (x, y) in enumerate(base):
            p = (x * s, y * s, z)
            if shape:
                p = shape(k, i / n, *p)
            ring.append(Vector(p))
        R.append(ring)
    return rings(R, cap_bottom, cap_top)


def tube(path, radius, n=10, cap=True, flat=1.0, twist=0.0, up=Vector((0, 0, 1))):
    """sweep a circle (or ellipse: flat = y/x ratio) along path; radius: float or f(t in 0..1)"""
    m = len(path); R = []
    prev_side = None
    for k, p in enumerate(path):
        t = k / max(1, m - 1)
        tan = (path[min(k + 1, m - 1)] - path[max(k - 1, 0)]).normalized()
        side = tan.cross(up)
        if side.length < 1e-6:
            side = tan.cross(Vector((1, 0, 0)))
        side.normalize()
        if prev_side is not None and side.dot(prev_side) < 0:
            side = -side
        prev_side = side
        nrm = side.cross(tan).normalized()
        r = radius(t) if callable(radius) else radius
        ring = []
        for i in range(n):
            a = 2 * PI * i / n + twist * t
            ring.append(p + side * math.cos(a) * r + nrm * math.sin(a) * r * flat)
        R.append(ring)
    return rings(R, cap, cap)


def box(c, s, bevel=0.0):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * s[0], v.co.y * s[1], v.co.z * s[2])) + Vector(c)
    if bevel > 0:
        bmesh.ops.bevel(bm, geom=bm.edges[:], offset=bevel, segments=3, profile=0.5, affect='EDGES')
    return bm


def sphere(c, r, seg=24, rings_=12, scale=(1, 1, 1)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings_, radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(c)
    return bm


def bezier(p0, p1, p2, p3, n=16):
    out = []
    for i in range(n + 1):
        t = i / n
        out.append((1 - t) ** 3 * p0 + 3 * (1 - t) ** 2 * t * p1 + 3 * (1 - t) * t * t * p2 + t ** 3 * p3)
    return out


def transform(bm, M):
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    return bm


def displace(bm, fn):
    for v in bm.verts:
        v.co = fn(v.co)
    return bm


# ------------------------------------------------------------------ objects
def make_obj(name, bm, mat, bone, smooth=True, subsurf=0, solid=0.0, weld=False):
    me = bpy.data.meshes.new(name)
    if weld:
        bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    ob = bpy.data.objects.new(name, me); coll().objects.link(ob)
    me.materials.append(mat)
    if solid:
        m = ob.modifiers.new('solid', 'SOLIDIFY'); m.thickness = solid; m.offset = 0.0
    if subsurf:
        m = ob.modifiers.new('sub', 'SUBSURF'); m.levels = subsurf; m.render_levels = subsurf
    ob['bone'] = bone
    return ob


# ------------------------------------------------------------------ decals: 2D outline on a face, projected onto the body
def decal(name, P, outline_uv, frame, direction, mat, bone='spine_01', off=0.0012, res=0.004):
    """outline_uv: list of (u, v) in metres in the plane of `frame` (Matrix: cols u, v, normal(out of surface), origin).
    The polygon is triangulated, subdivided to ~res and every vertex is projected along `direction` onto the body."""
    bm = bmesh.new()
    V = [bm.verts.new(frame @ Vector((u, v, 0.05))) for (u, v) in outline_uv]
    f = bm.faces.new(V)
    bmesh.ops.triangulate(bm, faces=[f])
    # refine: subdivide edges until short enough
    for _ in range(6):
        long = [e for e in bm.edges if e.calc_length() > res]
        if not long:
            break
        bmesh.ops.subdivide_edges(bm, edges=long, cuts=1, use_grid_fill=True)
        bmesh.ops.triangulate(bm, faces=bm.faces[:])
    d = Vector(direction).normalized()
    keep = True
    for v in bm.verts:
        loc, nor = P.hit(v.co - d * 0.2, d)
        if loc is None:
            keep = False; continue
        v.co = loc - d * off + nor * off
    ob = make_obj(name, bm, mat, bone, smooth=True)
    return ob


# ------------------------------------------------------------------ materials (procedural, baked later)
def _mat(name):
    m = bpy.data.materials.get(name)
    if m:
        bpy.data.materials.remove(m)
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs[0])
    return m, nt, bs


def _tc(nt, kind='Object'):
    tc = nt.nodes.new('ShaderNodeTexCoord')
    return tc.outputs[kind]


def _noise(nt, vec, scale, detail=4.0, rough=0.55):
    n = nt.nodes.new('ShaderNodeTexNoise'); n.inputs['Scale'].default_value = scale
    n.inputs['Detail'].default_value = detail; n.inputs['Roughness'].default_value = rough
    nt.links.new(vec, n.inputs['Vector'])
    return n


def _ramp(nt, fac, c0, c1, p0=0.3, p1=0.7):
    r = nt.nodes.new('ShaderNodeValToRGB'); r.color_ramp.elements[0].position = p0; r.color_ramp.elements[1].position = p1
    r.color_ramp.elements[0].color = (*c0, 1); r.color_ramp.elements[1].color = (*c1, 1)
    nt.links.new(fac, r.inputs['Fac'])
    return r


def _bump(nt, bs, height, strength, dist=0.002):
    b = nt.nodes.new('ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = dist
    nt.links.new(height, b.inputs['Height']); nt.links.new(b.outputs['Normal'], bs.inputs['Normal'])
    return b


def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


def mat_felt(name, col, col2=None, rough=0.82, fiber=0.35):
    """felt / wool: two-tone mottling + fine fibre bump"""
    m, nt, bs = _mat(name)
    vec = _tc(nt)
    n1 = _noise(nt, vec, 18, 6, 0.6)
    r = _ramp(nt, n1.outputs['Fac'], srgb(col), srgb(col2 or col), 0.35, 0.75)
    nt.links.new(r.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = rough
    try:
        bs.inputs['Sheen Weight'].default_value = 0.12
        bs.inputs['Sheen Tint'].default_value = (*srgb(col2 or col), 1)
    except (KeyError, TypeError):
        pass
    n2 = _noise(nt, vec, 900, 2, 0.5)
    _bump(nt, bs, n2.outputs['Fac'], fiber, 0.0006)
    return m


def mat_plain(name, col, rough=0.5, metal=0.0, col2=None, nscale=40, bump=0.08, bscale=300):
    m, nt, bs = _mat(name)
    vec = _tc(nt)
    if col2:
        n1 = _noise(nt, vec, nscale, 5, 0.6)
        r = _ramp(nt, n1.outputs['Fac'], srgb(col), srgb(col2), 0.3, 0.75)
        nt.links.new(r.outputs['Color'], bs.inputs['Base Color'])
    else:
        bs.inputs['Base Color'].default_value = (*srgb(col), 1)
    bs.inputs['Roughness'].default_value = rough; bs.inputs['Metallic'].default_value = metal
    if bump:
        n2 = _noise(nt, vec, bscale, 3, 0.5)
        _bump(nt, bs, n2.outputs['Fac'], bump, 0.0008)
    return m


def mat_metal(name, col, rough=0.25, scratches=0.5):
    """painted-out or bare metal with fine directional scratches (roughness + bump)"""
    m, nt, bs = _mat(name)
    vec = _tc(nt)
    bs.inputs['Base Color'].default_value = (*srgb(col), 1); bs.inputs['Metallic'].default_value = 1.0
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 60.0, 1.0)
    nt.links.new(vec, mp.inputs['Vector'])
    sc = _noise(nt, mp.outputs['Vector'], 60, 8, 0.7)
    r = _ramp(nt, sc.outputs['Fac'], (rough, rough, rough), (rough + 0.25, rough + 0.25, rough + 0.25), 0.45, 0.7)
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(r.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[0], bs.inputs['Roughness'])
    _bump(nt, bs, sc.outputs['Fac'], 0.05 * scratches, 0.0005)
    return m


def mat_image(name, img, rough=0.75, metal=0.0, bump=0.15, mapping='UV', scale=(1, 1, 1), tint=None):
    m, nt, bs = _mat(name)
    tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(TEX, img), check_existing=True)
    if mapping == 'UV':
        uv = nt.nodes.new('ShaderNodeUVMap')
        mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = scale
        nt.links.new(uv.outputs[0], mp.inputs['Vector']); nt.links.new(mp.outputs[0], tx.inputs['Vector'])
    if tint:
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs['Factor'].default_value = 1.0
        nt.links.new(tx.outputs['Color'], mix.inputs['A']); mix.inputs['B'].default_value = (*srgb(tint), 1)
        nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    else:
        nt.links.new(tx.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = rough; bs.inputs['Metallic'].default_value = metal
    if bump:
        vec = _tc(nt); n2 = _noise(nt, vec, 700, 2, 0.5)
        _bump(nt, bs, n2.outputs['Fac'], bump, 0.0006)
    return m


def mat_hair(name, col, col2):
    """stylised hair clumps: strand bump along the object's local X/Z + two-tone"""
    m, nt, bs = _mat(name)
    vec = _tc(nt)
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (220.0, 220.0, 12.0)
    nt.links.new(vec, mp.inputs['Vector'])
    n = _noise(nt, mp.outputs['Vector'], 4, 3, 0.5)
    r = _ramp(nt, n.outputs['Fac'], srgb(col), srgb(col2), 0.3, 0.7)
    nt.links.new(r.outputs['Color'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.6
    _bump(nt, bs, n.outputs['Fac'], 0.35, 0.0015)
    return m


def uv_box(ob, scale=12.0):
    """box-projected UVs straight from the mesh (no operators): u, v = metres * scale on the dominant axis plane"""
    me = ob.data
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            if ax == 0:
                uv.data[li].uv = (co.y * scale, co.z * scale)
            elif ax == 1:
                uv.data[li].uv = (co.x * scale, co.z * scale)
            else:
                uv.data[li].uv = (co.x * scale, co.y * scale)


uv_cylinder = uv_box


def ctx():
    """an override with a real window/area, for operators run from scripts or the MCP socket"""
    wm = bpy.context.window_manager
    win = wm.windows[0] if wm.windows else None
    d = {}
    if win:
        d['window'] = win; d['screen'] = win.screen
        for a in win.screen.areas:
            if a.type == 'VIEW_3D':
                d['area'] = a
                d['region'] = next((r for r in a.regions if r.type == 'WINDOW'), None)
                break
    return d


def revolve(section, a, b, n=64, closed=True, zfn=None, sfn=None):
    """revolve a closed 2D section [(s, z)] around the local Z axis along an ellipse (a, b):
    point = (a*s*cos f, b*s*sin f, z) (+ zfn(f, s) lift, s scaled by sfn(f))"""
    R = []
    for (s, z) in section:
        ring = []
        for i in range(n):
            f = 2 * PI * i / n
            ss = s * (sfn(f) if sfn else 1.0)
            zz = z + (zfn(f, s) if zfn else 0.0)
            ring.append(Vector((a * ss * math.cos(f), b * ss * math.sin(f), zz)))
        R.append(ring)
    if closed:
        R.append(R[0])
    bm = rings(R, False, False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-6)
    return bm


def ribbon(path, width, normal_fn, thick=0.0):
    """flat strip along path; width(t) ; normal_fn(t, tangent)->surface normal (strip spans tangent x normal)"""
    verts = []; faces = []; m = len(path)
    for k, p in enumerate(path):
        t = k / max(1, m - 1)
        tan = (path[min(k + 1, m - 1)] - path[max(k - 1, 0)]).normalized()
        nrm = normal_fn(t, tan)
        side = tan.cross(nrm).normalized()
        w = width(t) if callable(width) else width
        verts += [p - side * w / 2, p + side * w / 2]
        if k:
            faces.append((2 * k - 2, 2 * k - 1, 2 * k + 1, 2 * k))
    return bm_from(verts, faces)


def frame_matrix(origin, x, y, z):
    M = Matrix.Identity(4)
    M.col[0][:3] = x; M.col[1][:3] = y; M.col[2][:3] = z; M.col[3][:3] = origin
    return M


def settle(P, objs, normal, clear=0.004, check=None):
    """lift hat objects along `normal` until every vertex of the `check` objects sits at least `clear` above the body
    (rays straight down in world Z). Returns the lift applied."""
    check = check or objs
    need = 0.0
    n = Vector(normal).normalized()
    for ob in check:
        mw = ob.matrix_world
        for v in ob.data.vertices:
            w = mw @ v.co
            loc, nor = P.hit(w + n * 1.0, -n)
            if loc is not None:
                h = (w - loc).dot(n)            # height of the vertex above the body along n
                if h < clear:
                    need = max(need, clear - h)
    if need > 0:
        for ob in objs:
            me = ob.data
            for v in me.vertices:
                v.co = v.co + normal * need
            me.update()
    return need


def inside_count(P, objs, clear=0.0):
    """how many vertices of objs are inside the body (or closer than `clear` to its surface, on the inside side)"""
    c = 0
    for ob in objs:
        mw = ob.matrix_world
        for v in ob.data.vertices:
            w = mw @ v.co
            loc, nor, idx, d = P.bvh.find_nearest(w)
            if loc is not None and (w - loc).dot(nor) < clear:
                c += 1
    return c


def sink(P, objs, normal, check, clear=0.0015, step=0.002, limit=0.08):
    """after settle(): lower the hat along -normal as far as possible while no `check` vertex enters the body,
    so the rim wraps down over the rounded edges instead of hovering on the highest point. Returns the drop."""
    n = Vector(normal).normalized()
    def move(dz):
        for ob in objs:
            me = ob.data
            for v in me.vertices:
                v.co = v.co - n * dz
            me.update()
    base = inside_count(P, check, clear)
    drop = 0.0
    while drop < limit:
        move(step)
        if inside_count(P, check, clear) > base:
            move(-step)
            break
        drop += step
    return drop
