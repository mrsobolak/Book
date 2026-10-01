# The twelve CheeseTeam weapons. Each builder fills the WPN collection with parts (joined into one object at export).
import bpy, bmesh, math, random, os
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


# ================================================================== grips (lofted, oval sections)
def _bez(p0, p1, p2, t):
    return Vector(((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0],
                   (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]))


class Grip:
    """handle along a quadratic spine in the side plane (mm). depth(t) -> (front, back) half-depths, width(t) half-width."""
    def __init__(self, p0, p1, p2, depth, width, e=2.3, butt=0.06):
        self.p = (p0, p1, p2); self.depth = depth; self.width = width; self.e = e; self.butt = butt

    def centre(self, t):
        return _bez(*self.p, t)

    def frame2(self, t):
        a = _bez(*self.p, max(0.0, t - 0.01)); b = _bez(*self.p, min(1.0, t + 0.01))
        T = (b - a).normalized()
        D = Vector((-T.y, T.x))
        if D.x < 0:
            D = -D
        return T, D

    def point(self, t, th, k=1.0, pad=0.0):
        c = self.centre(t); T, D = self.frame2(t)
        cu, sx = math.cos(th), math.sin(th)
        pu = math.copysign(abs(cu) ** (2 / self.e), cu); px = math.copysign(abs(sx) ** (2 / self.e), sx)
        fa, ba = self.depth(t)
        a = (fa if pu > 0 else ba)
        # rounded butt: the last few mm pull in
        if t > 1 - self.butt:
            q = (t - (1 - self.butt)) / self.butt
            k *= math.sqrt(max(0.0, 1 - q ** 3.0)) * 0.6 + 0.4 if q < 1 else 0.4
        uv = c + D * pu * (a * k + pad)
        return W(uv.x, uv.y, px * (self.width(t) * k + pad))

    def rings(self, t0, t1, th0, th1, nt=36, nth=24, k=1.0, pad=0.0, fn=None):
        R = []
        for j in range(nt + 1):
            t = t0 + (t1 - t0) * j / nt
            ring = []
            for i in range(nth + 1):
                th = th0 + (th1 - th0) * i / nth
                kk = k * (fn(t, th) if fn else 1.0)
                ring.append(self.point(t, th, kk, pad))
            R.append(ring)
        return R


def grip_parts(name, g, wood_m, steel_m, strap=0.36, t0=0.0, t1=1.0, nt=40):
    """wood panels on the sides, steel front strap + backstrap (flush, with a little seam), rounded butt"""
    ths = math.asin(max(0.0, min(1.0, strap ** (g.e / 2))))
    obs = []
    edge = lambda t, th: 1.0
    for side in (1, -1):
        a0, a1 = (ths, PI - ths) if side > 0 else (PI + ths, 2 * PI - ths)
        R = g.rings(t0, t1, a0, a1, nt=nt, nth=26)
        for ring in R:                       # roll the panel edges into the seam
            n = len(ring); c = sum(ring, Vector()) / n
            for i in (0, n - 1):
                ring[i] = ring[i].lerp(c, 0.035)
        obs.append(make('%s_Panel%s' % (name, 'L' if side > 0 else 'R'), wk.loft(R, closed=False), wood_m, smooth=True))
    for (a0, a1, nm) in ((-ths - 0.12, ths + 0.12, 'FrontStrap'), (PI - ths - 0.12, PI + ths + 0.12, 'Backstrap')):
        R = g.rings(t0, t1, a0, a1, nt=nt, nth=10, k=0.992)
        obs.append(make('%s_%s' % (name, nm), wk.loft(R, closed=False), steel_m, solid=0.002))
    # butt: closed cap under everything
    R = g.rings(t1 - 0.004, t1, 0.0, 2 * PI, nt=1, nth=48, k=0.985)
    obs.append(make(name + '_Butt', wk.loft([R[-1]], closed=True, cap0=True), steel_m, smooth=True))
    return obs


def cloth_wrap(name, g, t0, t1, mat, pad=1.8, seed=3):
    """fabric band wrapped round a lofted grip between t0..t1, knotted at the back, two tails hanging"""
    N, R = 72, 16
    rings = []; uvs = []
    for j in range(R + 1):
        t = t0 + (t1 - t0) * j / R; tt = j / R
        roll = 1.1 * (math.exp(-(tt / 0.10) ** 2) + math.exp(-((tt - 1) / 0.10) ** 2))
        ring = []
        for i in range(N):
            th = 2 * PI * i / N
            fold = 0.8 * math.sin(th * 5 + tt * 7 + 1.3) * math.sin(PI * tt) + 0.45 * noise.noise(Vector((th * 2, tt * 4, seed)))
            ring.append(g.point(t, th, 1.0, pad + roll + fold))
            uvs.append((i / N * 3.0, tt * 0.6))
        rings.append(ring)
    obs = [make(name, wk.loft(rings, closed=True, uvs=uvs), mat, solid=0.0012)]
    kc = g.point((t0 + t1) / 2, PI, 1.0, pad + 5.0)
    kb = sphere(kc, 0.0068, seg=28, rings=16, scale=(1.0, 0.9, 1.15))
    for vv in kb.verts:
        d = vv.co - kc
        vv.co = kc + d * (1.0 + 0.22 * noise.noise(d * 900.0 + Vector((seed, 0, 0))))
    wk.set_uv(kb, lambda co: (co.x * 60, co.z * 60))
    obs.append(make(name + 'Knot', kb, mat, subsurf=1))
    T, D = g.frame2((t0 + t1) / 2)
    back = -Vector((0, D.x, 0)).normalized() if D.x else Vector((0, 1, 0))
    for k, (L, sx, tw) in enumerate(((0.048, 1, 0.8), (0.038, -1, -0.6))):
        pts = [kc + Vector((sx * 0.005 * t + 0.003 * math.sin(t * 4 + k), 0.012 * t + 0.004 * t * t, -L * t)) for t in [i / 12 for i in range(13)]]
        bm = ribbon(pts, lambda t: 0.016 * (1 - 0.55 * t) + 0.004 * math.sin(t * 9) * t,
                    lambda t, tan: Vector((math.cos(tw * t * 3), 0.0, math.sin(tw * t * 3) * 0.3)).normalized())
        wk.set_uv(bm, lambda co: (co.x * 40 + k, co.z * 40))
        obs.append(make(name + 'Tail%d' % k, bm, mat, solid=0.0010, subsurf=1))
    return obs


# ================================================================== 1. REVOLVER (Outlaw, primary)
def revolver():
    blued = wk.steel('M_RevBlued', base='#14171d', bare='#b4b7bc', rough=0.27, wear=1.6, scratch=1.0, edge_gain=14.0)
    blued_dk = wk.steel('M_RevBluedDark', base='#0f1013', bare='#a6a9ae', rough=0.32, wear=1.2, scratch=0.6, edge_gain=14.0)
    walnut = wk.wood('M_RevWalnut', light='#3f2111', dark='#1a0b05', rough=0.36, ring=22.0, axis='Z', grain=0.45)
    lead = wk.steel('M_RevLead', base='#606266', bare='#7b7e82', rough=0.55, wear=0.0, scratch=0.0, metallic=0.85)
    fabric = wk.fabric_img('M_RevBandana', 'bandana_paisley.png', sat=1.35, val=0.85)

    # ---- frame, built like the real thing from rounded parts (no flat slab)
    cax = -14.0
    fo = rounded([(-8.2, 11.0, 3), (-3.0, 13.2, 2), (43.0, 13.2, 3), (48.5, 11.5, 3), (48.5, -20.0, 4), (44.0, -37.5, 8),
                  (28.0, -41.6, 14), (6.0, -42.3, 6), (-8.2, -42.5, 0)], n=8)
    win = rounded([(-0.6, -35.8, 3.0), (41.6, -35.8, 3.0), (41.6, 8.3, 3.0), (-0.6, 8.3, 3.0)], n=8)
    fob = make('Rev_Frame', profile(fo, -14.6, 14.6, holes=[win]), blued, bevel=0.0019, seg=5, angle=30)
    cut(fob, box(W(-1.5, 13.6, 0), (0.0022, 0.009, 0.0034)), 'rearsight')
    cut(fob, cyl(W(40.0, 0, 0), W(60, 0, 0), 0.0096, n=48), 'barrelseat')
    # hammer housing / top of the grip frame, narrower than the shield
    hh = rounded([(-7.0, 9.5, 2), (-14, 10.5, 7), (-27, 3.0, 8), (-33, -8.0, 6), (-29, -26.0, 0), (-20, -42.5, 0), (-7.0, -42.5, 0)], n=8)
    house = make('Rev_HammerHousing', profile(hh, -10.6, 10.6), blued, bevel=0.0024, seg=5, angle=30)
    cut(house, box(W(-17, 4, 0), (0.0072, 0.024, 0.030)), 'hammerslot')
    lg = rounded([(-6.5, -22, 2), (-0.8, -22, 1), (-0.8, -6, 1), (-6.5, -6, 2)])
    make('Rev_LoadingGate', profile(lg, -15.4, -14.3), blued_dk, bevel=0.0005)
    for (u, v, x) in ((45.0, -15.5, 14.6), (45.0, -15.5, -14.6), (-20.0, -27.0, 10.6), (-20.0, -27.0, -10.6),
                      (24.0, -39.5, 14.6), (24.0, -39.5, -14.6), (-4.0, -39.0, 14.6), (-4.0, -39.0, -14.6)):
        wk.screw(W(u, v, x), Vector((1 if x > 0 else -1, 0, 0)), r=0.0019, mat=blued_dk, name='Rev_Screw', slot_ang=0.3 + u * 0.05)

    # ---- barrel: long octagon-style hex, muzzle crown, bore, front sight blade
    hexr = 9.2
    bar = lathe([(hexr, 44.0), (hexr, 236.0), (hexr - 0.9, 238.0)], n=6, phase=0.0)
    barrel = make('Rev_Barrel', bar, blued, bevel=0.0006, seg=3, angle=40)
    cut(barrel, cyl(W(150, 0, 0), W(245, 0, 0), 0.0057, n=48), 'bore')
    cut(barrel, lathe([(5.7, 236.6), (7.0, 238.6), (7.0, 240.0)], n=48), 'crown')
    fs = rounded([(226, 7.0, 0), (236, 7.0, 0), (235.5, 12.5, 2.5), (229, 14.0, 1.5)])
    make('Rev_FrontSight', profile(fs, -1.1, 1.1), blued, bevel=0.0003)
    for a in range(6):
        ang = PI / 3 * a + 0.2
        make('Rev_Land', cyl(W(225, 5.45 * math.sin(ang), 5.45 * math.cos(ang)), W(238.3, 5.45 * math.sin(ang), 5.45 * math.cos(ang)),
                             0.0006, n=6), blued_dk, smooth=False)

    # ---- ejector housing + rod (right side under the barrel)
    ej = lathe([(0.0, 50.0), (3.4, 50.5), (4.1, 52.0), (4.1, 166.0), (3.8, 168.5), (2.6, 170.0), (0.0, 170.5)], n=28, axis_v=-8.6, x=-7.2)
    ejo = make('Rev_EjectorHousing', ej, blued, bevel=0.0004)
    cut(ejo, box(W(108, -8.6, -11.1), (0.0022, 0.088, 0.0020)), 'ejslot')
    make('Rev_EjectorRod', lathe([(1.5, 60.0), (1.5, 175.0)], n=12, axis_v=-8.6, x=-7.2), blued_dk)
    make('Rev_EjectorHead', lathe([(0.0, 172.0), (2.8, 172.5), (3.2, 174.5), (3.2, 178.0), (2.4, 179.5), (0.0, 180.0)], n=24,
                                  axis_v=-8.6, x=-7.2), blued_dk, bevel=0.0003)
    wk.screw(W(162, -3.0, -10.9), Vector((-1, 0, 0)), r=0.0016, mat=blued_dk, name='Rev_Screw')

    # ---- cylinder: six visible chambers with bullet noses, stop notches, chamfers
    cy = lathe([(13.0, 0.3), (19.9, 0.3), (20.8, 1.7), (20.8, 39.4), (19.8, 40.8), (8.0, 40.8)], n=96, axis_v=cax)
    cyo = make('Rev_Cylinder', cy, blued, bevel=0.0005)
    for k in range(6):
        ang = PI / 2 + PI / 3 * k
        cv, cx = cax + 14.0 * math.sin(ang), 14.0 * math.cos(ang)
        cut(cyo, cyl(W(26.0, cv, cx), W(42.0, cv, cx), 0.0058, n=40), 'ch%d' % k)
        cut(cyo, lathe([(5.8, 40.1), (6.6, 41.0), (6.6, 42.0)], n=40, axis_v=cv, x=cx), 'chamf%d' % k)
        make('Rev_Bullet%d' % k, lathe([(5.55, 30.0), (5.55, 34.5), (5.1, 36.2), (3.9, 37.6), (2.0, 38.5), (0.0, 38.8)], n=28,
                                       axis_v=cv, x=cx), lead)
        a2 = ang + PI / 6
        dirn = Vector((math.cos(a2), 0, math.sin(a2)))
        nb = box((0, 0, 0), (0.0030, 0.0060, 0.0028))
        transform(nb, frame(W(14.5, cax + 20.8 * math.sin(a2), 20.8 * math.cos(a2)), Vector((0, 1, 0)).cross(dirn).normalized(),
                            Vector((0, 1, 0)), dirn))
        cut(cyo, nb, 'stop%d' % k)
    make('Rev_BasePin', lathe([(3.0, 40.0), (3.0, 49.0), (4.0, 49.0), (4.2, 51.0), (3.8, 52.0), (0.0, 52.3)], n=24, axis_v=cax),
         blued_dk, bevel=0.0003)

    # ---- hammer with a wide checkered spur
    hm = rounded([(-7.5, 7, 1.5), (-7.5, -7, 2), (-15, -15, 4), (-22, -11, 4), (-26, 1, 6), (-31, 10, 4), (-34, 14, 2),
                  (-26, 17, 3), (-17, 12, 4), (-12, 10.5, 2)])
    make('Rev_Hammer', profile(hm, -3.4, 3.4), blued_dk, bevel=0.0006)
    sp = rounded([(-26.5, 14.5, 2), (-35, 13, 3), (-40, 17, 3), (-38, 21.5, 3), (-27.5, 19, 2)])
    spur = make('Rev_HammerSpur', profile(sp, -6.8, 6.8), blued_dk, bevel=0.0008, seg=4)
    for k in range(7):
        u = -29.0 - k * 1.45
        gb = box((0, 0, 0), (0.016, 0.0006, 0.0012))
        transform(gb, Matrix.Translation(W(u, 20.4 + (u + 29) * -0.12, 0)) @ Matrix.Rotation(math.radians(-14), 4, 'X'))
        cut(spur, gb, 'knurl%d' % k)

    # ---- trigger + trigger guard
    tg = rounded([(4.5, -41, 0), (3.5, -50, 4), (0.5, -58, 4), (-4, -63.5, 2), (-6.3, -62.5, 2), (-3.5, -56, 4), (-1.5, -49, 4),
                  (-1.5, -41, 0)])
    make('Rev_Trigger', profile(tg, -2.3, 2.3), blued_dk, bevel=0.0005)
    gp = [Vector(W(u, v, 0)) for (u, v) in
          [(15, -41.0), (16.5, -49), (13.5, -59), (6, -66.0), (-3, -67.5), (-10, -63.5), (-13.0, -55), (-13.0, -46)]]
    sm = wk.spline(gp, 8)
    make('Rev_TriggerGuard', tube(sm, 0.0045, n=20, flat=0.42), blued)

    # ---- grip: plow-handle, oval sections; walnut panels between steel straps; bandana at the bottom
    g = Grip((-20.5, -30.0), (-19.0, -80.0), (-45.0, -110.0),
             depth=lambda t: (11.5 + 2.5 * math.sin(PI * min(1.0, t * 1.1)), 12.0 + 4.0 * t),
             width=lambda t: 14.0 + 1.6 * math.sin(PI * t * 0.9), e=2.4, butt=0.05)
    grip_parts('Rev_Grip', g, walnut, blued)
    for sgn in (1, -1):
        p = g.point(0.42, PI / 2 if sgn > 0 else -PI / 2, 1.0, 0.2)
        wk.screw(p, Vector((sgn, 0, 0)), r=0.0024, mat=blued_dk, name='Rev_GripScrew')
    cloth_wrap('Rev_Bandana', g, 0.70, 0.93, fabric)

    c = g.centre(0.45)
    PIVOT['Revolver'] = (c.x, c.y)
    return 'Revolver'


