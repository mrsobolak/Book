"""
TIM CHEESE v2, the Cheeseman: a TF2-style character with a Swiss-cheese wedge for a head and googly eyes.

    blender -b --python build_cheeseman.py -- [out_dir] [--nobake]

Build: lean and lanky, somewhere between the Scout and the Demoman. Torso, neck, limbs, palms and every
finger segment are elliptical lofts / rounded rods under Catmull-Clark smoothing; the head, hat, grater,
buckles, pouches, laces and tags are hard-surface parts with exact booleans. Character faces -Y, +Z up,
+X is his own left. Metres; he stands about 1.86 m to the top of the wedge, 1.97 m with the cap.
"""
import json, math, os, sys

sys.path.insert(0, "/home/user/Book/cod/armory")
import bpy, bmesh
from mathutils import Vector, Matrix
import lib
from lib import (path, rrect, circle, superellipse, smoothstep, bm_prism, bm_lathe, bm_tube, bm_loft, bm_ellipsoid,
                 bm_rod, bm_box, bm_place, rotate_verts, mirror_y, mk, cut, prism, lathe, rod, loft, ellipsoid,
                 rounded_lathe_end)

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in args if not a.startswith("--")), HERE)
BAKE = "--nobake" not in args

lib.reset()
V = Vector
UPY = (0, -1, 0)         # loft "up" for mostly-vertical tubes: rx along X, ry along Y


def lerp(a, b, t):
    return V(a).lerp(V(b), t)


def ring(name, p0, p1, t, r_in, r_out, width, mat, **kw):
    """Annulus around segment p0->p1 at parameter t (cuffs, sock tops, tape)."""
    bm = bmesh.new()
    vs = bm_lathe(bm, [(0, r_in), (0, r_out), (width * 0.2, r_out + 0.004), (width * 0.8, r_out + 0.004),
                       (width, r_out), (width, r_in)], 40, "X", (0, 0, 0), closed=True)
    d = (V(p1) - V(p0)).normalized()
    c = lerp(p0, p1, t) - d * width / 2
    bm_place(bm, vs, c, c + d)
    return mk(name, bm, mat, smooth=60, **kw)


# ================================================================== SKELETON
SH_L, EL_L, WR_L = V((0.215, -0.030, 1.425)), V((0.262, 0.035, 1.180)), V((0.250, -0.075, 0.960))
SH_R, EL_R, WR_R = V((-0.215, -0.030, 1.425)), V((-0.258, 0.060, 1.185)), V((-0.268, 0.000, 0.965))
HIP_L, KN_L, AN_L = V((0.105, 0.000, 0.935)), V((0.125, -0.035, 0.520)), V((0.130, 0.000, 0.105))
HIP_R, KN_R, AN_R = V((-0.105, 0.000, 0.935)), V((-0.135, -0.010, 0.515)), V((-0.150, 0.010, 0.105))

# ================================================================== TORSO (shirt), NECK
loft("Torso", [
    (V((0.0, 0.000, 0.905)), 0.150, 0.105),
    (V((0.0, 0.000, 0.980)), 0.140, 0.100),
    (V((0.0, -0.005, 1.060)), 0.135, 0.098),      # waist
    (V((0.0, -0.015, 1.160)), 0.152, 0.108),
    (V((0.0, -0.025, 1.260)), 0.180, 0.122),      # chest
    (V((0.0, -0.030, 1.350)), 0.200, 0.128),
    (V((0.0, -0.030, 1.425)), 0.205, 0.120),      # shoulders
    (V((0.0, -0.028, 1.470)), 0.150, 0.100),
    (V((0.0, -0.025, 1.495)), 0.095, 0.078),      # traps / collar base
], "Team", seg=40, up=UPY, subsurf=2)
for s, sh in ((1, SH_L), (-1, SH_R)):
    ellipsoid(f"Delt{s}", sh + V((s * 0.012, 0, 0.012)), 0.082, 0.076, 0.080, "Team", subsurf=1)
