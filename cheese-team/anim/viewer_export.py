# Export each class's third-person set as a GLB for the HTML viewer (runs inside Blender).
# Both weapons are bone-parented to the `weapon` socket (and `wp_01` for the second sawed-off) exactly the way
# anim.Rig.attach places them (scale 0.7 x class height, origin at the grip), named W_<Weapon>_<bone>_... so the
# viewer can show only the gun that belongs to the playing action.
import bpy, os
from mathutils import Matrix

ANIM = r"C:\Users\mrsobo\Documents\LonelyRoad\CheeseAnim\export"
WP = r"C:\Users\mrsobo\Documents\LonelyRoad\CheeseWeapons_Blender\export"
AMMO = r"C:\Users\mrsobo\Documents\LonelyRoad\CheeseWeapons_Blender\export_ammo"
WS = 0.7
CLASS_WEAPONS = {'Outlaw': ('Revolver', 'Derringer'), 'MrShotgun': ('SawedOff', 'MachinePistol'),
                 'RocketGuy': ('RocketLauncher', 'SemiAuto'), 'Sniper': ('BoltRifle', 'LeverRifle'),
                 'Mechanic': ('SMG', 'Blueprint'), 'Greg': ('Minigun', 'SnubNose')}
DUAL = {'SawedOff'}
PARTS = {'Minigun': (('Barrels', 'wp_02'),), 'RocketLauncher': (('ammo:Rocket', 'wp_03'),)}            # fallback if anim isn't loaded


def parts_of(w):
    """moving parts + ammo pieces on spare socket bones, straight from anim.WDEF (the animations drive these bones)"""
    try:
        import anim
        return tuple((p[0], p[1]) for p in anim.WDEF.get(w, {}).get('parts', ()))
    except Exception:
        return PARTS.get(w, ())


def export(cls, dst, tex=1024, fmt='WEBP'):
    bpy.ops.wm.open_mainfile(filepath=os.path.join(ANIM, cls + '_TP.blend'))
    arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
    s = arm.matrix_world.to_scale()[0] / 0.01
    arm.data.pose_position = 'REST'
    bpy.context.view_layer.update()
    for w in CLASS_WEAPONS[cls]:
        jobs = [(w, b) for b in (('weapon', 'wp_01') if w in DUAL else ('weapon',))]
        jobs += [(w + '_' + part, b) for part, b in parts_of(w)]
        for fn, bone in jobs:
            before = set(bpy.data.objects)
            if '_ammo:' in fn:                                      # a round from the ammo set (the loaded rocket)
                a = fn.split('_ammo:')[1]; path = os.path.join(AMMO, a, a + '.glb')
            else:
                path = os.path.join(WP, w, fn + '.glb')
            bpy.ops.import_scene.gltf(filepath=path)
            new = [o for o in bpy.data.objects if o not in before]
            loc, rot, _ = (arm.matrix_world @ arm.data.bones[bone].matrix_local).decompose()
            H = Matrix.LocRotScale(loc, rot, (WS * s,) * 3)
            for o in new:
                if o.type != 'MESH':
                    continue
                M = Matrix.LocRotScale(o.location, o.matrix_basis.to_quaternion(), (1, 1, 1))
                o.parent = arm; o.parent_type = 'BONE'; o.parent_bone = bone
                o.matrix_parent_inverse = Matrix.Identity(4)
                bpy.context.view_layer.update()
                o.matrix_world = H @ M
                o.name = 'W_%s_%s_%s' % (w, bone, o.name)
            for o in new:
                if o.type != 'MESH':
                    bpy.data.objects.remove(o, do_unlink=True)
    arm.data.pose_position = 'POSE'
    bpy.context.view_layer.update()
    for im in bpy.data.images:                      # small textures: the viewer embeds every model in one HTML file
        if im.size[0] > tex or im.size[1] > tex:
            im.scale(min(tex, im.size[0]), min(tex, im.size[1]))
    path = os.path.join(dst, cls + '.glb')
    win = bpy.context.window_manager.windows[0]
    area = next((a for a in win.screen.areas if a.type == 'VIEW_3D'), win.screen.areas[0])
    with bpy.context.temp_override(window=win, screen=win.screen, area=area, active_object=arm, object=arm):
        bpy.ops.export_scene.gltf(filepath=path, export_format='GLB', export_animations=True,
                                  export_animation_mode='ACTIONS', export_image_format=fmt,
                                  export_image_quality=82)
    return path
