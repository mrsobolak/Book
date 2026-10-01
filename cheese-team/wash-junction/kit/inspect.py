"""Four-view contact sheet of an exported GLB (front 3/4, back 3/4, side, top-down) for checking a finished asset.
    blender -b -P kit/inspect.py -- export/Name/SM_Name.glb [out.jpg]
Writes <glb dir>/_inspect_<Name>.jpg by default (git-ignored)."""
import bpy, sys, os, math, subprocess
from mathutils import Vector
from bpy_extras.object_utils import world_to_camera_view

argv = sys.argv[sys.argv.index("--") + 1:]
glb = os.path.abspath(argv[0])
name = os.path.splitext(os.path.basename(glb))[0]
out = os.path.abspath(argv[1]) if len(argv) > 1 else os.path.join(os.path.dirname(glb), "_inspect_%s.jpg" % name)
bpy.ops.wm.read_factory_settings(use_empty=True)
sc = bpy.context.scene
sc.render.engine = "CYCLES"
bpy.ops.import_scene.gltf(filepath=glb)
objs = [o for o in sc.objects if o.type == "MESH"]
lo = Vector((1e9, 1e9, 1e9)); hi = -lo
for o in objs:
    for c in o.bound_box:
        p = o.matrix_world @ Vector(c)
        lo = Vector(map(min, lo, p)); hi = Vector(map(max, hi, p))
lift = -lo.z
for o in objs:
    o.location.z += lift
lo.z += lift; hi.z += lift
w = bpy.data.worlds.new("w"); sc.world = w; w.use_nodes = True
sky = w.node_tree.nodes.new("ShaderNodeTexSky"); sky.sky_type = "NISHITA"; sky.sun_disc = False
sky.sun_elevation = math.radians(38); sky.sun_rotation = math.radians(-60); sky.dust_density = 2.0
w.node_tree.links.new(sky.outputs[0], w.node_tree.nodes["Background"].inputs[0])
w.node_tree.nodes["Background"].inputs[1].default_value = 0.22
sun = bpy.data.lights.new("sun", "SUN"); sun.energy = 3.2; sun.angle = math.radians(1.2)
so = bpy.data.objects.new("sun", sun); sc.collection.objects.link(so)
d = Vector((math.cos(math.radians(38)) * math.cos(math.radians(-60)), math.cos(math.radians(38)) * math.sin(math.radians(-60)), math.sin(math.radians(38))))
so.rotation_euler = d.to_track_quat("Z", "Y").to_euler()
bpy.ops.mesh.primitive_plane_add(size=500, location=(0, 0, -0.002))
gm = bpy.data.materials.new("g"); gm.use_nodes = True
gm.node_tree.nodes["Principled BSDF"].inputs["Base Color"].default_value = (0.25, 0.22, 0.19, 1)
sc.objects["Plane"].data.materials.append(gm)
cam = bpy.data.cameras.new("c"); cam.lens = 50; cam.clip_end = 5000
co = bpy.data.objects.new("c", cam); sc.collection.objects.link(co); sc.camera = co
sc.render.resolution_x, sc.render.resolution_y = 640, 480
sc.cycles.samples = 20; sc.cycles.use_denoising = False
sc.view_settings.view_transform = "AgX"; sc.view_settings.exposure = -0.35
sc.render.image_settings.file_format = "JPEG"
tgt = (lo + hi) / 2
corners = [Vector((x, y, z)) for x in (lo.x, hi.x) for y in (lo.y, hi.y) for z in (lo.z, hi.z)]
views = [("front34", -36, 17), ("back34", 144, 22), ("side", -90, 5), ("top", -36, 70)]
tmp = []
for tag, az, el in views:
    dv = Vector((math.cos(math.radians(el)) * math.cos(math.radians(az)), math.cos(math.radians(el)) * math.sin(math.radians(az)), math.sin(math.radians(el))))
    a, b = 0.05, 5000.0
    def fits(dist):
        co.location = tgt + dv * dist
        co.rotation_euler = (-dv).to_track_quat("-Z", "Y").to_euler()
        bpy.context.view_layer.update()
        for c in corners:
            p = world_to_camera_view(sc, co, c)
            if p.z <= 0 or not (0.06 <= p.x <= 0.94 and 0.06 <= p.y <= 0.94):
                return False
        return True
    for _ in range(50):
        m = (a + b) / 2
        if fits(m): b = m
        else: a = m
    fits(b)
    f = os.path.join(os.path.dirname(out), "_v_%s_%s.jpg" % (name, tag))
    sc.render.filepath = f
    bpy.ops.render.render(write_still=True)
    tmp.append(f)
subprocess.run(["/usr/bin/python3", "-c", """
import sys
from PIL import Image, ImageDraw
fs = sys.argv[2:]; W = Image.new('RGB', (1280, 960))
for i, f in enumerate(fs):
    im = Image.open(f); W.paste(im, ((i % 2) * 640, (i // 2) * 480))
    ImageDraw.Draw(W).text(((i % 2) * 640 + 8, (i // 2) * 480 + 6), ['front 3/4', 'back 3/4', 'side (-Y)', 'top'][i], fill=(255, 255, 0))
W.save(sys.argv[1], quality=88)
""", out] + tmp, check=True)
for f in tmp:
    os.remove(f)
print("[inspect] wrote", out)
