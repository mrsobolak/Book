# The six CheeseTeam classes: accessories built on the unchanged base body.
import math, bmesh
from mathutils import Vector, Matrix, Euler, noise
import acc as A
from acc import PI

SCALE = {'Outlaw': 1.0, 'MrShotgun': 1.0, 'RocketGuy': 1.0, 'Sniper': 1.07, 'Mechanic': 1.0, 'Heavy': 1.16}
EYE_L, EYE_R = Vector((0.087, A.FRONT_Y, 0.78)), Vector((-0.100, A.FRONT_Y, 0.775))   # character's left (+x) / right eye
MOUTH = Vector((-0.006, A.FRONT_Y, 0.680))


def hat_frame(T, fwd=0.0, side=0.0, lift=0.0, shift=(0, 0), pivot=(0, 0, 0)):
    """top-plane frame, moved along the plane, then tilted about a pivot (local): fwd > 0 dips the front (-y),
    side > 0 dips the +x side. Pivot at the crown's front edge keeps the front seated and lifts the back."""
    R = Matrix.Rotation(fwd, 4, 'X') @ Matrix.Rotation(side, 4, 'Y')
    pv = Vector(pivot)
    return T @ Matrix.Translation((shift[0], shift[1], lift)) @ Matrix.Translation(pv) @ R @ Matrix.Translation(-pv)


# ================================================================== 1. OUTLAW
def outlaw(P, T):
    obs = []
    felt = A.mat_felt('M_OutlawHat', '#0b0a0a', '#18161a', rough=0.68, fiber=0.3)
    band = A.mat_plain('M_OutlawBand', '#2a1c14', rough=0.45, col2='#3b281c', bump=0.12)
    silver = A.mat_metal('M_Concho', '#d9d6cf', rough=0.22)
    a, b = 0.100, 0.112
    H = hat_frame(T, fwd=math.radians(17), side=math.radians(8), lift=-0.004, shift=(0.012, -0.030), pivot=(0.03, -b, 0))
    hat = []
    a, b = 0.100, 0.112
    # crown: low, flat top, slight taper, rounded top edge, faint pinch at the front
    crown = [(0.0, -0.01), (1.0, -0.01), (1.0, 0.0), (0.994, 0.02), (0.982, 0.045), (0.97, 0.06), (0.955, 0.068),
             (0.93, 0.0735), (0.88, 0.0765), (0.6, 0.078), (0.0, 0.079)]
    pinch = lambda f, s: -0.004 * max(0.0, -math.sin(f)) ** 6 * (s > 0.5)
    bm = A.revolve(crown, a, b, n=72, closed=False, zfn=pinch)
    hat.append(A.make_obj('Outlaw_Crown', A.transform(bm, H), felt, 'spine_01'))
    # brim: wide and flat, thin, rounded lip with the faintest upturn at the edge
    ra, rb = 0.215 / a, 0.228 / b
    brim = [(0.9, 0.0035), (ra * 0.55, 0.0035), (ra * 0.9, 0.0033), (ra * 0.985, 0.0042), (ra * 1.0, 0.0012), (ra * 0.99, -0.0022),
            (ra * 0.9, -0.0034), (ra * 0.55, -0.0035), (0.9, -0.0035)]
    curl = lambda f, s: 0.004 * max(0.0, (s - ra * 0.8) / (ra * 0.2)) ** 2
    bm = A.revolve(brim, a, b * (rb / ra), n=96, closed=True, zfn=curl)
    brim_ob = A.make_obj('Outlaw_Brim', A.transform(bm, H), felt, 'spine_01'); hat.append(brim_ob)
    # hatband + three silver conchos down the left side
    hb = [(1.0, 0.002), (1.012, 0.002), (1.012, 0.019), (1.0, 0.019)]
    bm = A.revolve(hb, a, b, n=72, closed=True, zfn=pinch)
    hat.append(A.make_obj('Outlaw_Band', A.transform(bm, H), band, 'spine_01'))
    for k, f in enumerate((-0.35, 0.0, 0.35)):
        ang = -PI / 2 + 0.9 + f      # front-left quarter
        p = Vector((a * 1.013 * math.cos(ang), b * 1.013 * math.sin(ang), 0.0105))
        nrm = Vector((math.cos(ang) / a, math.sin(ang) / b, 0)).normalized()
        c = A.lathe([(1.0, 0.0), (0.95, 0.0012), (0.7, 0.0022), (0.3, 0.0027), (0.0, 0.0028)], 0.0058, 0.0058, n=20)
        z = nrm; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
        A.transform(c, A.frame_matrix(p, x, y, z))
        hat.append(A.make_obj('Outlaw_Concho%d' % k, A.transform(c, H), silver, 'spine_01'))
    print('outlaw hat settle', A.settle(P, hat, Vector(H.col[2][:3]), clear=0.003, check=[brim_ob]))
    obs += hat
    # pencil moustache: two hairline strokes with a parted middle, tips flicked down a touch
    hair = A.mat_hair('M_OutlawStache', '#18120e', '#3a2a20')
    for sgn in (-1, 1):
        pts = [Vector((MOUTH.x + sgn * (0.004 + 0.066 * t), A.FRONT_Y - 0.0022, MOUTH.z + 0.006 - 0.004 * t - 0.007 * t ** 3)) for t in [i / 14 for i in range(15)]]
        bm = A.tube(pts, lambda t: 0.0028 * (1 - 0.65 * t ** 1.5) + 0.0004, n=10, flat=1.45)
        obs.append(A.make_obj('Outlaw_Moustache%s' % ('L' if sgn > 0 else 'R'), bm, hair, 'spine_01'))
    # toothpick out of the left corner of the "mouth", pointing down and out
    wood = A.mat_plain('M_Toothpick', '#d6b27a', rough=0.7, col2='#b48a52', nscale=180, bump=0.1, bscale=900)
    p0 = Vector((MOUTH.x + 0.030, A.FRONT_Y + 0.006, MOUTH.z - 0.010))
    dirn = Vector((0.66, -0.55, -0.26)).normalized()
    pts = [p0 + dirn * 0.085 * (i / 14) + Vector((0, 0, -0.005 * (i / 14) ** 2)) for i in range(15)]
    bm = A.tube(pts, lambda t: 0.0005 + 0.0029 * math.sin(PI * min(1.0, 0.06 + t * 0.94)) ** 0.45, n=12)
    obs.append(A.make_obj('Outlaw_Toothpick', bm, wood, 'spine_01'))
    # red bandana tied round the right upper arm
    obs += bandana(P, 'upperarm_r')
    return obs