loft("Neck", [(V((0, -0.020, 1.455)), 0.060, 0.056), (V((0, -0.020, 1.520)), 0.054, 0.050),
              (V((0, -0.022, 1.580)), 0.052, 0.048)], "Skin", seg=32, up=UPY, subsurf=2)
# collar (team accent) + undershirt V
lathe("Collar", [(0, 0.070), (0, 0.098), (0.018, 0.104), (0.036, 0.094), (0.036, 0.070)], "Team2", seg=48, axis="Z",
      c=(0, -0.022, 1.500), closed=True, smooth=60)
prism("Undershirt", path([("M", -0.058, 1.505), ("L", 0.058, 1.505), ("L", 0.0, 1.415)]), -0.125, 0.012, "Cloth",
      bev=0.004, segs=2)
# rolled sleeve cuffs
for s, sh, el in ((1, SH_L, EL_L), (-1, SH_R, EL_R)):
    ring(f"SleeveCuff{s}", sh, el, 0.40, 0.058, 0.074, 0.040, "Team2")
    loft(f"Sleeve{s}", [(sh + V((s * 0.01, 0, -0.02)), 0.070, 0.068), (lerp(sh, el, 0.42), 0.062, 0.060)], "Team",
         seg=32, up=UPY, subsurf=2)

# ================================================================== ARMS
for s, sh, el, wr in ((1, SH_L, EL_L, WR_L), (-1, SH_R, EL_R, WR_R)):
    loft(f"UpperArm{s}", [(lerp(sh, el, 0.35), 0.056, 0.054), (lerp(sh, el, 0.7), 0.052, 0.050), (el, 0.050, 0.048)],
         "Skin", seg=32, up=UPY, subsurf=2)
    ellipsoid(f"Elbow{s}", el, 0.052, 0.050, 0.054, "Skin", subsurf=1)
    loft(f"Forearm{s}", [(el, 0.052, 0.050), (lerp(el, wr, 0.35), 0.058, 0.052), (lerp(el, wr, 0.7), 0.050, 0.044),
                         (wr, 0.040, 0.034)], "Skin", seg=32, up=UPY, subsurf=2)

# ================================================================== HANDS with fingers
def hand(prefix, wrist, F, U, curls, thumb_curl, glove=False, spread=1.0, sign=1):
    """wrist: Vector; F: finger direction (flat hand); U: back-of-hand normal; curls: 4 base curl angles (rad)
    per segment for index..pinky; sign=+1 puts the thumb on the +Sd side, -1 on the other."""
    F = V(F).normalized(); U = V(U).normalized()
    Sd = F.cross(U).normalized(); U = Sd.cross(F).normalized()
    palm_mat = "Glove" if glove else "Skin"
    # palm: flat loft wrist -> knuckles
    loft(f"{prefix}Palm", [(wrist, 0.034, 0.022), (wrist + F * 0.028, 0.041, 0.018), (wrist + F * 0.062, 0.045, 0.016),
                           (wrist + F * 0.086, 0.043, 0.015)], palm_mat, seg=28, up=U, subsurf=2)
    if glove:
        ring(f"{prefix}GloveCuff", wrist - F * 0.02, wrist + F * 0.03, 0.15, 0.030, 0.040, 0.026, "Glove")
    fingers, knuckles = bmesh.new(), bmesh.new()
    lengths = [0.076, 0.082, 0.076, 0.060]
    offs = [-0.031, -0.0105, 0.0105, 0.031]
    for i, (L, off) in enumerate(zip(lengths, offs)):
        base = wrist + F * 0.086 + Sd * (off * spread * sign)
        base -= U * 0.003
        r = 0.0115 if i < 3 else 0.0100
        d = F.copy(); ang = 0.0
        p = base
        bm_ellipsoid(knuckles, p, r * 1.15, r * 1.15, r * 1.15, seg=16, rings=8)
        for k, frac in enumerate((0.42, 0.32, 0.26)):
            ang += curls[i] * (1.0 + 0.15 * k)
            d = (F * math.cos(ang) - U * math.sin(ang)).normalized()      # curl toward the palm
            q = p + d * (L * frac)
            rk = r * (1.0 - 0.12 * k)
            bm_rod(fingers, p, q, rk, seg=16, rounded=True)
            if k < 2:
                bm_ellipsoid(knuckles, q, rk * 1.08, rk * 1.08, rk * 1.08, seg=16, rings=8)
            p = q
    # thumb
    tb = wrist + F * 0.030 + Sd * (0.036 * sign) - U * 0.004
    d0 = (F * 0.55 + Sd * (0.75 * sign) - U * 0.25).normalized()
    ax = d0.cross(U).normalized()
    p = tb
    bm_ellipsoid(knuckles, p, 0.014, 0.014, 0.014, seg=16, rings=8)
    for k, L in enumerate((0.046, 0.040)):
        rot = Matrix.Rotation(-thumb_curl * (1.0 + 0.3 * k), 3, ax)
        d0 = (rot @ d0).normalized()
        q = p + d0 * L
        bm_rod(fingers, p, q, 0.0125 - 0.0015 * k, seg=16, rounded=True)
        if k == 0:
            bm_ellipsoid(knuckles, q, 0.0125, 0.0125, 0.0125, seg=16, rings=8)
        p = q
    mk(f"{prefix}Fingers", fingers, "Skin", smooth=60)
    mk(f"{prefix}Knuckles", knuckles, "Skin", smooth=60)

