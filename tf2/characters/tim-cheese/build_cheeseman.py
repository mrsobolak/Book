"""
TIM CHEESE, the Cheeseman: a TF2-style character with a Swiss-cheese head and googly eyes.

    blender -b --python build_cheeseman.py -- [out_dir] [--nobake]

Body forms are metaballs (smooth, chunky TF2 volumes); the head, eyes, gear and grater are
hard-surface parts. Reuses the toolkit in cod/armory/lib.py for prisms, lathes, booleans,
the AO bake and GLB export. Character faces -Y, +Z up, metres (about 1.95 m tall).
"""
import json, math, os, random, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, "/home/user/Book/cod/armory")
import bpy, bmesh
from mathutils import Vector, Quaternion
import lib
from lib import path, rrect, circle, bm_prism, bm_lathe, bm_tube, bm_place, mk, cut, prism, lathe, rod, smoothstep

args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in args if not a.startswith("--")), HERE)
BAKE = "--nobake" not in args

lib.reset()
COLORS = {  # name: (hex, metallic, roughness) - viewer re-shades these in TF2 style
    "Cheese": ("#f2c14e", 0.0, 0.55), "Rind": ("#e0902a", 0.0, 0.45), "Skin": ("#d99a74", 0.0, 0.6),
    "Team": ("#b8383b", 0.0, 0.7), "Pants": ("#5d5240", 0.0, 0.8), "Boots": ("#4a3222", 0.0, 0.6),
    "Glove": ("#2e2723", 0.0, 0.6), "Leather": ("#6b4428", 0.0, 0.55), "GooglyWhite": ("#f4f1ea", 0.0, 0.3),
    "Pupil": ("#111111", 0.0, 0.3), "Wax": ("#b8383b", 0.0, 0.35),
}
for n, (h, m, r) in COLORS.items():
    mat = bpy.data.materials.new(n)
    mat.use_nodes = True
    b = mat.node_tree.nodes["Principled BSDF"]
    rgb = [lib._lin(int(h[i:i + 2], 16)) for i in (1, 3, 5)]
    b.inputs["Base Color"].default_value = (*rgb, 1)
    b.inputs["Metallic"].default_value, b.inputs["Roughness"].default_value = m, r
    lib.MAT[n] = mat

K = 1 / 0.575   # metaball radius -> visible radius factor (stiffness 2, threshold 0.6)

# ================================================================== metaball body
BALLS = {}
def fam(name):
    if name not in BALLS:
        mb = bpy.data.metaballs.new(name)
        mb.resolution = mb.render_resolution = 0.014
        mb.threshold = 0.6
        ob = bpy.data.objects.new(name, mb)
        lib.COL.objects.link(ob)
        BALLS[name] = mb
    return BALLS[name]

def ball(f, co, r):
    el = fam(f).elements.new(type="BALL"); el.co, el.radius, el.stiffness = co, r * K, 2.0

def ellip(f, co, a, b, c):
    el = fam(f).elements.new(type="ELLIPSOID")
    el.co, el.radius, el.stiffness = co, K, 2.0
    el.size_x, el.size_y, el.size_z = a, b, c

def caps(f, p0, p1, r):
    p0, p1 = Vector(p0), Vector(p1)
    el = fam(f).elements.new(type="CAPSULE")
    el.co = (p0 + p1) / 2
    el.radius, el.stiffness = r * K, 2.0
    el.size_x = (p1 - p0).length / 2
    el.rotation = Vector((1, 0, 0)).rotation_difference((p1 - p0).normalized())

def lerp(a, b, t):
    return tuple(a[i] + (b[i] - a[i]) * t for i in range(3))

# key joints (character's left = +X)
SH_L, EL_L, WR_L = (0.40, 0.01, 1.43), (0.62, 0.10, 1.17), (0.41, 0.06, 0.99)    # hand on hip
SH_R, EL_R, WR_R = (-0.40, 0.01, 1.43), (-0.53, 0.02, 1.12), (-0.565, -0.03, 0.86)
HIP_L, KNEE_L, ANK_L = (0.16, 0.0, 0.86), (0.22, -0.03, 0.50), (0.245, 0.0, 0.14)
HIP_R, KNEE_R, ANK_R = (-0.16, 0.0, 0.86), (-0.22, -0.03, 0.50), (-0.245, 0.0, 0.14)

