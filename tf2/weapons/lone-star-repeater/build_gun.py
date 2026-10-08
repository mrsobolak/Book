"""
The Lone Star Repeater - TF2-style semi-auto shotgun.

Procedurally builds the model in Blender and exports a GLB (+ .blend).

    blender -b --python build_gun.py -- <output_dir>

Axes while modelling: +X = muzzle, +Y = right side of the gun, +Z = up.
Units are arbitrary (~1 unit = 1 m); overall length is ~1.7.
"""
import bpy, bmesh, math, sys, os

OUT = sys.argv[sys.argv.index("--") + 1] if "--" in sys.argv else os.path.dirname(os.path.abspath(__file__))
os.makedirs(OUT, exist_ok=True)

bpy.ops.wm.read_factory_settings(use_empty=True)
COL = bpy.context.scene.collection

# ------------------------------------------------------------------ materials
def _lin(c):
    c /= 255.0
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4

def make_mat(name, hexcol, metallic=0.0, rough=0.6):
    m = bpy.data.materials.new(name)
    m.use_nodes = True
    b = m.node_tree.nodes["Principled BSDF"]
    r, g, bl = (int(hexcol[i:i + 2], 16) for i in (1, 3, 5))
    b.inputs["Base Color"].default_value = (_lin(r), _lin(g), _lin(bl), 1)
    b.inputs["Metallic"].default_value = metallic
    b.inputs["Roughness"].default_value = rough
    return m

M = {
    "Wood":     make_mat("Wood",     "#8c4a22", 0.0, 0.55),
    "Gunmetal": make_mat("Gunmetal", "#474c55", 0.6, 0.45),
    "Steel":    make_mat("Steel",    "#7d838c", 0.8, 0.35),
    "Brass":    make_mat("Brass",    "#c9973a", 1.0, 0.35),
    "Rubber":   make_mat("Rubber",   "#2b2522", 0.0, 0.9),
    "Bore":     make_mat("Bore",     "#0b0b0d", 0.0, 1.0),
    "Team":     make_mat("Team",     "#b8383b", 0.0, 0.6),
}

# ------------------------------------------------------------------ 2D path helper
def path(cmds):
    """Tiny SVG-like path -> list of 2D points.
    ('M',x,y) ('L',x,y) ('Q',(cx,cy),(x,y),n) ('A',cx,cy,r,deg0,deg1,n)"""
    pts, cur = [], None
    for c in cmds:
        k = c[0]
        if k in "ML":
            cur = (c[1], c[2]); pts.append(cur)
        elif k == "Q":
            (cx, cy), (x, y) = c[1], c[2]
            n = c[3] if len(c) > 3 else 10
            for i in range(1, n + 1):
                t = i / n
                a, b, d = (1 - t) ** 2, 2 * (1 - t) * t, t * t
                pts.append((a * cur[0] + b * cx + d * x, a * cur[1] + b * cy + d * y))
            cur = (x, y)
        elif k == "A":
            _, cx, cy, r, a0, a1, n = c
            for i in range(n + 1):
                a = math.radians(a0 + (a1 - a0) * i / n)
                cur = (cx + r * math.cos(a), cy + r * math.sin(a)); pts.append(cur)
    out = []
    for p in pts:  # drop duplicates
        if not out or math.dist(p, out[-1]) > 1e-6:
            out.append(p)
    if math.dist(out[0], out[-1]) < 1e-6:
        out.pop()
    return out

def rrect(x0, y0, x1, y1, r, n=5):
    return path([("A", x1 - r, y0 + r, r, -90, 0, n), ("A", x1 - r, y1 - r, r, 0, 90, n),
                 ("A", x0 + r, y1 - r, r, 90, 180, n), ("A", x0 + r, y0 + r, r, 180, 270, n)])

def circle(cx, cy, r, n=40):
    return [(cx + r * math.cos(2 * math.pi * i / n), cy + r * math.sin(2 * math.pi * i / n)) for i in range(n)]

# ------------------------------------------------------------------ mesh helpers
def finish(name, bm, mats, bevel=None, segs=4, bevel_angle=30, smooth_angle=48):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me); bm.free()
    for m in mats:
        me.materials.append(M[m])
    ob = bpy.data.objects.new(name, me)
    COL.objects.link(ob)
    for p in me.polygons:
        p.use_smooth = True
    me.use_auto_smooth = True
    me.auto_smooth_angle = math.radians(smooth_angle)
    if bevel:
        md = ob.modifiers.new("Bevel", "BEVEL")
        md.width = bevel
        md.segments = segs
        md.profile = 0.5
        md.limit_method = "ANGLE"
        md.angle_limit = math.radians(bevel_angle)
        md.use_clamp_overlap = True
        md.harden_normals = True
    return ob

