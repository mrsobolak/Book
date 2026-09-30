"""
ctf_curdworks: a symmetric Capture-the-Flag map. TF2 factory style with a Call of Duty edge
(sandbags, military crates, a stranded truck, barbed wire). Built procedurally for a low budget.

    blender -b --python-expr "import sys; sys.path.insert(0,'/home/user/Book/cod/armory')" --python build_map.py -- [out_dir] [--nobake]

Axes: +X toward BLU, -X toward RED, +Y = map "north" (the far side), +Z up. Metres. The RED half is built,
then mirrored through the origin (180 degrees about Z) for BLU with team materials swapped.
"""
import json, math, os, sys

sys.path.insert(0, "/home/user/Book/cod/armory")
import bpy, bmesh
from mathutils import Vector, Matrix
import lib
from lib import path, rrect, circle, bm_prism, bm_lathe, bm_box, bm_rod, bm_tube, mk, cut, prism, lathe, rod, text

HERE = os.path.dirname(os.path.abspath(__file__))
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
OUT = next((a for a in args if not a.startswith("--")), HERE)
BAKE = "--nobake" not in args
lib.reset()
V = Vector
SWAP = {"Red": "Blu", "Blu": "Red", "RedDark": "BluDark", "BluDark": "RedDark"}
PARTS = []          # (name, bmesh-builder, material, kwargs) collected per half


def part(name, mat, bm, **kw):
    ob = mk(name, bm, mat, **kw)
    lib.densify(ob, max_len=0.6)
    ob["nodensify"] = True
    return ob


def box(name, mat, x0, x1, y0, y1, z0, z1, **kw):
    bm = bmesh.new(); bm_box(bm, x0, x1, y0, y1, z0, z1)
    return part(name, mat, bm, **kw)


# ================================================================== GROUND (shared)
box("Ground", "Dirt", -52, 52, -28, 28, -0.6, 0.0)
box("GrassN", "Grass", -30, 30, 14, 26, -0.02, 0.02)
box("GrassS", "Grass", -30, 30, -26, -14, -0.02, 0.02)
riv = box("Riverbed", "Dirt", -3.5, 3.5, -28, 28, -2.6, -2.5)
box("Water", "Water", -3.0, 3.0, -28, 28, -2.2, -2.1)
gnd = bpy.data.objects["Ground"]
bm = bmesh.new(); bm_box(bm, -3.5, 3.5, -30, 30, -3.0, 0.5); cut(gnd, bm)           # dry canal through the middle
# perimeter wall + barbed wire posts
for y0, y1 in ((-28, -27.4), (27.4, 28)):
    box(f"WallLong{y0}", "Concrete", -52, 52, y0, y1, 0, 3.2, bev=0.05, segs=1)
for x0, x1 in ((-52, -51.4), (51.4, 52)):
    box(f"WallShort{x0}", "Concrete", x0, x1, -28, 28, 0, 3.2, bev=0.05, segs=1)
wire = bmesh.new()
for x in range(-50, 51, 4):
    for y in (-27.7, 27.7):
        bm_rod(wire, (x, y, 3.2), (x, y, 4.2), 0.05, seg=8)
for y in (-27.7, 27.7):
    for zz in (3.6, 4.0):
        bm_rod(wire, (-50, y, zz), (50, y, zz), 0.02, seg=6)
part("BarbedWire", "Metal", wire)