def bandana(P, bone):
    Mb, h, t = A.bone_frame(bone)
    d = (t - h).normalized(); c = h + (t - h) * 0.46
    up = Vector((0, -0.55, 0.84)); k = (up - d * up.dot(d)).normalized()     # knot faces front-up
    j = d.cross(k).normalized()
    cloth = A.mat_image('M_Bandana', 'bandana_paisley.png', rough=0.82, bump=0.25, scale=(3.0, 3.0, 1.0))
    obs = []
    # the wrap: a cloth band with soft folds, wider at the knot side
    R = []
    for si in range(9):
        s = (si / 8 - 0.5)
        ring = []
        for ii in range(40):
            f = 2 * PI * ii / 40
            dirr = k * math.cos(f) + j * math.sin(f)
            r = 0.0150 + 0.0020 * math.sin(5 * f + 1.3) * math.cos(PI * s) + 0.0016 * math.cos(f) ** 8
            w = 0.046 + 0.012 * math.cos(f) ** 2                      # band gets wider into the knot
            ring.append(c + d * s * w + dirr * r)
        R.append(ring)
    bm = A.rings(R, False, False)
    ob = A.make_obj('Bandana_Wrap', bm, cloth, bone, solid=0.0014)
    obs.append(ob)
    # knot
    kc = c + k * 0.0175
    bm = A.sphere(kc, 0.0115, 22, 14, (1.0, 1.0, 1.0))
    def lump(v):
        q = v - kc
        n = noise.noise(q * 200.0) * 0.0024
        return kc + Matrix.Rotation(0.3, 3, 'Z') @ Vector((q.x * 1.25, q.y * 1.0, q.z * 0.85)) + q.normalized() * n
    A.displace(bm, lump)
    obs.append(A.make_obj('Bandana_Knot', bm, cloth, bone))
    # two tails, falling with gravity and fanning out
    for sgn, L, sway in ((1, 0.085, 0.35), (-1, 0.068, -0.25)):
        start = kc + k * 0.005 + d * 0.005 * sgn
        dirv = (Vector((0, 0, -1)) * 0.75 + k * 0.45 + d * sgn * 0.35 + j * sway * 0.3).normalized()
        pts = []
        for i in range(12):
            tt = i / 11
            wob = j * 0.004 * math.sin(tt * 5 + sgn) + d * 0.003 * math.sin(tt * 3)
            pts.append(start + dirv * L * tt + Vector((0, 0, -0.012 * tt * tt)) + wob)
        nf = lambda tt, tan, sgn=sgn: (k * 0.7 + d * 0.3 * sgn + j * 0.2).normalized()
        bm = A.ribbon(pts, lambda tt: 0.024 * (1 - tt) ** 0.8 + 0.005, nf)
        obs.append(A.make_obj('Bandana_Tail%d' % (0 if sgn > 0 else 1), bm, cloth, bone, solid=0.0012))
    for ob in obs:
        A.uv_cylinder(ob)
    return obs


