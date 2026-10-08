"""SM_VaultDoor_Open + SM_VaultDoorFrame -- round bank-vault door (shown open, standing on its own) and its
frame ring, for the Wash Junction cheese depot.

Door  (W x H x D = 3.7 x 3.7 x 0.7): disc axis along X, outer face +X, modelled around the disc centre.
      Stepped sealing edge (4 rings), 16 radial locking bolts, 3-spoke handwheel on a hub, blank combination
      dial, hinge arms + hinge blocks + hollow hinge barrel on -Y (outboard of the disc), bolt-throw linkage
      on the inner face (-X).
Frame (4.7 x 4.7 x 0.5): ring 4.7 outer / 4.0 bore, stepped bore with a seal counterbore, 16 bolt
      receivers (two hidden under the threshold are left solid), hinge pocket + hinge brackets + hinge pin on
      -Y, front mounting flange with anchor bolts, saddle foot with gussets, tread-plate threshold.

Both share the hinge pin line: vertical axis at (x = +0.15, y = -2.00) from the disc / ring centre.
"""
import sys, os, math, random
sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "kit"))
import assetkit as K
import bmesh, bpy, types
from mathutils import Vector, Matrix

# kit/pack.py runs under system python with kit/ first on sys.path, where kit/inspect.py shadows the stdlib
# `inspect` that numpy imports -> the texture pack step dies.  PYTHONSAFEPATH (py >= 3.11) keeps the script dir
# off sys.path for that subprocess.  (Reported as a kit request; nothing in kit/ is touched.)
os.environ["PYTHONSAFEPATH"] = "1"

PIN_X, PIN_Y = 0.15, -2.00          # hinge pin axis (door and frame modelling space)
BOLT_X = -0.05                      # locking-bolt plane (door) == receiver plane (frame)
BOLT_ANG = [11.25 + 22.5 * k for k in range(16)]


# ----------------------------------------------------------------------------- helpers
def lathe2(profile, seg, keep=None, closed=False, axis="z", phase=0.0):
    """Revolve a profile [(r, z)] that runs counter-clockwise in (r right, z up) so normals face out.
    keep: set of segment indices to build (segment k joins point k and k+1). closed: join last -> first.
    r == 0 makes a fan.  Built without recalc so partial shells keep the right orientation."""
    bm = bmesh.new()
    rings = []
    for r, z in profile:
        if r < 1e-9:
            rings.append([bm.verts.new((0.0, 0.0, z))])
        else:
            rings.append([bm.verts.new((r * math.cos(phase + 2 * math.pi * i / seg),
                                        r * math.sin(phase + 2 * math.pi * i / seg), z)) for i in range(seg)])
    n = len(profile)
    for k in range(n if closed else n - 1):
        if keep is not None and k not in keep:
            continue
        A, B = rings[k], rings[(k + 1) % n]
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
    loose = [v for v in bm.verts if not v.link_faces]
    if loose:
        bmesh.ops.delete(bm, geom=loose, context="VERTS")
    K._axis(bm, axis)
    return bm


def radial(theta_deg, x=0.0):
    """Matrix taking local +Z onto the radial direction theta (deg) in the YZ plane, origin on the X axis at x."""
    th = math.radians(theta_deg)
    return Matrix.Translation((x, 0, 0)) @ Matrix.Rotation(th - math.pi / 2, 4, "X")


def yz(r, theta_deg):
    th = math.radians(theta_deg)
    return r * math.cos(th), r * math.sin(th)


def wobble(seed, amp, rmax):
    """Low-frequency out-of-round / out-of-flat for big turned parts (axis along X)."""
    rr = random.Random(seed)
    ph = [rr.uniform(0, 6.283) for _ in range(6)]

    def f(v):
        r = math.hypot(v.y, v.z)
        if r < 1e-6:
            return v
        th = math.atan2(v.z, v.y)
        dr = amp * (0.6 * math.sin(2 * th + ph[0]) + 0.4 * math.sin(5 * th + ph[1])) * min(1.0, r / rmax)
        dx = amp * 0.6 * math.sin(3 * th + ph[2]) * (r / rmax) ** 2
        k = (r + dr) / r
        return Vector((v.x + dx, v.y * k, v.z * k))
    return f


def dents(spots):
    """spots: [(Vector centre, radius, depth, Vector push_dir)] -- local impact dents."""
    def f(v):
        out = v.copy()
        for c, rad, dep, d in spots:
            dist = (v - c).length
            if dist < rad:
                out += d * (dep * (1 - (dist / rad) ** 2) ** 2)
        return out
    return f


