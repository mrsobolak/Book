# Build Rind Ridge in Blender (reuses the Whey Station kit).
#   desktop Blender (MCP):  import rrbuild; rrbuild.step('start'|'T'|'K'|'S'|'P', texdir) ... rrbuild.finish(outdir)
import sys, os, json, math, importlib
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.environ.get('RR_SRC', '.')
for p in (HERE, os.path.join(HERE, '..', 'whey-station', 'kit'), os.path.join(HERE, 'kit')):
    if p not in sys.path:
        sys.path.insert(0, p)
import bpy
import wskit, wsparts, rrlayout, rrtrack, rrterrain, rrstruct
for m in (wskit, wsparts, rrlayout, rrtrack, rrterrain, rrstruct):
    importlib.reload(m)
from wskit import Kit, build_objects, TEXAVG, MATS
PI = math.pi
ROOT_COL = 'COL-RindRidge'
MATS.update({
    'RR_Sand': ('dry_ground_01', 7.0, '#c9a27a', 0.95, 0), 'RR_Dirt': ('dirt', 5.0, '#a07450', 0.95, 0),
    'RR_Rock': ('cliff_rock', 8.0, '#a85a3a', 0.9, 0), 'RR_Road': ('sandy_gravel', 4.0, '#a48a6c', 0.95, 0),
    'RR_Timber': ('rough_wood', 2.0, '#7a5638', 0.85, 0), 'RR_Planks': ('old_planks_02', 2.0, '#8a6a4a', 0.85, 0),
    'RR_SidingG': ('weathered_plank_siding', 2.5, '#5f7d5a', 0.85, 0), 'RR_SidingR': ('weathered_plank_siding', 2.5, '#9a4a35', 0.85, 0),
    'RR_Tin': ('rusty_corrugated_iron', 2.5, '#8a7a68', 0.6, 0.4),
    'RR_Cheese': ('yellow_plaster', 1.5, '#ffd95a', 0.55, 0), 'RR_Rind': ('yellow_plaster', 1.5, '#e8a63a', 0.65, 0),
    'RR_Wax': ('yellow_plaster', 1.5, '#c4232a', 0.4, 0),
})


def _texavg(texdir):
    for man in (os.path.join(HERE, '..', 'whey-station', 'kit', 'texman.json'), os.path.join(texdir, 'texman.json')):
        if os.path.exists(man):
            for k, v in json.load(open(man)).items():
                a = v.get('avg') if isinstance(v, dict) else None
                if a:
                    TEXAVG[k] = [c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4 for c in a]


STATE = {}


def _coll(group):
    scn = bpy.context.scene
    root = bpy.data.collections.get(ROOT_COL)
    if root is None:
        root = bpy.data.collections.new(ROOT_COL); scn.collection.children.link(root)
    name = 'COL-RR-' + group
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name); root.children.link(c)
    return c


def clear():
    root = bpy.data.collections.get(ROOT_COL)
    if root:
        for c in list(root.children_recursive) + [root]:
            for ob in list(c.objects):
                me = ob.data; bpy.data.objects.remove(ob, do_unlink=True)
                if me is not None and getattr(me, 'users', 1) == 0 and hasattr(me, 'polygons'):
                    bpy.data.meshes.remove(me)
        for c in list(root.children_recursive):
            bpy.data.collections.remove(c)
        bpy.data.collections.remove(root)


def step(name, texdir):
    if name == 'start':
        clear(); _texavg(texdir); wskit.set_floors([0.0]); STATE['K'] = Kit(seed=31)
        STATE['S'] = rrtrack.samples(); return 'cleared'
    K, S = STATE['K'], STATE['S']
    if name == 'T':
        K.group = 'Terrain'; X, Z, H, D, I = rrterrain.build(K, S); STATE['H'] = (X, Z, H)
    elif name == 'K':
        K.group = 'Track'; rrstruct.track(K, S, STATE['H'])
    elif name == 'S':
        K.group = 'Structures'; rrstruct.structures(K, S, STATE['H'])
    elif name == 'P':
        return 'P: %d props' % place_props(K)
    objs = build_objects(K, texdir, _coll)
    return '%s: %d objects, %d faces' % (name, len(objs), sum(len(o.data.polygons) for o in objs))


def place_props(K):
    n = 0
    for pr in K.props:
        src = bpy.data.objects.get('SRC-' + pr['src'])
        if src is None:
            continue
        ob = src.copy(); ob.data = src.data
        x, y, z = pr['p']
        ob.location = (x, -z, y); ob.rotation_euler = (0, 0, pr['ry']); ob.scale = (pr['scale'],) * 3
        ob.hide_viewport = ob.hide_render = False
        _coll('Props').objects.link(ob); n += 1
    return n


def finish(outdir):
    os.makedirs(outdir, exist_ok=True); K, S = STATE['K'], STATE['S']
    data = {'map': 'rind_ridge', 'mode': 'payload', 'cols': K.cols, 'lights': K.lights, 'areas': K.areas, 'labels': K.labels,
            'props': K.props, 'track': [[round(v, 3) for v in s['p']] for s in S], 'checkpoints': rrtrack.checkpoints(S),
            'spawns': rrstruct.SPAWNS_OUT}
    with open(os.path.join(outdir, 'rr_data.json'), 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    return {'cols': len(K.cols), 'track_m': S[-1]['s']}
