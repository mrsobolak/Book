"""
ctf_curdworks v2: a symmetric Capture-the-Flag map on three levels. TF2 factory style with a Call of Duty
edge (sandbags, military crates, stranded trucks, barbed wire). Built procedurally at an Xbox One budget.

    blender -b --python-expr "import sys; sys.path.insert(0,'/home/user/Book/cod/armory')" --python build_map.py -- [out_dir] [--nobake]

Axes: +X toward BLU, -X toward RED, +Y = north, +Z up. Metres. Ground level is z = 0, the canal and sewers
are at z = -3, the battlements at z = 5, the upper floors at z = 5, the intel rooms at z = -3.
The RED half is built and mirrored through the origin for BLU with team materials swapped.
"""
import math, os, sys

sys.path.insert(0, "/home/user/Book/cod/armory")
import bpy, bmesh
from mathutils import Vector
import lib
from lib import path, rrect, circle, bm_prism, bm_lathe, bm_box, bm_rod, mk, cut, text

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in args if not a.startswith("--")), HERE)
BAKE = "--nobake" not in args
lib.reset()
V = Vector


def part(name, mat, bm, dens=0.8, **kw):
    ob = mk(name, bm, mat, **kw)
    lib.densify(ob, max_len=dens)
    ob["nodensify"] = True
    return ob


def box(name, mat, x0, x1, y0, y1, z0, z1, **kw):
    bm = bmesh.new(); bm_box(bm, min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z0, z1)
    return part(name, mat, bm, **kw)


def cbox(bm, x0, x1, y0, y1, z0, z1):
    bm_box(bm, min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1), z0, z1)


def ramp_x(name, mat, x0, x1, y0, y1, z0, z1, thick=0.3):
    """Slab rising from (x0, z0) to (x1, z1), spanning y0..y1."""
    pts = [(x0, z0 - thick), (x1, z1 - thick), (x1, z1), (x0, z0)]
    if (x1 - x0) < 0:
        pts = pts[::-1]
    bm = bmesh.new(); bm_prism(bm, pts, (y0 + y1) / 2, abs(y1 - y0), "XZ")
    return part(name, mat, bm)


def ramp_y(name, mat, y0, y1, x0, x1, z0, z1, thick=0.3):
    pts = [(y0, z0 - thick), (y1, z1 - thick), (y1, z1), (y0, z0)]
    if (y1 - y0) < 0:
        pts = pts[::-1]
    bm = bmesh.new(); bm_prism(bm, pts, (x0 + x1) / 2, abs(x1 - x0), "YZ")
    return part(name, mat, bm)


def lamp(name, x, y, z, w=0.9, d=0.3):
    box(name, "Glow", x - w / 2, x + w / 2, y - d / 2, y + d / 2, z - 0.08, z)
    box(name + "H", "Metal", x - w / 2 - 0.05, x + w / 2 + 0.05, y - d / 2 - 0.05, y + d / 2 + 0.05, z, z + 0.12)


# ================================================================== GROUND: one thick slab, everything below grade is cut out of it
ground = box("Ground", "Concrete", -54, 54, -30, 30, -7.0, 0.0)
GC = bmesh.new()                                   # ground cutters (canal, sewers, intel pits, stairwells)
cbox(GC, -7, 7, -32, 32, -3.0, 1.0)                # canal
box("CanalWater", "Water", -7, 7, -30, 30, -2.3, -2.2)
box("DirtN", "Dirt", -54, 54, 14, 30, 0.0, 0.05)
box("DirtS", "Dirt", -54, 54, -30, -14, 0.0, 0.05)
box("GrassNE", "Grass", 8, 22, 15, 26, 0.05, 0.10); box("GrassNW", "Grass", -22, -8, 15, 26, 0.05, 0.10)
box("GrassSE", "Grass", 8, 22, -26, -15, 0.05, 0.10); box("GrassSW", "Grass", -22, -8, -26, -15, 0.05, 0.10)
for y0, y1 in ((-30, -29.4), (29.4, 30)):
    box(f"WallLong{y0}", "Concrete", -54, 54, y0, y1, 0, 3.4, bev=0.05, segs=1)
