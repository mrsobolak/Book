"""
TIM CHEESE v3, the Cheeseman: a TF2-style character with a Swiss-cheese wedge for a head and googly eyes.

    blender -b --python build_cheeseman.py -- [out_dir] [--nobake]

Lean build between the Scout and the Demoman. The organic masses (shirt, each arm, each hand, pants, each
boot) are built from overlapping shells (lofts, ellipsoids, capsules) and FUSED into one continuous surface
with a voxel remesh + smoothing, the way a sculptor blocks in a figure: no seams between torso and
shoulders, forearm and hand, finger and palm. Hard-surface parts (head, cap, grater, belt, buckles, laces)
are exact-boolean prisms and lathes. Pose: grater slung over the right shoulder, left hand pointing at you.
Character faces -Y, +Z up, +X is his own left. Metres.
"""
import json, math, os, sys

sys.path.insert(0, "/home/user/Book/cod/armory")
import bpy, bmesh
from mathutils import Vector, Matrix
import lib
from lib import (path, rrect, circle, superellipse, smoothstep, bm_prism, bm_lathe, bm_tube, bm_loft, bm_ellipsoid,
                 bm_rod, bm_box, bm_place, rotate_verts, mirror_y, mk, cut, prism, lathe, rod, loft, ellipsoid)

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in args if not a.startswith("--")), HERE)
BAKE = "--nobake" not in args

lib.reset()
V = Vector
UPY = (0, -1, 0)   # loft "up" for mostly-vertical tubes: rx along X, ry along Y


def lerp(a, b, t):
    return V(a).lerp(V(b), t)


def bm_ring(bm, p0, p1, t, r_in, r_out, width):
    """Closed torus-like ring (a rolled cuff) around segment p0->p1 at parameter t."""
    vs = bm_lathe(bm, [(0, r_in), (0, r_out), (width * 0.25, r_out + 0.006), (width * 0.75, r_out + 0.006),
                       (width, r_out), (width, r_in)], 32, "X", (0, 0, 0), closed=True)
    d = (V(p1) - V(p0)).normalized()
    c = lerp(p0, p1, t) - d * width / 2
    bm_place(bm, vs, c, c + d)
    return vs


def ring(name, p0, p1, t, r_in, r_out, width, mat, **kw):
    bm = bmesh.new()
    bm_ring(bm, p0, p1, t, r_in, r_out, width)
    return mk(name, bm, mat, smooth=60, **kw)


# ================================================================== SKELETON (pose)
SH_L, EL_L, WR_L = V((0.212, -0.052, 1.445)), V((0.300, 0.030, 1.245)), V((0.262, -0.205, 1.215))   # pointing at you
SH_R, EL_R, WR_R = V((-0.212, -0.052, 1.445)), V((-0.268, 0.020, 1.160)), V((-0.212, -0.190, 1.287))  # grater on shoulder
HIP_L, KN_L, AN_L = V((0.090, 0.000, 0.930)), V((0.155, -0.095, 0.535)), V((0.170, -0.040, 0.105))
HIP_R, KN_R, AN_R = V((-0.090, 0.000, 0.930)), V((-0.128, -0.060, 0.525)), V((-0.140, 0.030, 0.105))

# ================================================================== SHIRT: one fused mass
shirt = bmesh.new()
bm_loft(shirt, [
    (V((0.0, 0.000, 0.930)), 0.150, 0.108),      # hem, tucked under the belt
    (V((0.0, 0.000, 1.000)), 0.146, 0.105),
    (V((0.0, -0.008, 1.080)), 0.134, 0.097),     # waist
    (V((0.0, -0.018, 1.160)), 0.145, 0.102),
    (V((0.0, -0.030, 1.240)), 0.165, 0.114),
    (V((0.0, -0.040, 1.320)), 0.180, 0.120),     # chest
    (V((0.0, -0.048, 1.400)), 0.186, 0.116),
    (V((0.0, -0.052, 1.455)), 0.172, 0.104),     # shoulder line
    (V((0.0, -0.054, 1.500)), 0.118, 0.086),     # traps
    (V((0.0, -0.054, 1.540)), 0.072, 0.064),     # collar
], seg=40, up=UPY)
for s, sh, el in ((1, SH_L, EL_L), (-1, SH_R, EL_R)):
    bm_ellipsoid(shirt, sh + V((s * 0.004, 0, 0.006)), 0.068, 0.066, 0.074, seg=32, rings=16)          # deltoid cap
    bm_loft(shirt, [(sh + V((s * 0.006, 0, -0.004)), 0.070, 0.068), (lerp(sh, el, 0.25), 0.066, 0.064),
                    (lerp(sh, el, 0.44), 0.062, 0.060)], seg=28, up=UPY)                                # short sleeve
    bm_ring(shirt, sh, el, 0.44, 0.050, 0.070, 0.040)                                                    # rolled cuff
