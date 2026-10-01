# CheeseTeam third-person weapon animations (runs inside Blender).
# Procedural keyframe authoring on the CheesePlayer rig: two-bone IK for the stick arms and legs, a foot-planted gait for
# walk forward / back / strafe left / right, weapon held on the `weapon` socket bone (second gun on `wp_01`), fire and
# reload per hold type, and a per-frame clipping check (weapon vs body, arms vs body, leg vs leg).
#
# Spaces: "char space" = metres, character at rest, facing -Y, character's LEFT is +X, feet at z=0.
# Weapon meshes: muzzle along -Y, up +Z, origin at the grip (see weapons/wfinish pivot json).
import bpy, bmesh, math, os, json
from mathutils import Vector, Matrix, Quaternion, Euler
from mathutils.bvhtree import BVHTree

CH = r"C:\Users\mrsobo\Documents\LonelyRoad\CheeseClasses_Blender\export"
WP = r"C:\Users\mrsobo\Documents\LonelyRoad\CheeseWeapons_Blender\export"
FPS = 30
WS = 0.7                      # weapon scale relative to real-world size (cheese-sized guns)
PI = math.pi
MM = 0.001


def W(u, v, x=0.0):
    return Vector((x * MM, -u * MM, v * MM))


def ease(t):
    t = max(0.0, min(1.0, t))
    return t * t * (3 - 2 * t)


def lerp(a, b, t):
    return a + (b - a) * t


# ------------------------------------------------------------------ scene setup
class Rig:
    def __init__(self, cls):
        bpy.ops.wm.open_mainfile(filepath=os.path.join(CH, cls, cls + '.blend'))
        self.cls = cls
        self.arm = next(o for o in bpy.data.objects if o.type == 'ARMATURE')
        self.body = next(o for o in bpy.data.objects if o.type == 'MESH' and o.name.endswith('_Body'))
        self.acc = [o for o in bpy.data.objects if o.type == 'MESH' and o is not self.body]
        self.arm.data.pose_position = 'POSE'
        if self.arm.animation_data is None:
            self.arm.animation_data_create()
        self.pb = self.arm.pose.bones
        self.mw = self.arm.matrix_world.copy()
        self.s = self.mw.to_scale()[0] / 0.01                     # class height scale
        self.weapons = {}

    # char-space metres <-> armature space (cm, class scale folded into the object)
    def A(self, p):
        return Vector(p) * 100.0

    def C(self, a):
        return Vector(a) / 100.0

    def bone_len(self, n):
        return self.arm.data.bones[n].length

    def head(self, n):
        return self.pb[n].head.copy()

    def tail(self, n):
        return self.pb[n].tail.copy()

    def update(self):
        bpy.context.view_layer.update()

    def reset(self):
        for p in self.pb:
            p.location = (0, 0, 0); p.rotation_quaternion = (1, 0, 0, 0); p.scale = (1, 1, 1)
        self.update()

    # set a bone so it starts at its (parent-driven) head and points along `y` with the X axis as close to `xref`
    def aim_bone(self, n, y, xref):
        y = Vector(y).normalized()
        x = (Vector(xref) - y * Vector(xref).dot(y))
        if x.length < 1e-6:
            x = y.orthogonal()
        x.normalize(); z = x.cross(y)
        M = Matrix.Identity(4)
        M.col[0][:3] = x; M.col[1][:3] = y; M.col[2][:3] = z
        M.col[3][:3] = self.pb[n].head
        self.pb[n].matrix = M
        self.update()

    def set_matrix(self, n, M):
        self.pb[n].matrix = M
        self.update()

    def rest_x(self, n):
        return self.arm.data.bones[n].matrix_local.col[0].to_3d().normalized()

    def two_bone(self, b1, b2, target, pole, b3=None, b3_dir=None, b3_x=None):
        """two-bone IK in armature space: b1 head fixed, b2 tail reaches target, elbow/knee toward pole"""
        S = self.head(b1); T = Vector(target)
        L1 = self.bone_len(b1); L2 = self.bone_len(b2)
        d = (T - S).length
        d = max(abs(L1 - L2) + 1e-3, min(L1 + L2 - 1e-3, d))
        u = (T - S).normalized()
        a = (L1 * L1 - L2 * L2 + d * d) / (2 * d)
        h = math.sqrt(max(0.0, L1 * L1 - a * a))
        pv = Vector(pole) - u * Vector(pole).dot(u)
        if pv.length < 1e-6:
            pv = u.orthogonal()
        pv.normalize()
        E = S + u * a + pv * h
        T2 = S + u * d
        self.aim_bone(b1, E - S, pv.cross(E - S))
        self.aim_bone(b2, T2 - E, pv.cross(T2 - E))
        if b3:
            self.aim_bone(b3, b3_dir if b3_dir is not None else (T2 - E), b3_x if b3_x is not None else pv.cross(T2 - E))
        return E, T2

    def key_all(self, frame):
        for p in self.pb:
            p.keyframe_insert('location', frame=frame)
            p.keyframe_insert('rotation_quaternion', frame=frame)

    # ---------------------------------------------------------- weapons
    def attach(self, wname, bone='weapon', key=None):
        before = set(bpy.data.objects)
        bpy.ops.import_scene.gltf(filepath=os.path.join(WP, wname, wname + '.glb'))
        new = [o for o in bpy.data.objects if o not in before]
        hold = bpy.data.objects.new('Socket_%s_%s' % (wname, bone), None)
        bpy.context.scene.collection.objects.link(hold)
        for o in new:
            if o.parent is None:
                o.parent = hold
            if o.type == 'MESH':
                o.scale = (1, 1, 1)
        hold.scale = (WS * self.s,) * 3
        c = hold.constraints.new('CHILD_OF'); c.target = self.arm; c.subtarget = bone
        c.use_scale_x = c.use_scale_y = c.use_scale_z = False
        c.inverse_matrix = Matrix.Identity(4)
        piv = json.load(open(os.path.join(WP, wname, wname + '_pivot.json')))['pivot_mm']
        self.weapons[key or bone] = {'name': wname, 'objs': [o for o in new if o.type == 'MESH'], 'pivot': piv, 'hold': hold}
        return hold

    def wlocal(self, key, u, v, x=0.0):
        """weapon point given in the weapon's design mm (u forward, v up, x left) -> weapon-local metres at WS"""
        pu, pv = self.weapons[key]['pivot']
        return (W(u, v, x) - W(pu, pv, 0.0)) * WS

    def place_weapon(self, bone, grip, rot):
        """put the weapon socket so the weapon origin (grip) sits at char-space `grip` with rotation `rot` (3x3, char space)"""
        M = rot.to_4x4()
        M.translation = self.A(grip)
        self.set_matrix(bone, M)