for x0, x1 in ((-54, -53.4), (53.4, 54)):
    box(f"WallShort{x0}", "Concrete", x0, x1, -30, 30, 0, 3.4, bev=0.05, segs=1)
wire = bmesh.new()
for x in range(-52, 53, 4):
    for y in (-29.7, 29.7):
        bm_rod(wire, (x, y, 3.4), (x, y, 4.5), 0.05, seg=8)
for y in (-29.7, 29.7):
    for zz in (3.8, 4.2):
        bm_rod(wire, (-52, y, zz), (52, y, zz), 0.02, seg=6)
part("BarbedWire", "Metal", wire)


# ================================================================== ONE BASE (RED side, x < 0; sgn = -1 mirrors it for BLU)
def base(T, TD, sgn, tag):
    X = lambda x: sgn * x
    lo = lambda a, b: (min(X(a), X(b)), max(X(a), X(b)))
    # ---- the fort: one solid block, rooms and courtyard cut out of it
    bx0, bx1 = lo(-52, -22)
    fort = box(f"Fort{tag}", T, bx0, bx1, -14, 14, 0, 9.6)
    C = bmesh.new()
    cbox(C, *lo(-34, -24), -11, 11, 0.0, 30)                 # open courtyard
    cbox(C, *lo(-25, -21), -2.6, 2.6, 0.0, 4.2)              # gate through the front wall
    cbox(C, *lo(-24, -22.6), -11, 11, 5.0, 30)               # battlement walkway on the front wall
    cbox(C, *lo(-22.6, -22), -11, 11, 6.3, 30)               # above the parapet
    for y in range(-10, 11, 2):                              # crenellation notches
        cbox(C, *lo(-22.7, -21.9), y - 0.5, y + 0.5, 5.9, 30)
    cbox(C, *lo(-51.4, -34.6), -13.4, 13.4, 0.0, 4.4)        # ground floor
    cbox(C, *lo(-51.4, -34.6), -13.4, 13.4, 4.9, 9.1)        # upper floor
    cbox(C, *lo(-35.5, -33.5), -7.5, -4.5, 0.0, 3.2)         # ground doors from the courtyard (south, north)
    cbox(C, *lo(-35.5, -33.5), 4.5, 7.5, 0.0, 3.2)
    cbox(C, *lo(-35.5, -33.5), 7.6, 10.4, 5.0, 8.0)          # upper door from the north ledge
    for y in (-5, 0, 5):                                     # sniper windows over the courtyard
        cbox(C, *lo(-35.5, -33.5), y - 0.9, y + 0.9, 6.2, 8.0)
    for x in (-46, -40):                                     # side windows, both floors
        for yy in (-14.5, 13.5):
            cbox(C, *lo(x - 0.9, x + 0.9), yy - 0.5, yy + 1.5, 6.2, 8.0)
            cbox(C, *lo(x - 0.9, x + 0.9), yy - 0.5, yy + 1.5, 1.8, 3.4)
    cbox(C, *lo(-40, -37), -13.5, -10.5, 4.4, 4.9)           # stairwell hole between floors (south side)
    cbox(C, *lo(-38.6, -36.4), -6.5, -1.5, -0.3, 0.6)        # top of the spiral down to the intel
    cbox(C, *lo(-44, -40), 11.5, 14.5, 0.0, 3.2)             # sewer-side back door (north) onto the field
    cut(fort, C)
    box(f"Slab{tag}", "Concrete", *lo(-51.4, -34.6), -13.4, 13.4, 4.4, 4.9)          # first floor slab
    slab = bpy.data.objects[f"Slab{tag}"]
    S = bmesh.new(); cbox(S, *lo(-40, -37), -13.5, -10.5, 4.0, 5.2); cut(slab, S)
    ramp_x(f"Stair{tag}", "Concrete", X(-37), X(-46), -13.0, -10.6, 0.0, 4.4)       # inside stair (a ramp, cheap)
    # battlement access: ramp on the south side of the courtyard, flat ledge on the north side
    ramp_x(f"BattRamp{tag}", "Concrete", X(-34), X(-24), -11, -8.6, 0.0, 5.0)
    box(f"NorthLedge{tag}", "Concrete", *lo(-34.6, -24), 8.6, 11, 4.7, 5.0)
    for i in range(10):                                                              # ledge railing posts
        box(f"LedgePost{tag}{i}", "Metal", *lo(-33.6 + i, -33.4 + i), 8.6, 8.8, 5.0, 6.0)
    box(f"LedgeRail{tag}", "Metal", *lo(-34.6, -24), 8.55, 8.85, 6.0, 6.15)
    # crenellation caps and the sign over the gate
    box(f"GateLintel{tag}", TD, *lo(-25.2, -21.8), -3.2, 3.2, 4.2, 5.0)
    text("RED" if tag == "R" else "BLU", 3.2, X(-22) + (-0.05 if sgn > 0 else 0.05), 7.4, 0, f"GateSign{tag}", mat="Cross")
    bpy.data.objects[f"GateSign{tag}"].rotation_euler = (math.radians(90), 0, math.radians(90 if sgn > 0 else -90))
    text("INTEL", 1.4, X(-34.5) + (-0.05 if sgn > 0 else 0.05), 2.4, -2.5, f"IntelArrow{tag}", mat="Cross")
    bpy.data.objects[f"IntelArrow{tag}"].rotation_euler = (math.radians(90), 0, math.radians(90 if sgn > 0 else -90))
    box(f"Stripe{tag}", TD, bx0 - 0.05, bx1 + 0.05, -14.05, 14.05, 4.3, 4.7)
    box(f"Chimney{tag}", TD, *lo(-48, -46.4), 6, 7.6, 9.6, 13.0)
    # roof over the building only (the courtyard is open sky)
    box(f"Roof{tag}", "Roof", *lo(-52.2, -34.4), -14.2, 14.2, 9.6, 10.0)
    # ---- the spiral: ramp down from the ground floor into the intel room at z = -3
    cbox(GC, *lo(-51.4, -38), -7, 7, -3.0, 0.5)             # intel room
    cbox(GC, *lo(-45, -36.4), -6.5, -1.5, -3.4, 0.5)         # descent trench
    ramp_x(f"IntelRamp{tag}", "Concrete", X(-36.4), X(-44.4), -6.3, -1.7, 0.0, -3.0)
    box(f"IntelPad{tag}", "Concrete", *lo(-48.5, -45.5), 1.0, 4.0, -3.0, -2.5, bev=0.05, segs=1)
    box(f"Intel{tag}", TD, *lo(-47.45, -46.55), 2.2, 2.85, -2.5, -1.9, bev=0.04, segs=2)
    box(f"IntelHandle{tag}", "Metal", *lo(-47.2, -46.8), 2.5, 2.56, -1.9, -1.75)
    box(f"IntelGlow{tag}", "Glow", *lo(-47.5, -46.5), 2.15, 2.9, -2.5, -2.47)
    lamp(f"IntelLamp{tag}", X(-44), 0, -0.35, w=2.2); lamp(f"IntelLamp2{tag}", X(-48), -3, -0.35)
    for i in range(6):                                                               # ladder up the pit wall
        box(f"Rung{tag}{i}", "Metal", *lo(-38.35, -38.05), 3.5, 4.3, -2.7 + 0.5 * i, -2.6 + 0.5 * i)
    for i in range(3):                                                               # pipes along the intel room wall
        box(f"IntelPipe{tag}{i}", "Metal", *lo(-51.2, -38.2), 6.5 - 0.35 * i, 6.7 - 0.35 * i, -0.9 - 0.3 * i, -0.7 - 0.3 * i)
    # ---- sewer: from the canal wall under the field into the intel room (north side)
    cbox(GC, *lo(-46, -6), 8.5, 11.5, -3.0, -0.7)
    cbox(GC, *lo(-46, -43), 5.5, 11.5, -3.0, -0.7)
    box(f"SewerWater{tag}", "Water", *lo(-46, -7.2), 8.5, 11.5, -2.4, -2.35)
    grate = bmesh.new()
    for y in (9.0, 9.5, 10.0, 10.5, 11.0):
        bm_rod(grate, (X(-7.6), y, -3.0), (X(-7.6), y, -0.7), 0.05, seg=8)
    part(f"SewerGrate{tag}", "Metal", grate)
    for i in range(4):
        lamp(f"SewerLamp{tag}{i}", X(-14 - 8 * i), 10, -0.75, w=0.6, d=0.6)
    # ---- spawn: upper floor back; lockers, two resupply cabinets, lamps
    box(f"Lockers{tag}", "Metal", *lo(-51.3, -50.7), -12, 0, 4.9, 7.4)
    for i in range(12):
        box(f"LockerDoor{tag}{i}", TD, *lo(-50.72, -50.6), -11.8 + i, -11.1 + i, 5.0, 7.3)
    for i, y in enumerate((3, 8)):
        box(f"Resupply{tag}{i}", "Metal", *lo(-51.3, -50.1), y - 0.7, y + 0.7, 4.9, 7.5, bev=0.03, segs=1)
        box(f"ResupplyX{tag}{i}", "Cross", *lo(-50.12, -50.05), y - 0.35, y + 0.35, 5.9, 6.5)
        box(f"ResupplyY{tag}{i}", "Cross", *lo(-50.12, -50.05), y - 0.12, y + 0.12, 5.6, 6.8)
    for y in (-8, 0, 8):
        lamp(f"UpperLamp{tag}{y}", X(-43), y, 9.05, w=1.8); lamp(f"LowerLamp{tag}{y}", X(-43), y, 4.35, w=1.8)
    # ---- ground floor clutter: crates, barrels, a workbench, pallets of cheese
    for i, (x, y, w) in enumerate(((-49, -11, 1.4), (-47.4, -11.5, 1.1), (-49, 11, 1.4), (-45, 12, 1.0), (-37, 12, 1.2))):
        box(f"InCrate{tag}{i}", "Plank", *lo(x - w / 2, x + w / 2), y - w / 2, y + w / 2, 0, w * 0.8, bev=0.04, segs=1)
    box(f"Bench{tag}", "Plank", *lo(-51, -47), -6, -4.8, 0.9, 1.05); box(f"BenchLegs{tag}", "Metal", *lo(-50.8, -47.2), -5.9, -4.9, 0, 0.9)
    for i in range(3):
        wheel = bmesh.new()
        bm_lathe(wheel, [(0.1 + 0.3 * i, 0), (0.1 + 0.3 * i, 0.55), (0.38 + 0.3 * i, 0.55), (0.38 + 0.3 * i, 0)], 20, "Z", (X(-49.5), 3, 0))
        part(f"InWheel{tag}{i}", "Cheese", wheel)
    # ---- courtyard cover + signs + lamps
    for j, (cx, cy) in enumerate(((-30, -4), (-28, 5))):
        for i in range(2):
            for k in range(3 - i):
                sb = bmesh.new()
                vs = bm_lathe(sb, [(-0.5, 0), (-0.5, 0.30), (-0.42, 0.34), (0.42, 0.34), (0.5, 0.30), (0.5, 0)], 14, "X", (0, 0, 0))
                for v in vs:
                    v.co = V((X(cx) + v.co.x, cy - 0.9 + k * 0.9 + i * 0.45 + v.co.y * 1.15, 0.18 + 0.34 * i + v.co.z * 0.55))
                part(f"CSandbag{tag}{j}{i}{k}", "Sand", sb, smooth=50)
    for i, (x, y) in enumerate(((-32, -9.5), (-27, 9.5), (-26, -9.8))):
        br = bmesh.new()
        bm_lathe(br, [(0, 0), (0, 0.45), (0.1, 0.48), (1.15, 0.48), (1.25, 0.45), (1.25, 0)], 18, "Z", (X(x), y, 0))
        part(f"CBarrel{tag}{i}", TD if i != 1 else "Metal", br)
    for y in (-6, 6):
        lamp(f"CourtLamp{tag}{y}", X(-34.7), y, 4.0, w=0.4, d=0.4)
    # ---- outside: silos, pipes, truck, floodlights, health/ammo, catwalk ramps up to the battlement wall ends
    for i, y in enumerate((-19, -24)):
        sil = bmesh.new()
        bm_lathe(sil, [(0, 0), (0, 2.6), (7.5, 2.6), (8.2, 2.0), (8.6, 0.9), (8.6, 0)], 32, "Z", (X(-44), y, 0))
        part(f"Silo{tag}{i}", "Metal", sil)
        for zz in (2.5, 5.0):
            band = bmesh.new()
            bm_lathe(band, [(zz - 0.15, 2.62), (zz - 0.15, 2.72), (zz + 0.15, 2.72), (zz + 0.15, 2.62)], 32, "Z", (X(-44), y, 0), closed=True)
            part(f"SiloBand{tag}{i}{zz}", TD, band)
    pipe = bmesh.new()
    bm_rod(pipe, (X(-44), -19, 6.5), (X(-44), -24, 6.5), 0.35, seg=12)
    bm_rod(pipe, (X(-44), -21.5, 6.5), (X(-44), -14.2, 6.5), 0.3, seg=12)
    part(f"Pipes{tag}", "Metal", pipe)
    tx, ty = X(-16), 21
    box(f"TruckBed{tag}", "Tarp", tx - 3.2, tx + 1.2, ty - 1.3, ty + 1.3, 0.9, 1.5, bev=0.05, segs=1)
    box(f"TruckCab{tag}", TD, tx + 1.2 * sgn - (1.0 if sgn < 0 else 0), tx + 3.2 * sgn - (1.0 if sgn < 0 else 0) + (1.0 if sgn < 0 else 0), ty - 1.2, ty + 1.2, 0.9, 2.9, bev=0.08, segs=2)
    box(f"TruckCanopy{tag}", "Tarp", tx - 3.1, tx + 1.1, ty - 1.25, ty + 1.25, 1.5, 3.1, bev=0.15, segs=3)
    wh = bmesh.new()
    for wx in (tx - 2.2, tx + 2.2):
        for wy in (ty - 1.35, ty + 1.35):
            bm_lathe(wh, [(-0.2, 0), (-0.2, 0.55), (0.2, 0.55), (0.2, 0)], 16, "Y", (wx, wy, 0.55))
    part(f"TruckWheels{tag}", "Rubber", wh)
    for i, (cx, cy) in enumerate(((-30, -26), (-30, 26))):
        pole = bmesh.new()
        bm_rod(pole, (X(cx), cy, 0), (X(cx), cy, 9), 0.18, seg=10)
        bm_box(pole, X(cx) - 0.6, X(cx) + 0.6, cy - 0.3, cy + 0.3, 8.6, 9.2)
        part(f"Flood{tag}{i}", "Metal", pole)
        box(f"FloodGlow{tag}{i}", "Glow", X(cx) - 0.55, X(cx) + 0.55, cy - 0.34 if cy < 0 else cy + 0.3, cy - 0.3 if cy < 0 else cy + 0.34, 8.65, 9.15)
    for i, (cx, cy) in enumerate(((-18, -12), (-18, 12), (-46, -2), (-30, 0))):
        z0 = -3.0 if i == 2 else 0.0
        box(f"Health{tag}{i}", "Cross", X(cx) - 0.35, X(cx) + 0.35, cy - 0.35, cy + 0.35, z0, z0 + 0.35, bev=0.04, segs=2)
        box(f"HealthX{tag}{i}", "Red", X(cx) - 0.25, X(cx) + 0.25, cy - 0.08, cy + 0.08, z0 + 0.35, z0 + 0.38)
        box(f"HealthY{tag}{i}", "Red", X(cx) - 0.08, X(cx) + 0.08, cy - 0.25, cy + 0.25, z0 + 0.35, z0 + 0.38)
        box(f"Ammo{tag}{i}", "Tarp", X(cx) - 0.4, X(cx) + 0.4, cy + 1.2, cy + 1.8, z0, z0 + 0.4, bev=0.03, segs=1)
    # outside cover in front of the gate
    for i, (x, y, w) in enumerate(((-16, -5, 1.6), (-15, -6.6, 1.2), (-17, 4, 1.6), (-14, 6, 1.0))):
        box(f"OutCrate{tag}{i}", "Tarp", *lo(x - w / 2, x + w / 2), y - w / 2, y + w / 2, 0, w * 0.8, bev=0.04, segs=1)
        box(f"OutBand{tag}{i}", "Metal", *lo(x - w / 2 - 0.02, x + w / 2 + 0.02), y - 0.08, y + 0.08, 0, w * 0.8 + 0.02)
    # ---- north catwalk: raised plank walkway from the base's north door out toward mid
    box(f"Catwalk{tag}", "Plank", *lo(-40, -12), 16.8, 19.2, 3.3, 3.6)
    ramp_x(f"CatRampIn{tag}", "Plank", X(-40), X(-46), 16.8, 19.2, 3.3, 0.0)
    ramp_x(f"CatRampOut{tag}", "Plank", X(-12), X(-6), 16.8, 19.2, 3.3, 0.0)
    for i in range(8):
        for y in (16.7, 19.3):
            box(f"CatPost{tag}{i}{y}", "Plank", *lo(-40 + 4 * i - 0.15, -40 + 4 * i + 0.15), y - 0.15, y + 0.15, 0, 4.6)
    for y in (16.7, 19.3):
        box(f"CatRail{tag}{y}", "Plank", *lo(-40, -12), y - 0.08, y + 0.08, 4.5, 4.65)
    # canal ramps: from the field down to the water level beside the sewer mouth
    ramp_x(f"CanalRamp{tag}", "Concrete", X(-13), X(-7.2), 2.5, 7.5, 0.0, -3.0)