mk("Shirt", shirt, "Team", subsurf=1, fuse=0.006, decimate=0.5, smooth=60)
lathe("Collar", [(0, 0.062), (0, 0.092), (0.016, 0.100), (0.034, 0.090), (0.034, 0.062)], "Team2", seg=48, axis="Z",
      c=(0, -0.054, 1.535), closed=True, smooth=60)
prism("Undershirt", path([("M", -0.052, 1.545), ("L", 0.052, 1.545), ("L", 0.0, 1.462)]), -0.148, 0.012, "Cloth",
      bev=0.004, segs=2)
loft("Neck", [(V((0, -0.048, 1.480)), 0.062, 0.058), (V((0, -0.050, 1.540)), 0.056, 0.052),
              (V((0, -0.052, 1.600)), 0.054, 0.050)], "Skin", seg=32, up=UPY, subsurf=2)

# ================================================================== HANDS (shells into a bmesh, fused with the arm)
def hand_shells(bm, wrist, F, U, curls, thumb_curl, sign, scale=1.0):
    """F: finger direction of the flat hand; U: back-of-hand normal; curls: per-finger curl (rad per segment)
    index..pinky; sign: +1 puts thumb and index on the +Sd side (Sd = F x U), -1 on the other."""
    F = V(F).normalized(); U = V(U).normalized()
    Sd = F.cross(U).normalized(); U = Sd.cross(F).normalized()
    k = scale
    bm_loft(bm, [(wrist - F * 0.01, 0.036 * k, 0.024 * k), (wrist + F * 0.03, 0.044 * k, 0.020 * k),
                 (wrist + F * 0.065, 0.048 * k, 0.018 * k), (wrist + F * 0.092, 0.046 * k, 0.017 * k)], seg=28, up=U)
    lengths = [0.082, 0.088, 0.082, 0.066]
    offs = [0.034, 0.0115, -0.0115, -0.034]             # index sits next to the thumb
    for i, (L, off) in enumerate(zip(lengths, offs)):
        base = wrist + F * 0.090 + Sd * (off * sign * k) - U * 0.002
        r = (0.0125 if i < 3 else 0.0110) * k
        ang, p = 0.0, base
        bm_ellipsoid(bm, p, r * 1.12, r * 1.12, r * 1.12, seg=16, rings=8)
        for seg_i, frac in enumerate((0.42, 0.32, 0.26)):
            ang += curls[i] * (1.0 + 0.15 * seg_i)
            d = (F * math.cos(ang) - U * math.sin(ang)).normalized()
            q = p + d * (L * frac * k)
            rk = r * (1.0 - 0.10 * seg_i)
            bm_rod(bm, p, q, rk, seg=14, rounded=True)
            if seg_i < 2:
                bm_ellipsoid(bm, q, rk * 1.06, rk * 1.06, rk * 1.06, seg=14, rings=8)
            p = q
    tb = wrist + F * 0.032 + Sd * (0.040 * sign * k) - U * 0.004
    d0 = (F * 0.55 + Sd * (0.75 * sign) - U * 0.20).normalized()
    ax = d0.cross(U).normalized()
    p = tb
    bm_ellipsoid(bm, p, 0.016 * k, 0.016 * k, 0.016 * k, seg=16, rings=8)
    for seg_i, L in enumerate((0.050, 0.042)):
        d0 = (Matrix.Rotation(-thumb_curl * (1.0 + 0.3 * seg_i), 3, ax) @ d0).normalized()
        q = p + d0 * (L * k)
        bm_rod(bm, p, q, (0.0135 - 0.0015 * seg_i) * k, seg=14, rounded=True)
        if seg_i == 0:
            bm_ellipsoid(bm, q, 0.0135 * k, 0.0135 * k, 0.0135 * k, seg=14, rings=8)
        p = q