# ------------------------------------------------------------------ collision-aware arm IK
# the wedge (rest char space, metres): main block + the googly-eye bulge on the front face
WEDGE_BOXES = [(Vector((x0, y0, z0)), Vector((x1, 0.153, z1))) for (z0, z1, x0, x1, y0) in (
    (0.575, 0.675, -0.212, 0.200, -0.112),
    (0.675, 0.725, -0.205, 0.197, -0.135),
    (0.725, 0.875, -0.196, 0.198, -0.152),
    (0.875, 0.925, -0.185, 0.196, -0.144),
    (0.925, 1.000, -0.181, 0.095, -0.112))]                   # measured slabs (rest), eye bulge included
IK_MISSES = []
ARM_R = 0.012                                     # stick radius + a hair of air


def _seg_hits_box(p0, p1, lo, hi):
    """segment vs axis-aligned box (slab test)"""
    t0, t1 = 0.0, 1.0
    d = p1 - p0
    for i in range(3):
        if abs(d[i]) < 1e-9:
            if p0[i] < lo[i] or p0[i] > hi[i]:
                return False
            continue
        a = (lo[i] - p0[i]) / d[i]; b = (hi[i] - p0[i]) / d[i]
        if a > b:
            a, b = b, a
        t0 = max(t0, a); t1 = min(t1, b)
        if t0 > t1:
            return False
    return True


def weapon_tree(rig):
    """BVH of the held weapon(s) in char space for the current pose"""
    bpy.context.view_layer.update()
    C = (rig.arm.matrix_world @ Matrix.Scale(100.0, 4)).inverted()
    verts = []; polys = []
    for w in rig.weapons.values():
        for o in w['objs']:
            M = C @ o.matrix_world; base = len(verts)
            verts += [M @ v.co for v in o.data.vertices]
            polys += [tuple(base + i for i in p.vertices) for p in o.data.polygons]
    return BVHTree.FromPolygons(verts, polys) if polys else None