BUILDERS['Revolver'] = revolver


# ================================================================== 2. DERRINGER (Outlaw, secondary)
def derringer():
    nickel = wk.steel('M_DerNickel', base='#8f8b83', bare='#a5803f', rough=0.16, wear=1.3, scratch=1.0, edge_gain=12.0, tint_var=0.04)
    nickel_dk = wk.steel('M_DerNickelDark', base='#77736c', bare='#8f6f37', rough=0.30, wear=0.8, scratch=0.6, edge_gain=12.0)
    bore = wk.steel('M_DerBore', base='#1b1b1c', bare='#3a3a3c', rough=0.5, wear=0.0, scratch=0.0)
    pearl = wk.pearl('M_DerPearl')

    # ---- barrels: two round tubes fused into a figure-8, joined by a web, top rib, hinge lug at the top rear
    tubes = []
    for (bv, nm) in ((6.2, 'up'), (-6.7, 'dn')):
        t = make('Der_Barrel_' + nm, lathe([(7.4, 0.0), (7.6, 1.0), (7.6, 74.5), (7.0, 76.0)], n=64, axis_v=bv), nickel,
                 bevel=0.0008, angle=40)
        cut(t, cyl(W(20.0, bv, 0), W(80.0, bv, 0), 0.0052, n=40), 'bore')
        cut(t, lathe([(5.2, 75.3), (6.2, 76.3), (6.2, 78.0)], n=40, axis_v=bv), 'crown')
        make('Der_Bore_' + nm, lathe([(5.25, 40.0), (5.25, 75.0)], n=32, axis_v=bv, cap0=True, cap1=False), bore)
        tubes.append(t)
    web = rounded([(1.0, -1.0, 0), (74.0, -1.0, 0), (74.0, 1.0, 0), (1.0, 1.0, 0)])
    make('Der_Web', profile(web, -5.6, 5.6), nickel, bevel=0.0006)
    rib = rounded([(2.0, 11.5, 0), (73.5, 11.5, 0), (72.5, 15.6, 1.5), (3.0, 15.6, 1.5)])
    make('Der_Rib', profile(rib, -2.4, 2.4), nickel, bevel=0.0007)
    make('Der_FrontSight', sphere(W(70.5, 15.6, 0), 0.0016, seg=16, rings=8, scale=(0.8, 1.6, 1.0)), nickel)
    hl = rounded([(-4.0, 11.0, 3), (5.0, 11.0, 0), (5.0, 18.0, 3.5), (-4.0, 18.0, 3.5)])
    make('Der_HingeLug', profile(hl, -5.0, 5.0), nickel, bevel=0.0010)
    for side in (1, -1):
        make('Der_HingePin%d' % side, cyl(W(0.5, 14.5, side * 5.0), W(0.5, 14.5, side * 6.2), 0.0021, n=20), nickel_dk)

    # ---- frame: hammer housing + recoil shield behind the barrels, lip under them, spur-trigger sheath
    fr = rounded([(0.0, 11.0, 0), (0.0, -13.0, 0), (12.0, -13.0, 0), (12.0, -16.5, 2), (-4.0, -17.5, 3), (-9.0, -24.0, 2.5),
                  (-12.5, -24.0, 2), (-13.5, -15.0, 0), (-24.0, -12.0, 0), (-28.0, 0.0, 6), (-22.0, 10.0, 6), (-9.0, 12.0, 3)], n=8)
    frm = make('Der_Frame', profile(fr, -8.2, 8.2), nickel, bevel=0.0014, seg=5, angle=30)
    cut(frm, box(W(-16.0, 9.0, 0), (0.0056, 0.020, 0.020)), 'hammerslot')
    cut(frm, box(W(-6.5, -20.5, 0), (0.0040, 0.0060, 0.011)), 'triggerslot')
    # locking lever (right side) + screws
    lv = rounded([(-3.0, 1.0, 2.5), (6.0, 3.5, 1.5), (6.0, 6.5, 1.5), (-3.0, 7.0, 2.5)])
    make('Der_Lever', profile(lv, -9.6, -8.2), nickel_dk, bevel=0.0004)
    wk.screw(W(-1.5, 4.0, -9.6), Vector((-1, 0, 0)), r=0.0016, mat=nickel_dk, name='Der_Screw')
    for (u, v) in ((-17.0, -6.0), (8.0, -15.0)):
        for side in (1, -1):
            wk.screw(W(u, v, side * 8.2), Vector((side, 0, 0)), r=0.0015, mat=nickel_dk, name='Der_Screw', slot_ang=u * 0.1)

    # ---- hammer with checkered spur
    hm = rounded([(-9.5, 6.0, 1.5), (-10.5, -3.0, 2), (-17.0, -6.0, 3), (-22.0, 2.0, 4), (-25.0, 11.0, 3), (-29.0, 17.5, 2),
                  (-26.5, 20.5, 2), (-20.0, 17.0, 3), (-13.5, 12.5, 2)])
    make('Der_Hammer', profile(hm, -2.7, 2.7), nickel_dk, bevel=0.0005)
    sp = rounded([(-24.0, 16.0, 1.5), (-29.5, 16.5, 2), (-31.0, 20.5, 2), (-26.0, 21.5, 1.5)])
    spur = make('Der_HammerSpur', profile(sp, -4.2, 4.2), nickel_dk, bevel=0.0005)
    for k in range(5):
        u = -25.5 - k * 1.1
        gb = box((0, 0, 0), (0.010, 0.00045, 0.0010))
        transform(gb, Matrix.Translation(W(u, 21.3 + (u + 25.5) * 0.15, 0)))
        cut(spur, gb, 'knurl%d' % k)

    # ---- spur trigger (no guard)
    tg = rounded([(-4.6, -17.0, 0), (-5.2, -23.0, 2), (-7.0, -28.5, 2), (-9.3, -29.0, 1.5), (-8.6, -24.5, 2), (-8.0, -17.0, 0)])
    make('Der_Trigger', profile(tg, -1.6, 1.6), nickel_dk, bevel=0.0004)

    # ---- bird's-head grip in pearl between nickel straps
    g = Grip((-18.0, -13.0), (-19.0, -38.0), (-38.0, -50.0),
             depth=lambda t: (8.0 + 2.5 * t, 8.5 + 3.5 * math.sin(PI * min(1.0, t * 1.2))),
             width=lambda t: 8.8 + 1.4 * math.sin(PI * t * 0.8), e=2.3, butt=0.10)
    grip_parts('Der_Grip', g, pearl, nickel, strap=0.32, nt=36)
    for sgn in (1, -1):
        wk.screw(g.point(0.45, PI / 2 if sgn > 0 else -PI / 2, 1.0, 0.15), Vector((sgn, 0, 0)), r=0.0016, mat=nickel_dk,
                 name='Der_GripScrew', slot_ang=1.1)
    c = g.centre(0.40)
    PIVOT['Derringer'] = (c.x, c.y)
    return 'Derringer'


BUILDERS['Derringer'] = derringer


# ================================================================== 3. SAWED-OFF PUMP SHOTGUN (Mr. Shotgun, primary)
def sawedoff():
    black = wk.steel('M_SgParkerized', base='#1c1d1f', bare='#8f9297', rough=0.55, wear=0.8, scratch=1.4, edge_gain=6.0, tint_var=0.08)
    black_dk = wk.steel('M_SgParkDark', base='#141516', bare='#8a8d91', rough=0.5, wear=0.8, scratch=1.0, edge_gain=11.0)
    bare = wk.steel('M_SgSawCut', base='#8d9095', bare='#c4c6c9', rough=0.42, wear=0.0, scratch=2.0)
    bolt = wk.steel('M_SgBolt', base='#6d7075', bare='#b5b8bc', rough=0.3, wear=0.5, scratch=1.0)
    wood = wk.wood('M_SgPumpWood', light='#5a3219', dark='#2a1309', rough=0.5, ring=110.0, axis='Y', wear=1.0, grain=0.4)
    grip_m = wk.rubber('M_SgGripPoly', '#0d0d0e', rough=0.7, stipple=0.8)
    duct = wk.tape('M_SgDuctTape')

    # ---- receiver
    rc = rounded([(0, 21, 7), (163, 23, 3), (170, 19, 2), (170, -18, 2), (161, -24, 3), (8, -24, 3), (0, -17, 7)], n=8)
    recv = make('Sg_Receiver', profile(rc, -15.5, 15.5), black, bevel=0.0032, seg=6, angle=30)
    cut(recv, box(W(122, 1.0 + 8.5, -14.0), (0.007, 0.052, 0.017)), 'ejport')           # ejection port (right)
    cut(recv, box(W(143, -22.0, 0), (0.019, 0.042, 0.008)), 'loadport')                    # loading port (bottom)
    make('Sg_Bolt', profile(rounded([(98, 2, 2), (146, 2, 2), (146, 17, 2), (98, 17, 2)]), -12.5, -8.5), bolt, bevel=0.0006)
    sf = rounded([(6, 21.5, 0), (20, 21.5, 0), (19, 26.5, 2), (7, 26.5, 2)])
    saf = make('Sg_Safety', profile(sf, -5.0, 5.0), black_dk, bevel=0.0006)
    for k in range(4):
        gb = box(W(9.5 + k * 2.6, 27.0, 0), (0.0110, 0.0008, 0.0016)); cut(saf, gb, 'ck%d' % k)
    for (u, v) in ((32, -16), (105, -16), (150, 10)):
        for sd in (1, -1):
            make('Sg_Pin', cyl(W(u, v, sd * 15.3), W(u, v, sd * 16.1), 0.0024, n=20), black_dk)

    # ---- trigger housing with integrated guard + trigger
    th = rounded([(18, -23, 0), (120, -23, 0), (118, -31, 4), (100, -36, 6), (88, -60, 8), (50, -63, 9), (34, -45, 6), (20, -36, 4)], n=8)
    hole = rounded([(54, -38, 5), (84, -38, 5), (80, -55, 7), (57, -56, 7)], n=8)
    make('Sg_TriggerHousing', profile(th, -10.5, 10.5, holes=[hole]), black, bevel=0.0016, seg=4, angle=30)
    tr = rounded([(70, -37, 0), (69, -44, 3), (65, -51, 2), (62.5, -51, 1.5), (65.5, -44, 3), (66, -37, 0)])
    make('Sg_Trigger', profile(tr, -3.0, 3.0), black_dk, bevel=0.0005)

    # ---- cut-down barrel with a rough hacksaw end
    BU = 412.0
    bar = lathe([(11.1, 166.0), (11.1, BU - 3.0), (11.1, BU)], n=64)
    wk.jagged(bar, BU - 2.5, amp_mm=0.9, tilt_deg=2.5, seed=4)
    barrel = make('Sg_Barrel', bar, black, bevel=0.0, smooth=True)
    cut(barrel, cyl(W(300, 0, 0), W(430, 0, 0), 0.0093, n=64), 'bore')
    ring = lathe([(11.15, BU - 3.2), (11.15, BU + 0.4)], n=64, cap0=False, cap1=False)
    wk.jagged(ring, BU - 3.5, amp_mm=0.9, tilt_deg=2.5, seed=4)
    make('Sg_SawBurr', ring, bare, smooth=True)
    make('Sg_BoreInner', lathe([(9.25, 330.0), (9.25, BU + 1.0)], n=48, cap0=True, cap1=False), black_dk)
    # ---- magazine tube, cap, barrel clamp
    MV = -24.5
    make('Sg_MagTube', lathe([(10.8, 166.0), (10.8, 352.0)], n=48, axis_v=MV), black, bevel=0.0)
    cap = lathe([(0, 352.0), (12.4, 352.2), (12.8, 353.5), (12.8, 364.0), (12.2, 366.0), (8.0, 367.0), (0, 367.2)], n=48, axis_v=MV)
    capo = make('Sg_MagCap', cap, black_dk, bevel=0.0004)
    for k in range(18):
        a = 2 * PI * k / 18
        gb = box((0, 0, 0), (0.0012, 0.0080, 0.0016))
        transform(gb, Matrix.Translation(W(358.0, MV + 12.8 * math.sin(a), 12.8 * math.cos(a))) @ Matrix.Rotation(-a + PI / 2, 4, 'Y'))
        cut(capo, gb, 'kn%d' % k)
    cl = rounded([(338, 15.5, 4), (350, 15.5, 4), (350, -38.0, 6), (338, -38.0, 6)])
    clamp = make('Sg_BarrelClamp', profile(cl, -9.0, 9.0), black, bevel=0.0012)
    cut(clamp, cyl(W(330, 0, 0), W(360, 0, 0), 0.0111, n=48), 'b'); cut(clamp, cyl(W(330, MV, 0), W(360, MV, 0), 0.0108, n=48), 'm')
    wk.screw(W(344, -12.0, 9.0), Vector((1, 0, 0)), r=0.0022, mat=black_dk, name='Sg_Screw')

    # ---- wooden pump with grip grooves, action bars back to the receiver
    def oval(i, k, r, a):
        return r * (1.0 + 0.16 * math.cos(a) ** 2) * (1.0 - 0.10 * max(0.0, -math.sin(a)))
    prof = [(11.4, 186.0), (14.5, 188.0), (17.0, 192.0), (18.2, 198.0), (18.2, 202.0)]
    for k in range(10):                                    # shallow rounded grip grooves, part of the surface
        u = 205.0 + k * 8.0
        prof += [(18.2, u), (17.6, u + 1.0), (16.9, u + 2.0), (17.6, u + 3.0), (18.2, u + 4.0)]
    prof += [(18.2, 287.0), (17.0, 292.0), (14.5, 296.0), (11.4, 298.0)]
    pump = lathe(prof, n=72, axis_v=MV, shape=oval, cap0=False, cap1=False)
    pmp = make('Sg_Pump', pump, wood, bevel=0.0, smooth=True)
    for sd in (1, -1):
        make('Sg_ActionBar%d' % sd, profile(rounded([(150, -21.5, 0), (192, -21.5, 0), (192, -16.5, 0), (150, -16.5, 0)]),
                                            sd * 11.0 - 1.1, sd * 11.0 + 1.1), black_dk, bevel=0.0004)

    # ---- pistol grip only (no stock), silver duct tape wrapped round it
    rcap = rounded([(-4, 18, 4), (8, 18, 0), (8, -22, 0), (-4, -22, 6)])
    make('Sg_RearCap', profile(rcap, -14.5, 14.5), black, bevel=0.0026, seg=5)
    g = Grip((24.0, -30.0), (8.0, -80.0), (-22.0, -124.0),
             depth=lambda t: (19.0 + 2.0 * math.sin(PI * t), 21.0 + 2.5 * t), width=lambda t: 13.5 + 1.2 * math.sin(PI * t), e=2.6, butt=0.06)
    fg = lambda t, th: 1.0 - 0.07 * max(0.0, math.cos(th)) ** 4 * max(0.0, math.sin(PI * (t - 0.18) / 0.62 * 3.0)) * (0.18 < t < 0.80)
    R = g.rings(0.0, 1.0, 0.0, 2 * PI, nt=56, nth=56, fn=fg)
    gp = make('Sg_PistolGrip', wk.loft([r[:-1] for r in R], closed=True, cap1=True), grip_m, smooth=True)
    tape_wrap('Sg_DuctTape', g, 0.30, 0.66, duct)

    c = g.centre(0.42)
    PIVOT['SawedOff'] = (c.x, c.y)
    return 'SawedOff'


def tape_wrap(name, g, t0, t1, mat, turns=2.6, width_t=0.11, pad=0.45, seed=5):
    """one strip of tape spiralling round a lofted grip (overlapping itself), crinkled, with a lifted torn end"""
    N = int(64 * turns)
    span = (t1 - t0 - width_t)
    rows = 5
    rings = []
    for r in range(rows + 1):
        ring = []
        for i in range(N + 1):
            s = i / N
            th = 2 * PI * turns * s
            tt = t0 + span * s + width_t * r / rows
            crinkle = 0.22 * noise.noise(Vector((th * 2.5, tt * 40, seed))) + 0.12 * s       # later turns sit on top
            lift = 0.0
            if s > 0.96:                                                                     # torn end lifts off
                lift = (s - 0.96) / 0.04 * 1.4
            ring.append(g.point(min(tt, 0.985), th, 1.0, pad + crinkle + lift))
        rings.append(ring)
    bm = wk.loft(rings, closed=False)
    return [make(name, bm, mat, solid=0.0004)]