def arm_shells(bm, sh, el, wr):
    bm_loft(bm, [(lerp(sh, el, 0.30), 0.058, 0.056), (lerp(sh, el, 0.65), 0.054, 0.052), (el, 0.052, 0.050)], seg=28, up=UPY)
    bm_ellipsoid(bm, el, 0.054, 0.052, 0.056, seg=24, rings=12)
    bm_loft(bm, [(el, 0.053, 0.051), (lerp(el, wr, 0.30), 0.060, 0.054), (lerp(el, wr, 0.65), 0.050, 0.044),
                 (wr, 0.040, 0.034)], seg=28, up=UPY)


# left arm + hand: skin, pointing (index straight, others curled, thumb up)
arm = bmesh.new()
arm_shells(arm, SH_L, EL_L, WR_L)
hand_shells(arm, WR_L, F=(-0.15, -1.0, -0.10), U=(0.30, -0.05, 0.95), curls=(0.04, 0.95, 1.0, 1.05), thumb_curl=0.25, sign=1, scale=1.05)
mk("ArmL", arm, "Skin", subsurf=1, fuse=0.0045, decimate=0.5, smooth=60)
ring("TapeL1", WR_L - V((0, 0.03, 0)), WR_L + V((0, 0.03, 0)), 0.30, 0.036, 0.043, 0.012, "Cloth")
ring("TapeL2", WR_L - V((0, 0.03, 0)), WR_L + V((0, 0.03, 0)), 0.62, 0.037, 0.044, 0.012, "Cloth")
# right arm: skin to the wrist; the hand is a full work glove gripping the grater's bar
arm = bmesh.new()
arm_shells(arm, SH_R, EL_R, WR_R)
mk("ArmR", arm, "Skin", subsurf=1, fuse=0.0045, decimate=0.5, smooth=60)
F_R, U_R = V((0, 0.20, 0.98)).normalized(), V((0, -0.98, 0.20)).normalized()
glove = bmesh.new()
hand_shells(glove, WR_R, F=F_R, U=U_R, curls=(1.0, 1.05, 1.05, 1.1), thumb_curl=0.95, sign=-1, scale=1.08)
bm_ring(glove, WR_R - F_R * 0.05, WR_R + F_R * 0.05, 0.25, 0.030, 0.046, 0.030)                         # glove cuff
mk("GloveR", glove, "Glove", subsurf=1, fuse=0.0045, decimate=0.5, smooth=60)
BAR = WR_R + F_R * 0.120 - U_R * 0.026                                                                    # inside the fist

# ================================================================== PANTS: hips + legs, one fused mass
pants = bmesh.new()
bm_loft(pants, [(V((0, 0.0, 0.850)), 0.148, 0.108), (V((0, 0.0, 0.905)), 0.156, 0.113), (V((0, 0.0, 0.965)), 0.150, 0.109)],
        seg=40, up=UPY)
for hip, kn, an in ((HIP_L, KN_L, AN_L), (HIP_R, KN_R, AN_R)):
    bm_loft(pants, [(hip + V((0, 0, 0.03)), 0.092, 0.096), (lerp(hip, kn, 0.4), 0.084, 0.088),
                    (lerp(hip, kn, 0.8), 0.070, 0.074), (kn, 0.064, 0.068)], seg=32, up=UPY)
    bm_ellipsoid(pants, kn + V((0, -0.008, 0)), 0.068, 0.072, 0.074, seg=24, rings=12)
    bm_loft(pants, [(kn, 0.064, 0.068), (lerp(kn, an, 0.35), 0.066, 0.072), (lerp(kn, an, 0.75), 0.052, 0.056),
                    (an + V((0, 0, 0.14)), 0.048, 0.052)], seg=32, up=UPY)