def polar_unwrap(A, prof, closed, segs, mats, lseg, lphase, per=8, tol=0.012, breaks=()):
    """Replace this asset's UV unwrap: run the kit's smart-project, then re-map the faces of the big turned body
    (profile `prof` revolved around X through the modelling origin) as sector strips -- u = arc length, v = distance
    along the profile -- and re-pack everything with averaged island scale.  Flat annuli otherwise become ring
    islands with empty middles (25-45 % UV coverage).  `breaks`: segment indices that start a new island.
    lseg / lphase: the lathe's segment count and phase; sectors are `per` lathe columns wide (straight island ends)."""
    base = K.Asset._unwrap

    def _unwrap(self, ob):
        base(self, ob)
        me = ob.data
        sh = self.shift
        P = [(r, x + sh.x) for r, x in prof]
        n = len(P)
        L = {k: math.hypot(P[(k + 1) % n][0] - P[k][0], P[(k + 1) % n][1] - P[k][1]) for k in segs}
        cum, acc = {}, 0.0
        for k in sorted(segs):
            if k in breaks:
                acc += 0.5
            cum[k] = acc
            acc += L[k]
        names = {m.name for m in mats}
        midx = {i for i, m in enumerate(me.materials) if m.name in names}
        bm = bmesh.new()
        bm.from_mesh(me)
        uvl = bm.loops.layers.uv.active
        bm.normal_update()
        cy, cz = sh.y, sh.z
        col_w = 2 * math.pi / lseg
        ph0 = lphase - math.pi / 2          # lathe angle a -> final YZ angle a - 90 deg (axis "x")
        nsec = lseg // per

        def proj(pr, px, k):
            a, b = P[k], P[(k + 1) % n]
            dr, dx = b[0] - a[0], b[1] - a[1]
            t = max(0.0, min(1.0, ((pr - a[0]) * dr + (px - a[1]) * dx) / (dr * dr + dx * dx)))
            return t, math.hypot(pr - a[0] - t * dr, px - a[1] - t * dx)

        vinfo = {}

        def vert_info(v):
            if v.index not in vinfo:
                pr, px = math.hypot(v.co.y - cy, v.co.z - cz), v.co.x
                best = min(segs, key=lambda k: proj(pr, px, k)[1])
                vinfo[v.index] = (pr, px, best)
            return vinfo[v.index]

        def linked(j, k):
            return j == k or (abs(j - k) == 1 and max(j, k) not in breaks)

        bm.verts.index_update()
        done = 0
        for f in bm.faces:
            if f.material_index not in midx:
                continue
            infos = [vert_info(v) for v in f.verts]
            best = None
            for k in segs:
                d = max(proj(pr, px, k)[1] for pr, px, _ in infos)
                if d < tol and (best is None or d < best[1]):
                    best = (k, d)
            if best is None:
                continue
            k = best[0]
            a, b = P[k], P[(k + 1) % n]
            nr, nx = b[1] - a[1], -(b[0] - a[0])
            ln = math.hypot(nr, nx)
            c = f.calc_center_median()
            th = math.atan2(c.z - cz, c.y - cy)
            expect = Vector((nx / ln, nr / ln * math.cos(th), nr / ln * math.sin(th)))
            if f.normal.dot(expect) < 0.9:
                continue
            col = int(((th - ph0) % (2 * math.pi)) / col_w) % lseg
            sec = col // per
            thc = ph0 + (sec * per + per / 2.0) * col_w
            for lo, (pr, px, j) in zip(f.loops, infos):
                kk = j if linked(j, k) else k
                t = proj(pr, px, kk)[0]
                v = lo.vert.co
                dth = (math.atan2(v.z - cz, v.y - cy) - thc + math.pi) % (2 * math.pi) - math.pi
                lo[uvl].uv = (10.0 + sec * 4.0 + dth * pr, 10.0 + cum[kk] + t * L[kk])
            done += 1
        for f in bm.faces:
            for lo in f.loops:
                lo[uvl].select = True
                lo[uvl].select_edge = True
        bm.to_mesh(me)
        bm.free()
        print("[vault] polar-mapped %d faces of %s" % (done, self.sm))
        K._select([ob], ob)
        bpy.ops.object.mode_set(mode="EDIT")
        bpy.ops.mesh.select_all(action="SELECT")
        margin = 6.0 / self.tex
        bpy.ops.uv.average_islands_scale()
        bpy.ops.uv.pack_islands(rotate=True, margin_method="SCALED", margin=margin, shape_method="CONCAVE")
        bpy.ops.object.mode_set(mode="OBJECT")
        dump = K._arg("--uvdump")
        if dump:       # debug: UV triangles for an external plot
            import numpy as np
            me.calc_loop_triangles()
            uv = me.uv_layers.active.data
            arr = np.array([[uv[l].uv[:] for l in t.loops] for t in me.loop_triangles], np.float32)
            mi = np.array([t.material_index for t in me.loop_triangles], np.int32)
            np.savez(os.path.join(dump, "uv_%s.npz" % self.name), uv=arr, mat=mi)
    A._unwrap = types.MethodType(_unwrap, A)