# left hand: relaxed at his side, fingers loosely curled, wrapped in tape
hand("HandL", WR_L, F=(0.10, -0.30, -0.95), U=(0.96, -0.22, 0.15), curls=(0.30, 0.36, 0.40, 0.44), thumb_curl=0.35, sign=-1)
ring("TapeL1", WR_L - V((0, 0, 0.03)), WR_L + V((0, 0, 0.03)), 0.35, 0.034, 0.041, 0.012, "Cloth")
ring("TapeL2", WR_L - V((0, 0, 0.03)), WR_L + V((0, 0, 0.03)), 0.62, 0.035, 0.042, 0.012, "Cloth")
# right hand: fingerless glove, gripping the grater handle (bar along Y under the palm)
hand("HandR", WR_R, F=(0.0, -0.10, -1.0), U=(-1.0, 0.0, 0.0), curls=(0.95, 1.0, 1.0, 1.05), thumb_curl=0.9, glove=True, sign=1)

# ================================================================== LEGS, BOOTS
for s, hip, kn, an in ((1, HIP_L, KN_L, AN_L), (-1, HIP_R, KN_R, AN_R)):
    loft(f"Thigh{s}", [(hip + V((0, 0, 0.02)), 0.090, 0.092), (lerp(hip, kn, 0.4), 0.082, 0.084),
                       (lerp(hip, kn, 0.8), 0.070, 0.072), (kn, 0.064, 0.066)], "Pants", seg=32, up=UPY, subsurf=2)
    ellipsoid(f"Knee{s}", kn + V((0, -0.006, 0)), 0.066, 0.070, 0.072, "Pants", subsurf=1)
    loft(f"Shin{s}", [(kn, 0.064, 0.066), (lerp(kn, an, 0.35), 0.064, 0.070), (lerp(kn, an, 0.75), 0.052, 0.056),
                      (an + V((0, 0, 0.10)), 0.046, 0.050)], "Pants", seg=32, up=UPY, subsurf=2)
    ring(f"Sock{s}", an + V((0, 0, 0.10)), an + V((0, 0, 0.25)), 0.55, 0.045, 0.054, 0.030, "Cloth")
    # boot: shaft + foot + toe cap, sole, laces with eyelets
    loft(f"BootShaft{s}", [(an + V((0, 0, 0.19)), 0.056, 0.060), (an + V((0, 0, 0.10)), 0.058, 0.062),
                           (an + V((0, 0, 0.04)), 0.060, 0.066), (an + V((0, -0.01, 0.0)), 0.060, 0.070)],
         "Boots", seg=32, up=UPY, subsurf=2)
    foot = an + V((0, 0, -0.045))
    loft(f"Foot{s}", [(foot + V((0, 0.06, 0)), 0.052, 0.050), (foot + V((0, 0.0, 0.004)), 0.062, 0.058),
                      (foot + V((0, -0.08, 0.002)), 0.064, 0.055), (foot + V((0, -0.16, -0.004)), 0.062, 0.046),
                      (foot + V((0, -0.215, -0.010)), 0.048, 0.034)], "Boots", seg=32, up=(0, 0, 1), subsurf=2)
    ellipsoid(f"ToeCap{s}", foot + V((0, -0.170, 0.000)), 0.060, 0.070, 0.044, "Leather", subsurf=1)
    sole = prism(f"Sole{s}", rrect(-0.070, -0.245, 0.070, 0.075, 0.060, n=6), foot.z - 0.045, 0.028, "Rubber",
                 plane="XY", bev=0.006, segs=2)
    sole.location = (an.x, an.y, 0)
    # lacing panel
    lace, eye = bmesh.new(), bmesh.new()
    for k in range(4):
        z = an.z + 0.03 + 0.036 * k
        y = an.y - 0.055 - 0.012 * k
        for side in (1, -1):
            bm_lathe(eye, [(0, 0), (0, 0.0055), (0.004, 0.0055), (0.004, 0)], 12, "Y", (an.x + side * 0.024, y - 0.014, z))
        if k < 3:
            z2, y2 = z + 0.036, y - 0.012
            bm_rod(lace, (an.x - 0.024, y - 0.017, z), (an.x + 0.024, y2 - 0.017, z2), 0.0035, seg=10)
            bm_rod(lace, (an.x + 0.024, y - 0.017, z), (an.x - 0.024, y2 - 0.017, z2), 0.0035, seg=10)
    mk(f"Laces{s}", lace, "Cloth", smooth=60)
    mk(f"Eyelets{s}", eye, "Brass")

