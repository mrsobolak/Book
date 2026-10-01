"""SM_FlagPedestal -- the CTF flag stand.

A heavy fabricated hexagonal steel plinth:
  * 32 mm hex base flange (flame-cut, chamfered corners) anchored by 12 studs with plate washers and nuts,
    six corner gussets, a fillet weld all round the foot of the body;
  * hex body: a proud kick rail, recessed infill panels framed by the corner posts, welded corners,
    a bolted access cover on the FRONT (+X) and a galvanised junction box + conduit (power feed for the
    light ring) on the back;
  * a [TEAM] perimeter band under an overhanging deck of six diamond-plate segments with welded radial seams;
  * a recessed circular channel (D 1.52 - 1.68 m) holding a frosted emitter ring (Glow slot) under retaining clips;
  * a raised machined turntable seat with six rubber chocks for the 1.2 m flag cheese.

Hexagon: 2.9 m across the corners on Y (W), 2.56 m across the flats on X (D) -- a flat faces the FRONT (+X).
Pivot: bottom centre = hex centre at ground level (modelled there, pivot="none" so it stays exactly on the hex axis).
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import assetkit as K
import bmesh
from mathutils import Vector, Matrix

C30, S30 = math.cos(math.radians(30)), math.sin(math.radians(30))


def ab(R, e):
    """hex with circumradius R (flats facing +/-X) whose corners are chamfered e deep -> (apothem, chamfer dist)"""
    return R * C30, R - e


# ------------------------------------------------------------------ dimensions (metres)
G_W = 0.040                          # grout fillet beyond the flange edge
A_F, B_F = 1.44 * C30, 1.41          # base flange 2.82 across chamfered corners; + grout = 2.90 (Y), 2.574 across flats (X)
A_K, B_K = ab(1.3014, 0.025)          # kick rail
A_W, B_W = ab(1.2875, 0.025)          # body wall (corner posts)
A_B, B_B = ab(1.3279, 0.030)          # [TEAM] band
A_D, B_D = ab(1.3452, 0.032)          # deck plate
Z_F = 0.032                           # flange top
Z_KT = 0.128                          # kick rail top
Z_WT = 0.776                          # body wall top / band bottom
Z_D = 0.920                           # deck top
T_D = 0.016                           # deck plate thickness
R_CI, R_CO = 0.750, 0.850             # light channel inner / outer radius
CH_DEPTH = 0.026
Z_GE, Z_GM = Z_D - 0.019, Z_D - 0.011  # emitter lens: edge / crown height
Z_TT = Z_D + 0.007                    # turntable top
R_MAT = 0.588                         # rubber seat mat radius
SEG = 48                              # segments on every circle in the channel (all aligned)


def isect(t1, d1, t2, d2):
    """intersection of the lines n(t1).p = d1 and n(t2).p = d2"""
    det = math.sin(t2 - t1)
    return ((d1 * math.sin(t2) - d2 * math.sin(t1)) / det, (d2 * math.cos(t1) - d1 * math.cos(t2)) / det)


def poly12(a, b):
    """hexagon (flats at 0, 60, ... deg at distance a) with its corners cut by chamfer faces at distance b.
    12 points CCW: [side0/ch0, ch0/side1, side1/ch1, ...].  Face j (point j -> j+1): even = chamfer, odd = side."""
    pts = []
    for k in range(6):
        th, ph, th2 = math.radians(60 * k), math.radians(60 * k + 30), math.radians(60 * k + 60)
        pts.append(isect(th, a, ph, b))
        pts.append(isect(ph, b, th2, a))
    return pts


def hexlathe(rings, split=True):
    """rings [(a, b, z)] listed bottom -> top with the solid on the inside.  Open 12-sided shell.
    split: every one of the 12 face columns gets its own vertices (they meet at 30 deg hard edges anyway), so
    the UV unwrap gets 12 straight strips instead of one hollow hexagonal ring that wastes the atlas.
    returns bm, faces[band][j]"""
    bm = bmesh.new()
    P = [(poly12(a, b), z) for a, b, z in rings]
    faces = [[None] * 12 for _ in range(len(rings) - 1)]
    if split:
        for j in range(12):
            k = (j + 1) % 12
            col = [(bm.verts.new((pts[j][0], pts[j][1], z)), bm.verts.new((pts[k][0], pts[k][1], z))) for pts, z in P]
            for i in range(len(rings) - 1):
                (a0, a1), (b0, b1) = col[i], col[i + 1]
                faces[i][j] = bm.faces.new([a0, a1, b1, b0])
    else:
        R = [[bm.verts.new((x, y, z)) for x, y in pts] for pts, z in P]
        for i, (A, B) in enumerate(zip(R, R[1:])):
            for j in range(12):
                k = (j + 1) % 12
                faces[i][j] = bm.faces.new([A[j], A[k], B[k], B[j]])
    return bm, faces


def rlathe(profile, seg, phase=0.0, chunks=1):
    """revolve [(r, z)] (bottom -> top / outside -> in, solid on the inside) without normal recalculation.
    r == 0 closes the end with a fan.  chunks > 1 splits the ring into that many arcs with their own vertices
    (arcs pack into the UV atlas far better than full rings)."""
    bm = bmesh.new()
    n = seg // chunks
    for c in range(chunks):
        idx = list(range(c * n, c * n + n + (1 if chunks > 1 else 0)))
        rings = []
        for r, z in profile:
            if r < 1e-9:
                rings.append([bm.verts.new((0, 0, z))])
            else:
                rings.append([bm.verts.new((r * math.cos(phase + 2 * math.pi * i / seg), r * math.sin(phase + 2 * math.pi * i / seg), z))
                              for i in idx])
        m = len(idx)
        for A, B in zip(rings, rings[1:]):
            for i in range(n):
                j = (i + 1) % m
                if len(B) == 1:
                    bm.faces.new([A[i], A[j], B[0]])
                elif len(A) == 1:
                    bm.faces.new([A[0], B[j], B[i]])
                else:
                    bm.faces.new([A[i], A[j], B[j], B[i]])
    return bm


def field(seed):
    """smooth world-space irregularity shared by every part, so the stacked shells stay closed:
    a few mm of lean and waviness growing with height, nothing at the ground."""
    rng = random.Random(seed)
    ph = [rng.uniform(0, 6.283) for _ in range(8)]

    def f(v):
        h = max(v.z, 0.0)
        dx = 0.0032 * h + 0.0012 * math.sin(2.1 * v.y + ph[0]) * h + 0.0006 * math.sin(5.3 * v.y + ph[1])
        dy = -0.0021 * h + 0.0012 * math.sin(1.9 * v.x + ph[2]) * h + 0.0006 * math.sin(4.7 * v.x + ph[3])
        dz = (0.0012 * math.sin(1.7 * v.x + ph[4]) * math.sin(1.3 * v.y + ph[5]) + 0.0008 * math.sin(3.1 * v.x + 2.3 * v.y + ph[6])) * min(1.0, h / 0.2)
        return Vector((v.x + dx, v.y + dy, v.z + dz))
    return f


F = field(5)


def world_deform(bm, rotz=0.0, extra=None):
    """apply F to a part built in a frame rotated by rotz (deg) about Z (keeps its local texture frame)."""
    R = Matrix.Rotation(math.radians(rotz), 3, "Z")
    Ri = R.inverted()

    def f(v):
        w = R @ v
        d = F(w) - w
        if extra:
            d = d + extra(w)
        return v + Ri @ d
    return K.deform(bm, f)


def rot2(x, y, deg):
    c, s = math.cos(math.radians(deg)), math.sin(math.radians(deg))
    return (c * x - s * y, s * x + c * y)


# ------------------------------------------------------------------ materials
import materials as MT


def r_ped_paint(g, p):
    """kit 'paint' + two layers the stock recipe lacks: dirt runs washed down from the ledge under the band
    (strongest just below it, fading towards the kick rail) and big sun-chalked blotches."""
    out = MT.r_paint(g, p)
    col, rough = out["color"], out["rough"]
    s = g.noise(g.vs(g.W, (13.0, 13.0, 0.65)), 1.0, 4, 0.6)
    s2 = g.noise(g.vs(g.W, (38.0, 38.0, 1.3)), 1.0, 3, 0.5)
    run = g.mul(g.smooth(g.add(g.mul(s, 0.7), g.mul(s2, 0.3)), 0.50, 0.68), g.vert)
    hang = g.smooth(g.Wz, p.get("z_top", 0.8) - p.get("run_len", 0.5), p.get("z_top", 0.8))
    m = g.mul(g.mul(run, g.add(g.mul(hang, 0.75), 0.25)), p.get("runs", 0.6))
    col = g.mixc(m, col, g.mulc(col, (0.55, 0.47, 0.38)))
    rough = g.mixf(m, rough, g.add(rough, 0.08))
    ch = g.mul(g.smooth(g.noise(g.vo(g.W, 4.4), 1.4, 4, 0.55), 0.48, 0.74), p.get("chalk", 0.35))
    col = g.mixc(ch, col, g.hsv(col, 0.5, 0.7, 1.2))
    rough = g.mixf(ch, rough, 0.86)
    out.update(color=col, rough=rough)
    return out


MT.RECIPES["ped_paint"] = r_ped_paint      # registered from this script only (kit untouched)

BODY = K.mat("ped_paint", z_top=0.776, runs=0.7, chalk=0.4, color="#474842", under="rust", chips=0.7, flake=0.8, fade=0.6, scratch=0.7, rough=0.68,
             grime=1.0, dust=0.5, streaks=1.0, splash=0.75, splash_h=0.32)
COVER = K.mat("ped_paint", z_top=0.62, runs=0.5, chalk=0.3, run_len=0.3, color="#50524c", under="rust", chips=0.7, flake=0.1, fade=0.4, scratch=0.7,
              grime=0.7, dust=0.45, streaks=0.5, splash=0.5, splash_h=0.3)
TEAMP = K.mat("team", chips=0.7, flake=0.3, scratch=0.8, rough=0.62, grime=0.7, dust=0.35, streaks=0.6, splash=0.35)
DECK = K.mat("diamond", color="#5d5f60", pitch=0.04, rust=0.45, worn=0.8, grime=0.65, dust=0.35)
PLATE_EDGE = K.mat("steel", color="#4a4a48", rust=0.55, worn=0.9, grime=0.6, dust=0.4)
FLANGE = K.mat("steel", color="#3d3a35", rust=0.75, worn=0.55, grime=0.7, dust=0.6, splash=0.8, splash_h=0.2)
WELD = K.mat("steel", color="#3a3936", rust=0.7, worn=0.6, grime=0.6, dust=0.4)
TURN = K.mat("steel", color="#5a5c5e", rust=0.2, worn=1.0, rough=0.38, grime=0.5, dust=0.35)
NUT = K.mat("steel", color="#4b4a47", rust=0.6, worn=0.9, grime=0.6, dust=0.5, splash=0.6, splash_h=0.15)
BOLT = K.mat("steel", color="#55575a", rust=0.3, worn=1.0, grime=0.5, dust=0.4)
RUBBER = K.mat("rubber", color="#1f1e1c", dust=0.55)
MAT = K.mat("rubber", color="#262523", dust=0.25, grime=0.7)
BRASS = K.mat("brass", color="#7d6234", tarnish=1.0, dust=0.45)
GROUT = K.mat("concrete", color="#8e877b", board=0, chips=0.9, efflor=0.3, dust=0.7, grime=0.7, splash=0.6, splash_h=0.1)
GALV = K.mat("galv", oxide=0.7, rust=0.25, dust=0.45, splash=0.5, splash_h=0.25)
CLIP = K.mat("steel", color="#4f5052", rust=0.35, worn=0.9, dust=0.3)


# ------------------------------------------------------------------ parts
def base_flange(A):
    bm, _ = hexlathe([(A_F, B_F, 0.0), (A_F, B_F, Z_F - 0.009), (A_F - 0.009, B_F - 0.009, Z_F),
                      (A_K - 0.006, B_K - 0.006, Z_F)])
    world_deform(bm)
    fl = A.add(bm, FLANGE, smooth=20, name="flange")
    # non-shrink grout bed under the plate, trimmed off at ~45 deg round its edge
    rng = random.Random(3)
    bm, _ = hexlathe([(A_F + G_W, B_F + G_W, 0.0), (A_F + 0.018, B_F + 0.018, 0.011), (A_F - 0.002, B_F - 0.002, 0.017)])
    K.deform(bm, lambda v: Vector((v.x, v.y, v.z * (1.0 + 0.25 * math.sin(7.0 * v.x + 3.0) * math.sin(6.0 * v.y + 1.0))
                                   if v.z > 0.005 else v.z)))
    A.add(bm, GROUT, smooth=40, name="grout")
    return fl


def anchors(A, rng):
    for k in range(6):
        th = 60 * k
        for s in (-1, 1):
            t = s * 0.40 + rng.uniform(-0.01, 0.01)
            x, y = rot2(1.188, t, th)
            spin = th + rng.uniform(-8, 8)
            # plate washer, nut, stud
            A.add(K.box(0.078, 0.078, 0.008, drop=("-z",)), NUT, at=(x, y, Z_F + 0.004), rot=(0, 0, th + rng.uniform(-4, 4)),
                  smooth=20, name="washer")
            A.add(K.cyl(0.027, 0.024, seg=6, phase=0.0), NUT, at=(x, y, Z_F + 0.008 + 0.012), rot=(0, 0, spin), smooth=20,
                  name="nut", drop=("-z",))
            sh = rng.uniform(0.022, 0.036)
            A.add(K.cyl(0.0145, sh, seg=6), NUT, at=(x, y, Z_F + 0.008 + 0.024 + sh / 2 - 0.004), rot=(0, 0, spin + 30),
                  smooth=50, name="stud", drop=("-z",))


def gussets(A, rng):
    L, H = B_F - 0.018 - (B_W - 0.004), 0.20
    for k in range(6):
        ph = 60 * k + 30
        bm = K.prism([(0, 0), (L, 0), (L, 0.028), (0.032, H), (0, H)], 0.016, plane="xz")
        r0 = B_W - 0.004
        x, y = rot2(r0, 0, ph)
        A.add(bm, FLANGE, at=(x, y, Z_F), rot=(0, 0, ph), smooth=20, name="gusset", drop=("-z", "-x"))


def kick_rail(A, rng):
    """[TEAM] kick plates round the foot of the body, bent in here and there"""
    rings = [(A_K, B_K, Z_F), (A_K, B_K, Z_KT), (A_W - 0.002, B_W - 0.002, Z_KT + 0.012)]
    bm, faces = hexlathe(rings)
    hz = set()
    for j in range(1, 12, 2):
        for e in faces[0][j].edges:
            if abs(e.verts[0].co.z - e.verts[1].co.z) < 1e-6:
                hz.add(e)
    bmesh.ops.subdivide_edges(bm, edges=list(hz), cuts=3, use_grid_fill=True)
    dents = []
    for k in rng.sample(range(6), 3):
        th = math.radians(60 * k)
        t = rng.uniform(-0.35, 0.35)
        n = Vector((math.cos(th), math.sin(th), 0))
        c = n * A_K + Vector((-math.sin(th), math.cos(th), 0)) * t
        dents.append((c, n, rng.uniform(0.004, 0.009), rng.uniform(0.14, 0.24)))

    def dent(w):
        d = Vector((0, 0, 0))
        h = min(1.0, max(0.0, (w.z - Z_F) / (Z_KT - Z_F)))
        for c, n, depth, rad in dents:
            q = Vector((w.x - c.x, w.y - c.y, 0))
            if q.dot(n) < -0.05:
                continue
            d -= n * depth * math.exp(-(q.length / rad) ** 2) * h
        return d
    world_deform(bm, extra=dent)
    return A.add(bm, TEAMP, smooth=20, name="kick")


def body(A):
    """corner posts + recessed infill panels"""
    rings = [(A_W, B_W, Z_KT + 0.004), (A_W, B_W, Z_WT)]
    bm, faces = hexlathe(rings)
    sides = [faces[0][j] for j in range(12) if j % 2 == 1]
    bm.normal_update()
    res = bmesh.ops.inset_individual(bm, faces=sides, thickness=0.07, depth=0.0, use_even_offset=True)
    border = set(res["faces"])
    diag = [e for e in bm.edges if len(e.link_faces) == 2 and all(f in border for f in e.link_faces)]
    bmesh.ops.split_edges(bm, edges=diag)          # frame -> 4 strips (coplanar, so no shading seam)
    bm.normal_update()
    bmesh.ops.inset_individual(bm, faces=sides, thickness=0.004, depth=-0.014, use_even_offset=True)
    world_deform(bm)
    return A.add(bm, BODY, smooth=20, name="body")


def padeye(rh=0.021, w=0.035, h=0.12, t=0.02, n=8):
    """lifting padeye in local XZ (u = x outward from the wall at x=0, v = z up), thickness along y"""
    c, R = (w, h / 2), h / 2
    outer, inner = [], []
    for i in range(n):
        a = math.radians(-90 + 360 * i / n)
        ca, sa = math.cos(a), math.sin(a)
        inner.append((c[0] + rh * ca, c[1] + rh * sa))
        if ca >= -1e-6:
            outer.append((c[0] + R * ca, c[1] + R * sa))
        else:
            tt = c[0] / -ca
            v = c[1] + tt * sa
            if v > h:
                tt = (h - c[1]) / sa
            elif v < 0:
                tt = -c[1] / sa
            outer.append((c[0] + tt * ca, c[1] + tt * sa))
    bm = bmesh.new()
    Of = [bm.verts.new((u, -t / 2, v)) for u, v in outer]; Ob = [bm.verts.new((u, t / 2, v)) for u, v in outer]
    If = [bm.verts.new((u, -t / 2, v)) for u, v in inner]; Ib = [bm.verts.new((u, t / 2, v)) for u, v in inner]
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([Of[i], Of[j], If[j], If[i]])
        bm.faces.new([Ob[j], Ob[i], Ib[i], Ib[j]])
        bm.faces.new([Of[j], Of[i], Ob[i], Ob[j]])
        bm.faces.new([If[i], If[j], Ib[j], Ib[i]])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    return bm


def lugs(A, rng):
    """three lifting padeyes welded to alternate corner posts under the band"""
    for k in (1, 3, 5):
        ph = 60 * k + 30
        bm = padeye()
        x, y = rot2(B_W - 0.004, 0, ph)
        A.add(bm, WELD, at=(x, y, Z_WT - 0.165), rot=(0, 0, ph + rng.uniform(-1.5, 1.5)), smooth=40, name="lug", drop=("-x",))


def band_bolts(A, rng):
    for k in range(6):
        th = 60 * k
        for t in (-0.36, 0.36):
            x, y = rot2(A_B + 0.0045, t + rng.uniform(-0.01, 0.01), th)
            A.add(K.cyl(0.0135, 0.009, seg=6, axis="x", phase=0.0), BOLT, at=(x, y, (Z_WT + Z_D - T_D) / 2 + 0.004),
                  rot=(rng.uniform(0, 60), 0, th), smooth=20, name="bbolt", drop=("-x",))


def id_plate(A, rng):
    """blank brass maker's plate on the left-front panel (no text)"""
    th = -60
    xf = A_W - 0.014
    x, y = rot2(xf + 0.002, -0.30, th)
    A.add(K.box(0.004, 0.17, 0.10, drop=("-x",)), BRASS, at=(x, y, Z_WT - 0.16), rot=(0, 0, th), smooth=20, name="idplate")
    for t in (-0.07, 0.07):
        x, y = rot2(xf + 0.004 + 0.0015, -0.30 + t, th)
        A.add(K.cyl(0.0055, 0.003, seg=6, axis="x"), BRASS, at=(x, y, Z_WT - 0.16), rot=(0, 0, th), smooth=60,
              name="rivet", drop=("-x",))