def slot_by_segment(A, part, seg, mapping):
    """Give the faces of a lathe2() part (face order = profile segment order) their own material slots.
    mapping: {segment index: K.mat}; unmapped segments keep the part's material."""
    me = part.ob.data
    slots = {me.materials[0].name: 0}
    for k, m in mapping.items():
        mt = A._mat(m)
        if mt.name not in slots:
            me.materials.append(mt)
            slots[mt.name] = len(me.materials) - 1
    for p in me.polygons:
        m = mapping.get(p.index // seg)
        if m is not None:
            p.material_index = slots[A._mat(m).name]


def draft_view(A):
    """Draft-only camera override for checking other sides:  -- --draft --az 144 --el 22"""
    az = K._arg("--az")
    if az is not None:
        A.render_opts = dict(az=float(az), el=float(K._arg("--el", "17")))
    if K._arg("--res") is not None:
        w = int(K._arg("--res"))
        A.render_opts = dict(getattr(A, "render_opts", {}), res=(w, w * 3 // 4))


# ----------------------------------------------------------------------------- materials (specs only)
# door
D_FACE = K.mat("steel", color="#a0a3a6", rough=0.34, worn=0.9, rust=0.2, grime=0.6, dust=0.35, streaks=0.45,
               splash=0.25, splash_h=0.3)
D_RING = K.mat("steel", color="#a8abae", rough=0.3, worn=1.0, rust=0.18, grime=0.8, dust=0.35, streaks=0.35,
               splash=0.25, splash_h=0.3)
D_EDGE = K.mat("steel", color="#9a9da0", rough=0.28, worn=1.0, rust=0.3, grime=1.0, dust=0.45, streaks=0.25,
               splash=0.25, splash_h=0.3)
D_BACK = K.mat("steel", color="#6f7275", rough=0.46, worn=0.8, rust=0.4, grime=0.8, dust=0.25, streaks=0.35,
               splash=0.25, splash_h=0.3)
GASKET = K.mat("rubber", color="#1f1e1c", dust=0.3)
LOCKBOLT = K.mat("steel", color="#aeb0b2", rough=0.22, worn=1.0, rust=0.12, grime=0.7, dust=0.3, streaks=0.1,
                 splash=0.2, splash_h=0.3)
WHEEL = K.mat("chrome", color="#bdbcb6", dust=0.45)
HUB = K.mat("steel", color="#8a8d90", rough=0.28, worn=1.0, rust=0.15, grime=0.8, dust=0.3)
DIAL_RING = K.mat("brass", tarnish=0.75)
DIAL = K.mat("steel", color="#3c3e40", rough=0.42, worn=0.9, rust=0.1, grime=0.6, dust=0.2)
HINGE = K.mat("iron", color="#57534e", rough=0.58, worn=0.8, rust=0.5, grime=0.85, dust=0.4)
PLATE = K.mat("brass", color="#a88a4a", tarnish=0.85, dust=0.3)
ARM = K.mat("steel", color="#55585b", rough=0.48, worn=0.9, rust=0.45, grime=0.8, dust=0.4, streaks=0.4)
FAST = K.mat("steel", color="#4a4c4e", rough=0.5, worn=0.9, rust=0.5, grime=0.7, dust=0.3)
COVER = K.mat("paint", color="#4f5a4c", under="steel", chips=0.55, flake=0.1, fade=0.3, rough=0.55, scratch=0.6,
              grime=0.75, dust=0.2, streaks=0.3, splash=0.0)
LINK = K.mat("steel", color="#75787b", rough=0.34, worn=1.0, rust=0.3, grime=0.85, dust=0.2)
# frame
F_PAINT = K.mat("paint", color="#4f5a4c", under="rust", chips=0.6, flake=0.25, fade=0.45, rough=0.6, scratch=0.5,
                grime=0.75, dust=0.45, streaks=0.5, splash=0.5, splash_h=0.55)
F_BORE = K.mat("steel", color="#8a8d90", rough=0.32, worn=1.0, rust=0.4, grime=1.0, dust=0.5, streaks=0.25,
               splash=0.35, splash_h=0.55)
F_RECV = K.mat("brass", color="#a07c3e", tarnish=0.9, grime=0.9)
F_IRON = K.mat("iron", color="#57534e", rough=0.58, worn=0.8, rust=0.55, grime=0.85, dust=0.45)
F_BOLT = K.mat("steel", color="#4a4c4e", rough=0.55, worn=0.85, rust=0.65, grime=0.7, dust=0.4)
F_TREAD = K.mat("diamond", rust=0.35, worn=0.9, dust=0.55, grime=0.6, splash=0.3, splash_h=0.55)
F_BASE = K.mat("paint", color="#465044", under="rust", chips=0.75, flake=0.35, fade=0.3, rough=0.65, scratch=0.4,
               grime=0.8, dust=0.3, streaks=0.4, splash=0.45, splash_h=0.4)


# ============================================================================= DOOR
# profile (r, x), counter-clockwise: back centre -> back face -> stepped edge -> front face -> boss
DOOR_PROF = [
    (0.0, -0.29),     # 0  back centre
    (1.61, -0.29),    # 1  seg0  back face (fan)
    (1.64, -0.26),    # 2  seg1  back chamfer
    (1.64, -0.22),    # 3  seg2  step ring 4
    (1.70, -0.22),    # 4  seg3  step face
    (1.70, -0.15),    # 5  seg4  step ring 3
    (1.76, -0.15),    # 6  seg5  step face (gasket)
    (1.76, 0.05),     # 7  seg6  step ring 2 (bolt band)
    (1.82, 0.05),     # 8  seg7  step face
    (1.82, 0.135),    # 9  seg8  step ring 1
    (1.785, 0.178),   # 10 seg9  outer chamfer
    (1.47, 0.178),    # 11 seg10 raised face ring
    (1.43, 0.145),    # 12 seg11 face ring inner chamfer
    (1.03, 0.145),    # 13 seg12 main face (outer zone)
    (1.00, 0.17),     # 14 seg13 lock plate chamfer
    (0.40, 0.17),     # 15 seg14 lock plate
    (0.37, 0.195),    # 16 seg15 boss chamfer
    (0.0, 0.195),     # 17 seg16 boss (fan)
]
DSEG = 64
XB = -0.29          # inner face plane
ARM_Z = 0.66        # hinge arm height (+/-)


def build_door():
    A = K.Asset("VaultDoor_Open", size=(3.7, 3.7, 0.7), tris=8000, tex=2048, pivot="bottom",
                note="Round vault door shown open, standing on its own (rests on its two lowest locking bolts). "
                     "Outer face +X. Hinge barrel/blocks sit outboard of the disc on -Y, so bbox Y is ~9% over (deliberate). "
                     "Hinge pin axis (vertical) at x=+0.15, y=-2.00 from the disc centre.")
    if A.skip:
        A.build()
        return
    draft_view(A)
    polar_unwrap(A, DOOR_PROF, False, list(range(1, 16)), [D_FACE, D_RING, D_EDGE, GASKET], DSEG, math.radians(2.8),
                 per=8, tol=0.012, breaks=(12,))
    rng = random.Random(41)
    wob = wobble(3, 0.003, 1.8)
    dn = dents([(Vector((0.12, 1.80 * math.cos(math.radians(a)), 1.80 * math.sin(math.radians(a)))), 0.25, 0.01,
                 -Vector((0, math.cos(math.radians(a)), math.sin(math.radians(a))))) for a in (63, 147, 238, 322)])

    bm = lathe2(DOOR_PROF, DSEG, axis="x", phase=math.radians(2.8))      # closed: fans at both ends
    K.deform(bm, wob)
    K.deform(bm, dn)
    body = A.add(bm, D_EDGE, smooth=30, name="door_body")
    slot_by_segment(A, body, DSEG, {0: D_BACK, 5: GASKET, 9: D_RING, 10: D_RING, 11: D_RING, 12: D_FACE,
                                    13: D_RING, 14: D_RING, 15: D_RING, 16: D_RING})

    # ---- 16 locking bolts: collar + shaft + chamfered nose, radial from the bolt band (r 1.76)
    for th in BOLT_ANG:
        prof = [(0.0, 1.70), (0.096, 1.70), (0.096, 1.79), (0.08, 1.805), (0.08, 1.94), (0.056, 1.97), (0.0, 1.97)]
        bm = lathe2(prof, 10, keep={1, 2, 3, 4, 5}, axis="z", phase=rng.uniform(0, 1))
        A.add(bm, LOCKBOLT, M=radial(th, BOLT_X), smooth=40, name="lockbolt")

    # ---- face fasteners: 24 hex bolts on the raised face ring
    for k in range(24):
        y, z = yz(1.625, 7.5 + 15 * k)
        A.add(K.cyl(0.034, 0.028, seg=6, axis="x", phase=rng.uniform(0, 1)), FAST, at=(0.178 + 0.011, y, z),
              smooth=20, drop=("-x",), name="facebolt")

    # ---- lock-plate bolts and a blank brass maker's plate below the wheel
    for k in range(12):
        y, z = yz(0.92, 15 + 30 * k)
        A.add(K.cyl(0.03, 0.026, seg=6, axis="x", phase=rng.uniform(0, 1)), FAST, at=(0.17 + 0.01, y, z),
              smooth=20, drop=("-x",), name="platebolt")
    A.add(K.box(0.012, 0.46, 0.15, chamfer=0.004, drop=("-x",)), PLATE, at=(0.145 + 0.005, 0, -1.215), smooth=20,
          name="makerplate")
    for y in (-0.2, 0.2):
        for z in (-1.165, -1.265):
            A.add(K.cyl(0.011, 0.008, seg=6, axis="x"), PLATE, at=(0.156 + 0.003, y, z), smooth=50, drop=("-x",),
                  name="rivet")

    # ---- handwheel: hub, 3 spokes, rim, grips
    hub = lathe2([(0.21, 0.19), (0.21, 0.212), (0.15, 0.23), (0.14, 0.24), (0.14, 0.315), (0.118, 0.33),
                  (0.08, 0.33), (0.08, 0.346), (0.064, 0.356), (0.0, 0.356)], 20, axis="x")
    A.add(hub, HUB, smooth=30, name="hub")
    WX = 0.285
    for s in range(3):
        a = 7.0 + 270 + 120 * s
        cy, cz = math.cos(math.radians(a)), math.sin(math.radians(a))
        path = [(0.31, 0.10 * cy, 0.10 * cz), (0.298, 0.36 * cy, 0.36 * cz), (WX, 0.66 * cy, 0.66 * cz)]
        prof = [(0.04 * math.cos(2 * math.pi * i / 8), 0.026 * math.sin(2 * math.pi * i / 8)) for i in range(8)]
        A.add(K.sweep(path, prof, cap=False, up=(1, 0, 0), scale=[1.35, 1.05, 0.85]), WHEEL, smooth=60, name="spoke")
        grip = lathe2([(0.0, 0.632), (0.04, 0.643), (0.055, 0.672), (0.058, 0.712), (0.047, 0.752), (0.0, 0.768)], 8,
                      axis="z")
        A.add(grip, WHEEL, M=radial(a, WX), smooth=60, name="grip")
    A.add(K.torus(0.56, 0.04, seg=36, rseg=8, axis="x"), WHEEL, at=(WX, 0, 0), smooth=60, name="rim")

    # ---- combination dial (blank) above the wheel
    DZ = 1.215
    A.add(lathe2([(0.172, 0.14), (0.172, 0.158), (0.156, 0.17), (0.118, 0.17)], 20, axis="x"), DIAL_RING,
          at=(0, 0, DZ), smooth=30, name="dialring")
    A.add(lathe2([(0.113, 0.16), (0.113, 0.205), (0.102, 0.214), (0.064, 0.217), (0.055, 0.24), (0.038, 0.246),
                  (0.0, 0.246)], 20, axis="x"), DIAL, at=(0, 0, DZ), smooth=30, name="dial")

    # ---- hinge: two tapered arms bolted across the face, hinge blocks, hollow barrel on the pin line
    hinge_parts = []
    for zc in (ARM_Z, -ARM_Z):
        pts = [(PIN_Y, -0.17), (-1.25, -0.12), (-0.98, -0.10), (-0.91, -0.06), (-0.91, 0.06), (-0.98, 0.10),
               (-1.25, 0.12), (PIN_Y, 0.17)]
        arm = A.add(K.prism(pts, 0.15, plane="yz"), ARM, at=(0.21, 0, zc), smooth=20, name="arm")
        hb = A.add(K.box(0.27, 0.29, 0.40, chamfer=0.02), HINGE, at=(PIN_X, PIN_Y + 0.02, zc), smooth=20, name="hblock")
        hinge_parts.append((arm, hb))
        for yb in (-1.05, -1.3, -1.55):
            A.add(K.cyl(0.03, 0.026, seg=6, axis="x", phase=rng.uniform(0, 1)), FAST, at=(0.285 + 0.01, yb, zc),
                  smooth=20, drop=("-x",), name="armbolt")
    barrel = lathe2([(0.0, -1.0), (0.062, -1.0), (0.062, -1.04), (0.118, -1.04), (0.118, 1.04), (0.062, 1.04),
                     (0.062, 1.0), (0.0, 1.0)], 16, axis="z")
    bar = A.add(barrel, HINGE, at=(PIN_X, PIN_Y, 0), smooth=30, name="barrel")

    # ---- inner face (-X): bolt-throw linkage, bolt carriers, cover plate
    for th in BOLT_ANG:
        p0 = Vector(yz(0.48, th - 16)); p1 = Vector(yz(1.33, th))
        d = p1 - p0
        phi = math.degrees(math.atan2(d.y, d.x))
        mid = (p0 + p1) / 2
        A.add(K.box(0.027, d.length + 0.06, 0.07, drop=("+x",)), LINK, at=(XB - 0.0115, mid.x, mid.y),
              rot=(phi, 0, 0), smooth=20, name="linkbar")
        cy, cz = yz(1.50, th)
        A.add(K.box(0.05, 0.20, 0.13, drop=("+x",)), LINK, at=(XB - 0.023, cy, cz), rot=(th, 0, 0), smooth=20,
              name="carrier")
        A.add(K.cyl(0.03, 0.024, seg=6, axis="x", phase=rng.uniform(0, 1)), FAST, at=(XB - 0.046 - 0.010, *yz(1.52, th)),
              smooth=20, drop=("+x",), name="carrierbolt")
        A.add(K.cyl(0.03, 0.02, seg=6, axis="x", phase=rng.uniform(0, 1)), FAST, at=(XB - 0.026 - 0.009, p1.x, p1.y),
              smooth=20, drop=("+x",), name="linkpin")
    A.add(K.cyl(0.62, 0.024, seg=8, axis="x", phase=math.pi / 8), COVER, at=(XB - 0.046, 0, 0), smooth=20, name="cover")
    for k in range(8):
        y, z = yz(0.54, 7.5 + 45 * k)
        A.add(K.cyl(0.024, 0.036, seg=6, axis="x", caps=False), FAST, at=(XB - 0.018, y, z), smooth=20, name="standoff")
        A.add(K.cyl(0.024, 0.016, seg=6, axis="x", phase=rng.uniform(0, 1)), FAST, at=(XB - 0.058 - 0.008, y, z),
              smooth=20, drop=("+x",), name="coverbolt")
    A.add(lathe2([(0.0, -0.375), (0.07, -0.375), (0.085, -0.368), (0.085, -0.36), (0.20, -0.36), (0.225, -0.345)],
                 16, axis="x"), LINK, smooth=30, name="camboss")

    # ---- collision
    A.ucx_cyl((-0.05, 0, 0), 1.84, 0.48, seg=16, axis="x")
    A.ucx_cyl((BOLT_X, 0, 0), 1.975, 0.18, seg=16, axis="x")
    A.ucx_cyl((-0.33, 0, 0), 1.6, 0.09, seg=16, axis="x")
    A.ucx_cyl((0.27, 0, 0), 0.77, 0.17, seg=12, axis="x")
    A.ucx_cyl((0.2, 0, DZ), 0.172, 0.1, seg=8, axis="x")
    A.ucx_parts(bar, hinge_parts[0][1], hinge_parts[1][1])
    for arm, _ in hinge_parts:
        A.ucx_parts(arm)
    A.build()


# ============================================================================= FRAME
# ring cross-section (r, x), counter-clockwise, closed
FRAME_PROF = [
    (2.00, 0.07),     # 0  bore (down)
    (2.00, -0.22),    # 1  bore back chamfer
    (2.025, -0.24),   # 2  back face
    (2.20, -0.24),    # 3  back outer chamfer
    (2.24, -0.20),    # 4  body outer
    (2.24, 0.07),     # 5  flange back face
    (2.35, 0.07),     # 6  flange rim
    (2.35, 0.105),    # 7  flange front chamfer
    (2.33, 0.125),    # 8  painted flange face
    (2.17, 0.125),    # 9  step up to the steel seal ring
    (2.17, 0.15),     # 10 seal ring face
    (2.075, 0.15),    # 11 lip chamfer
    (2.05, 0.125),    # 12 counterbore
    (2.05, 0.07),     # 13 step face -> back to 0
]
FSEG = 44


def build_frame():
    A = K.Asset("VaultDoorFrame", size=(4.7, 4.7, 0.5), tris=3000, tex=2048, pivot="bottom",
                note="Vault door frame ring, bore axis along X, front (hinge side) +X. Walk-through bore 4.0 m with "
                     "a flat tread-plate threshold. Hinge pin axis (vertical) at x=+0.15, y=-2.00 from the ring centre.")
    if A.skip:
        A.build()
        return
    draft_view(A)
    polar_unwrap(A, FRAME_PROF, True, list(range(len(FRAME_PROF))), [F_PAINT, F_BORE], FSEG, math.radians(3.75),
                 per=4, tol=0.01)
    rng = random.Random(77)
    ring_bm = lathe2(FRAME_PROF, FSEG, closed=True, axis="x", phase=math.radians(3.75))
    K.deform(ring_bm, wobble(9, 0.003, 2.3))
    ring = A.add(ring_bm, F_PAINT, smooth=30, name="ring")
    # machined bore / counterbore / seal ring get the bore material (2nd slot inside the same closed part)
    me = ring.ob.data
    me.materials.append(A._mat(F_BORE))
    for p in me.polygons:
        c = p.center
        if math.hypot(c.y, c.z) < 2.175:
            p.material_index = 1
    # 16 receivers (the two under the threshold stay solid)
    for th in BOLT_ANG:
        if abs(((th + 90) % 360) - 0) < 30 or abs(((th + 90) % 360) - 360) < 30:
            continue
        c = A.cutter(K.cyl(0.084, 0.25, seg=8, axis="z"), F_RECV, M=radial(th, BOLT_X) @ Matrix.Translation((0, 0, 2.0)),
                     smooth=40)
        A.cut(ring, c)
    # hinge pocket for the door barrel
    A.cut(ring, A.cutter(K.box(0.2, 0.25, 2.1), F_BORE, at=(0.035 + 0.1, PIN_Y, 0), smooth=30))

    # front flange anchor bolts
    for k in range(24):
        th = 7.5 + 15 * k
        if 140 < th < 220 or 250 < th < 290:
            continue
        y, z = yz(2.25, th)
        A.add(K.cyl(0.036, 0.03, seg=6, axis="x", phase=rng.uniform(0, 1)), F_BOLT, at=(0.125 + 0.012, y, z),
              smooth=20, drop=("-x",), name="anchor")

    # stiffener gussets welded between the front flange and the ring body, plus back-face bolts
    for th in (0, 45, 90, 135, 180, 225, 315):
        rib = K.prism([(-0.17, 2.232), (0.068, 2.232), (0.068, 2.343), (0.035, 2.343)], 0.032, plane="xz")
        A.add(rib, F_PAINT, M=radial(th, 0.0), smooth=20, name="rib", drop=("-z",))
    for k in range(8):
        y, z = yz(2.115, 22.5 + 45 * k)
        A.add(K.cyl(0.032, 0.02, seg=6, axis="x", phase=rng.uniform(0, 1)), F_BOLT, at=(-0.24 - 0.006, y, z),
              smooth=20, drop=("+x",), name="backbolt")

    # hinge brackets + knuckles + pin
    for sgn in (1, -1):
        zc = sgn * 1.20
        A.add(K.box(0.13, 0.40, 0.30, chamfer=0.015), F_IRON, at=(0.18, -1.89, zc), smooth=20, name="bracket")
        A.add(K.cyl(0.10, 0.30, seg=14), F_IRON, at=(PIN_X, PIN_Y, zc), smooth=30, name="knuckle")
        for yb, dz in ((-1.76, -0.075), (-1.76, 0.075)):
            A.add(K.cyl(0.032, 0.02, seg=6, axis="x", phase=rng.uniform(0, 1)), F_BOLT,
                  at=(0.245 + 0.006, yb, zc + dz), smooth=20, drop=("-x",), name="brbolt")
        A.add(K.cyl(0.068, 0.035, seg=6, phase=rng.uniform(0, 1)), F_BOLT, at=(PIN_X, PIN_Y, sgn * (1.35 + 0.0175)),
              smooth=20, name="pinnut")
    A.add(K.cyl(0.06, 2.80, seg=10), F_BOLT, at=(PIN_X, PIN_Y, 0), smooth=40, name="pin")

    # threshold: steel block filling the bore bottom + tread plate on top (walkable, flat)
    TZ = -1.90
    blk = K.prism([(-0.70, TZ), (-0.30, -2.035), (0.30, -2.035), (0.70, TZ)], 0.383, plane="yz")
    A.add(blk, F_BORE, at=(-0.0435, 0, 0), smooth=20, name="threshold", drop=("+z",))
    A.add(K.box(0.383, 1.40, 0.014, drop=("-z",)), F_TREAD, at=(-0.0435, 0, TZ + 0.007), smooth=20, name="tread")

    # cradle foot: base plate, front cradle plate on the flange, rear gussets, anchor bolts
    ZG = -2.35
    A.add(K.box(0.50, 2.0, 0.05, drop=("-z",)), F_BASE, at=(0.0, 0, ZG + 0.025), smooth=20, name="baseplate")

    def ring_z(y, R):
        return -math.sqrt(R * R - y * y)
    cr = [(-1.0, ZG + 0.05), (1.0, ZG + 0.05), (1.0, ZG + 0.12)] + \
         [(y, ring_z(y, 2.27)) for y in (0.82, 0.55, 0.28, 0.0, -0.28, -0.55, -0.82)] + [(-1.0, ZG + 0.12)]
    A.add(K.prism(cr, 0.04, plane="yz"), F_BASE, at=(0.125 + 0.02 - 0.005, 0, 0), smooth=20, name="cradle")
    for xg in (-0.215, -0.07):
        pts = [(-0.95, ZG + 0.05), (0.95, ZG + 0.05), (0.95, ZG + 0.1), (0.72, ring_z(0.72, 2.22)),
               (0.36, ring_z(0.36, 2.22)), (0.0, ring_z(0.0, 2.22)), (-0.36, ring_z(-0.36, 2.22)),
               (-0.72, ring_z(-0.72, 2.22)), (-0.95, ZG + 0.1)]
        A.add(K.prism(pts, 0.03, plane="yz"), F_BASE, at=(xg, 0, 0), smooth=20, name="gusset")
    for xb in (-0.16, 0.21):
        for yb in (-0.88, 0.88):
            A.add(K.cyl(0.032, 0.03, seg=6, phase=rng.uniform(0, 1)), F_BOLT, at=(xb, yb, ZG + 0.05 + 0.013),
                  smooth=20, drop=("-z",), name="footbolt")

    # ---- collision: flat walkable bottom piece + ring of convex sectors
    bot = []
    for x in (-0.24, 0.15):
        bot += [(x, -0.70, TZ + 0.014), (x, 0.70, TZ + 0.014), (x, -0.83, -2.20), (x, 0.83, -2.20)]
    for x in (-0.25, 0.25):
        bot += [(x, -1.0, ZG), (x, 1.0, ZG), (x, -1.0, ZG + 0.05), (x, 1.0, ZG + 0.05)]
    A.ucx_hull(bot)
    a0, a1 = -69.5, 249.5
    n = 14
    for i in range(n):
        t0 = a0 + (a1 - a0) * i / n
        t1 = a0 + (a1 - a0) * (i + 1) / n
        half = math.radians((t1 - t0) / 2)
        pts = []
        for t in (t0, t1):
            yi, zi = yz(2.0, t)
            yo, zo = yz(2.35 / math.cos(half), t)
            yb_, zb_ = yz(2.24 / math.cos(half), t)
            pts += [(-0.24, yi, zi), (0.15, yi, zi), (0.07, yo, zo), (0.15, yo, zo), (-0.24, yb_, zb_)]
        A.ucx_hull(pts)
    for sg in (1, -1):
        A.ucx_hull([(x, y, sg * z) for x in (0.05, 0.26) for y in (-2.11, -1.68) for z in (1.04, 1.39)])
    A.ucx_box((PIN_X + 0.01, PIN_Y, 0), (0.12, 0.12, 2.1))
    A.build()


build_door()
build_frame()
