"""Embed the GLB into viewer_template.html and write index.html.

    python3 build_viewer.py            -> index.html (standalone page)
    python3 build_viewer.py --fragment -> viewer_fragment.html (no <html>/<head> wrapper)
"""
import base64, os, sys

here = os.path.dirname(os.path.abspath(__file__))
tpl = open(os.path.join(here, "viewer_template.html"), encoding="utf-8").read()
glb = base64.b64encode(open(os.path.join(here, "kestrel7.glb"), "rb").read()).decode()
body = tpl.replace("__GLB_BASE64__", glb)

if "--fragment" in sys.argv:
    out, html = sys.argv[-1] if sys.argv[-1].endswith(".html") else os.path.join(here, "viewer_fragment.html"), body
else:
    out = os.path.join(here, "index.html")
    html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
            '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
            + body.replace("<style>", "<style>\n  html, body { margin: 0; }", 1)
            .replace("<div class=\"wrap\">", "</head>\n<body>\n<div class=\"wrap\">", 1)
            + "\n</body>\n</html>\n")
open(out, "w", encoding="utf-8").write(html)
print(f"wrote {out} ({len(html) / 1024:.0f} KB)")
