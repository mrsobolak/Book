"""
KESTREL-7 - realistic modern assault rifle, built procedurally in Blender.

    blender -b --python build_rifle.py -- <output_dir> [--nobake]

Modelling axes: +X = muzzle, +Y = right side, +Z = up, bore axis on z = 0.
Units are metres at real scale (overall length ~0.85 m).

Pipeline
  1. every part is a profile prism or a lathe, cut with exact booleans
  2. angle-limited bevels with hardened normals (hard-surface look)
  3. parts are merged per group (base gun + one object per attachment)
  4. per-vertex data is baked into COLOR_0:
        R = ambient occlusion (Cycles bake)
        G = convexity  (edge-wear mask)
        B = concavity  (grime mask)
  5. GLB export; the web viewer does the PBR materials, camo and wear.
"""
import bpy, bmesh, math, sys, os
import numpy as np
from mathutils import Matrix, Vector

ARGS = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in ARGS if not a.startswith("--")), os.path.dirname(os.path.abspath(__file__)))
BAKE = "--nobake" not in ARGS
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
scene = bpy.context.scene
COL = scene.collection

# ------------------------------------------------------------------ materials
def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def make_mat(name, hexcol, metallic, rough):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    r, g, bl = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    b.inputs["Base Color"].default_value = (_lin(r), _lin(g), _lin(bl), 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m

MAT = {n: make_mat(n, *v) for n, v in {
    "Paint":       ("#2c2e31", 0.0, 0.55),   # cerakote on aluminium (takes camo)
    "Polymer":     ("#222325", 0.0, 0.60),   # glass-filled nylon (takes camo)
    "Grip":        ("#1e1f21", 0.0, 0.75),   # stippled polymer
    "Steel":       ("#3b3d40", 1.0, 0.45),   # phosphate / nitride steel
    "BrightSteel": ("#a0a4a8", 1.0, 0.25),   # nickel-boron bolt carrier
    "Rubber":      ("#161616", 0.0, 0.90),
    "Optic":       ("#1a1b1d", 0.2, 0.40),   # hard anodised optic bodies
    "Suppressor":  ("#2b2927", 0.1, 0.60),   # high-temp coating
    "Glass":       ("#a8c4d4", 0.0, 0.05),
    "Reticle":     ("#ff2a1a", 0.0, 0.50),
    "Marking":     ("#cfcec6", 0.0, 0.60),   # laser-etched, paint-filled text
}.items()}

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

# ------------------------------------------------------------------ bmesh builders (return new verts)
def _P(plane, u, v, w):
    if plane == "XZ": return (u, w, v)
    if plane == "YZ": return (w, u, v)
    return (u, v, w)  # XY

def bm_prism(bm, pts, offset, thick, plane="XZ", taper=None):
    """Closed 2D profile extruded along the plane normal, centred on `offset`."""
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
    """Hollow prism: outer & inner loops must have the same point count."""
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

def bm_lathe(bm, prof, seg=48, axis="X", c=(0, 0, 0), closed=False):
    """Revolve (a, r) around an axis through c; a is measured along the axis from c."""
    def pt(a, u, v):
        if axis == "X": return (c[0] + a, c[1] + u, c[2] + v)
        if axis == "Y": return (c[0] + u, c[1] + a, c[2] + v)
        return (c[0] + u, c[1] + v, c[2] + a)
    rings, new = [], []
    for a, r in prof:
        if r < 1e-9:
            ring = [bm.verts.new(pt(a, 0, 0))]
        else:
            ring = [bm.verts.new(pt(a, r * math.cos(2 * math.pi * i / seg), r * math.sin(2 * math.pi * i / seg)))
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

def bm_box(bm, x0, x1, y0, y1, z0, z1):
    return bm_prism(bm, [(x0, z0), (x1, z0), (x1, z1), (x0, z1)], (y0 + y1) / 2, y1 - y0, "XZ")

def mirror_y(bm):
    for v in bm.verts:
        v.co.y = -v.co.y

# ------------------------------------------------------------------ objects
def mk(name, bm, mat, group="base", bev=None, segs=2, bang=30, smooth=35):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    me.materials.append(MAT[mat])
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    me.use_auto_smooth = True
    me.auto_smooth_angle = math.radians(smooth)
    ob["group"] = group
    if bev:
        ob["bev"], ob["segs"], ob["bang"] = bev, segs, bang
    return ob

def cutter(bm):
    ob = mk("cutter", bm, "Steel", group="__cutter")
    ob.hide_render = True
    return ob

def cut(ob, bm):
    md = ob.modifiers.new("cut", "BOOLEAN")
    md.operation, md.solver, md.object = "DIFFERENCE", "EXACT", cutter(bm)

def prism(name, pts, offset, thick, mat, plane="XZ", group="base", taper=None, **kw):
    bm = bmesh.new(); bm_prism(bm, pts, offset, thick, plane, taper)
    return mk(name, bm, mat, group, **kw)

def lathe(name, prof, mat, group="base", seg=48, axis="X", c=(0, 0, 0), closed=False, **kw):
    bm = bmesh.new(); bm_lathe(bm, prof, seg, axis, c, closed)
    return mk(name, bm, mat, group, **kw)

def text(body, size, x, z, y_face, name, group="base"):
    cu = bpy.data.curves.new(name, "FONT")
    cu.body, cu.size, cu.extrude, cu.align_x = body, size, 0.00012, "CENTER"
    cu.materials.append(MAT["Marking"])
    ob = bpy.data.objects.new(name, cu)
    COL.objects.link(ob)
    if y_face < 0:
        ob.rotation_euler = (math.radians(90), 0, 0)                   # reads left-to-right from the left side
    else:
        ob.rotation_euler = (math.radians(90), 0, math.radians(180))   # ...and from the right side
    ob.location = (x, y_face, z)
    ob["group"] = group
    return ob

# ================================================================== PICATINNY RAIL
def rail(name, x0, x1, zb, mat="Paint", group="base"):
    zt = 0.0285
    sec = [(-0.0078, zt), (0.0078, zt), (0.0106, zt - 0.0028), (0.0106, zt - 0.0038), (0.0080, zt - 0.0062),
           (0.0080, zb), (-0.0080, zb), (-0.0080, zt - 0.0062), (-0.0106, zt - 0.0038), (-0.0106, zt - 0.0028)]
    ob = prism(name, sec, (x0 + x1) / 2, x1 - x0, mat, plane="YZ", group=group, bev=0.0004, segs=1)
    bm = bmesh.new()
    x = x0 + 0.0055
    while x + 0.0026 < x1 - 0.002:
        bm_box(bm, x - 0.00262, x + 0.00262, -0.013, 0.013, zt - 0.0030, zt + 0.002)
        x += 0.01001                                                       # MIL-STD-1913 pitch
    cut(ob, bm)
    return ob

# ================================================================== UPPER RECEIVER
upper = prism("Upper", rrect(-0.145, -0.012, 0.100, 0.019, 0.003), 0.0, 0.030, "Paint", bev=0.0008, segs=2)
bm = bmesh.new()
bm_prism(bm, rrect(-0.060, -0.005, 0.012, 0.012, 0.0022), 0.016, 0.022)            # ejection port pocket
bm_prism(bm, rrect(-0.122, 0.000, -0.090, 0.0125, 0.003), -0.0160, 0.004)           # billet pockets
bm_prism(bm, rrect(0.030, -0.006, 0.088, 0.0125, 0.003), -0.0160, 0.004)
bm_prism(bm, rrect(0.030, -0.006, 0.088, 0.0125, 0.003), 0.0160, 0.004)
cut(upper, bm)
rail("UpperRail", -0.140, 0.098, 0.017)

# brass deflector, forward assist, charging handle
prism("Deflector", rrect(-0.080, 0.000, -0.064, 0.014, 0.004), 0.016, 0.012, "Paint", bev=0.0025, segs=3)
fa = lathe("ForwardAssist", [(0, 0), (0, 0.0075), (0.017, 0.0075), (0.0185, 0.0064), (0.026, 0.0064),
                             (0.027, 0.0056), (0.027, 0)], "Paint", seg=32, bev=0.0005, segs=2)
fa.rotation_euler = (0, 0, math.radians(155)); fa.location = (-0.098, 0.010, 0.004)
ch = path([("M", -0.140, -0.004), ("L", -0.150, -0.004), ("L", -0.150, -0.017), ("Q", (-0.150, -0.022), (-0.154, -0.022), 3),
           ("L", -0.159, -0.020), ("L", -0.159, 0.020), ("L", -0.154, 0.022), ("Q", (-0.150, 0.022), (-0.150, 0.017), 3),
           ("L", -0.150, 0.004), ("L", -0.140, 0.004)])
prism("ChargingHandle", ch, 0.0195, 0.006, "Optic", plane="XY", bev=0.0006, segs=2)

# bolt carrier group seen through the open port, dust cover hanging open
lathe("BoltCarrier", [(-0.080, 0), (-0.080, 0.0092), (-0.030, 0.0092), (-0.029, 0.0082), (-0.024, 0.0082),
                      (-0.023, 0.0092), (0.002, 0.0092), (0.002, 0)], "BrightSteel", seg=40, c=(0, 0, 0.003),
      bev=0.0004, segs=2)
lathe("Bolt", [(0.002, 0), (0.002, 0.0066), (0.012, 0.0066), (0.013, 0.0058), (0.013, 0)], "Steel", seg=32,
      c=(0, 0, 0.003), bev=0.0004, segs=1)
dc = path([("M", -0.062, -0.0065), ("L", 0.013, -0.0065), ("L", 0.013, -0.022), ("Q", (0.013, -0.025), (0.010, -0.025), 3),
           ("L", -0.018, -0.025), ("L", -0.020, -0.028), ("L", -0.028, -0.028), ("L", -0.030, -0.025),
           ("L", -0.059, -0.025), ("Q", (-0.062, -0.025), (-0.062, -0.022), 3)])
prism("DustCover", dc, 0.0163, 0.0012, "Steel", bev=0.0003, segs=1)
lathe("DustCoverRod", [(-0.066, 0), (-0.066, 0.0012), (0.016, 0.0012), (0.016, 0)], "Steel", seg=12, c=(0, 0.0156, -0.0064))

# ================================================================== LOWER RECEIVER
lower_pts = path([
    ("M", -0.135, -0.0123), ("L", 0.068, -0.0123), ("L", 0.068, -0.034), ("L", 0.064, -0.074),
    ("Q", (0.064, -0.082), (0.056, -0.082), 4), ("L", 0.008, -0.082), ("Q", (0.002, -0.082), (0.001, -0.076), 4),
    ("L", 0.000, -0.066), ("Q", (-0.002, -0.080), (-0.016, -0.080), 6), ("L", -0.048, -0.078),
    ("Q", (-0.060, -0.077), (-0.064, -0.066), 6), ("L", -0.070, -0.040), ("L", -0.110, -0.036),
    ("Q", (-0.128, -0.034), (-0.132, -0.026), 4),
])
lower = prism("Lower", lower_pts, 0.0, 0.026, "Paint", bev=0.0008, segs=2)
bm = bmesh.new()
bm_prism(bm, rrect(0.006, -0.0115, 0.060, 0.0115, 0.002), -0.056, 0.070, plane="XY")   # magwell
bm_prism(bm, rrect(-0.052, -0.071, -0.006, -0.038, 0.006), 0.0, 0.040)                  # trigger opening
bm_prism(bm, rrect(0.010, -0.074, 0.054, -0.040, 0.004), -0.0135, 0.002)                # flats for markings
bm_prism(bm, rrect(0.010, -0.074, 0.054, -0.040, 0.004), 0.0135, 0.002)
cut(lower, bm)

trigger = path([("M", -0.028, -0.037), ("L", -0.022, -0.037), ("Q", (-0.019, -0.050), (-0.021, -0.063), 6),
                ("Q", (-0.023, -0.067), (-0.026, -0.064), 3), ("L", -0.028, -0.052), ("Q", (-0.029, -0.043), (-0.028, -0.037), 3)])
prism("Trigger", trigger, 0.0, 0.0045, "Steel", bev=0.0005, segs=2)

# pins, selector, bolt catch, mag release (both sides where it applies)
bm = bmesh.new()
for x, z, r in [(0.056, -0.018, 0.0040), (-0.122, -0.018, 0.0040), (-0.028, -0.031, 0.0030), (-0.046, -0.029, 0.0030)]:
    for side in (1, -1):
        prof = [(0, 0), (0, r), (0.0006, r), (0.0009, r * 0.8), (0.0009, 0)]
        vs = bm_lathe(bm, prof, 24, "Y", (x, 0.0128, z))
        if side < 0:
            for v in vs: v.co.y = -v.co.y
mk("Pins", bm, "Steel", bev=0.0002, segs=1)
lathe("SelectorHub", [(0, 0), (0, 0.0058), (-0.0022, 0.0058), (-0.0028, 0.0048), (-0.0028, 0)], "Steel", seg=32,
      axis="Y", c=(-0.085, -0.0128, -0.024), bev=0.0003, segs=1)
prism("SelectorLever", path([("M", -0.086, -0.0265), ("L", -0.068, -0.0262), ("Q", (-0.064, -0.0262), (-0.064, -0.024), 3),
                              ("Q", (-0.064, -0.0215), (-0.068, -0.0215), 3), ("L", -0.086, -0.0215)]),
      -0.0156, 0.0016, "Steel", bev=0.0003, segs=1)
prism("BoltCatch", path([("M", -0.006, -0.034), ("L", 0.004, -0.034), ("Q", (0.008, -0.034), (0.008, -0.029), 3),
                          ("L", 0.007, -0.020), ("L", -0.004, -0.020), ("L", -0.006, -0.026)]),
      -0.0143, 0.003, "Steel", bev=0.0004, segs=2)
lathe("MagRelease", [(0, 0), (0, 0.0046), (0.0025, 0.0046), (0.0032, 0.0038), (0.0032, 0)], "Steel", seg=32,
      axis="Y", c=(0.003, 0.0128, -0.030), bev=0.0003, segs=1)
prism("MagReleaseFence", path([("M", -0.006, -0.038), ("L", 0.012, -0.038), ("Q", (0.014, -0.030), (0.012, -0.022), 4),
                                ("L", 0.009, -0.022), ("Q", (0.010, -0.030), (0.009, -0.035), 3), ("L", -0.003, -0.035),
                                ("Q", (-0.004, -0.030), (-0.003, -0.025), 3), ("L", -0.006, -0.025),
                                ("Q", (-0.008, -0.030), (-0.006, -0.038), 3)]),
      0.0138, 0.0025, "Paint", bev=0.0004, segs=2)

# markings (paint-filled laser engraving)
text("KESTREL-7", 0.0062, 0.032, -0.0525, -0.01245, "MarkName")
text("CAL 5.56x45 NATO", 0.0028, 0.032, -0.0615, -0.01245, "MarkCal")
text("KESTREL ARMS", 0.0036, 0.032, -0.0505, 0.01245, "MarkMaker")
text("SN  K7-004213", 0.0028, 0.032, -0.0595, 0.01245, "MarkSerial")
text("SAFE", 0.0024, -0.066, -0.0195, -0.01305, "MarkSafe")
text("FIRE", 0.0024, -0.100, -0.0205, -0.01305, "MarkFire")

# pistol grip (stippled polymer)
grip = path([
    ("M", -0.066, -0.034), ("L", -0.104, -0.034), ("Q", (-0.118, -0.034), (-0.118, -0.044), 4), ("L", -0.112, -0.050),
    ("L", -0.131, -0.122), ("Q", (-0.135, -0.140), (-0.118, -0.141), 6), ("L", -0.094, -0.139),
    ("Q", (-0.084, -0.138), (-0.086, -0.126), 4), ("Q", (-0.074, -0.108), (-0.080, -0.096), 6),
    ("Q", (-0.068, -0.080), (-0.070, -0.066), 6), ("Q", (-0.066, -0.050), (-0.066, -0.034), 4),
])
prism("Grip", grip, 0.0, 0.026, "Grip", taper=lambda x, z: 1.0 + 0.16 * smoothstep(-0.045, -0.125, z),
      bev=0.0022, segs=3)

# ================================================================== BUFFER TUBE + STOCK
TZ = -0.002
tube = lathe("BufferTube", [(-0.1345, 0), (-0.1345, 0.0145), (-0.338, 0.0145), (-0.342, 0.0125), (-0.342, 0)],
             "Paint", seg=48, c=(0, 0, TZ), bev=0.0006, segs=2)
bm = bmesh.new()
for x in (-0.172, -0.194):
    bm_lathe(bm, [(-0.024, 0), (-0.024, 0.0022), (-0.010, 0.0022), (-0.010, 0)], 16, "Z", (x, 0, 0))
cut(tube, bm)
nut = lathe("CastleNut", [(-0.1505, 0), (-0.1505, 0.0158), (-0.1500, 0.0164), (-0.1390, 0.0164), (-0.1385, 0.0158),
                          (-0.1385, 0)], "Steel", seg=48, c=(0, 0, TZ), bev=0.0003, segs=1)
bm = bmesh.new()
for k in range(4):
    vs = bm_box(bm, -0.1520, -0.1460, -0.0022, 0.0022, 0.0135, 0.020)
    bmesh.ops.rotate(bm, verts=vs, cent=(0, 0, TZ), matrix=Matrix.Rotation(math.radians(45 + 90 * k), 3, "X"))
cut(nut, bm)
prism("EndPlate", rrect(-0.0165, -0.0205, 0.0165, 0.0135, 0.006), -0.1365, 0.0030, "Steel", plane="YZ",
      bev=0.0004, segs=1)

stock = path([
    ("M", -0.212, 0.020), ("L", -0.300, 0.028), ("Q", (-0.360, 0.034), (-0.392, 0.030), 8), ("L", -0.398, 0.030),
    ("L", -0.402, -0.094), ("L", -0.370, -0.094), ("Q", (-0.300, -0.060), (-0.250, -0.026), 8),
    ("L", -0.212, -0.018), ("Q", (-0.206, 0.001), (-0.212, 0.020), 6),
])
stk = prism("Stock", stock, 0.0, 0.037, "Polymer", taper=lambda x, z: 1.0 - 0.22 * smoothstep(-0.02, -0.09, z),
            bev=0.0022, segs=3)
bm = bmesh.new()
bm_prism(bm, path([("M", -0.300, -0.034), ("L", -0.372, -0.034), ("Q", (-0.382, -0.034), (-0.382, -0.046), 4),
                   ("L", -0.382, -0.072), ("Q", (-0.382, -0.082), (-0.372, -0.078), 4), ("L", -0.312, -0.046),
                   ("Q", (-0.300, -0.040), (-0.300, -0.034), 4)]), 0.0, 0.06)          # skeleton cut-out
bm_prism(bm, rrect(-0.330, 0.004, -0.232, 0.016, 0.004), 0.0195, 0.004)                # side panels
bm_prism(bm, rrect(-0.330, 0.004, -0.232, 0.016, 0.004), -0.0195, 0.004)
cut(stk, bm)
pad = path([("M", -0.3965, 0.034), ("L", -0.411, 0.034), ("Q", (-0.4165, 0.034), (-0.4165, 0.028), 3),
            ("L", -0.4205, -0.092), ("Q", (-0.4205, -0.098), (-0.414, -0.098), 3), ("L", -0.4005, -0.098)])
prism("ButtPad", pad, 0.0, 0.040, "Rubber", bev=0.003, segs=3)
prism("StockLever", rrect(-0.246, -0.025, -0.214, -0.019, 0.002), 0.0, 0.012, "Polymer", bev=0.0012, segs=2)
lathe("StockQD", [(0, 0.0034), (0, 0.0064), (-0.0018, 0.0064), (-0.0018, 0.0034)], "Steel", seg=32, axis="Y",
      c=(-0.228, -0.0172, 0.001), closed=True, bev=0.0003, segs=1)

# ================================================================== HANDGUARD + BARREL
HG0, HG1 = 0.100, 0.400
bm = bmesh.new()
bm_tube(bm, superellipse(0.0235, 0.024, 0, -0.004), superellipse(0.0195, 0.0200, 0, -0.004), HG0, HG1)
hg = mk("Handguard", bm, "Paint", bev=0.0010, segs=2)
bm = bmesh.new()
for xc in (0.145, 0.195, 0.245, 0.295, 0.345):
    bm_prism(bm, rrect(xc - 0.016, -0.0077, xc + 0.016, -0.0003, 0.0036), 0.0, 0.07)            # side M-LOK
    bm_prism(bm, rrect(xc - 0.016, -0.0037, xc + 0.016, 0.0037, 0.0036), -0.026, 0.02, plane="XY")  # bottom
for xc in (0.170, 0.220, 0.270, 0.320, 0.370):
    vs = bm_prism(bm, rrect(xc - 0.009, -0.0024, xc + 0.009, 0.0024, 0.0024), 0.0, 0.07)        # 45° vents
    bmesh.ops.rotate(bm, verts=vs, cent=(0, 0, -0.004), matrix=Matrix.Rotation(math.radians(45), 3, "X"))
    vs = bm_prism(bm, rrect(xc - 0.009, -0.0024, xc + 0.009, 0.0024, 0.0024), 0.0, 0.07)
    bmesh.ops.rotate(bm, verts=vs, cent=(0, 0, -0.004), matrix=Matrix.Rotation(math.radians(-45), 3, "X"))
cut(hg, bm)
rail("HandguardRail", 0.104, 0.398, 0.0165)
bm = bmesh.new()
for x in (0.112, 0.128):
    for side in (1, -1):
        vs = bm_lathe(bm, [(0, 0), (0, 0.0033), (0.0011, 0.0033), (0.0015, 0.0027), (0.0015, 0)], 24, "Y",
                      (x, 0.0229, -0.013))
        if side < 0:
            for v in vs: v.co.y = -v.co.y
screws = mk("Screws", bm, "Steel", bev=0.0002, segs=1)
bm = bmesh.new()
for x in (0.112, 0.128):
    for side in (1, -1):
        vs = bm_prism(bm, circle(x, -0.013, 0.0015, 6), side * 0.0250, 0.0030)
cut(screws, bm)

lathe("Barrel", [(0.090, 0), (0.090, 0.0095), (0.434, 0.0095), (0.434, 0.0075), (0.445, 0.0075), (0.445, 0.0028),
                 (0.420, 0.0028), (0.420, 0)], "Steel", seg=40, bev=0.0004, segs=1)

# flip-up sight bases (always on) + folded flaps (shown when an optic is mounted)
prism("RearBUISBase", path([("M", -0.138, 0.0245), ("L", -0.112, 0.0245), ("L", -0.112, 0.033),
                             ("Q", (-0.112, 0.036), (-0.115, 0.036), 3), ("L", -0.135, 0.036),
                             ("Q", (-0.138, 0.036), (-0.138, 0.033), 3)]), 0.0, 0.025, "Optic", bev=0.0008, segs=2)
prism("FrontBUISBase", path([("M", 0.370, 0.0245), ("L", 0.392, 0.0245), ("L", 0.392, 0.033),
                              ("Q", (0.392, 0.036), (0.389, 0.036), 3), ("L", 0.373, 0.036),
                              ("Q", (0.370, 0.036), (0.370, 0.033), 3)]), 0.0, 0.025, "Optic", bev=0.0008, segs=2)
prism("RearFlapFolded", rrect(-0.135, 0.036, -0.108, 0.0395, 0.0015), 0.0, 0.019, "Optic", group="buis_folded",
      bev=0.0005, segs=2)
prism("FrontFlapFolded", rrect(0.366, 0.036, 0.390, 0.0395, 0.0015), 0.0, 0.019, "Optic", group="buis_folded",
      bev=0.0005, segs=2)

# ================================================================== ATTACHMENTS
# --- muzzle: tri-port compensator ---------------------------------------
comp = lathe("Compensator", [(0.436, 0), (0.436, 0.0105), (0.440, 0.0118), (0.486, 0.0118), (0.492, 0.0100),
                             (0.492, 0.0048), (0.488, 0.0040), (0.440, 0.0040), (0.440, 0)],
             "Steel", group="att_muzzle_comp", seg=48, bev=0.0005, segs=2)
bm = bmesh.new()
bm_box(bm, 0.435, 0.446, 0.0096, 0.02, -0.02, 0.02); bm_box(bm, 0.435, 0.446, -0.02, -0.0096, -0.02, 0.02)
for x in (0.452, 0.464, 0.476):
    bm_prism(bm, rrect(x, -0.0065, x + 0.0075, 0.0065, 0.0026), 0.0, 0.04)
for x in (0.4575, 0.4705):
    bm_prism(bm, circle(x, 0.0, 0.0022, 20), 0.013, 0.014, plane="XY")
cut(comp, bm)

# --- muzzle: suppressor ---------------------------------------------------
sp = [(0.430, 0), (0.430, 0.0115), (0.433, 0.0135)]
x = 0.435
while x < 0.466:
    sp += [(x, 0.0135), (x + 0.001, 0.0146), (x + 0.0028, 0.0146), (x + 0.0038, 0.0135)]
    x += 0.0042
sp += [(0.468, 0.0135), (0.470, 0.0180), (0.474, 0.0195)]
for g in (0.490, 0.500):
    sp += [(g, 0.0195), (g + 0.0008, 0.0186), (g + 0.0022, 0.0186), (g + 0.003, 0.0195)]
sp += [(0.628, 0.0195), (0.634, 0.0176), (0.636, 0.0122), (0.636, 0.0050), (0.632, 0.0045), (0.600, 0.0045), (0.600, 0)]
lathe("Suppressor", sp, "Suppressor", group="att_muzzle_suppressor", seg=64, bev=0.0004, segs=2)

# --- optic: flip-up irons standing ------------------------------------------
rear = prism("RearAperture", path([("M", -0.0105, 0.035), ("L", 0.0105, 0.035), ("L", 0.0105, 0.061),
                                    ("Q", (0.0105, 0.064), (0.0075, 0.064), 3), ("L", 0.0055, 0.064),
                                    ("L", 0.0045, 0.0605), ("L", -0.0045, 0.0605), ("L", -0.0055, 0.064),
                                    ("L", -0.0075, 0.064), ("Q", (-0.0105, 0.064), (-0.0105, 0.061), 3)]),
             -0.122, 0.004, "Optic", plane="YZ", group="att_optic_irons", bev=0.0005, segs=2)
bm = bmesh.new(); bm_lathe(bm, [(-0.03, 0), (-0.03, 0.0019), (0.03, 0.0019), (0.03, 0)], 20, "X", (-0.122, 0, 0.0535))
cut(rear, bm)
prism("FrontPost", path([("M", -0.009, 0.035), ("L", 0.009, 0.035), ("L", 0.009, 0.062), ("Q", (0.009, 0.065), (0.006, 0.065), 3),
                         ("L", 0.005, 0.065), ("L", 0.004, 0.050), ("L", 0.0012, 0.048), ("L", 0.0012, 0.0555),
                         ("L", -0.0012, 0.0555), ("L", -0.0012, 0.048), ("L", -0.004, 0.050), ("L", -0.005, 0.065),
                         ("L", -0.006, 0.065), ("Q", (-0.009, 0.065), (-0.009, 0.062), 3)]),
      0.382, 0.004, "Optic", plane="YZ", group="att_optic_irons", bev=0.0005, segs=2)

# --- optic: micro red dot ---------------------------------------------------
G = "att_optic_reddot"
OZ = 0.0535
prism("RDMount", path([("M", -0.0125, 0.0245), ("L", 0.0125, 0.0245), ("L", 0.0125, 0.034), ("L", 0.007, 0.041),
                       ("L", -0.007, 0.041), ("L", -0.0125, 0.034)]), -0.025, 0.050, "Optic", plane="YZ", group=G,
      bev=0.0008, segs=2)
prism("RDRiser", rrect(-0.046, 0.036, -0.010, 0.046, 0.002), 0.0, 0.016, "Optic", group=G, bev=0.0008, segs=2)
lathe("RDTube", [(-0.064, 0.0118), (-0.064, 0.0166), (-0.057, 0.0166), (-0.055, 0.0150), (0.000, 0.0150),
                 (0.002, 0.0166), (0.008, 0.0166), (0.008, 0.0118)], "Optic", group=G, seg=56,
      c=(0, 0, OZ), closed=True, bev=0.0005, segs=2)
lathe("RDTurretTop", [(0, 0), (0, 0.0068), (0.0070, 0.0068), (0.0080, 0.0058), (0.0080, 0)], "Optic", group=G,
      seg=40, axis="Z", c=(-0.028, 0, OZ + 0.0140), bev=0.0004, segs=2)
lathe("RDTurretSide", [(0, 0), (0, 0.0068), (0.0070, 0.0068), (0.0080, 0.0058), (0.0080, 0)], "Optic", group=G,
      seg=40, axis="Y", c=(-0.028, 0.0140, OZ), bev=0.0004, segs=2)
bm = bmesh.new()
for x in (-0.058, 0.003):
    bm_lathe(bm, [(x, 0), (x, 0.0119), (x + 0.001, 0.0119), (x + 0.001, 0)], 48, "X", (0, 0, OZ))
mk("RDLenses", bm, "Glass", group=G)
lathe("RDDot", [(-0.0548 + 0.0007 * math.cos(math.radians(a)), 0.0007 * math.sin(math.radians(a))) for a in range(180, -1, -30)],
      "Reticle", group=G, seg=12, c=(0, 0, OZ))
prism("RDKnob", rrect(-0.032, 0.026, -0.018, 0.036, 0.004), 0.0145, 0.006, "Steel", group=G, bev=0.0008, segs=2)

# --- optic: holographic -------------------------------------------------------
G = "att_optic_holo"
prism("HoloBase", path([("M", -0.090, 0.0245), ("L", 0.012, 0.0245), ("L", 0.012, 0.036), ("L", -0.090, 0.036)]),
      0.0, 0.030, "Optic", group=G, bev=0.0010, segs=2)
prism("HoloBody", rrect(-0.090, 0.034, -0.038, 0.054, 0.005), 0.0, 0.030, "Optic", group=G, bev=0.0012, segs=2)
hood = prism("HoloHood", rrect(-0.0170, 0.034, 0.0170, 0.077, 0.006), -0.013, 0.050, "Optic", plane="YZ", group=G,
             bev=0.0010, segs=2)
bm = bmesh.new(); bm_prism(bm, rrect(-0.0135, 0.0395, 0.0135, 0.0725, 0.004), -0.013, 0.07, plane="YZ")
cut(hood, bm)
bm = bmesh.new()
for x in (-0.034, 0.008):
    bm_prism(bm, rrect(-0.0137, 0.0393, 0.0137, 0.0727, 0.004), x, 0.0012, plane="YZ")
mk("HoloGlass", bm, "Glass", group=G)
bm = bmesh.new()
bm_lathe(bm, [(-0.0132, 0.0053), (-0.0132, 0.0061), (-0.0130, 0.0061), (-0.0130, 0.0053)], 48, "X", (0, 0, 0.056), closed=True)
bm_lathe(bm, [(-0.0132, 0), (-0.0132, 0.0007), (-0.0130, 0.0007), (-0.0130, 0)], 12, "X", (0, 0, 0.056))
mk("HoloReticle", bm, "Reticle", group=G)
bm = bmesh.new()
for y in (-0.0065, 0.0065):
    bm_prism(bm, rrect(y - 0.0045, 0.040, y + 0.0045, 0.047, 0.0015), -0.0905, 0.002, plane="YZ")
mk("HoloButtons", bm, "Rubber", group=G, bev=0.0004, segs=1)
lathe("HoloKnob", [(0, 0), (0, 0.0060), (0.0060, 0.0060), (0.0070, 0.0050), (0.0070, 0)], "Steel", group=G, seg=32,
      axis="Y", c=(-0.020, 0.0150, 0.030), bev=0.0004, segs=1)

# --- underbarrel: vertical grip ---------------------------------------------
G = "att_under_vgrip"
prism("VGripMount", rrect(0.278, -0.036, 0.322, -0.0255, 0.003), 0.0, 0.020, "Polymer", group=G, bev=0.0012, segs=2)
vg = [(-0.121, 0), (-0.121, 0.0118), (-0.119, 0.0137), (-0.113, 0.0142)]
z = -0.106
while z < -0.058:
    vg += [(z, 0.0140), (z + 0.0015, 0.0133), (z + 0.0045, 0.0133), (z + 0.006, 0.0138)]
    z += 0.0075
vg += [(-0.050, 0.0128), (-0.040, 0.0131), (-0.037, 0.0124), (-0.034, 0.0105), (-0.034, 0)]
lathe("VGrip", vg, "Polymer", group=G, seg=48, axis="Z", c=(0.300, 0, 0), bev=0.0005, segs=2)

# --- underbarrel: angled grip ---------------------------------------------
prism("AngledGrip", path([("M", 0.215, -0.0255), ("L", 0.320, -0.0255), ("Q", (0.327, -0.0255), (0.325, -0.034), 4),
                          ("L", 0.317, -0.058), ("Q", (0.313, -0.067), (0.303, -0.065), 6), ("L", 0.230, -0.041),
                          ("Q", (0.215, -0.037), (0.215, -0.030), 4)]),
      0.0, 0.026, "Polymer", group="att_under_agrip", taper=lambda x, z: 1.0 - 0.18 * smoothstep(-0.03, -0.06, z),
      bev=0.0025, segs=3)

# --- magazines (curved polymer) ---------------------------------------------
MC = (0.35, -0.04)
RF, RR = math.dist(MC, (0.059, -0.015)), math.dist(MC, (0.007, -0.015))
def arc_pts(r, a0, a1, n):
    return [(MC[0] + r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
             MC[1] + r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
def magazine(group, a1):
    a0 = 175.4
    n = int((a1 - a0) * 1.2)
    body = arc_pts(RF, a0, a1, n) + arc_pts(RR, a1, a0, n)
    prism("MagBody", body, 0.0, 0.0225, "Polymer", group=group, bev=0.0012, segs=2)
    plate = arc_pts(RF - 0.0026, a1 - 3.2, a1 + 0.9, 6) + arc_pts(RR + 0.0026, a1 + 0.9, a1 - 3.2, 6)
    prism("MagFloor", plate, 0.0, 0.0262, "Polymer", group=group, bev=0.0015, segs=2)
    bm = bmesh.new()
    for k in range(4):
        a = a1 - 6.5 - 2.4 * k
        rib = arc_pts(RF + 0.007, a - 0.35, a + 0.35, 1) + arc_pts(RR - 0.007, a + 0.35, a - 0.35, 1)
        for side in (1, -1):
            bm_prism(bm, rib, side * 0.0118, 0.0016)
    mk("MagRibs", bm, "Polymer", group=group, bev=0.0004, segs=1)
    # raised grip panel below the magwell (both sides)
    bm = bmesh.new()
    win = arc_pts(RF + 0.014, 188.0, 196.0, 8) + arc_pts(RR - 0.014, 196.0, 188.0, 8)
    for side in (1, -1):
        bm_prism(bm, win, side * 0.0117, 0.0012)
    mk("MagPanel", bm, "Polymer", group=group, bev=0.0003, segs=1)
magazine("att_mag_30", 208.0)
magazine("att_mag_40", 220.0)

# ================================================================== FINALISE
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

# ---- per-vertex convexity / concavity -------------------------------------
def curvature(me):
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

# ---- AO bake ------------------------------------------------------------------
ao = {}
if BAKE:
    scene.render.engine = "CYCLES"
    scene.cycles.device = "CPU"
    scene.cycles.samples = 64
    scene.world = bpy.data.worlds.new("W")
    scene.world.light_settings.distance = 0.035
    scene.render.bake.target = "VERTEX_COLORS"
    for g, ob in merged.items():
        # occluders: the gun itself (+ the standard magazine) and the part being baked
        vis = {g, "base", "att_mag_30"} if g in ("base", "buis_folded") else {g, "base"}
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
        print(f"baked AO {g}: verts={len(ob.data.vertices)} mean={ao[g].mean():.3f}")
    for o in merged.values():
        o.hide_render = False

for g, ob in merged.items():
    me = ob.data
    c = curvature(me)
    n = len(me.vertices)
    data = np.ones((n, 4), dtype=np.float32)
    data[:, 0] = ao.get(g, np.ones(n))
    data[:, 1] = np.clip((c - 0.05) / 0.22, 0, 1)
    data[:, 2] = np.clip((-c - 0.05) / 0.22, 0, 1)
    attr = me.color_attributes.new("data", "FLOAT_COLOR", "POINT")
    attr.data.foreach_set("color", data.ravel())
    me.color_attributes.active_color = attr
    me.color_attributes.render_color_index = me.color_attributes.find("data")

# ------------------------------------------------------------------ export
scene.render.engine = "BLENDER_EEVEE"
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "kestrel7.blend"))
bpy.ops.object.select_all(action="SELECT")
bpy.ops.export_scene.gltf(filepath=os.path.join(OUT, "kestrel7.glb"), export_format="GLB", export_apply=True,
                          export_yup=True, export_normals=True, export_colors=True, export_texcoords=False,
                          export_materials="EXPORT")
tris = 0
for ob in merged.values():
    ob.data.calc_loop_triangles(); tris += len(ob.data.loop_triangles)
print(f"EXPORTED groups={sorted(merged)} tris={tris}")
