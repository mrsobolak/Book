"""
Wash Junction asset kit -- game-ready props from Python (Blender 4.0, headless, CPU Cycles).

    blender -b -P src/SM_Thing.py -- [--draft] [--only NAME] [--tex N] [--out DIR] [--norender]

A build script:

    import sys, os; sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "kit"))
    import assetkit as K
    A = K.Asset("Bollard", size=(0.26, 1.2, 0.26), tris=200)          # size = W x H x D (metres)
    YEL = K.mat("paint", color="#d6a21c", under="rust", chips=0.6)
    A.add(K.cyl(0.13, 1.2, seg=12), YEL, at=(0, 0, 0.6))
    A.ucx_cyl((0, 0, 0.6), 0.13, 1.2)
    A.build()

Conventions (from the Cheese Team spec):
    Z up, FRONT = +X, metres.  W -> Y extent, H -> Z extent, D -> X extent.
    Pivot: bottom centre (default) / "center" / "none" (as modelled; e.g. trailer king-pin).
    Slots: M_<Name> (everything baked), TeamPaint (engine tints), Glow (engine emissive).
    Textures: T_<Name>_BaseColor (sRGB, RGBA if alpha), T_<Name>_Normal (DirectX / Unreal, green down),
              T_<Name>_ORM (R=AO, G=Roughness, B=Metallic, linear).
    FBX: 1 unit = 1 cm, transforms applied, smoothing groups, UCX_ collision, LOD1 as its own FBX.
    GLB: metres, Y-up glTF, OpenGL normal map embedded (web preview).
"""
import bpy, bmesh, math, os, sys, json, time, random, subprocess, hashlib, shutil
import numpy as np
from mathutils import Vector, Matrix, Euler
from bpy_extras.object_utils import world_to_camera_view

KIT = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(KIT)
if KIT not in sys.path:
    sys.path.insert(0, KIT)
import materials as MT

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []


def _arg(k, d=None):
    return ARGV[ARGV.index(k) + 1] if k in ARGV and ARGV.index(k) + 1 < len(ARGV) else d


DRAFT = "--draft" in ARGV
NORENDER = "--render" not in ARGV          # no preview renders unless asked (speed)
ONLY = _arg("--only")
TEX_OVERRIDE = int(_arg("--tex", "0"))
OUT = os.path.abspath(_arg("--out", os.path.join(ROOT, "export")))
GPU = "--gpu" in ARGV                      # bake on the GPU (OptiX/CUDA/HIP/oneAPI/Metal, whatever Cycles finds)


def _find_python():
    """System Python with numpy + Pillow (writes the PNGs). Override with the WJ_PYTHON environment variable."""
    p = os.environ.get("WJ_PYTHON")
    if p:
        return p
    for c in ("python3", "python", "py"):
        w = shutil.which(c)
        if w and "WindowsApps" not in w:
            return w
    return "python3"


PYTHON = _find_python()

# =================================================================== materials
class Mat:
    def __init__(self, recipe, params, name=None):
        if recipe not in MT.RECIPES:
            raise ValueError("unknown recipe %r (have %s)" % (recipe, sorted(MT.RECIPES)))
        self.recipe, self.params = recipe, params
        h = hashlib.md5(repr((recipe, sorted((k, repr(v)) for k, v in params.items()))).encode()).hexdigest()[:6]
        self.name = name or "%s_%s" % (recipe, h)
        self.slot = MT.SLOT.get(recipe, "base")


def mat(recipe, name=None, **params):
    """Procedural material spec. See kit/materials.py for recipes and their params."""
    return Mat(recipe, params, name)


TEAM = mat("team", name="team")
GLOW = mat("glow", name="glow")


# =================================================================== geometry (local-space bmesh builders)
def _bm():
    return bmesh.new()


def box(sx, sy, sz, chamfer=0.0, drop=()):
    """Box centred on the origin. drop: faces to delete, e.g. ('-z',) for a face sitting on the ground."""
    bm = _bm()
    bmesh.ops.create_cube(bm, size=1.0)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, v.co.z * sz))
    if chamfer > 0:
        bmesh.ops.bevel(bm, geom=list(bm.edges) + list(bm.verts), offset=chamfer, segments=1, affect="EDGES",
                        profile=0.5, clamp_overlap=True)
    _drop(bm, drop)
    return bm


def _drop(bm, drop):
    if not drop:
        return
    dirs = {"+x": (1, 0, 0), "-x": (-1, 0, 0), "+y": (0, 1, 0), "-y": (0, -1, 0), "+z": (0, 0, 1), "-z": (0, 0, -1)}
    bm.normal_update()
    kill = []
    for f in bm.faces:
        for d in drop:
            if f.normal.dot(Vector(dirs[d])) > 0.999:
                kill.append(f)
    bmesh.ops.delete(bm, geom=list(set(kill)), context="FACES")


def lathe(profile, seg=16, phase=0.0, axis="z", cap=True):
    """profile: [(r, z), ...] bottom->top.  r == 0 at an end closes it with a fan."""
    bm = _bm()
    rings = []
    for r, z in profile:
        if r < 1e-9:
            rings.append([bm.verts.new((0, 0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(phase + 2 * math.pi * i / seg), r * math.sin(phase + 2 * math.pi * i / seg), z))
                          for i in range(seg)])
    for A, B in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                bm.faces.new([A[0], B[i], B[j]])
            elif len(B) == 1:
                bm.faces.new([A[i], B[0], A[j]])
            else:
                bm.faces.new([A[i], A[j], B[j], B[i]])
    if cap:
        if len(rings[0]) > 1:
            bm.faces.new(rings[0][::-1])
        if len(rings[-1]) > 1:
            bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _axis(bm, axis)
    return bm


def _axis(bm, axis):
    if axis == "x":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(math.pi / 2, 3, "Y"))
    elif axis == "y":
        bmesh.ops.rotate(bm, verts=bm.verts, cent=(0, 0, 0), matrix=Matrix.Rotation(-math.pi / 2, 3, "X"))


def cyl(r, h, seg=16, axis="z", r2=None, caps=True, phase=None):
    """Cylinder / frustum centred on the origin along axis."""
    r2 = r if r2 is None else r2
    prof = ([(0, -h / 2)] if caps else []) + [(r, -h / 2), (r2, h / 2)] + ([(0, h / 2)] if caps else [])
    bm = lathe(prof, seg, phase if phase is not None else math.pi / seg, axis="z", cap=False)
    _axis(bm, axis)
    return bm