def slab(name, pts, thick, mat, plane="XZ", offset=0.0, bevel=0.01, segs=4, taper=None, loc=(0, 0, 0)):
    """Extrude a closed 2D profile into a solid. plane XZ extrudes along Y,
    YZ along X, XY along Z. `offset` = centre of the slab along the extrude axis."""
    def P(a, b, w):
        if plane == "XZ":
            s = taper(a, b) if taper else 1.0
            return (loc[0] + a, loc[1] + offset + w * s, loc[2] + b)
        if plane == "YZ":
            return (loc[0] + offset + w, loc[1] + a, loc[2] + b)
        return (loc[0] + a, loc[1] + b, loc[2] + offset + w)
    bm = bmesh.new()
    lo = [bm.verts.new(P(a, b, -thick / 2)) for a, b in pts]
    hi = [bm.verts.new(P(a, b, thick / 2)) for a, b in pts]
    bm.faces.new(lo[::-1]); bm.faces.new(hi)
    n = len(pts)
    for i in range(n):
        j = (i + 1) % n
        bm.faces.new([lo[i], lo[j], hi[j], hi[i]])
    return finish(name, bm, [mat], bevel, segs)

def lathe(name, prof, mats, seg=48, cy=0.0, cz=0.0, bevel=None, segs=3, mat_fn=None):
    """Revolve (x, r) profile around the X axis through (y=cy, z=cz)."""
    bm = bmesh.new()
    rings = []
    for x, r in prof:
        if r < 1e-7:
            rings.append([bm.verts.new((x, cy, cz))])
        else:
            rings.append([bm.verts.new((x, cy + r * math.cos(2 * math.pi * i / seg),
                                        cz + r * math.sin(2 * math.pi * i / seg))) for i in range(seg)])
    for A, B in zip(rings, rings[1:]):
        for i in range(seg):
            j = (i + 1) % seg
            if len(A) == 1 and len(B) == 1:
                continue
            if len(A) == 1:
                f = bm.faces.new([A[0], B[j], B[i]])
            elif len(B) == 1:
                f = bm.faces.new([A[i], A[j], B[0]])
            else:
                f = bm.faces.new([A[i], A[j], B[j], B[i]])
            if mat_fn:
                f.material_index = mat_fn(f)
    return finish(name, bm, mats, bevel, segs)

def rotated(ob, rx=0, ry=0, rz=0, loc=None):
    ob.rotation_euler = (math.radians(rx), math.radians(ry), math.radians(rz))
    if loc:
        ob.location = loc
    return ob

# ================================================================== THE GUN
# ---- barrel (steel tube with a flared muzzle band and a real bore) -------
BARREL_R = 0.030
barrel_prof = [
    (0.24, 0.0), (0.24, BARREL_R), (0.965, BARREL_R),
    (0.972, 0.036), (1.013, 0.036), (1.025, 0.031),
    (1.025, 0.018), (1.000, 0.017), (0.82, 0.017), (0.82, 0.0),
]
def bore_mat(f):
    c = f.calc_center_median()
    return 1 if math.hypot(c.y, c.z) < 0.0185 else 0
lathe("Barrel", barrel_prof, ["Gunmetal", "Bore"], seg=56, bevel=0.003, segs=2, mat_fn=bore_mat)

# collar where the barrel enters the receiver
lathe("BarrelCollar", [(0.285, 0.0), (0.285, 0.035), (0.29, 0.038), (0.33, 0.038), (0.338, 0.032), (0.338, 0.0)],
      ["Steel"], seg=56, bevel=0.003, segs=2)

# ---- ventilated rib (one profile: posts are notches in the bottom edge) ---
rib = [("M", 0.30, 0.050), ("L", 0.30, 0.036)]
x = 0.30
while x < 0.96:
    rib += [("L", x + 0.012, 0.036), ("L", x + 0.012, 0.024), ("L", x + 0.034, 0.024), ("L", x + 0.034, 0.036)]
    x += 0.062
rib += [("L", 0.98, 0.036), ("L", 0.98, 0.043), ("Q", (0.98, 0.050), (0.973, 0.050), 4)]
slab("VentRib", path(rib), 0.014, "Gunmetal", bevel=0.0025, segs=2)

# front bead
lathe("FrontBead", [(0.962, 0.0), *[(0.969 + 0.007 * math.sin(math.radians(a)), 0.007 * math.cos(math.radians(a)))
                                    for a in range(-90, 91, 15)], (0.976, 0.0)],
      ["Brass"], seg=24, cz=0.052)