# shirt (team colour): big barrel chest, gut, traps, short sleeves
ellip("Team", (0, -0.02, 1.33), 0.34, 0.24, 0.21)
ellip("Team", (0, 0.0, 1.19), 0.32, 0.23, 0.24)
ellip("Team", (0, -0.05, 1.05), 0.28, 0.23, 0.16)
ellip("Team", (0, 0.0, 0.96), 0.25, 0.20, 0.07)
ellip("Team", (0, 0.03, 1.49), 0.22, 0.14, 0.07)
for sh, el in ((SH_L, EL_L), (SH_R, EL_R)):
    ball("Team", sh, 0.135)
    caps("Team", sh, lerp(sh, el, 0.45), 0.115)
# skin: neck, arms
caps("Skin", (0, 0.02, 1.48), (0, 0.02, 1.60), 0.092)
for sh, el, wr in ((SH_L, EL_L, WR_L), (SH_R, EL_R, WR_R)):
    caps("Skin", lerp(sh, el, 0.35), el, 0.100)
    ball("Skin", el, 0.090)
    caps("Skin", el, lerp(el, wr, 0.5), 0.098)
    caps("Skin", lerp(el, wr, 0.5), wr, 0.080)
# gloves: big fists
ellip("Glove", (0.385, 0.06, 0.935), 0.065, 0.085, 0.085)             # left fist on the hip
caps("Glove", (0.43, 0.00, 0.97), (0.43, 0.10, 0.96), 0.034)          # knuckles, pointing back
FIST_R = (-0.572, -0.04, 0.775)
ellip("Glove", FIST_R, 0.075, 0.08, 0.088)
caps("Glove", (-0.615, -0.108, 0.772), (-0.530, -0.108, 0.772), 0.036)  # knuckle ridge (faces forward)
caps("Glove", (-0.505, -0.050, 0.815), (-0.522, -0.100, 0.770), 0.027)  # thumb
# pants
ellip("Pants", (0, 0.0, 0.87), 0.27, 0.21, 0.12)
ellip("Pants", (0, 0.01, 0.78), 0.12, 0.13, 0.07)
for hip, kn, ank in ((HIP_L, KNEE_L, ANK_L), (HIP_R, KNEE_R, ANK_R)):
    caps("Pants", hip, kn, 0.125)
    ball("Pants", kn, 0.108)
    caps("Pants", kn, lerp(kn, ank, 0.7), 0.098)
# boots
for s, ank in ((1, ANK_L), (-1, ANK_R)):
    x = ank[0]
    caps("Boots", (x, 0.0, 0.30), (x + s * 0.005, 0.0, 0.11), 0.105)
    caps("Boots", (x + s * 0.005, 0.02, 0.075), (x + s * 0.015, -0.17, 0.062), 0.072)
    ellip("Boots", (x + s * 0.015, -0.175, 0.062), 0.078, 0.075, 0.058)

# convert metaball families to meshes, decimate a little
for name in list(BALLS):
    ob = bpy.data.objects[name]
    bpy.ops.object.select_all(action="DESELECT")
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    bpy.ops.object.convert(target="MESH")
    me_ob = bpy.context.view_layer.objects.active
    me_ob.name = f"Body{name}"
    md = me_ob.modifiers.new("dec", "DECIMATE"); md.ratio = 0.35
    sm = me_ob.modifiers.new("smooth", "SMOOTH"); sm.factor, sm.iterations = 0.5, 4
    bpy.ops.object.modifier_apply(modifier="dec")
    bpy.ops.object.modifier_apply(modifier="smooth")
    me_ob.data.materials.clear()
    me_ob.data.materials.append(lib.MAT[name])
    for p in me_ob.data.polygons:
        p.use_smooth = True
    me_ob["group"] = "base"
    me_ob["nodensify"] = True