BUILDERS['SawedOff'] = sawedoff


# ================================================================== 4. MACHINE PISTOL (Mr. Shotgun, secondary)
def machinepistol():
    finish = wk.paint('M_MpFinish', '#0e0e0f', under='#868a8f', rough=0.62, wear=1.4, scuff=1.4, col_var=0.12)
    finish_dk = wk.paint('M_MpFinishDk', '#0f0f10', under='#7a7d82', rough=0.55, wear=1.0, scuff=0.8)
    steel = wk.steel('M_MpSteel', base='#2a2b2e', bare='#a5a8ad', rough=0.42, wear=1.0, scratch=1.2, edge_gain=8.0)
    rub = wk.rubber('M_MpRubber', '#121213', rough=0.75)

    # ---- upper receiver: stamped box, pressed side ribs, spot welds, top slot + charging knob
    rc = rounded([(-18, 2, 4), (172, 2, 3), (176, 8, 2), (176, 40, 3), (168, 44, 3), (-10, 44, 4), (-18, 38, 4)], n=6)
    recv = make('Mp_Upper', profile(rc, -23.0, 23.0), finish, bevel=0.0024, seg=5, angle=30)
    cut(recv, box(W(85, 44.0, 0), (0.0065, 0.145, 0.006)), 'topslot')
    cut(recv, box(W(118, 26, -22.5), (0.004, 0.050, 0.014)), 'ejport')
    for side in (1, -1):
        rb = rounded([(8, 14, 4), (150, 14, 4), (150, 32, 4), (8, 32, 4)])
        make('Mp_Rib%d' % side, profile(rb, side * 23.0 - (0 if side > 0 else 1.2), side * 23.0 + (1.2 if side > 0 else 0)),
             finish, bevel=0.0010, seg=3)
        for (u, v) in ((-4, 9), (-4, 37), (162, 9), (162, 37), (40, 7), (100, 7)):
            make('Mp_Weld', sphere(W(u, v, side * 23.0), 0.0016, seg=12, rings=6, scale=(0.35, 1, 1)), finish_dk)
    make('Mp_Bolt', profile(rounded([(96, 20, 1.5), (140, 20, 1.5), (140, 32, 1.5), (96, 32, 1.5)]), -20.5, -15.0), steel, bevel=0.0005)
    make('Mp_ChargeStem', cyl(W(70, 40, 0), W(70, 52, 0), 0.0036, n=16), steel)
    make('Mp_ChargeKnob', cyl(W(70, 49, 0), W(70, 57, 0), 0.0068, n=32), finish_dk, bevel=0.0012, seg=4)
    # sling loop at the back
    make('Mp_SlingLoop', tube([W(-14, 36, 0) + Vector((0, 0.011 * math.sin(a), -0.010 + 0.010 * math.cos(a))) for a in [PI / 2 + PI * i / 14 for i in range(15)]],
                              0.0018, n=10), steel)

    # ---- lower: boxy grip frame + stamped trigger guard
    lw = rounded([(-4, 4, 0), (120, 4, 0), (120, -4, 3), (58, -6, 4), (48, -120, 4), (14, -120, 4), (-4, -6, 6)], n=6)
    lower = make('Mp_Lower', profile(lw, -17.5, 17.5), finish, bevel=0.0022, seg=5, angle=30)
    cut(lower, box(W(32, -150, 0), (0.0255, 0.064, 0.0230)), 'magwell')
    gd = rounded([(58, -4, 0), (112, -4, 0), (112, -10, 3), (104, -30, 8), (66, -32, 6), (58, -26, 2)], n=6)
    hole = rounded([(66, -8, 3), (104, -8, 3), (98, -25, 6), (68, -26, 5)], n=6)
    make('Mp_Guard', profile(gd, -7.5, 7.5, holes=[hole]), finish, bevel=0.0012)
    tr = rounded([(84, -5, 0), (83, -12, 3), (79, -20, 2), (76.5, -20, 1.5), (79.5, -12, 3), (80, -5, 0)])
    make('Mp_Trigger', profile(tr, -2.6, 2.6), steel, bevel=0.0004)
    for side in (1, -1):                                       # stippled grip panels
        gp = rounded([(20, -18, 5), (46, -18, 5), (44, -108, 5), (19, -108, 5)])
        make('Mp_GripPanel%d' % side, profile(gp, side * 17.5 - (0 if side > 0 else 2.0), side * 17.5 + (2.0 if side > 0 else 0)),
             rub, bevel=0.0012, seg=4)
    # magazine release button
    make('Mp_MagRelease', cyl(W(30, -122, 0) + Vector((0, 0, -0.002)), W(30, -126, 0), 0.0045, n=20), steel)

    # ---- long straight magazine out of the grip
    mg = rounded([(19, -100, 0), (45, -100, 0), (45, -262, 2), (19, -262, 2)])
    mag = make('Mp_Magazine', profile(mg, -10.8, 10.8), finish_dk, bevel=0.0012, seg=3)
    for side in (1, -1):
        for k in range(6):
            gb = box(W(32, -140 - k * 20, side * 10.8), (0.0016, 0.012, 0.0060))
            cut(mag, gb, 'win%d%d' % (side, k))                      # witness holes
    bp = rounded([(16, -262, 2), (48, -262, 2), (48, -270, 3), (16, -270, 3)])
    make('Mp_MagBase', profile(bp, -12.5, 12.5), finish, bevel=0.0012)
    make('Mp_MagRounds', profile(rounded([(22, -150, 2), (42, -150, 2), (42, -246, 2), (22, -246, 2)]), -8.5, 8.5),
         wk.steel('M_MpBrass', base='#9c7735', bare='#c9a35b', rough=0.35, wear=0.3, scratch=0.3), bevel=0.0010)

    # ---- barrel nut + short threaded barrel
    make('Mp_BarrelNut', lathe([(0, 174.0), (12.0, 174.0), (13.0, 176.0), (13.0, 190.0), (12.0, 192.0), (9.0, 192.5)], n=6, axis_v=24.0,
                               phase=PI / 6), steel, bevel=0.0008, angle=40)
    th = [(8.0, 192.0), (8.0, 205.0)]
    for k in range(18):
        u = 205.0 + k * 1.6
        th += [(8.0, u), (8.7, u + 0.4), (8.7, u + 0.8), (8.0, u + 1.2)]
    th += [(8.0, 235.0), (7.4, 236.0)]
    bar = make('Mp_Barrel', lathe(th, n=48, axis_v=24.0), steel)
    cut(bar, cyl(W(200, 24, 0), W(240, 24, 0), 0.0046, n=32), 'bore')

    # ---- little folding front grip under the front of the receiver (deployed)
    hb = rounded([(140, 3, 2), (168, 3, 2), (168, -6, 2), (140, -6, 2)])
    make('Mp_FGMount', profile(hb, -9.0, 9.0), steel, bevel=0.0008)
    make('Mp_FGHinge', cyl(W(158, -8, -10.0), W(158, -8, 10.0), 0.0045, n=24), steel)
    fg = rounded([(150, -6, 3), (166, -6, 3), (164, -70, 6), (148, -72, 6)], n=6)
    fgo = make('Mp_FrontGrip', profile(fg, -8.5, 8.5), finish_dk, bevel=0.0030, seg=5)
    for k in range(4):
        gb = box(W(156.5, -24 - k * 12, 0), (0.030, 0.026, 0.0024))
        cut(fgo, gb, 'gr%d' % k)

    PIVOT['MachinePistol'] = (33.0, -60.0)
    return 'MachinePistol'


BUILDERS['MachinePistol'] = machinepistol


# ================================================================== stickers on cylinders
def tube_sticker(name, img, R, u0, a0_deg, w, h, rot_deg=0.0, axis_v=0.0, circle=False, lift=0.35, n=24):
    """die-cut vinyl sticker wrapped on a cylinder of radius R (mm) around the bore axis; rect or circle"""
    a0 = math.radians(a0_deg); ro = math.radians(rot_deg)
    verts = []; uvs = []; faces = []
    def place(s, t):
        uu = u0 + s * math.cos(ro) - t * math.sin(ro)
        arc = s * math.sin(ro) + t * math.cos(ro)
        a = a0 + arc / R
        rr = R + lift
        return W(uu, axis_v + rr * math.sin(a), rr * math.cos(a))
    if circle:
        rad = w / 2; NR, NA = 10, 48
        verts.append(place(0, 0)); uvs.append((0.5, 0.5))
        for i in range(1, NR + 1):
            for j in range(NA):
                ang = 2 * PI * j / NA; r = rad * i / NR
                s, t = r * math.cos(ang), r * math.sin(ang)
                verts.append(place(s, t)); uvs.append((0.5 + s / w, 0.5 + t / w))
        for j in range(NA):
            faces.append((0, 1 + j, 1 + (j + 1) % NA))
        for i in range(NR - 1):
            for j in range(NA):
                a = 1 + i * NA + j; b = 1 + i * NA + (j + 1) % NA
                faces.append((a, a + NA, b + NA, b))
    else:
        nu, nv = n, max(4, int(n * h / w))
        for i in range(nu + 1):
            for j in range(nv + 1):
                s = (i / nu - 0.5) * w; t = (j / nv - 0.5) * h
                verts.append(place(s, t)); uvs.append((i / nu, j / nv))
        for i in range(nu):
            for j in range(nv):
                q = i * (nv + 1) + j
                faces.append((q, q + nv + 1, q + nv + 2, q + 1))
    bm = wk.bm_from(verts, faces)
    uvl = bm.loops.layers.uv.new('UVMap'); bm.verts.index_update()
    fu = math.cos(a0) > 0                     # left side: u runs right-to-left on screen; right side: arc runs downward
    for f in bm.faces:
        for lp in f.loops:
            uu, vv = uvs[lp.vert.index]
            lp[uvl].uv = ((1 - uu) if fu else uu, vv if fu else (1 - vv))
    mat = wk.image_mat('M_' + name, img, rough=0.32, bump=0.03)
    return make(name, bm, mat, solid=0.0003)


def chain(name, pts, link_l=22.0, link_w=12.0, wire=2.3, mat=None):
    """chain of alternating links following a world-space polyline (mm sizes)"""
    P = wk.spline(pts, 16)
    # resample at link pitch
    pitch = (link_l - 2 * wire) * MM
    samples = [P[0]]; acc = 0.0
    for a, b in zip(P[:-1], P[1:]):
        seg = (b - a).length; d = 0.0
        while acc + (seg - d) >= pitch:
            step = pitch - acc
            d += step; acc = 0.0
            samples.append(a + (b - a) * (d / seg))
        acc += seg - d
    out = bmesh.new()
    for k in range(len(samples) - 1):
        a, b = samples[k], samples[k + 1]
        c = (a + b) / 2; t = (b - a).normalized()
        side = t.cross(Vector((0, 0, 1)))
        if side.length < 1e-4:
            side = t.cross(Vector((1, 0, 0)))
        side.normalize()
        if k % 2:
            side = t.cross(side).normalized()
        L2 = link_l * MM / 2 - wire * MM; W2 = link_w * MM / 2 - wire * MM
        path = []
        for i in range(24):                               # stadium loop
            ang = 2 * PI * i / 24
            x = math.cos(ang); y = math.sin(ang)
            px = L2 * (1 if x >= 0 else -1) + W2 * x
            path.append(c + t * px + side * W2 * y)
        lk = wk.tube(path, wire * MM, n=8, closed=True)
        me = bpy.data.meshes.new('tmp'); lk.to_mesh(me); lk.free(); out.from_mesh(me); bpy.data.meshes.remove(me)
    return make(name, out, mat)


# ================================================================== 5. ROCKET LAUNCHER (Boom Boom, primary)
def rocketlauncher():
    sprayed = wk.paint('M_RlTube', '#121313', under='#4f5a31', under_metal=0.0, rough=0.62, wear=1.6, scuff=1.5, col_var=0.18)
    olive = wk.paint('M_RlOlive', '#4b5530', under='#7c7f82', rough=0.55, wear=1.0, scuff=0.8)
    steel = wk.steel('M_RlSteel', base='#2a2c2f', bare='#a9acb1', rough=0.4, wear=1.2, scratch=1.2, edge_gain=8.0)
    inner = wk.steel('M_RlInner', base='#0c0c0d', bare='#2b2b2c', rough=0.6, wear=0.0, scratch=0.0, metallic=0.4)
    rub = wk.rubber('M_RlRubber', '#141415', rough=0.75)
    chain_m = wk.steel('M_RlChain', base='#5d5f63', bare='#b9bcc0', rough=0.35, wear=1.0, scratch=0.6, edge_gain=10.0)
    R = 48.0
    # ---- hollow tube, muzzle band, rear venturi flare
    make('Rl_Tube', lathe([(R, 0.0), (R, 1000.0), (R - 3.5, 1000.0), (R - 3.5, 0.0), (R, 0.0)], n=96, cap0=False, cap1=False), sprayed)
    make('Rl_TubeInner', lathe([(R - 3.6, 10.0), (R - 3.6, 998.0)], n=64, cap0=False, cap1=False), inner)
    mb = lathe([(R - 3.4, 975.0), (R + 4.0, 975.0), (R + 5.0, 978.0), (R + 5.0, 1004.0), (R + 3.5, 1008.0), (R - 3.4, 1008.0),
                (R - 3.4, 975.0)], n=96, cap0=False, cap1=False)
    make('Rl_MuzzleBand', mb, steel, bevel=0.0)
    vf = lathe([(R + 3.0, 22.0), (R + 4.0, 18.0), (R + 4.0, 0.0), (R + 2.0, -12.0), (R + 3.0, -60.0), (R + 9.0, -120.0),
                (R + 17.0, -160.0), (R + 21.0, -168.0), (R + 21.5, -173.0), (R + 19.0, -175.0), (R + 16.5, -168.0), (R + 7.0, -120.0),
                (R + 0.5, -60.0), (R - 3.4, -12.0), (R - 3.4, 22.0), (R + 3.0, 22.0)], n=96, cap0=False, cap1=False)
    make('Rl_Venturi', vf, olive)
    # ---- clamp rings with bolts (grip + sight mounts)
    for (u, nm) in ((350.0, 'A'), (580.0, 'B')):
        cr = lathe([(R, u - 14), (R + 3.5, u - 14), (R + 4.2, u - 12), (R + 4.2, u + 12), (R + 3.5, u + 14), (R, u + 14), (R, u - 14)],
                   n=96, cap0=False, cap1=False)
        make('Rl_Clamp' + nm, cr, steel)
        for sd in (1, -1):
            ear = rounded([(u - 10, -R - 4, 2), (u + 10, -R - 4, 2), (u + 10, -R - 16, 3), (u - 10, -R - 16, 3)])
            make('Rl_ClampEar' + nm, profile(ear, sd * 5.0 - 3.5, sd * 5.0 + 3.5), steel, bevel=0.0010)
        make('Rl_ClampBolt' + nm, cyl(W(u, -R - 11, -11), W(u, -R - 11, 11), 0.0032, n=16), steel)
        for sd in (1, -1):
            make('Rl_ClampNut' + nm, cyl(W(u, -R - 11, sd * 9.0), W(u, -R - 11, sd * 13.0), 0.0052, n=6), steel)
    # ---- pistol grip + trigger housing under the tube
    th = rounded([(330, -R - 2, 0), (420, -R - 2, 0), (418, -R - 14, 4), (404, -R - 18, 4), (396, -R - 46, 8), (360, -R - 48, 8),
                  (352, -R - 30, 6), (330, -R - 16, 4)], n=6)
    hole = rounded([(362, -R - 20, 4), (392, -R - 20, 4), (388, -R - 40, 6), (366, -R - 41, 6)], n=6)
    make('Rl_TriggerHousing', profile(th, -9.0, 9.0, holes=[hole]), steel, bevel=0.0016, seg=4)
    tr = rounded([(379, -R - 18, 0), (378, -R - 26, 3), (374, -R - 34, 2), (371.5, -R - 34, 1.5), (374.5, -R - 26, 3), (375, -R - 18, 0)])
    make('Rl_Trigger', profile(tr, -2.8, 2.8), steel, bevel=0.0004)
    g = Grip((342.0, -R - 12.0), (330.0, -R - 70.0), (306.0, -R - 118.0),
             depth=lambda t: (17.0 + 2.0 * math.sin(PI * t), 19.0 + 2.0 * t), width=lambda t: 14.0 + 1.0 * math.sin(PI * t), e=2.6, butt=0.06)
    fg = lambda t, th: 1.0 - 0.07 * max(0.0, math.cos(th)) ** 4 * max(0.0, math.sin(PI * (t - 0.18) / 0.62 * 3.0)) * (0.18 < t < 0.80)
    Rr = g.rings(0.0, 1.0, 0.0, 2 * PI, nt=48, nth=56, fn=fg)
    make('Rl_Grip', wk.loft([r[:-1] for r in Rr], closed=True, cap1=True), rub)
    # ---- flip-up rear leaf sight + front post
    rb = rounded([(560, R - 2, 0), (600, R - 2, 0), (600, R + 8, 2), (560, R + 8, 2)])
    make('Rl_SightBase', profile(rb, -9.0, 9.0), steel, bevel=0.0010)
    leaf = rounded([(586, R + 6, 0), (592, R + 6, 0), (594, R + 44, 3), (584, R + 44, 3)])
    lo = make('Rl_SightLeaf', profile(leaf, -11.0, 11.0), steel, bevel=0.0006)
    cut(lo, cyl(W(580, R + 34, 0), W(600, R + 34, 0), 0.0034, n=24), 'aperture')
    make('Rl_SightHinge', cyl(W(589, R + 7, -10), W(589, R + 7, 10), 0.0028, n=16), steel)
    fp = rounded([(950, R - 2, 0), (972, R - 2, 0), (968, R + 18, 2), (956, R + 18, 2)])
    make('Rl_FrontSightBase', profile(fp, -6.0, 6.0), steel, bevel=0.0008)
    make('Rl_FrontPost', profile(rounded([(959, R + 16, 0), (964, R + 16, 0), (963, R + 40, 1.5), (960, R + 40, 1.5)]), -1.4, 1.4), steel)
    # ---- no stickers/logos: just two wraps of worn duct tape round the tube
    duct = wk.tape('M_RlTape')
    for (u0, wd, k) in ((470.0, 46.0, 0), (820.0, 34.0, 1)):
        rings = []
        for j in range(7):
            uu = u0 + wd * j / 6
            ring = []
            for i in range(97):
                a = 2 * PI * i / 96 * 2.2
                rr = R + 0.45 + 0.35 * (a / (2 * PI)) + 0.12 * noise.noise(Vector((a, uu * 0.05, k)))
                ring.append(W(uu + 1.5 * math.sin(a * 0.5), rr * math.sin(a), rr * math.cos(a)))
            rings.append(ring)
        make('Rl_Tape%d' % k, wk.loft(rings, closed=False), duct, solid=0.0004)
    # ---- loop of chain hanging from the front
    make('Rl_ChainLug', profile(rounded([(962, R - 6, 2), (984, R - 6, 2), (984, R + 4, 3), (962, R + 4, 3)]), 26.0, 34.0), steel, bevel=0.0008)
    a1 = W(973, R - 2, 36); a2 = W(940, -R + 10, 46)
    cpts = [a1, W(975, R - 30, 62), W(968, -R - 40, 70), W(955, -R - 70, 58), W(945, -R - 55, 50), a2]
    chain('Rl_Chain', cpts, mat=chain_m)
    PIVOT['RocketLauncher'] = (g.centre(0.45).x, g.centre(0.45).y)
    return 'RocketLauncher'