def foot_weld(A):
    bm, _ = hexlathe([(A_K + 0.013, B_K + 0.013, Z_F), (A_K + 0.005, B_K + 0.005, Z_F + 0.008), (A_K - 0.002, B_K - 0.002, Z_F + 0.015)])
    world_deform(bm)
    A.add(bm, WELD, smooth=70, name="weld")


def corner_welds(A, rng):
    for k in range(6):
        ph = 60 * k + 30
        prof = [(-0.007, -0.002), (0.007, -0.002), (0.004, 0.003), (-0.004, 0.003)]
        r = B_W
        z0, z1 = Z_KT + 0.013, Z_WT - 0.002
        path = []
        for i in range(4):
            t = i / 3
            path.append((r, rng.uniform(-0.0015, 0.0015), z0 + (z1 - z0) * t))
        bm = K.sweep(path, prof, up=(1, 0, 0))
        bm.transform(Matrix.Rotation(math.radians(ph), 4, "Z"))
        world_deform(bm)
        A.add(bm, WELD, smooth=70, name="cweld")


def band(A):
    rings = [(A_W - 0.004, B_W - 0.004, Z_WT), (A_B - 0.007, B_B - 0.007, Z_WT), (A_B, B_B, Z_WT + 0.007),
             (A_B, B_B, Z_D - T_D)]
    bm, _ = hexlathe(rings)
    world_deform(bm)
    return A.add(bm, TEAMP, smooth=20, name="band")


