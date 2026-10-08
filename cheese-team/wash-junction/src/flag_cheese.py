"""SM_FlagCheese_Cheddar / SM_FlagCheese_Bleu -- the CTF 'flags'.
Giant wheel, 1.2 m across, 0.42 m tall, with a ~45 degree wedge cut out of the FRONT (+X) so the paste
shows.  Pivot at the centre (carried by players)."""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import assetkit as K
from mathutils import Vector

R, H = 0.6, 0.21           # radius, half height
GAP = 45.0                 # wedge angle, centred on +X


def wheel_profile():
    # (r, z) bottom -> top: flat-ish faces, rounded shoulders, slightly bulged belly
    pts = [(0.0, -H), (0.30, -H), (0.50, -H + 0.002), (0.565, -H + 0.006), (0.588, -H + 0.018), (0.598, -H + 0.045),
           (0.604, -0.07), (0.606, 0.0), (0.604, 0.07), (0.598, H - 0.045), (0.588, H - 0.018), (0.565, H - 0.006),
           (0.50, H - 0.002), (0.30, H), (0.0, H)]
    return pts


def wheel(rng):
    bm = K.lathe(wheel_profile(), seg=60, cap=False)
    # hand-made irregularity: a few mm of lumpiness, a slight sag
    ph = [rng.uniform(0, 6.28) for _ in range(4)]
    def f(v):
        a = math.atan2(v.y, v.x)
        rr = math.hypot(v.x, v.y)
        k = 1.0 + 0.004 * math.sin(3 * a + ph[0]) + 0.003 * math.sin(5 * a + ph[1])
        z = v.z + 0.003 * math.sin(2 * a + ph[2]) * (rr / R) - 0.004 * (1 - (rr / R) ** 2) * (1 if v.z > 0 else -1) * 0.5
        return Vector((v.x * k, v.y * k, z))
    return K.deform(bm, f)


def prof_r(z):
    pts = wheel_profile()
    for (r0, z0), (r1, z1) in zip(pts, pts[1:]):
        if z0 <= z <= z1 and z1 > z0:
            return r0 + (r1 - r0) * (z - z0) / (z1 - z0)
    return R


def drip(A, m, ang, z0, length, w, rng):
    """Wax drip on the side wall: a thin trail from the shoulder ending in a fat bead, 2-4 mm proud."""
    path, sc = [], []
    n = 9
    for i in range(n):
        t = i / (n - 1)
        z = z0 - length * t
        rr = prof_r(z) * 1.006 + 0.0015
        a = ang + 0.006 * math.sin(t * 4.0)
        path.append((rr * math.cos(a), rr * math.sin(a), z))
        sc.append(0.35 + 0.35 * t if t < 0.75 else (1.0 if t < 0.95 else 0.45))
    prof = [(w * math.cos(2 * math.pi * k / 6), 0.0055 * math.sin(2 * math.pi * k / 6)) for k in range(6)]
    bm = K.sweep(path, prof, up=(math.cos(ang), math.sin(ang), 0), scale=sc)
    A.add(bm, m, smooth=80, name="drip")


def build(name, rind_mat, paste_mat, rng, drips=True, holes=8):
    A = K.Asset(name, size=(1.2, 0.42, 1.2), tris=3000, tex=2048, pivot="center",
                note="Pivot at the wheel centre. Wedge (45 deg) faces +X.")
    body = A.add(wheel(rng), rind_mat, smooth=50, name="wheel")
    # the wedge cut -- faces made by this cutter become paste
    a = math.radians(GAP / 2)
    L = 1.0
    wedge = K.prism([(-0.003, 0.0), (L * math.cos(-a), L * math.sin(-a)), (L * 1.2, 0.0), (L * math.cos(a), L * math.sin(a))],
                    0.6, plane="xy")
    cw = A.cutter(wedge, paste_mat, smooth=20)
    A.cut(body, cw)
    # eyes in the cut faces: low-poly spheres sunk into both faces
    for side in (+1, -1):
        th = side * a
        u = Vector((math.cos(th), math.sin(th), 0))
        nrm = Vector((math.sin(a), -side * math.cos(a), 0))   # face normal, pointing into the gap
        for k in range(holes):
            rr = rng.uniform(0.12, 0.52)
            zz = rng.uniform(-0.15, 0.15)
            rho = rng.uniform(0.018, 0.04)
            c = u * rr + Vector((0, 0, zz)) + nrm * (rho * 0.35)
            sp = K.sphere(rho, seg=8, rings=5)
            A.cut(body, A.cutter(sp, paste_mat, at=c, smooth=80))
    if drips:
        for k in range(6):
            ang = math.radians(35 + k * 52 + rng.uniform(-12, 12))
            drip(A, rind_mat, ang, H - 0.035 - rng.uniform(0, 0.02), rng.uniform(0.07, 0.17), rng.uniform(0.010, 0.016), rng)
    A.ucx_cyl((0, 0, 0), R + 0.01, 2 * H, seg=12)
    A.build()


WAX = K.mat("wax", color="#8b0f12", dust=0.04)
CHEDDAR = K.mat("cheddar", color="#eaa24c",
                rim=dict(R=R, H=H, bands=[(0.006, "#6e0b0e", 0.35), (0.005, "#c27a2d", 0.7)]))
build("FlagCheese_Cheddar", WAX, CHEDDAR, random.Random(11))

BLEU_RIND = K.mat("bleu_rind")
BLEU = K.mat("bleu_paste", color="#e9e0c4",
             rim=dict(R=R, H=H, bands=[(0.004, "#9aa6a8", 0.95), (0.006, "#b8a888", 0.8)]))
build("FlagCheese_Bleu", BLEU_RIND, BLEU, random.Random(23), drips=False, holes=6)
