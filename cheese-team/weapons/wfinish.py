# Weapon export: build -> apply modifiers -> join -> bake one PBR set (+ORM) -> FBX / GLB / .blend / preview. Runs in Blender.
import bpy, os, sys, math, shutil
import numpy as np
from mathutils import Vector, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
WEAPONS = ['Revolver', 'Derringer', 'SawedOff', 'MachinePistol', 'RocketLauncher', 'SemiAuto',
           'BoltRifle', 'LeverRifle', 'SMG', 'Blueprint', 'Minigun', 'SnubNose']
OWNER = {'Revolver': 'Outlaw', 'Derringer': 'Outlaw', 'SawedOff': 'MrShotgun', 'MachinePistol': 'MrShotgun',
         'RocketLauncher': 'BoomBoom', 'SemiAuto': 'BoomBoom', 'BoltRifle': 'MrFaraway', 'LeverRifle': 'MrFaraway',
         'SMG': 'Mechanic', 'Blueprint': 'Mechanic', 'Minigun': 'Greg', 'SnubNose': 'Greg'}


def log(msg, path=None):
    print(msg)
    if path:
        with open(path, 'a') as f:
            f.write(msg + '\n')


def ov(active=None, selected=None):
    win = bpy.context.window_manager.windows[0]
    d = {'window': win, 'screen': win.screen, 'scene': win.scene}
    for a in win.screen.areas:
        if a.type == 'VIEW_3D':
            d['area'] = a; d['region'] = next(r for r in a.regions if r.type == 'WINDOW')
            break
    if active is not None:
        d['active_object'] = active; d['object'] = active; d['view_layer'] = win.view_layer
    if selected is not None:
        d['selected_objects'] = selected; d['selected_editable_objects'] = selected
    return d


def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)


def output(m):
    return next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)


def uses_alpha(ob):
    for m in ob.data.materials:
        if m and m.use_nodes:
            bs = principled(m)
            if bs and bs.inputs['Alpha'].is_linked:
                return True
    return False


def apply_all(ob):
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data; ob.modifiers.clear(); ob.data = me
    if old.users == 0:
        bpy.data.meshes.remove(old)


def join(obs, name):
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    vl.objects.active = obs[0]
    if len(obs) > 1:
        with bpy.context.temp_override(**ov(obs[0], obs)):
            bpy.ops.object.join()
    t = obs[0]; t.name = name; t.data.name = name
    return t


def smart_uv(ob, margin=0.003):
    me = ob.data
    me.uv_layers.new(name='BakeUV'); me.uv_layers.active = me.uv_layers['BakeUV']
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    ob.select_set(True); vl.objects.active = ob
    with bpy.context.temp_override(**ov(ob, [ob])):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(55), island_margin=margin, area_weight=0.7, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode='OBJECT')


def new_img(name, res, color, non_color):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, res, res, alpha=False)
    im.generated_color = color
    im.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    return im


def save_img(im, path):
    im.filepath_raw = path; im.file_format = 'PNG'; im.save(); im.filepath = path


def bake_pass(ob, img, kind, samples=16, margin=16):
    mats = [m for m in ob.data.materials if m]
    saved = []
    for m in mats:
        nt = m.node_tree
        tn = nt.nodes.new('ShaderNodeTexImage'); tn.image = img; tn.name = '__bake'
        for n in nt.nodes:
            n.select = False
        tn.select = True; nt.nodes.active = tn
        if kind != 'normal':
            bs = principled(m); out = output(m)
            em = nt.nodes.new('ShaderNodeEmission'); em.name = '__em'
            sock = bs.inputs[{'basecolor': 'Base Color', 'roughness': 'Roughness', 'metallic': 'Metallic'}[kind]]
            if sock.is_linked:
                src = sock.links[0].from_socket
                if kind == 'basecolor':
                    nt.links.new(src, em.inputs['Color'])
                else:
                    cc = nt.nodes.new('ShaderNodeCombineColor'); cc.name = '__cc'
                    for i in range(3):
                        nt.links.new(src, cc.inputs[i])
                    nt.links.new(cc.outputs[0], em.inputs['Color'])
            else:
                v = sock.default_value
                em.inputs['Color'].default_value = (v[0], v[1], v[2], 1) if kind == 'basecolor' else (v, v, v, 1)
            prev = out.inputs['Surface'].links[0].from_socket if out.inputs['Surface'].is_linked else None
            nt.links.new(em.outputs[0], out.inputs['Surface'])
            saved.append((m, out, prev))
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = samples if kind in ('basecolor', 'roughness', 'metallic') else max(samples, 8)
    sc.render.bake.margin = margin; sc.render.bake.use_selected_to_active = False
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(False)
    ob.select_set(True); vl.objects.active = ob
    with bpy.context.temp_override(**ov(ob, [ob])):
        if kind == 'normal':
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=margin, use_clear=True)
        else:
            bpy.ops.object.bake(type='EMIT', margin=margin, use_clear=True)
    for (m, out, prev) in saved:
        if prev is not None:
            m.node_tree.links.new(prev, out.inputs['Surface'])
    for m in mats:
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.name.startswith('__')]:
            nt.nodes.remove(n)