def deck_segment(k, rng):
    """one of six tread plates (side 0 frame, rotated by 60k when added): returns (top, cut edges) bmeshes --
    the plate's flame-cut edges and the channel wall are plain steel, only the top carries the pattern"""
    th = math.radians(30)
    outer = [(B_D * math.cos(-th), B_D * math.sin(-th)), isect(-th, B_D, 0.0, A_D), isect(0.0, A_D, th, B_D),
             (B_D * math.cos(th), B_D * math.sin(th))]
    au, bu = A_B - 0.004, B_B - 0.004
    under = [(bu * math.cos(-th), bu * math.sin(-th)), isect(-th, bu, 0.0, au), isect(0.0, au, th, bu),
             (bu * math.cos(th), bu * math.sin(th))]
    n = SEG // 6
    arc = [(R_CO * math.cos(-th + 2 * th * i / n), R_CO * math.sin(-th + 2 * th * i / n)) for i in range(n + 1)]
    zt, zb, zd = Z_D, Z_D - T_D, Z_D - CH_DEPTH
    top = bmesh.new()
    T = [top.verts.new((x, y, zt)) for x, y in outer]
    Ar = [top.verts.new((x, y, zt)) for x, y in arc]
    top.faces.new(T + Ar[::-1])
    ed = bmesh.new()
    T = [ed.verts.new((x, y, zt)) for x, y in outer]
    Bo = [ed.verts.new((x, y, zb)) for x, y in outer]
    U = [ed.verts.new((x, y, zb)) for x, y in under]
    Ar = [ed.verts.new((x, y, zt)) for x, y in arc]
    Ad = [ed.verts.new((x, y, zd)) for x, y in arc]
    for i in range(3):
        ed.faces.new([Bo[i], Bo[i + 1], T[i + 1], T[i]])
        ed.faces.new([Bo[i], U[i], U[i + 1], Bo[i + 1]])
    for i in range(n):
        ed.faces.new([Ad[i + 1], Ad[i], Ar[i], Ar[i + 1]])
    # each plate sits a hair differently: +-1 mm tilt, 1.5 mm sag between the channel and the band
    tx, ty = rng.uniform(-0.002, 0.002), rng.uniform(-0.002, 0.002)

    def plate(w):
        r = math.hypot(w.x, w.y)
        t = min(1.0, max(0.0, (r - R_CO) / (A_D - R_CO)))
        return Vector((0, 0, -0.0015 * math.sin(math.pi * t) + tx * w.x * 0.5 + ty * w.y * 0.5 - 0.0005))
    world_deform(top, 60 * k, plate)
    world_deform(ed, 60 * k, plate)
    return top, ed


