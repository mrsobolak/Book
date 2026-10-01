# CheeseTeam weapons -- modelling + material kit (runs inside Blender).
# Convention: metres, real-world size. Muzzle points -Y, up is +Z, the weapon's left side (shooter's view) is +X.
# Side profiles are written in (u, v) millimetres: u = forward (toward the muzzle), v = up; P(u, v, x) -> world.
import bpy, bmesh, math, os, random
from mathutils import Vector, Matrix, noise
from mathutils.geometry import tessellate_polygon

HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else '.'
TEX = os.path.join(HERE, 'tex')
PI = math.pi
MM = 0.001


def W(u, v, x=0.0):
    """profile mm -> world metres"""
    return Vector((x * MM, -u * MM, v * MM))


# ------------------------------------------------------------------ scene
def coll(name='WPN'):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name); bpy.context.scene.collection.children.link(c)
    return c


def new_scene():
    bpy.ops.wm.read_homefile(use_empty=True)
    sc = bpy.context.scene
    sc.unit_settings.system = 'METRIC'
    return sc


# ------------------------------------------------------------------ 2D helpers (mm)
def arc(cu, cv, r, a0, a1, n=12):
    return [(cu + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)), cv + r * math.sin(math.radians(a0 + (a1 - a0) * i / n)))
            for i in range(n + 1)]


def rounded(poly, n=6):
    """poly: [(u, v, r)] -> corners with r > 0 filleted (r in mm)"""
    out = []
    m = len(poly)
    for i in range(m):
        u, v, r = poly[i]
        if r <= 0:
            out.append((u, v)); continue
        p = Vector((u, v)); a = Vector(poly[i - 1][:2]); b = Vector(poly[(i + 1) % m][:2])
        da = (a - p).normalized(); db = (b - p).normalized()
        cosang = max(-0.9999, min(0.9999, da.dot(db)))
        th = math.acos(cosang)
        d = min(r / math.tan(th / 2), (a - p).length * 0.49, (b - p).length * 0.49)
        rr = d * math.tan(th / 2)
        p1 = p + da * d; p2 = p + db * d
        bis = (da + db).normalized()
        c = p + bis * (rr / math.sin(th / 2))
        a1 = math.atan2(p1.y - c.y, p1.x - c.x); a2 = math.atan2(p2.y - c.y, p2.x - c.x)
        da_ = a2 - a1
        while da_ > PI: da_ -= 2 * PI
        while da_ < -PI: da_ += 2 * PI
        for k in range(n + 1):
            t = a1 + da_ * k / n
            out.append((c.x + rr * math.cos(t), c.y + rr * math.sin(t)))
    return out


def bezier2(p0, p1, p2, n=10):
    return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
             (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]


# ------------------------------------------------------------------ meshes (all coordinates in metres unless noted)
def bm_from(verts, faces):
    bm = bmesh.new(); V = [bm.verts.new(v) for v in verts]
    for f in faces:
        try:
            bm.faces.new([V[i] for i in f])
        except ValueError:
            pass
    return bm


def transform(bm, M):
    bmesh.ops.transform(bm, matrix=M, verts=bm.verts[:])
    return bm


