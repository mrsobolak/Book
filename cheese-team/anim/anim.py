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
AMMO = r"C:\Users\mrsobo\Documents\LonelyRoad\CheeseWeapons_Blender\export_ammo"
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
            if p.name.startswith('wp_'):                          # moving parts / ammo hide by scaling to ~0
                p.keyframe_insert('scale', frame=frame)

    # ---------------------------------------------------------- weapons
    def attach(self, wname, bone='weapon', key=None, part=None):
        """import a weapon GLB (or one of its parts, e.g. part='Barrels') onto a socket bone; origin = the grip"""
        before = set(bpy.data.objects)
        fn = wname + ('_' + part if part else '')
        root = WP
        if part and part.startswith('ammo:'):                       # a round from the ammo set (e.g. the loaded rocket)
            fn = wname = part[5:]; root = AMMO
        bpy.ops.import_scene.gltf(filepath=os.path.join(root, wname, fn + '.glb'))
        new = [o for o in bpy.data.objects if o not in before]
        hold = bpy.data.objects.new('Socket_%s_%s' % (fn, bone), None)
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
        piv = json.load(open(os.path.join(root, wname, wname + '_pivot.json')))['pivot_mm']
        self.weapons[key or bone] = {'name': wname, 'objs': [o for o in new if o.type == 'MESH'], 'pivot': piv, 'hold': hold}
        return hold

    def wlocal(self, key, u, v, x=0.0):
        """weapon point given in the weapon's design mm (u forward, v up, x left) -> weapon-local metres at WS"""
        pu, pv = self.weapons[key]['pivot']
        return (W(u, v, x) - W(pu, pv, 0.0)) * WS

    def place_weapon(self, bone, grip, rot, s=1.0):
        """put the weapon socket so the weapon origin (grip) sits at char-space `grip` with rotation `rot` (3x3, char space);
        s < 1 hides a part / ammo piece (bone scale, ~0 = not there)"""
        M = (rot * s).to_4x4()
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
REACH_MISSES = []                                  # frames where a hand target was out of the arm's reach (hand would float)
ARM_R = 0.0105                                    # stick radius + a hair of air


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
    for key, w in rig.weapons.items():
        if key in rig.pb and rig.pb[key].scale.x < 0.5:             # hidden part / ammo
            continue
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
    rc = r / math.cos(PI / 6)                                         # hexagon circumscribing the round tube
    ring = [a * (rc * math.cos(k * PI / 3)) + b * (rc * math.sin(k * PI / 3)) for k in range(6)]
    verts = [p0 + o for o in ring] + [p1 + o for o in ring]
    faces = [(k, (k + 1) % 6, 6 + (k + 1) % 6, 6 + k) for k in range(6)] + [tuple(range(6)), tuple(range(11, 5, -1))]
    return bool(tree.overlap(BVHTree.FromPolygons(verts, faces)))


def acc_tree_rest(rig):
    """hats / face accessories (skinned to the wedge) as a BVH in REST char space, built once per rig"""
    if getattr(rig, '_acc_rest', 'none') != 'none':
        return rig._acc_rest
    rig._acc_rest = None
    if not rig.acc:
        return None
    rig.arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
    C = (rig.arm.matrix_world @ Matrix.Scale(100.0, 4)).inverted()
    dg = bpy.context.evaluated_depsgraph_get()
    verts = []; polys = []
    for o in rig.acc:
        gi = {g.index: g.name for g in o.vertex_groups}
        ev = o.evaluated_get(dg); me = ev.to_mesh(); M = C @ o.matrix_world
        keep = set()
        for v in o.data.vertices:
            ws = {gi.get(g.group): g.weight for g in v.groups}
            if ws and max(ws, key=ws.get) in ('spine_01', 'aim'):
                keep.add(v.index)
        base = len(verts); verts += [M @ v.co for v in me.vertices]
        polys += [tuple(base + i for i in p.vertices) for p in me.polygons if all(i in keep for i in p.vertices)]
        ev.to_mesh_clear()
    rig.arm.data.pose_position = 'POSE'; bpy.context.view_layer.update()
    rig._acc_rest = BVHTree.FromPolygons(verts, polys) if polys else None
    return rig._acc_rest


def forearm_cuff(rig, side):
    """(radius, t0, t1) of whatever accessory is skinned to the forearm (spiked wristbands...), t along the forearm;
    None when the forearm is a bare stick"""
    cache = getattr(rig, '_cuff', None)
    if cache is None:
        cache = rig._cuff = {}
        rig.arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
        C = (rig.arm.matrix_world @ Matrix.Scale(100.0, 4)).inverted()
        for sd in ('l', 'r'):
            b = rig.arm.data.bones['lowerarm_' + sd]
            h = rig.C(b.head_local); t = rig.C(b.tail_local); L = (t - h).length; ax = (t - h) / L
            r = 0.0; ts = []
            for o in rig.acc:
                gi = {g.index: g.name for g in o.vertex_groups}; M = C @ o.matrix_world
                for v in o.data.vertices:
                    ws = {gi.get(g.group): g.weight for g in v.groups}
                    if ws and max(ws, key=ws.get) == 'lowerarm_' + sd:
                        p = M @ v.co - h; a = p.dot(ax)
                        r = max(r, (p - ax * a).length + 0.002); ts.append(a / L)
            cache[sd] = (r, max(0.0, min(ts) - 0.02), min(1.0, max(ts) + 0.02)) if ts else None
        rig.arm.data.pose_position = 'POSE'; bpy.context.view_layer.update()
    return cache[side]


def wedge_tree_rest(rig, groups=('spine_01', 'aim')):
    """body parts (by dominant group) as a BVH in REST char space, cached per rig + group set"""
    cache = getattr(rig, '_wedge_rest', None)
    if cache is None:
        cache = rig._wedge_rest = {}
    if groups in cache:
        return cache[groups]
    rig.arm.data.pose_position = 'REST'; bpy.context.view_layer.update()
    C = (rig.arm.matrix_world @ Matrix.Scale(100.0, 4)).inverted()
    dg = bpy.context.evaluated_depsgraph_get()
    o = rig.body; gi = {g.index: g.name for g in o.vertex_groups}
    ev = o.evaluated_get(dg); me = ev.to_mesh(); M = C @ o.matrix_world
    keep = set()
    for v in o.data.vertices:
        ws = {gi.get(g.group): g.weight for g in v.groups}
        if ws and max(ws, key=ws.get) in groups:
            keep.add(v.index)
    verts = [M @ v.co for v in me.vertices]
    polys = [tuple(p.vertices) for p in me.polygons if all(i in keep for i in p.vertices)]
    ev.to_mesh_clear()
    rig.arm.data.pose_position = 'POSE'; bpy.context.view_layer.update()
    cache[groups] = BVHTree.FromPolygons(verts, polys) if polys else None
    return cache[groups]