BUILDERS = {'Outlaw': outlaw}


# ================================================================== helpers shared by several classes
import bpy, random


def face_point(P, x, z, off=0.0015):
    """point on the front of the body at (x, z) (follows eyes, dents) pushed `off` toward the viewer"""
    loc, nor = P.hit((x, -1.0, z), (0, 1, 0))
    if loc is None:
        return Vector((x, A.FRONT_Y - off, z)), Vector((0, -1, 0))
    return loc + Vector((0, -off, 0)), nor


def hair_tufts(P, name, mat, seeds, rng, bone='spine_01'):
    """many tapered, curving tufts merged into one object; seeds = [(root, direction, length, radius)]"""
    import bmesh
    acc_bm = bmesh.new()
    for (root, dirn, L, r) in seeds:
        curl = Vector((rng.uniform(-1, 1), rng.uniform(-0.6, 0.2), rng.uniform(-1, 0.3))) * 0.25
        pts = [root + (dirn + curl * (i / 6) ** 2).normalized() * L * (i / 6) for i in range(7)]
        tb = A.tube(pts, lambda t, r=r: r * (1 - t) ** 0.9 + 0.0006, n=7, flat=0.75)
        tmp = bpy.data.meshes.new('tmp'); tb.to_mesh(tmp); tb.free(); acc_bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    return A.make_obj(name, acc_bm, mat, bone)


def clumps(P, name, mat, specs, follow_face=None, bone='spine_01'):
    """cartoon hair: each spec (root, dir, length, radius, curl, flat) -> a tapered, curving, pointed clump; all merged.
    follow_face: keep every clump point at least this far in front of the body (no clipping into the cheese)."""
    bm_all = bmesh.new()
    for (root, d, L, r, curl, flat) in specs:
        pts = []
        for i in range(11):
            t = i / 10
            p = root + (d + curl * t * t).normalized() * L * t
            if follow_face is not None and t > 0.15:
                loc, nor = P.hit((p.x, -1.0, p.z), (0, 1, 0))
                if loc is not None and p.y > loc.y - follow_face - r * flat * (1 - t) ** 0.8:
                    p.y = loc.y - follow_face - r * flat * (1 - t) ** 0.8
            pts.append(p)
        tb = A.tube(pts, lambda t, r=r: r * min(1.0, 0.45 + 2.75 * t) * (1 - t) ** 0.7 * 1.15 + 0.0004,
                    n=12, flat=flat, up=Vector((0, -1, 0)))
        tmp = bpy.data.meshes.new('tmp'); tb.to_mesh(tmp); tb.free(); bm_all.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    return A.make_obj(name, bm_all, mat, bone, subsurf=1)


