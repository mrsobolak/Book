# Finishing pipeline (runs in the desktop Blender): build a class, bake its accessories to one texture set, skin them to
# the rig, apply the class height, and export FBX + GLB + .blend + textures + a preview render. Then a six-class lineup.
import bpy, os, sys, math, shutil
import numpy as np
from mathutils import Vector, Matrix, Euler

HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.insert(0, HERE)
CLASSES = ['Outlaw', 'MrShotgun', 'RocketGuy', 'Sniper', 'Mechanic', 'Heavy']
NICE = {'Outlaw': 'Outlaw', 'MrShotgun': 'Mr. Shotgun', 'RocketGuy': 'Rocket Guy', 'Sniper': 'Sniper', 'Mechanic': 'Mechanic',
        'Heavy': 'Heavy'}


def log(msg, path=None):
    print(msg)
    if path:
        with open(path, 'a') as f:
            f.write(msg + '\n')


def ov(active=None, selected=None):
    wm = bpy.context.window_manager
    win = wm.windows[0]
    d = {'window': win, 'screen': win.screen}
    for a in win.screen.areas:
        if a.type == 'VIEW_3D':
            d['area'] = a
            d['region'] = next(r for r in a.regions if r.type == 'WINDOW')
            break
    if active is not None:
        d['active_object'] = active; d['object'] = active
        d['view_layer'] = bpy.context.view_layer
    if selected is not None:
        d['selected_objects'] = selected; d['selected_editable_objects'] = selected
    return d


def build(cls):
    for m in ('classes', 'acc'):
        sys.modules.pop(m, None)
    import acc, classes
    bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'src', 'cheese', 'CheesePlayer.blend'))
    P = acc.Probe(); T = acc.top_frame(P)
    classes.BUILDERS[cls](P, T)
    return acc, classes


def uses_alpha(ob):
    for m in ob.data.materials:
        if m and m.use_nodes:
            for l in m.node_tree.links:
                if l.to_socket.name == 'Alpha' and l.from_node.type == 'TEX_IMAGE':
                    return True
    return False


def bake_ready(ob):
    """apply modifiers, give every vertex a rigid weight to the stored bone"""
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(ob.evaluated_get(dg), preserve_all_data_layers=True, depsgraph=dg)
    old = ob.data
    ob.modifiers.clear()
    ob.data = me
    bpy.data.meshes.remove(old)
    vg = ob.vertex_groups.new(name=ob.get('bone', 'spine_01'))
    vg.add(list(range(len(me.vertices))), 1.0, 'REPLACE')


def join(obs, name):
    target = obs[0]
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    for o in obs:
        o.select_set(True)
    bpy.context.view_layer.objects.active = target
    if len(obs) > 1:
        with bpy.context.temp_override(**ov(target, obs)):
            bpy.ops.object.join()
    target.name = name; target.data.name = name
    return target


def smart_uv(ob, layer='BakeUV', margin=0.004):
    me = ob.data
    uv = me.uv_layers.new(name=layer)
    me.uv_layers.active = uv
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    with bpy.context.temp_override(**ov(ob, [ob])):
        bpy.ops.object.mode_set(mode='EDIT')
        bpy.ops.mesh.select_all(action='SELECT')
        bpy.ops.uv.smart_project(angle_limit=math.radians(60), island_margin=margin, area_weight=0.6, scale_to_bounds=True)
        bpy.ops.object.mode_set(mode='OBJECT')
    return uv


def principled(m):
    return next((n for n in m.node_tree.nodes if n.type == 'BSDF_PRINCIPLED'), None)


def output(m):
    return next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL' and n.is_active_output), None) or \
        next((n for n in m.node_tree.nodes if n.type == 'OUTPUT_MATERIAL'), None)