# ---- magazine tube + brass end cap --------------------------------------
MAG_Z, MAG_R = -0.066, 0.024
lathe("MagTube", [(0.26, 0.0), (0.26, MAG_R), (0.92, MAG_R), (0.92, 0.0)], ["Gunmetal"], cz=MAG_Z, bevel=0.002, segs=2)
cap = [(0.915, 0.0), (0.915, 0.028), (0.942, 0.028)]
cap += [(0.942 + 0.016 * math.sin(math.radians(a)), 0.012 + 0.016 * math.cos(math.radians(a))) for a in range(15, 91, 15)]
cap += [(0.958, 0.0)]
lathe("MagCap", cap, ["Brass"], cz=MAG_Z, bevel=0.002, segs=2)

# ---- barrel band (one stadium ring hugging barrel + tube) ----------------
band = path([("A", 0.0, 0.0, 0.037, 0, 180, 16), ("A", 0.0, MAG_Z, 0.037, 180, 360, 16)])
slab("BarrelBand", band, 0.026, "Steel", plane="YZ", offset=0.885, bevel=0.004, segs=3)

# ---- forend (chunky wood, slides on the tube) ----------------------------
forend = path([
    ("M", 0.49, -0.028), ("L", 0.74, -0.028),
    ("Q", (0.775, -0.028), (0.775, -0.060), 8),
    ("Q", (0.775, -0.100), (0.735, -0.104), 8),
    ("Q", (0.62, -0.094), (0.51, -0.108), 10),
    ("Q", (0.465, -0.110), (0.465, -0.070), 8),
    ("Q", (0.465, -0.028), (0.49, -0.028), 8),
])
slab("Forend", forend, 0.086, "Wood", bevel=0.027, segs=6)

# ---- receiver (Auto-5 style "humpback") ----------------------------------
receiver = path([
    ("M", 0.020, -0.100),
    ("L", 0.300, -0.100),
    ("Q", (0.312, -0.100), (0.312, -0.085), 4),
    ("L", 0.312, 0.030),
    ("Q", (0.312, 0.046), (0.290, 0.046), 4),
    ("Q", (0.200, 0.046), (0.150, 0.066), 10),
    ("Q", (0.130, 0.074), (0.100, 0.074), 6),
    ("L", 0.040, 0.074),
    ("Q", (0.020, 0.074), (0.020, 0.054), 5),
])
slab("Receiver", receiver, 0.078, "Gunmetal", bevel=0.013, segs=5)

# loading port on the belly (dark recess) + carrier
slab("LoadingPort", rrect(0.13, -0.022, 0.29, 0.022, 0.012), 0.004, "Bore", plane="XY", offset=-0.1005, bevel=0.0015, segs=1)
slab("Carrier", rrect(0.15, -0.013, 0.27, 0.013, 0.008), 0.004, "Steel", plane="XY", offset=-0.1008, bevel=0.0015, segs=1)

# ejection port (right side) with bolt + charging handle
slab("EjectPort", rrect(0.150, -0.002, 0.262, 0.040, 0.010), 0.004, "Bore", offset=0.0385, bevel=0.0015, segs=1)
slab("Bolt", rrect(0.158, 0.004, 0.240, 0.034, 0.008), 0.004, "Steel", offset=0.0405, bevel=0.0015, segs=2)
knob = [(0.0, 0.0), (0.0, 0.0065), (0.030, 0.0065)]
knob += [(0.040 + 0.012 * math.sin(math.radians(a)), 0.012 * math.cos(math.radians(a))) for a in range(-60, 91, 15)]
knob += [(0.052, 0.0)]
rotated(lathe("ChargingHandle", knob, ["Steel"], seg=32), rz=90, loc=(0.222, 0.036, 0.019))

# lone-star medallion (left side): brass ring / team disc / brass star
MED = (0.090, 0.012)
slab("MedallionRing", circle(*MED, 0.036), 0.005, "Brass", offset=-0.0405, bevel=0.0018, segs=2)
slab("MedallionDisc", circle(*MED, 0.029), 0.005, "Team", offset=-0.0425, bevel=0.0015, segs=2)
star = []
for i in range(10):
    a = math.radians(90 + 36 * i)
    r = 0.024 if i % 2 == 0 else 0.0098
    star.append((MED[0] + r * math.cos(a), MED[1] + r * math.sin(a)))
slab("MedallionStar", star[::-1], 0.006, "Brass", offset=-0.0455, bevel=0.0018, segs=2)

# receiver pins (both sides)
pin = [(0.0, 0.0)] + [(0.004 * (1 - math.cos(math.radians(a))), 0.0075 * math.sin(math.radians(a)) if a < 90 else 0.0075)
                      for a in range(15, 91, 15)] + [(0.008, 0.0)]