def shotgun_shell(P, name, base_pt, axis, hull, brass, prim, depth=0.6, L=0.064, R=0.0130):
    """12-gauge style shell: red ribbed hull with crimp, brass head with rim + primer. base_pt on the surface,
    axis pointing OUT of the cheese; the shell is pushed in by depth*L."""
    z = axis.normalized(); x = z.cross(Vector((0, 0, 1)))
    if x.length < 1e-3:
        x = z.cross(Vector((1, 0, 0)))
    x.normalize(); y = z.cross(x)
    M = A.frame_matrix(base_pt - z * depth * L, x, y, z)       # local z=0 = crimp end (inside), z=L = brass head
    obs = []
    ribs = lambda k, t, px, py, pz: (px * (1 + 0.035 * math.cos(t * 2 * PI * 16)), py * (1 + 0.035 * math.cos(t * 2 * PI * 16)), pz)
    prof = [(0.55, 0.0), (0.85, 0.002), (0.97, 0.006), (1.0, 0.012), (1.0, L - 0.016), (1.0, L - 0.0145)]
    bm = A.lathe(prof, R, R, n=48, cap_top=False, shape=ribs)
    obs.append(A.make_obj(name + '_Hull', A.transform(bm, M), hull, 'spine_01'))
    prof = [(0.99, L - 0.016), (1.02, L - 0.016), (1.03, L - 0.004), (1.12, L - 0.0035), (1.13, L - 0.001), (1.1, L), (0.5, L + 0.0002), (0.0, L + 0.0002)]
    bm = A.lathe(prof, R, R, n=48)
    obs.append(A.make_obj(name + '_Head', A.transform(bm, M), brass, 'spine_01'))
    bm = A.lathe([(1.0, L), (1.0, L + 0.0008), (0.7, L + 0.0012), (0.0, L + 0.0013)], R * 0.3, R * 0.3, n=20)
    obs.append(A.make_obj(name + '_Primer', A.transform(bm, M), prim, 'spine_01'))
    return obs


