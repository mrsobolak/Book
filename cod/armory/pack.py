"""Compress every weapon GLB with gltfpack (meshopt) and build the armory page.

    python3 pack.py [--fragment out.html]

Needs `gltfpack` on PATH (npm i -g gltfpack) or GLTFPACK=/path/to/gltfpack.
Thumbnails are read from thumbs.json when present (see make_thumbs.mjs).
"""
import base64, json, os, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))
GLTFPACK = os.environ.get("GLTFPACK", "gltfpack")

W = lambda **k: k
REGISTRY = [
    W(id="kestrel7", slot="Primary", name="KESTREL-7", cls="Assault rifle", code="KST-7", maker="Kestrel Arms",
      src="../weapons/kestrel-7/kestrel7.glb",
      show=["base", "att_muzzle_comp", "att_optic_reddot", "buis_folded", "att_mag_30", "att_under_agrip"],
      desc="Short-stroke piston carbine with a free-float M-LOK handguard. Fitted here with the tri-port comp, micro dot and angled grip.",
      stats={"Accuracy": 64, "Damage": 61, "Range": 57, "Fire rate": 72, "Mobility": 66, "Handling": 63},
      spec=[["Caliber", "5.56×45 mm"], ["Action", "Short-stroke piston"], ["Rate of fire", "780 rpm"], ["Magazine", "30 rds"], ["Barrel", "14.0 in"]]),
    W(id="vespa9", slot="Primary", name="VESPA-9", cls="Submachine gun", code="VSP-9", maker="Kestrel Arms",
      desc="Compact 9 mm with a cocking tube on the left, a side-folding skeleton stock and an open-emitter reflex sight.",
      stats={"Accuracy": 55, "Damage": 45, "Range": 38, "Fire rate": 84, "Mobility": 86, "Handling": 82},
      spec=[["Caliber", "9×19 mm"], ["Action", "Closed-bolt blowback"], ["Rate of fire", "900 rpm"], ["Magazine", "30 rds"], ["Barrel", "5.5 in"]]),
    W(id="bulwark", slot="Primary", name="BULWARK-60", cls="Light machine gun", code="BWK-60", maker="Halvard Defence",
      desc="Belt-fed 7.62 with a 100-round box, feed-cover rail, quick-change heavy barrel with carry handle, and a deployed bipod.",
      stats={"Accuracy": 58, "Damage": 74, "Range": 72, "Fire rate": 62, "Mobility": 38, "Handling": 34},
      spec=[["Caliber", "7.62×51 mm"], ["Action", "Gas piston, open bolt"], ["Rate of fire", "650 rpm"], ["Feed", "100-rd belt"], ["Barrel", "18.0 in"]]),
    W(id="talonb", slot="Primary", name="TALON-B", cls="Marksman rifle", code="TLN-B", maker="Halvard Defence",
      desc="Bullpup marksman rifle with a full-hand trigger guard, magazine behind the grip and a 1–6× variable optic.",
      stats={"Accuracy": 78, "Damage": 76, "Range": 80, "Fire rate": 40, "Mobility": 60, "Handling": 55},
      spec=[["Caliber", "6.8×51 mm"], ["Action", "Gas piston, semi"], ["Rate of fire", "Semi-auto"], ["Magazine", "20 rds"], ["Barrel", "16.0 in"]]),
    W(id="longreach", slot="Primary", name="LONGREACH .338", cls="Sniper rifle", code="LR-338", maker="Northline Precision",
      desc="Bolt-action chassis rifle with a fluted barrel, a triple-port brake and a 5–25×56 scope in 34 mm rings.",
      stats={"Accuracy": 92, "Damage": 95, "Range": 96, "Fire rate": 12, "Mobility": 42, "Handling": 30},
      spec=[["Caliber", ".338 Lapua Mag"], ["Action", "Bolt action"], ["Rate of fire", "Bolt"], ["Magazine", "5 rds"], ["Barrel", "26.0 in"]]),
    W(id="hollowpoint", slot="Primary", name="HOLLOWPOINT 12", cls="Shotgun", code="HP-12", maker="Northline Precision",
      desc="Pump 12 gauge with a vented heat shield, breaching muzzle, ghost-ring sights and a six-shell side saddle.",
      stats={"Accuracy": 40, "Damage": 90, "Range": 22, "Fire rate": 30, "Mobility": 70, "Handling": 66},
      spec=[["Caliber", "12 ga 3 in"], ["Action", "Pump"], ["Rate of fire", "Pump"], ["Magazine", "6+1 tube"], ["Barrel", "18.5 in"]]),
    W(id="warden", slot="Secondary", name="WARDEN .45", cls="Pistol", code="WDN-45", maker="Kestrel Arms",
      desc="Full-size striker-fired .45 with front and rear serrations, tritium night sights and a stippled grip.",
      stats={"Accuracy": 60, "Damage": 52, "Range": 30, "Fire rate": 58, "Mobility": 95, "Handling": 92},
      spec=[["Caliber", ".45 ACP"], ["Action", "Striker, semi"], ["Rate of fire", "Semi-auto"], ["Magazine", "13 rds"], ["Barrel", "4.5 in"]]),
    W(id="magistrate", slot="Secondary", name="MAGISTRATE", cls="Revolver", code="MAG-357", maker="Halvard Defence",
      desc="Six-shot stainless .357 with a full-lug barrel, vented rib, fluted cylinder and walnut finger-groove grips.",
      stats={"Accuracy": 70, "Damage": 78, "Range": 40, "Fire rate": 28, "Mobility": 88, "Handling": 74},
      spec=[["Caliber", ".357 Magnum"], ["Action", "Double action"], ["Rate of fire", "Semi-auto"], ["Cylinder", "6 rds"], ["Barrel", "6.0 in"]]),
    W(id="hornet", slot="Secondary", name="HORNET RPL", cls="Launcher", code="HNT-85", maker="Halvard Defence",
      desc="Shoulder-fired rocket launcher with a walnut heat guard, side-mounted optic, flared venturi and an 85 mm HE round loaded.",
      stats={"Accuracy": 50, "Damage": 100, "Range": 60, "Fire rate": 5, "Mobility": 45, "Handling": 35},
      spec=[["Caliber", "85 mm HE"], ["Action", "Recoilless"], ["Rate of fire", "Single shot"], ["Magazine", "1 round"], ["Tube", "40 mm"]]),
    W(id="raven", slot="Melee", name="RAVEN", cls="Combat knife", code="RVN-7", maker="Northline Precision",
      desc="Seven-inch clip-point fighter with a coated flat grind, satin edge bevel, fuller, textured handle and glass-breaker pommel.",
      stats={"Accuracy": 90, "Damage": 100, "Range": 5, "Fire rate": 85, "Mobility": 100, "Handling": 98},
      spec=[["Blade", "7.0 in clip point"], ["Steel", "1095 carbon"], ["Grind", "Flat, 20°"], ["Handle", "Textured polymer"], ["Weight", "340 g"]]),
]