def deck(A, rng):
    for k in range(6):
        top, ed = deck_segment(k, rng)
        A.add(top, DECK, rot=(0, 0, 60 * k), smooth=20, name="deck", grain="x")
        A.add(ed, PLATE_EDGE, rot=(0, 0, 60 * k), smooth=20, name="deckedge")
    # radial butt welds between the plates (bead sunk 5 mm so it never floats over a sagging plate)
    prof = [(-0.0065, -0.005), (0.0065, -0.005), (0.0045, 0.0024), (-0.0045, 0.0024)]
    for k in range(6):
        ph = math.radians(60 * k + 30)
        path = []
        for i in range(3):
            r = (R_CO + 0.002) + (B_D - R_CO - 0.001) * i / 2
            path.append((r * math.cos(ph), r * math.sin(ph), Z_D + rng.uniform(-0.0006, 0.0004)))
        bm = K.sweep(path, prof, up=(0, 0, 1))
        world_deform(bm)
        A.add(bm, WELD, smooth=70, name="dweld")


def turntable(A, rng):
    prof = [(R_CI, Z_D - CH_DEPTH), (R_CI, Z_TT - 0.007), (R_CI - 0.008, Z_TT), (R_MAT - 0.014, Z_TT)]
    bm = rlathe(prof, SEG, chunks=6)
    tp = A.add(bm, TURN, smooth=20, name="turntable")
    # ribbed rubber seat mat the wheel sits on
    bm = rlathe([(R_MAT, Z_TT), (R_MAT, Z_TT + 0.006), (R_MAT - 0.007, Z_TT + 0.009), (0.0, Z_TT + 0.009)], 36)
    A.add(bm, MAT, smooth=20, name="mat")
    # bolt circle (machine bolts holding the plate to the frame)
    for i in range(12):
        a = math.radians(15 + 30 * i)
        r = 0.705
        A.add(K.cyl(0.0165, 0.010, seg=6, phase=0.0), BOLT, at=(r * math.cos(a), r * math.sin(a), Z_TT + 0.005),
              rot=(0, 0, rng.uniform(0, 60)), smooth=20, name="tbolt", drop=("-z",))
    # rubber chocks that centre the 1.2 m wheel
    for i in range(6):
        a = 60 * i
        bm = K.prism([(0, 0), (0.048, 0), (0.048, 0.023), (0.041, 0.030), (0.017, 0.030)], 0.13, plane="xz")
        x, y = rot2(0.607, 0, a)
        A.add(bm, RUBBER, at=(x, y, Z_TT), rot=(0, 0, a), smooth=20, name="chock", drop=("-z",))
    return tp