def final_material(name, imgs):
    m = bpy.data.materials.new(name); m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bs = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bs.outputs[0], out.inputs[0])
    uv = nt.nodes.new('ShaderNodeUVMap'); uv.uv_map = 'UVMap'
    def tex(img):
        t = nt.nodes.new('ShaderNodeTexImage'); t.image = img; nt.links.new(uv.outputs[0], t.inputs['Vector']); return t
    nt.links.new(tex(imgs['basecolor']).outputs['Color'], bs.inputs['Base Color'])
    nt.links.new(tex(imgs['roughness']).outputs['Color'], bs.inputs['Roughness'])
    nt.links.new(tex(imgs['metallic']).outputs['Color'], bs.inputs['Metallic'])
    nm = nt.nodes.new('ShaderNodeNormalMap'); nm.uv_map = 'UVMap'
    nt.links.new(tex(imgs['normal']).outputs['Color'], nm.inputs['Color'])
    nt.links.new(nm.outputs['Normal'], bs.inputs['Normal'])
    return m


def preview(path, res=(1600, 900), samples=128):
    import wpull
    wpull.SRC_SCENE[0] = None
    p = wpull.auto(84, 58, fill=1.15, samples=samples)
    shutil.copyfile(p, path)
    wpull.back()


def finish(name, export_root, res=2048, logp=None):
    for m in ('weapons', 'wk'):
        sys.modules.pop(m, None)
    import weapons, wk
    weapons.build(name)
    outd = os.path.join(export_root, name); texd = os.path.join(outd, 'textures')
    os.makedirs(texd, exist_ok=True)
    obs = list(wk.coll().objects)
    for o in obs:
        apply_all(o)
    for c in list(wk.coll('CUTTERS').objects):
        bpy.data.objects.remove(c)
    decals = [o for o in obs if uses_alpha(o)]
    solid = [o for o in obs if o not in decals]
    W = join(solid, 'SM_%s' % name)
    smart_uv(W)
    me = W.data
    if 'UVMap' in me.uv_layers:
        me.uv_layers['UVMap'].active_render = True
    else:
        me.uv_layers.new(name='UVMap').active_render = True
    me.uv_layers.active = me.uv_layers['BakeUV']
    imgs = {'basecolor': new_img('T_%s_BaseColor' % name, res, (0.5, 0.5, 0.5, 1), False),
            'roughness': new_img('T_%s_Roughness' % name, res, (0.6, 0.6, 0.6, 1), True),
            'metallic': new_img('T_%s_Metallic' % name, res, (0, 0, 0, 1), True),
            'normal': new_img('T_%s_Normal' % name, res, (0.5, 0.5, 1.0, 1), True)}
    for k in ('basecolor', 'roughness', 'metallic', 'normal'):
        bake_pass(W, imgs[k], k)
        save_img(imgs[k], os.path.join(texd, imgs[k].name + '.png'))
        log('  %s: baked %s' % (name, k), logp)
    rp = np.array(imgs['roughness'].pixels[:]).reshape(-1, 4); mp = np.array(imgs['metallic'].pixels[:]).reshape(-1, 4)
    orm = np.stack([np.ones(len(rp)), rp[:, 0], mp[:, 0], np.ones(len(rp))], 1)
    oi = new_img('T_%s_ORM' % name, res, (1, 1, 0, 1), True); oi.pixels = orm.ravel().tolist()
    save_img(oi, os.path.join(texd, oi.name + '.png'))
    fm = final_material('M_%s' % name, imgs)
    me.materials.clear(); me.materials.append(fm)
    for p in me.polygons:
        p.material_index = 0
    for l in [l for l in me.uv_layers if l.name != 'BakeUV']:
        me.uv_layers.remove(l)
    me.uv_layers['BakeUV'].name = 'UVMap'
    me.uv_layers['UVMap'].active_render = True
    if decals:
        D = join(decals, 'SM_%s_Decals' % name)
        for m in D.data.materials:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image:
                    src = bpy.path.abspath(n.image.filepath)
                    dst = os.path.join(texd, os.path.basename(src))
                    if os.path.exists(src) and src != dst:
                        shutil.copyfile(src, dst)
                    n.image.filepath = dst
        D.parent = W
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(outd, '%s.blend' % name), relative_remap=True)
    exp = [W] + ([D] if decals else [])
    vl = bpy.context.view_layer
    for o in vl.objects:
        o.select_set(o in exp)
    vl.objects.active = W
    with bpy.context.temp_override(**ov(W, exp)):
        bpy.ops.export_scene.fbx(filepath=os.path.join(outd, '%s.fbx' % name), use_selection=True, object_types={'MESH'},
                                 path_mode='COPY', embed_textures=True, apply_unit_scale=True, mesh_smooth_type='FACE')
        bpy.ops.export_scene.gltf(filepath=os.path.join(outd, '%s.glb' % name), export_format='GLB', use_selection=True)
    log('  %s: exported (%d tris)' % (name, sum(len(p.vertices) - 2 for p in me.polygons)), logp)
    preview(os.path.join(outd, '%s_preview.png' % name))
    log('%s done' % name, logp)
    return outd