mk("Pants", pants, "Pants", subsurf=1, fuse=0.006, decimate=0.5, smooth=60)

# ================================================================== BOOTS: big TF2 feet, fused per boot
for s, an in ((1, AN_L), (-1, AN_R)):
    boot = bmesh.new()
    bm_loft(boot, [(an + V((0, 0, 0.22)), 0.058, 0.064), (an + V((0, 0, 0.12)), 0.060, 0.066),
                   (an + V((0, 0, 0.04)), 0.062, 0.070), (an + V((0, -0.008, -0.01)), 0.064, 0.076)], seg=32, up=UPY)
    foot = an + V((0, 0, -0.050))
    bm_loft(boot, [(foot + V((0, 0.075, 0.004)), 0.056, 0.052), (foot + V((0, 0.0, 0.006)), 0.066, 0.060),
                   (foot + V((0, -0.09, 0.004)), 0.068, 0.056), (foot + V((0, -0.18, -0.002)), 0.066, 0.048),
                   (foot + V((0, -0.245, -0.010)), 0.050, 0.034)], seg=32, up=(0, 0, 1))
    bm_ellipsoid(boot, foot + V((0, -0.19, 0.002)), 0.064, 0.075, 0.046, seg=28, rings=12)
    bm_ring(boot, an + V((0, 0, 0.16)), an + V((0, 0, 0.30)), 0.40, 0.050, 0.063, 0.034)                 # pant cuff bulge
    mk(f"Boot{s}", boot, "Boots", subsurf=1, fuse=0.005, decimate=0.5, smooth=60)
    sole = prism(f"Sole{s}", rrect(-0.074, -0.275, 0.074, 0.090, 0.062, n=6), foot.z - 0.045, 0.030, "Rubber",
                 plane="XY", bev=0.006, segs=2)
    sole.location = (an.x, an.y, 0)
    ring(f"Sock{s}", an + V((0, 0, 0.14)), an + V((0, 0, 0.30)), 0.55, 0.046, 0.056, 0.026, "Cloth")
    lace, eye = bmesh.new(), bmesh.new()
    for k in range(4):
        z = an.z + 0.035 + 0.040 * k
        y = an.y - 0.062 - 0.010 * k
        for side in (1, -1):
            bm_lathe(eye, [(0, 0), (0, 0.006), (0.004, 0.006), (0.004, 0)], 12, "Y", (an.x + side * 0.026, y - 0.014, z))
        if k < 3:
            z2, y2 = z + 0.040, y - 0.010
            bm_rod(lace, (an.x - 0.026, y - 0.017, z), (an.x + 0.026, y2 - 0.017, z2), 0.0038, seg=10)
            bm_rod(lace, (an.x + 0.026, y - 0.017, z), (an.x - 0.026, y2 - 0.017, z2), 0.0038, seg=10)
    mk(f"Laces{s}", lace, "Cloth", smooth=60)
    mk(f"Eyelets{s}", eye, "Brass")

# ================================================================== BELT, POUCHES, TAGS
bm = bmesh.new()
bm_tube(bm, superellipse(0.176, 0.128, 0, 0.0, e=2.4, n=64), superellipse(0.152, 0.108, 0, 0.0, e=2.4, n=64),
        0.915, 0.960, plane="XY")
mk("Belt", bm, "Leather", bev=0.004, segs=2)
bk = prism("Buckle", path([("M", -0.038, 0.918), ("L", 0.038, 0.918), ("L", 0.038, 0.958), ("L", -0.038, 0.929)]),
           -0.138, 0.012, "Brass", bev=0.003, segs=2)
bm = bmesh.new()
for x, z, r in ((0.019, 0.940, 0.006), (0.0, 0.928, 0.0045)):
    bm_lathe(bm, [(-0.02, 0), (-0.02, r), (0.02, r), (0.02, 0)], 16, "Y", (x, -0.14, z))
