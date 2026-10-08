# blender -b -P build_class.py -- <Class> <outdir> [preview|full]
import bpy, sys, os, importlib, math
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import acc, classes, arms
importlib.reload(acc); importlib.reload(classes); importlib.reload(arms)
argv = sys.argv[sys.argv.index('--') + 1:] if '--' in sys.argv else ['Outlaw', '/tmp/cls']
cls, out = argv[0], argv[1]
mode = argv[2] if len(argv) > 2 else 'preview'
os.makedirs(out, exist_ok=True)
bpy.ops.wm.open_mainfile(filepath=os.path.join(HERE, 'src', 'cheese', 'CheesePlayer.blend'))
arms.lengthen()
P = acc.Probe()
T = acc.top_frame(P)
obs = classes.BUILDERS[cls](P, T)
print('built', cls, len(obs), 'objects')
bpy.ops.wm.save_as_mainfile(filepath=os.path.join(out, cls + '_work.blend'))
