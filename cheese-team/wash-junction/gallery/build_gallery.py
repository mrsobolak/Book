"""Build export/index.html (gallery + GLB viewer) and ASSETS.md (table) from the per-asset report.json files.
    python3 gallery/build_gallery.py
"""
import json, os, glob, html

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EXP = os.path.join(ROOT, "export")
TIER = {}
for line in open(os.path.join(ROOT, "SPEC.md")):
    pass
P1 = ["FlagCheese_Cheddar", "FlagCheese_Bleu", "FlagPedestal", "VaultDoor_Open", "VaultDoorFrame", "HealthPack_S", "HealthPack_M",
      "HealthPack_L", "AmmoPack_S", "AmmoPack_M", "AmmoPack_L", "ResupplyCabinet", "Lockers_1", "Lockers_1_Open", "SpawnDoorFrame"]
P2 = ["WaterTower_Wood", "Windmill_Pump", "Windmill_Wheel", "StockTank", "Billboard_2Post", "SignGantry", "HighwaySign",
      "SemiTrailer_DryVan", "SemiCab_American", "RoofSignFrame", "GarageRollUp_Half"]
ORDER = P1 + P2


def tier(n):
    return "P1" if n in P1 else ("P2" if n in P2 else "P3")


def load():
    out = []
    for f in sorted(glob.glob(os.path.join(EXP, "*", "SM_*.report.json"))):
        r = json.load(open(f))
        folder = os.path.basename(os.path.dirname(f))
        name = r["name"][3:]
        r["_folder"] = folder
        r["_short"] = name
        r["_tier"] = tier(name)
        files = sorted(os.listdir(os.path.dirname(f)))
        r["_tex"] = [x for x in files if x.startswith("T_") and x.endswith(".png")]
        r["_fbx"] = [x for x in files if x.startswith(r["name"]) and x.endswith(".fbx")]
        r["_glb"] = r["name"] + ".glb" if r["name"] + ".glb" in files else None
        r["_prev"] = r["name"] + "_preview.jpg" if r["name"] + "_preview.jpg" in files else None
        out.append(r)
    key = lambda r: (r["_tier"], ORDER.index(r["_short"]) if r["_short"] in ORDER else 999, r["_short"])
    return sorted(out, key=key)


def fmt_dims(d):
    return " × ".join("%.2f" % x for x in d) if d else "-"