# ================================================================== 2. MR. SHOTGUN
def mrshotgun(P, T):
    import bmesh
    obs = []
    rng = random.Random(7)
    foam = A.mat_felt('M_TruckerFront', '#efe8da', '#ddd3c2', rough=0.7, fiber=0.25)
    mesh = A.mat_image('M_TruckerMesh', 'trucker_mesh.png', rough=0.8, bump=0.0, tint='#c8342b')
    strap = A.mat_plain('M_Snapback', '#2b2a2a', rough=0.45, bump=0.02)
    stud = A.mat_plain('M_SnapStud', '#ece7df', rough=0.3, bump=0.0)
    a, b = 0.214, 0.166
    H = hat_frame(T, fwd=math.radians(7), side=math.radians(3), lift=-0.030, shift=(-0.004, -0.004), pivot=(0, 0, 0))
    H = H @ Matrix.Rotation(PI, 4, 'Z')                 # turned round: local -y (cap front) points to the character's back
    prof = [(1.0, 0.0), (0.995, 0.035), (0.975, 0.070), (0.93, 0.103), (0.85, 0.132), (0.72, 0.155), (0.54, 0.170), (0.30, 0.178), (0.0, 0.180)]
    def raise_front(k, t, x, y, z):                     # trucker: tall, flatter front panel
        f = max(0.0, -y / b) ** 2.0
        return (x, y * (1.0 + 0.04 * f), z * (1.0 + 0.10 * f))
    bm = A.lathe(prof, a, b, e=2.6, n=72, cap_bottom=False, shape=raise_front)
    dele = [f for f in bm.faces if f.calc_center_median().z < 0.034 and abs(math.atan2(f.calc_center_median().y, f.calc_center_median().x) - PI / 2) < 0.33]
    bmesh.ops.delete(bm, geom=dele, context='FACES')     # snapback opening (faces the character's front)
    bml = bm.copy()                                     # dark sweatband / lining so the inside never shows the red foam
    A.transform(bml, Matrix.Diagonal((0.975, 0.975, 0.975, 1.0)))
    bm2 = bm.copy()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y > -0.035], context='FACES')
    bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if f.calc_center_median().y <= -0.035], context='FACES')
    cap = [A.make_obj('Shotgun_CapFoam', A.transform(bm, H), foam, 'spine_01', solid=0.004),
           A.make_obj('Shotgun_CapMesh', A.transform(bm2, H), mesh, 'spine_01', solid=0.004)]
    A.uv_box(cap[1], 30.0)
    cap.append(A.make_obj('Shotgun_CapLining', A.transform(bml, H), A.mat_plain('M_CapLining', '#1d1b1a', rough=0.85, bump=0.02), 'spine_01', solid=0.002))
    billm = A.mat_felt('M_TruckerBill', '#b3302a', '#9a2822', rough=0.65, fiber=0.2)
    seam = A.mat_plain('M_TruckerSeam', '#d9cfbd', rough=0.6, bump=0.0)
    for k in range(6):
        ang = k / 6 * 2 * PI + PI / 6
        pts = []
        for (s, z) in prof[1:-1]:
            fz = max(0.0, -(b * s * math.sin(ang)) / b) ** 2.0
            pts.append(Vector((a * s * math.cos(ang) * 1.002, b * s * math.sin(ang) * (1 + 0.04 * fz) * 1.002, z * (1 + 0.10 * fz) + 0.0035)))
        bm = A.tube(pts, 0.0014, n=6)
        cap.append(A.make_obj('Shotgun_Seam%d' % k, A.transform(bm, H), seam, 'spine_01'))
    bm = A.lathe([(1.0, 0.0), (1.0, 0.004), (0.7, 0.0075), (0.0, 0.0085)], 0.011, 0.011, n=24)
    A.transform(bm, Matrix.Translation((0, 0, 0.180)))
    cap.append(A.make_obj('Shotgun_Button', A.transform(bm, H), foam, 'spine_01'))
    verts = []; faces = []
    nu, nv = 16, 8
    for i in range(nu + 1):
        u = i / nu * 2 - 1
        for j in range(nv + 1):
            v = j / nv
            bx = u * (a * 0.86) * (1 - 0.18 * v ** 2)
            by = -(b * 0.96) * math.sqrt(max(0.0, 1 - (bx / a) ** 2)) - v * 0.125 * (1 - 0.55 * u * u)
            bz = 0.006 - 0.022 * u * u - 0.014 * v * v
            verts.append(Vector((bx, by, bz)))
    for i in range(nu):
        for j in range(nv):
            q = i * (nv + 1) + j
            faces.append((q, q + nv + 1, q + nv + 2, q + 1))
    cap.append(A.make_obj('Shotgun_Bill', A.transform(A.bm_from(verts, faces), H), billm, 'spine_01', solid=0.007))
    sp = [Vector((a * 0.985 * math.cos(PI / 2 - 0.40 + 0.80 * i / 16), b * 0.985 * math.sin(PI / 2 - 0.40 + 0.80 * i / 16), 0.012)) for i in range(17)]
    bm = A.ribbon(sp, 0.016, lambda t, tan: Vector((sp[min(16, int(t * 16))].x / a, sp[min(16, int(t * 16))].y / b, 0)).normalized())
    cap.append(A.make_obj('Shotgun_Strap', A.transform(bm, H), strap, 'spine_01', solid=0.003))
    for k in range(5):
        ang = PI / 2 - 0.30 + 0.15 * k
        p = Vector((a * math.cos(ang), b * math.sin(ang), 0.012))
        nrm = Vector((math.cos(ang) / a, math.sin(ang) / b, 0)).normalized()
        st = A.lathe([(1.0, 0.0), (1.0, 0.0012), (0.6, 0.0022), (0.0, 0.0025)], 0.0032, 0.0032, n=14)
        xx = Vector((0, 0, 1)).cross(nrm).normalized(); yy = nrm.cross(xx)
        A.transform(st, A.frame_matrix(p, xx, yy, nrm))
        cap.append(A.make_obj('Shotgun_Stud%d' % k, A.transform(st, H), stud, 'spine_01'))
    print('shotgun cap fit', A.fit_hat(P, cap, cap[:3] + [o for o in cap if o.name == 'Shotgun_Bill'], H.col[3][:3], H.col[0][:3], H.col[1][:3], H.col[2][:3]))
    print('shotgun cap drape', A.drape(P, cap, cap[:3] + [o for o in cap if o.name == 'Shotgun_Bill'], H.col[2][:3]))
    obs += cap
    # hair: smooth, chunky cartoon clumps (matches the toon body; no stringy strands)
    hair = A.mat_plain('M_ShotgunHair', '#5e3b21', rough=0.55, col2='#432914', nscale=55, bump=0.04, bscale=180)
    # angry eyebrows: thick tapered clumps riding on the googly eyes, inner ends dropped low
    for (eye, sgn) in ((EYE_R, -1), (EYE_L, 1)):
        specs = []
        for j, (t0, L, r, up) in enumerate(((0.00, 0.082, 0.0200, 0.34), (0.16, 0.080, 0.0215, 0.46), (0.34, 0.072, 0.0195, 0.56), (0.52, 0.058, 0.0160, 0.66))):
            x0 = eye.x - sgn * 0.062 + sgn * 0.110 * t0
            z0 = eye.z + 0.030 + 0.075 * t0
            root, _ = face_point(P, x0, z0, 0.005)
            d = Vector((sgn * 1.0, -0.12, up * 0.9)).normalized()
            specs.append((root, d, L, r, Vector((0, 0, -0.10)), 0.55))
        obs.append(clumps(P, 'Shotgun_Brow%s' % ('L' if sgn > 0 else 'R'), hair, specs, follow_face=0.005))
    # big bushy mutton chops: one soft domed mass per side (narrow at the temple, wide over the jaw corner, tufted
    # lower edge), plus a few loose 3D tufts on the tips so the silhouette is hairy, not a flat sticker
    chop_ol = [(0.196, 0.868), (0.199, 0.800), (0.199, 0.720), (0.198, 0.650), (0.191, 0.598), (0.174, 0.627), (0.157, 0.590),
               (0.139, 0.623), (0.119, 0.597), (0.105, 0.630), (0.083, 0.626), (0.098, 0.655), (0.126, 0.676), (0.150, 0.700),
               (0.171, 0.734), (0.177, 0.780), (0.176, 0.825), (0.181, 0.868)]
    tips = [(0.191, 0.598), (0.157, 0.590), (0.119, 0.597), (0.083, 0.626)]
    for sgn in (-1, 1):
        ol = [(sgn * x, z) for (x, z) in chop_ol]
        if sgn < 0:
            ol.reverse()
        obs.append(A.puff('Shotgun_Chop%s' % ('L' if sgn > 0 else 'R'), P, ol, 0.024, hair, edge=0.026))
        specs = []
        for (x, z) in tips:
            root, _ = face_point(P, sgn * (x + 0.012 * (1 if x > 0.12 else -0.5)), z + 0.030, 0.004)
            d = Vector((sgn * (x - 0.15) * 4.0, -0.25, -1.0)).normalized()
            specs.append((root, d, 0.040, 0.0105, Vector((-sgn * 0.3, -0.1, 0.1)), 0.6))
        obs.append(clumps(P, 'Shotgun_ChopTufts%s' % ('L' if sgn > 0 else 'R'), hair, specs, follow_face=0.003))
    # shotgun shells pushed into the cheese holes, like a bandolier
    hull = A.mat_plain('M_ShellHull', '#b4231f', rough=0.38, col2='#8f1915', nscale=60, bump=0.05)
    brass = A.mat_metal('M_ShellBrass', '#d9a441', rough=0.28)
    prim = A.mat_metal('M_ShellPrimer', '#c9c2b6', rough=0.3)
    # front: the centre hole (the jaw-corner holes are under the mutton chops), tipped so the red hull shows
    for k, ((hx, hz), ax) in enumerate((((0.039, 0.649), Vector((-0.40, -0.80, 0.45))),)):
        obs += shotgun_shell(P, 'Shotgun_Shell%d' % k, Vector((hx, A.FRONT_Y, hz)), ax.normalized(), hull, brass, prim, depth=0.18)
    # -x side face: a row of three, like a bandolier
    for k, (y, z, ax) in enumerate(((-0.098, 0.643, Vector((-1, -0.25, 0.25))), (-0.072, 0.776, Vector((-1, -0.15, 0.40))), (0.066, 0.795, Vector((-1, 0.1, 0.35))))):
        loc, nor = P.hit((-1.0, y, z), (1, 0, 0))
        obs += shotgun_shell(P, 'Shotgun_ShellS%d' % k, Vector((loc.x if loc is not None else -0.19, y, z)), ax.normalized(), hull, brass, prim, depth=0.2)
    return obs


BUILDERS['MrShotgun'] = mrshotgun