def bake_pass(ob, img, kind, margin=12):
    """kind: 'basecolor' | 'roughness' | 'metallic' (emission route) or 'normal' (tangent-space normal bake)"""
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
                    cv = nt.nodes.new('ShaderNodeCombineColor'); cv.name = '__cv'
                    for i in range(3):
                        nt.links.new(src, cv.inputs[i])
                    nt.links.new(cv.outputs[0], em.inputs['Color'])
            else:
                v = sock.default_value
                em.inputs['Color'].default_value = (v[0], v[1], v[2], 1) if kind == 'basecolor' else (v, v, v, 1)
            prev = out.inputs['Surface'].links[0].from_socket if out.inputs['Surface'].is_linked else None
            nt.links.new(em.outputs[0], out.inputs['Surface'])
            saved.append((m, out, prev))
    sc = bpy.context.scene
    sc.render.engine = 'CYCLES'
    sc.cycles.samples = 1 if kind != 'normal' else 4
    sc.render.bake.margin = margin
    sc.render.bake.use_selected_to_active = False
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    ob.select_set(True); bpy.context.view_layer.objects.active = ob
    with bpy.context.temp_override(**ov(ob, [ob])):
        if kind == 'normal':
            bpy.ops.object.bake(type='NORMAL', normal_space='TANGENT', margin=margin, use_clear=True)
        else:
            bpy.ops.object.bake(type='EMIT', margin=margin, use_clear=True)
    for (m, out, prev) in saved:
        nt = m.node_tree
        if prev is not None:
            nt.links.new(prev, out.inputs['Surface'])
    for m in mats:
        nt = m.node_tree
        for n in [n for n in nt.nodes if n.name.startswith('__')]:
            nt.nodes.remove(n)


def new_img(name, res, color, non_color):
    im = bpy.data.images.get(name)
    if im:
        bpy.data.images.remove(im)
    im = bpy.data.images.new(name, res, res, alpha=False, float_buffer=False)
    im.generated_color = color
    im.colorspace_settings.name = 'Non-Color' if non_color else 'sRGB'
    return im


def save_img(im, path):
    im.filepath_raw = path; im.file_format = 'PNG'; im.save()
    im.filepath = path


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


def skin(ob, arm):
    ob.parent = arm
    ob.matrix_parent_inverse = arm.matrix_world.inverted()
    md = ob.modifiers.new('Armature', 'ARMATURE'); md.object = arm


def preview(path, cls, res=1200):
    sc = bpy.context.scene
    arm = bpy.data.objects['Armature']
    arm.data.pose_position = 'POSE'
    act = bpy.data.actions.get('TP_Idle')
    if act:
        arm.animation_data_create(); arm.animation_data.action = act
        sc.frame_set(int(act.frame_range[0]) + 6)
    h = 1.0 * classes_scale(cls)
    cam_d = bpy.data.cameras.new('PrevCam'); cam_d.lens = 70
    cam = bpy.data.objects.new('PrevCam', cam_d); sc.collection.objects.link(cam)
    tgt = Vector((0, 0, 0.58 * h))
    pos = tgt + Vector((math.sin(math.radians(28)) * 2.6, -math.cos(math.radians(28)) * 2.6, 0.45)) * h
    cam.location = pos
    cam.rotation_euler = (tgt - pos).to_track_quat('-Z', 'Y').to_euler()
    sc.camera = cam
    for nm_, loc, en, size in (('Key', (2.2, -2.6, 3.0), 600.0, 2.0), ('Fill', (-2.8, -1.5, 1.4), 180.0, 3.0),
                               ('Rim', (0.5, 3.0, 2.6), 400.0, 1.5)):
        ld = bpy.data.lights.new(nm_, 'AREA'); ld.energy = en; ld.size = size
        lo = bpy.data.objects.new(nm_, ld); sc.collection.objects.link(lo)
        lo.location = Vector(loc) * h
        lo.rotation_euler = (Vector((0, 0, 0.6 * h)) - lo.location).to_track_quat('-Z', 'Y').to_euler()
    w = bpy.data.worlds.new('PrevWorld'); w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.36, 0.32, 0.27, 1); bg.inputs['Strength'].default_value = 0.6
    sc.world = w
    try:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = res; sc.render.resolution_y = res
    sc.render.film_transparent = False
    sc.render.filepath = path
    with bpy.context.temp_override(**ov()):
        bpy.ops.render.render(write_still=True)
    for o in (cam,) + tuple(bpy.data.objects[n] for n in ('Key', 'Fill', 'Rim')):
        bpy.data.objects.remove(o)