BUILDERS['RocketLauncher'] = rocketlauncher


def flat_sticker(name, img, centre, x_side, w, h, rot_deg=0.0, circle=True, lift=0.3):
    """die-cut sticker on a flat side face (x = const), centre (u, v) mm"""
    ro = math.radians(rot_deg); NR, NA = 8, 48
    verts = []; uvs = []; faces = []
    def P(s, t):
        u = centre[0] + s * math.cos(ro) - t * math.sin(ro); v = centre[1] + s * math.sin(ro) + t * math.cos(ro)
        return W(u, v, x_side + (lift if x_side > 0 else -lift))
    flip = x_side > 0                         # +x side seen from +x: u runs right-to-left on screen
    if circle:
        verts.append(P(0, 0)); uvs.append((0.5, 0.5))
        for i in range(1, NR + 1):
            for j in range(NA):
                a = 2 * PI * j / NA; r = w / 2 * i / NR
                s, t = r * math.cos(a), r * math.sin(a)
                verts.append(P(s, t)); uvs.append((0.5 + s / w, 0.5 + t / w))
        for j in range(NA):
            faces.append((0, 1 + j, 1 + (j + 1) % NA))
        for i in range(NR - 1):
            for j in range(NA):
                a = 1 + i * NA + j; b = 1 + i * NA + (j + 1) % NA
                faces.append((a, a + NA, b + NA, b))
    else:
        for (s, t) in ((-w / 2, -h / 2), (w / 2, -h / 2), (w / 2, h / 2), (-w / 2, h / 2)):
            verts.append(P(s, t)); uvs.append((s / w + 0.5, t / h + 0.5))
        faces.append((0, 1, 2, 3))
    bm = wk.bm_from(verts, faces)
    uvl = bm.loops.layers.uv.new('UVMap'); bm.verts.index_update()
    for f in bm.faces:
        for lp in f.loops:
            uu, vv = uvs[lp.vert.index]
            lp[uvl].uv = ((1 - uu) if flip else uu, vv)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces[:])
    return make(name, bm, wk.image_mat('M_' + name, img, rough=0.3, bump=0.03), solid=0.0003)


# ================================================================== 6. SEMI-AUTO PISTOL (Boom Boom, secondary)
def semiauto():
    blk = wk.steel('M_SaBlack', base='#121315', bare='#b3b6bb', rough=0.32, wear=1.6, scratch=1.2, edge_gain=11.0)
    blk_dk = wk.steel('M_SaBlackDk', base='#0d0d0f', bare='#9fa2a7', rough=0.36, wear=1.0, scratch=0.8, edge_gain=12.0)
    rub = wk.rubber('M_SaRubber', '#111112', rough=0.78, stipple=1.4)
    # ---- slide: squared-off, flat top, rear serrations, ejection port, sights
    sl = rounded([(-32, -3.5, 1.5), (168, -3.5, 1.5), (170, -1.0, 1.0), (170, 15.5, 2.0), (166, 18.5, 2.5), (-27, 18.5, 2.5),
                  (-32, 14.0, 2.0)], n=6)
    slide = make('Sa_Slide', profile(sl, -11.6, 11.6), blk, bevel=0.0012, seg=4, angle=30)
    for k in range(11):
        u = -26.0 + k * 2.4
        for sd in (1, -1):
            gb = box(W(u, 8.0, sd * 11.6), (0.0016, 0.0009, 0.0190))
            cut(slide, gb, 'ser%d%d' % (k, sd))
    cut(slide, box(W(62, 9.0, -9.5), (0.010, 0.040, 0.014)), 'ejport')
    cut(slide, cyl(W(160, 0, 0), W(175, 0, 0), 0.0072, n=40), 'muzzle')
    make('Sa_Bushing', lathe([(5.0, 160.0), (7.0, 160.0), (7.0, 169.5), (6.6, 170.4), (4.4, 170.4), (4.4, 160.0)], n=40,
                             cap0=False, cap1=False), blk_dk, bevel=0.0)
    make('Sa_Barrel', lathe([(5.4, 30.0), (5.4, 168.0)], n=32), wk.steel('M_SaBarrel', base='#5d6065', bare='#b2b5ba', rough=0.3), bevel=0.0)
    bore = make('Sa_Bore', lathe([(5.5, 120.0), (5.5, 169.0)], n=32, cap0=True, cap1=False),
                wk.steel('M_SaBore', base='#0b0b0c', bare='#222222', rough=0.5, wear=0, scratch=0))
    make('Sa_EjBarrelHood', profile(rounded([(42, 2.0, 1), (82, 2.0, 1), (82, 12.0, 1), (42, 12.0, 1)]), -9.4, -6.0),
         wk.steel('M_SaHood', base='#5d6065', bare='#b2b5ba', rough=0.28), bevel=0.0004)
    fs = rounded([(155, 18.0, 0), (162, 18.0, 0), (161, 24.0, 1.5), (157, 24.0, 1.5)])
    make('Sa_FrontSight', profile(fs, -1.6, 1.6), blk_dk, bevel=0.0004)
    rs = rounded([(-24, 18.0, 0), (-12, 18.0, 0), (-12, 24.5, 1.5), (-24, 23.0, 1.5)])
    rso = make('Sa_RearSight', profile(rs, -6.0, 6.0), blk_dk, bevel=0.0005)
    cut(rso, box(W(-18, 24.5, 0), (0.0030, 0.020, 0.0050)), 'notch')
    # ---- frame: dust cover, trigger guard, grip frame with beavertail
    fr = rounded([(-40, -3.5, 4), (150, -3.5, 2), (150, -14.0, 3), (88, -16.0, 4), (80, -40.0, 8), (44, -42.0, 9),
                  (30, -24.0, 5), (8, -24.0, 6), (-2, -100.0, 4), (-8, -108.0, 3), (-44, -108.0, 3), (-46, -100.0, 3),
                  (-32, -24.0, 10), (-50, -2.0, 6), (-52, 3.0, 3), (-44, 4.0, 2)], n=8)
    hole = rounded([(36, -19.0, 4), (80, -19.0, 4), (74, -36.0, 8), (46, -37.0, 6)], n=6)
    make('Sa_Frame', profile(fr, -10.4, 10.4, holes=[hole]), blk, bevel=0.0012, seg=4, angle=30)
    tr = rounded([(50, -14, 0), (60, -14, 0), (60, -28, 2), (52, -28, 2)])
    make('Sa_Trigger', profile(tr, -3.6, 3.6), blk_dk, bevel=0.0006)
    # hammer (ring hammer), thumb safety, slide stop, mag release, grip panels, magazine base
    hm = rounded([(-38, 2, 1.5), (-40, 18, 3), (-50, 22, 4), (-56, 16, 4), (-50, 8, 3), (-44, -2, 2)], n=6)
    ham = make('Sa_Hammer', profile(hm, -3.2, 3.2), blk_dk, bevel=0.0005)
    cut(ham, cyl(W(-49, 15, -5), W(-49, 15, 5), 0.0028, n=20), 'ring')
    ts = rounded([(-34, 2.0, 2), (-14, 4.0, 2), (-12, 9.0, 2), (-30, 8.0, 2)])
    make('Sa_ThumbSafety', profile(ts, 10.4, 12.2), blk_dk, bevel=0.0005)
    ss = rounded([(10, -3.0, 2), (36, -1.5, 2), (36, 4.0, 2), (14, 4.5, 2)])
    make('Sa_SlideStop', profile(ss, 10.4, 12.0), blk_dk, bevel=0.0005)
    make('Sa_SlideStopPin', cyl(W(30, 0.5, 12.0), W(30, 0.5, 12.8), 0.0028, n=20), blk_dk)
    make('Sa_MagRelease', cyl(W(14, -22, 10.4), W(14, -22, 12.0), 0.0045, n=24), blk_dk, bevel=0.0004)
    gp = rounded([(-30, -30, 6), (2, -30, 5), (-6, -100, 4), (-40, -100, 4)], n=6)
    for sd in (1, -1):
        po = make('Sa_GripPanel%d' % sd, profile(gp, sd * 10.4 - (0 if sd > 0 else 3.0), sd * 10.4 + (3.0 if sd > 0 else 0)), rub,
                  bevel=0.0022, seg=4)
        wk.screw(W(-12, -36, sd * 13.4), Vector((sd, 0, 0)), r=0.0022, mat=blk_dk, name='Sa_GripScrew')
        wk.screw(W(-20, -94, sd * 13.4), Vector((sd, 0, 0)), r=0.0022, mat=blk_dk, name='Sa_GripScrew')
    mb = rounded([(-42, -106, 2), (-4, -106, 2), (-4, -112, 2.5), (-44, -112, 2.5)])
    make('Sa_MagBase', profile(mb, -9.0, 9.0), blk_dk, bevel=0.0010)
    PIVOT['SemiAuto'] = (-22.0, -62.0)
    return 'SemiAuto'


BUILDERS['SemiAuto'] = semiauto


# ================================================================== stock lofting
def stock_loft(name, sections, mat, e=2.6, nth=48, cap0=True, cap1=True):
    """sections: [(u, v_top, v_bot, half_width)] mm along the weapon -> lofted superellipse body (smooth stocks)"""
    rings = []
    S = []
    for k in range(len(sections) - 1):                             # resample smoothly
        a = sections[max(0, k - 1)]; b = sections[k]; c = sections[k + 1]; d = sections[min(len(sections) - 1, k + 2)]
        for i in range(6):
            t = i / 6
            S.append(tuple(0.5 * ((2 * b[j]) + (-a[j] + c[j]) * t + (2 * a[j] - 5 * b[j] + 4 * c[j] - d[j]) * t * t +
                                  (-a[j] + 3 * b[j] - 3 * c[j] + d[j]) * t ** 3) for j in range(4)))
    S.append(sections[-1])
    for (u, vt, vb, hw) in S:
        vc = (vt + vb) / 2; hv = (vt - vb) / 2
        ring = []
        for i in range(nth):
            th = 2 * PI * i / nth
            c_, s_ = math.cos(th), math.sin(th)
            px = math.copysign(abs(c_) ** (2 / e), c_); py = math.copysign(abs(s_) ** (2 / e), s_)
            ring.append(W(u, vc + hv * py, hw * px))
        rings.append(ring)
    return make(name, wk.loft(rings, closed=True, cap0=cap0, cap1=cap1), mat)


def scope_body(prefix, u0, u1, v, mat, glass, obj_r=26.0, eye_r=21.0, tube_r=12.7):
    """riflescope along u (front = u1): eyepiece, tube, turrets, objective bell, glass"""
    prof = [(0.0, u0), (eye_r - 1.5, u0), (eye_r, u0 + 2), (eye_r, u0 + 34), (eye_r - 0.8, u0 + 36), (eye_r, u0 + 38), (eye_r, u0 + 50),
            (tube_r + 2.0, u0 + 66), (tube_r + 2.0, u0 + 72), (tube_r, u0 + 76), (tube_r, u1 - 92), (tube_r + 1.0, u1 - 88),
            (obj_r - 2, u1 - 52), (obj_r, u1 - 46), (obj_r, u1 - 2), (obj_r - 1.5, u1), (0.0, u1)]
    body = make(prefix + '_Scope', lathe(prof, n=64, axis_v=v), mat, bevel=0.0, smooth=True)
    for (uu, r, nm) in ((u1 - 1.0, obj_r - 3.0, 'Obj'), (u0 + 1.0, eye_r - 3.0, 'Eye')):
        cut(body, lathe([(r, uu - 6 if nm == 'Obj' else uu - 2), (r, uu + 2 if nm == 'Obj' else uu + 6)], n=48, axis_v=v), 'rec' + nm)
        gl = lathe([(0, uu - (4.5 if nm == 'Obj' else -4.5)), (r, uu - (4.5 if nm == 'Obj' else -4.5))], n=48, axis_v=v, cap0=False, cap1=False)
        make(prefix + '_Lens' + nm, lathe([(r - 0.1, uu - 5 if nm == 'Obj' else uu + 3.5), (0.0, uu - 4 if nm == 'Obj' else uu + 4.5)],
                                          n=48, axis_v=v), glass)
    tc = (u0 + u1) / 2 - 10
    tt = lathe([(0, 0), (9.5, 0), (9.5, 14), (8.5, 15.5), (0, 16)], n=40)
    for (dirv, nm) in (((0, 0, 1), 'Elev'), ((1, 0, 0), 'Wind')):
        base = cyl(W(tc, v, 0), W(tc, v, 0) + Vector(dirv) * (tube_r + 3.0) * MM, 0.0105, n=40)
        make(prefix + '_TurretBase' + nm, base, mat)
        cap = cyl(W(tc, v, 0) + Vector(dirv) * (tube_r + 3.0) * MM, W(tc, v, 0) + Vector(dirv) * (tube_r + 15.0) * MM, 0.0092, n=40)
        co = make(prefix + '_Turret' + nm, cap, mat)
        for k in range(20):
            a = 2 * PI * k / 20
            nrm = Vector(dirv)
            x = nrm.orthogonal().normalized(); y = nrm.cross(x)
            p = W(tc, v, 0) + nrm * (tube_r + 9.0) * MM + (x * math.cos(a) + y * math.sin(a)) * 9.2 * MM
            g = box((0, 0, 0), (0.0011, 0.0011, 0.0115))
            transform(g, frame(p, x * math.cos(a) + y * math.sin(a), (x * -math.sin(a) + y * math.cos(a)), nrm))
            cut(co, g, 'kn%d' % k)
    return body