def light_ring(A):
    bm = rlathe([(R_CO, Z_GE), ((R_CI + R_CO) / 2, Z_GM), (R_CI, Z_GE)], SEG, chunks=6)
    A.add(bm, K.GLOW, smooth=60, name="glow")
    # retaining clips across the lens, ends buried in the channel walls
    prof = [(-0.011, -0.002), (0.011, -0.002), (0.011, 0.002), (-0.011, 0.002)]
    for i in range(12):
        a = math.radians(15 + 30 * i)
        path = []
        for r, z in ((R_CI - 0.004, Z_GE + 0.0025), ((R_CI + R_CO) / 2, Z_GM + 0.0025), (R_CO + 0.004, Z_GE + 0.0025)):
            path.append((r * math.cos(a), r * math.sin(a), z))
        A.add(K.sweep(path, prof, up=(0, 0, 1)), CLIP, smooth=30, name="clip")


def access_cover(A, rng):
    """bolted cover over the light-ring driver, centred on the FRONT panel"""
    xf = A_W - 0.013            # recessed panel face
    w, h, t = 0.62, 0.34, 0.010
    zc = (Z_KT + 0.013 + Z_WT) / 2 - 0.01
    bm = K.box(t, w, h, drop=("-x",))
    bm.normal_update()
    top = [f for f in bm.faces if f.normal.x > 0.9]
    bmesh.ops.inset_individual(bm, faces=top, thickness=0.009, depth=0.004, use_even_offset=True)
    A.add(bm, COVER, at=(xf + t / 2, 0.0, zc), smooth=20, name="cover")
    for yy in (-0.27, 0.0, 0.27):
        for zz in (-0.135, 0.135):
            A.add(K.cyl(0.0135, 0.009, seg=6, axis="x", phase=0.0), BOLT, at=(xf + t + 0.004 + 0.0045, yy, zc + zz),
                  rot=(rng.uniform(0, 60), 0, 0), smooth=20, name="cbolt", drop=("-x",))


