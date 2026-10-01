# The twelve CheeseTeam weapons. Each builder fills the WPN collection with parts (joined into one object at export).
import bpy, bmesh, math, random
from mathutils import Vector, Matrix, noise
import wk
from wk import W, MM, PI, rounded, arc, profile, lathe, cyl, box, sphere, tube, ribbon, make, cut, frame, transform

BUILDERS = {}
PIVOT = {}           # grip point (mm, u/v) per weapon: becomes the object origin


def inset(poly, d):
    """offset a closed (u, v) polygon inward by d mm (vertex-normal offset; fine for smooth outlines)"""
    n = len(poly); out = []
    area = sum(poly[i][0] * poly[(i + 1) % n][1] - poly[(i + 1) % n][0] * poly[i][1] for i in range(n))
    sgn = 1.0 if area > 0 else -1.0
    for i in range(n):
        a = Vector(poly[i - 1]); b = Vector(poly[i]); c = Vector(poly[(i + 1) % n])
        t = (c - a).normalized()
        nrm = Vector((-t.y, t.x)) * sgn          # inward for a CCW polygon
        out.append((b.x + nrm.x * d, b.y + nrm.y * d))
    return out


def outline_at(poly, v):
    """front-most / back-most u of a closed outline at height v"""
    us = []
    n = len(poly)
    for i in range(n):
        (u0, v0), (u1, v1) = poly[i], poly[(i + 1) % n]
        if (v0 - v) * (v1 - v) <= 0 and v0 != v1:
            us.append(u0 + (v - v0) / (v1 - v0) * (u1 - u0))
    return (max(us), min(us)) if us else (0.0, 0.0)


def cloth_wrap(name, poly, v0, v1, half_x, mat, knot_side=-1, pad=2.2, seed=3):
    """fabric band wrapped round a grip between heights v0..v1 (mm), knotted at the back, two tails hanging"""
    rng = random.Random(seed)
    N, R = 64, 14
    verts = []; uvs = []; faces = []
    rings = []
    for j in range(R + 1):
        t = j / R
        v = v0 + (v1 - v0) * t
        uf, ub = outline_at(poly, v)
        uc = (uf + ub) / 2; a = (uf - ub) / 2 + pad; b = half_x + pad
        roll = 1.2 * (math.exp(-((t - 0.0) / 0.12) ** 2) + math.exp(-((t - 1.0) / 0.12) ** 2))
        ring = []
        for i in range(N):
            ang = 2 * PI * i / N
            c, s = math.cos(ang), math.sin(ang)
            e = 3.0
            px = math.copysign(abs(c) ** (2 / e), c); py = math.copysign(abs(s) ** (2 / e), s)
            fold = 0.9 * math.sin(ang * 5 + v * 0.35 + 1.3) * math.sin(PI * t) + 0.5 * noise.noise(Vector((ang * 2, v * 0.1, seed)))
            k = 1.0 + (roll + fold) / max(a, b)
            u = uc + a * px * k; x = b * py * k
            verts.append(W(u, v, x)); uvs.append((i / N * 3.0, t * 0.55))
            ring.append(len(verts) - 1)
        rings.append(ring)
    for j in range(R):
        for i in range(N):
            a_ = rings[j][i]; b_ = rings[j][(i + 1) % N]; c_ = rings[j + 1][(i + 1) % N]; d_ = rings[j + 1][i]
            faces.append((a_, b_, c_, d_))
    bm = wk.bm_from(verts, faces)
    uvl = bm.loops.layers.uv.new('UVMap'); bm.verts.index_update()
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = uvs[lp.vert.index]
    obs = [make(name, bm, mat, solid=0.0012 * 1.0)]
    # knot at the back of the grip, mid-height
    vm = (v0 + v1) / 2
    uf, ub = outline_at(poly, vm)
    kc = W(ub - pad - 5.0, vm, 0.0)
    kb = sphere(kc, 0.0068, seg=28, rings=16, scale=(1.15, 0.85, 0.9))
    wk.transform(kb, Matrix.Identity(4))
    for vv in kb.verts:
        d = vv.co - kc
        vv.co = kc + d * (1.0 + 0.22 * noise.noise(d * 900.0 + Vector((seed, 0, 0))))
    wk.set_uv(kb, lambda co: (co.x * 60, co.z * 60))
    obs.append(make(name + 'Knot', kb, mat, subsurf=1))
    for k, (L, sx, tw) in enumerate(((0.050, 1, 0.8), (0.040, -1, -0.6))):
        pts = []
        for i in range(13):
            t = i / 12
            pts.append(kc + Vector((sx * 0.004 * t + 0.003 * math.sin(t * 4 + k), 0.016 * t, -L * t)) +
                       Vector((0, 0.004 * t * t, 0)))
        bm = ribbon(pts, lambda t: 0.017 * (1 - 0.55 * t) + 0.004 * math.sin(t * 9) * t,
                    lambda t, tan: Vector((math.cos(tw * t * 3), 0.0, math.sin(tw * t * 3) * 0.3)).normalized())
        wk.set_uv(bm, lambda co: (co.x * 40 + k, co.z * 40))
        obs.append(make(name + 'Tail%d' % k, bm, mat, solid=0.0010, subsurf=1))
    return obs