def mat_glass(name, tint='#2b4a4a'):
    g = wk.NT(name)
    g.set('Base Color', (*wk.srgb(tint), 1)); g.set('Roughness', 0.02); g.set('Metallic', 0.6)
    try:
        g.set('Coat Weight', 1.0); g.set('Thin Film Thickness', 300.0)
    except KeyError:
        pass
    return g.m


def sling(name, pts, width, mat, thick=0.0025, twist=0.0):
    P = wk.spline(pts, 10)
    bm = ribbon(P, width, lambda t, tan: Vector((math.cos(twist * t), 0.0, math.sin(twist * t))).normalized()
                if abs(tan.dot(Vector((math.cos(twist * t), 0, math.sin(twist * t))))) < 0.95 else Vector((0, 0, 1)))
    wk.set_uv(bm, lambda co: (co.y * 20.0, co.z * 20.0))
    return make(name, bm, mat, solid=thick)


def webbing(name, col):
    g = wk.NT(name)
    wv = g.node('ShaderNodeTexWave'); wv.inputs['Scale'].default_value = 2600.0; wv.bands_direction = 'Y'
    wv2 = g.node('ShaderNodeTexWave'); wv2.inputs['Scale'].default_value = 900.0; wv2.bands_direction = 'Z'
    g.link(g.co, wv.inputs['Vector']); g.link(g.co, wv2.inputs['Vector'])
    dirt = g.noise(30, 5, 0.6)
    c0 = wk.srgb(col)
    g.set('Base Color', g.ramp(dirt, 0.3, 0.9, tuple(c * 0.6 for c in c0), c0))
    g.set('Roughness', 0.85)
    g.bump(g.math('ADD', wv.outputs['Fac'], g.math('MULTIPLY', wv2.outputs['Fac'], 0.5)), 0.25, 0.0003)
    return g.m


# ================================================================== 7. SCOPED BOLT-ACTION RIFLE (Mr. Faraway, primary)
def boltrifle():
    blued = wk.steel('M_BrBlued', base='#15171b', bare='#a9acb1', rough=0.28, wear=1.2, scratch=0.9, edge_gain=10.0)
    blued_dk = wk.steel('M_BrBluedDk', base='#0e0f12', bare='#999ca1', rough=0.33, wear=0.8, scratch=0.5, edge_gain=10.0)
    walnut = wk.wood('M_BrWalnut', light='#4f2a13', dark='#1d0c05', rough=0.34, ring=18.0, axis='Y', grain=0.4, wear=0.8)
    rub = wk.rubber('M_BrButtPad', '#1d1a19', rough=0.8)
    camo = wk.image_mat('M_BrCamoTape', 'camo_tape.png', rough=0.85, bump=0.15)
    glass = mat_glass('M_BrGlass')
    blaze = webbing('M_BrSling', '#e63600')
    BV = 0.0
    # ---- stock: butt -> wrist (pistol grip) -> action area -> forend
    st = [(-380, 18, -112, 20), (-370, 22, -118, 21), (-300, 15, -96, 19.5), (-220, 6, -72, 17.5), (-160, 0, -55, 15.5),
          (-118, -2, -46, 14.0), (-92, -4, -86, 14.0), (-70, -6, -82, 14.5), (-48, -8, -40, 16.0), (0, -6, -34, 17.0),
          (120, -4, -32, 17.0), (260, -3, -28, 15.5), (380, -3, -24, 14.0), (420, -4, -20, 12.0)]
    stock = stock_loft('Br_Stock', st, walnut, e=2.4)
    cut(stock, box(W(30, 4, 0), (0.0300, 0.300, 0.020)), 'inlet')               # action inlet
    cut(stock, cyl(W(150, 0, 0), W(460, 0, 0), 0.0105, n=32), 'barrelchannel')
    # cheek piece (left) + checkering panels (darker)
    make('Br_ButtPad', profile(rounded([(-394, 22, 6), (-379, 22, 3), (-379, -120, 4), (-394, -120, 8)], n=6), -21.5, 21.5), rub,
         bevel=0.0030, seg=4)
    make('Br_ButtSpacer', profile(rounded([(-380, 22, 0), (-378, 22, 0), (-378, -119, 0), (-380, -119, 0)]), -21.2, 21.2),
         wk.plastic('M_BrSpacer', '#e8e2d4', rough=0.5), bevel=0.0004)
    # ---- receiver, bolt, trigger, guard, magazine floorplate
    make('Br_Receiver', lathe([(15.8, -60.0), (16.5, -55.0), (16.5, 130.0), (15.0, 140.0)], n=48, axis_v=8.0), blued, bevel=0.0)
    make('Br_RecvTang', profile(rounded([(-90, 0, 4), (-55, 4, 0), (-55, 14, 0), (-85, 6, 4)]), -6.0, 6.0), blued, bevel=0.0010)
    make('Br_Bolt', lathe([(9.5, -66.0), (9.5, 70.0)], n=32, axis_v=8.0, x=-1.0), blued_dk)
    make('Br_BoltShroud', lathe([(0, -86.0), (9.0, -86.0), (11.5, -80.0), (12.0, -66.0)], n=32, axis_v=8.0), blued_dk)
    # bolt handle sticking out to the right, swept back, round knob
    hp = [W(-40, 8, -10), W(-44, 6, -26), W(-52, 0, -40), W(-58, -8, -50)]
    make('Br_BoltHandle', tube(wk.spline(hp, 6), 0.0042, n=16), blued_dk)
    make('Br_BoltKnob', sphere(W(-60, -10, -53), 0.0105, seg=32, rings=16), blued_dk)
    make('Br_TriggerGuard', profile(rounded([(-60, -36, 4), (10, -36, 4), (8, -46, 6), (-12, -62, 10), (-40, -62, 8), (-58, -48, 6)],
                                            n=6), -6.5, 6.5, holes=[rounded([(-48, -40, 4), (0, -40, 4), (-12, -56, 8), (-38, -56, 6)], n=6)]),
         blued, bevel=0.0010)
    make('Br_Trigger', profile(rounded([(-20, -36, 0), (-21, -44, 2), (-25, -52, 2), (-27.5, -52, 1.5), (-24.5, -44, 2), (-24, -36, 0)]),
                               -2.4, 2.4), blued_dk, bevel=0.0004)
    for (u, sd) in ((-75, 1), (30, 1), (110, 1)):
        make('Br_StockScrew', cyl(W(u, -36.5, 0) + Vector((0, 0, -0.0005)), W(u, -38, 0), 0.0028, n=20), blued_dk)
    # ---- long tapered barrel with crown, sling swivels
    bar = lathe([(14.5, 140.0), (14.5, 175.0), (11.0, 230.0), (9.2, 560.0), (8.4, 820.0), (8.4, 823.0)], n=48, axis_v=8.0)
    bo = make('Br_Barrel', bar, blued, bevel=0.0)
    cut(bo, cyl(W(780, 8, 0), W(830, 8, 0), 0.0035, n=24), 'bore')
    cut(bo, lathe([(3.5, 821.0), (5.0, 823.5), (5.0, 826.0)], n=40, axis_v=8.0), 'crown')
    for (u, v) in ((-300, -96), (360, -26)):
        make('Br_SwivelStud', cyl(W(u, v + 2, 0), W(u, v - 5, 0), 0.0030, n=16), blued_dk)
        make('Br_Swivel', tube([W(u, v - 5, 0) + Vector((0, 0.009 * math.sin(a), -0.009 * (1 - math.cos(a)))) for a in [PI * i / 10 for i in range(11)]],
                               0.0016, n=8), blued_dk)
    # ---- scope with rings + camo tape wrap
    SV = 52.0
    scope_body('Br', -150.0, 210.0, SV, blued, glass, obj_r=27.0, eye_r=21.5, tube_r=12.7)
    for u in (-30.0, 110.0):
        ring = lathe([(12.8, u - 6), (16.0, u - 6), (16.5, u - 4), (16.5, u + 4), (16.0, u + 6), (12.8, u + 6), (12.8, u - 6)],
                     n=48, axis_v=SV, cap0=False, cap1=False)
        make('Br_ScopeRing', ring, blued_dk)
        make('Br_RingBase', profile(rounded([(u - 6, 17, 1), (u + 6, 17, 1), (u + 6, SV - 14, 2), (u - 6, SV - 14, 2)]), -7.0, 7.0), blued_dk,
             bevel=0.0008)
        for sd in (1, -1):
            make('Br_RingScrew', cyl(W(u, SV + 15.5, sd * 12.5), W(u, SV + 15.5, sd * 15.5), 0.0022, n=6), blued_dk)
    for (u_a, u_b, k) in ((-110.0, -62.0, 0), (20.0, 90.0, 1), (130.0, 152.0, 2)):
        rings = []
        for j in range(9):
            uu = u_a + (u_b - u_a) * j / 8
            r = 12.7
            ring = []
            for i in range(65):
                a = 2 * PI * i / 64 * 3.4 + j * 0.0
                rr = r + 0.6 + 0.35 * (a / (2 * PI)) + 0.15 * noise.noise(Vector((a, uu * 0.05, k)))
                ring.append(W(uu + 0.0, SV + rr * math.sin(a), rr * math.cos(a)))
            rings.append(ring)
        bm = wk.loft(rings, closed=False, uvs=[(i / 64 * 3.4, j / 8) for j in range(9) for i in range(65)])
        make('Br_CamoTape%d' % k, bm, camo, solid=0.0004)
    PIVOT['BoltRifle'] = (-84.0, -60.0)
    return 'BoltRifle'


BUILDERS['BoltRifle'] = boltrifle


# ================================================================== 8. VARMINT RIFLE (Mr. Faraway, secondary)
def leverrifle():
    blued = wk.steel('M_LvBlued', base='#17191d', bare='#a9acb1', rough=0.3, wear=1.2, scratch=0.9, edge_gain=10.0)
    blued_dk = wk.steel('M_LvBluedDk', base='#101114', bare='#999ca1', rough=0.34, wear=0.8, scratch=0.5, edge_gain=10.0)
    blond = wk.wood('M_LvBlond', light='#c9914a', dark='#8a5726', rough=0.4, ring=20.0, axis='Y', grain=0.55, wear=0.6)
    strap = webbing('M_LvStrap', '#e63600')
    # ---- receiver (flat-sided, rounded top), loading gate, lever, hammer
    rc = rounded([(-14, 16, 6), (96, 16, 4), (100, 12, 2), (100, -16, 3), (94, -22, 2), (2, -22, 2), (-14, -12, 6)], n=8)
    recv = make('Lv_Receiver', profile(rc, -10.5, 10.5), blued, bevel=0.0018, seg=5)
    cut(recv, box(W(60, -2, -10.5), (0.0020, 0.030, 0.010)), 'gate')
    make('Lv_LoadingGate', profile(rounded([(48, -7, 2), (76, -7, 2), (76, 3, 2), (48, 3, 2)]), -11.2, -10.0), blued_dk, bevel=0.0004)
    for (u, v) in ((10, -6), (84, -12)):
        for sd in (1, -1):
            wk.screw(W(u, v, sd * 10.5), Vector((sd, 0, 0)), r=0.0018, mat=blued_dk, name='Lv_Screw', slot_ang=u * 0.1)
    hm = rounded([(-8, 10, 1.5), (-10, -2, 2), (-18, -6, 3), (-24, 4, 3), (-28, 16, 3), (-34, 22, 2), (-30, 26, 2), (-20, 18, 3)], n=6)
    make('Lv_Hammer', profile(hm, -3.0, 3.0), blued_dk, bevel=0.0005)
    # lever loop (finger loop + trigger)
    lp = [W(u, v, 0) for (u, v) in ((92, -23), (62, -27), (34, -29), (8, -31), (-6, -40), (-12, -58), (-4, -74), (14, -76),
                                   (24, -62), (20, -46), (10, -36))]
    make('Lv_Lever', tube(wk.spline(lp, 6), 0.0040, n=16, flat=0.55), blued)
    make('Lv_Trigger', profile(rounded([(30, -22, 0), (29, -30, 2), (25, -38, 2), (22.5, -38, 1.5), (25.5, -30, 2), (26, -22, 0)]), -2.4, 2.4),
         blued_dk, bevel=0.0004)
    # ---- thin barrel + tube magazine underneath, barrel band, sights
    BV = 4.0; MV = -11.0
    bo = make('Lv_Barrel', lathe([(8.0, 98.0), (8.0, 120.0), (7.0, 160.0), (6.6, 520.0), (6.6, 522.0)], n=40, axis_v=BV), blued)
    cut(bo, cyl(W(480, BV, 0), W(530, BV, 0), 0.0029, n=24), 'bore')
    make('Lv_MagTube', lathe([(5.6, 100.0), (5.6, 500.0)], n=32, axis_v=MV), blued)
    make('Lv_MagCap', lathe([(0, 500.0), (5.9, 500.0), (5.9, 512.0), (5.0, 514.0), (0, 514.5)], n=32, axis_v=MV), blued_dk, bevel=0.0003)
    for u in (300.0, 495.0):
        bd = rounded([(u - 5, BV + 8, 3), (u + 5, BV + 8, 3), (u + 5, MV - 7, 3), (u - 5, MV - 7, 3)])
        band = make('Lv_Band', profile(bd, -8.0, 8.0), blued, bevel=0.0012)
        cut(band, cyl(W(u - 10, BV, 0), W(u + 10, BV, 0), 0.0067, n=32), 'b'); cut(band, cyl(W(u - 10, MV, 0), W(u + 10, MV, 0), 0.0057, n=32), 'm')
    fs = rounded([(500, BV + 6, 0), (512, BV + 6, 0), (510, BV + 14, 2), (504, BV + 14, 2)])
    make('Lv_FrontSight', profile(fs, -1.2, 1.2), blued_dk, bevel=0.0003)
    make('Lv_FrontBead', sphere(W(507, BV + 14.5, 0), 0.0012, seg=12, rings=6), wk.steel('M_LvBead', base='#d8c27a', bare='#e8d89a', rough=0.25))
    rs = rounded([(180, BV + 5, 0), (200, BV + 5, 0), (200, BV + 13, 1.5), (180, BV + 11, 1.5)])
    rso = make('Lv_RearSight', profile(rs, -5.5, 5.5), blued_dk, bevel=0.0004)
    cut(rso, box(W(190, BV + 13, 0), (0.030, 0.0030, 0.0040)), 'notch')
    # ---- blond wood forend + buttstock with straight wrist
    fe = [(102, 3, -20, 11.0), (140, 2, -20, 11.5), (260, 0, -19, 11.0), (296, -1, -18, 10.0)]
    stock_loft('Lv_Forend', fe, blond, e=2.6)
    bt = [(-12, 10, -20, 11.0), (-40, 10, -30, 11.5), (-90, 10, -44, 13.0), (-160, 12, -70, 15.5), (-240, 15, -92, 17.5),
          (-300, 17, -104, 18.5), (-312, 17, -106, 18.5)]
    stock_loft('Lv_Butt', bt, blond, e=2.5)
    make('Lv_ButtPlate', profile(rounded([(-318, 18, 4), (-311, 18, 2), (-311, -107, 3), (-318, -107, 6)], n=6), -18.6, 18.6), blued, bevel=0.0018)
    # ---- blaze-orange strap on the stock (wrapped round the butt, buckle)
    rings = []
    for j in range(7):
        uu = -210 + j * 5.5
        vt = 15.0 + 2.0 * (uu + 160) / -80; vb = -70 - 22 * (uu + 160) / -80
        hw = 15.5 + 2.0 * (uu + 160) / -80
        vc = (vt + vb) / 2; hv = (vt - vb) / 2 + 1.4
        ring = []
        for i in range(48):
            th = 2 * PI * i / 48
            c_, s_ = math.cos(th), math.sin(th)
            px = math.copysign(abs(c_) ** (2 / 2.5), c_); py = math.copysign(abs(s_) ** (2 / 2.5), s_)
            ring.append(W(uu, vc + hv * py, (hw + 1.4) * px))
        rings.append(ring)
    make('Lv_Strap', wk.loft(rings, closed=True, uvs=[(i / 48 * 4, j / 6) for j in range(7) for i in range(48)]), strap, solid=0.0015)
    bk = rounded([(-206, 4, 2), (-186, 4, 2), (-186, -22, 2), (-206, -22, 2)])
    bko = make('Lv_Buckle', profile(bk, -18.9, -17.6), wk.steel('M_LvBuckle', base='#7a7d82', bare='#c0c3c7', rough=0.3), bevel=0.0005)
    cut(bko, box(W(-196, -9, -18.2), (0.012, 0.020, 0.004)), 'win')
    PIVOT['LeverRifle'] = (-20.0, -40.0)
    return 'LeverRifle'