def junction_box(A, rng):
    """galvanised junction box + rigid conduit feeding the light ring, on the BACK panel"""
    xf = -(A_W - 0.013)
    yb, zb = 0.30, 0.47
    d, w, h = 0.085, 0.20, 0.25
    A.add(K.box(d, w, h, drop=("+x", "-x")), GALV, at=(xf - d / 2, yb, zb), smooth=20, name="jbox")
    A.add(K.box(0.012, w + 0.014, h + 0.014, chamfer=0.003), GALV, at=(xf - d - 0.006, yb, zb), smooth=20, name="jlid")
    xc = xf - 0.047
    z0 = zb - h / 2
    A.add(K.cyl(0.024, 0.022, seg=6, phase=0.0), GALV, at=(xc, yb, z0 - 0.011), smooth=20, name="gland", drop=("+z",))
    A.rod((xc, yb, z0 - 0.02), (xc, yb, Z_F - 0.004), 0.0165, GALV, seg=8, smooth=50, name="conduit")
    A.add(K.cyl(0.026, 0.02, seg=6, phase=0.0), GALV, at=(xc, yb, Z_F + 0.01), smooth=20, name="gland2", drop=("-z",))


# ------------------------------------------------------------------ build
A = K.Asset("FlagPedestal", size=(2.9, 0.95, 2.9), tris=4000, tex=2048, pivot="none",
            note="Hex plinth: 2.90 m across corners on Y (W), 2.574 m across flats on X (D) -- inherent to a hexagon; "
                 "a flat faces FRONT +X. Pivot = hex centre at ground level. Deck top z=0.920, turntable seat z=0.927 "
                 "rubber seat mat top z=0.936 (flag cheese centre at z=1.146). Light ring in the Glow slot, perimeter band in TeamPaint.")