def classes_scale(cls):
    import classes
    return classes.SCALE.get(cls, 1.0)


def finish(cls, export_root, res=2048, logp=None):
    acc, classes = build(cls)
    outd = os.path.join(export_root, cls); texd = os.path.join(outd, 'textures')
    os.makedirs(texd, exist_ok=True)
    arm = bpy.data.objects['Armature']; body = bpy.data.objects['SK_CheeseTP']
    arm.data.pose_position = 'REST'
    obs = list(bpy.data.collections['ACC'].objects)
    for o in obs:
        bake_ready(o)
    decals = [o for o in obs if uses_alpha(o)]
    solid = [o for o in obs if o not in decals]
    accm = join(solid, 'SK_%s_Accessories' % cls)
    smart_uv(accm)
    me = accm.data                                   # (layer references go stale across edit mode: look up by name)
    # render (sample the pattern textures) with the original UVs, bake into BakeUV
    rname = 'UVMap' if 'UVMap' in me.uv_layers else next((l.name for l in me.uv_layers if l.name != 'BakeUV'), 'BakeUV')
    me.uv_layers[rname].active_render = True
    me.uv_layers.active = me.uv_layers['BakeUV']
    imgs = {
        'basecolor': new_img('T_%s_Acc_BaseColor' % cls, res, (0.5, 0.5, 0.5, 1), False),
        'roughness': new_img('T_%s_Acc_Roughness' % cls, res, (0.6, 0.6, 0.6, 1), True),
        'metallic': new_img('T_%s_Acc_Metallic' % cls, res, (0.0, 0.0, 0.0, 1), True),
        'normal': new_img('T_%s_Acc_Normal' % cls, res, (0.5, 0.5, 1.0, 1), True),
    }
    for k in ('basecolor', 'roughness', 'metallic', 'normal'):
        bake_pass(accm, imgs[k], k)
        save_img(imgs[k], os.path.join(texd, imgs[k].name + '.png'))
        log('  %s: baked %s' % (cls, k), logp)
    # ORM (R=AO 1, G=roughness, B=metallic) for glTF/Unreal-style shaders
    rp = np.array(imgs['roughness'].pixels[:]).reshape(-1, 4); mp = np.array(imgs['metallic'].pixels[:]).reshape(-1, 4)
    orm = np.stack([np.ones(len(rp)), rp[:, 0], mp[:, 0], np.ones(len(rp))], 1)
    oi = new_img('T_%s_Acc_ORM' % cls, res, (1, 1, 0, 1), True); oi.pixels = orm.ravel().tolist()
    save_img(oi, os.path.join(texd, oi.name + '.png'))
    # swap to the single baked material, keep only the bake UVs (renamed UVMap)
    fm = final_material('M_%s_Accessories' % cls, imgs)
    me.materials.clear(); me.materials.append(fm)
    for p in me.polygons:
        p.material_index = 0
    for l in [l for l in me.uv_layers if l.name != 'BakeUV']:
        me.uv_layers.remove(l)
    me.uv_layers['BakeUV'].name = 'UVMap'
    me.uv_layers['UVMap'].active_render = True
    skin(accm, arm)
    if decals:
        dm = join(decals, 'SK_%s_Decals' % cls)
        for m in dm.data.materials:
            for n in m.node_tree.nodes:
                if n.type == 'TEX_IMAGE' and n.image:
                    dst = os.path.join(texd, os.path.basename(n.image.filepath_raw or n.image.name))
                    shutil.copyfile(bpy.path.abspath(n.image.filepath), dst)
                    n.image.filepath = dst
        skin(dm, arm)
    # class height: uniform scale of the whole rig (animations scale with it)
    s = classes.SCALE.get(cls, 1.0)
    arm.scale = (0.01 * s, 0.01 * s, 0.01 * s)
    body.name = 'SK_%s_Body' % cls
    arm.data.pose_position = 'POSE'
    bpy.context.view_layer.update()
    # exports
    blend = os.path.join(outd, '%s.blend' % cls)
    bpy.ops.wm.save_as_mainfile(filepath=blend, relative_remap=True)
    for o in bpy.context.view_layer.objects:
        o.select_set(False)
    with bpy.context.temp_override(**ov()):
        bpy.ops.export_scene.fbx(filepath=os.path.join(outd, '%s.fbx' % cls), use_selection=False,
                                 object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, bake_anim=True,
                                 bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False, path_mode='COPY',
                                 embed_textures=True, apply_unit_scale=True)
        bpy.ops.export_scene.gltf(filepath=os.path.join(outd, '%s.glb' % cls), export_format='GLB',
                                  export_animations=True, export_animation_mode='ACTIONS')
    log('  %s: exported fbx/glb/blend' % cls, logp)
    preview(os.path.join(outd, '%s_preview.png' % cls), cls)
    log('%s done' % cls, logp)
    return outd


