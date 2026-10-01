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