# ================================================================== clothing details
def ring_along(name, p0, p1, t, r_in, r_out, width, mat):
    """Annulus around the segment p0->p1 at parameter t."""
    bm = bmesh.new()
    vs = bm_lathe(bm, [(0, r_in), (0, r_out), (width * 0.15, r_out + 0.006), (width * 0.85, r_out + 0.006),
                       (width, r_out), (width, r_in)], 40, "X", (0, 0, 0), closed=True)
    d = (Vector(p1) - Vector(p0)).normalized()
    c = Vector(lerp(p0, p1, t)) - d * width / 2
    bm_place(bm, vs, c, c + d)
    return mk(name, bm, mat, smooth=60)

ring_along("SleeveCuffL", SH_L, EL_L, 0.44, 0.095, 0.122, 0.045, "Team")
ring_along("SleeveCuffR", SH_R, EL_R, 0.44, 0.095, 0.122, 0.045, "Team")
ring_along("GloveCuffL", WR_L, EL_L, 0.10, 0.070, 0.090, 0.040, "Glove")
ring_along("GloveCuffR", WR_R, EL_R, 0.10, 0.070, 0.090, 0.040, "Glove")
ring_along("BootRimL", (0.245, 0, 0.26), (0.245, 0, 0.40), 0.0, 0.098, 0.116, 0.035, "Boots")
ring_along("BootRimR", (-0.245, 0, 0.26), (-0.245, 0, 0.40), 0.0, 0.098, 0.116, 0.035, "Boots")
lathe("Collar", [(0, 0.088), (0, 0.118), (0.020, 0.124), (0.040, 0.112), (0.040, 0.088)], "Team", seg=48, axis="Z",
      c=(0, 0.02, 1.515), closed=True, smooth=60)
for s in (1, -1):
    prism(f"Sole{s}", rrect(-0.085, -0.265, 0.085, 0.085, 0.07, n=6), 0.018, 0.036, "Pants", plane="XY",
          bev=0.008, segs=3).data.materials[0] = lib.MAT["Rubber"]
    bpy.data.objects[f"Sole{s}"].location.x = s * 0.255

# belt + cheese-wedge buckle
bm = bmesh.new()
bm_tube(bm, lib.superellipse(0.300, 0.232, 0, 0.0, e=2.4, n=64), lib.superellipse(0.270, 0.205, 0, 0.0, e=2.4, n=64),
        0.905, 0.968, plane="XY")
mk("Belt", bm, "Leather", bev=0.006, segs=2)
bk = prism("Buckle", path([("M", -0.050, 0.908), ("L", 0.050, 0.908), ("L", 0.050, 0.966), ("L", -0.050, 0.922)]),
           -0.239, 0.014, "Brass", bev=0.004, segs=2)
bm = bmesh.new()
for x, z, r in ((0.028, 0.936, 0.008), (0.005, 0.921, 0.006)):
    bm_lathe(bm, [(-0.02, 0), (-0.02, r), (0.02, r), (0.02, 0)], 20, "Y", (x, -0.246, z))
cut(bk, bm)

# ================================================================== BRIE-DOLIER
C0 = Vector((0, -0.01, 1.25))
TILT = math.radians(-38)
def ring_pt(a, rx=0.435, ry=0.305):
    p = Vector((rx * math.cos(a), ry * math.sin(a), 0))
    return Vector((p.x * math.cos(TILT) + p.z * math.sin(TILT), p.y, -p.x * math.sin(TILT) + p.z * math.cos(TILT))) + C0
PN = Vector((math.sin(TILT), 0, math.cos(TILT)))   # ring-plane normal
bm = bmesh.new()
N, W, T = 96, 0.075, 0.018
loops = []
for i in range(N):
    a = 2 * math.pi * i / N
    p = ring_pt(a)
    out = (p - C0 - PN * (p - C0).dot(PN)).normalized()
    loops.append([bm.verts.new(p + PN * sx * W / 2 + out * sy * T / 2) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))])
