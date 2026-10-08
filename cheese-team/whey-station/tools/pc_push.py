"""Emit Blender-MCP code that writes the Whey Station source files onto the user's PC (base64 + md5 check).
    python3 tools/pc_push.py file1 file2 ... > push_code.py   (paste/exec the output via execute_blender_code)"""
import sys, base64, hashlib, os
DST = r"C:\Users\mrsobo\Documents\LonelyRoad\WheyStation_Blender"
files = sys.argv[1:]
lines = ["import base64, hashlib, os", "D = r'%s'" % DST, "out = []"]
for f in files:
    data = open(f, 'rb').read()
    lines.append("p = os.path.join(D, *%r.split('/')); os.makedirs(os.path.dirname(p), exist_ok=True)" % f)
    lines.append("b = base64.b64decode(%r); open(p, 'wb').write(b)" % base64.b64encode(data).decode())
    lines.append("out.append((%r, hashlib.md5(open(p,'rb').read()).hexdigest() == %r))" % (f, hashlib.md5(data).hexdigest()))
lines.append("print(out)")
print("\n".join(lines))