def profile(outline, x0, x1, holes=(), taper=None):
    """side profile (u, v mm) extruded across x0..x1 (mm). holes: inner loops. taper(u, v) -> extra half-width (mm)"""
    loops = [list(outline)] + [list(h) for h in holes]
    # orientation: outer CCW, holes CW (tessellate is orientation agnostic, but walls need consistent winding)
    def area(lp):
        return sum(lp[i][0] * lp[(i + 1) % len(lp)][1] - lp[(i + 1) % len(lp)][0] * lp[i][1] for i in range(len(lp))) / 2
    if area(loops[0]) < 0:
        loops[0] = loops[0][::-1]
    for k in range(1, len(loops)):
        if area(loops[k]) > 0:
            loops[k] = loops[k][::-1]
    flat = [p for lp in loops for p in lp]
    tris = tessellate_polygon([[Vector((p[0], p[1], 0)) for p in lp] for lp in loops])
    n = len(flat)
    def xa(p, side):
        t = taper(p[0], p[1]) if taper else 0.0
        return (x1 + t) if side > 0 else (x0 - t)
    verts = [W(p[0], p[1], xa(p, -1)) for p in flat] + [W(p[0], p[1], xa(p, 1)) for p in flat]
    faces = []
    for (a, b, c) in tris:
        faces.append((a, b, c)); faces.append((a + n, c + n, b + n))
    base = 0
    for lp in loops:
        m = len(lp)
        for i in range(m):
            a = base + i; b = base + (i + 1) % m
            faces.append((a, a + n, b + n, b))
        base += m
    bm = bm_from(verts, faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def lathe(prof, n=32, axis_u=0.0, axis_v=0.0, x=0.0, cap0=True, cap1=True, phase=0.0, shape=None):
    """revolve [(r_mm, u_mm)] around an axis parallel to the bore (along u) through (axis_u ignored, axis_v, x).
    shape(i, k, r, ang) -> r (for flats, flutes...)"""
    verts = []; faces = []
    m = len(prof)
    for k, (r, u) in enumerate(prof):
        for i in range(n):
            a = phase + 2 * PI * i / n
            rr = shape(i, k, r, a) if shape else r
            verts.append(W(u, axis_v + rr * math.sin(a), x + rr * math.cos(a)))
    for k in range(m - 1):
        for i in range(n):
            a = k * n + i; b = k * n + (i + 1) % n
            faces.append((a, b, b + n, a + n))
    if cap0 and prof[0][0] > 0:
        c = len(verts); verts.append(W(prof[0][1], axis_v, x))
        for i in range(n):
            faces.append((c, (i + 1) % n, i))
    if cap1 and prof[-1][0] > 0:
        c = len(verts); verts.append(W(prof[-1][1], axis_v, x))
        o = (m - 1) * n
        for i in range(n):
            faces.append((c, o + i, o + (i + 1) % n))
    bm = bm_from(verts, faces)
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def cyl(p0, p1, r, n=24, cap=True):
    """cylinder between two world points (metres)"""
    p0 = Vector(p0); p1 = Vector(p1)
    ax = (p1 - p0); L = ax.length; z = ax.normalized()
    x = z.orthogonal().normalized(); y = z.cross(x)
    verts = []
    for p in (p0, p1):
        for i in range(n):
            a = 2 * PI * i / n
            verts.append(p + x * r * math.cos(a) + y * r * math.sin(a))
    faces = [(i, (i + 1) % n, n + (i + 1) % n, n + i) for i in range(n)]
    if cap:
        faces.append(tuple(range(n))[::-1]); faces.append(tuple(range(n, 2 * n)))
    bm = bm_from(verts, faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def box(c, s):
    bm = bmesh.new(); bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * s[0], v.co.y * s[1], v.co.z * s[2])) + Vector(c)
    return bm


def sphere(c, r, seg=24, rings=12, scale=(1, 1, 1)):
    bm = bmesh.new(); bmesh.ops.create_uvsphere(bm, u_segments=seg, v_segments=rings, radius=r)
    for v in bm.verts:
        v.co = Vector((v.co.x * scale[0], v.co.y * scale[1], v.co.z * scale[2])) + Vector(c)
    return bm


def tube(path, radius, n=10, cap=True, flat=1.0, up=Vector((0, 0, 1)), closed=False):
    """sweep a circle/ellipse along a world path; radius float or f(t)"""
    m = len(path); R = []
    prev = None
    for k, p in enumerate(path):
        t = k / max(1, m - 1)
        if closed:
            tan = (path[(k + 1) % m] - path[k - 1]).normalized()
        else:
            tan = (path[min(k + 1, m - 1)] - path[max(k - 1, 0)]).normalized()
        side = tan.cross(up)
        if side.length < 1e-6:
            side = tan.cross(Vector((1, 0, 0)))
        side.normalize()
        if prev is not None and side.dot(prev) < 0:
            side = -side
        prev = side
        nrm = side.cross(tan).normalized()
        r = radius(t) if callable(radius) else radius
        R.append([p + side * math.cos(2 * PI * i / n) * r + nrm * math.sin(2 * PI * i / n) * r * flat for i in range(n)])
    verts = [v for ring in R for v in ring]; faces = []
    rng = range(m) if closed else range(m - 1)
    for k in rng:
        k2 = (k + 1) % m
        for i in range(n):
            faces.append((k * n + i, k * n + (i + 1) % n, k2 * n + (i + 1) % n, k2 * n + i))
    if cap and not closed:
        faces.append(tuple(range(n))[::-1]); faces.append(tuple(range((m - 1) * n, m * n)))
    bm = bm_from(verts, faces)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def ribbon(path, width, normal_fn, thick=0.0):
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