# ================================================================== BELT, POUCHES, TAGS
bm = bmesh.new()
bm_tube(bm, superellipse(0.172, 0.126, 0, 0.0, e=2.4, n=64), superellipse(0.150, 0.106, 0, 0.0, e=2.4, n=64),
        0.915, 0.958, plane="XY")
mk("Belt", bm, "Leather", bev=0.004, segs=2)
bk = prism("Buckle", path([("M", -0.036, 0.918), ("L", 0.036, 0.918), ("L", 0.036, 0.956), ("L", -0.036, 0.928)]),
           -0.134, 0.012, "Brass", bev=0.003, segs=2)
bm = bmesh.new()
for x, z, r in ((0.018, 0.938, 0.006), (0.0, 0.927, 0.0045)):
    bm_lathe(bm, [(-0.02, 0), (-0.02, r), (0.02, r), (0.02, 0)], 16, "Y", (x, -0.14, z))
cut(bk, bm)
for s in (1, -1):
    x = s * 0.125
    prism(f"Pouch{s}", rrect(x - 0.036, 0.845, x + 0.036, 0.935, 0.012), -0.118, 0.034, "Leather", bev=0.006, segs=3)
    prism(f"PouchFlap{s}", rrect(x - 0.039, 0.900, x + 0.039, 0.945, 0.010), -0.128, 0.020, "Team2", bev=0.005, segs=3)
    lathe(f"PouchButton{s}", [(0, 0), (0, 0.007), (0.003, 0.007), (0.004, 0.005), (0.004, 0)], "Brass", seg=20, axis="Y",
          c=(x, -0.138, 0.906))