BUILDERS['LeverRifle'] = leverrifle


def grease_mat(name, base_mat_fn):
    """wrap: takes an NT-built material function result and overlays dark glossy grease stains (procedural)"""
    m = base_mat_fn
    nt = m.node_tree
    bs = next(n for n in nt.nodes if n.type == 'BSDF_PRINCIPLED')
    co = nt.nodes.new('ShaderNodeTexCoord').outputs['Object']
    nz = nt.nodes.new('ShaderNodeTexNoise'); nz.inputs['Scale'].default_value = 28.0; nz.inputs['Detail'].default_value = 8
    nz.inputs['Distortion'].default_value = 1.5
    nt.links.new(co, nz.inputs['Vector'])
    rp = nt.nodes.new('ShaderNodeValToRGB'); rp.color_ramp.elements[0].position = 0.60; rp.color_ramp.elements[1].position = 0.70
    nt.links.new(nz.outputs['Fac'], rp.inputs['Fac'])
    sep = nt.nodes.new('ShaderNodeSeparateColor'); nt.links.new(rp.outputs['Color'], sep.inputs[0])
    m_ = sep.outputs[0]
    for sock, val in (('Base Color', (0.012, 0.010, 0.008, 1)), ('Roughness', 0.18)):
        mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA' if sock == 'Base Color' else 'FLOAT'
        nt.links.new(m_, mix.inputs['Factor'])
        if bs.inputs[sock].is_linked:
            nt.links.new(bs.inputs[sock].links[0].from_socket, mix.inputs['A'])
        else:
            mix.inputs['A'].default_value = bs.inputs[sock].default_value
        mix.inputs['B'].default_value = val
        nt.links.new(mix.outputs['Result'], bs.inputs[sock])
    return m


# ================================================================== 9. SMG (Mechanic, primary)
def smg():
    blk = grease_mat('g', wk.steel('M_SmgBody', base='#161719', bare='#9fa2a7', rough=0.5, wear=1.2, scratch=1.4, edge_gain=8.0, tint_var=0.08))
    blk_dk = wk.steel('M_SmgDark', base='#0f1011', bare='#8d9095', rough=0.45, wear=0.8, scratch=0.8, edge_gain=8.0)
    orange = grease_mat('g2', wk.paint('M_SmgOrange', '#d4510a', under='#1a1a1a', under_metal=0.0, rough=0.55, wear=1.6, scuff=1.3, col_var=0.12))
    zipm = wk.plastic('M_SmgZipTie', '#e8e2cf', rough=0.4)
    # ---- tubular receiver with cocking slot, rear cap, front nut
    R = 19.0
    rcv = make('Smg_Receiver', lathe([(R, -40.0), (R, 230.0)], n=64, axis_v=0.0), blk)
    cut(rcv, box(W(80, 0, -R), (0.008, 0.110, 0.006)), 'cockslot')
    cut(rcv, box(W(150, 6, R - 1), (0.010, 0.050, 0.020)), 'ejport')
    make('Smg_CockHandle', cyl(W(40, 0, -R + 2), W(40, 0, -R - 14), 0.0042, n=20), blk_dk)
    make('Smg_CockKnob', sphere(W(40, 0, -R - 16), 0.0062, seg=24, rings=12, scale=(1, 1, 0.8)), blk_dk)
    make('Smg_RearCap', lathe([(0, -52.0), (R - 2, -52.0), (R + 1.5, -49.0), (R + 1.5, -38.0), (R, -36.0)], n=64), blk_dk, bevel=0.0005)
    # ---- ribbed barrel shroud with cooling holes, short barrel
    # perforated shroud: a thin shell with rows of round-ish cooling holes cut from the quads, then solidified
    prof = [(R - 1.0, 228.0 + 2.0 * i) for i in range(52)] + [(R - 4.0, 334.0)]
    shb = lathe(prof, n=64, cap0=False, cap1=False)
    dele = []
    for f in shb.faces:
        c = f.calc_center_median()
        uu = -c.y / MM; a = math.atan2(c.z / MM, c.x / MM)
        for k in range(6):
            u0 = 245.0 + k * 14.0
            if abs(uu - u0) < 4.0:
                for j in range(8):
                    a0 = 2 * PI * j / 8 + (k % 2) * PI / 8
                    da = (a - a0 + PI) % (2 * PI) - PI
                    if (abs(uu - u0) / 4.0) ** 2 + (da * R / 4.0) ** 2 < 1.0:
                        dele.append(f)
    bmesh.ops.delete(shb, geom=list(set(dele)), context='FACES')
    make('Smg_Shroud', shb, blk, solid=0.0018)
    for k in range(5):                                     # raised rib rings
        uu = 238.0 + k * 22.0
        make('Smg_Rib', lathe([(R - 0.5, uu), (R + 1.2, uu + 0.5), (R + 1.2, uu + 3.5), (R - 0.5, uu + 4.0)], n=64, cap0=False, cap1=False), blk)
    bo = make('Smg_Barrel', lathe([(7.0, 300.0), (7.0, 352.0), (6.4, 354.0)], n=32), blk_dk)
    cut(bo, cyl(W(330, 0, 0), W(360, 0, 0), 0.0046, n=24), 'bore')
    make('Smg_FrontSight', profile(rounded([(318, R - 2, 0), (328, R - 2, 0), (327, R + 10, 1.5), (319, R + 10, 1.5)]), -1.5, 1.5), blk_dk, bevel=0.0003)
    make('Smg_RearSight', profile(rounded([(-30, R - 2, 0), (-14, R - 2, 0), (-14, R + 8, 2), (-30, R + 8, 2)]), -5.0, 5.0), blk_dk, bevel=0.0005)
    # ---- side-mounted magazine (sticking out to the left, +x) with housing + zip tie
    hb = profile(rounded([(115, -14, 2), (165, -14, 2), (165, 14, 2), (115, 14, 2)]), R - 4, R + 22)
    make('Smg_MagHousing', hb, blk, bevel=0.0014)
    mg = profile(rounded([(124, -11, 2), (156, -11, 2), (156, 11, 2), (124, 11, 2)]), R + 22, R + 190)
    mag = make('Smg_Magazine', mg, blk_dk, bevel=0.0012)
    for k in range(6):
        for sv in (1, -1):
            rb = profile(rounded([(128, sv * 11.0 - 0.8, 0), (152, sv * 11.0 - 0.8, 0), (152, sv * 11.0 + 0.8, 0), (128, sv * 11.0 + 0.8, 0)]),
                         R + 46 + k * 24, R + 50 + k * 24)
            make('Smg_MagRib', rb, blk_dk, bevel=0.0004)
    make('Smg_MagBase', profile(rounded([(121, -13, 2), (159, -13, 2), (159, 13, 2), (121, 13, 2)]), R + 190, R + 197), blk, bevel=0.0010)
    # zip tie around housing + magazine
    # zip tie cinched round the receiver tube + the magazine, head on top of the mag, cut tail sticking up
    ZU = 160.0
    loop = [(0, -R - 1.6), (R * 0.72, -R * 0.72 - 1.0), (R + 1.6, 0), (15.6, R + 4), (15.6, R + 26), (12.6, R + 30), (12.6, R + 44),
            (0, R + 46.5), (-12.6, R + 44), (-12.6, R + 30), (-15.6, R + 26), (-15.6, R + 4), (-R - 1.6, 0), (-R * 0.72, -R * 0.72 - 1.0)]
    pts = [W(ZU, v, x) for (v, x) in loop]
    P = wk.spline(pts + pts[:3], 6)[: len(pts) * 6]
    make('Smg_ZipTie', tube(P, 0.0024, n=8, flat=0.42, closed=True, up=Vector((0, 1, 0))), zipm)
    make('Smg_ZipHead', box(W(ZU, 15.6 + 3.0, R + 15), (0.0060, 0.0080, 0.0060)), zipm, bevel=0.0008)
    make('Smg_ZipTail', tube([W(ZU, 18.6, R + 18), W(ZU - 1, 26, R + 21), W(ZU - 2, 33, R + 26)], 0.0012, n=6, flat=0.45), zipm)
    # ---- trigger group + orange-painted pistol grip
    th = rounded([(70, -14, 0), (150, -14, 0), (148, -22, 3), (120, -26, 4), (112, -50, 8), (80, -52, 8), (72, -36, 4)], n=6)
    hole = rounded([(86, -28, 4), (114, -28, 4), (108, -46, 7), (90, -46, 6)], n=6)
    make('Smg_TriggerHousing', profile(th, -9.5, 9.5, holes=[hole]), blk, bevel=0.0014)
    make('Smg_Trigger', profile(rounded([(102, -24, 0), (101, -32, 2), (97, -40, 2), (94.5, -40, 1.5), (97.5, -32, 2), (98, -24, 0)]), -2.4, 2.4),
         blk_dk, bevel=0.0004)
    g = Grip((76.0, -30.0), (64.0, -78.0), (46.0, -118.0),
             depth=lambda t: (15.0 + 1.5 * math.sin(PI * t), 17.0 + 2.0 * t), width=lambda t: 13.5 + 1.0 * math.sin(PI * t), e=2.6, butt=0.06)
    fg = lambda t, th: 1.0 - 0.07 * max(0.0, math.cos(th)) ** 4 * max(0.0, math.sin(PI * (t - 0.18) / 0.62 * 3.0)) * (0.18 < t < 0.80)
    Rr = g.rings(0.0, 1.0, 0.0, 2 * PI, nt=48, nth=56, fn=fg)
    make('Smg_Grip', wk.loft([r[:-1] for r in Rr], closed=True, cap1=True), orange)
    # ---- wire folding stock (folded out)
    S = blk_dk
    for sd in (1, -1):
        p = [W(-50, 8, sd * 14), W(-140, 2, sd * 15), W(-260, -12, sd * 15), W(-300, -18, sd * 15)]
        make('Smg_StockWire%d' % sd, tube(wk.spline(p, 6), 0.0040, n=12), S)
        p2 = [W(-50, -12, sd * 14), W(-160, -40, sd * 15), W(-300, -66, sd * 15)]
        make('Smg_StockWireLo%d' % sd, tube(wk.spline(p2, 6), 0.0036, n=12), S)
    make('Smg_StockButt', tube([W(-300, -18, 15), W(-306, -40, 16), W(-300, -66, 15)], 0.0045, n=12), S)
    make('Smg_StockButtPad', profile(rounded([(-312, -8, 4), (-300, -8, 4), (-300, -74, 4), (-312, -74, 4)]), -16.0, 16.0),
         wk.rubber('M_SmgPad', '#141414'), bevel=0.0020)
    make('Smg_StockHinge', cyl(W(-46, -2, -16), W(-46, -2, 16), 0.0060, n=24), S)
    PIVOT['SMG'] = (g.centre(0.45).x, g.centre(0.45).y)
    return 'SMG'


BUILDERS['SMG'] = smg


# ================================================================== 10. BLUEPRINT (Mechanic, secondary)
def blueprint():
    alu = wk.steel('M_BpAlu', base='#b9bcc0', bare='#e2e4e7', rough=0.38, wear=0.6, scratch=1.8, edge_gain=8.0, tint_var=0.05)
    clipm = wk.steel('M_BpClip', base='#a7aaae', bare='#d5d7da', rough=0.25, wear=0.8, scratch=0.8, edge_gain=8.0)
    paper = wk.image_mat('M_BpPaper', 'blueprint.png', rough=0.82, bump=0.0)
    wood_p = wk.wood('M_BpPencil', light='#f0b52a', dark='#d89a18', rough=0.5, ring=200.0, axis='Y', grain=0.1, wear=0.3)
    graphite = wk.plastic('M_BpGraphite', '#262628', rough=0.35)
    eraser = wk.plastic('M_BpEraser', '#e6909a', rough=0.7)
    ferrule = wk.steel('M_BpFerrule', base='#9aa0a4', bare='#c8ccd0', rough=0.3, wear=0.3, scratch=0.5)
    # clipboard lies in the X-Z plane (facing -Y), held like a book: 230 x 320 mm aluminium board
    Wd, Ht = 230.0, 320.0
    bd = rounded([(-Wd / 2, -Ht / 2, 8), (Wd / 2, -Ht / 2, 8), (Wd / 2, Ht / 2, 8), (-Wd / 2, Ht / 2, 8)], n=8)
    # profile() extrudes across x; build in (u=x_board, v=z) then rotate so the board faces -Y
    board = make('Bp_Board', profile(bd, -1.0, 1.0), alu, bevel=0.0006)
    R90 = Matrix.Rotation(-PI / 2, 4, 'Z')
    board.data.transform(R90)
    # paper: slightly smaller, bowed, curled corners (bottom-right corner most)
    nu, nv = 40, 56
    pw, ph = 216.0, 290.0
    verts = []; uvs = []; faces = []
    for i in range(nu + 1):
        for j in range(nv + 1):
            s = i / nu; t = j / nv
            x = (s - 0.5) * pw; z = (t - 0.5) * ph + 4.0
            lift = 1.2 + 0.6 * math.sin(PI * s) * math.sin(PI * t)
            for (cs, ct, amp) in ((1, 0, 22.0), (0, 0, 9.0), (1, 1, 5.0), (0, 1, 3.0)):
                d = math.hypot((s - cs) / 0.28, (t - ct) / 0.28)
                if d < 1:
                    lift += amp * (1 - d) ** 2.2
            lift += 0.5 * math.sin(t * 7 + 1.2) * (1 - t)
            verts.append(Vector((x * MM, -(lift + 1.0) * MM, z * MM))); uvs.append((s, t))
    for i in range(nu):
        for j in range(nv):
            q = i * (nv + 1) + j
            faces.append((q, q + nv + 1, q + nv + 2, q + 1))
    bm = wk.bm_from(verts, faces)
    uvl = bm.loops.layers.uv.new('UVMap'); bm.verts.index_update()
    for f in bm.faces:
        for lp in f.loops:
            lp[uvl].uv = uvs[lp.vert.index]
    make('Bp_Paper', bm, paper, solid=0.0003)
    # a couple of under-sheets peeking out
    for k in range(2):
        v2 = [Vector((v.x + (k + 1) * 0.0012, v.y + (k + 1) * 0.0003, v.z - (k + 1) * 0.0018)) for v in verts]
        bm2 = wk.bm_from(v2, faces)
        uvl = bm2.loops.layers.uv.new('UVMap'); bm2.verts.index_update()
        for f in bm2.faces:
            for lp in f.loops:
                lp[uvl].uv = uvs[lp.vert.index]
        make('Bp_Under%d' % k, bm2, paper, solid=0.0002)
    # spring clip at the top: base plate, curved jaw, lever loop, rivets
    cz = Ht / 2 - 18.0
    bp = rounded([(-50, cz - 14, 4), (50, cz - 14, 4), (50, cz + 12, 6), (-50, cz + 12, 6)], n=6)
    base = make('Bp_ClipBase', profile(bp, -1.8, 0.0), clipm, bevel=0.0005)
    base.data.transform(R90 @ Matrix.Translation((-0.0010, 0, 0)))
    jw = rounded([(-48, -10, 3), (48, -10, 3), (44, 10, 8), (-44, 10, 8)], n=6)
    jo = make('Bp_ClipJaw', profile(jw, -1.2, 1.2), clipm, bevel=0.0004)
    jo.data.transform(Matrix.Translation((0, -0.0058, (cz - 6) * MM)) @ Matrix.Rotation(math.radians(-18), 4, 'X') @ Matrix.Rotation(-PI / 2, 4, 'Z') @
                      Matrix.Rotation(PI / 2, 4, 'Y'))
    loop = [Vector((x * MM, -y * MM, (cz + z) * MM)) for (x, y, z) in ((-26, 3, 6), (-26, 14, 20), (-18, 20, 32), (0, 22, 35), (18, 20, 32),
                                                                        (26, 14, 20), (26, 3, 6))]
    make('Bp_ClipLever', tube(wk.spline(loop, 6), 0.0024, n=12), clipm)
    make('Bp_ClipBarrel', cyl(Vector((-32 * MM, -6 * MM, (cz + 4) * MM)), Vector((32 * MM, -6 * MM, (cz + 4) * MM)), 0.0042, n=24), clipm)
    for x in (-40, 40):
        make('Bp_Rivet', sphere(Vector((x * MM, -1.9 * MM, (cz + 6) * MM)), 0.0030, seg=16, rings=8, scale=(1, 0.4, 1)), clipm)
    # pencil clipped under the clip, angled
    a = math.radians(-8)
    d = Vector((math.cos(a), 0, math.sin(a)))
    p0 = Vector((-70 * MM, -9 * MM, (cz - 12) * MM))
    hexr = 3.6
    pen = lathe([(hexr, 0.0), (hexr, 150.0)], n=6, phase=PI / 6)
    po = make('Bp_Pencil', pen, wood_p, bevel=0.0003, angle=40)
    tip = lathe([(hexr * 0.95, 150.0), (1.0, 166.0), (0.9, 167.0)], n=24)
    to = make('Bp_PencilWood', tip, wk.wood('M_BpPencilWood', light='#e7c79a', dark='#cfa676', rough=0.6, ring=300, axis='Y', grain=0.2))
    lead = make('Bp_PencilLead', lathe([(1.15, 162.0), (0.0, 169.0)], n=16), graphite)
    fe = make('Bp_Ferrule', lathe([(hexr + 0.3, -12.0), (hexr + 0.3, 1.0)], n=32), ferrule)
    er = make('Bp_Eraser', lathe([(hexr - 0.1, -22.0), (hexr, -12.0)], n=32, cap0=True), eraser)
    M = Matrix.Translation(p0) @ Matrix.Rotation(a, 4, 'Y') @ Matrix.Rotation(PI / 2, 4, 'Z')
    for o in (po, to, lead, fe, er):
        o.data.transform(M)
    PIVOT['Blueprint'] = (0.0, 0.0)
    return 'Blueprint'