def lineup(export_root, path):
    bpy.ops.wm.read_homefile(use_empty=True)
    sc = bpy.context.scene
    x = -2.5 * 0.62
    tops = []
    for cls in CLASSES:
        before = set(bpy.data.objects)
        with bpy.context.temp_override(**ov()):
            bpy.ops.import_scene.gltf(filepath=os.path.join(export_root, cls, '%s.glb' % cls))
        new = [o for o in bpy.data.objects if o not in before]
        roots = [o for o in new if o.parent is None]
        for r in roots:
            r.location.x += x
        for o in new:
            if o.type == 'ARMATURE':
                ad = o.animation_data
                acts = [a for a in bpy.data.actions if 'Idle' in a.name and 'Pistol' not in a.name]
                if ad and acts:
                    ad.action = acts[-1]
        x += 0.62
    sc.frame_set(6)
    cam_d = bpy.data.cameras.new('LineCam'); cam_d.lens = 50
    cam = bpy.data.objects.new('LineCam', cam_d); sc.collection.objects.link(cam)
    cam.location = (0.0, -5.2, 1.05); cam.rotation_euler = (math.radians(86), 0, 0)
    sc.camera = cam
    for nm_, loc, en, size in (('Key', (2.5, -3.5, 4.0), 1500.0, 4.0), ('Fill', (-4.0, -2.5, 2.0), 500.0, 5.0),
                               ('Rim', (0.0, 3.5, 3.0), 900.0, 4.0)):
        ld = bpy.data.lights.new(nm_, 'AREA'); ld.energy = en; ld.size = size
        lo = bpy.data.objects.new(nm_, ld); sc.collection.objects.link(lo); lo.location = loc
        lo.rotation_euler = (Vector((0, 0, 0.7)) - lo.location).to_track_quat('-Z', 'Y').to_euler()
    bpy.ops.mesh.primitive_plane_add(size=30)
    gm = bpy.data.materials.new('Ground'); gm.use_nodes = True
    principled(gm).inputs['Base Color'].default_value = (0.42, 0.36, 0.28, 1); principled(gm).inputs['Roughness'].default_value = 0.9
    bpy.context.active_object.data.materials.append(gm)
    w = bpy.data.worlds.new('LineWorld'); w.use_nodes = True
    bg = next(n for n in w.node_tree.nodes if n.type == 'BACKGROUND')
    bg.inputs['Color'].default_value = (0.55, 0.47, 0.38, 1); bg.inputs['Strength'].default_value = 0.7
    sc.world = w
    try:
        sc.render.engine = 'BLENDER_EEVEE_NEXT'
    except TypeError:
        sc.render.engine = 'BLENDER_EEVEE'
    sc.render.resolution_x = 2400; sc.render.resolution_y = 1000
    sc.render.filepath = path
    with bpy.context.temp_override(**ov()):
        bpy.ops.render.render(write_still=True)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(export_root, 'Lineup.blend'))
