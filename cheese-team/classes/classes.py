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
def camo_stripe(P, name, z_mid, height, mat, x0=-0.186, x1=0.186, seed=1, wobble=0.004, slope=0.0):
    """brushy face-paint band across the front face (follows the surface and dips into holes like real paint)"""
    rng = random.Random(seed)
    top = []; bot = []
    n = 26
    ph1, ph2 = rng.uniform(0, 6), rng.uniform(0, 6)
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        e = 1.0
        h = height * e
        zz = z_mid + slope * x + 0.004 * math.sin(x * 22 + ph1)
        top.append((x, zz + h / 2 + wobble * math.sin(x * 61 + ph2) * rng.uniform(0.4, 1.0)))
        bot.append((x, zz - h / 2 - wobble * math.sin(x * 47 + ph1) * rng.uniform(0.4, 1.0)))
    # ragged brush-stroke ends
    lend = [(x0 - 0.004 * rng.uniform(0.3, 1.0) * (k % 2), z_mid + slope * x0 + height * (0.5 - k / 4)) for k in range(1, 4)]
    rend = [(x1 + 0.004 * rng.uniform(0.3, 1.0) * (k % 2), z_mid + slope * x1 + height * (-0.5 + k / 4)) for k in range(1, 4)]
    outline = bot + rend + top[::-1] + lend
    return A.puff(name, P, outline, 0.0009, mat, edge=0.004, power=1.0, bury=0.0012, res=0.0025, hole_clamp=False)


def sniper(P, T):
    """bare-headed (no hat, no grass): two stripes of camo face paint under the eyes; the class reads by its height"""
    obs = []
    olive = A.mat_plain('M_CamoOlive', '#4b5a2a', rough=0.88, col2='#3a4720', nscale=120, bump=0.05, bscale=500)
    black = A.mat_plain('M_CamoBlack', '#1f2414', rough=0.9, col2='#14180d', nscale=120, bump=0.05, bscale=500)
    obs.append(camo_stripe(P, 'Sniper_CamoTop', 0.688, 0.024, olive, seed=3, slope=-0.06))
    obs.append(camo_stripe(P, 'Sniper_CamoLow', 0.651, 0.022, black, seed=8, slope=-0.06))
    return obs


BUILDERS['Sniper'] = sniper


# ================================================================== 5. MECHANIC
def lathe_uv(bm, rep_u=4.0, v_scale=1.0, name='UVMap'):
    """cylindrical UVs for a lathe around local Z: u = angle (repeated rep_u times), v = height; seam-safe"""
    uvl = bm.loops.layers.uv.new(name)
    for f in bm.faces:
        us = [((math.atan2(lp.vert.co.y, lp.vert.co.x) / (2 * PI)) % 1.0) * rep_u for lp in f.loops]
        if max(us) - min(us) > rep_u * 0.5:
            us = [u + rep_u if u < rep_u * 0.5 else u for u in us]
        for lp, u in zip(f.loops, us):
            lp[uvl].uv = (u, lp.vert.co.z * v_scale)
    return bm


def grease_mat(name='M_Grease'):
    """dark, slightly glossy, uneven grease (thicker = darker + shinier)"""
    m, nt, bs = A._mat(name)
    vec = A._tc(nt)
    n = A._noise(nt, vec, 90, 6, 0.6)
    r = A._ramp(nt, n.outputs['Fac'], A.srgb('#17130f'), A.srgb('#4a3d31'), 0.30, 0.80)
    nt.links.new(r.outputs['Color'], bs.inputs['Base Color'])
    rr = A._ramp(nt, n.outputs['Fac'], (0.22, 0.22, 0.22), (0.6, 0.6, 0.6), 0.4, 0.7)
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(rr.outputs['Color'], sep.inputs[0])
    nt.links.new(sep.outputs[0], bs.inputs['Roughness'])
    A._bump(nt, bs, n.outputs['Fac'], 0.04, 0.0004)
    return m