BUILDERS['Blueprint'] = blueprint


# ================================================================== 11. MINIGUN (Greg, primary)
def minigun():
    gun = wk.steel('M_MgBarrels', base='#4d5157', bare='#b4b7bc', rough=0.34, wear=1.2, scratch=1.1, edge_gain=10.0, tint_var=0.08)
    heat = wk.steel('M_MgHeat', base='#3b342e', bare='#8e8a86', rough=0.42, wear=0.6, scratch=0.6, tint_var=0.2)   # heat-darkened muzzles
    gun_dk = wk.steel('M_MgDark', base='#1e2023', bare='#8f9297', rough=0.42, wear=1.2, scratch=0.9, edge_gain=10.0)
    park = wk.steel('M_MgPark', base='#2b2d30', bare='#9a9da2', rough=0.6, wear=1.0, scratch=1.2, edge_gain=8.0, tint_var=0.1)
    red = wk.paint('M_MgRed', '#4a0e0c', under='#3f4246', rough=0.5, wear=1.6, scuff=1.5, col_var=0.16)
    brass = wk.steel('M_MgBrass', base='#a8823a', bare='#d8b66e', rough=0.30, wear=0.5, scratch=0.5)
    copper = wk.steel('M_MgCopper', base='#a5582e', bare='#d08a58', rough=0.32, wear=0.3, scratch=0.3)
    rub = wk.rubber('M_MgRubber', '#141414')
    cable = wk.rubber('M_MgCable', '#1a1a1b', rough=0.55, stipple=0.3)
    starm = wk.NT('M_MgStar')
    tx = starm.node('ShaderNodeTexImage'); tx.image = bpy.data.images.load(os.path.join(wk.TEX, 'star_paint.png'), check_existing=True)
    uvn = starm.node('ShaderNodeUVMap'); uvn.uv_map = 'UVMap'; starm.link(uvn.outputs[0], tx.inputs['Vector'])
    starm.set('Base Color', tx.outputs['Color']); starm.set('Alpha', tx.outputs['Alpha']); starm.set('Roughness', 0.42); starm.set('Metallic', 0.7)
    try:
        starm.m.surface_render_method = 'BLENDED'
    except Exception:
        pass

    # Classic handheld heavy minigun: fat round body, short thick barrel cluster in a big muzzle shroud,
    # tall angular carry-handle frame on top, silver ammo drum lying lengthwise underneath, loop grip at the front.
    silver = wk.steel('M_MgSilver', base='#9da1a6', bare='#d3d6da', rough=0.30, wear=1.0, scratch=1.6, edge_gain=8.0, tint_var=0.06)
    BR = 84.0                       # body radius

    # ================= main body (dark red) + rear cap + front ring
    make('Mg_Body', lathe([(BR - 6, -150.0), (BR, -146.0), (BR, 196.0), (BR - 6, 200.0)], n=128, cap0=False, cap1=False), red)
    for u in (-110.0, -20.0, 70.0, 160.0):                                      # raised bands with bolts
        make('Mg_Band', lathe([(BR, u - 6), (BR + 3.0, u - 5), (BR + 3.0, u + 5), (BR, u + 6)], n=128, cap0=False, cap1=False), park)
        for k in range(12):
            a = 2 * PI * k / 12 + 0.13
            make('Mg_BandBolt', sphere(W(u, (BR + 3.2) * math.sin(a), (BR + 3.2) * math.cos(a)), 0.0028, seg=12, rings=6), gun_dk)
    make('Mg_RearCap', lathe([(BR - 6, -150.0), (BR - 2, -156.0), (BR - 10, -172.0), (BR - 28, -186.0), (BR - 52, -194.0), (0, -197.0)], n=128),
         park, bevel=0.0)
    make('Mg_RearHub', lathe([(0, -196.0), (26.0, -196.0), (28.0, -200.0), (28.0, -212.0), (24.0, -216.0), (0, -216.0)], n=64), gun_dk)
    for k in range(8):
        a = 2 * PI * k / 8
        make('Mg_RearBolt', cyl(W(-185, 44 * math.sin(a), 44 * math.cos(a)), W(-190, 44 * math.sin(a), 44 * math.cos(a)), 0.0042, n=6), gun_dk)
    make('Mg_FrontRing', lathe([(0, 196.0), (BR + 4, 196.0), (BR + 6, 200.0), (BR + 6, 222.0), (BR + 2, 226.0), (64.0, 232.0), (0, 232.0)], n=128),
         park, bevel=0.0)
    # gold sheriff star painted on the round body (left side), conformed to the curve
    nu, nv = 16, 16; sw = 110.0; su, sa = 20.0, 0.0
    verts = []; uvs = []; faces = []
    for i in range(nu + 1):
        for j in range(nv + 1):
            s = (i / nu - 0.5) * sw; t = (j / nv - 0.5) * sw
            a = sa + t / BR
            verts.append(W(su + s, (BR + 0.4) * math.sin(a), (BR + 0.4) * math.cos(a))); uvs.append((1 - i / nu, j / nv))
    for i in range(nu):
        for j in range(nv):
            q = i * (nv + 1) + j
            faces.append((q, q + 1, q + nv + 2, q + nv + 1))
    sb = wk.bm_from(verts, faces)
    uvl = sb.loops.layers.uv.new('UVMap'); sb.verts.index_update()
    for f in sb.faces:
        for lp in f.loops:
            lp[uvl].uv = uvs[lp.vert.index]
    bmesh.ops.recalc_face_normals(sb, faces=sb.faces[:])
    make('Mg_Star', sb, starm.m)

    # ================= barrel cluster: rotor, six thick barrels, spacer ring, big muzzle shroud
    RC = 38.0
    make('Mg_Rotor', lathe([(0, 232.0), (60.0, 232.0), (62.0, 236.0), (62.0, 268.0), (58.0, 272.0), (0, 272.0)], n=96), gun_dk)
    make('Mg_Spindle', lathe([(16.0, 272.0), (16.0, 560.0)], n=40), gun_dk)
    for k in range(6):
        a = PI / 2 + k * PI / 3
        v, x = RC * math.sin(a), RC * math.cos(a)
        make('Mg_Barrel%d' % k, lathe([(15.5, 272.0), (15.5, 290.0), (14.0, 296.0), (14.0, 560.0)], n=32, axis_v=v, x=x), gun, bevel=0.0)
    make('Mg_SpacerRing', lathe([(0, 400.0), (60.0, 400.0), (62.0, 402.0), (62.0, 418.0), (60.0, 420.0), (0, 420.0)], n=96,
                                shape=lambda i, kk, rr, ang: rr * (1.0 - 0.12 * (0.5 + 0.5 * math.cos(6 * (ang - PI / 2) - PI)))), park)
    # muzzle shroud: thick open tube, barrels visible inside, inner lip
    sh = [(58.0, 520.0), (66.0, 522.0), (68.0, 528.0), (68.0, 612.0), (66.0, 616.0), (60.0, 618.0), (58.0, 614.0), (58.0, 520.0)]
    make('Mg_MuzzleShroud', lathe(sh, n=128, cap0=False, cap1=False), gun_dk, bevel=0.0)
    make('Mg_ShroudInner', lathe([(57.8, 524.0), (57.8, 614.0)], n=96, cap0=False, cap1=False), heat)
    make('Mg_ShroudBack', lathe([(16.5, 520.0), (58.5, 520.0)], n=96, cap0=False, cap1=False), gun_dk)
    for k in range(6):
        a = PI / 2 + k * PI / 3
        v, x = RC * math.sin(a), RC * math.cos(a)
        mo = make('Mg_Muzzle%d' % k, lathe([(14.0, 520.0), (15.0, 590.0), (15.0, 600.0)], n=32, axis_v=v, x=x), heat)
        cut(mo, cyl(W(570, v, x), W(610, v, x), 0.0090, n=32), 'bore')
    make('Mg_SpindleNose', lathe([(16.0, 560.0), (16.0, 596.0), (12.0, 600.0), (0, 601.0)], n=32), gun_dk)
    for k in range(4):                                         # bolts on the shroud
        a = PI / 4 + k * PI / 2
        make('Mg_ShroudBolt', cyl(W(570, 67.5 * math.sin(a), 67.5 * math.cos(a)), W(570, 71 * math.sin(a), 71 * math.cos(a)), 0.0045, n=6), park)

    # ================= silver ammo drum lying lengthwise underneath + connector + latch
    DV = -BR - 66.0; DRr = 68.0
    make('Mg_Drum', lathe([(0, -130.0), (DRr - 4, -130.0), (DRr, -126.0), (DRr, 150.0), (DRr - 4, 154.0), (0, 154.0)], n=128, axis_v=DV), silver)
    for u in (-118.0, 142.0):
        make('Mg_DrumRim', lathe([(DRr, u - 5), (DRr + 3.5, u - 4), (DRr + 3.5, u + 4), (DRr, u + 5)], n=128, axis_v=DV, cap0=False, cap1=False), gun_dk)
    for u in (-60.0, 10.0, 80.0):
        make('Mg_DrumRib', lathe([(DRr, u - 2), (DRr + 1.6, u - 1), (DRr + 1.6, u + 1), (DRr, u + 2)], n=128, axis_v=DV, cap0=False, cap1=False), silver)
    make('Mg_DrumCapBolt', lathe([(0, -138.0), (18.0, -138.0), (20.0, -134.0), (20.0, -130.0), (0, -130.0)], n=48, axis_v=DV), gun_dk)
    make('Mg_DrumConnector', profile(rounded([(-90, DV + 40, 8), (120, DV + 40, 8), (120, -BR + 14, 6), (-90, -BR + 14, 6)]), -34.0, 34.0),
         gun_dk, bevel=0.0025, seg=4)
    lt = rounded([(150, DV - 6, 3), (166, DV - 6, 3), (166, DV + 12, 3), (150, DV + 12, 3)])
    make('Mg_DrumLatch', profile(lt, DRr - 2, DRr + 8), park, bevel=0.0010)
    make('Mg_DrumHandle', tube(wk.spline([W(-40, DV - DRr - 2, -20), W(-40, DV - DRr - 18, -10), W(-40, DV - DRr - 18, 10), W(-40, DV - DRr - 2, 20)], 6),
                               0.0050, n=12), gun_dk)

    # ================= tall angular carry-handle frame on top (square tube) + rubber grip on its top bar
    hp = [W(214, BR - 4, 0), W(236, BR + 70, 0), W(150, BR + 118, 0), W(-60, BR + 118, 0), W(-140, BR + 70, 0), W(-140, BR - 2, 0)]
    pts = []
    for a_, b_ in zip(hp[:-1], hp[1:]):
        for i in range(10):
            pts.append(a_.lerp(b_, i / 10))
    pts.append(hp[-1])
    make('Mg_HandleFrame', tube(pts, 0.0120, n=4, flat=1.0), park, bevel=0.0025, seg=3)
    make('Mg_HandleGrip', lathe([(15.5, -40.0), (16.5, -36.0), (16.5, 130.0), (15.5, 134.0)], n=48, axis_v=BR + 118.0,
                                shape=lambda i, k, r, a: r * (1.0 + 0.035 * math.cos(a * 18))), rub)
    for (u, v) in ((214, BR - 4), (-140, BR - 2)):
        make('Mg_HandleFoot', profile(rounded([(u - 18, v - 6, 4), (u + 18, v - 6, 4), (u + 18, v + 8, 4), (u - 18, v + 8, 4)]), -16, 16), park,
             bevel=0.0015)

    # ================= front loop grip underneath + rear grip with trigger
    fg = [W(180, -BR + 4, 0), W(200, -BR - 40, 0), W(238, -BR - 100, 0), W(270, -BR - 104, 0), W(268, -BR - 60, 0), W(240, -BR + 8, 0)]
    make('Mg_FrontGripFrame', tube(wk.spline(fg, 8), 0.0100, n=16), park)
    make('Mg_FrontGrip', cyl(W(212, -BR - 64, 0), W(244, -BR - 104 + 4, 0), 0.0170, n=40), rub)
    rg = rounded([(-176, -40, 6), (-150, -40, 6), (-156, -128, 10), (-188, -132, 10)], n=6)
    make('Mg_RearGrip', profile(rg, -16, 16), rub, bevel=0.0060, seg=5)
    make('Mg_TriggerBar', profile(rounded([(-146, -48, 3), (-136, -48, 3), (-140, -86, 3), (-150, -86, 3)]), -10, 10),
         wk.plastic('M_MgButton', '#8a1210', rough=0.35), bevel=0.0012)

    PIVOT['Minigun'] = (-168.0, -86.0)
    return 'Minigun'


BUILDERS['Minigun'] = minigun