base("Red", "RedDark", 1, "R")
base("Blu", "BluDark", -1, "B")
cut(ground, GC)

# ================================================================== MID: covered bridge, canal, water tower, shed, conveyor yard
box("BridgeFloor", "Plank", -8, 8, -4, 4, 0.0, 0.3)
for y0, y1 in ((-4.4, -4.0), (4.0, 4.4)):
    w = box(f"BridgeWall{y0}", "Plank", -8, 8, y0, y1, 0.3, 3.0)
    C = bmesh.new()
    for x in (-5, -2, 1, 4):
        cbox(C, x, x + 1.2, y0 - 1, y1 + 1, 1.5, 2.4)
    cut(w, C)
roof = bmesh.new()
bm_prism(roof, [(-5.0, 3.0), (5.0, 3.0), (0, 5.2)], 0, 17.0, "YZ")
part("BridgeRoof", "Roof", roof)
roof_in = bmesh.new(); bm_prism(roof_in, [(-4.6, 2.9), (4.6, 2.9), (0, 4.9)], 0, 16.6, "YZ")
cut(bpy.data.objects["BridgeRoof"], roof_in)
for x in (-7.5, -3.75, 0, 3.75, 7.5):
    beam = bmesh.new(); bm_prism(beam, [(-4.6, 2.9), (4.6, 2.9), (0, 4.85)], x, 0.25, "YZ")
    inner = bmesh.new(); bm_prism(inner, [(-4.2, 2.9), (4.2, 2.9), (0, 4.6)], x, 0.5, "YZ")
    b = part(f"Beam{x}", "Plank", beam); cut(b, inner)