# dog tags on a thin chain
rod("TagChain", (0.0, -0.118, 1.470), (0.012, -0.152, 1.350), 0.0018, "Steel", seg=8)
for i, (dx, dz) in enumerate(((0.0, 0.0), (0.008, -0.010))):
    prism(f"Tag{i}", rrect(0.0 + dx, 1.300 + dz, 0.028 + dx, 1.352 + dz, 0.008), -0.155 - 0.004 * i, 0.003, "Steel",
          bev=0.001, segs=1)

# ================================================================== THE BRIE-DOLIER (bandolier of wax wheels)
C0 = V((0, -0.02, 1.235))
TILT = math.radians(-40)
def ring_pt(a, rx=0.245, ry=0.165):
    p = V((rx * math.cos(a), ry * math.sin(a), 0))
    return V((p.x * math.cos(TILT) + p.z * math.sin(TILT), p.y, -p.x * math.sin(TILT) + p.z * math.cos(TILT))) + C0
PN = V((math.sin(TILT), 0, math.cos(TILT)))
bm = bmesh.new()
N, W, T = 96, 0.055, 0.014
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
for deg in (-124, -104, -84, -64):
    a = math.radians(deg)
    p = ring_pt(a)
    out = (p - C0 - PN * (p - C0).dot(PN)).normalized()
    base = p + out * (T / 2 - 0.002)
    vs = bm_lathe(cheese, [(0, 0), (0, 0.024), (0.022, 0.024), (0.022, 0)], 32, "X"); bm_place(cheese, vs, base, base + out)
    vs = bm_lathe(wax, [(0, 0), (0, 0.026), (0.003, 0.0275), (0.021, 0.0275), (0.024, 0.026), (0.024, 0)], 32, "X")
    bm_place(wax, vs, base, base + out)
    vs = bm_prism(cutters, [(0.0, 0.0), (0.05 * math.cos(math.radians(62)), 0.05 * math.sin(math.radians(62))),
                            (0.05 * math.cos(math.radians(118)), 0.05 * math.sin(math.radians(118)))], 0.02, 0.05, plane="YZ")
    bm_place(cutters, vs, base, base + out)
mk("BrieCheese", cheese, "Cheese", smooth=40)
wx = mk("BrieWax", wax, "Wax", smooth=40)
cut(wx, cutters)

# ================================================================== CHEESE HEAD
Z0 = 1.560
HW, HD = 0.135, 0.150            # half width (x), half depth (y)
LOW, HIGH = 0.115, 0.365         # wedge heights at -X and +X
def top_z(x):
    return Z0 + LOW + (x + HW) / (2 * HW) * (HIGH - LOW)
tri = path([("M", -HW, Z0), ("L", HW, Z0), ("L", HW, Z0 + HIGH), ("L", -HW, Z0 + LOW)])
bm = bmesh.new()
bm_prism(bm, tri, 0.0, 2 * HD, "XZ")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    f.material_index = 1 if f.normal.x > 0.9 else 0
head = mk("CheeseHead", bm, "Cheese", mats=["Cheese", "Rind"], bev=0.024, segs=5, bang=30, smooth=40)

EYES = {"L": ((0.062, Z0 + 0.205), 0.054), "R": ((-0.048, Z0 + 0.128), 0.041)}   # his left eye is the big one
FY = -HD                                                                            # front face plane
holes = [((-0.095, FY, Z0 + 0.036), 0.016), ((0.118, FY, Z0 + 0.060), 0.020), ((0.005, FY, Z0 + 0.300), 0.014),
         ((0.120, FY, Z0 + 0.300), 0.018), ((-0.015, FY, Z0 + 0.235), 0.012)]
for s, y, r in ((0.16, -0.05, 0.030), (0.40, 0.07, 0.038), (0.66, -0.07, 0.024), (0.86, 0.04, 0.030), (0.30, -0.10, 0.016)):
    x = -HW + 2 * HW * s
    holes.append(((x, y, top_z(x)), r))
for x, z, r in ((0.06, Z0 + 0.10, 0.034), (-0.08, Z0 + 0.05, 0.022), (0.10, Z0 + 0.26, 0.022), (-0.02, Z0 + 0.19, 0.016)):
    holes.append(((x, HD, z), r))