# ================================================================== ONE HALF (RED side, x < 0)
def half(T, TD, sgn, tag):
    def X(x):  # mirror helper for positions along X
        return sgn * x
    def Y(y):
        return sgn * y
    # ---- main base building: 22 x 18 footprint, two floors, open front toward mid
    bx0, bx1, by0, by1 = X(-48), X(-26), -9, 9
    lo, hi = min(bx0, bx1), max(bx0, bx1)
    b = box(f"Base{tag}", T, lo, hi, by0, by1, 0, 8.5, bev=0.08, segs=1)
    c = bmesh.new()
    bm_box(c, lo + 0.4, hi - 0.4, by0 + 0.4, by1 - 0.4, 0.4, 4.2)                     # ground floor interior
    bm_box(c, lo + 0.4, hi - 0.4, by0 + 0.4, by1 - 0.4, 4.6, 8.1)                     # first floor interior
    bm_box(c, X(-27) - 1, X(-27) + 1, -3.0, 3.0, 0, 3.8)                              # big front door
    bm_box(c, X(-37) - 1.4, X(-37) + 1.4, by0 - 1, by0 + 1, 0, 3.0)                   # south side door
    bm_box(c, X(-37) - 1.4, X(-37) + 1.4, by1 - 1, by1 + 1, 0, 3.0)                   # north side door
    bm_box(c, X(-27) - 1, X(-27) + 1, -6.0, 6.0, 5.2, 7.4)                            # balcony opening (sniper deck)
    for y in (-6, -2, 2, 6):                                                          # windows, both long sides
        for yy in (by0, by1):
            bm_box(c, X(-42) - 1, X(-42) + 1, yy - 1, yy + 1, 5.4, 7.2)
            bm_box(c, X(-32) - 1, X(-32) + 1, yy - 1, yy + 1, 5.4, 7.2)
    bm_box(c, X(-33) - 2, X(-33) + 2, -1.5, 1.5, 4.0, 4.8)                            # stair hole in the first floor
    cut(b, c)
    box(f"Floor1{tag}", "Concrete", lo + 0.4, hi - 0.4, by0 + 0.4, by1 - 0.4, 4.2, 4.6)
    f1 = bpy.data.objects[f"Floor1{tag}"]
    c = bmesh.new(); bm_box(c, X(-33) - 2, X(-33) + 2, -1.5, 1.5, 4.0, 4.8); cut(f1, c)
    # stairs up to the sniper deck
    for i in range(10):
        box(f"Step{tag}{i}", "Concrete", X(-35 + 0.4 * i) - 0.2, X(-35 + 0.4 * i) + 0.2, -1.4, 1.4, 0, 0.42 * (i + 1))
    # roof trim, chimney, sign
    box(f"RoofTrim{tag}", TD, lo - 0.2, hi + 0.2, by0 - 0.2, by1 + 0.2, 8.5, 9.0, bev=0.05, segs=1)
    box(f"Chimney{tag}", TD, X(-44) - 0.8, X(-44) + 0.8, 4, 5.6, 8.5, 11.5)
    text("RED" if tag == "R" else "BLU", 2.6, X(-37), 6.4, (by0 - 0.05) if True else 0, f"SignS{tag}", mat="Cross")
    text("RED" if tag == "R" else "BLU", 2.6, X(-37), 6.4, by1 + 0.05, f"SignN{tag}", mat="Cross")
    # team stripe around the building
    box(f"Stripe{tag}", TD, lo - 0.05, hi + 0.05, by0 - 0.05, by1 + 0.05, 3.9, 4.3)
    # ---- intel room at the back: raised pedestal + briefcase + spotlight glow
    box(f"IntelPad{tag}", "Concrete", X(-46) - 2, X(-46) + 2, -2, 2, 0.4, 0.9, bev=0.05, segs=1)
    box(f"Intel{tag}", TD, X(-46) - 0.45, X(-46) + 0.45, -0.32, 0.32, 0.9, 1.5, bev=0.04, segs=2)
    box(f"IntelHandle{tag}", "Metal", X(-46) - 0.18, X(-46) + 0.18, -0.03, 0.03, 1.5, 1.65)
    box(f"IntelGlow{tag}", "Glow", X(-46) - 0.5, X(-46) + 0.5, -0.36, 0.36, 0.905, 0.93)
    text("INTEL", 1.0, X(-46), 2.2, by0 + 0.45, f"IntelSign{tag}", mat="Cross")
    # ---- spawn / resupply room: a locker wall, a resupply cabinet, a door with a sign
    box(f"Lockers{tag}", "Metal", X(-47.4), X(-46.8), 3, 8.4, 0.4, 2.6)
    for i in range(6):
        box(f"LockerDoor{tag}{i}", TD, X(-46.9) - 0.02, X(-46.75) + 0.02, 3.2 + i * 0.85, 3.9 + i * 0.85, 0.5, 2.5)
    box(f"Resupply{tag}", "Metal", X(-46) - 0.6, X(-46) + 0.6, 7.2, 8.3, 0.4, 2.8, bev=0.03, segs=1)
    box(f"ResupplyCross{tag}", "Cross", X(-46) - 0.3, X(-46) + 0.3, 7.1, 7.2, 1.3, 1.9)
    box(f"ResupplyCross2{tag}", "Cross", X(-46) - 0.1, X(-46) + 0.1, 7.1, 7.2, 1.0, 2.2)
    # ---- cheese silos (the factory) beside the base
    for i, y in enumerate((-16, -21)):
        sil = bmesh.new()
        bm_lathe(sil, [(0, 0), (0, 2.6), (7.5, 2.6), (8.2, 2.0), (8.6, 0.9), (8.6, 0)], 32, "Z", (X(-40), y, 0))
        part(f"Silo{tag}{i}", "Metal", sil)
        for zz in (2.5, 5.0):
            band = bmesh.new()
            bm_lathe(band, [(zz - 0.15, 2.62), (zz - 0.15, 2.72), (zz + 0.15, 2.72), (zz + 0.15, 2.62)], 32, "Z", (X(-40), y, 0), closed=True)
            part(f"SiloBand{tag}{i}{zz}", TD, band)
    pipe = bmesh.new()
    bm_rod(pipe, (X(-40), -16, 6.5), (X(-40), -21, 6.5), 0.35, seg=12)
    bm_rod(pipe, (X(-40), -18.5, 6.5), (X(-36), -9.2, 6.5), 0.3, seg=12)
    part(f"Pipes{tag}", "Metal", pipe)
    # stacked cheese wheels on a pallet by the silos
    box(f"Pallet{tag}", "Plank", X(-33) - 0.8, X(-33) + 0.8, -18.8, -17.2, 0, 0.15)
    wheels = bmesh.new()
    for k in range(4):
        bm_lathe(wheels, [(0.15 + 0.32 * k, 0), (0.15 + 0.32 * k, 0.62), (0.47 + 0.32 * k, 0.62), (0.47 + 0.32 * k, 0)], 24, "Z", (X(-33), -18, 0))
    part(f"CheeseWheels{tag}", "Cheese", wheels)
    # ---- forward courtyard cover: sandbag nest, military crates, barrels, a stranded truck
    for j, (cx, cy) in enumerate(((X(-18), -5), (X(-18), 5), (X(-12), 0))):
        for i in range(3):
            for k in range(3 - i):
                sb = bmesh.new()
                cz = 0.18 + 0.34 * i
                vs = bm_lathe(sb, [(-0.5, 0), (-0.5, 0.30), (-0.42, 0.34), (0.42, 0.34), (0.5, 0.30), (0.5, 0)], 14, "X",
                              (0, 0, 0))
                for v in vs:                                                                  # squash into a bag
                    v.co = V((cx + v.co.x, cy - 0.9 + k * 0.9 + i * 0.45 + v.co.y * 1.15, cz + v.co.z * 0.55))
                part(f"Sandbag{tag}{j}{i}{k}", "Sand", sb, smooth=50)
    for i, (cx, cy, w) in enumerate(((X(-22), -12, 1.6), (X(-21), -13.5, 1.2), (X(-20), 12, 1.6), (X(-23), 13, 1.0))):
        box(f"Crate{tag}{i}", "Tarp", cx - w / 2, cx + w / 2, cy - w / 2, cy + w / 2, 0, w * 0.8, bev=0.04, segs=1)
        box(f"CrateBand{tag}{i}", "Metal", cx - w / 2 - 0.02, cx + w / 2 + 0.02, cy - 0.08, cy + 0.08, 0, w * 0.8 + 0.02)
    for i, (cx, cy) in enumerate(((X(-25), -2), (X(-25), -3.2), (X(-24.4), -2.6))):
        br = bmesh.new()
        bm_lathe(br, [(0, 0), (0, 0.45), (0.1, 0.48), (1.15, 0.48), (1.25, 0.45), (1.25, 0)], 20, "Z", (cx, cy, 0))
        part(f"Barrel{tag}{i}", TD if i != 1 else "Metal", br)
    tx, ty = X(-16), 18
    box(f"TruckBed{tag}", "Tarp", tx - 3.2, tx + 1.2, ty - 1.3, ty + 1.3, 0.9, 1.5, bev=0.05, segs=1)
    box(f"TruckCab{tag}", TD, tx + 1.2, tx + 3.2, ty - 1.2, ty + 1.2, 0.9, 2.9, bev=0.08, segs=2)
    box(f"TruckCanopy{tag}", "Tarp", tx - 3.1, tx + 1.1, ty - 1.25, ty + 1.25, 1.5, 3.1, bev=0.15, segs=3)
    box(f"TruckGlass{tag}", "Glass", tx + 2.6, tx + 3.25, ty - 1.0, ty + 1.0, 1.9, 2.7)
    wh = bmesh.new()
    for wx in (tx - 2.2, tx + 2.2):
        for wy in (ty - 1.35, ty + 1.35):
            bm_lathe(wh, [(-0.2, 0), (-0.2, 0.55), (0.2, 0.55), (0.2, 0)], 16, "Y", (wx, wy, 0.55))
    part(f"TruckWheels{tag}", "Rubber", wh)
    # ---- pickups: health kit + ammo box on the side routes
    for i, (cx, cy) in enumerate(((X(-30), -12), (X(-30), 12))):
        box(f"HealthKit{tag}{i}", "Cross", cx - 0.35, cx + 0.35, cy - 0.35, cy + 0.35, 0, 0.35, bev=0.04, segs=2)
        box(f"HealthCross{tag}{i}", "Red", cx - 0.25, cx + 0.25, cy - 0.08, cy + 0.08, 0.35, 0.38)
        box(f"HealthCross2{tag}{i}", "Red", cx - 0.08, cx + 0.08, cy - 0.25, cy + 0.25, 0.35, 0.38)
        box(f"AmmoBox{tag}{i}", "Tarp", cx - 0.4, cx + 0.4, cy + 1.2, cy + 1.8, 0, 0.4, bev=0.03, segs=1)
    # ---- floodlight poles on the corners, walkway lamp
    for i, (cx, cy) in enumerate(((X(-24), -24), (X(-24), 24))):
        pole = bmesh.new()
        bm_rod(pole, (cx, cy, 0), (cx, cy, 9), 0.18, seg=10)
        bm_box(pole, cx - 0.6, cx + 0.6, cy - 0.3, cy + 0.3, 8.6, 9.2)
        part(f"Flood{tag}{i}", "Metal", pole)
        box(f"FloodGlow{tag}{i}", "Glow", cx - 0.55, cx + 0.55, cy - 0.28 if cy < 0 else cy + 0.28, cy - 0.25 if cy < 0 else cy + 0.31, 8.65, 9.15)
    # ---- side-route catwalk over the canal edge: a raised wooden deck with railings
    box(f"Deck{tag}", "Plank", X(-10), X(-4), -24, -18, 1.8, 2.1)
    for i in range(6):
        box(f"DeckPost{tag}{i}", "Plank", X(-10 + i * 1.2) - 0.08, X(-10 + i * 1.2) + 0.08, -24.1, -23.9, 0, 3.0)
    box(f"DeckRail{tag}", "Plank", X(-10), X(-4), -24.1, -23.9, 2.9, 3.05)
    box(f"DeckRamp{tag}", "Plank", X(-14), X(-10), -22, -20, 0.0, 0.2)
    ramp = bpy.data.objects[f"DeckRamp{tag}"]
    ramp.rotation_euler = (0, math.radians(-sgn * 25), 0); ramp.location = (0, 0, 0.9)