for x in (-7.8, -4, 0, 4, 7.8):
    for y in (-4.2, 4.2):
        box(f"BridgePier{x}{y}", "Concrete", x - 0.35, x + 0.35, y - 0.35, y + 0.35, -3.0, 0.0)
box("CanalWalkN", "Concrete", -7, 7, 7.5, 11.5, -3.0, -2.6); box("CanalWalkS", "Concrete", -7, 7, -11.5, -7.5, -3.0, -2.6)
for i, (x, y) in enumerate(((-4, -9), (3, 9), (5, -9.5))):
    box(f"CanalCrate{i}", "Plank", x - 0.7, x + 0.7, y - 0.7, y + 0.7, -3.0, -1.8, bev=0.04, segs=1)
tower = bmesh.new()
for lx, ly in ((-1, -1), (1, -1), (1, 1), (-1, 1)):
    bm_rod(tower, (lx * 2.6, 22 + ly * 2.6, 0), (lx * 1.9, 22 + ly * 1.9, 11), 0.18, seg=10)
bm_lathe(tower, [(11, 0), (11, 2.4), (11.4, 3.0), (15.5, 3.0), (16.4, 1.6), (16.4, 0)], 32, "Z", (0, 22, 0))
part("WaterTower", "Metal", tower)
box("TowerBand", "Cheese", -3.05, 3.05, 18.95, 25.05, 12.6, 13.6)
text("CURDWORKS", 1.6, 0, 13.1, 18.9, "TowerSign", mat="Mouth")
shed = box("MidShed", "Concrete", -6, 6, -21, -15, 0, 3.8, bev=0.05, segs=1)
C = bmesh.new(); cbox(C, -5.6, 5.6, -20.6, -15.4, 0.3, 3.5); cbox(C, -1.2, 1.2, -22, -14, 0, 2.8); cbox(C, -7, 7, -18.5, -17.5, 1.5, 2.5); cut(shed, C)
box("ShedRoof", "Roof", -6.3, 6.3, -21.3, -14.7, 3.8, 4.1)
lamp("ShedLamp", 0, -18, 3.45, w=1.4)
conv = bmesh.new()
bm_box(conv, -10, 10, 13.5, 14.7, 0.9, 1.1)
for x in range(-10, 11, 2):
    bm_rod(conv, (x, 13.6, 0), (x, 13.6, 0.9), 0.06, seg=8); bm_rod(conv, (x, 14.6, 0), (x, 14.6, 0.9), 0.06, seg=8)