rng = random.Random(42)
base_flange(A)
anchors(A, rng)
gussets(A, rng)
kick_rail(A, rng)
body(A)
foot_weld(A)
corner_welds(A, rng)
band(A)
band_bolts(A, rng)
lugs(A, rng)
id_plate(A, rng)
deck(A, rng)
turntable(A, rng)
light_ring(A)
access_cover(A, rng)
junction_box(A, rng)

# collision: flange slab, body + deck hex prism, turntable disc
A.ucx_hull([(x, y, 0.0) for x, y in poly12(A_F + G_W, B_F + G_W)] + [(x, y, Z_F) for x, y in poly12(A_F, B_F)])
dk = poly12(A_D, B_D)
A.ucx_hull([(x, y, Z_F) for x, y in dk] + [(x, y, Z_D) for x, y in dk])
A.ucx_cyl((0, 0, (Z_D - 0.01 + Z_TT) / 2), R_CO, Z_TT - Z_D + 0.01, seg=12)
if os.environ.get("PED_VIEW"):     # draft helper: PED_VIEW="az,el[,w,h]" re-aims the draft camera
    v = [float(x) for x in os.environ["PED_VIEW"].split(",")]
    A.render_opts = dict(az=v[0], el=v[1], res=(int(v[2]), int(v[3])) if len(v) > 3 else (1280, 960))
ob = A.build()
if K.DRAFT and ob is not None and os.environ.get("PED_CLOSE"):   # draft helper: close-up "cx,cy,cz,size"
    import bpy
    c = [float(x) for x in os.environ["PED_CLOSE"].split(",")]
    bm = K.transform(K.box(c[3], c[3], c[3]), at=c[:3])
    me = bpy.data.meshes.new("_frame"); bm.to_mesh(me); bm.free()
    fr = bpy.data.objects.new("_frame", me); bpy.context.scene.collection.objects.link(fr)
    fr.hide_render = True
    A._render([fr], os.path.join(A.dir, "_draft_close.jpg"), draft=True)