# ================================================================== 1. REVOLVER (Outlaw, primary)
def revolver():
    blued = wk.steel('M_RevBlued', base='#14161b', bare='#9ea2a8', rough=0.30, wear=1.0, scratch=0.8)
    blued_dk = wk.steel('M_RevBluedDark', base='#0e0f12', bare='#8d9197', rough=0.36, wear=0.6, scratch=0.5)
    walnut = wk.wood('M_RevWalnut', light='#5a301a', dark='#1f0e06', rough=0.42, ring=45.0, axis='Z')
    lead = wk.steel('M_RevLead', base='#5f6165', bare='#7b7e82', rough=0.55, wear=0.0, scratch=0.0, metallic=0.85)
    brass = wk.steel('M_RevBrass', base='#a8823a', bare='#d4b06a', rough=0.35, wear=0.6, scratch=0.3)
    fabric = wk.fabric_img('M_RevBandana', 'bandana_paisley.png')

    # ---- frame: topstrap, cylinder window, recoil shield, narrowing into the grip
    fr = rounded([(50, 12, 3), (50, -30, 5), (45, -42, 4), (-12, -42, 2), (-30, -38, 0), (-37, -8, 7), (-28, 4, 9),
                  (-14, 11, 7), (-3, 13, 2)])
    win = rounded([(-0.6, -36.3, 1.5), (41.6, -36.3, 1.5), (41.6, 8.3, 1.5), (-0.6, 8.3, 1.5)])
    taper = lambda u, v: -min(5.5, max(0.0, (-7.0 - u)) * 0.45)
    frame_ob = make('Rev_Frame', profile(fr, -17, 17, holes=[win], taper=taper), blued, bevel=0.0009)
    cut(frame_ob, box(W(-16, 4, 0), (0.0076, 0.024, 0.026)), 'hammerslot')        # hammer channel
    cut(frame_ob, box(W(-2.5, 13.5, 0), (0.0022, 0.008, 0.003)), 'rearsight')      # rear sight groove
    cut(frame_ob, cyl(W(30, 0, 0), W(60, 0, 0), 0.0098, n=32), 'barrelbore')       # barrel seat
    # loading gate (right side) and frame screws
    lg = rounded([(-6.5, -21, 2), (-0.8, -21, 1), (-0.8, -7, 1), (-6.5, -7, 2)])
    make('Rev_LoadingGate', profile(lg, -17.6, -16.4), blued_dk, bevel=0.0004)
    for (u, v, side) in ((44, -24, 1), (44, -24, -1), (-20, -26, 1), (-20, -26, -1), (25, -39.5, 1), (25, -39.5, -1)):
        wk.screw(W(u, v, side * 17.0 + (side * -0.6 if u < -10 else 0)), Vector((side, 0, 0)), r=0.0021, mat=blued_dk,
                 name='Rev_Screw', slot_ang=0.3 + u * 0.05)

    # ---- barrel: long hexagonal, bore, crown, front sight blade
    hexr = 9.6
    bar = lathe([(hexr, 44.0), (hexr, 236.0), (hexr - 0.8, 238.0)], n=6, phase=0.0)
    barrel = make('Rev_Barrel', bar, blued, bevel=0.0007, angle=40)
    cut(barrel, cyl(W(150, 0, 0), W(245, 0, 0), 0.0057, n=40), 'bore')
    cut(barrel, lathe([(5.7, 236.5), (7.2, 238.5), (7.2, 240.0)], n=40), 'crown')
    fs = rounded([(226, 7.5, 0), (236, 7.5, 0), (235.5, 13.0, 2.5), (229, 14.5, 1.5)])
    make('Rev_FrontSight', profile(fs, -1.2, 1.2), blued, bevel=0.0003)
    # rifling hint: two lands visible inside the muzzle
    for a in range(6):
        ang = PI / 3 * a + 0.2
        p0 = W(225, 5.4 * math.sin(ang), 5.4 * math.cos(ang)); p1 = W(238.2, 5.4 * math.sin(ang), 5.4 * math.cos(ang))
        make('Rev_Land', cyl(p0, p1, 0.0006, n=6), blued_dk, smooth=False)

    # ---- ejector housing + rod (right side, under the barrel)
    ej = lathe([(0.0, 52.0), (3.6, 52.5), (4.3, 54.0), (4.3, 168.0), (4.0, 170.5), (2.8, 172.0), (0.0, 172.5)], n=24,
               axis_v=-8.5, x=-7.6)
    ejo = make('Rev_EjectorHousing', ej, blued, bevel=0.0004)
    cut(ejo, box(W(110, -8.5, -11.8), (0.0026, 0.090, 0.0022)), 'ejslot')
    make('Rev_EjectorRod', lathe([(1.6, 60.0), (1.6, 176.0)], n=12, axis_v=-8.5, x=-7.6), blued_dk)
    make('Rev_EjectorHead', lathe([(0.0, 174.0), (3.0, 174.5), (3.4, 176.5), (3.4, 180.0), (2.6, 181.5), (0.0, 182.0)], n=20,
                                  axis_v=-8.5, x=-7.6), blued_dk, bevel=0.0003)
    wk.screw(W(166, -2.5, -11.8), Vector((-1, 0, 0)), r=0.0017, mat=blued_dk, name='Rev_Screw')

    # ---- cylinder with six visible chambers (bullet noses inside), stop notches, chamfers
    cax = -14.0
    cy = lathe([(14.0, 0.3), (20.2, 0.3), (21.0, 1.6), (21.0, 39.6), (20.0, 40.8), (8.5, 40.8)], n=72, axis_v=cax)
    cyo = make('Rev_Cylinder', cy, blued, bevel=0.0005)
    for k in range(6):
        ang = PI / 2 + PI / 3 * k
        cv, cx = cax + 14.0 * math.sin(ang), 14.0 * math.cos(ang)
        cut(cyo, cyl(W(26.0, cv, cx), W(42.0, cv, cx), 0.0058, n=32), 'ch%d' % k)
        cut(cyo, lathe([(5.8, 40.0), (6.8, 41.0), (6.8, 42.0)], n=32, axis_v=cv, x=cx), 'chamf%d' % k)
        # round-nose lead bullets seated a little inside
        b = lathe([(5.55, 30.0), (5.55, 34.5), (5.1, 36.2), (3.9, 37.6), (2.0, 38.5), (0.0, 38.8)], n=24, axis_v=cv, x=cx)
        make('Rev_Bullet%d' % k, b, lead)
        # stop notch between chambers on the outside
        a2 = ang + PI / 6
        nv, nx = cax + 21.0 * math.sin(a2), 21.0 * math.cos(a2)
        nb = box((0, 0, 0), (0.0032, 0.0062, 0.0030))
        dirn = Vector((math.cos(a2), 0, math.sin(a2)))
        transform(nb, frame(W(14.5, nv, nx), Vector((0, 1, 0)).cross(dirn).normalized(), Vector((0, 1, 0)), dirn) @
                  Matrix.Translation((0, 0, 0.0)))
        cut(cyo, nb, 'stop%d' % k)
    # cylinder base pin (front of frame, under the barrel)
    make('Rev_BasePin', lathe([(3.2, 40.0), (3.2, 57.0), (4.2, 57.0), (4.4, 59.0), (4.0, 60.0), (0.0, 60.3)], n=24, axis_v=cax),
         blued_dk, bevel=0.0003)

    # ---- hammer with a wide checkered spur
    hm = rounded([(-7.5, 7, 1.5), (-7.5, -7, 2), (-15, -15, 4), (-22, -11, 4), (-26, 1, 6), (-31, 10, 4), (-34, 14, 2),
                  (-26, 17, 3), (-17, 12, 4), (-12, 10.5, 2)])
    make('Rev_Hammer', profile(hm, -3.6, 3.6), blued_dk, bevel=0.0005)
    sp = rounded([(-26.5, 14.5, 2), (-35, 13, 3), (-40, 17, 3), (-38, 21.5, 3), (-27.5, 19, 2)])
    spur = make('Rev_HammerSpur', profile(sp, -7.2, 7.2), blued_dk, bevel=0.0007)
    for k in range(7):
        u = -29.0 - k * 1.45
        g = box((0, 0, 0), (0.016, 0.0006, 0.0012))
        transform(g, Matrix.Translation(W(u, 20.4 + (u + 29) * -0.12, 0)) @ Matrix.Rotation(math.radians(-14), 4, 'X'))
        cut(spur, g, 'knurl%d' % k)

    # ---- trigger and trigger guard
    tg = rounded([(4.5, -41, 0), (3.5, -50, 4), (0.5, -58, 4), (-4, -63.5, 2), (-6.3, -62.5, 2), (-3.5, -56, 4), (-1.5, -49, 4),
                  (-1.5, -41, 0)])
    make('Rev_Trigger', profile(tg, -2.4, 2.4), blued_dk, bevel=0.0005)
    gp = [Vector(W(u, v, 0)) for (u, v) in
          [(16, -41.5), (16.5, -48), (14, -58), (8, -65.5), (-1, -68.5), (-9, -66.5), (-14.5, -59), (-16.5, -49), (-17.5, -42)]]
    sm = []
    for i in range(len(gp) - 1):
        for k in range(4):
            t = k / 4
            sm.append(gp[i].lerp(gp[i + 1], t))
    sm.append(gp[-1])
    make('Rev_TriggerGuard', tube(sm, 0.0046, n=16, flat=0.36), blued, bevel=0.0)

    # ---- grip: steel grip frame strap + dark walnut panels
    gr_raw = [(-10, -39, 0), (-12.5, -60, 12), (-20, -97, 14), (-25.5, -114, 6), (-47, -119, 7), (-53, -110, 6),
              (-47, -76, 18), (-39, -44, 14), (-34, -18, 6), (-29, -8, 0)]
    grip = rounded(gr_raw, n=8)
    make('Rev_GripFrame', profile(grip, -6.6, 6.6), blued, bevel=0.0008)
    panel = inset(grip, 1.6)
    for sgn in (-1, 1):
        x0, x1 = (6.4, 15.6) if sgn > 0 else (-15.6, -6.4)
        make('Rev_GripPanel%s' % ('L' if sgn > 0 else 'R'), profile(panel, x0, x1), walnut, bevel=0.0042, seg=5, angle=30)
        wk.screw(W(-32, -72, sgn * 15.6), Vector((sgn, 0, 0)), r=0.0026, mat=blued_dk, name='Rev_GripScrew')

    # ---- red bandana wrapped round the bottom of the grip
    cloth_wrap('Rev_Bandana', grip, -111.0, -88.0, 15.6, fabric)

    PIVOT['Revolver'] = (-30.0, -72.0)
    return 'Revolver'


BUILDERS['Revolver'] = revolver


def build(name):
    wk.new_scene()
    BUILDERS[name]()
    # move the grip point to the origin
    pu, pv = PIVOT.get(name, (0.0, 0.0))
    off = -W(pu, pv, 0)
    for ob in list(wk.coll().objects) + list(wk.coll('CUTTERS').objects):
        ob.data.transform(Matrix.Translation(off))
    wk.finalize()
    return name
