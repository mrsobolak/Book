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
def face_point(P, x, z, off=0.0015):
    """point on the front of the body at (x, z) (follows eyes, dents) pushed `off` toward the viewer"""
    loc, nor = P.hit((x, -1.0, z), (0, 1, 0))
    if loc is None:
        return Vector((x, A.FRONT_Y - off, z)), Vector((0, -1, 0))
    return loc + Vector((0, -off, 0)), nor


def hair_tufts(P, name, mat, seeds, rng, bone='spine_01'):
    """many tapered, curving tufts; seeds = [(root, direction, length, radius)]"""
    bms = []
    import bmesh
    acc_bm = bmesh.new()
    for (root, dirn, L, r) in seeds:
        side = dirn.cross(Vector((0, -1, 0)))
        if side.length < 1e-4:
            side = Vector((1, 0, 0))
        side.normalize()
        curl = Vector((rng.uniform(-1, 1), rng.uniform(-0.6, 0.2), rng.uniform(-1, 0.3))) * 0.25
        pts = [root + (dirn + curl * (i / 6) ** 2) .normalized() * L * (i / 6) for i in range(7)]
        tb = A.tube(pts, lambda t, r=r: r * (1 - t) ** 0.9 + 0.0006, n=7, flat=0.75)
        tmp = bpy.data.meshes.new('tmp'); tb.to_mesh(tmp); tb.free(); acc_bm.from_mesh(tmp); bpy.data.meshes.remove(tmp)
    return A.make_obj(name, acc_bm, mat, bone)


import bpy, random


def shotgun_shell(P, name, base_pt, axis, hull, brass, prim, depth=0.6, L=0.064, R=0.0118):
    """12-gauge style shell: red ribbed hull with crimp, brass head with rim + primer. base_pt on the surface,
    axis pointing OUT of the cheese; the shell is pushed in by depth*L."""
    import bmesh
    z = axis.normalized(); x = z.cross(Vector((0, 0, 1)))
    if x.length < 1e-3:
        x = z.cross(Vector((1, 0, 0)))
    x.normalize(); y = z.cross(x)
    M = A.frame_matrix(base_pt - z * depth * L, x, y, z)       # local z=0 = crimp end (inside), z=L = brass head
    obs = []
    # hull: ribbed plastic tube with a crimped, slightly rounded end
    ribs = lambda k, t, px, py, pz: (px * (1 + 0.035 * math.cos(t * 2 * PI * 16)), py * (1 + 0.035 * math.cos(t * 2 * PI * 16)), pz)
    prof = [(0.55, 0.0), (0.85, 0.002), (0.97, 0.006), (1.0, 0.012), (1.0, L - 0.016), (1.0, L - 0.0145)]
    bm = A.lathe(prof, R, R, n=48, cap_top=False, shape=ribs)
    obs.append(A.make_obj(name + '_Hull', A.transform(bm, M), hull, 'spine_01'))
    # brass head with rim and primer
    prof = [(0.99, L - 0.016), (1.02, L - 0.016), (1.03, L - 0.004), (1.12, L - 0.0035), (1.13, L - 0.001), (1.1, L), (0.5, L + 0.0002), (0.0, L + 0.0002)]
    bm = A.lathe(prof, R, R, n=48, cap_bottom=True, cap_top=True)
    obs.append(A.make_obj(name + '_Head', A.transform(bm, M), brass, 'spine_01'))
    bm = A.lathe([(1.0, L), (1.0, L + 0.0008), (0.7, L + 0.0012), (0.0, L + 0.0013)], R * 0.3, R * 0.3, n=20)
    obs.append(A.make_obj(name + '_Primer', A.transform(bm, M), prim, 'spine_01'))
    return obs