holes += [((HW, -0.05, Z0 + 0.20), 0.026), ((HW, 0.08, Z0 + 0.08), 0.018), ((HW, -0.11, Z0 + 0.32), 0.024),
          ((-HW, -0.10, Z0 + 0.05), 0.024)]
bm = bmesh.new()
for (x, y, z), r in holes:
    prof = [(-r, 0)] + [(-r * math.cos(math.pi * i / 16), r * math.sin(math.pi * i / 16)) for i in range(1, 16)] + [(r, 0)]
    bm_lathe(bm, prof, 24, "X", (x, y, z))
# mouth: a crooked smirk cut into the front face
mouth = path([("M", -0.070, Z0 + 0.052), ("Q", (-0.010, Z0 + 0.020), (0.088, Z0 + 0.070), 12),
              ("Q", (0.030, Z0 + 0.052), (-0.070, Z0 + 0.052), 12)])
bm_prism(bm, mouth, FY + 0.012, 0.06)
cut(head, bm)
prism("MouthInner", mouth, FY + 0.032, 0.010, "Mouth")
teeth = bmesh.new()
for k in range(5):
    x = -0.040 + 0.024 * k
    bm_prism(teeth, rrect(x - 0.009, Z0 + 0.044 + 0.004 * k, x + 0.009, Z0 + 0.066 + 0.004 * k, 0.003), FY + 0.020, 0.012)
mk("Teeth", teeth, "Teeth", bev=0.002, segs=2)
# brows: two angled rind ridges, cocky
for key_, ((x, z), R), tilt in (("L", EYES["L"], -14), ("R", EYES["R"], 18)):
    bm = bmesh.new()
    vs = bm_prism(bm, rrect(-R * 1.15, -0.010, R * 1.15, 0.010, 0.008), FY - 0.006, 0.020)
    rotate_verts(bm, vs, tilt, "Y", (0, 0, 0))
    for v in vs:
        v.co += V((x, 0, z + R + 0.022))
    mk(f"Brow{key_}", bm, "Rind", bev=0.004, segs=2)

# googly eyes: white housing, black pupil (own group, moved by the viewer), clear dome, raised rim
rig = {"eyes": []}
dome = bmesh.new()
for key_, ((x, z), R) in EYES.items():
    lathe(f"EyeWhite{key_}", [(0.004, 0), (0.004, R), (-0.004, R), (-0.006, R * 0.96), (-0.006, 0)], "GooglyWhite",
          seg=48, axis="Y", c=(x, FY, z), smooth=50)
    rp = R * 0.50
    lathe(f"Pupil{key_}", [(-0.0062, 0), (-0.0062, rp), (-0.0085, rp * 0.97), (-0.0092, rp * 0.8), (-0.0092, 0)], "Pupil",
          group=f"pupil_{key_}", seg=40, axis="Y", c=(x, FY, z), smooth=50)
    prof = [(-0.004, R * 1.03)] + [(-0.004 - R * 0.42 * math.sin(math.pi / 2 * i / 10), R * 1.03 * math.cos(math.pi / 2 * i / 10))
                                    for i in range(1, 11)]
    bm_lathe(dome, prof, 48, "Y", (x, FY, z))
    rim = bmesh.new()
    bm_lathe(rim, [(0.002, R * 0.99), (0.002, R * 1.09), (-0.006, R * 1.09), (-0.007, R * 1.0)], 48, "Y", (x, FY, z), closed=True)
    mk(f"EyeRim{key_}", rim, "GooglyWhite", smooth=50)
    rig["eyes"].append({"key": key_, "center": [x, FY - 0.0075, z], "radius": R, "pupil": rp})
mk("EyeDomes", dome, "Glass", group="domes", smooth=50)