def tube(ro, ri, h, seg=16, axis="z", a0=0.0, a1=360.0):
    """Thick ring / pipe section centred on origin. a0..a1 (deg) for partial arcs."""
    bm = _bm()
    full = abs(a1 - a0) >= 359.999
    n = seg if full else seg + 1
    ang = [math.radians(a0 + (a1 - a0) * i / seg) for i in range(n)]
    def ring(r, z):
        return [bm.verts.new((r * math.cos(a), r * math.sin(a), z)) for a in ang]
    O0, O1, I0, I1 = ring(ro, -h / 2), ring(ro, h / 2), ring(ri, -h / 2), ring(ri, h / 2)
    m = seg
    for i in range(m):
        j = (i + 1) % n
        bm.faces.new([O0[i], O0[j], O1[j], O1[i]])
        bm.faces.new([I0[j], I0[i], I1[i], I1[j]])
        bm.faces.new([O0[j], O0[i], I0[i], I0[j]])
        bm.faces.new([O1[i], O1[j], I1[j], I1[i]])
    if not full:
        bm.faces.new([O0[0], O1[0], I1[0], I0[0]])
        bm.faces.new([O0[-1], I0[-1], I1[-1], O1[-1]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    _axis(bm, axis)
    return bm


def prism(pts, thick, plane="xz", taper=None):
    """Extrude a 2D polygon. plane 'xz': pts are (x, z), extruded along y (centred). 'xy' -> along z, 'yz' -> along x."""
    bm = _bm()
    def P(u, v, w):
        return {"xz": (u, w, v), "xy": (u, v, w), "yz": (w, u, v)}[plane]
    lo = [bm.verts.new(P(u, v, -thick / 2)) for u, v in pts]
    hi = [bm.verts.new(P(u, v, thick / 2)) for u, v in pts]
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def sweep(path, profile, closed=False, cap=True, up=(0, 0, 1), scale=None):
    """Sweep a closed 2D profile [(u, v)] along a 3D polyline. u -> side, v -> up (parallel-transport frames).
    scale: optional list of per-point scale factors."""
    bm = _bm()
    P = [Vector(p) for p in path]
    n = len(P)
    tang = []
    for i in range(n):
        if closed:
            t = (P[(i + 1) % n] - P[i - 1])
        else:
            t = (P[min(i + 1, n - 1)] - P[max(i - 1, 0)])
        tang.append(t.normalized())
    u0 = Vector(up)
    side = u0.cross(tang[0])
    if side.length < 1e-6:
        side = Vector((1, 0, 0)).cross(tang[0])
    side.normalize()
    rings = []
    for i in range(n):
        if i > 0:
            side = side - tang[i] * side.dot(tang[i])
            side.normalize()
        upv = tang[i].cross(side).normalized()
        s = scale[i] if scale else 1.0
        # mitre: scale the profile across the bend so wall thickness stays constant
        rings.append([bm.verts.new(P[i] + side * (u * s) + upv * (v * s)) for u, v in profile])
    m = len(profile)
    pairs = list(zip(rings, rings[1:])) + ([(rings[-1], rings[0])] if closed else [])
    for A, B in pairs:
        for k in range(m):
            j = (k + 1) % m
            bm.faces.new([A[k], A[j], B[j], B[k]])
    if cap and not closed:
        bm.faces.new(rings[0][::-1]); bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def circle2(r, n=8, phase=None):
    ph = math.pi / n if phase is None else phase
    return [(r * math.cos(ph + 2 * math.pi * i / n), r * math.sin(ph + 2 * math.pi * i / n)) for i in range(n)]


def rect2(w, h):
    return [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)]


def torus(R, r, seg=24, rseg=8, axis="z"):
    path = [(R * math.cos(2 * math.pi * i / seg), R * math.sin(2 * math.pi * i / seg), 0) for i in range(seg)]
    bm = sweep(path, circle2(r, rseg), closed=True, cap=False, up=(0, 0, 1))
    _axis(bm, axis)
    return bm


def sphere(r, seg=16, rings=8, squash=1.0):
    prof = [(0, -r * squash)] + [(r * math.sin(math.pi * i / rings), -r * squash * math.cos(math.pi * i / rings)) for i in range(1, rings)] + [(0, r * squash)]
    return lathe(prof, seg, cap=False)


def grid(sx, sy, nx, ny):
    """Flat grid in XY (cloth, sheets), centred."""
    bm = _bm()
    bmesh.ops.create_grid(bm, x_segments=nx, y_segments=ny, size=0.5)
    for v in bm.verts:
        v.co = Vector((v.co.x * sx, v.co.y * sy, 0))
    return bm


# ---- structural sections, built along +X from 0..L (profile in YZ)
def ibeam(L, h, w, tw, tf):
    p = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, -h / 2 + tf), (tw / 2, -h / 2 + tf), (tw / 2, h / 2 - tf), (w / 2, h / 2 - tf),
         (w / 2, h / 2), (-w / 2, h / 2), (-w / 2, h / 2 - tf), (-tw / 2, h / 2 - tf), (-tw / 2, -h / 2 + tf), (-w / 2, -h / 2 + tf)]
    return _extrude_x(p, L)


def channel(L, h, w, t):
    """C-channel, web on -y side, flanges pointing +y."""
    p = [(-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, -h / 2 + t), (-w / 2 + t, -h / 2 + t), (-w / 2 + t, h / 2 - t), (w / 2, h / 2 - t),
         (w / 2, h / 2), (-w / 2, h / 2)]
    return _extrude_x(p, L)


def angle(L, a, t, b=None):
    b = a if b is None else b
    p = [(0, 0), (a, 0), (a, t), (t, t), (t, b), (0, b)]
    return _extrude_x([(u - a / 2, v - b / 2) for u, v in p], L)


