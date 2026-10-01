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
    # lower edge, combed strand grooves)
    chop_ol = [(0.194, 0.868), (0.196, 0.800), (0.196, 0.720), (0.195, 0.650), (0.189, 0.598), (0.174, 0.627), (0.157, 0.590),
               (0.139, 0.623), (0.119, 0.597), (0.105, 0.630), (0.083, 0.626), (0.098, 0.655), (0.126, 0.676), (0.150, 0.700),
               (0.171, 0.734), (0.177, 0.780), (0.176, 0.825), (0.181, 0.868)]
    for sgn in (-1, 1):
        ol = [(sgn * x, z) for (x, z) in chop_ol]
        if sgn < 0:
            ol.reverse()
        obs.append(A.puff('Shotgun_Chop%s' % ('L' if sgn > 0 else 'R'), P, ol, 0.026, hair, edge=0.028, groove=0.0035, groove_slant=-0.35 * sgn))
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


# ================================================================== 3. ROCKET GUY
def mat_helmet(name, col, stripe, uvname='Local', s0=0.040, s1=0.016):
    """glossy clear-coated paint, two racing stripes (from the shell's own x stored in a UV layer), scuffs"""
    m, nt, bs = A._mat(name)
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = uvname
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs[0], sep.inputs[0])
    def math_node(op, a, b=None):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op
        if isinstance(a, float): n.inputs[0].default_value = a
        else: nt.links.new(a, n.inputs[0])
        if b is not None:
            if isinstance(b, float): n.inputs[1].default_value = b
            else: nt.links.new(b, n.inputs[1])
        return n.outputs[0]
    d = math_node('ABSOLUTE', math_node('SUBTRACT', math_node('ABSOLUTE', sep.outputs[0]), s0))
    mask = math_node('LESS_THAN', d, s1)
    vec = A._tc(nt)
    wear = A._noise(nt, vec, 35, 6, 0.65)
    base = A._ramp(nt, wear.outputs['Fac'], A.srgb(col), A.srgb(col), 0.4, 0.8)
    base.color_ramp.elements[0].color = (*[c * 0.86 for c in A.srgb(col)], 1)
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(mask, mix.inputs['Factor']); nt.links.new(base.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = (*A.srgb(stripe), 1)
    nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (1.0, 1.0, 40.0)
    nt.links.new(vec, mp.inputs['Vector'])
    scr = A._noise(nt, mp.outputs['Vector'], 40, 10, 0.75)
    rr = A._ramp(nt, scr.outputs['Fac'], (0.22, 0.22, 0.22), (0.55, 0.55, 0.55), 0.55, 0.72)
    sepc = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(rr.outputs['Color'], sepc.inputs[0])
    nt.links.new(sepc.outputs[0], bs.inputs['Roughness'])
    try:
        bs.inputs['Coat Weight'].default_value = 0.8
        nt.links.new(sepc.outputs[0], bs.inputs['Coat Roughness'])
    except KeyError:
        pass
    A._bump(nt, bs, scr.outputs['Fac'], 0.04, 0.0004)
    return m


def mat_lens(name, col):
    """tinted goggle lens: glossy, with scratches in the roughness and a faint bump"""
    m, nt, bs = A._mat(name)
    bs.inputs['Base Color'].default_value = (*A.srgb(col), 1)
    bs.inputs['Metallic'].default_value = 0.35
    vec = A._tc(nt)
    sc1 = A._noise(nt, vec, 260, 12, 0.8)
    mp = nt.nodes.new('ShaderNodeMapping'); mp.inputs['Scale'].default_value = (90.0, 1.0, 4.0)
    mp.inputs['Rotation'].default_value = (0.0, 0.7, 0.4)
    nt.links.new(vec, mp.inputs['Vector'])
    sc2 = A._noise(nt, mp.outputs['Vector'], 6, 12, 0.85)
    mx = nt.nodes.new('ShaderNodeMath'); mx.operation = 'MAXIMUM'
    nt.links.new(sc1.outputs['Fac'], mx.inputs[0]); nt.links.new(sc2.outputs['Fac'], mx.inputs[1])
    rr = A._ramp(nt, mx.outputs[0], (0.03, 0.03, 0.03), (0.5, 0.5, 0.5), 0.68, 0.72)
    sepc = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(rr.outputs['Color'], sepc.inputs[0])
    nt.links.new(sepc.outputs[0], bs.inputs['Roughness'])
    try:
        bs.inputs['Coat Weight'].default_value = 1.0
        bs.inputs['Coat Roughness'].default_value = 0.03
    except KeyError:
        pass
    A._bump(nt, bs, mx.outputs[0], 0.015, 0.0002)
    return m


def wristband(P, bone, leather, chrome, t=0.55, side=''):
    """thick leather cuff around the stick forearm with two rows of chrome pyramid-ish spikes and stitched edges"""
    M, head, tail = A.bone_frame(bone)
    ax = (tail - head).normalized()
    c = head + (tail - head) * t
    x = ax.orthogonal().normalized(); y = ax.cross(x)
    F = A.frame_matrix(c, x, y, ax)
    obs = []
    h, ri, ro = 0.026, 0.0105, 0.0255
    sec = [(ri, -h), (ro - 0.003, -h), (ro - 0.0005, -h + 0.0012), (ro, -h + 0.004), (ro + 0.0006, 0.0), (ro, h - 0.004),
           (ro - 0.0005, h - 0.0012), (ro - 0.003, h), (ri, h)]
    bm = A.revolve(sec, 1.0, 1.0, n=40)
    obs.append(A.make_obj('Rocket_Cuff%s' % side, A.transform(bm, F), leather, bone))
    stitch = A.mat_plain('M_CuffStitch', '#cfc3a6', rough=0.7, bump=0.0)
    for zz in (-h + 0.0050, h - 0.0050):
        for k in range(20):                                   # dashed stitch line
            f0 = 2 * PI * k / 20; f1 = f0 + 2 * PI / 20 * 0.55
            pts = [Vector(((ro + 0.0004) * math.cos(f0 + (f1 - f0) * i / 3), (ro + 0.0004) * math.sin(f0 + (f1 - f0) * i / 3), zz)) for i in range(4)]
            bm = A.tube(pts, 0.00065, n=5)
            obs.append(A.make_obj('Rocket_CuffStitch%s_%d_%d' % (side, int(zz > 0), k), A.transform(bm, F), stitch, bone))
    for row, zz in enumerate((-0.0105, 0.0105)):
        for k in range(7):
            f = 2 * PI * (k + 0.5 * row) / 7
            r_dir = Vector((math.cos(f), math.sin(f), 0))
            t_dir = Vector((-math.sin(f), math.cos(f), 0))
            S = A.frame_matrix(Vector((0, 0, zz)) + r_dir * (ro - 0.0005), t_dir, Vector((0, 0, 1)), r_dir)
            sp = A.lathe([(1.0, 0.0), (1.0, 0.0012), (0.92, 0.0018), (0.55, 0.0088), (0.14, 0.0158), (0.0, 0.0166)],
                         0.0072, 0.0072, e=2.0, n=16)            # rivet base + cone with a blunted tip
            A.transform(sp, S)
            obs.append(A.make_obj('Rocket_Spike%s_%d_%d' % (side, row, k), A.transform(sp, F), chrome, bone))
    return obs


def rocketguy(P, T):
    obs = []
    paint = mat_helmet('M_HelmetPaint', '#efe6d2', '#1b1a1a')
    lining = A.mat_plain('M_HelmetLining', '#24201d', rough=0.85, col2='#151311', nscale=200, bump=0.15, bscale=600)
    rubber = A.mat_plain('M_HelmetTrim', '#161515', rough=0.55, bump=0.03)
    chrome = A.mat_metal('M_Chrome', '#e8e8ea', rough=0.12, scratches=0.4)
    a, b = 0.252, 0.188
    H = hat_frame(T, fwd=math.radians(-2), side=math.radians(-11), lift=0.0, shift=(0.004, 0.004))
    prof0 = [(1.0, -0.080), (1.0, -0.040), (0.997, 0.0), (0.965, 0.034), (0.90, 0.064), (0.80, 0.090), (0.665, 0.109),
             (0.49, 0.121), (0.27, 0.128), (0.0, 0.130)]
    prof = []                                                  # Catmull-Rom resample: dense, smooth rings
    P0 = [prof0[0]] + prof0 + [prof0[-1]]
    for k in range(1, len(P0) - 2):
        p0, p1, p2, p3 = [Vector(p) for p in P0[k - 1:k + 3]]
        m = max(2, int((p2 - p1).length / 0.005))
        for i in range(m):
            t = i / m
            q = 0.5 * ((2 * p1) + (-p0 + p2) * t + (2 * p0 - 5 * p1 + 4 * p2 - p3) * t * t + (-p0 + 3 * p1 - 3 * p2 + p3) * t ** 3)
            prof.append((q.x, q.y))
    prof.append(prof0[-1])
    shell = A.lathe(prof, a, b, e=4.0, n=128, cap_bottom=False)
    def cut_z(fx, fy):                       # opening: brow edge high at the front, cheek guards, low at the back
        th = math.degrees(abs(math.atan2(fx / a, -fy / b)))      # 0 = straight ahead, 180 = back
        if th < 50:
            return -0.016 + 0.006 * (th / 50) ** 2
        if th < 80:
            u = (th - 50) / 30
            return -0.010 - 0.062 * (3 * u * u - 2 * u ** 3)
        return -0.072 + 0.008 * min(1.0, (th - 80) / 60)
    dele = []
    for f in shell.faces:
        c = f.calc_center_median()
        if c.z < cut_z(c.x, c.y):
            dele.append(f)
    bmesh.ops.delete(shell, geom=dele, context='FACES')
    bmesh.ops.delete(shell, geom=[v for v in shell.verts if not v.link_faces], context='VERTS')
    for v in shell.verts:                    # snap the stair-stepped opening onto the cut curve
        if v.is_boundary and v.co.z < 0.02:
            v.co.z = max(v.co.z - 0.006, cut_z(v.co.x, v.co.y))
    loops = A.boundary_loops(shell)
    lin = shell.copy()
    A.transform(lin, Matrix.Diagonal((0.978, 0.97, 0.975, 1.0)) @ Matrix.Translation((0, 0, -0.002)))
    A.local_uv(shell)
    helm = [A.make_obj('Rocket_HelmetShell', A.transform(shell, H), paint, 'spine_01', solid=0.007)]
    helm.append(A.make_obj('Rocket_HelmetLining', A.transform(lin, H), lining, 'spine_01', solid=0.006))
    # rubber edge trim along the opening
    for i, lp in enumerate(loops):
        if len(lp) < 8:
            continue
        pts = lp + [lp[0]]
        bm = A.tube(pts, 0.0062, n=10, cap=False, flat=1.3, up=Vector((0, 0, 1)))
        helm.append(A.make_obj('Rocket_HelmetTrim%d' % i, A.transform(bm, H), rubber, 'spine_01'))
    # three chrome visor snaps across the brow
    sbvh = A.bvh_of(A.lathe(prof, a * 1.0, b * 1.0, e=4.0, n=128, cap_bottom=False))
    for k, sx in enumerate((-0.085, 0.0, 0.085)):
        loc, nor, idx, d = sbvh.ray_cast(Vector((sx, -1.0, 0.004)), Vector((0, 1, 0)))
        if loc is None:
            continue
        nor = nor if nor.y < 0 else -nor
        xx = Vector((0, 0, 1)).cross(nor).normalized(); yy = nor.cross(xx)
        bm = A.lathe([(1.0, 0.0), (1.0, 0.0012), (0.75, 0.0032), (0.0, 0.0038)], 0.0068, 0.0068, n=20)
        A.transform(bm, A.frame_matrix(loc + nor * 0.0035, xx, yy, nor))
        helm.append(A.make_obj('Rocket_Snap%d' % k, A.transform(bm, H), chrome, 'spine_01'))
    # goggles resting on the front of the dome
    rubber_g = A.mat_plain('M_GoggleRubber', '#2a2522', rough=0.6, bump=0.06, bscale=500)
    lens = mat_lens('M_GoggleLens', '#5e3810')
    strap = A.mat_plain('M_GoggleStrap', '#3c3a37', rough=0.75, col2='#2a2826', nscale=300, bump=0.12, bscale=900)
    gz = 0.058
    gr = 1.42                                 # goggle size factor
    centers = []
    for sx in (-0.074, 0.074):
        loc, nor, idx, d = sbvh.ray_cast(Vector((sx, -1.0, gz)), Vector((0, 1, 0)))
        nor = nor if nor.y < 0 else -nor
        nor = (nor + Vector((0, -0.25, 0.0))).normalized()
        centers.append((loc, nor))
        xx = Vector((0, 0, 1)).cross(nor).normalized(); yy = nor.cross(xx)
        G = A.frame_matrix(loc + nor * 0.004, xx, yy, nor)
        cup = A.lathe([(0.86, -0.004), (1.0, 0.0), (1.06, 0.006), (1.05, 0.014), (0.98, 0.019), (0.9, 0.020)], 0.033 * gr, 0.030 * gr, n=48,
                      cap_bottom=True, cap_top=False)
        helm.append(A.make_obj('Rocket_GoggleCup%d' % len(centers), A.transform(A.transform(cup, G), H), rubber_g, 'spine_01'))
        ring = A.revolve([(0.86, 0.017), (0.98, 0.017), (1.0, 0.0205), (0.97, 0.0235), (0.86, 0.0225)], 0.033 * gr, 0.030 * gr, n=56)
        helm.append(A.make_obj('Rocket_GoggleRim%d' % len(centers), A.transform(A.transform(ring, G), H), chrome, 'spine_01'))
        ln = A.lathe([(1.0, 0.0), (0.96, 0.0035), (0.75, 0.0058), (0.0, 0.0066)], 0.0285 * gr, 0.0258 * gr, n=56)
        A.transform(ln, Matrix.Translation((0, 0, 0.0168)))
        helm.append(A.make_obj('Rocket_GoggleLens%d' % len(centers), A.transform(A.transform(ln, G), H), lens, 'spine_01'))
    (l0, n0), (l1, n1) = centers
    p0 = l0 + n0 * 0.014 + Vector((0.030 * gr, 0, 0)); p1 = l1 + n1 * 0.014 - Vector((0.030 * gr, 0, 0))
    mid = (p0 + p1) / 2 + (n0 + n1).normalized() * 0.006
    bm = A.tube([p0, (p0 + mid) / 2 + Vector((0, -0.002, 0)), mid, (p1 + mid) / 2 + Vector((0, -0.002, 0)), p1], 0.0042, n=10, flat=0.7)
    helm.append(A.make_obj('Rocket_GoggleBridge', A.transform(bm, H), rubber_g, 'spine_01'))
    # strap: around the dome from one cup to the other, round the back, hugging the paint
    spts = []; snor = []
    for i in range(41):
        f = -PI / 2 + math.radians(38) + (2 * PI - math.radians(76)) * i / 40
        dvec = Vector((math.cos(f), math.sin(f), 0.0))
        zz = gz - 0.012 + 0.010 * math.sin(f + PI / 2) ** 2
        loc, nor, idx, d = sbvh.ray_cast(Vector((0, 0, zz)) + dvec * 1.0, -dvec)
        if loc is not None:
            nn = nor.normalized() * (1 if nor.dot(dvec) > 0 else -1)
            spts.append(loc + nn * 0.0048); snor.append(nn)
    bm = A.ribbon(spts, lambda t: 0.026, lambda t, tan: snor[min(len(snor) - 1, int(round(t * (len(snor) - 1))))], thick=0.0)
    helm.append(A.make_obj('Rocket_GoggleStrap', A.transform(bm, H), strap, 'spine_01', solid=0.0022))
    print('rocket helmet fit', A.fit_hat(P, helm, helm[:2], H.col[3][:3], H.col[0][:3], H.col[1][:3], H.col[2][:3], rng_deg=6.0, near=0.5))
    obs += helm
    # big band-aid over the centre hole, like it's covering a wound; one corner peeling up
    tan = A.mat_image('M_Bandaid', 'bandaid.png', rough=0.6, bump=0.05)
    L, W = 0.185, 0.062
    ang = math.radians(20)
    cx, cz = 0.048, 0.636
    ud = Vector((math.cos(ang), 0, math.sin(ang))); vd = Vector((-math.sin(ang), 0, math.cos(ang)))
    verts = []; uvs = []; faces = []
    nu, nv = 48, 12
    r = W * 0.42
    for i in range(nu + 1):
        for j in range(nv + 1):
            v = (j / nv - 0.5) * W
            ext = L / 2 - r + math.sqrt(max(0.0, r * r - max(0.0, abs(v) - (W / 2 - r)) ** 2))
            u = (i / nu * 2 - 1) * ext
            p = Vector((cx, 0, cz)) + ud * u + vd * v
            loc, nor = P.hit((p.x, -1.0, p.z), (0, 1, 0))
            y = min(loc.y if loc is not None else A.FRONT_Y, A.FRONT_Y) - 0.0011
            peel = max(0.0, (u / (L / 2) - 0.80) / 0.20) * max(0.0, (v / (W / 2) + 0.2) / 1.2)
            y -= 0.012 * peel ** 2
            verts.append(Vector((p.x, y, p.z))); uvs.append(((u + L / 2) / L, (v + W / 2) / W))
    for i in range(nu):
        for j in range(nv):
            q = i * (nv + 1) + j
            faces.append((q, q + nv + 1, q + nv + 2, q + 1))
    bm = A.bm_from(verts, faces)
    uvl = bm.loops.layers.uv.new('UVMap')
    bm.verts.index_update()
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = uvs[lp.vert.index]
    obs.append(A.make_obj('Rocket_Bandaid', bm, tan, 'spine_01', solid=0.0007))
    # spiked leather wristbands on both stick forearms
    leather = A.mat_plain('M_CuffLeather', '#2e1d14', rough=0.5, col2='#1c120c', nscale=90, bump=0.12, bscale=700)
    obs += wristband(P, 'lowerarm_l', leather, chrome, side='L')
    obs += wristband(P, 'lowerarm_r', leather, chrome, side='R')
    return obs


BUILDERS['RocketGuy'] = rocketguy


# ================================================================== 4. SNIPER
def ear_flap(P, cap_obs, sgn, name, mat, trim, W=0.138, D=0.084, yc=-0.004, min_z=0.808):
    """quilted ear flap hanging from the cap band down the side face (sgn=+1: character's left, +x)"""
    import bmesh
    # where the cap band sits on this side: lowest cap point per y slice
    rim = {}
    for ob in cap_obs:
        mw = ob.matrix_world
        for v in ob.data.vertices:
            w = mw @ v.co
            if sgn * w.x > 0.16:
                k = int(round(w.y / 0.01))
                rim[k] = min(rim.get(k, 9.0), w.z)
    ks = [k for k in rim if abs(k * 0.01 - yc) < W / 2 + 0.01]
    n_ = len(ks); my = sum(k * 0.01 for k in ks) / n_; mz = sum(rim[k] for k in ks) / n_
    sl = sum((k * 0.01 - my) * (rim[k] - mz) for k in ks) / max(1e-9, sum((k * 0.01 - my) ** 2 for k in ks))
    def rim_z(y):                                  # straight least-squares line along the band: no wrinkles
        return mz + sl * (y - my)
    def side_x(y, z):
        loc, nor = P.hit((sgn * 1.0, y, z), (-sgn, 0, 0))
        return abs(loc.x) if loc is not None else 0.205
    D = min(D, min(rim_z(yc - W / 2), rim_z(yc + W / 2)) + 0.014 - min_z)   # stay above the shoulder (arm sticks)
    nu, nv = 22, 18
    verts = []; faces = []; uvs = []
    for j in range(nv + 1):
        v = j / nv * D
        q = max(0.0, (v - 0.55 * D) / (0.45 * D))
        hw = W / 2 * math.sqrt(max(0.0, 1 - q ** 2.6)) if q < 1 else 0.0
        hw = max(hw, 0.004)
        for i in range(nu + 1):
            u = (i / nu * 2 - 1)
            y = yc + u * hw
            z = rim_z(y) + 0.014 - v
            x = side_x(y, z) + 0.0075 + 0.0045 * (v / D) + 0.0025 * (1 - u * u)
            verts.append(Vector((sgn * x, y, z))); uvs.append((u, v))
    for j in range(nv):
        for i in range(nu):
            q = j * (nu + 1) + i
            faces.append((q, q + 1, q + nu + 2, q + nu + 1))
    bm = A.bm_from(verts, faces)
    obs = [A.make_obj(name, bm, mat, 'spine_01', solid=0.0055)]
    # fleece trim around the sides + bottom
    border = [verts[j * (nu + 1)] for j in range(nv + 1)] + [verts[nv * (nu + 1) + i] for i in range(1, nu + 1)] + \
             [verts[j * (nu + 1) + nu] for j in range(nv - 1, -1, -1)]
    border = [p + Vector((sgn * 0.0005, 0, 0)) for p in border]
    bm = A.tube(border, 0.0052, n=10, flat=1.0)
    A.displace(bm, lambda p: p + Vector((sgn, 0, 0)) * 0.0012 * noise.noise(p * 600.0))
    obs.append(A.make_obj(name + 'Trim', bm, trim, 'spine_01'))
    # tie string from the bottom of the flap
    b0 = verts[nv * (nu + 1) + nu // 2] + Vector((sgn * 0.002, 0, 0.004))
    pts = [b0 + Vector((sgn * 0.004 * t, 0.006 * math.sin(t * 2.5), -0.05 * t)) for t in [i / 8 for i in range(9)]]
    bm = A.tube(pts, lambda t: 0.0022 - 0.0006 * t, n=8)
    obs.append(A.make_obj(name + 'Tie', bm, trim, 'spine_01'))
    return obs


def camo_stripe(P, name, z_mid, height, mat, x0=-0.186, x1=0.186, seed=1, wobble=0.004):
    """brushy face-paint band across the front face (follows the surface and dips into holes like real paint)"""
    rng = random.Random(seed)
    top = []; bot = []
    n = 26
    ph1, ph2 = rng.uniform(0, 6), rng.uniform(0, 6)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        e = 1.0
        h = height * e
        zz = z_mid + 0.004 * math.sin(x * 22 + ph1)
        top.append((x, zz + h / 2 + wobble * math.sin(x * 61 + ph2) * rng.uniform(0.4, 1.0)))
        bot.append((x, zz - h / 2 - wobble * math.sin(x * 47 + ph1) * rng.uniform(0.4, 1.0)))
    # ragged brush-stroke ends
    lend = [(x0 - 0.004 * rng.uniform(0.3, 1.0) * (k % 2), z_mid + height * (0.5 - k / 4)) for k in range(1, 4)]
    rend = [(x1 + 0.004 * rng.uniform(0.3, 1.0) * (k % 2), z_mid + height * (-0.5 + k / 4)) for k in range(1, 4)]
    outline = bot + rend + top[::-1] + lend
    return A.puff(name, P, outline, 0.0009, mat, edge=0.004, power=1.0, bury=0.0012, res=0.0025, hole_clamp=False)


def sniper(P, T):
    import bmesh
    obs = []
    blaze = A.mat_felt('M_BlazeOrange', '#f2520a', '#de4508', rough=0.74, fiber=0.3)
    fleece = A.mat_felt('M_Fleece', '#c9b089', '#a88f68', rough=0.95, fiber=0.9)
    under = A.mat_plain('M_CapUnderbrim', '#3f4a2c', rough=0.8, bump=0.03)
    a, b = 0.214, 0.166
    H = hat_frame(T, fwd=math.radians(4), side=math.radians(3), lift=-0.030, shift=(-0.004, -0.008))
    prof = [(1.0, 0.0), (0.995, 0.030), (0.975, 0.060), (0.93, 0.090), (0.85, 0.116), (0.72, 0.137), (0.54, 0.151), (0.30, 0.159), (0.0, 0.161)]
    def soft(k, t, x, y, z):                          # softer, slightly taller front panels
        f = max(0.0, -y / b) ** 2.0
        return (x, y * (1.0 + 0.03 * f), z * (1.0 + 0.06 * f))
    bm = A.lathe(prof, a, b, e=2.6, n=80, cap_bottom=False, shape=soft)
    lin = bm.copy(); A.transform(lin, Matrix.Diagonal((0.975, 0.975, 0.975, 1.0)))
    cap = [A.make_obj('Sniper_Crown', A.transform(bm, H), blaze, 'spine_01', solid=0.004),
           A.make_obj('Sniper_CapLining', A.transform(lin, H), A.mat_plain('M_SniperLining', '#2b2a24', rough=0.85, bump=0.02), 'spine_01', solid=0.002)]
    seam = A.mat_plain('M_SniperSeam', '#c2410a', rough=0.8, bump=0.0)
    for k in range(6):
        ang = k / 6 * 2 * PI + PI / 6
        pts = []
        for (s, z) in prof[1:-1]:
            fz = max(0.0, -(b * s * math.sin(ang)) / b) ** 2.0
            pts.append(Vector((a * s * math.cos(ang) * 1.003, b * s * math.sin(ang) * (1 + 0.03 * fz) * 1.003, z * (1 + 0.06 * fz) + 0.003)))
        bm = A.tube(pts, 0.0015, n=6)
        cap.append(A.make_obj('Sniper_Seam%d' % k, A.transform(bm, H), seam, 'spine_01'))
    bm = A.lathe([(1.0, 0.0), (1.0, 0.004), (0.7, 0.0075), (0.0, 0.0085)], 0.011, 0.011, n=24)
    A.transform(bm, Matrix.Translation((0, 0, 0.161)))
    cap.append(A.make_obj('Sniper_Button', A.transform(bm, H), blaze, 'spine_01'))
    # brim to the front, gently curved, dark olive underside (top + bottom as two shells)
    verts = []; faces = []
    nu, nv = 18, 9
    for i in range(nu + 1):
        u = i / nu * 2 - 1
        for j in range(nv + 1):
            v = j / nv
            bx = u * (a * 0.84) * (1 - 0.15 * v ** 2)
            by = -(b * 0.97) * math.sqrt(max(0.0, 1 - (bx / a) ** 2)) - v * 0.105 * (1 - 0.5 * u * u)
            bz = 0.010 - 0.020 * u * u - 0.040 * v - 0.006 * v * v
            verts.append(Vector((bx, by, bz)))
    for i in range(nu):
        for j in range(nv):
            q = i * (nv + 1) + j
            faces.append((q, q + nv + 1, q + nv + 2, q + 1))
    bm = A.bm_from(verts, faces)
    bot = bm.copy(); A.transform(bot, Matrix.Translation((0, 0, -0.0042)))
    cap.append(A.make_obj('Sniper_Brim', A.transform(bm, H), blaze, 'spine_01', solid=0.004))
    cap.append(A.make_obj('Sniper_BrimUnder', A.transform(bot, H), under, 'spine_01', solid=0.0012))
    # brim stitching rows
    for r in (0.25, 0.5, 0.75):
        pts = []
        for i in range(nu + 1):
            u = i / nu * 2 - 1
            v = 0.15 + r * 0.8
            bx = u * (a * 0.84) * (1 - 0.15 * v ** 2) * 0.96
            by = -(b * 0.97) * math.sqrt(max(0.0, 1 - (bx / a) ** 2)) - v * 0.105 * (1 - 0.5 * u * u)
            bz = 0.010 - 0.020 * u * u - 0.040 * v - 0.006 * v * v + 0.0024
            pts.append(Vector((bx, by, bz)))
        bm = A.tube(pts, 0.0008, n=5)
        cap.append(A.make_obj('Sniper_BrimStitch%d' % int(r * 4), A.transform(bm, H), seam, 'spine_01'))
    chk = [cap[0], cap[1], [o for o in cap if o.name == 'Sniper_Brim'][0]]
    print('sniper cap fit', A.fit_hat(P, cap, chk[:2], H.col[3][:3], H.col[0][:3], H.col[1][:3], H.col[2][:3], rng_deg=4.0))
    print('sniper cap drape', A.drape(P, cap, chk, H.col[2][:3]))
    obs += cap
    # ear flaps down
    for sgn in (-1, 1):
        obs += ear_flap(P, cap[:1], sgn, 'Sniper_Flap%s' % ('L' if sgn > 0 else 'R'), blaze, fleece)
    # two stripes of camo face paint across the wedge, under the eyes
    olive = A.mat_plain('M_CamoOlive', '#4b5a2a', rough=0.88, col2='#3a4720', nscale=120, bump=0.05, bscale=500)
    brown = A.mat_plain('M_CamoBrown', '#3b2a1a', rough=0.9, col2='#2a1d12', nscale=120, bump=0.05, bscale=500)
    obs.append(camo_stripe(P, 'Sniper_CamoTop', 0.676, 0.030, olive, seed=3))
    obs.append(camo_stripe(P, 'Sniper_CamoLow', 0.628, 0.030, brown, seed=8))
    # a long piece of dry grass where a mouth would be
    straw = A.mat_plain('M_DryGrass', '#cdb06a', rough=0.7, col2='#a88848', nscale=200, bump=0.08, bscale=900)
    root = Vector((MOUTH.x - 0.004, A.FRONT_Y + 0.006, 0.652))
    d = Vector((0.82, -0.50, 0.10)).normalized()
    pts = []
    for i in range(25):
        t = i / 24
        pts.append(root + d * 0.205 * t + Vector((0, 0, -0.045 * t * t)) + Vector((0.004 * math.sin(t * 5), 0, 0)))
    bm = A.tube(pts, lambda t: 0.0038 * (1 - 0.35 * t), n=8, flat=0.85)
    obs.append(A.make_obj('Sniper_GrassStem', bm, straw, 'spine_01'))
    # seed head: alternating spikelets along the last stretch + a couple of nodes on the stem
    head = A.mat_plain('M_GrassHead', '#b8954f', rough=0.75, col2='#8f6f35', nscale=300, bump=0.1, bscale=1200)
    hb = bmesh.new()
    for k in range(14):
        t = 0.78 + 0.22 * k / 13
        i = min(23, int(t * 24))
        p = pts[i] + (pts[i + 1] - pts[i]) * (t * 24 - i)
        tan = (pts[i + 1] - pts[i]).normalized()
        side = tan.cross(Vector((0, 0, 1))).normalized()
        dirn = (tan * 0.8 + side * (0.55 if k % 2 else -0.55) + Vector((0, 0, 0.3))).normalized()
        s = 1.0 - 0.45 * k / 13
        sp = A.sphere((0, 0, 0), 1.0, seg=10, rings_=6, scale=(0.0032 * s, 0.0032 * s, 0.0085 * s))
        zax = dirn; xax = zax.orthogonal().normalized(); yax = zax.cross(xax)
        A.transform(sp, A.frame_matrix(p + dirn * 0.006 * s, xax, yax, zax))
        tmp = bpy.data.meshes.new('tmp'); sp.to_mesh(tmp); sp.free(); hb.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    for t in (0.3, 0.55):
        i = int(t * 24)
        nd = A.sphere(pts[i], 0.0031, seg=10, rings_=6, scale=(1, 1, 0.8))
        tmp = bpy.data.meshes.new('tmp'); nd.to_mesh(tmp); nd.free(); hb.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    obs.append(A.make_obj('Sniper_GrassHead', hb, head, 'spine_01'))
    return obs


BUILDERS['Sniper'] = sniper