# flat cap perched on the slope of the wedge, brim forward, brass cheese badge
slope = math.degrees(math.atan2(HIGH - LOW, 2 * HW))
capc = V((0.055, -0.010, top_z(0.055) + 0.012))
bm = bmesh.new()
bm_ellipsoid(bm, (0, 0, 0.018), 0.135, 0.150, 0.040, seg=40, rings=12)
bm_prism(bm, path([("M", -0.065, -0.120), ("Q", (0.0, -0.215), (0.065, -0.120), 8), ("L", 0.065, -0.05), ("L", -0.065, -0.05)]),
         0.004, 0.012, plane="XY")
rotate_verts(bm, bm.verts[:], -slope, "Y", (0, 0, 0))
for v in bm.verts:
    v.co += capc
cap = mk("Cap", bm, "Team2", subsurf=1, smooth=50)
bm = bmesh.new()
vs = bm_lathe(bm, [(0, 0), (0, 0.012), (0.006, 0.012), (0.007, 0.008), (0.007, 0)], 20, "Z", (0, 0.0, 0.056))
rotate_verts(bm, vs, -slope, "Y", (0, 0, 0))
for v in vs:
    v.co += capc
mk("CapButton", bm, "Brass", bev=0.001, segs=1)
bm = bmesh.new()
vs = bm_prism(bm, path([("M", -0.020, -0.012), ("L", 0.020, -0.012), ("L", 0.020, 0.014), ("L", -0.020, -0.002)]),
              -0.146, 0.006, plane="XZ")
for v in vs:
    v.co += V((0, 0, 0.026))
rotate_verts(bm, vs, -slope, "Y", (0, 0, 0))
for v in vs:
    v.co += capc
mk("CapBadge", bm, "Brass", bev=0.002, segs=2)

# ================================================================== THE GRATE EQUALIZER (box grater, handle along Y)
GX, GY = WR_R.x - 0.012, WR_R.y - 0.02
HANDLE_Z = WR_R.z - 0.105
def frustum(bm, x, y, z0, z1, w0, d0, w1, d1):
    vs = [bm.verts.new((x + sx * (w0 if k == 0 else w1) / 2, y + sy * (d0 if k == 0 else d1) / 2, z0 if k == 0 else z1))
          for k in (0, 1) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(vs[3::-1]); bm.faces.new(vs[4:])
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([vs[i], vs[j], vs[4 + j], vs[4 + i]])
GZ0, GZ1 = HANDLE_Z - 0.335, HANDLE_Z - 0.012
bm = bmesh.new(); frustum(bm, GX, GY, GZ0, GZ1, 0.120, 0.098, 0.084, 0.068)
gr = mk("Grater", bm, "Stainless", bev=0.003, segs=2)
bm = bmesh.new(); frustum(bm, GX, GY, GZ0 - 0.01, GZ1 + 0.01, 0.110, 0.088, 0.074, 0.058)
for zi in range(7):
    z = GZ0 + 0.030 + zi * 0.040
    for xi in range(-1, 2):
        bm_prism(bm, rrect(GX + xi * 0.026 - 0.008, z, GX + xi * 0.026 + 0.008, z + 0.009, 0.0035), GY, 0.3)
    for yi in (-1, 1):
        bm_prism(bm, circle(GY + yi * 0.019, z + 0.011, 0.005, 12), GX, 0.3, plane="YZ")
cut(gr, bm)
bm = bmesh.new()
bm_prism(bm, path([("A", GY, GZ1, 0.052, 0, 180, 20), ("A", GY, GZ1, 0.038, 180, 0, 20)]), GX, 0.014, plane="YZ")
mk("GraterHandle", bm, "Polymer", bev=0.003, segs=2, smooth=50)

# ------------------------------------------------------------------ export
with open(os.path.join(OUT, "rig.json"), "w") as f:
    json.dump({"eyes": [{**e, "center": [e["center"][0], e["center"][2], -e["center"][1]]} for e in rig["eyes"]]}, f)
lib.finalize(os.path.join(OUT, "cheeseman.glb"), bake=BAKE, ao_distance=0.10, samples=32)