cut(bk, bm)
for s in (1, -1):
    x = s * 0.128
    prism(f"Pouch{s}", rrect(x - 0.038, 0.840, x + 0.038, 0.935, 0.012), -0.120, 0.036, "Leather", bev=0.006, segs=3)
    prism(f"PouchFlap{s}", rrect(x - 0.041, 0.900, x + 0.041, 0.947, 0.010), -0.131, 0.020, "Team2", bev=0.005, segs=3)
    lathe(f"PouchButton{s}", [(0, 0), (0, 0.007), (0.003, 0.007), (0.004, 0.005), (0.004, 0)], "Brass", seg=20, axis="Y",
          c=(x, -0.141, 0.906))
rod("TagChain", (0.0, -0.140, 1.500), (0.014, -0.170, 1.375), 0.0018, "Steel", seg=8)
for i, (dx, dz) in enumerate(((0.0, 0.0), (0.009, -0.011))):
    prism(f"Tag{i}", rrect(0.0 + dx, 1.322 + dz, 0.030 + dx, 1.377 + dz, 0.008), -0.173 - 0.004 * i, 0.003, "Steel",
          bev=0.001, segs=1)

# ================================================================== THE BRIE-DOLIER (bandolier of wax wheels)
C0 = V((0, -0.035, 1.245))
TILT = math.radians(-40)
def ring_pt(a, rx=0.250, ry=0.168):
    p = V((rx * math.cos(a), ry * math.sin(a), 0))
    return V((p.x * math.cos(TILT) + p.z * math.sin(TILT), p.y, -p.x * math.sin(TILT) + p.z * math.cos(TILT))) + C0
PN = V((math.sin(TILT), 0, math.cos(TILT)))
bm = bmesh.new()
N, W, T = 96, 0.056, 0.014
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
for deg in (-126, -106, -86, -66):
    a = math.radians(deg)
    p = ring_pt(a)
    out = (p - C0 - PN * (p - C0).dot(PN)).normalized()
    base = p + out * (T / 2 - 0.002)
    vs = bm_lathe(cheese, [(0, 0), (0, 0.025), (0.023, 0.025), (0.023, 0)], 32, "X"); bm_place(cheese, vs, base, base + out)
    vs = bm_lathe(wax, [(0, 0), (0, 0.027), (0.003, 0.0285), (0.022, 0.0285), (0.025, 0.027), (0.025, 0)], 32, "X")
    bm_place(wax, vs, base, base + out)
    vs = bm_prism(cutters, [(0.0, 0.0), (0.05 * math.cos(math.radians(62)), 0.05 * math.sin(math.radians(62))),
                            (0.05 * math.cos(math.radians(118)), 0.05 * math.sin(math.radians(118)))], 0.02, 0.05, plane="YZ")
    bm_place(cutters, vs, base, base + out)
mk("BrieCheese", cheese, "Cheese", smooth=40)
wx = mk("BrieWax", wax, "Wax", smooth=40)
cut(wx, cutters)

# ================================================================== CHEESE HEAD (big, TF2 head-to-body ratio)
Z0 = 1.590
HY = -0.052                       # head centre y (follows the neck lean)
HW, HD = 0.150, 0.150             # half width (x), half depth (y)
LOW, HIGH = 0.130, 0.380          # wedge heights at -X and +X
def top_z(x):
    return Z0 + LOW + (x + HW) / (2 * HW) * (HIGH - LOW)
tri = path([("M", -HW, Z0), ("L", HW, Z0), ("L", HW, Z0 + HIGH), ("L", -HW, Z0 + LOW)])
bm = bmesh.new()
bm_prism(bm, tri, HY, 2 * HD, "XZ")
bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
for f in bm.faces:
    f.material_index = 1 if f.normal.x > 0.9 else 0
head = mk("CheeseHead", bm, "Cheese", mats=["Cheese", "Rind"], bev=0.028, segs=6, bang=30, smooth=40)