def _seg_hits_tree(tree, p0, p1, r):
    """exact-ish: a hexagonal prism of radius r around the segment, overlapped against the tree"""
    d = p1 - p0
    if d.length < 1e-6:
        return False
    n = d.normalized(); a = n.orthogonal().normalized(); b = n.cross(a)
    ring = [a * (r * math.cos(k * PI / 3)) + b * (r * math.sin(k * PI / 3)) for k in range(6)]
    verts = [p0 + o for o in ring] + [p1 + o for o in ring]
    faces = [(k, (k + 1) % 6, 6 + (k + 1) % 6, 6 + k) for k in range(6)] + [tuple(range(6)), tuple(range(11, 5, -1))]
    return bool(tree.overlap(BVHTree.FromPolygons(verts, faces)))


def arm_ik(rig, side, target, pole, b3, wtree=None):
    """two-bone arm IK whose elbow swings around the shoulder->hand axis (nearest to `pole` first) until both
    sticks clear the wedge (and the held weapon, if a char-space BVH is given). target is char space."""
    up, lo = 'upperarm_' + side, 'lowerarm_' + side
    sp = rig.pb['spine_01']
    to_rest = rig.arm.data.bones['spine_01'].matrix_local @ sp.matrix.inverted()   # posed arm space -> rest arm space
    S = rig.C(to_rest @ rig.head(up)); T = rig.C(to_rest @ rig.A(target))
    L1 = rig.bone_len(up) / 100.0; L2 = rig.bone_len(lo) / 100.0
    d = max(abs(L1 - L2) + 1e-3, min(L1 + L2 - 1e-3, (T - S).length))
    u = (T - S).normalized()
    a = (L1 * L1 - L2 * L2 + d * d) / (2 * d); h = math.sqrt(max(0.0, L1 * L1 - a * a))
    p0 = to_rest.to_3x3() @ Vector(pole)
    p0 = (p0 - u * p0.dot(u)); p0 = p0.normalized() if p0.length > 1e-6 else u.orthogonal().normalized()
    back = to_rest.inverted()
    best = None; least = (99, p0)
    for k in range(0, 49):
        ang = math.radians(((k + 1) // 2) * 7.5 * (1 if k % 2 else -1))
        pv = Matrix.Rotation(ang, 3, u) @ p0
        E = S + u * a + pv * h; W = S + u * d
        Sa = S + (E - S).normalized() * 0.05             # the stick roots into the wedge side at the shoulder
        nh = sum(_seg_hits_box(q0, q1, lo_ - Vector((ARM_R,) * 3), hi_ + Vector((ARM_R,) * 3))
                 for (q0, q1) in ((Sa, E), (E, W)) for (lo_, hi_) in WEDGE_BOXES)
        if nh == 0 and wtree is not None:
            Ep, Wp, Sp = (rig.C(back @ rig.A(q)) for q in (E, W, Sa))
            Wc = Wp - (Wp - Ep).normalized() * 0.026          # the stick ends inside the hand ball, which holds the gun
            nh = 10 * (_seg_hits_tree(wtree, Sp, Ep, ARM_R) + _seg_hits_tree(wtree, Ep, Wc, ARM_R))
        if nh == 0:
            best = pv; break
        if nh < least[0]:
            least = (nh, pv)
    if best is None:
        best = least[1]
        IK_MISSES.append((side, tuple(round(c, 3) for c in target)))
    pole_posed = to_rest.inverted().to_3x3() @ best
    rig.two_bone(up, lo, rig.A(target), pole_posed, b3=b3)


# ------------------------------------------------------------------ hold definitions
def R(yaw=0.0, pitch=0.0, roll=0.0):
    """weapon orientation in char space: yaw (+ turns muzzle toward char left), pitch (+ muzzle up), roll (+ top to char right)"""
    return (Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Matrix.Rotation(math.radians(-pitch), 3, 'X') @
            Matrix.Rotation(math.radians(roll), 3, 'Y'))


HOLDS = {
    # one-handed pistol: right hand out front-right, left hand relaxed at the side
    'pistol': dict(grip=Vector((-0.25, -0.36, 0.62)), rot=dict(yaw=3, pitch=0, roll=0), support=None,
                   lhand=Vector((0.33, -0.05, 0.33)), relbow=Vector((-1, 0.3, -0.7)), lelbow=Vector((0.4, 1, -0.1))),
}

WEAPON_HOLD = {'Revolver': 'pistol', 'Derringer': 'pistol', 'SemiAuto': 'pistol', 'SnubNose': 'pistol'}


# ------------------------------------------------------------------ gait
GAIT = {
    'Idle':    dict(dir=Vector((0, 0, 0)), stride=0.0, frames=60),
    'WalkF':   dict(dir=Vector((0, -1, 0)), stride=0.10, frames=24),
    'WalkB':   dict(dir=Vector((0, 1, 0)), stride=0.08, frames=26),
    'StrafeL': dict(dir=Vector((1, 0, 0)), stride=0.05, frames=22),
    'StrafeR': dict(dir=Vector((-1, 0, 0)), stride=0.05, frames=22),
}
HIP_DROP = 0.035
LIFT = 0.045
STANCE = 0.6


def foot_offset(phase, stride, lift):
    """position of a foot along its travel line (+ = ahead in travel direction) and its lift, for gait phase 0..1"""
    if phase < STANCE:                                   # planted, sliding back under the body
        t = phase / STANCE
        return stride * (1 - 2 * t), 0.0
    t = (phase - STANCE) / (1 - STANCE)                  # swing forward
    e = 0.5 - 0.5 * math.cos(PI * t)
    return -stride + 2 * stride * e, lift * math.sin(PI * t)


def pose_frame(rig, hold, gait_name, t, extra=None):
    """t in 0..1 over the cycle. extra(rig, t) -> dict of weapon offset / overrides (fire, reload)."""
    g = GAIT[gait_name]
    rig.reset()
    moving = g['stride'] > 0
    # ---- pelvis bob / sway (two bobs per cycle while moving, slow breathing in idle)
    if moving:
        bob = -HIP_DROP - 0.012 * (0.5 + 0.5 * math.cos(4 * PI * t))
        sway = 0.008 * math.sin(2 * PI * t)
    else:
        bob = -HIP_DROP + 0.004 * math.sin(2 * PI * t)
        sway = 0.0
    side = Vector((-g['dir'].y, g['dir'].x, 0)) if moving else Vector((1, 0, 0))
    pel = rig.arm.data.bones['pelvis'].matrix_local.copy()
    pel.translation = pel.translation + rig.A(Vector((0, 0, bob)) + Vector((sway, 0, 0)))
    rig.set_matrix('pelvis', pel)
    # ---- body lean into the move direction a touch
    lean = Matrix.Identity(4)
    if moving:
        ax = Vector((0, 0, 1)).cross(g['dir']).normalized()
        lean = Matrix.Rotation(math.radians(3.5), 4, ax)
    sp = rig.pb['spine_01'].matrix.copy()
    hd = sp.translation.copy()
    sp = Matrix.Translation(hd) @ lean @ Matrix.Translation(-hd) @ sp
    rig.set_matrix('spine_01', sp)
    # ---- legs
    for side_n, sx, ph0 in (('l', 1, 0.0), ('r', -1, 0.5)):
        ph = (t + ph0) % 1.0
        off, lift = foot_offset(ph, g['stride'], LIFT) if moving else (0.0, 0.0)
        base = Vector((sx * (0.075 + 0.02 * abs(g['dir'].x)), 0, 0.045))   # strafes step a touch wider: feet never cross
        ank = base + g['dir'] * off + Vector((0, 0, lift))
        knee_pole = Vector((0, -1, 0)) if g['dir'].y <= 0 else Vector((0, -1, 0))
        toe_pitch = 0.0
        if moving and ph >= STANCE:
            toe_pitch = -12.0 * math.sin(PI * (ph - STANCE) / (1 - STANCE))
        fdir = Matrix.Rotation(math.radians(toe_pitch), 3, 'X') @ Vector((0, -1, -0.2)).normalized()
        rig.two_bone('thigh_' + side_n, 'calf_' + side_n, rig.A(ank), knee_pole, b3='foot_' + side_n, b3_dir=fdir,
                     b3_x=Vector((1, 0, 0)))
    # ---- weapon
    H = HOLDS[hold]
    grip = H['grip'].copy(); rot = dict(H['rot'])
    if moving:
        grip.z += 0.006 * math.sin(4 * PI * t + 0.6)
        grip.x += 0.004 * math.sin(2 * PI * t)
        rot['yaw'] += 1.5 * math.sin(2 * PI * t)
    else:
        grip.z += 0.003 * math.sin(2 * PI * t)
    grip.z += bob + HIP_DROP                                     # the whole upper body rides the pelvis
    lhand = H['lhand'].copy(); lhand.z += bob + HIP_DROP
    if moving:                                                   # free hand swings against the lead leg
        sw = math.sin(2 * PI * t)
        lhand += Vector((0, 0.045, 0)) * sw * (1 if g['dir'].y <= 0 else 0.6) * (0.4 if g['dir'].x else 1)
        lhand.z += 0.012 * abs(sw)
    lelbow = H['lelbow']; relbow = H['relbow']
    lspec = rspec = None
    if extra:
        e = extra(rig, t)
        grip += e.get('dgrip', Vector())
        for k, v in e.get('drot', {}).items():
            rot[k] += v
        lspec = e.get('lhand'); rspec = e.get('rhand')
        lelbow = e.get('lelbow', lelbow); relbow = e.get('relbow', relbow)
    Rm = R(**rot)
    # the hands and gun ride the spine lean (pivot at the spine head)
    piv = rig.C(hd); L3 = lean.to_3x3()
    grip = piv + L3 @ (grip - piv); Rm = L3 @ Rm
    lrest = piv + L3 @ (lhand - piv)
    rig.place_weapon('weapon', grip, Rm)
    # ---- arms
    if H['support'] is not None and lspec is None:
        lspec = ('w',) + tuple(H['support'])
    rh = hand_pos(rig, rspec, grip, Rm, grip)
    lh = hand_pos(rig, lspec, grip, Rm, lrest)
    wt = weapon_tree(rig)
    arm_ik(rig, 'r', rh, relbow, 'hand_r', wt)
    arm_ik(rig, 'l', lh, lelbow, 'hand_l', wt)
    return grip, Rm


def hand_pos(rig, spec, grip, Rm, rest):
    """hand target from a spec: None -> rest, 'grip', 'rest', ('w', u, v, x) weapon point (design mm, hand-ball centre),
    a char-space Vector, or ('mix', a, b, k)"""
    if spec is None or spec == 'rest':
        return rest
    if spec == 'grip':
        return grip
    if isinstance(spec, Vector):
        return spec
    if spec[0] == 'w':
        return grip + Rm @ rig.wlocal('weapon', *spec[1:])
    if spec[0] == 'mix':
        return hand_pos(rig, spec[1], grip, Rm, rest).lerp(hand_pos(rig, spec[2], grip, Rm, rest), spec[3])
    raise ValueError(spec)


def keyed(keys):
    """key-pose timeline -> extra(rig, t). keys: [(t, dict(dg=(x,y,z), dr=(yaw,pitch,roll), lh=spec, rh=spec,
    lel=pole, rel=pole, ease=fn))]; missing fields carry over from the previous key. Hand specs blend in place on the gun."""
    full = []; cur = dict(dg=(0, 0, 0), dr=(0, 0, 0), lh='rest', rh='grip', lel=None, rel=None)
    for t, k in keys:
        cur = dict(cur, **{a: b for a, b in k.items() if a != 'ease'}); cur['ease'] = k.get('ease', ease)
        full.append((t, cur))

    def ex(rig, t):
        i = 0
        while i < len(full) - 2 and t > full[i + 1][0]:
            i += 1
        (t0, a), (t1, b) = full[i], full[i + 1]
        k = b['ease']((t - t0) / max(1e-6, t1 - t0))
        out = {'dgrip': Vector(a['dg']).lerp(Vector(b['dg']), k),
               'drot': {n: lerp(a['dr'][j], b['dr'][j], k) for j, n in enumerate(('yaw', 'pitch', 'roll'))},
               'lhand': ('mix', a['lh'], b['lh'], k), 'rhand': ('mix', a['rh'], b['rh'], k)}
        for n in ('lel', 'rel'):
            pa, pb = a[n], b[n]
            if pa is not None or pb is not None:
                pa = Vector(pa if pa is not None else pb); pb = Vector(pb if pb is not None else pa)
                out['lelbow' if n == 'lel' else 'relbow'] = pa.normalized().lerp(pb.normalized(), k)
        return out
    return ex


def snap(t):
    """fast-out ease for flicks"""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# ------------------------------------------------------------------ fire / reload modifiers
def fire_revolver(rig, t):
    f = t * 18.0
    k = (f / 2.0) if f < 2 else math.exp(-(f - 2) / 3.2)
    k = max(0.0, min(1.0, k))
    return {'dgrip': Vector((0, 0.022 * k, 0.018 * k)), 'drot': {'pitch': 16 * k, 'yaw': -2 * k}}


# the side-mounted shoulders keep the hands >= ~0.14 m apart in front of the wedge, so the gun bridges the gap: flick it
# muzzle-up to dump the shells, the left hand takes it under the barrel while the right hand fetches rounds from the
# belt and thumbs them into the open cylinder (gun lying on its right side, cylinder up), then a flick shut.
_HAND = dict(dg=(0.16, 0.09, -0.02), dr=(88, -10, -90))           # grip (-0.09, -0.27, 0.60), muzzle to the left
_UNDER = ('w', 232, -10, -50)                                      # left palm under the barrel
reload_revolver = keyed([
    (0.00, {}),
    (0.10, dict(dg=(-0.01, 0.07, 0.03), dr=(10, 68, -40))),                                   # flick up: dump
    (0.14, dict(dg=(-0.01, 0.07, 0.045), dr=(10, 78, -44), ease=snap)),
    (0.19, dict(dg=(-0.01, 0.07, 0.03), dr=(10, 66, -40))),
    (0.30, dict(_HAND, lh=_UNDER, lel=(1, -0.5, -0.8))),                                     # into the left palm
    (0.34, dict(rh='grip')),
    (0.44, dict(rh=Vector((-0.30, -0.08, 0.45)), rel=(-1, 0.5, -0.2))),                      # right hand to the belt
    (0.48, dict()),
    (0.58, dict(rh=('w', 18, -12, 72), rel=(-0.6, -0.2, 0.8))),                               # over the cylinder
    (0.62, dict(rh=('w', 18, -12, 54), dg=(0.16, 0.09, -0.026))),                           # thumb them in
    (0.66, dict(rh=('w', 18, -12, 70), dg=(0.16, 0.09, -0.02))),
    (0.72, dict(rh='grip', rel=(-1, 0.3, -0.7))),                                            # regrip
    (0.80, dict(dg=(0.10, 0.05, 0.0), dr=(30, 4, 15), lh='rest', lel=(0.4, 1, -0.1), ease=snap)),  # flick shut
    (1.00, dict(dg=(0, 0, 0), dr=(0, 0, 0))),
])


ACTIONS = {
    'pistol': {'Fire': (18, fire_revolver), 'Reload': (78, reload_revolver)},
}


# ------------------------------------------------------------------ authoring
def bake(rig, prefix, hold, gait_name, frames, extra=None):
    name = '%s_%s' % (prefix, gait_name)
    act = bpy.data.actions.get(name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name)
    rig.arm.animation_data.action = act
    cyc = extra is None
    n = frames
    for f in range(n + 1):
        t = (f % n) / n if cyc else f / n
        pose_frame(rig, hold, gait_name if gait_name in GAIT else 'Idle', t, extra)
        rig.key_all(f + 1)
    act.use_fake_user = True
    try:
        act.frame_range = (1, n + 1)
        act.use_frame_range = True
    except Exception:
        pass
    return act


def build(cls, wname, prefix=None):
    rig = Rig(cls)
    rig.attach(wname, 'weapon')
    hold = WEAPON_HOLD[wname]
    prefix = prefix or 'TP_%s' % wname
    out = []
    for gname, g in GAIT.items():
        out.append(bake(rig, prefix, hold, gname, g['frames']))
    for an, (n, fn) in ACTIONS[hold].items():
        out.append(bake(rig, prefix, hold, an, n, extra=fn))
    return rig, out


# ------------------------------------------------------------------ clipping check
def _bvh(objs, exclude_groups=(), only_groups=None):
    dg = bpy.context.evaluated_depsgraph_get()
    verts = []; polys = []
    for o in objs:
        ev = o.evaluated_get(dg); me = ev.to_mesh()
        mw = o.matrix_world
        keep = None
        if exclude_groups or only_groups:
            gi = {g.index: g.name for g in o.vertex_groups}
            keep = set()
            for v in o.data.vertices:
                ws = {gi.get(g.group): g.weight for g in v.groups}
                top = max(ws, key=ws.get) if ws else None
                if (only_groups and top in only_groups) or (not only_groups and top not in exclude_groups):
                    keep.add(v.index)
        base = len(verts)
        verts += [mw @ v.co for v in me.vertices]
        for p in me.polygons:
            if keep is None or all(i in keep for i in p.vertices):
                polys.append(tuple(base + i for i in p.vertices))
        ev.to_mesh_clear()
    if not polys:
        return None
    t = _T()
    t.tree = BVHTree.FromPolygons(verts, polys)
    t.cents = [sum((verts[i] for i in p), Vector()) / len(p) for p in polys]
    return t


class _T:
    """BVHTree can't carry attributes: wrap it with the triangle centroids"""
    def overlap(self, other):
        return self.tree.overlap(other.tree)


def _ov(a, b, skip=None):
    """overlap pairs between two trees, ignoring pairs whose body-side triangle is inside a hand ball (a held grip)"""
    if a is None or b is None:
        return 0
    pairs = a.overlap(b)
    if not skip:
        return len(pairs)
    n = 0
    for (i, j) in pairs:
        ca, cb = a.cents[i], b.cents[j]
        if any((cb - c).length < r or (ca - c).length < r * 0.88 for (c, r) in skip):
            continue                     # contact hidden inside a hand ball (or rooted in the shoulder)
        n += 1
    return n


def check(rig, act, step=1):
    """count intersecting triangle pairs per frame: weapon vs (body minus hands), weapon vs accessories, arms vs wedge"""
    rig.arm.animation_data.action = act
    sc = bpy.context.scene
    f0, f1 = int(act.frame_range[0]), int(act.frame_range[1])
    hands = ('hand_l', 'hand_r')
    worst = []
    wobjs = [o for w in rig.weapons.values() for o in w['objs']]
    for f in range(f0, f1 + 1, step):
        sc.frame_set(f)
        wb = _bvh(wobjs)
        body = _bvh([rig.body], exclude_groups=hands)
        acc = _bvh(rig.acc) if rig.acc else None
        wedge = _bvh([rig.body], only_groups=('spine_01', 'pelvis', 'aim', 'root'))
        arms = _bvh([rig.body], only_groups=('upperarm_l', 'lowerarm_l', 'upperarm_r', 'lowerarm_r', 'hand_l', 'hand_r'))
        hats = _bvh(rig.acc, only_groups=('spine_01', 'aim')) if rig.acc else None
        legs_l = _bvh([rig.body], only_groups=('thigh_l', 'calf_l', 'foot_l'))
        legs_r = _bvh([rig.body], only_groups=('thigh_r', 'calf_r', 'foot_r'))
        mw = rig.arm.matrix_world
        k = rig.s
        skip = [(mw @ rig.arm.pose.bones[b].tail, 0.034 * k) for b in ('lowerarm_l', 'lowerarm_r')]
        c1 = _ov(wb, body, skip)
        c2 = len(wb.overlap(acc)) if (wb and acc) else 0
        sh = [(mw @ rig.arm.pose.bones[b].head, 0.05 * k) for b in ('upperarm_l', 'upperarm_r')]
        c3 = _ov(wedge, arms, sh)                       # (the arm sticks root into the wedge sides at the shoulders)
        c3 += _ov(hats, arms, sh)                       # arms through hats / face accessories count too
        c4 = len(legs_l.overlap(legs_r)) if (legs_l and legs_r) else 0
        if c1 or c2 or c3 or c4:
            worst.append((f, c1, c2, c3, c4))
    return worst


def _rest_arm_overlap(rig):
    """arm sticks are rooted inside the wedge's side faces: that contact exists at rest and is not clipping"""
    act = rig.arm.animation_data.action
    rig.arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
    wedge = _bvh([rig.body], only_groups=('spine_01', 'pelvis', 'aim', 'root'))
    arms = _bvh([rig.body], only_groups=('upperarm_l', 'lowerarm_l', 'upperarm_r', 'lowerarm_r'))
    n = len(arms.overlap(wedge)) if (arms and wedge) else 0
    rig.arm.data.pose_position = 'POSE'; bpy.context.view_layer.update()
    return n