def packed(w):
    src = os.path.normpath(os.path.join(HERE, w.get("src", f"models/{w['id']}.glb")))
    if not os.path.exists(src):
        return None
    dst = os.path.join(HERE, "models", "packed", f"{w['id']}.glb")
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if not os.path.exists(dst) or os.path.getmtime(dst) < os.path.getmtime(src):
        subprocess.run([GLTFPACK, "-i", src, "-o", dst, "-cc", "-vpf", "-kn", "-km"], check=True, capture_output=True)
    return dst

def main():
    tpl = open(os.path.join(HERE, "viewer_template.html"), encoding="utf-8").read()
    meta, scripts = [], []
    for w in REGISTRY:
        p = packed(w)
        if not p:
            print("skip (not built):", w["id"]); continue
        data = base64.b64encode(open(p, "rb").read()).decode()
        scripts.append(f'<script id="glb-{w["id"]}" type="application/octet-stream">{data}</script>')
        meta.append({k: v for k, v in w.items() if k != "src"})
        print(f"  {w['id']:12s} {os.path.getsize(p) / 1024:7.0f} KB")
    thumbs = {}
    tp = os.path.join(HERE, "thumbs.json")
    if os.path.exists(tp):
        thumbs = json.load(open(tp))
    body = (tpl.replace("__META__", json.dumps(meta)).replace("__THUMBS__", json.dumps(thumbs))
            .replace("__GLB_SCRIPTS__", "\n".join(scripts)))
    if "--fragment" in sys.argv:
        out, html = sys.argv[sys.argv.index("--fragment") + 1], body
    else:
        out = os.path.join(HERE, "index.html")
        html = ('<!doctype html>\n<html lang="en">\n<head>\n<meta charset="utf-8">\n'
                '<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">\n'
                + body.replace("<style>", "<style>\n  html, body { margin: 0; }", 1)
                .replace('<div class="wrap">', '</head>\n<body>\n<div class="wrap">', 1)
                + "\n</body>\n</html>\n")
    open(out, "w", encoding="utf-8").write(html)
    print(f"wrote {out} ({len(html) / 1024:.0f} KB, {len(meta)} weapons)")

if __name__ == "__main__":
    main()