def md_table(rs):
    lines = ["| Tier | Mesh | Tris / budget | LOD1 | Size X×Y×Z m (target) | Tex | Slots | UCX | Files |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rs:
        d = r.get("dims_xyz") or r.get("dims")
        t = r.get("target_xyz")
        prev = "[preview](export/%s/%s)" % (r["_folder"], r["_prev"]) if r["_prev"] else ""
        lines.append("| %s | `%s` | %s / %s | %s | %s (%s) | %s | %s | %s | %s |" % (
            r["_tier"], r["name"], r.get("tris"), r.get("budget"), r.get("lod1_tris") or "-", fmt_dims(d), fmt_dims(t),
            r.get("texture", "-"), ", ".join(r.get("slots", [])), r.get("ucx", "-"), prev))
    return "\n".join(lines)


def page(rs):
    cards = []
    for r in rs:
        d = r.get("dims_xyz") or r.get("dims")
        ok = r.get("tris", 0) <= r.get("budget", 1e9)
        files = "".join('<a href="%s/%s" download>%s</a>' % (r["_folder"], f, html.escape(f)) for f in r["_fbx"] + ([r["_glb"]] if r["_glb"] else []) + r["_tex"])
        cards.append("""<article class="card" data-glb="%s" data-name="%s">
  <div class="thumb">%s<span class="tier %s">%s</span></div>
  <h3>%s</h3>
  <dl><dt>Tris</dt><dd class="%s">%s / %s%s</dd><dt>Size</dt><dd>%s m</dd><dt>Target</dt><dd>%s m</dd>
  <dt>Slots</dt><dd>%s</dd><dt>Texture</dt><dd>%s² · %s px/m</dd></dl>
  <details><summary>Files</summary><div class="files">%s</div></details>
  %s
</article>""" % (
            ("%s/%s" % (r["_folder"], r["_glb"])) if r["_glb"] else "", html.escape(r["name"]),
            ('<img loading="lazy" src="%s/%s" alt="%s preview">' % (r["_folder"], r["_prev"], html.escape(r["name"]))) if r["_prev"] else "<div class=noimg>no preview</div>",
            r["_tier"].lower(), r["_tier"], html.escape(r["name"]), "ok" if ok else "bad", r.get("tris"), r.get("budget"),
            (" · LOD1 %s" % r["lod1_tris"]) if r.get("lod1_tris") else "", fmt_dims(d), fmt_dims(r.get("target_xyz")),
            html.escape(", ".join(r.get("slots", []))), r.get("texture"), r.get("px_per_m"), files,
            ('<button class="view">View 3D</button>' if r["_glb"] else "")))
    return TEMPLATE.replace("{{CARDS}}", "\n".join(cards)).replace("{{COUNT}}", str(len(rs)))


TEMPLATE = r"""<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Wash Junction Assets</title>
<style>
:root{--bg:#f3efe7;--fg:#211d18;--muted:#6d655a;--card:#fffaf2;--line:#ddd3c4;--acc:#c8601c;--acc2:#33669f;--ok:#2f7a3b;--bad:#b3261e}
@media (prefers-color-scheme:dark){:root:not([data-theme="light"]){--bg:#17140f;--fg:#ece5d8;--muted:#a69b8b;--card:#221e18;--line:#3a3329;--ok:#7fc489;--bad:#ff8a80}}
:root[data-theme="dark"]{--bg:#17140f;--fg:#ece5d8;--muted:#a69b8b;--card:#221e18;--line:#3a3329;--ok:#7fc489;--bad:#ff8a80}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--fg);font:15px/1.45 system-ui,-apple-system,Segoe UI,Roboto,sans-serif}
header{padding:28px 16px 8px;max-width:1400px;margin:auto}h1{margin:0 0 4px;font-size:28px;letter-spacing:-.01em}
header p{margin:0;color:var(--muted)}.bar{display:flex;gap:8px;flex-wrap:wrap;margin:14px 0}
.bar button{border:1px solid var(--line);background:var(--card);color:var(--fg);padding:6px 12px;border-radius:999px;cursor:pointer}
.bar button.on{background:var(--acc);border-color:var(--acc);color:#fff}
main{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:16px;padding:8px 16px 40px;max-width:1400px;margin:auto}
.card{background:var(--card);border:1px solid var(--line);border-radius:12px;overflow:hidden;display:flex;flex-direction:column}
.thumb{position:relative;aspect-ratio:4/3;background:#9c948a}.thumb img{width:100%;height:100%;object-fit:cover;display:block}
.tier{position:absolute;top:8px;left:8px;font-size:12px;font-weight:700;padding:2px 8px;border-radius:999px;background:#000a;color:#fff}
.tier.p1{background:var(--acc)}.tier.p2{background:var(--acc2)}
.card h3{margin:10px 12px 4px;font-size:15px;font-family:ui-monospace,Menlo,Consolas,monospace;word-break:break-all}
dl{display:grid;grid-template-columns:auto 1fr;gap:2px 10px;margin:0 12px 8px;font-size:13px}dt{color:var(--muted)}dd{margin:0}
dd.ok{color:var(--ok)}dd.bad{color:var(--bad);font-weight:700}
details{margin:0 12px 8px;font-size:13px}.files{display:flex;flex-direction:column;gap:2px;margin-top:4px}
.files a{color:var(--acc2);word-break:break-all}
.view{margin:auto 12px 12px;padding:8px;border-radius:8px;border:0;background:var(--fg);color:var(--bg);font-weight:600;cursor:pointer}
#viewer{position:fixed;inset:0;background:#000c;display:none;align-items:center;justify-content:center;z-index:9}
#viewer.open{display:flex}#vbox{position:relative;width:min(1100px,96vw);height:min(760px,86vh);background:#2a2724;border-radius:12px;overflow:hidden}
#vbox canvas{width:100%;height:100%;display:block}#vname{position:absolute;left:12px;top:10px;color:#fff;font:600 14px ui-monospace,monospace}
#vclose{position:absolute;right:10px;top:8px;border:0;background:#fff2;color:#fff;border-radius:6px;padding:4px 10px;cursor:pointer}
#vstat{position:absolute;left:12px;bottom:10px;color:#ddd;font-size:12px}
</style></head><body>
<header><h1>Wash Junction — Cheese Team assets</h1>
<p>{{COUNT}} game-ready meshes. Each has an FBX for Unreal (1 unit = 1 cm, UCX collision), a GLB in metres, baked PBR textures (BaseColor, DirectX Normal, ORM) and a preview render.</p>
<div class="bar"><button class="on" data-f="all">All</button><button data-f="P1">P1 gameplay</button><button data-f="P2">P2 landmarks</button><button data-f="P3">P3 set dressing</button></div></header>
<main>{{CARDS}}</main>
<div id="viewer"><div id="vbox"><span id="vname"></span><button id="vclose">Close</button><span id="vstat">drag to orbit · scroll to zoom</span></div></div>
<script type="importmap">{"imports":{"three":"https://cdn.jsdelivr.net/npm/three@0.160.0/build/three.module.js","three/addons/":"https://cdn.jsdelivr.net/npm/three@0.160.0/examples/jsm/"}}</script>
<script type="module">
import * as THREE from 'three';
import {OrbitControls} from 'three/addons/controls/OrbitControls.js';
import {GLTFLoader} from 'three/addons/loaders/GLTFLoader.js';
import {RoomEnvironment} from 'three/addons/environments/RoomEnvironment.js';
document.querySelectorAll('.bar button').forEach(b=>b.onclick=()=>{
  document.querySelectorAll('.bar button').forEach(x=>x.classList.toggle('on',x===b));
  document.querySelectorAll('.card').forEach(c=>{c.style.display=(b.dataset.f==='all'||c.querySelector('.tier').textContent===b.dataset.f)?'':'none'});
});
let renderer,scene,camera,controls,current;
function init(){
  const box=document.getElementById('vbox');
  renderer=new THREE.WebGLRenderer({antialias:true});renderer.setPixelRatio(Math.min(devicePixelRatio,2));
  renderer.outputColorSpace=THREE.SRGBColorSpace;renderer.toneMapping=THREE.ACESFilmicToneMapping;renderer.toneMappingExposure=1.0;
  renderer.shadowMap.enabled=true;box.prepend(renderer.domElement);
  scene=new THREE.Scene();scene.background=new THREE.Color(0x8d8578);
  const pm=new THREE.PMREMGenerator(renderer);scene.environment=pm.fromScene(new RoomEnvironment(),0.04).texture;
  const sun=new THREE.DirectionalLight(0xfff1dc,2.2);sun.position.set(4,6,-5);sun.castShadow=true;sun.shadow.mapSize.set(2048,2048);scene.add(sun);scene.userData.sun=sun;
  const g=new THREE.Mesh(new THREE.CircleGeometry(200,64),new THREE.MeshStandardMaterial({color:0x7d7468,roughness:1}));g.rotation.x=-Math.PI/2;g.receiveShadow=true;scene.add(g);
  camera=new THREE.PerspectiveCamera(40,1,0.01,2000);controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;
  const resize=()=>{const r=box.getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();};
  new ResizeObserver(resize).observe(box);resize();
  renderer.setAnimationLoop(()=>{controls.update();renderer.render(scene,camera);});
}
function open(url,name){
  if(!renderer)init();document.getElementById('viewer').classList.add('open');document.getElementById('vname').textContent=name;
  if(current){scene.remove(current);current=null;}
  new GLTFLoader().load(url,gl=>{
    current=gl.scene;current.traverse(o=>{if(o.isMesh){o.castShadow=o.receiveShadow=true;}});
    const b=new THREE.Box3().setFromObject(current);current.position.y-=b.min.y;
    const b2=new THREE.Box3().setFromObject(current),c=b2.getCenter(new THREE.Vector3()),s=b2.getSize(new THREE.Vector3()).length();
    scene.add(current);controls.target.copy(c);
    // glTF is Y-up with the asset front (+X in Blender) on +X: view from the front three-quarter
    camera.position.set(c.x+s*0.85,c.y+s*0.35,c.z+s*0.62);camera.near=s/500;camera.far=s*50;camera.updateProjectionMatrix();
    const sun=scene.userData.sun;sun.position.set(c.x+s*0.6,c.y+s*1.2,c.z+s*1.0);sun.target.position.copy(c);scene.add(sun.target);
    const sc=sun.shadow.camera;sc.left=sc.bottom=-s;sc.right=sc.top=s;sc.near=0.01;sc.far=s*6;sc.updateProjectionMatrix();
  });
}
document.querySelectorAll('.card .view').forEach(b=>b.onclick=()=>{const c=b.closest('.card');open(c.dataset.glb,c.dataset.name);});
document.getElementById('vclose').onclick=()=>document.getElementById('viewer').classList.remove('open');
</script></body></html>"""

if __name__ == "__main__":
    rs = load()
    open(os.path.join(EXP, "index.html"), "w").write(page(rs))
    open(os.path.join(ROOT, "ASSETS.md"), "w").write("# Wash Junction asset table\n\nGenerated by `gallery/build_gallery.py` from the per-asset reports.\n\n" + md_table(rs) + "\n")
    print("gallery:", len(rs), "assets")
