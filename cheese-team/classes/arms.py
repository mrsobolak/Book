# Longer arms for the CheesePlayer base (runs inside Blender, right after CheesePlayer.blend is opened).
# The stock stick arms (0.17 + 0.14 m) can't bring the hands together in front of the wedge, so two-handed weapons
# clip. This stretches the upper and lower arm sticks along their bones (radius unchanged), moves the hand balls with
# them, and lengthens the bones to match. Skeleton names and hierarchy stay the same.
import bpy
from mathutils import Vector

KU = 1.65          # upper arm length factor  (0.17 -> 0.28 m)
KL = 1.65          # lower arm length factor  (0.14 -> 0.23 m)


def _stretch(p, h, t, k):
    """displacement that stretches the segment h->t by k along its axis (caps beyond the ends just ride along)"""
    ax = t - h; L = ax.length; u = ax / L
    a = (p - h).dot(u)
    return u * ((k - 1.0) * max(0.0, min(L, a)))


def lengthen(ku=KU, kl=KL):
    arm = bpy.data.objects['Armature']; body = bpy.data.objects['SK_CheeseTP']
    if arm.get('arm_k'):
        return
    A2B = body.matrix_world.inverted() @ arm.matrix_world            # armature space (cm) -> body mesh space
    bones = arm.data.bones
    plan = {}
    for s in ('l', 'r'):
        H1 = A2B @ bones['upperarm_' + s].head_local; T1 = A2B @ bones['upperarm_' + s].tail_local
        T2 = A2B @ bones['lowerarm_' + s].tail_local
        d1 = (T1 - H1) * (ku - 1.0)                                   # elbow shift
        d2 = d1 + (T2 - T1) * (kl - 1.0)                             # wrist shift
        plan[s] = (H1, T1, T2, d1, d2)
    # ---- mesh: blend the per-bone displacements by the skin weights
    gi = {g.index: g.name for g in body.vertex_groups}
    for v in body.data.vertices:
        tot = 0.0; disp = Vector()
        for g in v.groups:
            n = gi.get(g.group, ''); w = g.weight
            if w <= 0.0:
                continue
            tot += w
            if n[:-2] in ('upperarm', 'lowerarm', 'hand') and n[-2:] in ('_l', '_r'):
                H1, T1, T2, d1, d2 = plan[n[-1]]
                if n.startswith('upperarm'):
                    disp += _stretch(v.co, H1, T1, ku) * w
                elif n.startswith('lowerarm'):
                    disp += (d1 + _stretch(v.co, T1, T2, kl)) * w
                else:
                    disp += d2 * w
        if tot > 0.0:
            v.co = v.co + disp / tot
    body.data.update()
    # ---- bones (edit in armature space; descendants of the lower arm ride the wrist)
    B2A = A2B.inverted()
    vw = bpy.context.view_layer
    for o in vw.objects:
        o.select_set(False)
    arm.hide_set(False); arm.select_set(True); vw.objects.active = arm
    win = bpy.context.window_manager.windows[0]
    ctx = dict(window=win, screen=win.screen, active_object=arm, object=arm, view_layer=vw,
               selected_objects=[arm], selected_editable_objects=[arm])
    with bpy.context.temp_override(**ctx):
        bpy.ops.object.mode_set(mode='EDIT')
        eb = arm.data.edit_bones
        for s in ('l', 'r'):
            H1, T1, T2, d1, d2 = plan[s]
            e1 = B2A.to_3x3() @ d1; e2 = B2A.to_3x3() @ d2
            up = eb['upperarm_' + s]; lo = eb['lowerarm_' + s]
            up.tail = up.tail + e1
            lo.head = lo.head + e1; lo.tail = lo.tail + e2
            for c in lo.children_recursive:
                c.head = c.head + e2; c.tail = c.tail + e2
        bpy.ops.object.mode_set(mode='OBJECT')
    arm.select_set(False)
    arm['arm_k'] = (ku, kl)
    vw.update()