for i in range(N):
    A, B = loops[i], loops[(i + 1) % N]
    for k in range(4):
        bm.faces.new([A[k], A[(k + 1) % 4], B[(k + 1) % 4], B[k]])
mk("Bandolier", bm, "Leather", smooth=50)
cheese, wax, cutters = bmesh.new(), bmesh.new(), bmesh.new()
for deg in (-128, -110, -92, -74, -56):
    a = math.radians(deg)
    p = ring_pt(a)
    out = (p - C0 - PN * (p - C0).dot(PN)).normalized()
    base = p + out * (T / 2 - 0.002)
    vs = bm_lathe(cheese, [(0, 0), (0, 0.032), (0.028, 0.032), (0.028, 0)], 36, "X")
    bm_place(cheese, vs, base, base + out)
    vs = bm_lathe(wax, [(0, 0), (0, 0.0345), (0.0035, 0.036), (0.027, 0.036), (0.0305, 0.0345), (0.0305, 0)], 36, "X")
    bm_place(wax, vs, base, base + out)
    vs = bm_prism(cutters, [(0.0, 0.0), (0.06 * math.cos(math.radians(62)), 0.06 * math.sin(math.radians(62))),
                            (0.06 * math.cos(math.radians(118)), 0.06 * math.sin(math.radians(118)))], 0.025, 0.05, plane="YZ")
    bm_place(cutters, vs, base, base + out)
mk("BrieCheese", cheese, "Cheese", smooth=40)
wx = mk("BrieWax", wax, "Wax", smooth=40)
cut(wx, cutters)

# ================================================================== CHEESE HEAD
Z0 = 1.555
tri = path([("M", -0.21, Z0), ("L", 0.21, Z0), ("L", 0.21, Z0 + 0.38), ("L", -0.21, Z0 + 0.07)])
def top_z(x):
    return Z0 + 0.07 + (x + 0.21) / 0.42 * 0.31
bm = bmesh.new()
bm_prism(bm, tri, 0.0, 0.30, "XZ")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    f.material_index = 1 if f.normal.x > 0.9 else 0
head = mk("CheeseHead", bm, "Cheese", mats=["Cheese", "Rind"], bev=0.030, segs=5, bang=30, smooth=40)

EYES = {"L": ((0.085, Z0 + 0.195), 0.066), "R": ((-0.052, Z0 + 0.122), 0.049)}   # L = his left = the big one
rng = random.Random(7)
holes = []
for x, z, r in ((-0.150, Z0 + 0.050, 0.026), (0.160, Z0 + 0.065, 0.032), (0.035, Z0 + 0.045, 0.018),
                (0.175, Z0 + 0.300, 0.020), (-0.120, Z0 + 0.105, 0.014), (0.100, Z0 + 0.095, 0.012)):
    holes.append(((x, -0.15, z), r))
for s, y, r in ((0.22, -0.05, 0.042), (0.58, 0.06, 0.052), (0.82, -0.08, 0.030), (0.42, 0.11, 0.026),
                (0.05, 0.02, 0.030), (0.70, -0.13, 0.034)):
    x = -0.21 + 0.42 * s
    holes.append(((x, y, top_z(x)), r))
for x, z, r in ((0.10, Z0 + 0.12, 0.045), (-0.12, Z0 + 0.06, 0.03), (0.16, Z0 + 0.28, 0.028), (0.0, Z0 + 0.20, 0.02)):
    holes.append(((x, 0.15, z), r))
holes += [((0.21, -0.03, Z0 + 0.22), 0.030), ((0.21, 0.09, Z0 + 0.08), 0.020), ((-0.21, -0.15, Z0 + 0.03), 0.040),
          ((0.21, -0.15, Z0 + 0.38), 0.035)]
bm = bmesh.new()
for (x, y, z), r in holes:
    prof = [(-r, 0)] + [(-r * math.cos(math.pi * i / 16), r * math.sin(math.pi * i / 16)) for i in range(1, 16)] + [(r, 0)]
    bm_lathe(bm, prof, 28, "X", (x, y, z))