half("Red", "RedDark", 1, "R")
half("Blu", "BluDark", -1, "B")

# ================================================================== MID: bridge, water tower, central cover
box("Bridge", "Plank", -4.5, 4.5, -3, 3, 0.0, 0.3)
for x in (-4.3, -2.2, 0, 2.2, 4.3):
    for y in (-3.1, 3.1):
        box(f"BridgePost{x}{y}", "Plank", x - 0.1, x + 0.1, y - 0.1, y + 0.1, 0.3, 1.4)
for y in (-3.1, 3.1):
    box(f"BridgeRail{y}", "Plank", -4.5, 4.5, y - 0.08, y + 0.08, 1.3, 1.45)
box("MidPlanks", "Plank", -4.5, 4.5, -3, 3, -2.5, -2.3)                                    # lower route under the bridge
for x in (-6, 6):
    box(f"CanalRamp{x}", "Concrete", x - 2.5, x + 2.5, -2.5, 2.5, -2.5, -2.0)
# water tower with the factory name
tower = bmesh.new()
for lx, ly in ((-2, -2), (2, -2), (2, 2), (-2, 2)):
    bm_rod(tower, (lx * 1.4, 14 + ly * 1.4, 0), (lx, 14 + ly, 11), 0.18, seg=10)
bm_lathe(tower, [(11, 0), (11, 2.4), (11.4, 3.0), (15.5, 3.0), (16.4, 1.6), (16.4, 0)], 32, "Z", (0, 14, 0))
part("WaterTower", "Metal", tower)
box("TowerBand", "Cheese", -3.05, 3.05, 10.95, 17.05, 12.6, 13.6)
text("CURDWORKS", 1.6, 0, 13.1, 10.9, "TowerSign", mat="Mouth")
# central shed with a hole to shoot through, and a rusted conveyor
shed = box("MidShed", "Concrete", -5, 5, -14, -9, 0, 3.6, bev=0.05, segs=1)
c = bmesh.new(); bm_box(c, -4.6, 4.6, -13.6, -9.4, 0.3, 3.3); bm_box(c, -1.2, 1.2, -15, -8, 0, 2.6); bm_box(c, -6, 6, -12, -11, 1.4, 2.4); cut(shed, c)
box("ShedRoof", "Roof", -5.3, 5.3, -14.3, -8.7, 3.6, 3.9)
conv = bmesh.new()
bm_box(conv, -9, 9, 20, 21.2, 0.9, 1.1)
for x in range(-8, 9, 2):
    bm_rod(conv, (x, 20.1, 0), (x, 20.1, 0.9), 0.06, seg=8); bm_rod(conv, (x, 21.1, 0), (x, 21.1, 0.9), 0.06, seg=8)
part("Conveyor", "Metal", conv)
belt = bmesh.new(); bm_box(belt, -9, 9, 20.1, 21.1, 1.1, 1.18); part("ConveyorBelt", "Rubber", belt)
wheels = bmesh.new()
for x in (-6, -2, 3, 7):
    bm_lathe(wheels, [(1.18, 0), (1.18, 0.4), (1.5, 0.4), (1.5, 0)], 20, "Z", (x, 20.6, 0))
part("BeltCheese", "Cheese", wheels)

# capture-route markers on the ground (arrows), for the layout view
for sgn, mat in ((1, "Red"), (-1, "Blu")):
    for x in range(8, 24, 5):
        arr = bmesh.new()
        bm_prism(arr, [(sgn * (x - 1.2), -0.5), (sgn * x, 0), (sgn * (x - 1.2), 0.5)], 0.01, 0.02, plane="XY")
        part(f"Arrow{mat}{x}", mat, arr)

# ------------------------------------------------------------------ export
lib.finalize(os.path.join(OUT, "curdworks.glb"), bake=BAKE, ao_distance=2.5, samples=24)