def arm_ik(rig, side, target, pole, b3, wtree=None):
    """two-bone arm IK whose elbow swings around the shoulder->hand axis (nearest to `pole` first) until both
    sticks clear the wedge (and the held weapon, if a char-space BVH is given). target is char space."""
    up, lo = 'upperarm_' + side, 'lowerarm_' + side
    sp = rig.pb['spine_01']
    to_rest = rig.arm.data.bones['spine_01'].matrix_local @ sp.matrix.inverted()   # posed arm space -> rest arm space
    S = rig.C(to_rest @ rig.head(up)); T = rig.C(to_rest @ rig.A(target))
    L1 = rig.bone_len(up) / 100.0; L2 = rig.bone_len(lo) / 100.0
    if (T - S).length > L1 + L2 - 1e-3:
        REACH_MISSES.append((side, round((T - S).length - (L1 + L2), 3)))
    d = max(abs(L1 - L2) + 1e-3, min(L1 + L2 - 1e-3, (T - S).length))
    u = (T - S).normalized()
    a = (L1 * L1 - L2 * L2 + d * d) / (2 * d); h = math.sqrt(max(0.0, L1 * L1 - a * a))
    p0 = to_rest.to_3x3() @ Vector(pole)
    p0 = (p0 - u * p0.dot(u)); p0 = p0.normalized() if p0.length > 1e-6 else u.orthogonal().normalized()
    back = to_rest.inverted()
    pel_rest = rig.arm.data.bones['pelvis'].matrix_local @ rig.pb['pelvis'].matrix.inverted()
    best = None; least = (99, p0)
    cands = [Matrix.Rotation(math.radians(((k + 1) // 2) * 7.5 * (1 if k % 2 else -1)), 3, u) @ p0 for k in range(49)]
    last = getattr(rig, '_last_pole', {}).get(side)                # hysteresis: keep last frame's elbow while it's clean
    if last is not None:                                          # and not far from the wanted pole (no twitching)
        lp = last - u * last.dot(u)
        if lp.length > 1e-4 and lp.normalized().dot(p0) > 0.35:
            cands.insert(0, lp.normalized())
    for pv in cands:
        E = S + u * a + pv * h; W = S + u * d
        Sa = S + (E - S).normalized() * 0.05             # the stick roots into the wedge side at the shoulder
        wtr = wedge_tree_rest(rig)
        nh = _seg_hits_tree(wtr, Sa, E, ARM_R) + _seg_hits_tree(wtr, E, W, ARM_R)
        ptr = wedge_tree_rest(rig, ('pelvis', 'root'))
        if nh == 0 and ptr is not None:                           # the pelvis doesn't twist: test it in its own frame
            Pp = [rig.C(pel_rest @ back @ rig.A(q)) for q in (Sa, E, W)]
            nh = _seg_hits_tree(ptr, Pp[0], Pp[1], ARM_R) + _seg_hits_tree(ptr, Pp[1], Pp[2], ARM_R)
        atree = acc_tree_rest(rig)
        if nh == 0 and atree is not None:
            nh = 5 * (_seg_hits_tree(atree, Sa, E, ARM_R) + _seg_hits_tree(atree, E, W, ARM_R))
        if nh == 0 and wtree is not None:
            Ep, Wp, Sp = (rig.C(back @ rig.A(q)) for q in (E, W, Sa))
            Wc = Wp - (Wp - Ep).normalized() * 0.026          # the stick ends inside the hand ball, which holds the gun
            nh = 10 * (_seg_hits_tree(wtree, Sp, Ep, ARM_R) + _seg_hits_tree(wtree, Ep, Wc, ARM_R))
            cuff = forearm_cuff(rig, side)
            if nh == 0 and cuff:
                nh = 10 * _seg_hits_tree(wtree, Ep.lerp(Wp, cuff[1]), Ep.lerp(Wp, cuff[2]), cuff[0])
        if nh == 0:
            best = pv; break
        if nh < least[0]:
            least = (nh, pv)
    if best is None:                                              # no clean elbow in the fast model: let the real meshes decide
        best = _mesh_pick(rig, side, target, b3, to_rest, u, p0, least[1])
        if best is None:
            IK_MISSES.append((side, tuple(round(c, 3) for c in target)))
            best = least[1]
    if not hasattr(rig, '_last_pole'):
        rig._last_pole = {}
    rig._last_pole[side] = best.copy()
    pole_posed = to_rest.inverted().to_3x3() @ best
    rig.two_bone(up, lo, rig.A(target), pole_posed, b3=b3)


def _arm_hits(rig, side):
    """actual posed-mesh overlaps of one arm (stick + hand) with the wedge, hats and the held gun"""
    mw = rig.arm.matrix_world; k = rig.s
    groups = ('upperarm_' + side, 'lowerarm_' + side, 'hand_' + side)
    arm = _bvh([rig.body], only_groups=groups)
    wedge = _bvh([rig.body], only_groups=('spine_01', 'pelvis', 'aim', 'root'))
    sh = [(mw @ rig.arm.pose.bones['upperarm_' + side].head, 0.05 * k)]
    hs = [(mw @ rig.arm.pose.bones['lowerarm_' + side].tail, 0.034 * k)]
    n = _ov(wedge, arm, sh)
    if rig.acc:
        n += _ov(_bvh(rig.acc, only_groups=('spine_01', 'aim')), arm, sh)
    wobjs = [o for key, w in rig.weapons.items() if rig.pb[key].scale.x >= 0.5 for o in w['objs']]
    if wobjs:
        n += _ov(_bvh(wobjs), _bvh([rig.body], only_groups=groups[:2]), hs)
    return n


def _mesh_pick(rig, side, target, b3, to_rest, u, p0, fallback):
    up, lo = 'upperarm_' + side, 'lowerarm_' + side
    inv = to_rest.inverted().to_3x3(); best = (10 ** 9, None)
    last = getattr(rig, '_last_pole', {}).get(side)               # temporal coherence: no single-frame elbow flips
    if last is not None and (last - u * last.dot(u)).length > 1e-4:
        p0 = (last - u * last.dot(u)).normalized()
    for k in range(0, 24):
        ang = math.radians(((k + 1) // 2) * 15.0 * (1 if k % 2 else -1))
        pv = Matrix.Rotation(ang, 3, u) @ p0
        rig.two_bone(up, lo, rig.A(target), inv @ pv, b3=b3)
        n = _arm_hits(rig, side)
        if n == 0:
            return pv
        if n < best[0]:
            best = (n, pv)
    return None


# ------------------------------------------------------------------ hold definitions
def R(yaw=0.0, pitch=0.0, roll=0.0):
    """weapon orientation in char space: yaw (+ turns muzzle toward char left), pitch (+ muzzle up), roll (+ top to char left,
    so the gun's right side comes up)"""
    return (Matrix.Rotation(math.radians(yaw), 3, 'Z') @ Matrix.Rotation(math.radians(-pitch), 3, 'X') @
            Matrix.Rotation(math.radians(roll), 3, 'Y'))


# holds are authored in BODY space (the wedge frame after the stance twist); see pose_frame
HOLDS = {
    # arms 1.8x (classes/arms.py): every hold keeps the hand at a natural reach (an arm is never folded up with the
    # elbow poking out sideways) and the elbows hang down / out
    # one-handed pistol: arm out in front at shoulder height, left arm hanging relaxed
    'pistol': dict(twist=0, grip=Vector((-0.16, -0.56, 0.70)), rot=dict(yaw=3, pitch=0, roll=0),
                   lhand=Vector((0.30, -0.10, 0.30)), relbow=Vector((-0.7, 0.1, -1)), lelbow=Vector((0.5, 0.6, -0.2))),
    # two pistols, mirrored
    'dual': dict(twist=0, grip=Vector((-0.17, -0.54, 0.68)), rot=dict(yaw=3, pitch=0, roll=0),
                 grip2=Vector((0.17, -0.54, 0.68)), rot2=dict(yaw=-3, pitch=0, roll=0),
                 relbow=Vector((-0.7, 0.1, -1)), lelbow=Vector((0.7, 0.1, -1))),
    # long guns: body faces forward, gun low in front, support arm across under the face (nat2 reach solver)
    'rifle': dict(twist=0, grip=Vector((-0.06, -0.37, 0.54)), rot=dict(yaw=0, pitch=0, roll=0),
                  relbow=Vector((-0.8, 0.2, -1)), lelbow=Vector((0.6, -0.1, -1))),
    # minigun at the hip: right hand on the rear grip, left hand on the top carry bar
    'heavy': dict(twist=0, sway=0.5, grip=Vector((-0.08, -0.30, 0.36)), rot=dict(yaw=0, pitch=0, roll=0),
                  relbow=Vector((-1, 0.3, -0.5)), lelbow=Vector((1, -0.2, -0.7))),
    # launcher on the right shoulder, beside the head
    'shoulder': dict(twist=0, sway=0.6, grip=Vector((-0.34, -0.30, 0.70)), rot=dict(yaw=0, pitch=2, roll=0),
                     relbow=Vector((-0.6, 0.2, -1)), lelbow=Vector((0.4, -0.4, -1))),
    # clipboard: held by its right edge, face tilted up toward the eyes (and the over-the-shoulder camera)
    'board': dict(twist=0, grip=Vector((-0.14, -0.40, 0.52)), rot=dict(yaw=180, pitch=35, roll=0),
                  lhand=Vector((0.30, -0.10, 0.30)), relbow=Vector((-0.7, 0.1, -1)), lelbow=Vector((0.5, 0.6, -0.2))),
}

# ------------------------------------------------------------------ gait
GAIT = {
    'Idle':    dict(dir=Vector((0, 0, 0)), stride=0.0, frames=60),
    'WalkF':   dict(dir=Vector((0, -1, 0)), stride=0.10, frames=12),
    'WalkB':   dict(dir=Vector((0, 1, 0)), stride=0.08, frames=13),
    'StrafeL': dict(dir=Vector((1, 0, 0)), stride=0.05, frames=11),
    'StrafeR': dict(dir=Vector((-1, 0, 0)), stride=0.05, frames=11),
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
        lean = Matrix.Rotation(math.radians(3.5 * (hold.get('sway', 1.0) if isinstance(hold, dict) else 1.0)), 4, ax)
    hd = rig.pb['spine_01'].matrix.translation.copy()
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
    # ---- weapon(s)
    H = hold if isinstance(hold, dict) else HOLDS[hold]
    grip = H['grip'].copy(); rot = dict(H['rot'])
    two = 'grip2' in H
    if two:
        grip2 = H['grip2'].copy(); rot2 = dict(H['rot2'])
    if moving:
        sw_k = H.get('sway', 1.0)
        bobv = Vector((0.004 * math.sin(2 * PI * t), 0, 0.006 * math.sin(4 * PI * t + 0.6))) * sw_k
        grip += bobv; rot['yaw'] += 1.5 * sw_k * math.sin(2 * PI * t)
        if two:
            grip2 += Vector((-bobv.x, 0, 0.006 * math.sin(4 * PI * t + 2.2))); rot2['yaw'] -= 1.5 * math.sin(2 * PI * t)
    else:
        grip.z += 0.003 * math.sin(2 * PI * t)
        if two:
            grip2.z += 0.003 * math.sin(2 * PI * t + 1.3)
    up = Vector((0, 0, bob + HIP_DROP))                              # the whole upper body rides the pelvis
    grip += up
    if two:
        grip2 += up
    lhand = H.get('lhand', Vector((0.33, -0.05, 0.33))).copy() + up
    if moving and not two and H.get('support') is None:            # free hand swings against the lead leg
        sw = math.sin(2 * PI * t)
        lhand += Vector((0, 0.045, 0)) * sw * (1 if g['dir'].y <= 0 else 0.6) * (0.4 if g['dir'].x else 1)
        lhand.z += 0.012 * abs(sw)
    lelbow = H['lelbow']; relbow = H['relbow']
    lspec = rspec = None; twist = H.get('twist', 0.0); dgun = dgun2 = None; lback = 0.0; spin = 0.0
    if extra:
        e = extra(rig, t)
        grip += e.get('dgrip', Vector())
        for k, v in e.get('drot', {}).items():
            rot[k] += v
        if two:
            grip2 += e.get('dgrip2', Vector())
            for k, v in e.get('drot2', {}).items():
                rot2[k] += v
        twist += e.get('dtwist', 0.0); lback = e.get('dlean', 0.0); spin = e.get('spin', 0.0)
        dgun = e.get('dgun'); dgun2 = e.get('dgun2')
        lspec = e.get('lhand'); rspec = e.get('rhand')
        def _pole(v, dflt):
            if isinstance(v, tuple) and v and v[0] == 'pole':
                pa = Vector(v[1] if v[1] is not None else dflt).normalized()
                pb = Vector(v[2] if v[2] is not None else dflt).normalized()
                return pa.lerp(pb, v[3])
            return v
        lelbow = _pole(e.get('lelbow', lelbow), H['lelbow']); relbow = _pole(e.get('relbow', relbow), H['relbow'])
    # ---- body: stance twist + lean about the spine head; body-space targets ride it
    Bm = lean @ Matrix.Rotation(math.radians(twist), 4, 'Z') @ Matrix.Rotation(math.radians(-lback), 4, 'X')
    sp = Matrix.Translation(hd) @ Bm @ Matrix.Translation(-hd) @ rig.pb['spine_01'].matrix
    rig.set_matrix('spine_01', sp)
    piv = rig.C(hd); B3 = Bm.to_3x3()
    body = lambda p: piv + B3 @ (p - piv)
    ctx = {'B3': B3, 'parts': {}, 'pdef': H.get('pdef', {})}

    def put(key, grip_b, rot_d):
        Rw = B3 @ R(**rot_d); gw = body(grip_b)
        hp = H.get('hold_pt2' if key == 'wp_01' else 'hold_pt')
        org = gw - Rw @ rig.wlocal(key, *hp) if hp else gw          # hold the gun somewhere other than its pivot
        rig.place_weapon(key, org, Rw)
        ctx[key] = (org, Rw, gw)
    if dgun is not None:
        grip = grip + R(**rot) @ dgun                                   # recoil along the gun's own axes
    put('weapon', grip, rot)
    if 'wp_02' in rig.weapons and 'wp_02' not in ctx['pdef']:      # spinning part (minigun barrels) about the bore axis
        org, Rw, _ = ctx['weapon']
        P0 = rig.wlocal('weapon', 0.0, 0.0, 0.0); Rs = Matrix.Rotation(math.radians(spin), 3, 'Y')
        rig.place_weapon('wp_02', org + Rw @ (P0 - Rs @ P0), Rw @ Rs)
    if two:
        if dgun2 is not None:
            grip2 = grip2 + R(**rot2) @ dgun2
        put('wp_01', grip2, rot2)
    lrest = body(lhand)
    pspecs = e.get('parts', {}) if extra else {}
    place_parts(rig, ctx, pspecs)                                   # parts on the gun first: hands may grab them
    # ---- arms
    ldef = 'grip2' if two else (('w',) + tuple(H['support']) if H.get('support') else 'rest')
    rh = hand_pos(rig, rspec, ctx, ctx['weapon'][2], 'grip')
    lh = hand_pos(rig, lspec, ctx, lrest, ldef)
    if 'wp_03' in rig.weapons and 'wp_03' not in ctx['pdef']:      # the launcher's rocket: loaded / in the hand / spent
        place_rocket(rig, ctx, lh, e.get('rocket') if extra else None)
    place_parts(rig, ctx, pspecs, {'l': lh, 'r': rh})                # then whatever is held in a hand
    wt = weapon_tree(rig)
    arm_ik(rig, 'r', rh, relbow, 'hand_r', wt)
    arm_ik(rig, 'l', lh, lelbow, 'hand_l', wt)
    return ctx


ROCKET_SEAT = 510.0          # launcher u (mm) of the rocket's base when loaded: warhead sticks out of the muzzle
ROCKET_GRIP = 690.0          # rocket u (mm) the hand holds (the nose cap)
ROCKET_SPENT = -360.0        # fired: pushed back deep inside the tube (out of sight; the game spawns the projectile)


def place_rocket(rig, ctx, lh, spec):
    """spec: None / ('tube', du) seated at ROCKET_SEAT + du along the tube, or ('hand', k): held by the nose in the left
    hand, k=0 carried tail-forward, k=1 lined up with the tube (ready to slide in)"""
    org, Rw, _ = ctx['weapon']
    state, k = spec if spec else ('tube', 0.0)
    if state == 'tube':
        Rr = Rw; o = org + Rw @ rig.wlocal('weapon', ROCKET_SEAT + k, 0.0, 0.0)
    else:
        Rr = R(yaw=180).to_quaternion().slerp(Rw.to_quaternion(), max(0.0, min(1.0, k))).to_matrix()
        o = lh - Rr @ rig.wlocal('wp_03', ROCKET_GRIP, 0.0, 0.0)
    rig.place_weapon('wp_03', o, Rr)


# ------------------------------------------------------------------ moving parts / ammo in the hands
# Split weapon parts (cylinder, mag, bolt, lever, slide, pump, ...) share the gun's origin, so "at rest" = placed exactly like
# the gun. Ammo pieces have their origin at the base, nose along +u. A part spec says where a socket bone is this frame:
#   ('g', key, pivot_uvx, axis, deg, d_uvx)  split part moved on gun `key`: turned `deg` about design axis u/v/x through
#                                            the pivot (design mm), then slid by d (design mm)
#   ('at', key, pos_uvx, ypr)                piece sitting at a point of gun `key`, rotated (yaw, pitch, roll) gun-relative
#   ('on', bone, pos_uvx, ypr)               piece riding another part (pos in that part's design mm)
#   ('h', side, grab_uvx, ypr, key)          held in hand 'l' / 'r' by its own point grab; ypr gun-relative (key) or body
#   ('c', pos, ypr)                          free in char space (falling / lying on the floor)
#   ('hide', spec)                           same place, scaled to ~0 (not there yet / gone)
AXES = {'u': Vector((0, -1, 0)), 'v': Vector((0, 0, 1)), 'x': Vector((1, 0, 0))}


def G(piv=(0, 0, 0), ax='u', deg=0.0, d=(0, 0, 0), key='weapon'):
    return ('g', key, piv, ax, deg, d)


def AT(pos, ypr=(0, 0, 0), key='weapon'):
    return ('at', key, pos, ypr)


def ON(bone, pos, ypr=(0, 0, 0)):
    return ('on', bone, pos, ypr)


def HAND(side, grab=(0, 0, 0), ypr=(0, 0, 0), key='weapon'):
    return ('h', side, grab, ypr, key)


def FREE(pos, ypr=(0, 0, 0)):
    return ('c', Vector(pos), ypr)


def HID(spec):
    return ('hide', spec)


def DROP(spec, off=(0, 0, 0), ypr=(0, 0, 0), mid=(0, 0, 0)):
    """spec moved by a char-space offset and turned (ypr) about its own point `mid`: tumbling / falling pieces"""
    return ('drop', spec, off, ypr, mid)


def fall(t):
    t = max(0.0, min(1.0, t))
    return t * t


REST = G()


def part_xf(rig, ctx, bone, spec, hands=None):
    """(origin, 3x3, scale) of a part bone in char space, or None while it needs hand positions that aren't known yet"""
    if spec is None:
        spec = ctx['pdef'].get(bone, REST)
    k = spec[0]
    if k == 'mix':
        sa = spec[1] if spec[1] is not None else ctx['pdef'].get(bone, REST)
        sb = spec[2] if spec[2] is not None else ctx['pdef'].get(bone, REST)
        if sa[0] == sb[0] == 'g' and sa[1:4] == sb[1:4]:            # same hinge: blend the angle (spins past 180 deg)
            t = spec[3]
            return part_xf(rig, ctx, bone, ('g', sa[1], sa[2], sa[3], lerp(sa[4], sb[4], t),
                                            tuple(lerp(p, q, t) for p, q in zip(sa[5], sb[5]))), hands)
        a = part_xf(rig, ctx, bone, sa, hands); b = part_xf(rig, ctx, bone, sb, hands)
        if a is None or b is None:
            return None
        t = spec[3]
        return (a[0].lerp(b[0], t), a[1].to_quaternion().slerp(b[1].to_quaternion(), t).to_matrix(), lerp(a[2], b[2], t))
    if k == 'hide':
        x = part_xf(rig, ctx, bone, spec[1], hands)
        return None if x is None else (x[0], x[1], 1e-3)
    if k == 'drop':                                                 # spec, moved by a char-space offset + extra turn
        x = part_xf(rig, ctx, bone, spec[1], hands)
        if x is None:
            return None
        Rr = R(*spec[3]) @ x[1]
        mid = x[0] + x[1] @ rig.wlocal(bone, *spec[4]) + Vector(spec[2])   # turns about the piece's own middle
        mid.z = max(mid.z, 0.012)                                    # lands on the floor, not through it
        return (mid - Rr @ rig.wlocal(bone, *spec[4]), Rr, x[2])
    if k == 'g':
        _, key, piv, ax, deg, d = spec
        org, Rw, _ = ctx[key]
        P = rig.wlocal(bone, *piv); Rs = Matrix.Rotation(math.radians(deg), 3, AXES[ax])
        return (org + Rw @ (P - Rs @ P + W(*d) * WS), Rw @ Rs, 1.0)
    o0 = None
    if k == 'at':
        _, key, pos, ypr = spec
        org, Rw, _ = ctx[key]
        Rr = Rw @ R(*ypr); o0 = org + Rw @ rig.wlocal(key, *pos)
    elif k == 'on':
        _, pb, pos, ypr = spec
        if pb not in ctx['parts']:
            return None
        po, pR, _ = ctx['parts'][pb]
        Rr = pR @ R(*ypr); o0 = po + pR @ rig.wlocal(pb, *pos)
    elif k == 'h':
        if hands is None:
            return None
        _, side, grab, ypr, key = spec
        Rr = (ctx[key][1] if key else ctx['B3']) @ R(*ypr)
        return (hands[side] - Rr @ rig.wlocal(bone, *grab), Rr, 1.0)
    elif k == 'c':
        _, pos, ypr = spec
        Rr = R(*ypr); o0 = Vector(pos)
    else:
        raise ValueError(spec)
    return (o0 - Rr @ rig.wlocal(bone, 0.0, 0.0, 0.0), Rr, 1.0)


def place_parts(rig, ctx, specs, hands=None):
    """place every part bone that can be placed now (parts riding parts resolve in a few passes)"""
    for _ in range(3):
        for b in ctx['pdef']:
            if b in ctx['parts']:
                continue
            x = part_xf(rig, ctx, b, specs.get(b), hands)
            if x is not None:
                ctx['parts'][b] = x
                rig.place_weapon(b, *x)


def hand_pos(rig, spec, ctx, rest, default='rest'):
    """hand target from a spec: None/'rest', 'grip' / 'grip2' (the held point of gun 1 / 2), ('w', u, v, x) /
    ('w2', u, v, x) a point on gun 1 / 2 (design mm, hand-ball centre), a char-space Vector, or ('mix', a, b, k)"""
    if spec is None:
        spec = default
    if spec == 'rest':
        return rest
    if spec == 'grip':
        return ctx['weapon'][2]
    if spec == 'grip2':
        return ctx['wp_01'][2]
    if isinstance(spec, Vector):
        return spec
    if spec[0] in ('w', 'w2'):
        key = 'weapon' if spec[0] == 'w' else 'wp_01'
        org, Rw, _ = ctx[key]
        return org + Rw @ rig.wlocal(key, *spec[1:])
    if spec[0] == 'mix':
        return hand_pos(rig, spec[1], ctx, rest, default).lerp(hand_pos(rig, spec[2], ctx, rest, default), spec[3])
    if spec[0] == 'p':                                              # a point on a moving part (bolt knob, lever loop, ...)
        o, Rp, _ = ctx['parts'][spec[1]]
        return o + Rp @ rig.wlocal(spec[1], *spec[2:])
    raise ValueError(spec)


def keyed(keys):
    """key-pose timeline -> extra(rig, t). keys: [(t, dict(dg=(x,y,z), dr=(yaw,pitch,roll), lh=spec, rh=spec,
    lel=pole, rel=pole, ease=fn))]; missing fields carry over from the previous key. Hand specs blend in place on the gun."""
    full = []; cur = dict(dg=(0, 0, 0), dr=(0, 0, 0), dg2=(0, 0, 0), dr2=(0, 0, 0), tw=0.0, lb=0.0, lh=None, rh='grip',
                          lel=None, rel=None, rk=None, pt={})
    for t, k in keys:
        pt = dict(cur['pt'], **k.get('pt', {}))
        cur = dict(cur, **{a: b for a, b in k.items() if a not in ('ease', 'pt')}); cur['ease'] = k.get('ease', ease)
        cur['pt'] = pt
        full.append((t, cur))

    def ex(rig, t):
        i = 0
        while i < len(full) - 2 and t > full[i + 1][0]:
            i += 1
        (t0, a), (t1, b) = full[i], full[i + 1]
        k = b['ease']((t - t0) / max(1e-6, t1 - t0))
        out = {'dgrip': Vector(a['dg']).lerp(Vector(b['dg']), k),
               'drot': {n: lerp(a['dr'][j], b['dr'][j], k) for j, n in enumerate(('yaw', 'pitch', 'roll'))},
               'dgrip2': Vector(a['dg2']).lerp(Vector(b['dg2']), k),
               'drot2': {n: lerp(a['dr2'][j], b['dr2'][j], k) for j, n in enumerate(('yaw', 'pitch', 'roll'))},
               'dtwist': lerp(a['tw'], b['tw'], k), 'dlean': lerp(a['lb'], b['lb'], k),
               'rhand': ('mix', a['rh'], b['rh'], k)}
        if a['lh'] is not None or b['lh'] is not None:
            out['lhand'] = ('mix', a['lh'], b['lh'], k)
        if b['rk'] is not None:
            ra, rb = a['rk'] or b['rk'], b['rk']
            out['rocket'] = (rb[0], lerp(ra[1], rb[1], k)) if ra[0] == rb[0] else rb
        for n in ('lel', 'rel'):
            if a[n] is not None or b[n] is not None:                     # None = the hold's own pole (resolved later)
                out['lelbow' if n == 'lel' else 'relbow'] = ('pole', a[n], b[n], k)
        if a['pt'] or b['pt']:
            out['parts'] = {bn: ('mix', a['pt'].get(bn), b['pt'].get(bn), k) for bn in set(a['pt']) | set(b['pt'])}
        return out
    return ex


def snap(t):
    """fast-out ease for flicks"""
    t = max(0.0, min(1.0, t))
    return 1 - (1 - t) ** 3


# ------------------------------------------------------------------ fire / reload modifiers
def _pulse(f, shots, decay):
    k = 0.0
    for s0 in shots:
        ff = f - s0
        if ff >= 0:
            k = max(k, ff / 1.5 if ff < 1.5 else math.exp(-(ff - 1.5) / decay))
    return min(1.0, k)


def kick(n, back=0.022, up=0.012, pitch=16.0, yaw=-2.0, decay=3.2, shots=(0,), guns=(1,), stagger=0, body=0.0, turn=0.0):
    """recoil: snaps back along the barrel and muzzle-up, settles exponentially. guns=(1,2) kicks both (stagger frames).
    body: the whole wedge rocks back (deg), turn: and twists toward the gun that fired (deg)."""
    def ex(rig, t):
        f = t * n; out = {'dlean': 0.0, 'dtwist': 0.0}
        for gi in guns:
            k = _pulse(f - (stagger if gi == 2 else 0), shots, decay)
            sfx = '' if gi == 1 else '2'
            out['dgun' + sfx] = Vector((0, back * k, up * k))
            out['drot' + sfx] = {'pitch': pitch * k, 'yaw': yaw * k * (1 if gi == 1 else -1)}
            out['dlean'] += body * k
            out['dtwist'] += turn * k * (-1 if gi == 1 else 1)
        return out
    return ex


def combo(*fns):
    """sum several modifiers (vectors and angles add, the last one that sets a hand wins)"""
    def ex(rig, t):
        out = {}
        for fn in fns:
            for k, v in fn(rig, t).items():
                if k in ('dgrip', 'dgrip2', 'dgun', 'dgun2'):
                    out[k] = out.get(k, Vector()) + v
                elif k in ('drot', 'drot2'):
                    d = dict(out.get(k, {}))
                    for a, b in v.items():
                        d[a] = d.get(a, 0.0) + b
                    out[k] = d
                elif k == 'rocket':
                    out[k] = v
                elif k == 'parts':
                    out[k] = dict(out.get(k, {}), **v)
                elif k in ('dtwist', 'dlean', 'spin'):
                    out[k] = out.get(k, 0.0) + v
                else:
                    out[k] = v
        return out
    return ex


def tracks(keys):
    """key-pose timeline where every channel interpolates between ITS OWN keys (a channel not named at a key keeps
    moving toward its next key). Same channels as keyed() plus pt={bone: part spec}; repeat a value to hold it.
    A channel starts at its rest value at t=0 unless keyed there."""
    rest = dict(dg=(0, 0, 0), dr=(0, 0, 0), dg2=(0, 0, 0), dr2=(0, 0, 0), tw=0.0, lb=0.0, lh=None, rh='grip',
                lel=None, rel=None, rk=None)
    ch = {}
    for t, k in sorted(keys, key=lambda x: x[0]):
        e = k.get('ease', ease)
        for n, v in k.items():
            if n == 'ease':
                continue
            for name, val in (((('pt', b), sp) for b, sp in v.items()) if n == 'pt' else ((n, v),)):
                lst = ch.setdefault(name, [])
                if not lst and t > 0:
                    lst.append((0.0, rest.get(name) if isinstance(name, str) else None, ease))
                lst.append((t, val, e))

    def at(lst, t):
        if t <= lst[0][0]:
            return lst[0][1], lst[0][1], 0.0
        for (t0, a, _), (t1, b, e) in zip(lst, lst[1:]):
            if t <= t1:
                return a, b, e((t - t0) / max(1e-6, t1 - t0))
        return lst[-1][1], lst[-1][1], 1.0

    def ex(rig, t):
        out = {}
        for name, lst in ch.items():
            a, b, k = at(lst, t)
            if isinstance(name, tuple):
                out.setdefault('parts', {})[name[1]] = ('mix', a, b, k)
            elif name in ('dg', 'dg2'):
                out['dgrip' + name[2:]] = Vector(a).lerp(Vector(b), k)
            elif name in ('dr', 'dr2'):
                out['drot' + name[2:]] = {n: lerp(a[j], b[j], k) for j, n in enumerate(('yaw', 'pitch', 'roll'))}
            elif name in ('tw', 'lb'):
                out['dtwist' if name == 'tw' else 'dlean'] = lerp(a, b, k)
            elif name == 'rh':
                out['rhand'] = ('mix', a, b, k)
            elif name == 'lh':
                if a is not None or b is not None:
                    out['lhand'] = ('mix', a, b, k)
            elif name in ('lel', 'rel'):
                if a is not None or b is not None:
                    out['lelbow' if name == 'lel' else 'relbow'] = ('pole', a, b, k)
            elif name == 'rk':
                if b is not None:
                    ra = a or b
                    out['rocket'] = (b[0], lerp(ra[1], b[1], k)) if ra[0] == b[0] else b
        return out
    return ex


def _show(bone, t, spec, hidden_before=None):
    """a piece pops into existence at t (hidden just before, at the same place unless told otherwise)"""
    return [(t - 0.004, dict(pt={bone: HID(hidden_before or spec)})), (t, dict(pt={bone: spec}))]


def _gone(bone, t, spec):
    return [(t, dict(pt={bone: spec})), (t + 0.004, dict(pt={bone: HID(spec)}))]


def _eject(bone, seat, out, t0, t1, t2, off=(-0.04, 0.03, -0.8), ypr=(70, 160, 40), mid=(16, 0, 0), ease_out=ease):
    """spent case: there (inside the gun) from t0, pulled out to `out` by t1, falls to the floor by t2, gone"""
    land = DROP(out, off, ypr, mid)
    return (_show(bone, t0, seat) + [(t1, dict(pt={bone: out}, ease=ease_out)),
                                     (t1 + 0.004, dict(pt={bone: DROP(out, (0, 0, 0), (0, 0, 0), mid)})),
                                     (t2, dict(pt={bone: land}, ease=fall))] + _gone(bone, t2 + 0.03, land))


# shared reload spots (body space, arms 1.8x): pouches on the hips, the work spot in front of the chest
BELT_L = Vector((0.26, -0.14, 0.40))
BELT_R = Vector((-0.26, -0.14, 0.40))
LEL = (1, -0.3, -0.7)                                                # left elbow out and down for front work
LEL_BELT = (0.6, 0.5, -0.3)
REL_BELT = (-0.6, 0.5, -0.3)
REL_T = None                                                         # (None = the hold's own elbow pole)
_RW = (0.08, 0.20, -0.15)                                            # pistol grip -> (-0.08, -0.36, 0.55), close to the chest


def shake(n, amp=0.004, ang=1.5, cycles=4, guns=(1,)):
    """seamless looping fire tremble (autos / minigun)"""
    def ex(rig, t):
        w = 2 * PI * cycles * t; out = {}
        for gi in guns:
            sfx = '' if gi == 1 else '2'
            out['dgun' + sfx] = Vector((amp * 0.4 * math.sin(w * 1.7), amp * (0.6 + 0.4 * math.sin(w)), amp * 0.5 * math.sin(w + 1.1)))
            out['drot' + sfx] = {'pitch': ang * (0.5 + 0.5 * math.sin(w + 0.4)), 'yaw': ang * 0.3 * math.sin(w * 1.3)}
        return out
    return ex


# ---- revolver (single action): gate open, half-cock, punch out two empties with the ejector rod, thumb in two rounds
# from the left pouch, gate shut, spin. Gun on its left side (gate up), right hand keeps the grip.
REV_SEAT = AT((1, -14, -14)); REV_OUT = AT((-40, -14, -14)); REV_LINE = AT((-44, -14, -14))
REV_GRAB = (-8, 0, -40)                                              # hand centre in round coords: behind it, gate side
_cyl = lambda a: {'wp_04': G((0, -14, 0), 'u', a)}
_gate = lambda a: {'wp_02': G((-3.6, -22, -14.85), 'u', a)}
_rod = lambda du: {'wp_03': G(d=(du, 0, 0))}


def _rev_round(bone, t_show, t_line, t_seat):
    return (_show(bone, t_show, HAND('l', REV_GRAB)) +
            [(t_line, dict(pt={bone: REV_LINE}, lh=('w', -44 - 8, -14, -54), lel=LEL)),
             (t_seat, dict(pt={bone: REV_SEAT}, lh=('w', 1 - 8, -14, -54)))] + _gone(bone, t_seat + 0.004, REV_SEAT))


reload_revolver = tracks([
    (0.00, dict(pt=dict(_gate(0), **_cyl(0), **_rod(0)))),
    (0.10, dict(dg=_RW, dr=(10, 30, 75), lh=('w', -3.6, -8, -58), lel=LEL)),
    (0.11, dict(pt=_gate(0))),
    (0.15, dict(pt=_gate(100), lh=('w', -3.6, -30, -62), ease=snap)),                       # flick the gate open
    (0.16, dict(pt=_cyl(0))), (0.19, dict(pt=_cyl(30))),                                   # half-cock: chamber at the gate
    (0.21, dict(lh=('w', 186, -8.6, -40), pt=_rod(0))),
    (0.25, dict(lh=('w', 140, -8.6, -40), pt=_rod(-46))), (0.29, dict(lh=('w', 186, -8.6, -40), pt=_rod(0))),
    (0.30, dict(pt=_cyl(30))), (0.33, dict(pt=_cyl(90))),
    (0.34, dict(lh=('w', 186, -8.6, -40), pt=_rod(0))),
    (0.38, dict(lh=('w', 140, -8.6, -40), pt=_rod(-46))), (0.42, dict(lh=('w', 186, -8.6, -40), pt=_rod(0))),
    (0.43, dict(pt=_cyl(90))), (0.46, dict(pt=_cyl(150))),
    (0.44, dict(dr=(10, 30, 75))),
    (0.50, dict(dr=(10, -15, 75), lh=BELT_L, lel=LEL_BELT)),                                 # muzzle down, hand at the pouch
    (0.52, dict(lh=BELT_L)),
    (0.65, dict(pt=_cyl(150))), (0.68, dict(pt=_cyl(210))),
    (0.70, dict(lh=BELT_L, lel=LEL_BELT)), (0.72, dict(lh=BELT_L)),
    (0.86, dict(pt=_cyl(210), lh=('w', -3.6, -30, -62), lel=LEL)),
    (0.88, dict(pt=_gate(100))), (0.91, dict(pt=_gate(0), lh=('w', -3.6, -6, -58), ease=snap)),   # gate shut
    (0.92, dict(pt=_cyl(210))), (0.97, dict(pt=_cyl(600), ease=snap)),                      # spin it (ends on a chamber)
    (0.94, dict(dg=_RW, dr=(10, -15, 75), lh=None, lel=None)),
    (1.00, dict(dg=(0, 0, 0), dr=(0, 0, 0))),
] + _eject('wp_05', REV_SEAT, REV_OUT, 0.21, 0.25, 0.40)
  + _eject('wp_06', REV_SEAT, REV_OUT, 0.34, 0.38, 0.52, off=(-0.02, 0.05, -0.8), ypr=(-40, 140, 70))
  + _rev_round('wp_07', 0.53, 0.60, 0.64) + _rev_round('wp_08', 0.73, 0.80, 0.84))
fire_revolver = combo(kick(18, 0.022, 0.012, 16), tracks([(0.0, dict(pt=_cyl(0))), (0.12, dict(pt=_cyl(60), ease=snap))]))


# ---- derringer: thumb the lever, tip the barrels up, pull both empties, two rounds in, snap shut
_dbar = lambda a: {'wp_02': G((0.5, 14.5, 0), 'x', a)}
_dlev = lambda a: {'wp_03': G((-1.5, 4.0, -8.9), 'x', a)}
DER_SEAT = (ON('wp_02', (2, 6.2, 0)), ON('wp_02', (2, -6.7, 0)))
DER_OUT = (ON('wp_02', (-28, 6.2, 0)), ON('wp_02', (-28, -6.7, 0)))
DER_LINE = (ON('wp_02', (-36, 6.2, 0)), ON('wp_02', (-36, -6.7, 0)))
DER_GRAB = ((-30, -6.2, 40), (-30, 6.7, 40))                          # one hand carries both rounds side by side
reload_derringer = tracks([
    (0.00, dict(pt=dict(_dbar(0), **_dlev(0)))),
    (0.10, dict(dg=_RW, dr=(50, 10, 0), pt=_dlev(0))),
    (0.14, dict(pt=_dlev(-90), ease=snap)),                                                # thumb the lever round
    (0.16, dict(lh=('w', 70, -26, 0), lel=LEL, pt=_dbar(0))),
    (0.22, dict(lh=('p', 'wp_02', 70, -26, 0), pt=_dbar(-55))),                            # tip the barrels up
    (0.26, dict(lh=('p', 'wp_02', -30, 0, 40))),
    (0.32, dict(lh=('p', 'wp_02', -58, 0, 40))),                                           # pull the empties
    (0.40, dict(lh=BELT_L, lel=LEL_BELT)), (0.44, dict(lh=BELT_L)),
    (0.56, dict(lh=('p', 'wp_02', -66, 0, 40), lel=LEL)),
    (0.62, dict(lh=('p', 'wp_02', -28, 0, 40))),                                           # both rounds in
    (0.66, dict(lh=('p', 'wp_02', 40, 40, 0), pt=_dbar(-55))),
    (0.72, dict(lh=('w', 40, 40, 0), pt=_dbar(0), ease=snap)),                             # snap shut
    (0.74, dict(pt=_dlev(-90))), (0.78, dict(pt=_dlev(0))),
    (0.82, dict(lh=None, lel=None, dg=_RW, dr=(50, 10, 0))),
    (0.94, dict(dg=(0, 0, 0), dr=(0, 0, 0))),
] + _eject('wp_04', DER_SEAT[0], DER_OUT[0], 0.24, 0.32, 0.46, mid=(14, 0, 0))
  + _eject('wp_05', DER_SEAT[1], DER_OUT[1], 0.24, 0.32, 0.47, off=(-0.01, 0.05, -0.8), ypr=(-60, 120, 20), mid=(14, 0, 0))
  + [kv for i, b in enumerate(('wp_06', 'wp_07')) for kv in
     _show(b, 0.45, HAND('l', DER_GRAB[i])) + [(0.56, dict(pt={b: DER_LINE[i]})), (0.62, dict(pt={b: DER_SEAT[i]}))]
     + _gone(b, 0.63, DER_SEAT[i])])


# ---- snub-nose: cylinder swings out, muzzle up, slap the ejector (five empties fall), speedloader in, twist, close
_scyl = lambda a: {'wp_02': G((0, -31, 13), 'u', a)}
SN_SEAT = ON('wp_02', (0.3, -12, 0)); SN_OUT = ON('wp_02', (-34, -12, 0)); SN_LINE = ON('wp_02', (-32, -12, 0))
SL_GRAB = (-62, 0, 0)                                                # hand centre behind the knob
reload_snubnose = tracks([
    (0.00, dict(pt=_scyl(0))),
    (0.10, dict(dg=_RW, dr=(20, 10, -70), lh=('w', 18, -12, 52), lel=LEL)),
    (0.11, dict(pt=_scyl(0))),
    (0.16, dict(pt=_scyl(-100), lh=('p', 'wp_02', 18, -12, 52))),                          # swing it out
    (0.21, dict(dr=(20, 60, -70), lh=('p', 'wp_02', 74, -12, 0))),                         # muzzle up
    (0.26, dict(lh=('p', 'wp_02', 52, -12, 0), ease=snap)),                                # slap the ejector
    (0.32, dict(dr=(20, -30, -70))),                                                       # muzzle down to load
    (0.40, dict(lh=BELT_L, lel=LEL_BELT)), (0.44, dict(lh=BELT_L)),
    (0.56, dict(lh=('p', 'wp_02', -32 - 62, -12, 0), lel=LEL)),
    (0.62, dict(lh=('p', 'wp_02', 0.3 - 62, -12, 0))),                                     # speedloader home
    (0.66, dict(lh=('p', 'wp_02', 0.3 - 62, -12, 0))),
    (0.70, dict(lh=('p', 'wp_02', -110, -12, 0), pt=_scyl(-100))),                          # pull it off
    (0.76, dict(pt=_scyl(0), dr=(10, -10, -20), ease=snap)),                               # flick the cylinder shut
    (0.78, dict(lh=BELT_L, lel=LEL_BELT)),
    (0.86, dict(lh=None, lel=None, dg=_RW, dr=(10, -10, -20))),
    (0.96, dict(dg=(0, 0, 0), dr=(0, 0, 0))),
] + _eject('wp_03', SN_SEAT, SN_OUT, 0.22, 0.26, 0.38, mid=(-14, 0, 0), ease_out=snap)
  + _show('wp_04', 0.45, HAND('l', SL_GRAB)) + _show('wp_05', 0.45, HAND('l', SL_GRAB))
  + [(0.56, dict(pt={'wp_04': SN_LINE, 'wp_05': SN_LINE})), (0.62, dict(pt={'wp_04': SN_SEAT, 'wp_05': SN_SEAT})),
     (0.66, dict(pt={'wp_04': ON('wp_02', (0.3, -12, 0), (0, 0, 25))})),
     (0.70, dict(pt={'wp_04': HAND('l', SL_GRAB, (0, 0, 25))})), (0.78, dict(pt={'wp_04': HAND('l', SL_GRAB, (0, 0, 25))}))]
  + _gone('wp_04', 0.79, HAND('l', SL_GRAB, (0, 0, 25))) + _gone('wp_05', 0.84, SN_SEAT))
fire_snubnose = combo(kick(16, 0.024, 0.014, 20, decay=2.8), tracks([(0.0, dict(pt=_scyl(0))), (0.14, dict(pt=_scyl(72), ease=snap))]))


# ---- semi-auto: slide locked back on the empty mag, mag drops, fresh one from the pouch, slide release
def _magd(k):                                                        # down the grip's rake
    return (-0.089 * k, -0.996 * k, 0.0)


SA_GRAB = (-27.6, -149, 0)                                           # palm under the baseplate
_sl = lambda du: {'wp_03': G(d=(du, 0, 0))}
_SA_FALL = DROP(G(d=_magd(120)), (0.02, -0.03, -0.7), (40, 70, 90), (-24, -60, 0))
reload_semiauto = tracks([
    (0.00, dict(pt=_sl(0))), (0.04, dict(pt=_sl(-40), ease=snap)),                        # locked open (empty)
    (0.10, dict(dg=_RW, dr=(25, 15, 0))),
    (0.12, dict(pt={'wp_02': G()})), (0.17, dict(pt={'wp_02': G(d=_magd(120))}, ease=fall)),  # mag drops free
    (0.175, dict(pt={'wp_02': DROP(G(d=_magd(120)), (0, 0, 0), (0, 0, 0), (-24, -60, 0))})),
    (0.32, dict(pt={'wp_02': _SA_FALL}, ease=fall)), (0.324, dict(pt={'wp_02': HID(_SA_FALL)})),
    (0.60, dict(pt={'wp_02': HID(G())})),
    (0.14, dict(lh=BELT_L, lel=LEL_BELT)), (0.20, dict(lh=BELT_L)),
    (0.32, dict(lh=('w', SA_GRAB[0] - 6.2, SA_GRAB[1] - 69.7, 0), lel=LEL, pt={'wp_04': G(d=_magd(70))})),
    (0.38, dict(lh=('w', *SA_GRAB), pt={'wp_04': G()}, ease=snap)),                        # seat it
    (0.42, dict(pt=_sl(-40))), (0.45, dict(pt=_sl(0), ease=snap)),                         # slide release
    (0.44, dict(lh=('w', *SA_GRAB))),
    (0.54, dict(lh=None, lel=None)),
    (0.62, dict(dg=_RW, dr=(25, 15, 0))),
    (0.76, dict(dg=(0, 0, 0), dr=(0, 0, 0))),
] + _show('wp_04', 0.204, HAND('l', SA_GRAB)))
fire_semiauto = combo(kick(10, 0.016, 0.008, 10, decay=1.8), tracks([(0.0, dict(pt=_sl(0))), (0.1, dict(pt=_sl(-40), ease=snap)),
                                                                     (0.3, dict(pt=_sl(0)))]))


# ---- machine pistol: long mag drops, new one up the grip, rack the top charging knob
MP_GRAB = (32, -310, 0)
_ch = lambda du: {'wp_03': G(d=(du, 0, 0))}
_MP_FALL = DROP(G(d=(0, -175, 0)), (0.02, -0.03, -0.62), (30, 80, 70), (32, -180, 0))
reload_mpistol = tracks([
    (0.10, dict(dg=_RW, dr=(25, 15, 0))),
    (0.12, dict(pt={'wp_02': G()})), (0.17, dict(pt={'wp_02': G(d=(0, -175, 0))}, ease=fall)),
    (0.175, dict(pt={'wp_02': DROP(G(d=(0, -175, 0)), (0, 0, 0), (0, 0, 0), (32, -180, 0))})),
    (0.32, dict(pt={'wp_02': _MP_FALL}, ease=fall)), (0.324, dict(pt={'wp_02': HID(_MP_FALL)})),
    (0.60, dict(pt={'wp_02': HID(G())})),
    (0.14, dict(lh=BELT_L, lel=LEL_BELT)), (0.20, dict(lh=BELT_L)),
    (0.32, dict(lh=('w', 32, -310 - 90, 0), lel=LEL, pt={'wp_04': G(d=(0, -90, 0))})),
    (0.38, dict(lh=('w', *MP_GRAB), pt={'wp_04': G()}, ease=snap)),
    (0.46, dict(lh=('p', 'wp_03', 70, 100, 0), pt=_ch(0))),                                 # hand on the charging knob
    (0.52, dict(lh=('p', 'wp_03', 70, 100, 0), pt=_ch(-40))),
    (0.55, dict(pt=_ch(0), lh=('w', 40, 110, 0), ease=snap)),                              # let it fly
    (0.64, dict(lh=None, lel=None)),
    (0.66, dict(dg=_RW, dr=(25, 15, 0))),
    (0.80, dict(dg=(0, 0, 0), dr=(0, 0, 0))),
] + _show('wp_04', 0.204, HAND('l', MP_GRAB)))
fire_mpistol = combo(kick(18, 0.012, 0.006, 6, 1.0, decay=1.6, shots=(0, 3, 6)),
                     tracks([(0.0, dict(pt=_ch(0)))] + [kv for s in (0, 3, 6) for kv in
                            ((s / 18 + 0.02, dict(pt=_ch(0))), ((s + 1) / 18, dict(pt=_ch(-30), ease=snap)), ((s + 2) / 18, dict(pt=_ch(0))))]))


# ---- dual sawed-offs: right-left double blast, each rocks the body back and toward that gun, muzzles climb hard
fire_dual = kick(30, 0.045, 0.020, 34, 3.0, decay=3.4, guns=(1, 2), stagger=5, body=5.0, turn=4.0)

# ---- dual sawed-offs (pump): one gun tucked in the waistband while the free hand feeds a shell up the loading port
# and racks the pump, then the other gun
SO_LINE = (118, -44, 0); SO_IN = (128, -24.5, 0); SO_HOME = (168, -24.5, 0)
SO_GRAB = (-10, -40, 0)                                              # hand behind / under the shell base
_TUCK_L = dict(dg2=(-0.04, 0.36, -0.12), dr2=(0, -80, 0))            # gun 2 down the left waistband
_TUCK_R = dict(dg=(0.04, 0.36, -0.12), dr=(0, -80, 0))
_LOAD_1 = dict(dg=(0.09, 0.16, -0.10), dr=(20, 10, 150))             # gun 1 upside down-ish in front: port up
_LOAD_2 = dict(dg2=(-0.09, 0.16, -0.10), dr2=(-20, 10, -150))
_pump = lambda du, b=('wp_02', 'wp_03'), key='weapon': {b[0]: G(d=(du, 0, 0), key=key), b[1]: G(d=(du * 44 / 60, 0, 0), key=key)}


def _shell(t_show, side, t_line, t_in, t_home, key):
    w = 'w' if key == 'weapon' else 'w2'
    hk = 'lh' if side == 'l' else 'rh'
    return (_show('wp_06', t_show, HAND(side, SO_GRAB, key=key)) +
            [(t_line, {'pt': {'wp_06': AT(SO_LINE, (0, 20, 0), key)}, hk: (w, SO_LINE[0] - 10, SO_LINE[1] - 40, 0)}),
             (t_in, {'pt': {'wp_06': AT(SO_IN, key=key)}, hk: (w, SO_IN[0] - 10, SO_IN[1] - 40, 0)}),
             (t_home, {'pt': {'wp_06': AT(SO_HOME, key=key)}, hk: (w, SO_HOME[0] - 10, SO_HOME[1] - 40, 0)})]
            + _gone('wp_06', t_home + 0.002, AT(SO_HOME, key=key)))


reload_dual = tracks([
    (0.00, dict(pt=dict(_pump(0), **_pump(0, ('wp_04', 'wp_05'), 'wp_01')))),
    (0.08, dict(_TUCK_L)), (0.48, dict(_TUCK_L)),
    (0.12, dict(_LOAD_1, lh=BELT_L, lel=LEL_BELT)), (0.15, dict(lh=BELT_L)),
    (0.34, dict(dr=(20, 10, 150))), (0.38, dict(dr=(10, 0, 0), lh=('p', 'wp_02', 242, -70, 0), lel=LEL)),
    (0.39, dict(pt=_pump(0))), (0.42, dict(pt=_pump(-60), ease=snap)), (0.46, dict(pt=_pump(0), ease=snap)),   # rack
    (0.47, dict(lh=('p', 'wp_02', 242, -70, 0))),
    (0.50, dict(lh='grip2', lel=None, dg=(0.09, 0.16, -0.10), dr=(10, 0, 0))),
    (0.54, dict(_TUCK_R)), (0.90, dict(_TUCK_R)),
    (0.56, dict(_LOAD_2)), (0.92, dict(dg2=_LOAD_2['dg2'])),
    (0.57, dict(rh='grip', rel=None)), (0.60, dict(rh=BELT_R, rel=REL_BELT)), (0.63, dict(rh=BELT_R)),
    (0.80, dict(dr2=(-20, 10, -150))), (0.84, dict(dr2=(-10, 0, 0), rh=('p', 'wp_04', 242, -70, 0), rel=(-1, -0.3, -0.7))),
    (0.85, dict(pt=_pump(0, ('wp_04', 'wp_05'), 'wp_01'))), (0.88, dict(pt=_pump(-60, ('wp_04', 'wp_05'), 'wp_01'), ease=snap)),
    (0.91, dict(pt=_pump(0, ('wp_04', 'wp_05'), 'wp_01'), ease=snap)),
    (0.92, dict(rh=('p', 'wp_04', 242, -70, 0))), (0.95, dict(rh='grip', rel=None)),
    (1.00, dict(dg=(0, 0, 0), dr=(0, 0, 0), dg2=(0, 0, 0), dr2=(0, 0, 0))),
] + _shell(0.16, 'l', 0.24, 0.28, 0.32, 'weapon') + _shell(0.64, 'r', 0.71, 0.75, 0.79, 'wp_01'))


# ---- bolt rifle: boom, then lift-back-forward-down on the bolt (empty flips out the port); reload two rounds down
# into the open action from the right hip pouch
_bolt = lambda deg, du: {'wp_02': G((0, 8, 0), 'u', deg, (du, 0, 0))}
KNOB = ('p', 'wp_02', -60, -10, -90)


def _cycle(t0, t1, casing=True):
    d = (t1 - t0) / 6
    k = [(t0, dict(rh='grip', pt=_bolt(0, 0))), (t0 + d, dict(rh=KNOB, rel=(-1, 0.3, -0.4), pt=_bolt(0, 0))),
         (t0 + 2 * d, dict(pt=_bolt(-80, 0))), (t0 + 3 * d, dict(pt=_bolt(-80, -75))),
         (t0 + 4 * d, dict(pt=_bolt(-80, 0))), (t0 + 5 * d, dict(pt=_bolt(0, 0), rh=KNOB)), (t1, dict(rh='grip', rel=REL_T))]
    if casing:                                                       # rides the bolt back, kicked out the right
        out = AT((-3, 8, 0)); fly = DROP(out, (-0.10, 0.02, 0.06), (0, 60, 20), (30, 0, 0))
        land = DROP(out, (-0.16, 0.10, -0.8), (40, 170, 60), (30, 0, 0))
        k += _show('wp_03', t0 + d, ON('wp_02', (72, 8, 0))) + [
            (t0 + 3 * d, dict(pt={'wp_03': ON('wp_02', (72, 8, 0))})), (t0 + 3 * d + 0.004, dict(pt={'wp_03': out})),
            (t0 + 3.6 * d, dict(pt={'wp_03': fly}, ease=snap)), (t0 + 3.6 * d + 0.2, dict(pt={'wp_03': land}, ease=fall))
        ] + _gone('wp_03', t0 + 3.6 * d + 0.21, land)
    return k


fire_bolt = combo(kick(40, 0.03, 0.012, 9, 1.0, decay=3.0, body=3.0), tracks(_cycle(0.24, 0.80)))
aimfire_bolt = combo(kick(40, 0.0, 0.004, 7, 1.0, decay=3.0, body=5.0), tracks(_cycle(0.24, 0.80)))
BR_GRAB = (30, 20, -45)                                              # fingers on the round's right side (under the scope)


def _bolt_round(bone, t_show, t_line, t_in):
    return (_show(bone, t_show, HAND('r', BR_GRAB)) +
            [(t_line, dict(pt={bone: AT((-5, 30, -16))}, rh=('w', 25, 50, -61), rel=(-1, 0.2, 0.2))),
             (t_in, dict(pt={bone: AT((-5, 10, 0))}, rh=('w', 25, 30, -45)))] + _gone(bone, t_in + 0.004, AT((-5, 10, 0))))


reload_bolt = tracks(_cycle(0.0, 0.30, casing=False)[:4] + [
    (0.22, dict(rh=KNOB)), (0.26, dict(rh=BELT_R, rel=REL_BELT)), (0.30, dict(rh=BELT_R)),
    (0.46, dict(rh=('w', 25, 50, -61))), (0.48, dict(rh=BELT_R, rel=REL_BELT)), (0.52, dict(rh=BELT_R)),
    (0.70, dict(rh=('w', 25, 50, -61), rel=(-1, 0.2, 0.2))), (0.74, dict(rh=KNOB, rel=(-1, 0.3, -0.4), pt=_bolt(-80, -75))),
    (0.80, dict(pt=_bolt(-80, 0))), (0.86, dict(pt=_bolt(0, 0), rh=KNOB)), (0.94, dict(rh='grip', rel=REL_T)),
] + _bolt_round('wp_04', 0.31, 0.38, 0.43) + _bolt_round('wp_05', 0.53, 0.60, 0.65))


# ---- lever rifle: boom, lever down (empty pops out the top) and up; reload thumbs two rounds into the side gate
_lev = lambda a: {'wp_02': G((92, -23, 0), 'x', a)}
LOOP = ('p', 'wp_02', 4, -58, 0)


def _lever(t0, t1, casing=True):
    d = (t1 - t0) / 4
    k = [(t0, dict(rh='grip', pt=_lev(0))), (t0 + d, dict(rh=LOOP, rel=(-1, 0.3, 0.0), pt=_lev(0))),
         (t0 + 2 * d, dict(pt=_lev(-50), dr=(0, -4, 0))), (t0 + 3 * d, dict(pt=_lev(0), dr=(0, 0, 0), rh=LOOP)),
         (t1, dict(rh='grip', rel=REL_T))]
    if casing:
        top = AT((40, 26, 0)); fly = DROP(top, (-0.04, 0.06, 0.14), (0, 90, 30), (25, 0, 0))
        land = DROP(top, (-0.12, 0.16, -0.75), (60, 200, 40), (25, 0, 0))
        k += _show('wp_03', t0 + d, AT((100, 4, 0))) + [
            (t0 + 1.5 * d, dict(pt={'wp_03': AT((100, 4, 0))})), (t0 + 2 * d, dict(pt={'wp_03': top})),
            (t0 + 2 * d + 0.06, dict(pt={'wp_03': fly}, ease=snap)), (t0 + 2 * d + 0.26, dict(pt={'wp_03': land}, ease=fall))
        ] + _gone('wp_03', t0 + 2 * d + 0.27, land)
    return k


fire_lever = combo(kick(32, 0.028, 0.012, 10, 1.0, decay=2.8, body=2.5), tracks(_lever(0.28, 0.80)))
aimfire_lever = combo(kick(32, 0.0, 0.004, 8, 1.0, decay=2.8, body=4.5), tracks(_lever(0.28, 0.80)))
LV_GRAB = (-30, 0, -35)                                              # thumb behind the round's base


def _gate_round(bone, t_show, t_line, t_in):
    return (_show(bone, t_show, HAND('r', LV_GRAB)) +
            [(t_line, dict(pt={bone: AT((30, -2, -18))}, rh=('w', 0, -2, -53))),
             (t_in, dict(pt={bone: AT((64, -2, -12))}, rh=('w', 34, -2, -47)))] + _gone(bone, t_in + 0.004, AT((64, -2, -12))))


reload_lever = tracks([
    (0.08, dict(dr=(0, 0, 40))), (0.60, dict(dr=(0, 0, 40))),                               # roll the gate up
    (0.10, dict(rh='grip', rel=REL_T)), (0.14, dict(rh=BELT_R, rel=REL_BELT)), (0.18, dict(rh=BELT_R)),
    (0.34, dict(rh=('w', 34, -2, -60), rel=(-1, 0.3, 0.0))), (0.38, dict(rh=BELT_R, rel=REL_BELT)), (0.42, dict(rh=BELT_R)),
    (0.58, dict(rh=('w', 34, -2, -60), rel=(-1, 0.3, 0.0))),
    (0.66, dict(dr=(0, 0, 0), rh='grip', rel=REL_T)),
] + _gate_round('wp_04', 0.19, 0.26, 0.31) + _gate_round('wp_05', 0.43, 0.50, 0.55) + _lever(0.66, 0.96, casing=False))


# ---- SMG: roll the side mag down, strip it and toss it, new one from the pouch, rack the cocking handle
SMG_GRAB = (140, 55, 140)                                            # palm on the mag (top side once it hangs down)
_ck = lambda du: {'wp_03': G(d=(du, 0, 0))}
_SMG_FALL = DROP(G(d=(0, 0, 200)), (0.05, -0.04, -0.5), (60, 30, 80), (140, 0, 125))
reload_smg = tracks([
    (0.10, dict(dr=(0, 4, 90), lh=('w', *SMG_GRAB), lel=LEL)),
    (0.12, dict(pt={'wp_02': G()})),
    (0.17, dict(pt={'wp_02': G(d=(0, 0, 200))}, lh=('w', SMG_GRAB[0], SMG_GRAB[1], SMG_GRAB[2] + 200), ease=snap)),  # strip it
    (0.174, dict(pt={'wp_02': DROP(G(d=(0, 0, 200)), (0, 0, 0), (0, 0, 0), (140, 0, 125))})),
    (0.32, dict(pt={'wp_02': _SMG_FALL}, ease=fall)), (0.324, dict(pt={'wp_02': HID(_SMG_FALL)})),
    (0.62, dict(pt={'wp_02': HID(G())})),
    (0.24, dict(lh=BELT_L, lel=LEL_BELT)), (0.28, dict(lh=BELT_L)),
    (0.40, dict(lh=('w', SMG_GRAB[0], SMG_GRAB[1], SMG_GRAB[2] + 90), lel=LEL, pt={'wp_04': G(d=(0, 0, 90))})),
    (0.46, dict(lh=('w', *SMG_GRAB), pt={'wp_04': G()}, ease=snap)),                       # seat it
    (0.48, dict(dr=(0, 4, 90))),
    (0.56, dict(dr=(0, 0, 0), lh=('w', 112, 0, -82))),
    (0.58, dict(lh=('p', 'wp_03', 112, 0, -82), pt=_ck(0))),
    (0.64, dict(lh=('p', 'wp_03', 112, 0, -82), pt=_ck(-80))),                             # rack it
    (0.67, dict(pt=_ck(0), lh=('w', 70, 0, -82), ease=snap)),
    (0.80, dict(lh=None, lel=None)),
] + _show('wp_04', 0.284, HAND('l', SMG_GRAB)))
fire_smg = combo(shake(12, 0.003, 1.2, 4), tracks([(0.0, dict(pt=_ck(0)))] + [kv for s in range(4) for kv in
                 ((s / 4 + 0.02, dict(pt=_ck(0))), (s / 4 + 1 / 12, dict(pt=_ck(-45), ease=snap)), (s / 4 + 2 / 12, dict(pt=_ck(0))))]
                 + [(1.0, dict(pt=_ck(0)))]))


# ---- minigun: barrels spin while firing (6 barrels: 300 deg per 12-frame loop = a seamless 25 deg/frame), light buzz
def spin_fire(n, per_frame=25.0):
    buzz = shake(n, 0.0015, 0.4, 6)
    def ex(rig, t):
        out = buzz(rig, t); out['spin'] = per_frame * n * t
        return out
    return ex

# ---- rocket launcher: shoulder-fired; reload = bring it down across the belly (muzzle left), rocket in, back up
fire_launcher = combo(kick(30, 0.045, 0.012, 7, 0.0, decay=5.0, body=6.0),
                      keyed([(0.0, dict(rk=('tube', 0.0))), (0.02, dict(rk=('tube', ROCKET_SPENT), ease=snap)), (1.0, {})]))
_BELLY = dict(dg=(0.24, 0.0, -0.27), dr=(90, -2, 0))                 # grip (-0.10, -0.30, 0.43), tube across the front
SPENT = ('tube', ROCKET_SPENT)
reload_launcher = keyed([
    (0.00, dict(rk=SPENT)),
    (0.05, dict(lh=Vector((0.44, -0.32, 0.58)), lel=(1, 0.2, -0.6))),                         # let go: out to the side first
    (0.12, dict(lh='rest', lel=(0.4, 1, -0.1))),
    (0.22, dict(_BELLY)),
    (0.34, dict(lh=BELT_L, lel=(0.6, 0.5, -0.3))),                                            # hand at the belt pouch
    (0.35, dict(rk=('hand', 0.0))),                                                           # rocket out, held by the nose
    (0.44, dict(lh=Vector((0.40, -0.40, 0.48)), lel=(1, -0.3, -0.6), rk=('hand', 0.3))),     # tail swings round
    (0.52, dict(lh=('w', ROCKET_SEAT + ROCKET_GRIP + 60, 0, 0), rk=('hand', 1.0))),          # lined up, tail in the tube
    (0.60, dict(lh=('w', ROCKET_SEAT + ROCKET_GRIP, 0, 0), dg=(0.25, 0.0, -0.27), ease=snap)),  # shove it home
    (0.61, dict(rk=('tube', 0.0))),
    (0.66, dict(lh=('w', ROCKET_SEAT + ROCKET_GRIP + 50, -20, 0), dg=(0.24, 0.0, -0.27))),
    (0.71, dict(lh=Vector((0.46, -0.34, 0.46)), lel=(1, 0.2, -0.6))),
    (0.78, dict(lh='rest', lel=(0.4, 1, -0.1))),
    (0.90, dict(dg=(0, 0, 0), dr=(0, 0, 0))),
    (1.00, dict(lh=None, lel=None)),
])

# ---- blueprint: present it (fire), flip the page (reload)
fire_board = keyed([(0.0, {}), (0.30, dict(dg=(0.0, -0.07, 0.02), dr=(0, -20, 0), ease=snap)),
                    (0.45, dict()), (1.0, dict(dg=(0, 0, 0), dr=(0, 0, 0)))])
reload_board = keyed([
    (0.00, {}),
    (0.16, dict(lh=('w', 24, 150, -150), lel=(1, -0.3, -0.6))),                               # top-left corner
    (0.40, dict(lh=('w', 70, 175, -80), dr=(0, 6, 0))),                                       # curl the page up and over
    (0.60, dict(lh=('w', 24, 120, -150), dr=(0, 0, 0))),                                      # smooth it down
    (0.80, dict(lh=None)),
    (1.00, {}),
])


# per weapon: hold (+ overrides), fire = (frames, modifier, loop), reload = (frames, modifier) or None,
# parts = (part, bone[, default spec]): split moving parts ('Cylinder' -> <W>_Cylinder.glb) and ammo ('ammo:Ammo45_Round')
_HID = HID(AT((0, 0, 0)))                                            # ammo waits hidden inside the gun hand
WDEF = {
    'Revolver':  dict(hold='pistol', fire=(18, fire_revolver, False), reload=(114, reload_revolver),
                      parts=(('Gate', 'wp_02', REST), ('Rod', 'wp_03', REST), ('Cylinder', 'wp_04', REST),
                             ('ammo:Ammo45_Casing', 'wp_05', _HID), ('ammo:Ammo45_Casing', 'wp_06', _HID),
                             ('ammo:Ammo45_Round', 'wp_07', _HID), ('ammo:Ammo45_Round', 'wp_08', _HID))),
    'Derringer': dict(hold='pistol', fire=(16, kick(16, 0.026, 0.014, 24, decay=2.6), False), reload=(84, reload_derringer),
                      parts=(('Barrels', 'wp_02', REST), ('Lever', 'wp_03', REST),
                             ('ammo:Ammo38_Casing', 'wp_04', _HID), ('ammo:Ammo38_Casing', 'wp_05', _HID),
                             ('ammo:Ammo38_Round', 'wp_06', _HID), ('ammo:Ammo38_Round', 'wp_07', _HID))),
    'SnubNose':  dict(hold='pistol', fire=(16, fire_snubnose, False), reload=(96, reload_snubnose),
                      parts=(('Cylinder', 'wp_02', REST), ('ammo:Casings38', 'wp_03', _HID),
                             ('ammo:Speedloader38', 'wp_04', _HID), ('ammo:Speedloader38_Rounds', 'wp_05', _HID))),
    'SemiAuto':  dict(hold='pistol', fire=(10, fire_semiauto, False), reload=(66, reload_semiauto),
                      parts=(('Mag', 'wp_02', REST), ('Slide', 'wp_03', REST), ('Mag', 'wp_04', HID(REST)))),
    'MachinePistol': dict(hold='pistol', fire=(18, fire_mpistol, False), reload=(72, reload_mpistol),
                          parts=(('Mag', 'wp_02', REST), ('Charger', 'wp_03', REST), ('Mag', 'wp_04', HID(REST)))),
    'SawedOff':  dict(hold='dual', dual=True, fire=(30, fire_dual, False), reload=(150, reload_dual),
                      parts=(('Pump', 'wp_02', REST), ('Bolt', 'wp_03', REST), ('Pump', 'wp_04', G(key='wp_01')),
                             ('Bolt', 'wp_05', G(key='wp_01')), ('ammo:Shotgun12_Shell', 'wp_06', _HID))),
    'BoltRifle': dict(hold='rifle', over=dict(support=(180, -27, 0)), aim=Vector((-0.07, -0.40, 0.67)), aimfire=aimfire_bolt,
                      fire=(40, fire_bolt, False), reload=(90, reload_bolt),
                      parts=(('Bolt', 'wp_02', REST), ('ammo:Ammo3006_Casing', 'wp_03', _HID),
                             ('ammo:Ammo3006_Round', 'wp_04', _HID), ('ammo:Ammo3006_Round', 'wp_05', _HID))),
    'LeverRifle': dict(hold='rifle', over=dict(grip=Vector((-0.06, -0.38, 0.54)), rot=dict(yaw=0, pitch=0, roll=0),
                                               support=(160, -40, 0)), aim=Vector((-0.07, -0.42, 0.70)), aimfire=aimfire_lever,
                       fire=(32, fire_lever, False), reload=(84, reload_lever),
                       parts=(('Lever', 'wp_02', REST), ('ammo:Ammo3030_Casing', 'wp_03', _HID),
                              ('ammo:Ammo3030_Round', 'wp_04', _HID), ('ammo:Ammo3030_Round', 'wp_05', _HID))),
    'SMG':       dict(hold='rifle', over=dict(grip=Vector((-0.08, -0.40, 0.56)), rot=dict(yaw=0, pitch=-5, roll=0),
                                              support=(240, -40, 0)),
                      fire=(12, fire_smg, True), reload=(72, reload_smg),
                      parts=(('Mag', 'wp_02', REST), ('Cock', 'wp_03', REST), ('Mag', 'wp_04', HID(REST)))),
    'RocketLauncher': dict(hold='shoulder', over=dict(support=(520, -66, 0)), parts=(('ammo:Rocket', 'wp_03'),),
                           fire=(30, fire_launcher, False), reload=(84, reload_launcher)),
    'Minigun':   dict(hold='heavy', over=dict(support=(100, 196, 0)), parts=(('Barrels', 'wp_02'),),
                      fire=(12, spin_fire(12), True), reload=None),
    'Blueprint': dict(hold='board', over=dict(hold_pt=(10, 0, 128)), fire=(24, fire_board, False), reload=(44, reload_board)),
}


def hold_of(wname):
    d = WDEF[wname]; H = dict(HOLDS[d['hold']])
    H.update(d.get('over', {}))
    H['pdef'] = {p[1]: p[2] for p in d.get('parts', ()) if len(p) > 2}    # bone -> where it sits when nothing moves it
    return H


# ------------------------------------------------------------------ authoring
def bake(rig, prefix, hold, gait_name, frames, extra=None, loop=None):
    name = '%s_%s' % (prefix, gait_name)
    act = bpy.data.actions.get(name)
    if act:
        bpy.data.actions.remove(act)
    act = bpy.data.actions.new(name)
    rig.arm.animation_data.action = act
    cyc = (extra is None) if loop is None else loop
    n = frames
    rig._last_pole = {}
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


def attach_set(rig, wname):
    d = WDEF[wname]
    rig.attach(wname, 'weapon')
    if d.get('dual'):
        rig.attach(wname, 'wp_01')
    for p in d.get('parts', ()):
        rig.attach(wname, p[1], part=p[0])


def bake_set(rig, wname, only=None, prefix=None):
    d = WDEF[wname]; H = hold_of(wname)
    prefix = prefix or 'TP_%s' % wname
    want = lambda a: not only or a in only
    out = [bake(rig, prefix, H, g, GAIT[g]['frames']) for g in GAIT if want(g)]
    n, fn, lp = d['fire']
    if want('Fire'):
        out.append(bake(rig, prefix, H, 'Fire', n, extra=fn, loop=lp))
    if d.get('reload') and want('Reload'):
        out.append(bake(rig, prefix, H, 'Reload', d['reload'][0], extra=d['reload'][1]))
    if d.get('aim') is not None:                                   # rifles: shouldered at the eye
        Ha = dict(H, grip=d['aim'], rot=dict(yaw=0, pitch=0, roll=0), sway=0.3)
        if want('Aim'):
            out.append(bake(rig, prefix, Ha, 'Aim', 60))
        if want('AimFire'):
            out.append(bake(rig, prefix, Ha, 'AimFire', n, extra=d.get('aimfire', fn), loop=False))
    return out


def build(cls, wname, prefix=None, only=None):
    """bake the third-person set for one class + weapon. only: subset of action names to (re)bake."""
    rig = Rig(cls)
    attach_set(rig, wname)
    return rig, bake_set(rig, wname, only, prefix)


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
    for f in range(f0, f1 + 1, step):
        sc.frame_set(f)
        wobjs = [o for key, w in rig.weapons.items() if rig.pb[key].scale.x >= 0.5 for o in w['objs']]
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


# ------------------------------------------------------------------ one-call test (results kept on the module)
LAST = {}


def test(cls, wname, only=None, step=1):
    del IK_MISSES[:]; del REACH_MISSES[:]
    rig, acts = build(cls, wname, only=only)
    res = {a.name: check(rig, a, step=step) for a in acts}
    LAST.update(rig=rig, res=res, misses=list(IK_MISSES), reach=list(REACH_MISSES))
    return {k: (len(v), v[:6]) for k, v in res.items()}, len(IK_MISSES), len(REACH_MISSES), REACH_MISSES[:3]


def probe(rig, act, frames):
    """per frame: which body groups each arm / the gun overlaps (wedge, hats, gun, legs) -- for tuning"""
    rig.arm.animation_data.action = bpy.data.actions[act] if isinstance(act, str) else act
    mw = rig.arm.matrix_world; out = []
    for f in frames:
        bpy.context.scene.frame_set(f)
        wb = _bvh([o for key, w in rig.weapons.items() if rig.pb[key].scale.x >= 0.5 for o in w['objs']])
        wedge = _bvh([rig.body], only_groups=('spine_01', 'pelvis', 'aim', 'root'))
        hats = _bvh(rig.acc, only_groups=('spine_01', 'aim')) if rig.acc else None
        hs = [(mw @ rig.arm.pose.bones[b].tail, 0.034 * rig.s) for b in ('lowerarm_l', 'lowerarm_r')]
        sh = [(mw @ rig.arm.pose.bones[b].head, 0.05 * rig.s) for b in ('upperarm_l', 'upperarm_r')]
        row = {}
        for g in ('spine_01', 'thigh_l', 'thigh_r', 'calf_l', 'calf_r', 'upperarm_l', 'lowerarm_l', 'hand_l',
                  'upperarm_r', 'lowerarm_r', 'hand_r'):
            t = _bvh([rig.body], only_groups=(g,))
            if not t:
                continue
            arm = 'arm' in g or 'hand' in g
            v = (_ov(wb, t, hs), _ov(wedge, t, sh) if arm else 0, _ov(hats, t, sh) if (hats and arm) else 0)
            if any(v):
                row[g] = v
        P = lambda b: tuple(round(c, 3) for c in rig.C(rig.arm.pose.bones[b].tail))
        out.append((f, row, 'hL', P('lowerarm_l'), 'hR', P('lowerarm_r')))
    return out


# ------------------------------------------------------------------ final bake + export per class
CLASS_WEAPONS = {'Outlaw': ('Revolver', 'Derringer'), 'MrShotgun': ('SawedOff', 'MachinePistol'),
                 'RocketGuy': ('RocketLauncher', 'SemiAuto'), 'Sniper': ('BoltRifle', 'LeverRifle'),
                 'Mechanic': ('SMG', 'Blueprint'), 'Greg': ('Minigun', 'SnubNose')}
OUT = r"C:\Users\mrsobo\Documents\LonelyRoad\CheeseAnim\export"


def _drop_weapons(rig):
    for w in rig.weapons.values():
        for o in [w['hold']] + list(w['hold'].children_recursive):
            bpy.data.objects.remove(o, do_unlink=True)
    rig.weapons.clear()


def export_class(cls, step=2, logp=None):
    """bake both weapons' third-person sets on one rig, verify, save <cls>_TP.blend + .fbx (armature, body, accessories,
    all TP_<Weapon>_<Action> actions). returns {action: clip-frames}"""
    os.makedirs(OUT, exist_ok=True)
    rig = Rig(cls)
    report = {}
    for wname in CLASS_WEAPONS[cls]:
        attach_set(rig, wname)
        acts = bake_set(rig, wname)
        for a in acts:
            report[a.name] = len(check(rig, a, step=step))
            if logp:
                open(logp, 'a').write('%s %s clip-frames=%d\n' % (cls, a.name, report[a.name]))
        _drop_weapons(rig)
    rig.arm.animation_data.action = bpy.data.actions.get('TP_%s_Idle' % CLASS_WEAPONS[cls][0])
    bpy.context.scene.frame_set(1)
    bpy.ops.wm.save_as_mainfile(filepath=os.path.join(OUT, '%s_TP.blend' % cls))
    win = bpy.context.window_manager.windows[0]
    keep = [rig.arm, rig.body] + list(rig.acc)
    for o in bpy.context.view_layer.objects:
        o.select_set(o in keep)
    with bpy.context.temp_override(window=win, active_object=rig.arm, selected_objects=keep):
        bpy.ops.export_scene.fbx(filepath=os.path.join(OUT, '%s_TP.fbx' % cls), use_selection=True,
                                 object_types={'ARMATURE', 'MESH'}, add_leaf_bones=False, bake_anim=True,
                                 bake_anim_use_all_actions=True, bake_anim_use_nla_strips=False,
                                 path_mode='COPY', embed_textures=True, apply_unit_scale=True)
    if logp:
        open(logp, 'a').write('%s exported\n' % cls)
    return report