cut(head, bm)

# googly eyes: white base, black pupil (separate node, animated in the viewer), clear dome
rig = {"eyes": []}
dome = bmesh.new()
for key_, ((x, z), R) in EYES.items():
    y0 = -0.150
    lathe(f"EyeWhite{key_}", [(0.004, 0), (0.004, R), (-0.004, R), (-0.006, R * 0.96), (-0.006, 0)], "GooglyWhite",
          seg=48, axis="Y", c=(x, y0, z), smooth=50)
    rp = R * 0.52
    lathe(f"Pupil{key_}", [(-0.0062, 0), (-0.0062, rp), (-0.0085, rp * 0.97), (-0.0092, rp * 0.8), (-0.0092, 0)], "Pupil",
          group=f"pupil_{key_}", seg=40, axis="Y", c=(x, y0, z), smooth=50)
    prof = [(-0.004, R * 1.03)] + [(-0.004 - R * 0.42 * math.sin(math.pi / 2 * i / 10), R * 1.03 * math.cos(math.pi / 2 * i / 10))
                                    for i in range(1, 11)]
    bm_lathe(dome, prof, 48, "Y", (x, y0, z))
    ring = bmesh.new()
    bm_lathe(ring, [(0.002, R * 0.99), (0.002, R * 1.08), (-0.006, R * 1.08), (-0.007, R * 1.0)], 48, "Y", (x, y0, z), closed=True)
    mk(f"EyeRim{key_}", ring, "GooglyWhite", smooth=50)
    rig["eyes"].append({"key": key_, "center": [x, y0 - 0.0075, z], "radius": R, "pupil": rp})
mk("EyeDomes", dome, "Glass", group="domes", smooth=50)

# ================================================================== THE GRATE EQUALIZER (box grater)
GX, GY = FIST_R[0], FIST_R[1]
def frustum(bm, x, y, z0, z1, w0, d0, w1, d1):
    vs = [bm.verts.new((x + sx * (w0 if k == 0 else w1) / 2, y + sy * (d0 if k == 0 else d1) / 2, z0 if k == 0 else z1))
          for k in (0, 1) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(vs[3::-1]); bm.faces.new(vs[4:])
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([vs[i], vs[j], vs[4 + j], vs[4 + i]])
bm = bmesh.new(); frustum(bm, GX, GY, 0.375, 0.705, 0.150, 0.120, 0.100, 0.080)
gr = mk("Grater", bm, "Steel", bev=0.004, segs=2)
bm = bmesh.new(); frustum(bm, GX, GY, 0.360, 0.720, 0.140, 0.110, 0.090, 0.070)
for zi in range(7):
    z = 0.410 + zi * 0.040
    for xi in range(-1, 2):
        bm_prism(bm, rrect(GX + xi * 0.030 - 0.009, z, GX + xi * 0.030 + 0.009, z + 0.010, 0.004), GY, 0.3)
    for yi in (-1, 1):
        bm_prism(bm, circle(GY + yi * 0.022, z + 0.012, 0.0055, 12), GX, 0.3, plane="YZ")
cut(gr, bm)
bm = bmesh.new()
bm_prism(bm, path([("A", GX, 0.705, 0.062, 0, 180, 20), ("A", GX, 0.705, 0.048, 180, 0, 20)]), GY, 0.016)
mk("GraterHandle", bm, "Polymer", bev=0.004, segs=2, smooth=50)

# ------------------------------------------------------------------ export
with open(os.path.join(OUT, "rig.json"), "w") as f:
    # convert to three.js space (Y up): (x, y, z)_blender -> (x, z, -y)
    json.dump({"eyes": [{**e, "center": [e["center"][0], e["center"][2], -e["center"][1]]} for e in rig["eyes"]]}, f)
lib.finalize(os.path.join(OUT, "cheeseman.glb"), bake=BAKE, ao_distance=0.12, samples=32)