# ================================================================== 12. SNUB-NOSE REVOLVER (Greg, secondary)
def snubnose():
    dark = wk.steel('M_SnDark', base='#1a1b1e', bare='#a3a6ab', rough=0.33, wear=1.3, scratch=0.9, edge_gain=11.0)
    dark_dk = wk.steel('M_SnDarkDk', base='#111214', bare='#94979c', rough=0.36, wear=0.8, scratch=0.6, edge_gain=11.0)
    wood = wk.wood('M_SnWood', light='#6a3a1c', dark='#2a1309', rough=0.4, ring=24.0, axis='Z', grain=0.5)
    lead = wk.steel('M_SnLead', base='#606266', bare='#7b7e82', rough=0.55, wear=0.0, scratch=0.0, metallic=0.85)
    cax = -12.0
    fo = rounded([(-7, 9.5, 3), (-2, 11.5, 2), (36, 11.5, 3), (41, 9.5, 3), (41, -18.0, 4), (36, -32.0, 8), (20, -36.0, 10), (-7, -36.5, 0)], n=8)
    win = rounded([(-0.5, -30.5, 3.0), (35.5, -30.5, 3.0), (35.5, 6.5, 3.0), (-0.5, 6.5, 3.0)], n=8)
    fob = make('Sn_Frame', profile(fo, -12.8, 12.8, holes=[win]), dark, bevel=0.0017, seg=5, angle=30)
    cut(fob, cyl(W(34.0, 0, 0), W(50, 0, 0), 0.0084, n=40), 'barrelseat')
    # rear frame: hammer housing + backstrap tang running down into the grip (joins grip, hammer and frame)
    rf = rounded([(-6.0, 9.5, 2), (-12.0, 10.5, 4), (-22.0, 6.0, 6), (-28.0, -4.0, 5), (-27.0, -22.0, 3), (-24.0, -40.0, 0),
                  (-6.0, -40.0, 0), (-6.0, -36.5, 0)], n=8)
    rfo = make('Sn_RearFrame', profile(rf, -9.5, 9.5), dark, bevel=0.0016, seg=5, angle=30)
    cut(rfo, box(W(-17.0, 6.0, 0), (0.0066, 0.020, 0.024)), 'hammerslot')
    for sd in (1, -1):
        wk.screw(W(-15.0, -8.0, sd * 9.5), Vector((sd, 0, 0)), r=0.0016, mat=dark_dk, name='Sn_Screw', slot_ang=0.5)
    # short 2" barrel with full-length underlug + ramp front sight
    bar = make('Sn_Barrel', lathe([(8.2, 38.0), (8.2, 88.0), (7.6, 90.0)], n=40), dark, bevel=0.0)
    cut(bar, cyl(W(70, 0, 0), W(95, 0, 0), 0.0046, n=32), 'bore')
    make('Sn_Underlug', profile(rounded([(40, -2, 0), (86, -2, 3), (86, -15, 4), (40, -16, 0)]), -5.5, 5.5), dark, bevel=0.0012)
    make('Sn_FrontSight', profile(rounded([(70, 6, 0), (86, 6, 0), (84, 12.5, 2), (80, 12.5, 1.5)]), -1.6, 1.6), dark, bevel=0.0004)
    # five-shot cylinder (fluted)
    cy = make('Sn_Cylinder', lathe([(11.0, 0.3), (17.6, 0.3), (18.4, 1.6), (18.4, 34.2), (17.4, 35.4), (7.0, 35.4)], n=80, axis_v=cax), dark)
    for k in range(5):
        a = PI / 2 + 2 * PI * k / 5
        cv, cx = cax + 11.8 * math.sin(a), 11.8 * math.cos(a)
        cut(cy, cyl(W(22.0, cv, cx), W(37.0, cv, cx), 0.0050, n=32), 'ch%d' % k)
        make('Sn_Bullet%d' % k, lathe([(4.8, 26.0), (4.8, 30.0), (4.3, 31.6), (3.2, 32.8), (1.6, 33.6), (0.0, 33.9)], n=24, axis_v=cv, x=cx), lead)
        a2 = a + PI / 5
        fl = cyl(W(6.0, cax + 21.4 * math.sin(a2), 21.4 * math.cos(a2)), W(29.0, cax + 21.4 * math.sin(a2), 21.4 * math.cos(a2)), 0.0050, n=24)
        cut(cy, fl, 'fl%d' % k)
    # hammer, trigger, guard
    hm = rounded([(-6, 6, 1.5), (-7, -6, 2), (-13, -12, 3), (-19, -8, 3), (-22, 3, 4), (-27, 10, 3), (-30, 14, 2), (-24, 16, 2), (-15, 10, 3)], n=6)
    make('Sn_Hammer', profile(hm, -3.0, 3.0), dark_dk, bevel=0.0005)
    sp = rounded([(-23.5, 12.5, 1.5), (-30, 12.0, 2), (-33, 15.5, 2), (-31, 18.5, 2), (-24.5, 16.5, 1.5)])
    make('Sn_HammerSpur', profile(sp, -5.0, 5.0), dark_dk, bevel=0.0006)
    make('Sn_Trigger', profile(rounded([(4, -35, 0), (3, -43, 3), (0, -50, 3), (-3.5, -54, 2), (-5.5, -53, 2), (-2.5, -47, 3), (-1, -41, 3), (-1, -35, 0)]),
                               -2.2, 2.2), dark_dk, bevel=0.0005)
    gp = [Vector(W(u, v, 0)) for (u, v) in [(13, -35.5), (14.5, -43), (11.5, -52), (4, -58.0), (-4, -59), (-10, -55.5), (-12.5, -47), (-12.5, -39)]]
    make('Sn_TriggerGuard', tube(wk.spline(gp, 8), 0.0041, n=20, flat=0.42), dark)
    # rounded wooden grip
    g = Grip((-15.0, -30.0), (-16.0, -64.0), (-33.0, -88.0),
             depth=lambda t: (12.5 + 2.0 * math.sin(PI * min(1.0, t * 1.1)), 13.0 + 3.0 * t), width=lambda t: 14.5 + 1.8 * math.sin(PI * t * 0.9),
             e=2.3, butt=0.14)
    R = g.rings(0.0, 1.0, 0.0, 2 * PI, nt=44, nth=56)
    make('Sn_Grip', wk.loft([r[:-1] for r in R], closed=True, cap0=True, cap1=True), wood)
    for sgn in (1, -1):
        wk.screw(g.point(0.42, PI / 2 if sgn > 0 else -PI / 2, 1.0, 0.1), Vector((sgn, 0, 0)), r=0.0022, mat=dark_dk, name='Sn_GripScrew', slot_ang=0.8)
    c = g.centre(0.4)
    PIVOT['SnubNose'] = (c.x, c.y)
    return 'SnubNose'


BUILDERS['SnubNose'] = snubnose


# ====================================================================== AMMO
# Real-size cartridges / projectiles (mm), muzzle direction = +u (-Y), origin at the base of each piece.
# Per calibre: <C>_Bullet (what flies), <C>_Round (loaded cartridge), <C>_Casing (fired, empty).
def _ammo_mats():
    return dict(brass=wk.steel('M_AmBrass', base='#9c7a35', bare='#e0c27a', rough=0.28, wear=0.6, scratch=0.5, edge_gain=6.0),
                nickel=wk.steel('M_AmNickel', base='#8d8f92', bare='#d5d7da', rough=0.25, wear=0.4, scratch=0.4, edge_gain=6.0),
                copper=wk.steel('M_AmCopper', base='#a4562c', bare='#d99263', rough=0.30, wear=0.3, scratch=0.3, edge_gain=5.0),
                lead=wk.steel('M_AmLead', base='#55585d', bare='#8c8f94', rough=0.55, wear=0.2, scratch=0.2, metallic=0.55),
                primer=wk.steel('M_AmPrimer', base='#b0b2b5', bare='#d0d2d4', rough=0.3, wear=0.0, scratch=0.0))


# calibre: case profile (r, u) outside, case length, bullet profile from its base, seat depth, metals
CALIBRES = {
    'Ammo45': dict(case=[(6.75, 0.0), (6.75, 1.5), (6.05, 1.5), (6.05, 2.4), (5.95, 32.6)], inner=5.55,
                   bullet=[(5.72, 0.0), (5.72, 9.0), (5.4, 11.5), (4.6, 14.2), (3.3, 16.4), (1.6, 17.6), (0.0, 18.0)],
                   seat=8.0, case_m='brass', bullet_m='lead', rim=True),
    'Ammo9mm': dict(case=[(4.95, 0.0), (4.95, 0.9), (4.4, 0.9), (4.4, 1.6), (4.95, 2.4), (4.82, 19.15)], inner=4.5,
                    bullet=[(4.5, 0.0), (4.5, 6.5), (4.25, 9.0), (3.6, 11.6), (2.5, 13.6), (1.2, 14.8), (0.0, 15.2)],
                    seat=5.0, case_m='brass', bullet_m='copper'),
    'Ammo3006': dict(case=[(6.0, 0.0), (6.0, 1.2), (5.2, 1.2), (5.2, 2.2), (6.0, 3.2), (5.85, 43.0), (5.6, 44.2), (4.4, 48.6),
                           (4.25, 49.4), (4.25, 63.3)], inner=3.9,
                     bullet=[(3.4, 0.0), (3.9, 3.2), (3.9, 15.0), (3.6, 20.0), (2.9, 24.5), (1.8, 28.6), (0.6, 31.4), (0.0, 32.0)],
                     seat=8.0, case_m='brass', bullet_m='copper'),
    'Ammo3030': dict(case=[(7.3, 0.0), (7.3, 1.6), (6.5, 1.6), (6.3, 36.0), (5.9, 37.5), (4.6, 40.6), (4.45, 41.5), (4.45, 51.8)],
                     inner=3.9, bullet=[(3.9, 0.0), (3.9, 14.0), (3.5, 18.0), (2.6, 21.5), (1.9, 23.0), (0.0, 23.3)],
                     seat=9.0, case_m='nickel', bullet_m='lead', rim=True),
}


def _case(c, m, mats, fired=False):
    prof = list(c['case']); L = prof[-1][1]
    mouth = [(c['inner'], L), (c['inner'], 4.0), (0.0, 4.0)]
    make('Case', lathe([(0.0, 0.0)] + prof + mouth, n=40, cap0=False, cap1=False), mats[m], bevel=0.0)
    make('Primer', lathe([(0.0, -0.15), (2.2 if prof[0][0] < 6 else 2.6, -0.15), (2.2 if prof[0][0] < 6 else 2.6, 0.4), (0.0, 0.4)],
                         n=24, cap0=False, cap1=False), mats['primer'], bevel=0.0)
    if fired:                                                        # firing-pin dent
        make('Dent', lathe([(0.0, -0.4), (0.7, -0.4), (0.9, -0.1), (0.0, -0.1)], n=16, cap0=False, cap1=False), mats['primer'], bevel=0.0)
    return L


def _bullet(c, mats, base_u=0.0):
    prof = [(0.0, base_u)] + [(r, u + base_u) for (r, u) in c['bullet']]
    make('Bullet', lathe(prof, n=40, cap0=False, cap1=False), mats[c['bullet_m']], bevel=0.0)


def _ammo_builder(cal, kind):
    def b():
        mats = _ammo_mats(); c = CALIBRES[cal]
        if kind == 'Bullet':
            _bullet(c, mats)
        elif kind == 'Casing':
            _case(c, c['case_m'], mats, fired=True)
        else:
            L = _case(c, c['case_m'], mats)
            _bullet(c, mats, base_u=L - c['seat'])
        PIVOT[cal + '_' + kind] = (0.0, 0.0)
        return cal + '_' + kind
    return b


for _cal in CALIBRES:
    for _k in ('Bullet', 'Round', 'Casing'):
        BUILDERS['%s_%s' % (_cal, _k)] = _ammo_builder(_cal, _k)


def shotshell():
    """12 gauge buckshot shell: red plastic hull, tall brass head, 6-point fold crimp"""
    hull = wk.plastic('M_AmHull', '#a3201a', rough=0.5)
    m = _ammo_mats()
    make('Ss_Head', lathe([(0.0, 0.0), (11.2, 0.0), (11.2, 1.4), (10.6, 1.4), (10.6, 15.0), (10.25, 15.6), (0.0, 15.6)],
                          n=48, cap0=False, cap1=False), m['brass'], bevel=0.0)
    make('Ss_Primer', lathe([(0.0, -0.15), (3.0, -0.15), (3.0, 0.4), (0.0, 0.4)], n=24, cap0=False, cap1=False), m['primer'])
    def crimp(i, k, r, a):
        return r * (1.0 - (0.06 if k == 3 else 0.0) * (0.5 + 0.5 * math.cos(6 * a)))
    make('Ss_Hull', lathe([(0.0, 15.0), (10.25, 15.0), (10.3, 64.0), (9.6, 67.5), (5.0, 69.0), (0.0, 69.4)], n=48, cap0=False, cap1=False,
                          shape=crimp), hull, bevel=0.0)
    PIVOT['Shotgun12_Shell'] = (0.0, 0.0)
    return 'Shotgun12_Shell'


def buckshot():
    make('Pellet', sphere(W(4.2, 0, 0), 0.0042, seg=20, rings=10), _ammo_mats()['lead'])
    PIVOT['Shotgun12_Pellet'] = (0.0, 0.0)
    return 'Shotgun12_Pellet'


def _closed(prof):
    """close a lathe profile onto the axis at both ends: a solid, so normals point out (edge-wear masks need that)"""
    prof = list(prof)
    if prof[0][0] > 0:
        prof = [(0.0, prof[0][1])] + prof
    if prof[-1][0] > 0:
        prof = prof + [(0.0, prof[-1][1])]
    return prof


def rocket():
    """TF2 'stock' style rocket (concept sheet): blunt nose cap, fat cone warhead, dark collar, long grey motor body with a
    dark band, flared nozzle at the back. Body fits the launcher tube (ID 89 mm); origin at the nozzle, nose along +u."""
    grey = wk.paint('M_RkGrey', '#4a4e52', under='#6e7276', rough=0.55, wear=0.35, scuff=0.35, col_var=0.06)
    head = wk.paint('M_RkHead', '#393c3f', under='#686b6f', rough=0.5, wear=0.4, scuff=0.35, col_var=0.06)
    dark = wk.paint('M_RkDark', '#18191b', under='#4a4c50', rough=0.6, wear=0.3, scuff=0.3)
    tip = wk.steel('M_RkTip', base='#26282b', bare='#8d9095', rough=0.45, wear=1.0, scratch=0.6)
    noz = wk.steel('M_RkNozzle', base='#1b1c1e', bare='#6a6c70', rough=0.5, wear=1.0, scratch=0.5)
    # flared nozzle bell + neck
    make('Rk_Nozzle', lathe(_closed([(0.0, 22.0), (26.0, 20.0), (36.0, 3.0), (41.0, 0.0), (43.0, 1.5), (43.0, 9.0), (40.0, 12.0),
                             (36.0, 22.0), (32.0, 36.0), (30.5, 52.0), (31.0, 60.0)]), n=56, cap0=False, cap1=False), noz, bevel=0.0)
    make('Rk_Throat', lathe(_closed([(0.0, 21.0), (12.0, 21.0), (12.0, 23.0), (0.0, 23.0)]), n=24, cap0=False, cap1=False), dark)
    # motor body
    make('Rk_Body', lathe(_closed([(31.0, 60.0), (35.5, 68.0), (36.0, 74.0), (36.0, 470.0)]), n=56, cap0=False, cap1=False), grey)
    make('Rk_BandRear', lathe(_closed([(36.0, 74.0), (37.2, 76.0), (37.2, 100.0), (36.0, 102.0)]), n=56, cap0=False, cap1=False), dark)
    make('Rk_BandMid', lathe(_closed([(36.0, 300.0), (37.5, 303.0), (37.5, 352.0), (36.0, 355.0)]), n=56, cap0=False, cap1=False), dark)
    # collar where the warhead meets the motor
    make('Rk_Collar', lathe(_closed([(36.0, 470.0), (38.5, 472.0), (38.5, 492.0), (37.0, 496.0)]), n=56, cap0=False, cap1=False), dark)
    # warhead: short swell to the widest point, groove, long cone to the nose
    make('Rk_Head', lathe(_closed([(37.0, 496.0), (40.0, 512.0), (43.5, 540.0), (44.0, 556.0), (44.0, 572.0)]), n=56, cap0=False, cap1=False), head)
    make('Rk_Groove', lathe(_closed([(44.0, 572.0), (41.5, 574.0), (41.5, 580.0), (44.0, 582.0)]), n=56, cap0=False, cap1=False), dark)
    make('Rk_Cone', lathe(_closed([(44.0, 582.0), (43.0, 600.0), (33.0, 640.0), (22.0, 676.0), (17.0, 690.0)]), n=56, cap0=False, cap1=False), head)
    make('Rk_Tip', lathe(_closed([(17.0, 690.0), (15.0, 692.0), (15.0, 708.0), (12.0, 714.0), (0.0, 716.0)]), n=40, cap0=False, cap1=False), tip)
    PIVOT['Rocket'] = (0.0, 0.0)
    return 'Rocket'


BUILDERS['Shotgun12_Shell'] = shotshell
BUILDERS['Shotgun12_Pellet'] = buckshot
BUILDERS['Rocket'] = rocket
AMMO = [k for k in BUILDERS if k.startswith(('Ammo', 'Shotgun12', 'Rocket'))]


def build(name):
    wk.new_scene()
    BUILDERS[name]()
    # move the grip point to the origin
    pu, pv = PIVOT.get(name, (0.0, 0.0))
    off = -W(pu, pv, 0)
    for ob in list(wk.coll().objects) + list(wk.coll('CUTTERS').objects):
        ob.data.transform(Matrix.Translation(off))
    wk.finalize()
    wk.studio()
    return name