# ================================================================== 2. MR. SHOTGUN
def mrshotgun(P, T):
    import bmesh
    obs = []
    rng = random.Random(7)
    foam = A.mat_felt('M_TruckerFront', '#b3302a', '#9a2822', rough=0.7, fiber=0.25)
    mesh = A.mat_image('M_TruckerMesh', 'trucker_mesh.png', rough=0.8, bump=0.0, scale=(1, 1, 1), tint='#efe7d6')
    strap = A.mat_plain('M_Snapback', '#2b2a2a', rough=0.45, bump=0.02)
    stud = A.mat_plain('M_SnapStud', '#ece7df', rough=0.3, bump=0.0)
    # cap frame: on the top plane, turned 180 degrees so the bill points to the back, cocked a little
    a, b = 0.172, 0.150
    H = hat_frame(T, fwd=math.radians(-6), side=math.radians(4), lift=-0.010, shift=(-0.010, 0.006), pivot=(0, b, 0))
    H = H @ Matrix.Rotation(PI, 4, 'Z')                 # local +y now points to the character's back
    prof = [(1.0, 0.0), (0.995, 0.018), (0.975, 0.042), (0.935, 0.066), (0.86, 0.088), (0.74, 0.104), (0.56, 0.115), (0.33, 0.121), (0.0, 0.123)]
    def raise_front(k, t, x, y, z):                     # trucker: tall flat-ish front panel (local -y = cap front)
        f = max(0.0, -y / b) ** 2.0
        return (x, y * (1.0 + 0.04 * f), z * (1.0 + 0.10 * f))
    bm = A.lathe(prof, a, b, e=2.6, n=72, cap_bottom=False, shape=raise_front)
    # snapback opening at the cap's back (local +y -> character front): delete low faces in the back sector
    dele = []
    for f in bm.faces:
        c = f.calc_center_median()
        ang = math.atan2(c.y, c.x)
        if c.z < 0.040 and abs(ang - PI / 2) < 0.42:
            dele.append(f)
    bmesh.ops.delete(bm, geom=dele, context='FACES')
    # split front (foam) / back (mesh) panels by local y
    bm2 = bm.copy()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y > -0.035], context='FACES')
    bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if f.calc_center_median().y <= -0.035], context='FACES')
    cap = [A.make_obj('Shotgun_CapFoam', A.transform(bm, H), foam, 'spine_01', solid=0.004),
           A.make_obj('Shotgun_CapMesh', A.transform(bm2, H), mesh, 'spine_01', solid=0.004)]
    A.uv_box(cap[1], 30.0)
    # panel seams + top button
    seam = A.mat_plain('M_TruckerSeam', '#d9cfbd', rough=0.6, bump=0.0)
    for k in range(6):
        ang = k / 6 * 2 * PI + PI / 6
        pts = []
        for (s, z) in prof[1:-1]:
            fz = max(0.0, -(b * s * math.sin(ang)) / b) ** 2.0
            pts.append(Vector((a * s * math.cos(ang) * 1.002, b * s * math.sin(ang) * (1 + 0.04 * fz) * 1.002, z * (1 + 0.10 * fz) + 0.0035)))
        if len(pts) > 2:
            bm = A.tube(pts, 0.0014, n=6)
            cap.append(A.make_obj('Shotgun_Seam%d' % k, A.transform(bm, H), seam, 'spine_01'))
    bm = A.lathe([(1.0, 0.0), (1.0, 0.004), (0.7, 0.0075), (0.0, 0.0085)], 0.011, 0.011, n=24)
    A.transform(bm, Matrix.Translation((0, 0, 0.123 + 0.002)))
    cap.append(A.make_obj('Shotgun_Button', A.transform(bm, H), foam, 'spine_01'))
    # bill: curved visor out of the cap's front (local -y), which is the character's back
    verts = []; faces = []
    nu, nv = 16, 8
    for i in range(nu + 1):
        u = i / nu * 2 - 1                                     # across
        for j in range(nv + 1):
            v = j / nv                                         # outwards
            bx = u * (a * 0.86) * (1 - 0.18 * v ** 2)
            by = -(b * 0.96) * math.sqrt(max(0.0, 1 - (bx / (a * 1.0)) ** 2)) - v * 0.125 * (1 - 0.55 * u * u)
            bz = 0.006 - 0.022 * u * u - 0.014 * v * v
            verts.append(Vector((bx, by, bz)))
    for i in range(nu):
        for j in range(nv):
            q = i * (nv + 1) + j
            faces.append((q, q + nv + 1, q + nv + 2, q + 1))
    bm = A.bm_from(verts, faces)
    cap.append(A.make_obj('Shotgun_Bill', A.transform(bm, H), foam, 'spine_01', solid=0.007))
    # snapback strap across the opening, with studs
    sp = []
    for i in range(17):
        t = i / 16; ang = PI / 2 - 0.40 + 0.80 * t
        sp.append(Vector((a * 0.985 * math.cos(ang), b * 0.985 * math.sin(ang), 0.012)))
    bm = A.ribbon(sp, 0.016, lambda t, tan: Vector((0, 0, 0)) + (Vector((sp[int(t * 16)].x / a, sp[int(t * 16)].y / b, 0)).normalized()))
    cap.append(A.make_obj('Shotgun_Strap', A.transform(bm, H), strap, 'spine_01', solid=0.003))
    for k in range(5):
        ang = PI / 2 - 0.30 + 0.15 * k
        p = Vector((a * 1.0 * math.cos(ang), b * 1.0 * math.sin(ang), 0.012))
        nrm = Vector((math.cos(ang) / a, math.sin(ang) / b, 0)).normalized()
        st = A.lathe([(1.0, 0.0), (1.0, 0.0012), (0.6, 0.0022), (0.0, 0.0025)], 0.0032, 0.0032, n=14)
        xx = Vector((0, 0, 1)).cross(nrm).normalized(); yy = nrm.cross(xx)
        A.transform(st, A.frame_matrix(p, xx, yy, nrm))
        cap.append(A.make_obj('Shotgun_Stud%d' % k, A.transform(st, H), stud, 'spine_01'))
    print('shotgun cap settle', A.settle(P, cap, Vector(H.col[2][:3]), clear=0.002, check=cap[:2]))
    obs += cap
    # ---- angry eyebrows: thick, slanted down to the middle, resting on the top of each googly eye
    hair = A.mat_hair('M_ShotgunHair', '#4a2f1c', '#6b4429')
    for (eye, sgn) in ((EYE_R, -1), (EYE_L, 1)):
        pts = []
        for i in range(13):
            t = i / 12
            x = eye.x - sgn * 0.045 + sgn * 0.11 * t                     # inner -> outer
            z = eye.z + 0.050 + 0.030 * t - 0.012 * (1 - t) ** 2
            p, _ = face_point(P, x, z, 0.004)
            pts.append(p)
        bm = A.tube(pts, lambda t: 0.0115 * (1 - 0.45 * t) + 0.002 * math.sin(t * PI), n=12, flat=0.55)
        def fuzz(v):
            return v + Vector((0, 0, 1)) * 0.0015 * noise.noise(v * 400.0)
        A.displace(bm, fuzz)
        obs.append(A.make_obj('Shotgun_Brow%s' % ('L' if sgn > 0 else 'R'), bm, hair, 'spine_01'))
    # ---- big bushy mutton chops down both sides of the face, curling in toward the mouth
    for sgn in (-1, 1):
        seeds = []
        # a solid base pad so it reads as one big mass
        base_pts = []
        for i in range(10):
            t = i / 9
            x = sgn * (0.192 - 0.075 * t ** 1.6); z = 0.80 - 0.18 * t
            p, _ = face_point(P, x, z, 0.002)
            base_pts.append(p)
        bm = A.tube(base_pts, lambda t: 0.022 * math.sin(PI * (0.15 + 0.85 * t)) ** 0.6 + 0.006, n=12, flat=0.55)
        pad = A.make_obj('Shotgun_ChopPad%s' % ('L' if sgn > 0 else 'R'), bm, hair, 'spine_01')
        obs.append(pad)
        for i in range(60):
            t = rng.random()
            x = sgn * (0.192 - 0.075 * t ** 1.6) + rng.uniform(-0.016, 0.016)
            z = 0.80 - 0.18 * t + rng.uniform(-0.014, 0.014)
            root, nor = face_point(P, x, z, -0.004)
            dirn = Vector((sgn * rng.uniform(0.15, 0.6) * (1 - t) - sgn * 0.5 * t, rng.uniform(-0.7, -0.3), rng.uniform(-1.0, -0.4))).normalized()
            seeds.append((root, dirn, rng.uniform(0.025, 0.05), rng.uniform(0.006, 0.010)))
        obs.append(hair_tufts(P, 'Shotgun_Chops%s' % ('L' if sgn > 0 else 'R'), hair, seeds, rng))
    # ---- shotgun shells pushed into the cheese holes, like a bandolier
    hull = A.mat_plain('M_ShellHull', '#b4231f', rough=0.38, col2='#8f1915', nscale=60, bump=0.05)
    brass = A.mat_metal('M_ShellBrass', '#d9a441', rough=0.28)
    prim = A.mat_metal('M_ShellPrimer', '#c9c2b6', rough=0.3)
    holes = [((-0.140, 0.646), Vector((0.10, -1, 0.25))), ((0.039, 0.649), Vector((-0.05, -1, 0.30))),
             ((0.123, 0.602), Vector((-0.15, -1, 0.35)))]
    for k, ((hx, hz), ax) in enumerate(holes):
        loc, nor = P.hit((hx, -1.0, hz), (0, 1, 0))
        base = Vector((hx, A.FRONT_Y, hz))
        obs += shotgun_shell(P, 'Shotgun_Shell%d' % k, base, ax.normalized(), hull, brass, prim, depth=0.45)
    # two more in the big holes on the right side face
    for k, (y, z, ax) in enumerate(((-0.098, 0.643, Vector((-1, -0.25, 0.25))), (0.066, 0.795, Vector((-1, 0.1, 0.35))))):
        loc, nor = P.hit((-1.0, y, z), (1, 0, 0))
        base = Vector((loc.x if loc is not None else -0.19, y, z))
        obs += shotgun_shell(P, 'Shotgun_ShellS%d' % k, base, ax.normalized(), hull, brass, prim, depth=0.4)
    return obs


