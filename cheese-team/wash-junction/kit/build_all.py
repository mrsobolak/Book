"""Rebuild every (or selected) asset script in parallel -- handy on a big local machine.
    python kit/build_all.py [--blender PATH] [--jobs N] [--gpu] [--render] [--draft] [script ...]
Examples (Windows PowerShell):
    python kit\\build_all.py --blender "C:\\Program Files\\Blender Foundation\\Blender 4.0\\blender.exe" --jobs 4 --gpu
    python kit\\build_all.py --jobs 6 water_tower semi_cab
Needs numpy + Pillow in this Python (pip install numpy pillow). Logs go to export/_logs/.
"""
import os, sys, subprocess, shutil, time, argparse
from concurrent.futures import ThreadPoolExecutor

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
ap = argparse.ArgumentParser()
ap.add_argument("--blender", default=os.environ.get("BLENDER") or shutil.which("blender") or "blender")
ap.add_argument("--jobs", type=int, default=max(1, (os.cpu_count() or 4) // 8))
ap.add_argument("--gpu", action="store_true")
ap.add_argument("--render", action="store_true", help="also write preview JPGs")
ap.add_argument("--draft", action="store_true", help="stats only, no bake")
ap.add_argument("scripts", nargs="*")
a = ap.parse_args()
src = os.path.join(ROOT, "src")
names = a.scripts or sorted(f[:-3] for f in os.listdir(src) if f.endswith(".py"))
logs = os.path.join(ROOT, "export", "_logs")
os.makedirs(logs, exist_ok=True)
env = dict(os.environ, WJ_PYTHON=sys.executable)


def run(n):
    cmd = [a.blender, "-b", "-P", os.path.join(src, n + ".py"), "--"] + [f for f, on in
           (("--gpu", a.gpu), ("--render", a.render), ("--draft", a.draft)) if on]
    t = time.time()
    with open(os.path.join(logs, n + ".log"), "w") as log:
        rc = subprocess.run(cmd, stdout=log, stderr=subprocess.STDOUT, env=env, cwd=ROOT).returncode
    txt = open(os.path.join(logs, n + ".log"), errors="replace").read()
    oks = [l for l in txt.splitlines() if l.startswith("[kit] OK") or l.startswith("[kit] OVER")]
    bad = "Traceback" in txt or rc != 0
    print("%-18s %s %4.0fs  %s" % (n, "FAIL" if bad else "ok  ", time.time() - t, " | ".join(l[6:60] for l in oks)), flush=True)
    return n, not bad


print("building %d scripts with %d parallel Blender jobs%s" % (len(names), a.jobs, " on GPU" if a.gpu else ""))
with ThreadPoolExecutor(a.jobs) as ex:
    res = list(ex.map(run, names))
failed = [n for n, ok in res if not ok]
print("done; failed:", failed or "none")
subprocess.run([sys.executable, os.path.join(ROOT, "gallery", "build_gallery.py")])
