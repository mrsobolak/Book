# Build Whey Station in Blender.
#   cloud sandbox (headless bpy):  python3 build.py <texdir> <outdir> [save.blend]
#   desktop Blender (MCP):          import build; build.step('start'|'C'|'B'|'M'|'P', texdir) ... build.finish(outdir)
import sys, os, json, math, importlib
HERE = os.path.dirname(os.path.abspath(__file__)) if '__file__' in globals() else os.environ.get('WS_SRC', '.')
for sub in ('', 'kit', 'map'):
    p = os.path.join(HERE, sub)
    if p not in sys.path:
        sys.path.insert(0, p)
import bpy
import wskit, wsparts, layout, wsbase, wsmiddle
for m in (wskit, wsparts, layout, wsbase, wsmiddle):
    importlib.reload(m)
from wskit import Kit, build_objects, TEXAVG
PI = math.pi
ROOT_COL = 'COL-WheyStation'


def _texavg(texdir):
    for man in (os.path.join(HERE, 'kit', 'texman.json'), os.path.join(texdir, '..', 'texman.json'), os.path.join(texdir, 'texman.json')):
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
    name = 'COL-WS-' + group
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
                if me is not None and me.users == 0 and hasattr(me, 'polygons'):
                    bpy.data.meshes.remove(me)
        for c in list(root.children_recursive):
            bpy.data.collections.remove(c)
        bpy.data.collections.remove(root)


def step(name, texdir):
    """'start' clears only the Whey Station collection; 'C' / 'B' build one base; 'M' the middle; 'P' places props"""
    if name == 'start':
        clear(); _texavg(texdir); wskit.set_floors(layout.FLOORS); STATE['K'] = Kit(seed=23); return 'cleared'
    K = STATE['K']
    if name in ('C', 'B'):
        x, ry = layout.BASE_FRAME[name]
        K.group = 'Base' + name; K.at(x, 0, 0, ry); wsbase.base(K, name); K.pop()
    elif name == 'M':
        K.group = 'Middle'; wsmiddle.middle(K)
    elif name == 'P':
        return 'P: %d props (placed by place_props in Blender)' % place_props(K)
    objs = build_objects(K, texdir, _coll)
    return '%s: %d objects, %d faces' % (name, len(objs), sum(len(o.data.polygons) for o in objs))


def place_props(K):
    """instance library models (hidden SRC-* objects in COL-WS-Sources) at the recorded prop spots"""
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


def finish(outdir, export=True):
    os.makedirs(outdir, exist_ok=True); K = STATE['K']
    data = {'map': 'whey_station', 'cols': K.cols, 'openings': K.openings, 'lights': K.lights, 'areas': K.areas,
            'labels': K.labels, 'props': K.props, 'spawns': layout.SPAWNS, 'flags': layout.FLAGS}
    with open(os.path.join(outdir, 'ws_data.json'), 'w') as f:
        json.dump(data, f, separators=(',', ':'))
    if export:
        root = bpy.data.collections.get(ROOT_COL)
        for ob in bpy.context.scene.objects:
            ob.select_set(ob.name in root.all_objects)
        kw = dict(filepath=os.path.join(outdir, 'ws_struct.glb'), export_format='GLB', export_image_format='NONE',
                  export_yup=True, export_apply=True, export_normals=True, export_texcoords=True, use_selection=True)
        props = bpy.ops.export_scene.gltf.get_rna_type().properties.keys()
        if 'export_vertex_color' in props:
            kw['export_vertex_color'] = 'ACTIVE'
        if 'export_lights' in props:
            kw['export_lights'] = False
        bpy.ops.export_scene.gltf(**kw)
    return {'cols': len(K.cols), 'lights': len(K.lights), 'props': len(K.props)}


def run(texdir, outdir, export=True):
    msgs = [step(s, texdir) for s in ('start', 'C', 'B', 'M')]
    return msgs, finish(outdir, export)


if __name__ == '__main__':
    argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else sys.argv[1:]
    texdir = argv[0] if argv else os.environ.get('WS_TEXDIR', '')
    outdir = argv[1] if len(argv) > 1 else os.environ.get('WS_OUTDIR', os.path.join(HERE, 'out'))
    print(run(texdir, outdir))
    if len(argv) > 2:
        bpy.ops.wm.save_as_mainfile(filepath=argv[2])