EYES = {"L": ((0.072, Z0 + 0.222), 0.058), "R": ((-0.052, Z0 + 0.140), 0.044)}   # his left eye is the big one
FY = HY - HD                                                                       # front face plane
holes = [((-0.105, FY, Z0 + 0.040), 0.017), ((0.128, FY, Z0 + 0.070), 0.020), ((0.010, FY, Z0 + 0.325), 0.015),
         ((0.128, FY, Z0 + 0.330), 0.019), ((-0.012, FY, Z0 + 0.262), 0.012), ((-0.120, FY, Z0 + 0.105), 0.011)]
for s, y, r in ((0.16, -0.05, 0.032), (0.40, 0.07, 0.040), (0.66, -0.07, 0.026), (0.86, 0.04, 0.032), (0.30, -0.10, 0.017)):
    x = -HW + 2 * HW * s
    holes.append(((x, HY + y, top_z(x)), r))
for x, z, r in ((0.06, Z0 + 0.10, 0.036), (-0.09, Z0 + 0.05, 0.024), (0.11, Z0 + 0.28, 0.024), (-0.02, Z0 + 0.20, 0.017)):
    holes.append(((x, HY + HD, z), r))
holes += [((HW, HY - 0.05, Z0 + 0.21), 0.028), ((HW, HY + 0.08, Z0 + 0.08), 0.019), ((HW, HY - 0.11, Z0 + 0.33), 0.025),
          ((-HW, HY - 0.10, Z0 + 0.05), 0.026)]
bm = bmesh.new()
for (x, y, z), r in holes:
    prof = [(-r, 0)] + [(-r * math.cos(math.pi * i / 16), r * math.sin(math.pi * i / 16)) for i in range(1, 16)] + [(r, 0)]
    bm_lathe(bm, prof, 24, "X", (x, y, z))
mouth = path([("M", -0.088, Z0 + 0.060), ("Q", (-0.012, Z0 + 0.018), (0.108, Z0 + 0.080), 14),
              ("Q", (0.040, Z0 + 0.060), (-0.088, Z0 + 0.060), 14)])
bm_prism(bm, mouth, FY + 0.014, 0.07)
cut(head, bm)
prism("MouthInner", mouth, FY + 0.038, 0.012, "Mouth")
teeth = bmesh.new()
for k in range(6):
    x = -0.052 + 0.026 * k
    bm_prism(teeth, rrect(x - 0.010, Z0 + 0.050 + 0.0045 * k, x + 0.010, Z0 + 0.074 + 0.0045 * k, 0.003), FY + 0.024, 0.014)
mk("Teeth", teeth, "Teeth", bev=0.002, segs=2)
# brows: thin, wide rind ridges just above each eye rim, inner ends down (smug)
for key_, ((x, z), R), tilt in (("L", EYES["L"], -12), ("R", EYES["R"], 14)):
    bm = bmesh.new()
    vs = bm_prism(bm, rrect(-R * 1.25, -0.007, R * 1.25, 0.007, 0.006), FY - 0.004, 0.014)
    rotate_verts(bm, vs, tilt, "Y", (0, 0, 0))
    for v in vs:
        v.co += V((x, 0, z + R * 1.12 + 0.016))
    mk(f"Brow{key_}", bm, "Rind", bev=0.003, segs=2)

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

# newsboy cap (team colour) perched on the slope of the wedge, cloth band, brass cheese badge
slope = math.degrees(math.atan2(HIGH - LOW, 2 * HW))
capc = V((0.060, HY - 0.012, top_z(0.060) + 0.010))
def place_cap(bm, verts):
    rotate_verts(bm, verts, -slope, "Y", (0, 0, 0))
    for v in verts:
        v.co += capc
bm = bmesh.new()
vs = bm_ellipsoid(bm, (0, 0, 0.030), 0.165, 0.180, 0.052, seg=40, rings=12)
vs += bm_prism(bm, path([("M", -0.075, -0.150), ("Q", (0.0, -0.250), (0.075, -0.150), 8), ("L", 0.075, -0.06), ("L", -0.075, -0.06)]),
               0.006, 0.014, plane="XY")