def lineup(export_root, path):
    import wk
    bpy.ops.wm.read_homefile(use_empty=True)
    sc = bpy.context.scene
    # two rows: primaries on top, secondaries below; each weapon laid flat, side-on, muzzle to the left (-Y -> screen left)
    prim = ['Revolver', 'SawedOff', 'RocketLauncher', 'BoltRifle', 'SMG', 'Minigun']
    sec = ['Derringer', 'MachinePistol', 'SemiAuto', 'LeverRifle', 'Blueprint', 'SnubNose']
    for row, names in enumerate((prim, sec)):
        x = 0.0
        for nm in names:
            before = set(bpy.data.objects)
            with bpy.context.temp_override(**ov()):
                bpy.ops.import_scene.gltf(filepath=os.path.join(export_root, nm, '%s.glb' % nm))
            new = [o for o in bpy.data.objects if o not in before]
            pts = [o.matrix_world @ Vector(c) for o in new if o.type == 'MESH' for c in o.bound_box]
            mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
            hold = bpy.data.objects.new('Slot_' + nm, None); sc.collection.objects.link(hold)
            for o in new:
                if o.parent is None:
                    o.parent = hold
            hold.rotation_euler = (0, 0, math.radians(-90))         # muzzle (-Y) -> -X: screen left for a camera looking +Y
            length = mx.y - mn.y
            hold.location = (x - mn.y, 0, -row * 0.55 - (mn.z + mx.z) / 2)
            x += length + 0.12
    pts = [o.matrix_world @ Vector(c) for o in bpy.data.objects if o.type == 'MESH' for c in o.bound_box]
    mn = Vector([min(p[i] for p in pts) for i in range(3)]); mx = Vector([max(p[i] for p in pts) for i in range(3)])
    c = (mn + mx) / 2
    cam_d = bpy.data.cameras.new('LineCam'); cam_d.type = 'ORTHO'; cam_d.ortho_scale = max(mx.x - mn.x, (mx.z - mn.z) * 2.2) * 1.08
    cam = bpy.data.objects.new('LineCam', cam_d); sc.collection.objects.link(cam)
    cam.location = (c.x, -3.0, c.z); cam.rotation_euler = (math.radians(90), 0, 0); sc.camera = cam
    w = bpy.data.worlds.new('LineWorld'); w.use_nodes = True
    nt = w.node_tree; bg = next(n for n in nt.nodes if n.type == 'BACKGROUND')
    hp = os.path.join(HERE, 'hdri', 'studio_small_09_2k.hdr')
    if os.path.exists(hp):
        env = nt.nodes.new('ShaderNodeTexEnvironment'); env.image = bpy.data.images.load(hp, check_existing=True)
        lp = nt.nodes.new('ShaderNodeLightPath'); mx_ = nt.nodes.new('ShaderNodeMixShader'); bgc = nt.nodes.new('ShaderNodeBackground')
        bgc.inputs['Color'].default_value = (0.2, 0.2, 0.205, 1)
        out = next(n for n in nt.nodes if n.type == 'OUTPUT_WORLD')
        nt.links.new(env.outputs[0], bg.inputs['Color'])
        nt.links.new(lp.outputs['Is Camera Ray'], mx_.inputs[0]); nt.links.new(bg.outputs[0], mx_.inputs[1]); nt.links.new(bgc.outputs[0], mx_.inputs[2])
        nt.links.new(mx_.outputs[0], out.inputs[0])
    sc.world = w
    sc.render.engine = 'CYCLES'; sc.cycles.samples = 128; sc.cycles.use_denoising = True
    try:
        sc.cycles.device = 'GPU'
    except Exception:
        pass
    try:
        sc.view_settings.view_transform = 'AgX'
    except TypeError:
        pass
    sc.render.resolution_x = 3000; sc.render.resolution_y = int(3000 * (mx.z - mn.z) * 1.25 / max(0.01, mx.x - mn.x)) + 200
    sc.render.filepath = path
    with bpy.context.temp_override(**ov()):
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(export_root, 'WeaponLineup.blend'))