BUILDERS['MrShotgun'] = mrshotgun


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


def shotgun_shell(P, name, base_pt, axis, hull, brass, prim, depth=0.6, L=0.064, R=0.0118):
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
    foam = A.mat_felt('M_TruckerFront', '#b3302a', '#9a2822', rough=0.7, fiber=0.25)
    mesh = A.mat_image('M_TruckerMesh', 'trucker_mesh.png', rough=0.8, bump=0.0, tint='#efe7d6')
    strap = A.mat_plain('M_Snapback', '#2b2a2a', rough=0.45, bump=0.02)
    stud = A.mat_plain('M_SnapStud', '#ece7df', rough=0.3, bump=0.0)
    a, b = 0.172, 0.150
    H = hat_frame(T, fwd=math.radians(-6), side=math.radians(4), lift=-0.010, shift=(-0.010, 0.006), pivot=(0, b, 0))
    H = H @ Matrix.Rotation(PI, 4, 'Z')                 # turned round: local -y (cap front) points to the character's back
    prof = [(1.0, 0.0), (0.995, 0.018), (0.975, 0.042), (0.935, 0.066), (0.86, 0.088), (0.74, 0.104), (0.56, 0.115), (0.33, 0.121), (0.0, 0.123)]
    def raise_front(k, t, x, y, z):                     # trucker: tall, flatter front panel
        f = max(0.0, -y / b) ** 2.0
        return (x, y * (1.0 + 0.04 * f), z * (1.0 + 0.10 * f))
    bm = A.lathe(prof, a, b, e=2.6, n=72, cap_bottom=False, shape=raise_front)
    dele = [f for f in bm.faces if f.calc_center_median().z < 0.040 and abs(math.atan2(f.calc_center_median().y, f.calc_center_median().x) - PI / 2) < 0.42]
    bmesh.ops.delete(bm, geom=dele, context='FACES')     # snapback opening (faces the character's front)
    bm2 = bm.copy()
    bmesh.ops.delete(bm, geom=[f for f in bm.faces if f.calc_center_median().y > -0.035], context='FACES')
    bmesh.ops.delete(bm2, geom=[f for f in bm2.faces if f.calc_center_median().y <= -0.035], context='FACES')
    cap = [A.make_obj('Shotgun_CapFoam', A.transform(bm, H), foam, 'spine_01', solid=0.004),
           A.make_obj('Shotgun_CapMesh', A.transform(bm2, H), mesh, 'spine_01', solid=0.004)]
    A.uv_box(cap[1], 30.0)
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
    A.transform(bm, Matrix.Translation((0, 0, 0.125)))
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
    cap.append(A.make_obj('Shotgun_Bill', A.transform(A.bm_from(verts, faces), H), foam, 'spine_01', solid=0.007))
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
    print('shotgun cap settle', A.settle(P, cap, Vector(H.col[2][:3]), clear=0.002, check=cap[:2]))
    obs += cap
    # angry eyebrows: thick, slanted down to the middle, resting on top of each googly eye
    hair = A.mat_hair('M_ShotgunHair', '#4a2f1c', '#6b4429')
    for (eye, sgn) in ((EYE_R, -1), (EYE_L, 1)):
        pts = []
        for i in range(13):
            t = i / 12
            x = eye.x - sgn * 0.045 + sgn * 0.11 * t
            z = eye.z + 0.050 + 0.030 * t - 0.012 * (1 - t) ** 2
            p, _ = face_point(P, x, z, 0.004)
            pts.append(p)
        bm = A.tube(pts, lambda t: 0.0115 * (1 - 0.45 * t) + 0.002 * math.sin(t * PI), n=12, flat=0.55)
        A.displace(bm, lambda v: v + Vector((0, 0, 1)) * 0.0015 * noise.noise(v * 400.0))
        obs.append(A.make_obj('Shotgun_Brow%s' % ('L' if sgn > 0 else 'R'), bm, hair, 'spine_01'))
    # big bushy mutton chops down both sides of the face, curling in toward the mouth
    for sgn in (-1, 1):
        base_pts = []
        for i in range(10):
            t = i / 9
            p, _ = face_point(P, sgn * (0.192 - 0.075 * t ** 1.6), 0.80 - 0.18 * t, 0.002)
            base_pts.append(p)
        bm = A.tube(base_pts, lambda t: 0.022 * math.sin(PI * (0.15 + 0.85 * t)) ** 0.6 + 0.006, n=12, flat=0.55)
        obs.append(A.make_obj('Shotgun_ChopPad%s' % ('L' if sgn > 0 else 'R'), bm, hair, 'spine_01'))
        seeds = []
        for i in range(60):
            t = rng.random()
            x = sgn * (0.192 - 0.075 * t ** 1.6) + rng.uniform(-0.016, 0.016)
            z = 0.80 - 0.18 * t + rng.uniform(-0.014, 0.014)
            root, nor = face_point(P, x, z, -0.004)
            dirn = Vector((sgn * rng.uniform(0.15, 0.6) * (1 - t) - sgn * 0.5 * t, rng.uniform(-0.7, -0.3), rng.uniform(-1.0, -0.4))).normalized()
            seeds.append((root, dirn, rng.uniform(0.025, 0.05), rng.uniform(0.006, 0.010)))
        obs.append(hair_tufts(P, 'Shotgun_Chops%s' % ('L' if sgn > 0 else 'R'), hair, seeds, rng))
    # shotgun shells pushed into the cheese holes, like a bandolier
    hull = A.mat_plain('M_ShellHull', '#b4231f', rough=0.38, col2='#8f1915', nscale=60, bump=0.05)
    brass = A.mat_metal('M_ShellBrass', '#d9a441', rough=0.28)
    prim = A.mat_metal('M_ShellPrimer', '#c9c2b6', rough=0.3)
    for k, ((hx, hz), ax) in enumerate((((-0.140, 0.646), Vector((0.10, -1, 0.25))), ((0.039, 0.649), Vector((-0.05, -1, 0.30))),
                                         ((0.123, 0.602), Vector((-0.15, -1, 0.35))))):
        obs += shotgun_shell(P, 'Shotgun_Shell%d' % k, Vector((hx, A.FRONT_Y, hz)), ax.normalized(), hull, brass, prim, depth=0.45)
    for k, (y, z, ax) in enumerate(((-0.098, 0.643, Vector((-1, -0.25, 0.25))), (0.066, 0.795, Vector((-1, 0.1, 0.35))))):
        loc, nor = P.hit((-1.0, y, z), (1, 0, 0))
        obs += shotgun_shell(P, 'Shotgun_ShellS%d' % k, Vector((loc.x if loc is not None else -0.19, y, z)), ax.normalized(), hull, brass, prim, depth=0.4)
    return obs


BUILDERS['MrShotgun'] = mrshotgun