def merge(*bms):
    out = bmesh.new()
    for b in bms:
        me = bpy.data.meshes.new('tmp'); b.to_mesh(me); b.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return out


def frame(o, x, y, z):
    M = Matrix.Identity(4)
    M.col[0][:3] = x; M.col[1][:3] = y; M.col[2][:3] = z; M.col[3][:3] = o
    return M


# ------------------------------------------------------------------ objects
def make(name, bm, mat, bevel=0.0, seg=3, angle=35.0, smooth=True, subsurf=0, solid=0.0, uv=None):
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for p in me.polygons:
        p.use_smooth = smooth
    ob = bpy.data.objects.new(name, me); coll().objects.link(ob)
    if mat is not None:
        me.materials.append(mat)
    if solid:
        m = ob.modifiers.new('solid', 'SOLIDIFY'); m.thickness = solid; m.offset = 0.0
    ob['bev'] = bevel; ob['seg'] = seg; ob['ang'] = angle; ob['sub'] = subsurf; ob['wn'] = int(smooth and (bevel > 0 or not subsurf))
    if uv == 'box':
        uv_box(ob)
    return ob


def cut(target, bm, name='cut'):
    """boolean difference with a hidden cutter object (applied when the weapon is finished)"""
    me = bpy.data.meshes.new(target.name + '_' + name); bm.to_mesh(me); bm.free()
    c = bpy.data.objects.new(target.name + '_' + name, me)
    coll('CUTTERS').objects.link(c)
    c.display_type = 'WIRE'; c.hide_render = True
    m = target.modifiers.new(name, 'BOOLEAN'); m.operation = 'DIFFERENCE'; m.object = c; m.solver = 'EXACT'
    return c


def finalize(objs=None):
    """append bevel / subsurf / weighted-normal modifiers after the booleans"""
    for ob in (objs or list(coll().objects)):
        if ob.get('done'):
            continue
        if ob.get('bev', 0) > 0:
            m = ob.modifiers.new('bevel', 'BEVEL'); m.width = ob['bev']; m.segments = ob['seg']
            m.limit_method = 'ANGLE'; m.angle_limit = math.radians(ob['ang']); m.harden_normals = True
        if ob.get('sub', 0):
            m = ob.modifiers.new('sub', 'SUBSURF'); m.levels = ob['sub']; m.render_levels = ob['sub']
        if ob.get('wn', 0):
            m = ob.modifiers.new('wn', 'WEIGHTED_NORMAL'); m.keep_sharp = True
        ob['done'] = 1


def uv_box(ob, scale=1.0):
    me = ob.data
    uv = me.uv_layers.new(name='UVMap') if not me.uv_layers else me.uv_layers[0]
    for p in me.polygons:
        n = p.normal; ax = max(range(3), key=lambda i: abs(n[i]))
        for li in p.loop_indices:
            co = me.vertices[me.loops[li].vertex_index].co
            uv.data[li].uv = ((co.y, co.z) if ax == 0 else (co.x, co.z) if ax == 1 else (co.x, co.y))
            uv.data[li].uv = (uv.data[li].uv[0] * scale, uv.data[li].uv[1] * scale)


def set_uv(bm, fn, name='UVMap'):
    uvl = bm.loops.layers.uv.new(name)
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = fn(lp.vert.co)
    return bm


