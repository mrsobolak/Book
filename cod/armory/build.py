"""Build one armory weapon.

    blender -b --python build.py -- <weapon_id> [out_dir] [--nobake]

<weapon_id> is a module in weapons/ that defines build().
"""
import importlib, os, sys

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
args = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
pos = [a for a in args if not a.startswith("--")]
wid = pos[0]
out_dir = pos[1] if len(pos) > 1 else os.path.join(HERE, "models")

import lib
lib.reset()
mod = importlib.import_module(f"weapons.{wid}")
mod.build()
lib.finalize(os.path.join(out_dir, f"{wid}.glb"), bake="--nobake" not in args)