part("Conveyor", "Metal", conv)
belt = bmesh.new(); bm_box(belt, -10, 10, 13.6, 14.6, 1.1, 1.18); part("ConveyorBelt", "Rubber", belt)
wheels = bmesh.new()
for x in (-8, -3, 2, 7):
    bm_lathe(wheels, [(1.18, 0), (1.18, 0.4), (1.5, 0.4), (1.5, 0)], 20, "Z", (x, 14.1, 0))
part("BeltCheese", "Cheese", wheels)
for i, (x, y) in enumerate(((-11, 23), (11, 23), (0, -25), (-12, -25), (12, -25))):
    box(f"MidCrate{i}", "Tarp", x - 0.8, x + 0.8, y - 0.8, y + 0.8, 0, 1.3, bev=0.04, segs=1)
    box(f"MidBand{i}", "Metal", x - 0.82, x + 0.82, y - 0.08, y + 0.08, 0, 1.32)
for sgn, mat in ((1, "Red"), (-1, "Blu")):                                                # route arrows on the ground
    for x in range(9, 20, 5):
        arr = bmesh.new()
        bm_prism(arr, [(sgn * (x - 1.2), -0.5), (sgn * x, 0), (sgn * (x - 1.2), 0.5)], 0.06, 0.03, plane="XY")
        part(f"Arrow{mat}{x}", mat, arr)

lib.finalize(os.path.join(OUT, "curdworks.glb"), bake=BAKE, ao_distance=1.2, samples=24)