# ------------------------------------------------------------------ materials (procedural PBR; baked at export)
def srgb(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return tuple(v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c)


class NT:
    """tiny node-graph helper"""
    def __init__(self, name):
        m = bpy.data.materials.new(name); m.use_nodes = True
        self.m = m; self.nt = m.node_tree; self.nt.nodes.clear()
        self.out = self.nt.nodes.new('ShaderNodeOutputMaterial')
        self.bs = self.nt.nodes.new('ShaderNodeBsdfPrincipled')
        self.link(self.bs.outputs[0], self.out.inputs[0])
        self.co = self.node('ShaderNodeTexCoord').outputs['Object']

    def node(self, t, **kw):
        n = self.nt.nodes.new(t)
        for k, v in kw.items():
            setattr(n, k, v)
        return n

    def link(self, a, b):
        self.nt.links.new(a, b)

    def val(self, s, v):
        if isinstance(v, (int, float)):
            s.default_value = v
        elif isinstance(v, tuple):
            s.default_value = v
        else:
            self.link(v, s)

    def math(self, op, a, b=None, clamp=False):
        n = self.node('ShaderNodeMath'); n.operation = op; n.use_clamp = clamp
        self.val(n.inputs[0], a)
        if b is not None:
            self.val(n.inputs[1], b)
        return n.outputs[0]

    def mix(self, fac, a, b):
        n = self.node('ShaderNodeMix'); n.data_type = 'RGBA'
        self.val(n.inputs['Factor'], fac)
        self.val(n.inputs['A'], a if not isinstance(a, str) else (*srgb(a), 1))
        self.val(n.inputs['B'], b if not isinstance(b, str) else (*srgb(b), 1))
        return n.outputs['Result']

    def mixf(self, fac, a, b):
        n = self.node('ShaderNodeMix'); n.data_type = 'FLOAT'
        self.val(n.inputs['Factor'], fac); self.val(n.inputs['A'], a); self.val(n.inputs['B'], b)
        return n.outputs['Result']

    def noise(self, scale, detail=4.0, rough=0.55, vec=None, stretch=None, dim='3D', distort=0.0):
        v = vec or self.co
        if stretch:
            mp = self.node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = stretch
            self.link(v, mp.inputs['Vector']); v = mp.outputs[0]
        n = self.node('ShaderNodeTexNoise'); n.noise_dimensions = dim
        n.inputs['Scale'].default_value = scale; n.inputs['Detail'].default_value = detail
        n.inputs['Roughness'].default_value = rough; n.inputs['Distortion'].default_value = distort
        self.link(v, n.inputs['Vector'])
        return n.outputs['Fac']

    def ramp(self, fac, p0, p1, c0=(0, 0, 0), c1=(1, 1, 1)):
        r = self.node('ShaderNodeValToRGB')
        r.color_ramp.elements[0].position = p0; r.color_ramp.elements[1].position = p1
        r.color_ramp.elements[0].color = (*c0, 1) if len(c0) == 3 else c0
        r.color_ramp.elements[1].color = (*c1, 1) if len(c1) == 3 else c1
        self.link(fac, r.inputs['Fac'])
        return r.outputs['Color']

    def bw(self, col):
        n = self.node('ShaderNodeRGBToBW'); self.link(col, n.inputs[0]); return n.outputs[0]

    def edges(self, radius=0.0009, gain=9.0, breakup=0.6, bscale=180.0):
        """worn-edge mask from the Bevel-node normal (Cycles; baked into the textures at export)"""
        bev = self.node('ShaderNodeBevel'); bev.samples = 8; bev.inputs['Radius'].default_value = radius
        geo = self.node('ShaderNodeNewGeometry')
        d = self.node('ShaderNodeVectorMath'); d.operation = 'DOT_PRODUCT'
        self.link(bev.outputs[0], d.inputs[0]); self.link(geo.outputs['Normal'], d.inputs[1])
        e = self.math('MULTIPLY', self.math('SUBTRACT', 1.0, d.outputs['Value']), gain, clamp=True)
        n = self.noise(bscale, 8, 0.7)
        nm = self.bw(self.ramp(n, 0.35 - 0.3 * breakup, 0.75))
        return self.math('MULTIPLY', e, nm, clamp=True)

    def scratches(self, density=1.0, scale=40.0):
        """thin directional scratches: stretched noise -> sharp lines"""
        a = self.noise(scale, 12, 0.75, stretch=(1.0, 22.0, 1.0))
        b = self.noise(scale * 1.3, 12, 0.75, stretch=(18.0, 1.0, 1.0))
        la = self.bw(self.ramp(a, 0.69 - 0.03 * density, 0.71))
        lb = self.bw(self.ramp(b, 0.70 - 0.02 * density, 0.715))
        return self.math('MAXIMUM', la, lb)

    def bump(self, h, strength, dist=0.0004):
        b = self.node('ShaderNodeBump'); b.inputs['Strength'].default_value = strength; b.inputs['Distance'].default_value = dist
        self.link(h, b.inputs['Height'])
        if self.bs.inputs['Normal'].is_linked:
            self.link(self.bs.inputs['Normal'].links[0].from_socket, b.inputs['Normal'])
        self.link(b.outputs[0], self.bs.inputs['Normal'])
        return b

    def set(self, name, v):
        self.val(self.bs.inputs[name], v)


def steel(name, base='#16181d', bare='#a2a5aa', rough=0.33, wear=1.0, scratch=1.0, metallic=1.0, tint_var=0.06):
    """blued / blackened / bare steel: mottled finish, worn bright edges, fine scratches, smudgy roughness"""
    g = NT(name)
    mot = g.noise(14, 6, 0.6)
    b0 = srgb(base)
    basec = g.ramp(mot, 0.3, 0.8, tuple(c * (1 - tint_var) for c in b0), tuple(min(1, c * (1 + tint_var * 2)) for c in b0))
    e = g.edges(breakup=0.6) if wear > 0 else 0.0
    s = g.scratches(scratch) if scratch > 0 else 0.0
    m = g.math('MAXIMUM', g.math('MULTIPLY', e, wear, clamp=True), g.math('MULTIPLY', s, 0.7 * scratch, clamp=True)) if wear or scratch else 0.0
    g.set('Base Color', g.mix(m, basec, bare))
    sm = g.noise(6, 3, 0.5)
    r = g.math('ADD', rough - 0.06, g.math('MULTIPLY', sm, 0.14))
    g.set('Roughness', g.mixf(m, r, 0.22))
    g.set('Metallic', metallic)
    g.bump(g.math('MULTIPLY', s, -1.0) if scratch else g.noise(400, 2), 0.06)
    return g.m


def paint(name, col, under='#8a8c90', under_metal=1.0, rough=0.55, wear=1.0, scuff=1.0, col_var=0.10):
    """painted metal: slightly uneven paint, chipped edges to bare metal, scuffs"""
    g = NT(name)
    mot = g.noise(9, 6, 0.6)
    c0 = srgb(col)
    basec = g.ramp(mot, 0.25, 0.85, tuple(c * (1 - col_var) for c in c0), tuple(min(1, c * (1 + col_var)) for c in c0))
    e = g.edges(radius=0.0012, gain=7.0, breakup=0.8, bscale=90)
    sc = g.noise(30, 10, 0.75, stretch=(1.0, 6.0, 1.0))
    scm = g.bw(g.ramp(sc, 0.66 - 0.04 * scuff, 0.70))
    m = g.math('MAXIMUM', g.math('MULTIPLY', e, wear, clamp=True), g.math('MULTIPLY', scm, scuff, clamp=True))
    g.set('Base Color', g.mix(m, basec, under))
    g.set('Roughness', g.mixf(m, g.math('ADD', rough - 0.05, g.math('MULTIPLY', g.noise(5, 3), 0.1)), 0.3))
    g.set('Metallic', g.mixf(m, 0.0, under_metal))
    g.bump(g.math('MULTIPLY', m, -1.0), 0.15, 0.0003)
    return g.m


def wood(name, light='#7a4a28', dark='#3a1f10', rough=0.45, grain=1.0, ring=60.0, wear=0.7, axis='Y'):
    """oiled hardwood: long grain along the weapon (Y), figure, pores, lighter worn edges"""
    g = NT(name)
    st = {'Y': (1.0, 0.06, 1.0), 'Z': (1.0, 1.0, 0.06), 'X': (0.06, 1.0, 1.0)}[axis]
    mp = g.node('ShaderNodeMapping'); mp.inputs['Scale'].default_value = st
    g.link(g.co, mp.inputs['Vector'])
    dn = g.noise(3.0, 4, 0.6, vec=mp.outputs[0])
    wv = g.node('ShaderNodeTexWave'); wv.wave_type = 'RINGS'; wv.inputs['Scale'].default_value = ring
    wv.inputs['Distortion'].default_value = 9.0; wv.inputs['Detail'].default_value = 6; wv.inputs['Detail Scale'].default_value = 3.0
    off = g.node('ShaderNodeVectorMath'); off.operation = 'ADD'
    g.link(mp.outputs[0], off.inputs[0]); g.link(dn, off.inputs[1])
    g.link(off.outputs[0], wv.inputs['Vector'])
    fine = g.noise(240, 6, 0.7, vec=mp.outputs[0])
    gr = g.math('ADD', g.math('MULTIPLY', wv.outputs['Fac'], 0.75 * grain), g.math('MULTIPLY', fine, 0.35))
    c = g.ramp(gr, 0.15, 0.95, srgb(dark), srgb(light))
    e = g.edges(radius=0.0015, gain=6.0, breakup=0.7, bscale=60)
    lighter = tuple(min(1, x * 1.6 + 0.02) for x in srgb(light))
    g.set('Base Color', g.mix(g.math('MULTIPLY', e, wear, clamp=True), c, (*lighter, 1)))
    g.set('Roughness', g.math('ADD', rough - 0.05, g.math('MULTIPLY', fine, 0.15)))
    try:
        g.set('Coat Weight', 0.25); g.set('Coat Roughness', 0.35)
    except KeyError:
        pass
    pores = g.bw(g.ramp(g.noise(900, 2, 0.5, vec=mp.outputs[0]), 0.62, 0.70))
    g.bump(g.math('MULTIPLY', g.math('ADD', pores, g.math('MULTIPLY', wv.outputs['Fac'], 0.3)), -1.0), 0.12, 0.0003)
    return g.m


def rubber(name, col='#18181a', rough=0.8, stipple=1.0):
    g = NT(name)
    g.set('Base Color', g.ramp(g.noise(20, 4), 0.3, 0.8, srgb(col), tuple(min(1, x * 1.35 + 0.004) for x in srgb(col))))
    g.set('Roughness', rough)
    vo = g.node('ShaderNodeTexVoronoi'); vo.inputs['Scale'].default_value = 900.0
    g.link(g.co, vo.inputs['Vector'])
    g.bump(vo.outputs['Distance'], 0.25 * stipple, 0.0003)
    return g.m


def plastic(name, col, rough=0.45, var=0.06):
    g = NT(name)
    c0 = srgb(col)
    g.set('Base Color', g.ramp(g.noise(12, 4), 0.3, 0.8, tuple(c * (1 - var) for c in c0), tuple(min(1, c * (1 + var)) for c in c0)))
    g.set('Roughness', g.math('ADD', rough - 0.05, g.math('MULTIPLY', g.noise(8, 3), 0.1)))
    g.bump(g.noise(500, 2), 0.04)
    return g.m


def pearl(name):
    g = NT(name)
    swirl = g.noise(18, 6, 0.65, distort=2.0)
    g.set('Base Color', g.ramp(swirl, 0.3, 0.8, srgb('#d9d3c6'), srgb('#f6f2ea')))
    g.set('Roughness', 0.18)
    try:
        g.set('Coat Weight', 0.8); g.set('Coat Roughness', 0.08)
        g.set('Thin Film Thickness', 380.0)
    except KeyError:
        pass
    g.bump(swirl, 0.04)
    return g.m


def image_mat(name, img, rough=0.6, metal=0.0, bump=0.0, uvname='UVMap', alpha=False):
    g = NT(name)
    tx = g.node('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(TEX, img), check_existing=True)
    uv = g.node('ShaderNodeUVMap'); uv.uv_map = uvname
    g.link(uv.outputs[0], tx.inputs['Vector'])
    g.set('Base Color', tx.outputs['Color'])
    g.set('Roughness', rough); g.set('Metallic', metal)
    if bump:
        g.bump(g.noise(700, 2), bump)
    return g.m


def fabric_img(name, img, rough=0.88, sat=1.0, val=1.0):
    g = NT(name)
    tx = g.node('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(TEX, img), check_existing=True)
    uv = g.node('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    g.link(uv.outputs[0], tx.inputs['Vector'])
    hs = g.node('ShaderNodeHueSaturation'); hs.inputs['Saturation'].default_value = sat; hs.inputs['Value'].default_value = val
    g.link(tx.outputs['Color'], hs.inputs['Color'])
    g.set('Base Color', hs.outputs['Color']); g.set('Roughness', rough)
    try:
        g.set('Sheen Weight', 0.08)
    except KeyError:
        pass
    wv = g.node('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 1400.0
    g.link(g.co, wv.inputs['Vector'])
    g.bump(wv.outputs['Fac'], 0.2, 0.0002)
    return g.m


# ------------------------------------------------------------------ finishing helpers
def screw(center, normal, r=0.0022, mat=None, name='Screw', slot_ang=0.4):
    """domed slotted screw head sitting on a surface"""
    n = Vector(normal).normalized(); x = n.orthogonal().normalized(); y = n.cross(x)
    F = frame(Vector(center), x, y, n)
    prof = [(1.0, 0.0), (1.0, 0.25), (0.85, 0.55), (0.55, 0.78), (0.0, 0.85)]
    verts = []; faces = []; N = 20
    for k, (s, h) in enumerate(prof):
        for i in range(N):
            a = 2 * PI * i / N
            verts.append(F @ Vector((r * s * math.cos(a), r * s * math.sin(a), r * h)))
    for k in range(len(prof) - 1):
        for i in range(N):
            faces.append((k * N + i, k * N + (i + 1) % N, (k + 1) * N + (i + 1) % N, (k + 1) * N + i))
    faces.append(tuple(range(N))[::-1])
    bm = bm_from(verts, faces)
    ob = make(name, bm, mat)
    sl = box((0, 0, 0), (r * 2.4, r * 0.32, r * 1.2))
    transform(sl, F @ Matrix.Translation((0, 0, r * 0.85)) @ Matrix.Rotation(slot_ang, 4, 'Z'))
    cut(ob, sl, 'slot')
    return ob


def loft(rings, closed=True, cap0=False, cap1=False, uvs=None):
    """skin a list of rings (lists of world Vectors, equal length). closed: rings wrap around."""
    n = len(rings[0]); m = len(rings)
    verts = [p for r in rings for p in r]; faces = []
    span = n if closed else n - 1
    for k in range(m - 1):
        for i in range(span):
            j = (i + 1) % n
            faces.append((k * n + i, k * n + j, (k + 1) * n + j, (k + 1) * n + i))
    if cap0:
        c = len(verts); verts.append(sum(rings[0], Vector()) / n)
        for i in range(span):
            faces.append((c, (i + 1) % n, i))
    if cap1:
        c = len(verts); verts.append(sum(rings[-1], Vector()) / n)
        for i in range(span):
            faces.append((c, (m - 1) * n + i, (m - 1) * n + (i + 1) % n))
    bm = bm_from(verts, faces)
    if uvs is not None:
        uvl = bm.loops.layers.uv.new('UVMap'); bm.verts.index_update()
        for f in bm.faces:
            for lp in f.loops:
                lp[uvl].uv = uvs[lp.vert.index] if lp.vert.index < len(uvs) else (0.5, 0.5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return bm


def studio(strength=1.0, hdri='studio_small_09_2k.hdr'):
    """product-shot lighting for checking weapons (not exported): studio HDRI reflections + soft key/rim, grey backdrop"""
    sc = bpy.context.scene
    c = coll('STUDIO')
    for nm_, loc, en, size, col in (('Key', (0.9, -0.7, 0.9), 90.0, 0.9, (1.0, 0.96, 0.9)),
                                    ('Rim', (-0.3, 1.0, 0.8), 90.0, 0.8, (1.0, 1.0, 1.0))):
        ld = bpy.data.lights.new(nm_, 'AREA'); ld.energy = en * strength; ld.size = size; ld.color = col
        lo = bpy.data.objects.new(nm_, ld); c.objects.link(lo); lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0)) - lo.location).to_track_quat('-Z', 'Y').to_euler()
    w = bpy.data.worlds.new('StudioWorld'); w.use_nodes = True
    nt = w.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputWorld')
    path = os.path.join(HERE, 'hdri', hdri)
    bg_env = nt.nodes.new('ShaderNodeBackground'); bg_env.inputs['Strength'].default_value = 1.0
    if os.path.exists(path):
        env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(path, check_existing=True)
        nt.links.new(env.outputs[0], bg_env.inputs['Color'])
    bg_cam = nt.nodes.new('ShaderNodeBackground'); bg_cam.inputs['Color'].default_value = (0.20, 0.20, 0.205, 1)
    lp = nt.nodes.new('ShaderNodeLightPath'); mx = nt.nodes.new('ShaderNodeMixShader')
    nt.links.new(lp.outputs['Is Camera Ray'], mx.inputs[0]); nt.links.new(bg_env.outputs[0], mx.inputs[1]); nt.links.new(bg_cam.outputs[0], mx.inputs[2])
    nt.links.new(mx.outputs[0], out.inputs[0])
    sc.world = w
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 96; sc.cycles.preview_samples = 32
    try:
        sc.cycles.use_preview_denoising = True; sc.cycles.device = 'GPU'
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = 'AgX'
    except TypeError:
        pass


def spline(pts, sub=6, closed=False):
    """Catmull-Rom resample of world points"""
    P = [pts[0]] + list(pts) + [pts[-1]]
    out = []
    for k in range(1, len(P) - 2):
        p0, p1, p2, p3 = P[k - 1], P[k], P[k + 1], P[k + 2]
        for i in range(sub):
            t = i / sub
            out.append(0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3))
    out.append(P[-2])
    return out