place_cap(bm, vs)
mk("Cap", bm, "Team", subsurf=1, fuse=0.005, decimate=0.6, smooth=60)
bm = bmesh.new()
vs = bm_lathe(bm, [(0.0, 0.150), (0.0, 0.158), (0.018, 0.158), (0.018, 0.150)], 48, "Z", (0, 0, 0), closed=True)
place_cap(bm, vs)
mk("CapBand", bm, "Cloth", smooth=60)
bm = bmesh.new()
vs = bm_lathe(bm, [(0, 0), (0, 0.013), (0.006, 0.013), (0.007, 0.009), (0.007, 0)], 20, "Z", (0, 0, 0.080))
place_cap(bm, vs)
mk("CapButton", bm, "Brass", bev=0.001, segs=1)
bm = bmesh.new()
vs = bm_prism(bm, path([("M", -0.024, -0.014), ("L", 0.024, -0.014), ("L", 0.024, 0.016), ("L", -0.024, -0.002)]),
              -0.162, 0.006, plane="XZ")
for v in vs:
    v.co += V((0, 0, 0.030))
place_cap(bm, vs)
mk("CapBadge", bm, "Brass", bev=0.002, segs=2)

# ================================================================== THE GRATE EQUALIZER, slung over the right shoulder
# built in a local frame: grip bar along X at the origin, two posts down to the grater top, body along -Z;
# then rotated about X so the body points up and back over the shoulder, and moved onto the bar in the fist.
D = V((0, 0.55, 0.83)).normalized()
theta = math.degrees(math.atan2(D.y, -D.z))
def to_world(bm, verts):
    rotate_verts(bm, verts, theta, "X", (0, 0, 0))
    for v in verts:
        v.co += BAR
def frustum(bm, z0, z1, w0, d0, w1, d1):
    vs = [bm.verts.new((sx * (w0 if k == 0 else w1) / 2, sy * (d0 if k == 0 else d1) / 2, z0 if k == 0 else z1))
          for k in (0, 1) for sx, sy in ((-1, -1), (1, -1), (1, 1), (-1, 1))]
    bm.faces.new(vs[3::-1]); bm.faces.new(vs[4:])
    for i in range(4):
        j = (i + 1) % 4
        bm.faces.new([vs[i], vs[j], vs[4 + j], vs[4 + i]])
    return vs
GZ1, GZ0 = -0.052, -0.400
bm = bmesh.new(); to_world(bm, frustum(bm, GZ0, GZ1, 0.130, 0.105, 0.090, 0.072))
gr = mk("Grater", bm, "Stainless", bev=0.003, segs=2)
bm = bmesh.new()
vs = frustum(bm, GZ0 - 0.01, GZ1 + 0.01, 0.120, 0.095, 0.080, 0.062)
for zi in range(7):
    z = GZ0 + 0.032 + zi * 0.044
    for xi in range(-1, 2):
        vs += bm_prism(bm, rrect(xi * 0.028 - 0.009, z, xi * 0.028 + 0.009, z + 0.010, 0.0035), 0.0, 0.3)
    for yi in (-1, 1):
        vs += bm_prism(bm, circle(yi * 0.020, z + 0.012, 0.0055, 12), 0.0, 0.3, plane="YZ")
to_world(bm, vs)
cut(gr, bm)
bm = bmesh.new()
vs = bm_rod(bm, (-0.040, 0, 0), (0.040, 0, 0), 0.011, seg=16, rounded=True)
for x in (-0.034, 0.034):
    vs += bm_rod(bm, (x, 0, 0.004), (x, 0, GZ1 + 0.004), 0.008, seg=12)
to_world(bm, vs)
mk("GraterHandle", bm, "Polymer", smooth=60)

# ------------------------------------------------------------------ export
with open(os.path.join(OUT, "rig.json"), "w") as f:
    json.dump({"eyes": [{**e, "center": [e["center"][0], e["center"][2], -e["center"][1]]} for e in rig["eyes"]]}, f)
lib.finalize(os.path.join(OUT, "cheeseman.glb"), bake=BAKE, ao_distance=0.10, samples=32)
