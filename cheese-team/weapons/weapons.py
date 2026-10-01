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
    nickel = wk.steel('M_DerNickel', base='#aba79e', bare='#a5803f', rough=0.16, wear=1.3, scratch=1.0, edge_gain=12.0, tint_var=0.04)
    nickel_dk = wk.steel('M_DerNickelDark', base='#8e8a83', bare='#8f6f37', rough=0.30, wear=0.8, scratch=0.6, edge_gain=12.0)
    bore = wk.steel('M_DerBore', base='#1b1b1c', bare='#3a3a3c', rough=0.5, wear=0.0, scratch=0.0)
    pearl = wk.pearl('M_DerPearl')

    # ---- barrel block: two stacked .41 barrels, top rib, side flutes, hinge lug at the top rear
    bb = rounded([(0.0, 13.0, 2), (74.0, 13.0, 2.5), (76.0, 11.0, 1.5), (76.0, -12.0, 1.5), (74.0, -13.5, 2.5), (0.0, -13.5, 2)], n=6)
    barrels = make('Der_Barrels', profile(bb, -8.6, 8.6), nickel, bevel=0.0016, seg=5, angle=30)
    for (bv, nm) in ((6.2, 'up'), (-6.7, 'dn')):
        cut(barrels, cyl(W(20.0, bv, 0), W(80.0, bv, 0), 0.0052, n=40), 'bore_' + nm)
        cut(barrels, lathe([(5.2, 75.3), (6.4, 76.4), (6.4, 78.0)], n=40, axis_v=bv), 'crown_' + nm)
        make('Der_Bore_' + nm, lathe([(5.25, 40.0), (5.25, 75.0)], n=32, axis_v=bv, cap0=True, cap1=False), bore, smooth=True)
    for side in (1, -1):
        g = box((0, 0, 0), (0.0016, 0.070, 0.0024))
        transform(g, Matrix.Translation(W(39.0, -0.3, side * 8.6)))
        cut(barrels, g, 'flute%d' % side)
    rib = rounded([(3.0, 12.5, 0), (73.0, 12.5, 0), (72.0, 15.0, 1.5), (4.0, 15.0, 1.5)])
    make('Der_Rib', profile(rib, -2.6, 2.6), nickel, bevel=0.0007)
    make('Der_FrontSight', sphere(W(70.5, 15.6, 0), 0.0016, seg=16, rings=8, scale=(0.8, 1.6, 1.0)), nickel)
    hl = rounded([(-4.0, 11.0, 3), (5.0, 11.0, 0), (5.0, 18.0, 3.5), (-4.0, 18.0, 3.5)])
    make('Der_HingeLug', profile(hl, -5.0, 5.0), nickel, bevel=0.0010)
    for side in (1, -1):
        make('Der_HingePin%d' % side, cyl(W(0.5, 14.5, side * 5.0), W(0.5, 14.5, side * 6.2), 0.0021, n=20), nickel_dk)

    # ---- frame: hammer housing + recoil shield behind the barrels, lip under them, spur-trigger sheath
    fr = rounded([(0.0, 11.0, 0), (0.0, -13.0, 0), (14.0, -13.5, 0), (14.0, -16.5, 2), (-4.0, -17.5, 3), (-9.0, -24.0, 2.5),
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