pin = [(0.0, 0.0), (0.0, 0.0075)] + [(0.004 * math.sin(math.radians(a)), 0.0075 * math.cos(math.radians(a))) for a in range(15, 91, 15)]
for i, (px, pz) in enumerate([(0.050, -0.074), (0.280, -0.074), (0.280, 0.022)]):
    rotated(lathe(f"PinR{i}", pin, ["Brass"], seg=24), rz=90, loc=(px, 0.038, pz))
    rotated(lathe(f"PinL{i}", pin, ["Brass"], seg=24), rz=-90, loc=(px, -0.038, pz))

# ---- trigger guard + trigger ---------------------------------------------
guard = path([
    ("M", 0.205, -0.095),
    ("Q", (0.212, -0.172), (0.145, -0.172), 10),
    ("L", 0.070, -0.172),
    ("Q", (0.005, -0.172), (-0.045, -0.150), 10),
    ("L", -0.048, -0.130),
    ("Q", (0.005, -0.157), (0.070, -0.157), 10),
    ("L", 0.145, -0.157),
    ("Q", (0.196, -0.157), (0.190, -0.095), 10),
])
slab("TriggerGuard", guard, 0.024, "Gunmetal", bevel=0.0065, segs=4)
trigger = path([
    ("M", 0.128, -0.098),
    ("Q", (0.136, -0.130), (0.108, -0.150), 10),
    ("Q", (0.100, -0.153), (0.101, -0.146), 3),
    ("Q", (0.118, -0.128), (0.110, -0.098), 10),
])
slab("Trigger", trigger, 0.012, "Steel", bevel=0.003, segs=3)

# ---- stock with pistol grip ------------------------------------------------
stock = path([
    ("M", 0.034, 0.064),
    ("Q", (-0.05, 0.062), (-0.14, 0.030), 10),     # drop at the wrist
    ("Q", (-0.20, 0.012), (-0.30, 0.008), 8),      # comb
    ("L", -0.632, -0.002),                          # heel
    ("L", -0.660, -0.200),                          # toe
    ("Q", (-0.43, -0.150), (-0.26, -0.095), 14),   # belly
    ("Q", (-0.170, -0.068), (-0.150, -0.135), 12), # into the grip
    ("L", -0.168, -0.232),                          # raked grip, back edge
    ("Q", (-0.172, -0.262), (-0.140, -0.264), 8),
    ("L", -0.080, -0.258),
    ("Q", (-0.052, -0.255), (-0.060, -0.228), 8),
    ("Q", (-0.070, -0.150), (0.034, -0.100), 14),  # grip front up to the receiver
])
def smoothstep(e0, e1, v):
    t = min(max((v - e0) / (e1 - e0), 0.0), 1.0)
    return t * t * (3 - 2 * t)
def stock_taper(x, z):
    s = 1.0 + 0.16 * smoothstep(-0.25, -0.63, x)          # flare toward the butt
    if x > -0.22:
        s *= 1.0 - 0.10 * smoothstep(-0.10, -0.17, z)     # slimmer grip
    return s
slab("Stock", stock, 0.072, "Wood", bevel=0.023, segs=6, taper=stock_taper)

# rubber butt pad
pad = path([("M", -0.628, 0.012), ("L", -0.659, -0.214), ("L", -0.687, -0.212), ("L", -0.656, 0.012)])
slab("ButtPad", pad, 0.088, "Rubber", bevel=0.018, segs=5)

# brass grip cap
slab("GripCap", path([("M", -0.169, -0.244), ("Q", (-0.176, -0.276), (-0.140, -0.278), 8), ("L", -0.078, -0.272),
                      ("Q", (-0.046, -0.268), (-0.057, -0.238), 8)]), 0.060, "Brass", bevel=0.014, segs=4)

# ------------------------------------------------------------------ export
bpy.ops.object.select_all(action="SELECT")
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, "lone_star_repeater.blend"))
bpy.ops.export_scene.gltf(
    filepath=os.path.join(OUT, "lone_star_repeater.glb"),
    export_format="GLB", export_apply=True, export_yup=True,
    export_normals=True, export_materials="EXPORT",
)
tris = 0
dg = bpy.context.evaluated_depsgraph_get()
for ob in bpy.context.scene.objects:
    if ob.type == "MESH":
        me = ob.evaluated_get(dg).to_mesh()
        me.calc_loop_triangles(); tris += len(me.loop_triangles)
print(f"EXPORTED objects={len(bpy.context.scene.objects)} tris={tris}")