def rag_towel_mat(name='M_ShopTowel'):
    """red shop towel: woven red with a darker double hem stripe near the edges (UV u across, v along)"""
    m, nt, bs = A._mat(name)
    uv = nt.nodes.new('ShaderNodeUVMap')
    sep = nt.nodes.new('ShaderNodeSeparateXYZ'); nt.links.new(uv.outputs[0], sep.inputs[0])
    def mn(op, a, b=None):
        n = nt.nodes.new('ShaderNodeMath'); n.operation = op
        if isinstance(a, float): n.inputs[0].default_value = a
        else: nt.links.new(a, n.inputs[0])
        if b is not None:
            if isinstance(b, float): n.inputs[1].default_value = b
            else: nt.links.new(b, n.inputs[1])
        return n.outputs[0]
    e = mn('MINIMUM', sep.outputs[0], mn('SUBTRACT', 1.0, sep.outputs[0]))          # distance to the nearer side edge
    st = mn('MAXIMUM', mn('LESS_THAN', mn('ABSOLUTE', mn('SUBTRACT', e, 0.10)), 0.025),
            mn('LESS_THAN', mn('ABSOLUTE', mn('SUBTRACT', e, 0.17)), 0.012))
    vec = A._tc(nt)
    n1 = A._noise(nt, vec, 70, 5, 0.6)
    base = A._ramp(nt, n1.outputs['Fac'], A.srgb('#b8261f'), A.srgb('#962019'), 0.3, 0.75)
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'
    nt.links.new(st, mix.inputs['Factor']); nt.links.new(base.outputs['Color'], mix.inputs['A'])
    mix.inputs['B'].default_value = (*A.srgb('#5e100c'), 1)
    nt.links.new(mix.outputs['Result'], bs.inputs['Base Color'])
    bs.inputs['Roughness'].default_value = 0.92
    wv = nt.nodes.new('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 900.0
    nt.links.new(vec, wv.inputs['Vector'])
    A._bump(nt, bs, wv.outputs['Fac'], 0.25, 0.0004)
    return m


def alpha_mat(m):
    """use the image alpha for coverage (soft decal edges)"""
    nt = m.node_tree
    tx = next(n for n in nt.nodes if n.type == 'TEX_IMAGE'); bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    nt.links.new(tx.outputs['Alpha'], bs.inputs['Alpha'])
    for attr, val in (('surface_render_method', 'BLENDED'), ('blend_method', 'BLEND')):
        try:
            setattr(m, attr, val)
        except (AttributeError, TypeError):
            pass
    try:
        m.use_backface_culling = True
    except AttributeError:
        pass
    return m


def tex_decal(P, name, cx, cz, L, W, ang, mat, flip=False, off=0.0009, nu=28, nv=10):
    """textured quad decal (u along the swipe) projected onto the FRONT of the body, UV 0..1"""
    import bmesh
    ud = Vector((math.cos(ang), 0, math.sin(ang))); vd = Vector((-math.sin(ang), 0, math.cos(ang)))
    verts = []; uvs = []; faces = []; ok = []
    for i in range(nu + 1):
        for j in range(nv + 1):
            u = (i / nu - 0.5) * L; v = (j / nv - 0.5) * W
            p = Vector((cx, 0, cz)) + ud * u + vd * v
            loc, nor = P.hit((p.x, -1.0, p.z), (0, 1, 0))
            ok.append(loc is not None)
            y = (loc.y if loc is not None else A.FRONT_Y) - off
            verts.append(Vector((p.x, y, p.z))); uvs.append((i / nu, (1 - j / nv) if flip else j / nv))
    for i in range(nu):
        for j in range(nv):
            q = i * (nv + 1) + j
            idx = (q, q + nv + 1, q + nv + 2, q + 1)
            if all(ok[k] for k in idx):
                faces.append(idx)
    bm = A.bm_from(verts, faces)
    bmesh.ops.delete(bm, geom=[v for v in bm.verts if not v.link_faces], context='VERTS')
    uvl = bm.loops.layers.uv.new('UVMap')
    bm.verts.index_update()
    # bm_from keeps creation order; map back through coordinates
    lut = {tuple(round(c, 7) for c in vv): uv for vv, uv in zip(verts, uvs)}
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = lut[tuple(round(c, 7) for c in lp.vert.co)]
    return A.make_obj(name, bm, mat, 'spine_01', smooth=True)


def smudge_outline(cx, cz, length, width, ang, seed, fingers=3):
    """finger-swipe smear: a few parallel, tapering streaks merged into one ragged outline"""
    rng = random.Random(seed)
    ca, sa = math.cos(ang), math.sin(ang)
    pts_top = []; pts_bot = []
    n = 30
    for i in range(n + 1):
        t = i / n
        u = (t - 0.5) * length
        w = width * (0.35 + 0.65 * math.sin(PI * min(1.0, t * 1.25)) ** 0.7) * (1.0 - 0.55 * t)
        wob = 0.0025 * math.sin(t * 19 + seed) + 0.0015 * math.sin(t * 41 + 2 * seed)
        # finger ridges: the top edge is scalloped by the streaks
        sc = 0.10 * width * abs(math.sin(t * PI * fingers * 1.5 + seed)) * (1 - t)
        pts_top.append((u, w / 2 + wob - sc)); pts_bot.append((u, -w / 2 + wob * 0.7 + sc * 0.5))
    out = pts_bot + pts_top[::-1]
    return [(cx + u * ca - v * sa, cz + u * sa + v * ca) for (u, v) in out]


def wrench_outline(L=0.215):
    """combination wrench in 2D (x along the tool): open jaw at -x, 12-point box end at +x (as a separate hole loop)"""
    out = []
    # open end (centre at -L/2+0.024): jaw opening along -x tilted 15 deg
    co = Vector((-L / 2 + 0.024, 0.0)); R = 0.0245; jaw = 0.0118
    tilt = math.radians(15)
    def rot(v, a):
        return Vector((v.x * math.cos(a) - v.y * math.sin(a), v.x * math.sin(a) + v.y * math.cos(a)))
    # outer arc of the open head from the shank top round to the jaw tip
    for i in range(14):
        a = math.radians(70) + math.radians(85) * i / 13
        out.append(co + rot(Vector((math.cos(a), math.sin(a))) * R, tilt))
    # jaw: two flat faces with a rounded throat
    j_top = co + rot(Vector((-R * 0.95, jaw)), tilt); j_bot = co + rot(Vector((-R * 0.95, -jaw)), tilt)
    out.append(j_top)
    out.append(co + rot(Vector((-0.004, jaw)), tilt))
    for i in range(7):                                       # rounded throat, bulging INTO the head
        a = PI / 2 - PI * i / 6
        out.append(co + rot(Vector((0.002 + math.cos(a) * jaw * 0.35, math.sin(a) * jaw)), tilt))
    out.append(co + rot(Vector((-0.004, -jaw)), tilt))
    out.append(j_bot)
    for i in range(14):
        a = math.radians(205) + math.radians(85) * i / 13
        out.append(co + rot(Vector((math.cos(a), math.sin(a))) * R, tilt))
    # shank bottom edge to the box end
    cb = Vector((L / 2 - 0.022, 0.0)); Rb = 0.0215
    sw = 0.0082
    for i in range(1, 9):
        t = i / 9
        x = co.x + 0.016 + (cb.x - 0.016 - co.x - 0.016) * t
        out.append(Vector((x, -sw * (1.0 + 0.10 * math.sin(PI * t)))))
    for i in range(25):
        a = math.radians(-120) + math.radians(240) * i / 24
        out.append(cb + Vector((math.cos(a), math.sin(a))) * Rb)
    for i in range(8, 0, -1):
        t = i / 9
        x = co.x + 0.016 + (cb.x - 0.016 - co.x - 0.016) * t
        out.append(Vector((x, sw * (1.0 + 0.10 * math.sin(PI * t)))))
    hole = []
    for i in range(24):                                            # 12-point box: alternating radii
        a = 2 * PI * i / 24
        r = 0.0128 if i % 2 == 0 else 0.0112
        hole.append(cb + Vector((math.cos(a), math.sin(a))) * r)
    return out, hole


def wrench_mesh(F, thick=0.0075, k=1.0):
    """extrude the wrench outline (with the box-end hole) into a solid: robust tessellation + explicit side walls"""
    from mathutils.geometry import tessellate_polygon
    out, hole = wrench_outline()
    out = [p * k for p in out]; hole = [p * k for p in hole]
    loops = [out, hole]
    flat = [p for lp in loops for p in lp]
    tris = tessellate_polygon([[Vector((p.x, p.y, 0.0)) for p in lp] for lp in loops])
    n = len(flat)
    verts = [Vector((p.x, p.y, -thick / 2)) for p in flat] + [Vector((p.x, p.y, thick / 2)) for p in flat]
    faces = []
    for (a, b, c) in tris:
        faces.append((a, c, b)); faces.append((a + n, b + n, c + n))
    base = 0
    for lp in loops:
        m = len(lp)
        for i in range(m):
            a = base + i; b = base + (i + 1) % m
            faces.append((a, b, b + n, a + n))
        base += m
    bm = A.bm_from(verts, faces)
    import bmesh
    bmesh.ops.remove_doubles(bm, verts=bm.verts[:], dist=1e-7)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    A.transform(bm, F)
    return bm


def mechanic(P, T):
    import bmesh
    obs = []
    rng = random.Random(11)
    weld = A.mat_image('M_WelderCap', 'welder_pattern.png', rough=0.82, bump=0.12)
    a, b = 0.212, 0.164
    E = 3.3
    H = hat_frame(T, fwd=math.radians(5), side=math.radians(2), lift=-0.030, shift=(-0.004, -0.006))
    prof = [(1.0, 0.0), (0.995, 0.024), (0.97, 0.048), (0.92, 0.070), (0.84, 0.088), (0.72, 0.101), (0.55, 0.109), (0.31, 0.113), (0.0, 0.114)]
    bm = A.lathe(prof, a, b, e=E, n=96, cap_bottom=False)
    lin = bm.copy(); A.transform(lin, Matrix.Diagonal((0.975, 0.975, 0.975, 1.0)))
    lathe_uv(bm, rep_u=3.0, v_scale=4.2)
    cap = [A.make_obj('Mech_Crown', A.transform(bm, H), weld, 'spine_01', solid=0.0035),
           A.make_obj('Mech_CapLining', A.transform(lin, H), A.mat_plain('M_MechLining', '#2b2622', rough=0.85, bump=0.02), 'spine_01', solid=0.002)]
    seam = A.mat_plain('M_MechSeam', '#1e1a18', rough=0.8, bump=0.0)
    for k in range(4):                                           # 4-panel welder cap
        ang = k / 4 * 2 * PI + PI / 4
        cx = math.copysign(abs(math.cos(ang)) ** (2.0 / E), math.cos(ang)); cy = math.copysign(abs(math.sin(ang)) ** (2.0 / E), math.sin(ang))
        pts = [Vector((a * s * cx * 1.004, b * s * cy * 1.004, z + 0.0025)) for (s, z) in prof[1:-1]]
        bm = A.tube(pts, 0.0013, n=6)
        cap.append(A.make_obj('Mech_Seam%d' % k, A.transform(bm, H), seam, 'spine_01'))
    # short brim, flipped up
    verts = []; faces = []
    nu, nv = 16, 5
    for i in range(nu + 1):
        u = i / nu * 2 - 1
        for j in range(nv + 1):
            v = j / nv
            bx = u * a * 0.62
            by0 = -b * math.sqrt(max(0.0, 1 - abs(bx / a) ** E)) ** (2.0 / E) * 0.985
            by = by0 - v * 0.040 * (1 - 0.6 * u * u) * math.cos(math.radians(38))
            bz = 0.004 + v * 0.040 * (1 - 0.6 * u * u) * math.sin(math.radians(38)) - 0.006 * u * u
            verts.append(Vector((bx, by, bz)))
    for i in range(nu):
        for j in range(nv):
            q = i * (nv + 1) + j
            faces.append((q, q + nv + 1, q + nv + 2, q + 1))
    bm = A.bm_from(verts, faces)
    uvl = bm.loops.layers.uv.new('UVMap')
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = (lp.vert.co.x * 14.0, lp.vert.co.y * 14.0)
    cap.append(A.make_obj('Mech_Brim', A.transform(bm, H), A.mat_felt('M_MechBrim', '#1d7179', '#185f66', rough=0.8, fiber=0.3), 'spine_01', solid=0.004))
    pts = [Vector((verts[i * (nv + 1) + nv].x, verts[i * (nv + 1) + nv].y, verts[i * (nv + 1) + nv].z)) for i in range(nu + 1)]
    bm = A.tube(pts, 0.0024, n=8)                                  # bound brim edge
    cap.append(A.make_obj('Mech_BrimEdge', A.transform(bm, H), seam, 'spine_01'))
    print('mech cap fit', A.fit_hat(P, cap, cap[:2], H.col[3][:3], H.col[0][:3], H.col[1][:3], H.col[2][:3], rng_deg=4.0))
    print('mech cap drape', A.drape(P, cap, cap[:2] + [o for o in cap if o.name == 'Mech_Brim'], H.col[2][:3]))
    obs += cap
    # black grease smudges (finger swipes) on the wedge: soft alpha decals
    gm = A.mat_image('M_GreaseSmear', 'grease_smear.png', rough=0.35, bump=0.0)
    alpha_mat(gm)
    for k, (cx, cz, L, W, ang, flip) in enumerate(((-0.044, 0.632, 0.150, 0.068, math.radians(38), False),
                                                  (-0.140, 0.890, 0.096, 0.048, math.radians(-62), True),
                                                  (0.152, 0.652, 0.078, 0.040, math.radians(-118), False))):
        obs.append(tex_decal(P, 'Mech_Grease%d' % k, cx, cz, L, W, ang, gm, flip=flip))
    # red shop rag stuffed into the big jaw hole, a tail hanging out
    rag = A.mat_plain('M_ShopRag', '#b3231d', rough=0.9, col2='#8c1813', nscale=70, bump=0.35, bscale=1400)
    ragt = rag_towel_mat()
    hc = Vector((-0.140, A.FRONT_Y, 0.646))
    bun = A.sphere((0, 0, 0), 1.0, seg=40, rings_=22)
    def crumple(p):
        q = Vector(p)
        ridge = 1.0 - abs(noise.noise(q * 2.6 + Vector((3, 1, 7))))          # sharp fold creases
        f = 0.86 + 0.30 * ridge ** 3 + 0.06 * noise.noise(q * 6.0)
        return Vector((q.x * 0.044 * f, q.y * 0.032 * f, q.z * 0.040 * f))
    A.displace(bun, crumple)
    A.transform(bun, Matrix.Translation(hc + Vector((0.002, 0.004, 0.004))))
    obs.append(A.make_obj('Mech_RagBunch', bun, rag, 'spine_01', subsurf=1))
    for k, (dx, dz, tw) in enumerate(((-0.030, 0.034, 0.7), (0.020, 0.040, -0.5))):    # two cloth corners poking out
        pts = [hc + Vector((dx * t, -0.022 - 0.010 * t, 0.010 + dz * t)) for t in [i / 6 for i in range(7)]]
        bm = A.ribbon(pts, lambda t: 0.030 * (1 - t) ** 0.9 + 0.002, lambda t, tan: Vector((0, -1, 0.3 * tw)).normalized())
        A.displace(bm, lambda p: p + Vector((0, -1, 0)) * 0.003 * noise.noise(p * 90.0))
        obs.append(A.make_obj('Mech_RagCorner%d' % k, bm, rag, 'spine_01', solid=0.0022, subsurf=1))
    # tail: a cloth strip from the bunch draping down the face, folds across it, frayed end
    nu, nv = 12, 18
    verts = []; faces = []; ruv = []
    for j in range(nv + 1):
        t = j / nv
        for i in range(nu + 1):
            u = i / nu * 2 - 1
            w = 0.066 * (1 - 0.10 * t)
            x = hc.x + 0.006 + u * w / 2 + 0.010 * math.sin(t * 2.2)
            z = hc.z - 0.014 - 0.070 * t
            fold = 0.0040 * math.sin(u * 2.6 + t * 3.0) + 0.0015 * math.sin(u * 5.0 - t * 2.0)
            loc, nor = P.hit((x, -1.0, z), (0, 1, 0))
            yb = min(loc.y, A.FRONT_Y) if (loc is not None and z > 0.586) else A.FRONT_Y + 0.004 + 0.01 * max(0.0, (0.586 - z) / 0.02)
            y = yb - 0.006 - 0.012 * (1 - t) ** 2 - abs(fold)
            z -= 0.026 * t * (u + 1) / 2                               # diagonal hem: a corner of the rag hangs lowest
            verts.append(Vector((x, y, z))); ruv.append(((u + 1) / 2, t))
    for j in range(nv):
        for i in range(nu):
            q = j * (nu + 1) + i
            faces.append((q, q + 1, q + nu + 2, q + nu + 1))
    bm = A.bm_from(verts, faces)
    uvl = bm.loops.layers.uv.new('UVMap'); bm.verts.index_update()
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = ruv[lp.vert.index]
    obs.append(A.make_obj('Mech_RagTail', bm, ragt, 'spine_01', solid=0.0025, subsurf=1))
    # big combination wrench clipped flat to the +x side face, under the shoulder
    steel = A.mat_metal('M_WrenchSteel', '#c9ccd2', rough=0.22, scratches=0.8)
    cz, cy = 0.630, 0.018
    ang = math.radians(8)
    # the side face is yawed (the wedge narrows to the back): fit its plane, skipping the arm stick
    pts = []
    for yy in (-0.10, -0.07, -0.04, 0.04, 0.07, 0.10, 0.12):
        for zz in (0.60, 0.63, 0.66):
            loc, nor = P.hit((1.0, yy, zz), (-1, 0, 0))
            if loc is not None and loc.x < 0.22:
                pts.append(loc)
    cen = sum(pts, Vector()) / len(pts)
    # least squares x = a*y + b*z + c
    import numpy as np
    M_ = np.array([[p.y, p.z, 1.0] for p in pts]); rhs = np.array([p.x for p in pts])
    (ka, kb, kc), *_ = np.linalg.lstsq(M_, rhs, rcond=None)
    Z = Vector((1.0, -ka, -kb)).normalized()                      # outward face normal
    up = (Vector((0, 0, 1)) - Z * Z.z).normalized(); fw = up.cross(Z).normalized()   # in-plane axes (fw ~ +y)
    if fw.y < 0:
        fw = -fw
    X = (fw * math.cos(ang) + up * math.sin(ang)).normalized(); Y = Z.cross(X).normalized()
    sx = ka * cy + kb * cz + kc
    base = Vector((sx, cy, cz))
    wt = 0.0092
    wk = 1.16                                                     # big wrench (fills the side face)
    F = A.frame_matrix((base + Z * (wt / 2 + 0.0004)), X, Y, Z)
    wb = wrench_mesh(F, thick=wt, k=wk)
    w = A.make_obj('Mech_Wrench', wb, steel, 'spine_01')
    bv = w.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0011; bv.segments = 2; bv.limit_method = 'ANGLE'
    obs.append(w)
    # the clip: a steel strap arching over the shank, both feet screwed into the cheese
    clipm = A.mat_metal('M_ClipSteel', '#9da3a8', rough=0.35, scratches=0.6)
    cw, st = 0.015, 0.0016
    top = wt + 0.0004 + st / 2
    hw = 0.0094 * wk + 0.0018
    prof = [(-hw - 0.018, st / 2), (-hw - 0.004, st / 2), (-hw - 0.0013, st / 2 + 0.0008)]
    for i in range(13):                                       # rounded arch over the shank
        a = PI - PI * i / 12
        prof.append((hw * math.cos(a), st / 2 + 0.0008 + (top - st / 2 - 0.0008) * math.sin(a) ** 0.55))
    prof += [(hw + 0.0013, st / 2 + 0.0008), (hw + 0.004, st / 2), (hw + 0.018, st / 2)]
    S = A.frame_matrix((base + Z * (0.0002)), X, Y, Z)
    path = [S @ Vector((0.0, py, ph)) for (py, ph) in prof]
    bm = A.ribbon(path, cw, lambda t, tan: X.cross(tan).normalized())     # strip spans the wrench axis
    strap = A.make_obj('Mech_Clip', bm, clipm, 'spine_01', solid=st)
    obs.append(strap)
    for k, off in enumerate((-hw - 0.0105, hw + 0.0105)):
        sc = A.lathe([(1.0, 0.0), (1.0, 0.0008), (0.8, 0.0020), (0.0, 0.0024)], 0.0040, 0.0040, n=16)
        A.transform(sc, A.frame_matrix((base + Z * (0.0002 + st)) + Y * off, X, Y, Z))
        obs.append(A.make_obj('Mech_Screw%d' % k, sc, clipm, 'spine_01'))
        slot = A.box((0, 0, 0), (0.0060, 0.0011, 0.0012))
        A.transform(slot, A.frame_matrix((base + Z * (0.0002 + st + 0.0021)) + Y * off, X, Y, Z) @ Matrix.Rotation(0.6 * k + 0.3, 4, 'Z'))
        obs.append(A.make_obj('Mech_ScrewSlot%d' % k, slot, A.mat_plain('M_SlotDark', '#1a1a1a', rough=0.6, bump=0.0), 'spine_01'))
    return obs


BUILDERS['Mechanic'] = mechanic


# ================================================================== 6. HEAVY
def heavy(P, T):
    import bmesh
    obs = []
    felt = A.mat_felt('M_TenGallon', '#d2bc98', '#c2aa84', rough=0.78, fiber=0.35)
    band = A.mat_plain('M_HeavyBand', '#3a2416', rough=0.5, col2='#26170e', nscale=160, bump=0.25, bscale=420)
    silver = A.mat_metal('M_HeavyBuckle', '#dcd8cf', rough=0.2)
    a, b = 0.128, 0.142
    H = hat_frame(T, fwd=math.radians(-4), side=math.radians(-3), lift=0.010, shift=(0.010, 0.004))
    hat = []
    # crown: tall cattleman crown, slightly tapered, rounded top edge
    crown = [(1.0, -0.090), (1.0, -0.06), (1.0, -0.03), (1.0, 0.0), (0.985, 0.04), (0.965, 0.08), (0.94, 0.12), (0.915, 0.155), (0.895, 0.178), (0.87, 0.192),
             (0.82, 0.200), (0.6, 0.204), (0.0, 0.206)]
    bm = A.revolve(crown, a, b, n=96, closed=False)
    def shape_crown(v):
        x, y, z = v.x, v.y, v.z
        hz = max(0.0, min(1.0, (z - 0.06) / 0.14))
        front = max(0.0, -y / b)
        x *= 1.0 - 0.20 * front ** 2 * hz ** 1.4                      # front pinches
        crease = 0.040 * math.exp(-(x / 0.040) ** 2) * hz ** 3 * (1.0 - 0.35 * max(0.0, y / b))
        z -= crease                                                   # long centre crease, front to back
        z -= 0.010 * front ** 2 * hz ** 2                             # crown dips a touch toward the front
        return Vector((x, y, z))
    A.displace(bm, shape_crown)
    hat.append(A.make_obj('Heavy_Crown', A.transform(bm, H), felt, 'spine_01', solid=0.004))
    # brim: huge, taco-curled at the sides, a slight dip front and back, bound edge
    ra, rb = 0.335 / a, 0.330 / b
    brim = [(0.85, 0.004), (ra * 0.55, 0.0042), (ra * 0.92, 0.0040), (ra * 0.995, 0.0046), (ra * 1.0, 0.0012), (ra * 0.99, -0.0026),
            (ra * 0.92, -0.0040), (ra * 0.55, -0.0042), (0.85, -0.004)]
    def taco(f, s):
        u = max(0.0, (s / ra - 0.40) / 0.60)
        return 0.085 * u ** 1.9 * math.cos(f) ** 2 - 0.016 * u ** 2 * math.sin(f) ** 2
    bm = A.revolve(brim, a, b * (rb / ra), n=128, closed=True, zfn=taco)
    brim_ob = A.make_obj('Heavy_Brim', A.transform(bm, H), felt, 'spine_01'); hat.append(brim_ob)
    edge = []
    for i in range(129):
        f = 2 * PI * i / 128
        edge.append(Vector((a * ra * 1.0 * math.cos(f), b * (rb / ra) * ra * math.sin(f), 0.0012 + taco(f, ra))))
    hat.append(A.make_obj('Heavy_BrimBinding', A.transform(A.tube(edge, 0.0042, n=8, cap=False), H), band, 'spine_01'))
    # braided leather band with a silver buckle on the left
    hb = []
    for (s, z) in ((1.0, 0.002), (1.016, 0.004), (1.02, 0.016), (1.016, 0.028), (1.0, 0.030)):
        hb.append((s, z))
    bm = A.revolve(hb, a, b, n=96, closed=True, zfn=lambda f, s: 0.0012 * math.sin(f * 48) * (s > 1.01))
    hat.append(A.make_obj('Heavy_Band', A.transform(bm, H), band, 'spine_01'))
    ang = PI - 0.15                                                   # character's right (-x) side, slightly forward
    p = Vector((a * 1.024 * math.cos(ang), b * 1.024 * math.sin(ang), 0.016))
    nrm = Vector((math.cos(ang) / a, math.sin(ang) / b, 0)).normalized()
    z = nrm; x = Vector((0, 0, 1)).cross(z).normalized(); y = z.cross(x)
    outer = [(-0.016, -0.0135), (0.016, -0.0135), (0.016, 0.0135), (-0.016, 0.0135)]
    inner = [(-0.010, -0.0080), (-0.010, 0.0080), (0.010, 0.0080), (0.010, -0.0080)]
    bk = A.extrude_outline([outer, inner], 0.003, A.frame_matrix(p, x, y, z))
    hat.append(A.make_obj('Heavy_Buckle', A.transform(bk, H), silver, 'spine_01'))
    print('heavy hat settle', A.settle(P, hat, Vector(H.col[2][:3]), clear=0.004, check=[brim_ob]))
    print('heavy crown conform', A.conform_bottom(P, hat[0], Vector(H.col[2][:3])))
    obs += hat
    # thick handlebar moustache: combed clumps, ends curled up and out (clear of the eyes)
    hair = A.mat_plain('M_HeavyStache', '#5e3a1f', rough=0.55, col2='#3f2513', nscale=70, bump=0.06, bscale=260)
    for sgn in (-1, 1):
        pts = []
        z0 = MOUTH.z + 0.006
        for i in range(31):
            t = i / 30
            x = MOUTH.x + sgn * (0.004 + 0.128 * t)
            z = z0 + 0.004 - 0.020 * math.sin(PI * min(1.0, t / 0.8) * 0.85) + 0.050 * max(0.0, t - 0.68) ** 1.5
            pts.append(Vector((x, 0.0, z)))
        end = pts[-1]
        for i in range(1, 13):                                          # the curl: up, then back in over itself
            th = PI * 1.3 * i / 12
            r = 0.018 * (1 - 0.35 * i / 12)
            pts.append(end + Vector((sgn * (r * math.sin(th)), 0.0, r * (1 - math.cos(th)))))
        out = []
        for p in pts:
            loc, nor = P.hit((p.x, -1.0, p.z), (0, 1, 0))
            y = min(loc.y if loc is not None else A.FRONT_Y, A.FRONT_Y)
            out.append(Vector((p.x, y - 0.014, p.z)))
        L = len(out)
        bmh = bmesh.new()
        for k, (dz, dy, rs) in enumerate(((0.0, 0.0, 1.0), (0.0095, 0.003, 0.72), (-0.0095, 0.003, 0.72), (0.0, -0.007, 0.70))):
            path = [q + Vector((0, dy, dz * (1 - i / L))) for i, q in enumerate(out)]
            tb = A.tube(path, lambda t, rs=rs: rs * (0.0255 * (1 - t) ** 0.85 + 0.0015) * min(1.0, 0.55 + t * 9), n=12, flat=0.72,
                        up=Vector((0, -1, 0)))
            tmp = bpy.data.meshes.new('tmp'); tb.to_mesh(tmp); tb.free(); bmh.from_mesh(tmp); bpy.data.meshes.remove(tmp)
        obs.append(A.make_obj('Heavy_Moustache%s' % ('L' if sgn > 0 else 'R'), bmh, hair, 'spine_01', subsurf=1))
    # gold sheriff's star stuck on the wedge (lower +x cheek), slightly askew
    gold = A.mat_metal('M_SheriffGold', '#e2b54a', rough=0.22, scratches=0.6)
    goldd = A.mat_metal('M_SheriffGoldDark', '#b8892e', rough=0.35, scratches=0.4)
    R = 0.050
    rot = math.radians(12)
    import numpy as np
    pts = []
    for yy in (-0.11, -0.09, -0.07, -0.05, -0.03):
        for zz in (0.62, 0.66, 0.70):
            loc, nor = P.hit((1.0, yy, zz), (-1, 0, 0))
            if loc is not None and loc.x < 0.22:
                pts.append(loc)
    M_ = np.array([[p.y, p.z, 1.0] for p in pts]); rhs = np.array([p.x for p in pts])
    (ka, kb, kc), *_ = np.linalg.lstsq(M_, rhs, rcond=None)
    Zs = Vector((1.0, -ka, -kb)).normalized()
    up = (Vector((0, 0, 1)) - Zs * Zs.z).normalized(); fw = up.cross(Zs).normalized()
    if fw.y > 0:
        fw = -fw                                                     # toward the front
    cy_, cz_ = -0.066, 0.664
    cxs = ka * cy_ + kb * cz_ + kc
    star = []
    for i in range(12):
        ang = PI / 2 + rot + 2 * PI * i / 12
        r = R if i % 2 == 0 else R * 0.60
        star.append((r * math.cos(ang), r * math.sin(ang)))
    front = A.frame_matrix(Vector((cxs, cy_, cz_)) + Zs * 0.0028, fw, up, Zs)
    st = A.extrude_outline([star], 0.0040, front)
    so = A.make_obj('Heavy_Star', st, gold, 'spine_01')
    bv = so.modifiers.new('bevel', 'BEVEL'); bv.width = 0.0012; bv.segments = 2; bv.limit_method = 'ANGLE'
    obs.append(so)
    for i in range(6):                                                 # ball tips
        ang = PI / 2 + rot + 2 * PI * i / 6
        c = front @ Vector(((R - 0.0015) * math.cos(ang), (R - 0.0015) * math.sin(ang), 0.0))
        obs.append(A.make_obj('Heavy_StarTip%d' % i, A.sphere(c, 0.0062, seg=16, rings_=10), gold, 'spine_01'))
    # raised centre disc with an engraved ring and a small embossed star
    disc = A.lathe([(1.0, 0.0), (1.0, 0.0012), (0.92, 0.0022), (0.0, 0.0024)], 0.0175, 0.0175, n=48)
    A.transform(disc, front @ Matrix.Translation((0, 0, 0.0020)))
    obs.append(A.make_obj('Heavy_StarDisc', disc, gold, 'spine_01'))
    ring = A.revolve([(0.0128, 0.0040), (0.0142, 0.0040), (0.0142, 0.0046), (0.0128, 0.0046)], 1.0, 1.0, n=48)
    A.transform(ring, front)
    obs.append(A.make_obj('Heavy_StarRing', ring, goldd, 'spine_01'))
    small = []
    for i in range(10):
        ang = PI / 2 + rot + 2 * PI * i / 10
        r = 0.0085 if i % 2 == 0 else 0.0036
        small.append((r * math.cos(ang), r * math.sin(ang)))
    ss = A.extrude_outline([small], 0.0012, front @ Matrix.Translation((0, 0, 0.0048)))
    obs.append(A.make_obj('Heavy_StarEmboss', ss, goldd, 'spine_01'))
    return obs


BUILDERS['Heavy'] = heavy
