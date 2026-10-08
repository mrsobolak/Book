"""Compress cheeseman.glb (gltfpack/meshopt) and embed it + rig.json into index.html.

    python3 build_viewer.py [--fragment out.html]      (GLTFPACK=/path/to/gltfpack if not on PATH)
"""
import base64, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
src, packed = os.path.join(HERE, "cheeseman.glb"), os.path.join(HERE, "cheeseman.packed.glb")
subprocess.run([os.environ.get("GLTFPACK", "gltfpack"), "-i", src, "-o", packed, "-cc", "-vpf", "-kn", "-km"],
               check=True, capture_output=True)
tpl = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
body = (tpl.replace("__RIG__", open(os.path.join(HERE, "rig.json")).read())
        .replace("__GLB_BASE64__", base64.b64encode(open(packed, "rb").read()).decode()))
if "--fragment" in sys.argv:
    out, html = sys.argv[sys.argv.index("--fragment") + 1], body
else:
    out = os.path.join(HERE, "index.html")
    html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + body.replace("<style>", "<style>\n  html, body { margin: 0; }", 1)
            .replace('<div class="wrap">', '</head>\n<body>\n<div class="wrap">', 1) + "\n</body>\n</html>\n")
open(out, "w", encoding="utf-8").write(html)
print(f"wrote {out} ({len(html) / 1024:.0f} KB; packed glb {os.path.getsize(packed) / 1024:.0f} KB)")
