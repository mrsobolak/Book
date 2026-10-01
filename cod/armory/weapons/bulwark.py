"""BULWARK-60: belt-fed 7.62 light machine gun with a 100-round box and deployed bipod."""
from lib import *


def build():
    # ---- receiver + feed cover
    rc = prism("Receiver", rrect(-0.165, -0.034, 0.165, 0.030, 0.004), 0.0, 0.050, "Paint", bev=0.0012, segs=2)
    bm = bmesh.new()
    bm_prism(bm, rrect(-0.030, 0.004, 0.036, 0.026, 0.003), -0.025, 0.012)                  # feed port (left)
    bm_prism(bm, rrect(-0.020, -0.022, 0.050, -0.004, 0.003), 0.025, 0.012)                 # ejection port (right)
    for s in (1, -1):
        bm_prism(bm, rrect(-0.152, -0.024, -0.042, 0.020, 0.004), s * 0.025, 0.003)
        bm_prism(bm, rrect(0.060, -0.024, 0.152, 0.020, 0.004), s * 0.025, 0.003)
    cut(rc, bm)
    prism("FeedCover", path([("M", -0.122, 0.028), ("L", 0.100, 0.028), ("L", 0.100, 0.040), ("Q", (0.100, 0.046), (0.094, 0.046), 3),
                             ("L", -0.100, 0.046), ("Q", (-0.120, 0.046), (-0.125, 0.036), 4)]),
          0.0, 0.046, "Paint", bev=0.0012, segs=2)
    rail("CoverRail", -0.095, 0.090, 0.044, zt=0.0545)
    prism("CoverLatch", rrect(-0.138, 0.030, -0.119, 0.043, 0.003), 0.0, 0.030, "Steel", bev=0.0008, segs=2)
    rod("CoverHinge", (0.097, -0.024, 0.036), (0.097, 0.024, 0.036), 0.0042, "Steel", seg=20)
    rod("ChargingArm", (0.115, 0.025, -0.006), (0.115, 0.044, -0.006), 0.0032, "Steel", seg=16)
    rod("ChargingKnob", (0.115, 0.040, -0.006), (0.115, 0.054, -0.006), 0.0060, "Polymer", seg=24, rounded=True)

    # ---- trigger module + grip
    tm = prism("TriggerModule", path([("M", -0.125, -0.033), ("L", 0.000, -0.033), ("L", 0.000, -0.048),
                                     ("Q", (-0.002, -0.078), (-0.016, -0.080), 5), ("L", -0.058, -0.078),
                                     ("Q", (-0.070, -0.077), (-0.074, -0.066), 5), ("L", -0.080, -0.050),
                                     ("L", -0.120, -0.046), ("Q", (-0.126, -0.044), (-0.125, -0.033), 3)]),
               0.0, 0.034, "Polymer", bev=0.0012, segs=2)
    bm = bmesh.new(); bm_prism(bm, rrect(-0.064, -0.072, -0.008, -0.045, 0.006), 0.0, 0.05); cut(tm, bm)
    ar_grip("Grip", -0.014, -0.012)
    ar_trigger("Trigger", -0.010, -0.010)
    selector(-0.100, -0.040, -0.017)
    pins("Pins", [(-0.110, -0.024, 0.0045), (0.150, -0.024, 0.0045), (-0.036, -0.041, 0.003)], 0.0250)

    # ---- heavy barrel, carry handle, gas system, handguard, bipod
    lathe("Barrel", [(0.160, 0), (0.160, 0.0170), (0.205, 0.0170), (0.210, 0.0135), (0.640, 0.0135), (0.640, 0)],
          "Steel", seg=40, bev=0.0005, segs=1)
    fh = lathe("FlashHider", [(0.634, 0), (0.634, 0.0100), (0.638, 0.0118), (0.694, 0.0118), (0.700, 0.0104),
                              (0.700, 0.0050), (0.690, 0.0046), (0.646, 0.0046), (0.646, 0)], "Steel", seg=40,
               bev=0.0004, segs=2)
    bm = bmesh.new()
    for k in range(5):
        vs = bm_box(bm, 0.652, 0.692, -0.0018, 0.0018, 0.004, 0.02)
        rotate_verts(bm, vs, 90 + 72 * k, "X", (0, 0, 0))
    cut(fh, bm)
    lathe("HandleClamp", [(0.244, 0.0132), (0.244, 0.0178), (0.276, 0.0178), (0.276, 0.0132)], "Steel", seg=40,
          closed=True, bev=0.0005, segs=1)
    bm = bmesh.new()
    bm_prism(bm, rrect(0.212, 0.050, 0.308, 0.066, 0.007), 0.0, 0.020)
    bm_rod(bm, (0.230, 0, 0.016), (0.226, 0, 0.056), 0.0055)
    bm_rod(bm, (0.290, 0, 0.016), (0.294, 0, 0.056), 0.0055)
    rotate_verts(bm, bm.verts[:], -38, "X", (0, 0, 0))
    mk("CarryHandle", bm, "Polymer", bev=0.0015, segs=2)
    rod("GasTube", (0.160, 0, -0.030), (0.470, 0, -0.030), 0.0075, "Steel", seg=24)
    gb = path([("A", 0.0, 0.0, 0.0175, 0, 180, 12), ("A", 0.0, -0.030, 0.0120, 180, 360, 10)])
    prism("GasBlock", gb, 0.472, 0.034, "Paint", plane="YZ", bev=0.0012, segs=2)
    prism("FrontPost", path([("M", -0.009, 0.014), ("L", 0.009, 0.014), ("L", 0.009, 0.046), ("Q", (0.009, 0.049), (0.006, 0.049), 3),
                             ("L", 0.005, 0.049), ("L", 0.004, 0.034), ("L", 0.0012, 0.032), ("L", 0.0012, 0.042),
                             ("L", -0.0012, 0.042), ("L", -0.0012, 0.032), ("L", -0.004, 0.034), ("L", -0.005, 0.049),
                             ("L", -0.006, 0.049), ("Q", (-0.009, 0.049), (-0.009, 0.046), 3)]),
          0.480, 0.005, "Paint", plane="YZ", bev=0.0005, segs=2)
    hg = prism("Handguard", superellipse(0.025, 0.022, 0, -0.031), 0.283, 0.236, "Polymer", plane="YZ",
               bev=0.0015, segs=2)
    bm = bmesh.new()
    for xc in (0.200, 0.240, 0.280, 0.320, 0.360):
        bm_prism(bm, rrect(xc - 0.012, -0.042, xc + 0.012, -0.030, 0.004), 0.0, 0.07)
    cut(hg, bm)

    prism("BipodYoke", rrect(0.458, -0.056, 0.486, -0.040, 0.004), 0.0, 0.030, "Paint", bev=0.0010, segs=2)
    for s in (1, -1):
        top, knee, foot = (0.472, s * 0.010, -0.050), (0.484, s * 0.052, -0.150), (0.494, s * 0.086, -0.236)
        rod(f"BipodLeg{s}", top, knee, 0.0062, "Paint", seg=20, bev=0.0004, segs=1)
        rod(f"BipodInner{s}", knee, foot, 0.0046, "Steel", seg=20)
        rod(f"BipodFoot{s}", (foot[0], foot[1], foot[2] + 0.004), (foot[0], foot[1] * 1.03, foot[2] - 0.010), 0.0075,
            "Rubber", seg=20, rounded=True)
        lathe(f"BipodCollar{s}", [(0, 0.0056), (0, 0.0078), (0.016, 0.0078), (0.016, 0.0056)], "Steel", seg=20,
              closed=True)
        bpy.data.objects[f"BipodCollar{s}"].location = (0, 0, 0)
    # collars sit at the knees
    for s in (1, -1):
        ob = bpy.data.objects[f"BipodCollar{s}"]
        d = Vector((0.484, s * 0.052, -0.150)) - Vector((0.472, s * 0.010, -0.050))
        ob.rotation_mode = "QUATERNION"
        ob.rotation_quaternion = Vector((1, 0, 0)).rotation_difference(d.normalized())
        ob.location = Vector((0.472, s * 0.010, -0.050)) + d * 0.86

    # ---- fixed stock
    st = prism("Stock", path([("M", -0.160, 0.024), ("L", -0.300, 0.030), ("Q", (-0.400, 0.034), (-0.440, 0.030), 8),
                              ("L", -0.448, 0.030), ("L", -0.452, -0.098), ("L", -0.420, -0.098),
                              ("Q", (-0.330, -0.060), (-0.260, -0.035), 8), ("L", -0.160, -0.030)]),
               0.0, 0.042, "Polymer", taper=lambda x, z: 1.0 - 0.2 * smoothstep(-0.02, -0.09, z), bev=0.0025, segs=3)
    bm = bmesh.new()
    bm_prism(bm, path([("M", -0.290, -0.030), ("L", -0.424, -0.030), ("Q", (-0.434, -0.030), (-0.434, -0.042), 4),
                       ("L", -0.434, -0.074), ("Q", (-0.434, -0.084), (-0.424, -0.080), 4), ("L", -0.300, -0.040),
                       ("Q", (-0.290, -0.036), (-0.290, -0.030), 3)]), 0.0, 0.06)
    for s in (1, -1):
        bm_prism(bm, rrect(-0.400, 0.004, -0.200, 0.020, 0.005), s * 0.021, 0.004)
    cut(st, bm)
    prism("ButtPad", rrect(-0.466, -0.104, -0.451, 0.036, 0.006), 0.0, 0.046, "Rubber", bev=0.003, segs=3)

    # ---- 100-round box with belt feeding into the left side
    bx = prism("AmmoBox", rrect(0.004, -0.172, 0.150, -0.036, 0.008), -0.011, 0.078, "Polymer", bev=0.0025, segs=3)
    bm = bmesh.new()
    for s in (1, -1):
        bm_prism(bm, rrect(0.016, -0.160, 0.138, -0.060, 0.006), -0.011 + s * 0.039, 0.003)
    cut(bx, bm)
    bm = bmesh.new()
    for k in range(5):
        bm_prism(bm, rrect(0.020, -0.152 + 0.019 * k, 0.134, -0.146 + 0.019 * k, 0.002), -0.011, 0.0795)
    mk("BoxRibs", bm, "Polymer", bev=0.0005, segs=1)
    prism("BoxLatch", rrect(0.060, -0.050, 0.094, -0.036, 0.003), -0.011, 0.082, "Steel", bev=0.0008, segs=2)
    text("7.62 LINKED  100", 0.0065, 0.077, -0.112, -0.05045, "MarkBox")

    cases, bullets, links = bmesh.new(), bmesh.new(), bmesh.new()
    n = 5
    for k in range(n):
        t = k / (n - 1)
        y = (1 - t) ** 2 * -0.048 + 2 * (1 - t) * t * -0.058 + t * t * -0.034
        z = (1 - t) ** 2 * -0.040 + 2 * (1 - t) * t * -0.012 + t * t * 0.014
        bprof = cartridge(cases, -0.030, y, z, 0.0060, 0.051, 0.020)
        bm_lathe(bullets, bprof, 20, "X", (0, y, z))
        for lx in (-0.012, 0.008):
            bm_lathe(links, [(lx, 0.0062), (lx, 0.0072), (lx + 0.004, 0.0072), (lx + 0.004, 0.0062)], 20, "X",
                     (0, y, z), closed=True)
    mk("BeltCases", cases, "Brass", bev=0.0003, segs=1)
    mk("BeltBullets", bullets, "Copper")
    mk("BeltLinks", links, "Steel", bev=0.0002, segs=1)

    # ---- compact prism optic on the cover rail
    OZ = 0.074
    prism("PrismBase", path([("M", -0.0125, 0.0505), ("L", 0.0125, 0.0505), ("L", 0.0125, 0.058), ("L", -0.0125, 0.058)]),
          -0.020, 0.060, "Optic", plane="YZ", bev=0.0008, segs=2)
    prism("PrismBody", rrect(-0.0160, 0.057, 0.0160, 0.092, 0.006), -0.022, 0.066, "Optic", plane="YZ", bev=0.0015, segs=2)
    lathe("PrismObjective", [(0.010, 0.0150), (0.010, 0.0182), (0.040, 0.0182), (0.044, 0.0170), (0.044, 0.0150),
                             (0.038, 0.0150)], "Optic", seg=48, c=(0, 0, OZ), closed=True, bev=0.0005, segs=2)
    lathe("PrismOcular", [(-0.078, 0.0120), (-0.078, 0.0160), (-0.054, 0.0160), (-0.054, 0.0120)], "Rubber", seg=48,
          c=(0, 0, OZ), closed=True, bev=0.0008, segs=2)
    bm = bmesh.new()
    bm_lathe(bm, [(0.037, 0), (0.037, 0.0152), (0.038, 0.0152), (0.038, 0)], 48, "X", (0, 0, OZ))
    bm_lathe(bm, [(-0.072, 0), (-0.072, 0.0122), (-0.071, 0.0122), (-0.071, 0)], 48, "X", (0, 0, OZ))
    mk("PrismLenses", bm, "Glass")
    lathe("PrismKnob", [(0, 0), (0, 0.0075), (0.006, 0.0075), (0.007, 0.0065), (0.007, 0)], "Optic", seg=32, axis="Y",
          c=(-0.022, 0.016, OZ), bev=0.0004, segs=1)

    text("BULWARK-60", 0.0075, -0.098, -0.008, -0.02355, "MarkName")
    text("7.62x51 NATO  HALVARD DEFENCE", 0.0030, -0.098, -0.017, -0.02355, "MarkCal")
    text("SN BW-60-0117", 0.0030, 0.106, -0.012, 0.02355, "MarkSerial")