def rtube(L, w, h, t=None):
    """Rectangular (hollow if t) tube."""
    if not t:
        return _extrude_x(rect2(w, h), L)
    bm = _bm()
    outer, inner = rect2(w, h), rect2(w - 2 * t, h - 2 * t)
    O0 = [bm.verts.new((0, u, v)) for u, v in outer]; O1 = [bm.verts.new((L, u, v)) for u, v in outer]
    I0 = [bm.verts.new((0, u, v)) for u, v in inner]; I1 = [bm.verts.new((L, u, v)) for u, v in inner]
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([O0[i], O0[j], O1[j], O1[i]]); bm.faces.new([I0[j], I0[i], I1[i], I1[j]])
        bm.faces.new([O0[j], O0[i], I0[i], I0[j]]); bm.faces.new([O1[i], O1[j], I1[j], I1[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def pipe(L, r, seg=8):
    return _extrude_x(circle2(r, seg), L)


def _extrude_x(prof, L):
    bm = _bm()
    a = [bm.verts.new((0, u, v)) for u, v in prof]
    b = [bm.verts.new((L, u, v)) for u, v in prof]
    bm.faces.new(a[::-1]); bm.faces.new(b)
    n = len(prof)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([a[i], a[j], b[j], b[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def corrugated(L, H, pitch=0.1, depth=0.02, kind="sine", n_per=6, thick=0.0):
    """Corrugated sheet in the XZ plane (corrugations run along Z, wave along X), facing +/-Y.
    L along x, H along z, centred.  thick>0 makes it double sided with closed edges."""
    bm = _bm()
    cols = []
    waves = max(1, round(L / pitch))
    pitch = L / waves
    if kind == "sine":
        xs = [i * pitch / n_per for i in range(waves * n_per + 1)]
        ys = [depth / 2 * math.sin(2 * math.pi * x / pitch) for x in xs]
    else:   # trapezoid box-profile (shipping container)
        xs, ys = [], []
        for w in range(waves):
            x0 = w * pitch
            for fx, fy in ((0.0, -0.5), (0.18, -0.5), (0.32, 0.5), (0.68, 0.5), (0.82, -0.5)):
                xs.append(x0 + fx * pitch); ys.append(fy * depth)
        xs.append(L); ys.append(-0.5 * depth)
    for x, y in zip(xs, ys):
        cols.append((bm.verts.new((x - L / 2, y, -H / 2)), bm.verts.new((x - L / 2, y, H / 2))))
    for (a0, a1), (b0, b1) in zip(cols, cols[1:]):
        bm.faces.new([a0, b0, b1, a1])
    if thick > 0:
        back = [(bm.verts.new((a.co.x, a.co.y + thick, a.co.z)), bm.verts.new((b.co.x, b.co.y + thick, b.co.z))) for a, b in cols]
        for (a0, a1), (b0, b1) in zip(back, back[1:]):
            bm.faces.new([a0, a1, b1, b0])
        for (f0, f1), (k0, k1) in zip(cols, back):
            pass
        for (fa0, fa1), (fb0, fb1), (ka0, ka1), (kb0, kb1) in zip(cols, cols[1:], back, back[1:]):
            bm.faces.new([fa0, ka0, kb0, fb0]); bm.faces.new([fa1, fb1, kb1, ka1])
        bm.faces.new([cols[0][0], cols[0][1], back[0][1], back[0][0]])
        bm.faces.new([cols[-1][0], back[-1][0], back[-1][1], cols[-1][1]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def hexbolt(r=0.012, h=0.008):
    return cyl(r, h, seg=6, phase=0.0)


def deform(bm, fn):
    """fn(Vector) -> Vector, applied to every vertex (bends, sags, dents)."""
    for v in bm.verts:
        v.co = Vector(fn(v.co.copy()))
    return bm


def merge(*bms):
    """Merge several bmeshes into one (they stay separate shells)."""
    out = _bm()
    for b in bms:
        me = bpy.data.meshes.new("_tmp")
        b.to_mesh(me)
        out.from_mesh(me)
        bpy.data.meshes.remove(me)
        b.free()
    return out


def transform(bm, at=(0, 0, 0), rot=(0, 0, 0)):
    bm.transform(Matrix.Translation(at) @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4())
    return bm


def align_x(p0, p1, roll=0.0, up=(0, 0, 1)):
    """Matrix that maps local +X (0..L) onto the segment p0->p1; local +Z stays as close to `up` as possible."""
    p0, p1 = Vector(p0), Vector(p1)
    d = (p1 - p0).normalized()
    upv = Vector(up)
    if abs(d.dot(upv)) > 0.999:
        upv = Vector((1, 0, 0)) if abs(d.x) < 0.9 else Vector((0, 1, 0))
    y = upv.cross(d).normalized()
    z = d.cross(y).normalized()
    R = Matrix((d, y, z)).transposed().to_4x4()
    return Matrix.Translation(p0) @ R @ Matrix.Rotation(math.radians(roll), 4, "X")


# =================================================================== scene helpers
def _use_gpu(sc):
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
    except Exception:
        return None
    for t in ("OPTIX", "CUDA", "HIP", "ONEAPI", "METAL"):
        try:
            prefs.compute_device_type = t
        except Exception:
            continue
        try:
            prefs.get_devices()
        except Exception:
            pass
        devs = [d for d in prefs.devices if d.type == t]
        if devs:
            for d in prefs.devices:
                d.use = d.type == t
            sc.cycles.device = "GPU"
            return t
    return None


def _reset():
    bpy.ops.wm.read_factory_settings(use_empty=True)
    sc = bpy.context.scene
    sc.render.engine = "CYCLES"
    sc.cycles.device = "CPU"
    if GPU:
        t = _use_gpu(sc)
        print("[kit] GPU backend:", t or "none found, using CPU")
    sc.unit_settings.system = "METRIC"
    sc.unit_settings.scale_length = 1.0
    return sc


def _link(ob):
    bpy.context.scene.collection.objects.link(ob)
    return ob


def _select(objs, active=None):
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in objs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = active or (objs[0] if objs else None)


class Part:
    def __init__(self, ob):
        self.ob = ob

    def move(self, dx=0, dy=0, dz=0):
        self.ob.data.transform(Matrix.Translation((dx, dy, dz)))
        return self


def _colorspace(img, name):
    for n in ((name, "Linear", "Linear Rec.709", "scene_linear") if name.startswith("Linear") else (name,)):
        try:
            img.colorspace_settings.name = n
            return
        except TypeError:
            continue


def _np_img(img):
    a = np.empty(img.size[0] * img.size[1] * 4, np.float32)
    img.pixels.foreach_get(a)
    return a.reshape(img.size[1], img.size[0], 4)


def _blur(a, it=1):
    for _ in range(it):
        a = (a + np.roll(a, 1, 0) + np.roll(a, -1, 0)) / 3.0
        a = (a + np.roll(a, 1, 1) + np.roll(a, -1, 1)) / 3.0
    return a


def image_from_array(name, arr, color=False):
    """numpy float array (H, W) or (H, W, 3|4), row 0 = TOP, values 0..1 -> packed Blender image for recipes
    (e.g. K.mat("card", img=...)).  Create it AFTER K.Asset(...) (the Asset constructor resets the scene)."""
    a = np.asarray(arr, np.float32)
    if a.ndim == 2:
        a = np.dstack([a, a, a])
    if a.shape[2] == 3:
        a = np.dstack([a, np.ones(a.shape[:2], np.float32)])
    h, w = a.shape[:2]
    img = bpy.data.images.new(name, w, h, alpha=True, float_buffer=True)
    img.colorspace_settings.name = "Linear Rec.709" if color else "Non-Color"
    img.pixels.foreach_set(a[::-1].ravel())
    img.pack()
    return img


def stencil_image(name, kind="wedge", res=512):
    """Procedural stencil masks (white = paint), returned as a non-colour Blender image."""
    yy, xx = np.mgrid[0:res, 0:res].astype(np.float32) / res
    m = np.zeros((res, res), np.float32)
    if kind == "wedge":
        # cheese wedge in side view: right-angle triangle, rind band on top, three holes, stencil bridges
        x, y = xx, yy
        tri = (x > 0.08) & (x < 0.92) & (y > 0.18) & (y < 0.18 + 0.62 * (x - 0.08) / 0.84)
        rind = (y > 0.18 + 0.62 * (x - 0.08) / 0.84 - 0.07) & tri
        m = tri.astype(np.float32)
        for cx, cy, r in ((0.55, 0.30, 0.06), (0.74, 0.42, 0.05), (0.80, 0.26, 0.035), (0.36, 0.24, 0.035)):
            m[(x - cx) ** 2 + (y - cy) ** 2 < r * r] = 0
        m[rind & (np.abs(x - 0.5) > 0.0)] = 0  # gap line between paste and rind
        rind2 = (y > 0.18 + 0.62 * (x - 0.08) / 0.84 - 0.05) & (y < 0.18 + 0.62 * (x - 0.08) / 0.84 + 0.02) & (x > 0.12) & (x < 0.92)
        m[rind2] = 1
        for bx in (0.33, 0.62):   # stencil bridges
            m[np.abs(x - bx) < 0.012] = 0
    elif kind == "chevron":
        m = (np.abs(((xx + yy) * 4) % 1.0 - 0.5) < 0.25).astype(np.float32)
    img = bpy.data.images.new(name, res, res, alpha=False, float_buffer=True)
    img.colorspace_settings.name = "Non-Color"
    px = np.dstack([m, m, m, np.ones_like(m)])
    img.pixels.foreach_set(px.ravel())
    img.pack()
    return img


# =================================================================== variant helpers
def group_verts(ob, name):
    vg = ob.vertex_groups.get(name)
    if vg is None:
        return []
    gi = vg.index
    return [v.index for v in ob.data.vertices if any(g.group == gi and g.weight > 0.5 for g in v.groups)]


def delete_group(ob, name):
    """Remove every vertex (and its faces) tagged with group `name` (e.g. the wheels on a rack)."""
    idx = set(group_verts(ob, name))
    bm = bmesh.new()
    bm.from_mesh(ob.data)
    bm.verts.ensure_lookup_table()
    bmesh.ops.delete(bm, geom=[bm.verts[i] for i in idx], context="VERTS")
    bm.to_mesh(ob.data)
    bm.free()
    ob.data.update()


def rotate_group(ob, name, pivot, axis, deg):
    """Swing the vertices of group `name` about an axis through `pivot` (doors, lids). Positions are in the
    asset's final (pivot-shifted) space -- use A.shift to convert from modelling space."""
    R = Matrix.Rotation(math.radians(deg), 4, axis)
    T = Matrix.Translation(Vector(pivot)) @ R @ Matrix.Translation(-Vector(pivot))
    for i in group_verts(ob, name):
        v = ob.data.vertices[i]
        v.co = T @ v.co
    # rotate split normals implicitly by recomputation
    ob.data.update()


# =================================================================== the asset
class Asset:
    def __init__(self, name, size, tris, tex=None, pivot="bottom", note="", edge_r=None, cav_d=None, ao_d=None,
                 bevel_r=None, lod1=None, folder=None, alpha=False):
        self.skip = bool(ONLY) and ONLY not in (name, "SM_" + name)
        self.name, self.sm = name, "SM_" + name
        self.size = tuple(size)
        W, H, D = size
        self.target = (D, W, H)
        self.budget = tris
        big = max(size)
        self.tex = TEX_OVERRIDE or tex or (2048 if (big >= 2.0 or tris >= 4000) else 1024)
        self.pivot, self.note = pivot, note
        self.user_ctx = dict(edge_r=edge_r, cav_d=cav_d, ao_d=ao_d, bevel_r=bevel_r)
        self.lod1 = (tris > 5000) if lod1 is None else lod1
        self.folder = folder or name
        self.alpha = alpha
        self.parts, self.cutters, self.ucx_specs = [], [], []
        self.mats = {}
        self._rng = random.Random(name)
        self.t0 = time.time()
        self.log = []
        _reset()

    # ------------------------------------------------------------ parts
    def add(self, bm, m, at=(0, 0, 0), rot=(0, 0, 0), M=None, smooth=35.0, group=None, grain=None, name="part", drop=()):
        """Add a bmesh built in its own local frame.  `m` is a K.mat() spec.
        at/rot (deg, XYZ euler) or a full matrix M place it.  smooth: angle (deg) below which edges shade smooth.
        grain: local axis ('x','y','z') used as the texture's long axis (default: the longest extent)."""
        if self.skip:
            bm.free()
            return None
        _drop(bm, drop)
        bm.verts.ensure_lookup_table()
        if len(bm.verts) == 0:
            bm.free()
            return None
        co = np.array([v.co[:] for v in bm.verts])
        ext = co.max(0) - co.min(0)
        order = list(np.argsort(-ext))
        if grain:
            g = "xyz".index(grain)
            order = [g] + [i for i in order if i != g]
        lco = bm.loops.layers.float_vector.new("lco")     # corner domain: cut faces can get their own frame
        pid = bm.verts.layers.float.new("pid")
        sang = bm.faces.layers.float.new("sang")
        cutl = bm.faces.layers.float.new("cut")
        r = self._rng.random()
        for v in bm.verts:
            v[pid] = r
        for f in bm.faces:
            f[cutl] = 1.0 if name == "cutter" else 0.0
            for lo in f.loops:
                c = lo.vert.co
                lo[lco] = Vector((c[order[0]], c[order[1]], c[order[2]]))
        bm.normal_update()
        lim = math.radians(smooth)
        for e in bm.edges:
            if len(e.link_faces) == 2:
                e.smooth = e.link_faces[0].normal.angle(e.link_faces[1].normal, 0.0) <= lim
            else:
                e.smooth = False
        for f in bm.faces:
            f.smooth = True
            f[sang] = max(smooth, 0.01)
        if M is None:
            M = Matrix.Translation(at) @ Euler([math.radians(a) for a in rot], "XYZ").to_matrix().to_4x4()
        bm.transform(M)
        me = bpy.data.meshes.new(name)
        bm.to_mesh(me)
        bm.free()
        ob = _link(bpy.data.objects.new(name, me))
        me.materials.append(self._mat(m))
        if group:
            vg = ob.vertex_groups.new(name=group)
            vg.add(list(range(len(me.vertices))), 1.0, "REPLACE")
        p = Part(ob)
        self.parts.append(p)
        return p

    def _mat(self, m):
        if m.name not in self.mats:
            mt = bpy.data.materials.new(m.name)
            mt.use_nodes = True
            self.mats[m.name] = (mt, m)
        return self.mats[m.name][0]

    # convenience wrappers ------------------------------------------------
    def rod(self, p0, p1, r, m, seg=8, **kw):
        L = (Vector(p1) - Vector(p0)).length
        return self.add(pipe(L, r, seg), m, M=align_x(p0, p1, kw.pop("roll", 0.0), kw.pop("up", (0, 0, 1))), **kw)

    def beam(self, bm_fn, p0, p1, m, roll=0.0, up=(0, 0, 1), **kw):
        """bm_fn(L) -> bmesh along +X (e.g. lambda L: K.ibeam(L, .3, .15, .01, .015))."""
        L = (Vector(p1) - Vector(p0)).length
        return self.add(bm_fn(L), m, M=align_x(p0, p1, roll, up), **kw)

    def cut(self, target, cutter, mode="DIFFERENCE"):
        """Exact boolean. Faces made by the cutter keep the CUTTER's material (material_mode TRANSFER)."""
        if self.skip or target is None or cutter is None:
            return
        md = target.ob.modifiers.new("cut", "BOOLEAN")
        md.operation, md.solver, md.object = mode, "EXACT", cutter.ob
        md.use_self = True
        try:
            md.material_mode = "TRANSFER"
        except Exception:
            pass
        cutter.ob.hide_render = True
        cutter.ob.display_type = "WIRE"
        if cutter not in self.cutters:
            self.cutters.append(cutter)
        if cutter in self.parts:
            self.parts.remove(cutter)

    def cutter(self, bm, m=None, at=(0, 0, 0), rot=(0, 0, 0), M=None, smooth=30):
        """A boolean tool. Its material and smoothing angle are what the cut faces get."""
        p = self.add(bm, m or mat("flat"), at=at, rot=rot, M=M, smooth=smooth, name="cutter")
        if p:
            self.parts.remove(p)
            self.cutters.append(p)
        return p

    # collision -----------------------------------------------------------
    def ucx_box(self, center, size, rot=(0, 0, 0)):
        bm = box(*size)
        transform(bm, center, rot)
        self._ucx_bm(bm)

    def ucx_cyl(self, center, r, h, seg=8, axis="z", rot=(0, 0, 0)):
        bm = cyl(r, h, seg, axis=axis)
        transform(bm, center, rot)
        self._ucx_bm(bm)

    def ucx_hull(self, points):
        bm = _bm()
        for p in points:
            bm.verts.new(p)
        self._ucx_bm(bm)

    def ucx_parts(self, *parts):
        pts = []
        for p in parts:
            if p:
                mw = p.ob.matrix_world
                pts += [mw @ v.co for v in p.ob.data.vertices]
        if pts:
            self.ucx_hull(pts)

    def _ucx_bm(self, bm):
        if self.skip:
            bm.free()
            return
        pts = [v.co.copy() for v in bm.verts]
        bm.free()
        self.ucx_specs.append(pts)

    # ------------------------------------------------------------ build
    def build(self, variants=None, skins=None):
        """variants: {"Name": fn(asset, ob)} -- extra meshes sharing this texture set (posed copies).
        skins: {"Suffix": {old_mat_name: K.mat(...)}} -- extra texture sets on the same mesh (first = default)."""
        if self.skip:
            print("[kit] skip", self.name)
            return
        self.dir = os.path.join(OUT, self.folder)
        os.makedirs(self.dir, exist_ok=True)
        ob = self._assemble()
        self._ucx_objects(ob)
        self._unwrap(ob)
        stats = self._stats(ob)
        self._ctx()
        if DRAFT:
            self._materials(None)
            if not NORENDER:
                self._render([ob], os.path.join(self.dir, "_draft_%s.jpg" % self.name), draft=True)
            self._report(ob, stats, draft=True)
            return ob
        sk = [("", {})] + list((skins or {}).items())
        mask = self._bake_mask(ob)
        main_imgs = None
        for si, (sfx, remap) in enumerate(sk):
            if remap:
                self._materials(mask, remap)
            elif si == 0:
                self._materials(mask)
            tag = self.name + (("_" + sfx) if sfx else "")
            imgs = self._bake_textures(ob, mask, tag)
            if si == 0:
                main_imgs = imgs
            self.log.append(("textures", tag))
            if si == 0:
                self.skin_imgs = [(tag, imgs)]
            else:
                self.skin_imgs.append((tag, imgs))
        self._final_materials(ob, main_imgs)
        lod = self._export(ob)
        render_objs = [ob]
        if len(self.skin_imgs) > 1:
            render_objs = self._skin_copies(ob)
        if not NORENDER:
            self._render(render_objs, os.path.join(self.dir, "%s_preview.jpg" % self.sm))
        self._report(ob, stats, lod=lod)
        for vname, fn in (variants or {}).items():
            self._variant(ob, vname, fn)
        for f in os.listdir(self.dir):
            if f.endswith("_Normal.gl.png"):
                os.remove(os.path.join(self.dir, f))
        return ob

    # ------------------------------------------------------------ assemble
    def _assemble(self):
        dg = bpy.context.evaluated_depsgraph_get()
        objs = []
        for p in self.parts:
            ob = p.ob
            if ob.modifiers:
                me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
                ob.modifiers.clear()
                old = ob.data
                ob.data = me
                bpy.data.meshes.remove(old)
            objs.append(ob)
        for c in self.cutters:
            bpy.data.objects.remove(c.ob, do_unlink=True)
        objs = [o for o in objs if len(o.data.polygons)]
        main = objs[0]
        _select(objs, main)
        with bpy.context.temp_override(active_object=main, selected_editable_objects=objs, object=main):
            bpy.ops.object.join()
        main.name = self.sm
        main.data.name = self.sm
        me = main.data
        bm = bmesh.new()
        bm.from_mesh(me)
        bmesh.ops.dissolve_degenerate(bm, dist=1e-6, edges=bm.edges)
        # faces made by boolean cutters: texture them in object space (their own frame is lost in the boolean)
        cl = bm.faces.layers.float.get("cut")
        ll = bm.loops.layers.float_vector.get("lco")
        if cl and ll:
            for f in bm.faces:
                if f[cl] > 0.5:
                    for lo in f.loops:
                        lo[ll] = lo.vert.co.copy()
        # re-derive hard edges after booleans: an edge is hard when its dihedral angle exceeds the smaller
        # smoothing angle of the two faces (cut faces carry the cutter's angle)
        sl = bm.faces.layers.float.get("sang")
        bm.normal_update()
        for e in bm.edges:
            if len(e.link_faces) != 2:
                e.smooth = False
                continue
            f1, f2 = e.link_faces
            a1 = f1[sl] if sl and f1[sl] > 0 else 35.0
            a2 = f2[sl] if sl and f2[sl] > 0 else 35.0
            ang = math.degrees(f1.normal.angle(f2.normal, 0.0))
            e.smooth = ang <= min(a1, a2)
        bmesh.ops.triangulate(bm, faces=bm.faces, quad_method="BEAUTY", ngon_method="BEAUTY")
        bm.to_mesh(me)
        bm.free()
        if hasattr(me, "use_auto_smooth"):          # Blender <= 4.0; 4.1+ shades by the sharp-edge flags directly
            me.use_auto_smooth = True
            me.auto_smooth_angle = math.pi
        # pivot
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        lo, hi = co.min(0), co.max(0)
        if self.pivot == "bottom":
            shift = Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -lo[2]))
        elif self.pivot == "center":
            shift = Vector((-(lo[0] + hi[0]) / 2, -(lo[1] + hi[1]) / 2, -(lo[2] + hi[2]) / 2))
        else:
            shift = Vector((0, 0, 0))
        self.shift = shift
        if shift.length > 1e-6:
            me.transform(Matrix.Translation(shift))
        me.update()
        return main

    def _ucx_objects(self, ob):
        self.ucx = []
        for i, pts in enumerate(self.ucx_specs):
            bm = _bm()
            for p in pts:
                bm.verts.new(Vector(p) + self.shift)
            res = bmesh.ops.convex_hull(bm, input=bm.verts)
            kill = list({g for g in res["geom_interior"] + res["geom_unused"] if isinstance(g, bmesh.types.BMVert)})
            if kill:
                bmesh.ops.delete(bm, geom=kill, context="VERTS")
            bmesh.ops.triangulate(bm, faces=bm.faces)
            me = bpy.data.meshes.new("UCX_%s_%02d" % (self.sm, i))
            bm.to_mesh(me)
            bm.free()
            u = _link(bpy.data.objects.new(me.name, me))
            u.display_type = "WIRE"
            u.hide_render = True
            self.ucx.append(u)

    # ------------------------------------------------------------ UV
    def _unwrap(self, ob):
        _select([ob], ob)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        margin = 6.0 / self.tex
        bpy.ops.uv.smart_project(angle_limit=math.radians(62), margin_method="SCALED", island_margin=margin,
                                 area_weight=0.0, correct_aspect=True, scale_to_bounds=False)
        try:
            bpy.ops.uv.pack_islands(rotate=True, margin_method="SCALED", margin=margin, shape_method="CONCAVE")
        except TypeError:
            bpy.ops.uv.pack_islands(rotate=True, margin=margin)
        bpy.ops.object.mode_set(mode="OBJECT")

    def _stats(self, ob):
        me = ob.data
        me.calc_loop_triangles()
        tris = len(me.loop_triangles)
        uv = me.uv_layers.active.data
        a3 = auv = 0.0
        for t in me.loop_triangles:
            v = [me.vertices[i].co for i in t.vertices]
            a3 += ((v[1] - v[0]).cross(v[2] - v[0])).length / 2
            u = [uv[l].uv for l in t.loops]
            auv += abs((u[1].x - u[0].x) * (u[2].y - u[0].y) - (u[2].x - u[0].x) * (u[1].y - u[0].y)) / 2
        co = np.empty(len(me.vertices) * 3, np.float32)
        me.vertices.foreach_get("co", co)
        co = co.reshape(-1, 3)
        lo, hi = co.min(0), co.max(0)
        self.px_per_m = self.tex * math.sqrt(auv / max(a3, 1e-9))
        return dict(tris=tris, bbox_min=[round(float(x), 4) for x in lo], bbox_max=[round(float(x), 4) for x in hi],
                    dims=[round(float(x), 4) for x in (hi - lo)], area_m2=round(a3, 3), uv_coverage=round(auv, 3),
                    px_per_m=round(self.px_per_m, 1))

    def _ctx(self):
        big = max(self.size)
        texel = 1.0 / max(self.px_per_m, 1.0)
        u = self.user_ctx
        self.ctx = dict(
            edge_r=u["edge_r"] or max(4.0 * texel, min(0.05, max(0.012, 0.02 * big ** 0.4))),
            cav_d=u["cav_d"] or max(0.02, min(0.15, 0.05 * big ** 0.5)),
            ao_d=u["ao_d"] or max(0.12, min(1.5, 0.35 * big ** 0.6)),
            bevel_r=u["bevel_r"] or max(0.0015, min(0.02, 2.2 * texel)),
        )

    # ------------------------------------------------------------ materials
    def _materials(self, mask_img, remap=None):
        self.graphs = {}
        ctx = dict(self.ctx, mask_image=mask_img)
        for name, (mt, spec) in self.mats.items():
            if remap and name in remap:
                spec = remap[name]
            g = MT.G(mt, ctx)
            out = MT.RECIPES[spec.recipe](g, dict(spec.params))
            self._wire(g, out)
            self.graphs[name] = g

    def _wire(self, g, out):
        nt = g.nt
        bsdf = g.node("ShaderNodeBsdfPrincipled")
        o = g.node("ShaderNodeOutputMaterial")
        g._set(bsdf.inputs["Base Color"], out["color"])
        g._set(bsdf.inputs["Roughness"], out.get("rough", 0.6))
        g._set(bsdf.inputs["Metallic"], out.get("metal", 0.0))
        bev = g.node("ShaderNodeBevel", samples=8)
        bev.inputs["Radius"].default_value = self.ctx["bevel_r"]
        bump = g.node("ShaderNodeBump")
        g._set(bump.inputs["Height"], out.get("height", 0.0))
        bump.inputs["Distance"].default_value = 0.001 * out.get("bump", 1.0)
        bump.inputs["Strength"].default_value = 1.0
        g.L.new(bev.outputs[0], bump.inputs["Normal"])
        g.L.new(bump.outputs[0], bsdf.inputs["Normal"])
        if "alpha" in out:
            g._set(bsdf.inputs["Alpha"], out["alpha"])
        g.L.new(bsdf.outputs[0], o.inputs["Surface"])
        em = g.node("ShaderNodeEmission")
        tgt = g.node("ShaderNodeTexImage")
        tgt.name = "BAKE_TARGET"
        nt.nodes.active = tgt
        g.bsdf, g.out_node, g.emit, g.target, g.channels = bsdf, o, em, tgt, out
        # channel sockets, forced to be sockets
        def sock(v, color=False):
            if isinstance(v, bpy.types.NodeSocket):
                return v
            return g.const_c(v) if color else g.const_f(v)
        g.ch = dict(color=sock(out["color"], True), rough=sock(out.get("rough", 0.6)), metal=sock(out.get("metal", 0.0)),
                    alpha=sock(out.get("alpha", 1.0)))
        rm = g.node("ShaderNodeCombineColor")
        g.L.new(g.ch["rough"], rm.inputs[0]); g.L.new(g.ch["metal"], rm.inputs[1])
        g.ch["rm"] = rm.outputs[0]

    def _route(self, mode, img):
        for name, g in self.graphs.items():
            L = g.L
            for l in list(g.out_node.inputs["Surface"].links):
                L.remove(l)
            for l in list(g.emit.inputs["Color"].links):
                L.remove(l)
            g.target.image = img
            g.nt.nodes.active = g.target
            if mode == "surface":
                L.new(g.bsdf.outputs[0], g.out_node.inputs["Surface"])
            else:
                src = g.ch[mode] if mode != "mask" else self._mask_sock(g)
                L.new(src, g.emit.inputs["Color"])
                L.new(g.emit.outputs[0], g.out_node.inputs["Surface"])

    def _mask_sock(self, g):
        e, c, a = g.live_masks()
        cc = g.node("ShaderNodeCombineColor")
        g.L.new(e, cc.inputs[0]); g.L.new(c, cc.inputs[1]); g.L.new(a, cc.inputs[2])
        return cc.outputs[0]

    # ------------------------------------------------------------ bake
    def _new_img(self, name, color=False, res=None):
        res = res or self.tex
        if name in bpy.data.images:
            bpy.data.images.remove(bpy.data.images[name])
        img = bpy.data.images.new(name, res, res, alpha=True, float_buffer=True)
        _colorspace(img, "Linear Rec.709" if color else "Non-Color")
        return img

    def _bake(self, ob, kind, img, samples):
        sc = bpy.context.scene
        sc.cycles.samples = samples
        sc.cycles.use_denoising = False
        sc.render.bake.use_clear = True
        sc.render.bake.margin = max(4, self.tex // 128)
        sc.render.bake.margin_type = "EXTEND"
        sc.render.bake.target = "IMAGE_TEXTURES"
        _select([ob], ob)
        t = time.time()
        if kind == "NORMAL":
            sc.render.bake.normal_space = "TANGENT"
            bpy.ops.object.bake(type="NORMAL", normal_space="TANGENT", margin=sc.render.bake.margin)
        else:
            bpy.ops.object.bake(type="EMIT", margin=sc.render.bake.margin)
        self.log.append(("bake", img.name, round(time.time() - t, 1)))
        print("[kit] baked %s in %.1fs" % (img.name, time.time() - t))

    def _bake_mask(self, ob):
        # temporary graphs just for the mask: live edge / cavity / AO
        self._materials(None)
        img = self._new_img("MASK_" + self.name)
        self._route("mask", img)
        self._bake(ob, "EMIT", img, 8)
        a = _np_img(img)
        a[..., :3] = _blur(a[..., :3], 1)
        img.pixels.foreach_set(a.ravel())
        img.update()
        return img

    def _bake_textures(self, ob, mask, tag):
        tex = self.tex
        col = self._new_img("COL_" + tag, color=True)
        self._route("color", col); self._bake(ob, "EMIT", col, 3)
        rm = self._new_img("RM_" + tag)
        self._route("rm", rm); self._bake(ob, "EMIT", rm, 2)
        alpha = None
        if self.alpha:
            alpha = self._new_img("A_" + tag)
            self._route("alpha", alpha); self._bake(ob, "EMIT", alpha, 2)
        nrm = self._new_img("NRM_" + tag)
        self._route("surface", nrm); self._bake(ob, "NORMAL", nrm, 5)
        self._route("surface", None)
        # ---- write PNGs through system python + PIL (optimised, exact colourspace handling)
        tmp = os.path.join(self.dir, "_tmp")
        os.makedirs(tmp, exist_ok=True)
        np.save(os.path.join(tmp, "col.npy"), _np_img(col)[::-1, :, :3])
        np.save(os.path.join(tmp, "rm.npy"), _np_img(rm)[::-1, :, :2])
        np.save(os.path.join(tmp, "nrm.npy"), _np_img(nrm)[::-1, :, :3])
        np.save(os.path.join(tmp, "ao.npy"), _np_img(mask)[::-1, :, 2])
        if alpha is not None:
            np.save(os.path.join(tmp, "alpha.npy"), _np_img(alpha)[::-1, :, 0])
        base = os.path.join(self.dir, "T_" + tag)
        subprocess.run([PYTHON, os.path.join(KIT, "pack.py"), tmp, base], check=True)
        for f in os.listdir(tmp):
            os.remove(os.path.join(tmp, f))
        os.rmdir(tmp)
        for i in (col, rm, nrm) + ((alpha,) if alpha else ()):
            bpy.data.images.remove(i)
        return dict(base=base + "_BaseColor.png", normal=base + "_Normal.png", orm=base + "_ORM.png",
                    normal_gl=base + "_Normal.gl.png")

    # ------------------------------------------------------------ export materials
    def _load(self, path, color):
        img = bpy.data.images.load(path, check_existing=True)
        img.colorspace_settings.name = "sRGB" if color else "Non-Color"
        return img

    def _pbr_material(self, name, imgs, glow=False):
        if name in bpy.data.materials:
            bpy.data.materials.remove(bpy.data.materials[name])
        m = bpy.data.materials.new(name)
        m.use_nodes = True
        nt = m.node_tree
        nt.nodes.clear()
        L = nt.links
        out = nt.nodes.new("ShaderNodeOutputMaterial")
        b = nt.nodes.new("ShaderNodeBsdfPrincipled")
        L.new(b.outputs[0], out.inputs["Surface"])
        tb = nt.nodes.new("ShaderNodeTexImage"); tb.image = self._load(imgs["base"], True)
        L.new(tb.outputs["Color"], b.inputs["Base Color"])
        if self.alpha:
            L.new(tb.outputs["Alpha"], b.inputs["Alpha"])
            for k, v in (("blend_method", "CLIP"), ("alpha_threshold", 0.5), ("shadow_method", "CLIP"),
                         ("surface_render_method", "DITHERED")):
                try:
                    setattr(m, k, v)
                except Exception:
                    pass
        to = nt.nodes.new("ShaderNodeTexImage"); to.image = self._load(imgs["orm"], False)
        sp = nt.nodes.new("ShaderNodeSeparateColor")
        L.new(to.outputs["Color"], sp.inputs[0])
        L.new(sp.outputs[1], b.inputs["Roughness"])
        L.new(sp.outputs[2], b.inputs["Metallic"])
        tn = nt.nodes.new("ShaderNodeTexImage"); tn.image = self._load(imgs["normal_gl"], False)
        tn.name = "NORMAL_TEX"
        nm = nt.nodes.new("ShaderNodeNormalMap")
        L.new(tn.outputs["Color"], nm.inputs["Color"])
        L.new(nm.outputs[0], b.inputs["Normal"])
        # glTF occlusion hookup
        grp = bpy.data.node_groups.get("glTF Material Output")
        if grp is None:
            grp = bpy.data.node_groups.new("glTF Material Output", "ShaderNodeTree")
            grp.interface.new_socket("Occlusion", in_out="INPUT", socket_type="NodeSocketFloat")
        gn = nt.nodes.new("ShaderNodeGroup"); gn.node_tree = grp
        L.new(sp.outputs[0], gn.inputs["Occlusion"])
        if glow:
            L.new(tb.outputs["Color"], b.inputs["Emission Color"])
            b.inputs["Emission Strength"].default_value = 3.0
        return m

    def _final_materials(self, ob, imgs):
        me = ob.data
        names = [m.name for m in me.materials]
        slot_of = []
        for n in names:
            spec = self.mats[n][1]
            slot_of.append(spec.slot)
        order = ["base"] + [s for s in ("TeamPaint", "Glow") if s in slot_of]
        newmats = {"base": self._pbr_material("M_" + self.name, imgs)}
        if "TeamPaint" in order:
            newmats["TeamPaint"] = self._pbr_material("TeamPaint", imgs)
        if "Glow" in order:
            newmats["Glow"] = self._pbr_material("Glow", imgs, glow=True)
        if "base" not in slot_of:
            order.remove("base")
        idx = np.empty(len(me.polygons), np.int32)
        me.polygons.foreach_get("material_index", idx)
        remap = np.array([order.index(s) for s in slot_of], np.int32)
        idx = remap[idx]
        me.materials.clear()
        for s in order:
            me.materials.append(newmats[s])
        me.polygons.foreach_set("material_index", idx)
        me.update()
        self.slots = [m.name for m in me.materials]

    # ------------------------------------------------------------ export
    def _swap_normal(self, ob, gl):
        for m in ob.data.materials:
            n = m.node_tree.nodes.get("NORMAL_TEX")
            if n:
                p = n.image.filepath
                want = p.replace("_Normal.png", "_Normal.gl.png") if gl else p.replace("_Normal.gl.png", "_Normal.png")
                if want != p:
                    n.image = self._load(want, False)

    def _fbx(self, objs, path):
        _select(objs, objs[0])
        bpy.ops.export_scene.fbx(filepath=path, use_selection=True, object_types={"MESH"}, apply_unit_scale=True,
                                 apply_scale_options="FBX_SCALE_NONE", bake_space_transform=True, mesh_smooth_type="FACE",
                                 use_tspace=True, use_triangles=True, use_mesh_modifiers=True, path_mode="STRIP",
                                 embed_textures=False, add_leaf_bones=False, colors_type="NONE",
                                 axis_forward="-Z", axis_up="Y", use_custom_props=False)

    def _glb(self, ob, path):
        _select([ob], ob)
        self._swap_normal(ob, gl=True)
        try:
            bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                                      export_yup=True, export_texcoords=True, export_normals=True, export_materials="EXPORT",
                                      export_image_format="JPEG", export_image_quality=90, export_tangents=False,
                                      export_extras=False, export_cameras=False, export_lights=False)
        except TypeError:   # newer exporter renamed options: fall back to the essentials
            bpy.ops.export_scene.gltf(filepath=path, export_format="GLB", use_selection=True, export_apply=True,
                                      export_yup=True)

    def _export(self, ob):
        d = self.dir
        self._swap_normal(ob, gl=False)
        self._fbx([ob] + self.ucx, os.path.join(d, self.sm + ".fbx"))
        lod = None
        if self.lod1:
            l1 = ob.copy(); l1.data = ob.data.copy()
            l1.name = l1.data.name = self.sm + "_LOD1"
            _link(l1)
            md = l1.modifiers.new("dec", "DECIMATE")
            md.decimate_type, md.ratio, md.use_collapse_triangulate = "COLLAPSE", 0.5, True
            dg = bpy.context.evaluated_depsgraph_get()
            me = bpy.data.meshes.new_from_object(l1.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
            l1.modifiers.clear(); l1.data = me; me.name = l1.name
            me.calc_loop_triangles()
            lod = len(me.loop_triangles)
            self._fbx([l1], os.path.join(d, self.sm + "_LOD1.fbx"))
            bpy.data.objects.remove(l1, do_unlink=True)
        self._glb(ob, os.path.join(d, self.sm + ".glb"))
        return lod

    def _variant(self, ob, vname, fn):
        v = ob.copy(); v.data = ob.data.copy()
        v.name = v.data.name = "SM_" + vname
        _link(v)
        res = fn(self, v)
        ucx = []
        specs = res if isinstance(res, list) else None
        if specs is not None:
            for i, pts in enumerate(specs):
                bm = _bm()
                for p in pts:
                    bm.verts.new(Vector(p) + self.shift)
                bmesh.ops.convex_hull(bm, input=bm.verts)
                me = bpy.data.meshes.new("UCX_SM_%s_%02d" % (vname, i)); bm.to_mesh(me); bm.free()
                ucx.append(_link(bpy.data.objects.new(me.name, me)))
        else:
            for i, u in enumerate(self.ucx):
                c = u.copy(); c.data = u.data.copy(); c.name = "UCX_SM_%s_%02d" % (vname, i); _link(c); ucx.append(c)
        v.data.update()
        self._swap_normal(v, gl=False)
        self._fbx([v] + ucx, os.path.join(self.dir, "SM_%s.fbx" % vname))
        lod = None
        self._glb(v, os.path.join(self.dir, "SM_%s.glb" % vname))
        st = self._stats(v)
        if not NORENDER:
            for o in [ob] + self.ucx:
                o.hide_render = True
            self._render([v], os.path.join(self.dir, "SM_%s_preview.jpg" % vname))
            ob.hide_render = False
        rep = dict(self.report)
        rep.update(name="SM_" + vname, variant_of=self.sm, tris=st["tris"], dims=st["dims"], ucx=len(ucx),
                   files=sorted(f for f in os.listdir(self.dir) if not f.startswith("_")))
        with open(os.path.join(self.dir, "SM_%s.report.json" % vname), "w") as f:
            json.dump(rep, f, indent=1)
        for c in ucx:
            bpy.data.objects.remove(c, do_unlink=True)
        bpy.data.objects.remove(v, do_unlink=True)

    def _skin_copies(self, ob):
        objs = [ob]
        span = self.target[1] * 1.25 + 0.2
        for k, (tag, imgs) in enumerate(self.skin_imgs[1:], 1):
            c = ob.copy(); c.data = ob.data.copy(); _link(c)
            c.location.y = -span * k
            mats = []
            for m in ob.data.materials:
                nm = self._pbr_material(m.name + "__" + tag, imgs, glow=(m.name == "Glow"))
                mats.append(nm)
            c.data.materials.clear()
            for m in mats:
                c.data.materials.append(m)
            objs.append(c)
        return objs

    # ------------------------------------------------------------ preview render
    def _render(self, objs, path, draft=False):
        sc = bpy.context.scene
        for u in self.ucx:
            u.hide_render = True
        w = bpy.data.worlds.new("sky")
        sc.world = w
        w.use_nodes = True
        nt = w.node_tree
        bg = nt.nodes["Background"]
        sky = nt.nodes.new("ShaderNodeTexSky")
        for st in ("NISHITA", "SINGLE_SCATTERING", "MULTIPLE_SCATTERING", "HOSEK_WILKIE"):
            try:
                sky.sky_type = st
                break
            except TypeError:
                continue
        sky.sun_disc = False
        sky.sun_elevation = math.radians(38)
        sky.sun_rotation = math.radians(-60)
        sky.altitude = 900
        sky.air_density = 1.0
        sky.dust_density = 2.0
        nt.links.new(sky.outputs[0], bg.inputs[0])
        bg.inputs[1].default_value = 0.22
        sun = bpy.data.lights.new("sun", "SUN")
        sun.energy = 3.2
        sun.angle = math.radians(1.2)
        sun.color = (1.0, 0.95, 0.87)
        so = _link(bpy.data.objects.new("sun", sun))
        el, az = math.radians(38), math.radians(-60)
        dvec = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
        so.rotation_euler = dvec.to_track_quat("Z", "Y").to_euler()
        # ground
        lo = Vector((1e9, 1e9, 1e9)); hi = -lo
        for o in objs:
            for c in o.bound_box:
                p = o.matrix_world @ Vector(c)
                lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
        lift = 0.0
        if lo.z < -1e-4 or self.pivot == "center":
            lift = -lo.z
            for o in objs:
                o.location.z += lift
            lo.z += lift; hi.z += lift
        gm = bpy.data.materials.new("ground")
        gm.use_nodes = True
        g = MT.G(gm, dict(self.ctx, mask_image=None))
        n1 = g.noise(g.W, 0.6, 5, 0.6)
        n2 = g.noise(g.W, 9.0, 4, 0.6)
        gc = g.mixc(g.lin(g.add(g.mul(n1, 0.7), g.mul(n2, 0.3)), 0.35, 0.65), MT.rgb("#7d7468"), MT.rgb("#9a8f80"))
        b = g.node("ShaderNodeBsdfPrincipled")
        g._set(b.inputs["Base Color"], gc); b.inputs["Roughness"].default_value = 0.95
        o = g.node("ShaderNodeOutputMaterial")
        g.L.new(b.outputs[0], o.inputs["Surface"])
        gbm = box(400, 400, 0.02)
        me = bpy.data.meshes.new("ground"); gbm.to_mesh(me); gbm.free()
        ground = _link(bpy.data.objects.new("ground", me))
        ground.location.z = -0.0101
        me.materials.append(gm)
        # camera: front three-quarter
        ro = getattr(self, "render_opts", {})
        sc.render.resolution_x, sc.render.resolution_y = ro.get("res", (640, 480) if draft else (1280, 960))
        sc.render.resolution_percentage = 100
        cam = bpy.data.cameras.new("cam")
        cam.lens = 50; cam.sensor_width = 36; cam.clip_start = 0.01; cam.clip_end = 2000
        co = _link(bpy.data.objects.new("cam", cam))
        sc.camera = co
        tgt = (lo + hi) / 2
        az, el = math.radians(ro.get("az", -36)), math.radians(ro.get("el", 17))
        dv = Vector((math.cos(el) * math.cos(az), math.cos(el) * math.sin(az), math.sin(el)))
        corners = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
        def fits(dist, margin=0.07):
            co.location = tgt + dv * dist
            co.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
            bpy.context.view_layer.update()
            for c in corners:
                p = world_to_camera_view(sc, co, c)
                if p.z <= 0 or not (margin <= p.x <= 1 - margin and margin <= p.y <= 1 - margin):
                    return False
            return True
        a, b_ = 0.05, 5000.0
        for _ in range(60):
            mid = (a + b_) / 2
            if fits(mid):
                b_ = mid
            else:
                a = mid
        fits(b_)
        sc.cycles.samples = ro.get("samples", 16 if draft else 96)
        sc.cycles.use_adaptive_sampling = True
        sc.cycles.adaptive_threshold = 0.03 if draft else 0.012
        sc.cycles.use_denoising = False
        sc.cycles.max_bounces = 4
        sc.cycles.diffuse_bounces = 2
        sc.cycles.glossy_bounces = 2
        sc.cycles.transmission_bounces = 2
        sc.cycles.caustics_reflective = sc.cycles.caustics_refractive = False
        sc.cycles.blur_glossy = 1.0
        sc.cycles.sample_clamp_indirect = 3.0
        sc.cycles.filter_width = 1.6
        sc.view_settings.view_transform = "AgX"
        try:
            sc.view_settings.look = "AgX - Medium High Contrast"
        except TypeError:
            pass
        sc.view_settings.exposure = ro.get("exposure", -0.35)
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 92
        sc.render.filepath = path
        t = time.time()
        bpy.ops.render.render(write_still=True)
        print("[kit] render %s %.1fs" % (os.path.basename(path), time.time() - t))
        self.log.append(("render", os.path.basename(path), round(time.time() - t, 1)))
        for x in (ground, co, so):
            bpy.data.objects.remove(x, do_unlink=True)
        for o in objs:
            o.location.z -= lift

    # ------------------------------------------------------------ report
    def _report(self, ob, st, draft=False, lod=None):
        D, W, H = self.target
        dims = st["dims"]
        dev = [round(dims[i] / t - 1.0, 3) if t else None for i, t in enumerate((D, W, H))]
        rep = dict(name=self.sm, draft=draft, tris=st["tris"], budget=self.budget, within_budget=st["tris"] <= self.budget,
                   lod1_tris=lod, target_xyz=[D, W, H], dims_xyz=dims, dims_dev=dev, pivot=self.pivot,
                   pivot_shift=[round(x, 4) for x in self.shift], bbox_min=st["bbox_min"], bbox_max=st["bbox_max"],
                   texture=self.tex, px_per_m=st["px_per_m"], uv_coverage=st["uv_coverage"], area_m2=st["area_m2"],
                   ucx=len(self.ucx), slots=getattr(self, "slots", sorted({s.slot for _, s in self.mats.values()})),
                   materials={n: dict(recipe=s.recipe, slot=s.slot) for n, (_, s) in self.mats.items()},
                   ctx={k: round(v, 4) for k, v in self.ctx.items()}, note=self.note,
                   seconds=round(time.time() - self.t0, 1), log=self.log)
        if not draft:
            rep["files"] = sorted(f for f in os.listdir(self.dir) if not f.startswith("_"))
        self.report = rep
        fn = "_draft.report.json" if draft else self.sm + ".report.json"
        with open(os.path.join(self.dir, fn), "w") as f:
            json.dump(rep, f, indent=1)
        flag = "OK " if rep["within_budget"] else "OVER"
        print("[kit] %s %s tris %d/%d  dims %s (target %s) dev %s  %.0fs" % (flag, self.sm, st["tris"], self.budget, dims,
                                                                               [D, W, H], dev, rep["seconds"]))
