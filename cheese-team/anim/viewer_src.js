
import * as THREE from 'three';
import { OrbitControls } from 'three/addons/controls/OrbitControls.js';
import { GLTFLoader } from 'three/addons/loaders/GLTFLoader.js';

const FPS = 30;
const ACTION_ORDER = ['Idle', 'WalkF', 'WalkB', 'StrafeL', 'StrafeR', 'Fire', 'Reload'];
const ACTION_LABEL = { Idle:'Idle', WalkF:'Walk forward', WalkB:'Walk back', StrafeL:'Strafe left', StrafeR:'Strafe right', Fire:'Fire', Reload:'Reload' };
const MOVE = { WalkF:[0, 0, 1], WalkB:[0, 0, -1], StrafeL:[1, 0, 0], StrafeR:[-1, 0, 0] };   // glTF: char faces +Z
// body speed of the foot-planted gait: a foot slides 2*stride while planted (60% of the cycle)
const GAIT = { WalkF:[0.10, 24], WalkB:[0.08, 26], StrafeL:[0.05, 22], StrafeR:[0.05, 22] };
const SPEED = Object.fromEntries(Object.entries(GAIT).map(([k, [st, n]]) => [k, 2 * st / (0.6 * n / FPS)]));
const HEIGHT = { Sniper:1.07, Greg:1.16 };
const CLASS_NAME = { Outlaw:'Outlaw', MrShotgun:'Mr. Shotgun', RocketGuy:'Boom Boom', Sniper:'Mr. Faraway', Mechanic:'Mechanic', Greg:'Greg' };

// ---------------- scene
const view = document.getElementById('view');
function webglOK() {
  try { const c = document.createElement('canvas'); return !!(c.getContext('webgl2') || c.getContext('webgl')); } catch (e) { return false; }
}
if (!webglOK()) {
  window.__fatal && window.__fatal('This browser has 3D (WebGL) turned off. Fix: open this file in Chrome or Edge, ' +
    'or in Firefox go to Settings > Performance and tick "Use hardware acceleration", then restart Firefox.');
  throw new Error('no WebGL');
}
let renderer;
try { renderer = new THREE.WebGLRenderer({ antialias:true }); }
catch (e) {
  try { renderer = new THREE.WebGLRenderer({ antialias:false, powerPreference:'low-power' }); }
  catch (e2) { window.__fatal && window.__fatal('3D failed to start: ' + (e2.message || e2) + '. Try Chrome or Edge.'); throw e2; }
}
renderer.setPixelRatio(Math.min(devicePixelRatio, 2));
renderer.outputColorSpace = THREE.SRGBColorSpace;
renderer.toneMapping = THREE.ACESFilmicToneMapping;
renderer.shadowMap.enabled = true;
view.appendChild(renderer.domElement);
const scene = new THREE.Scene();
scene.background = new THREE.Color(0x2a2d31);
scene.fog = new THREE.Fog(0x2a2d31, 6, 16);
const camera = new THREE.PerspectiveCamera(40, 1, 0.02, 100);
const controls = new OrbitControls(camera, renderer.domElement);
controls.enableDamping = true;
scene.add(new THREE.HemisphereLight(0xfff4e0, 0x404850, 1.2));
const sun = new THREE.DirectionalLight(0xffffff, 2.2);
sun.position.set(2.5, 4, 3); sun.castShadow = true;
sun.shadow.mapSize.set(2048, 2048);
Object.assign(sun.shadow.camera, { left:-2, right:2, top:2, bottom:-2, near:0.5, far:12 });
scene.add(sun);
const rim = new THREE.DirectionalLight(0xbcd4ff, 0.8); rim.position.set(-3, 2, -3); scene.add(rim);

// checker floor that can scroll under the walker
function checkerTex() {
  const c = document.createElement('canvas'); c.width = c.height = 128; const g = c.getContext('2d');
  for (let y = 0; y < 2; y++) for (let x = 0; x < 2; x++) { g.fillStyle = (x + y) % 2 ? '#44484e' : '#3a3e43'; g.fillRect(x * 64, y * 64, 64, 64); }
  const t = new THREE.CanvasTexture(c); t.wrapS = t.wrapT = THREE.RepeatWrapping; t.repeat.set(40, 40);
  t.colorSpace = THREE.SRGBColorSpace; t.anisotropy = 8; return t;
}
const floorTex = checkerTex();
const floor = new THREE.Mesh(new THREE.PlaneGeometry(20, 20), new THREE.MeshStandardMaterial({ map:floorTex, roughness:0.95 }));
floor.rotation.x = -Math.PI / 2; floor.receiveShadow = true; scene.add(floor);

// ---------------- state
const chars = {};          // name -> { root, mixer, clips: {weapon: {action: clip}}, weaponMeshes: {weapon: [mesh]}, height }
let cur = null, curWeapon = null, curAction = null, action = null, playing = true, skel = null;
const $ = id => document.getElementById(id);
const status = t => $('status').textContent = t;

// ---------------- loading
const loader = new GLTFLoader();
function loadFile(file) {
  return new Promise((res, rej) => {
    const url = URL.createObjectURL(file);
    loader.load(url, g => { URL.revokeObjectURL(url); res(g); }, undefined, e => { URL.revokeObjectURL(url); rej(e); });
  });
}
function weaponOf(name) {
  let m = /^W_([A-Za-z]+?)_(weapon|wp_\d+)/.exec(name);
  return m ? m[1] : null;
}
async function addFiles(files) {
  files = [...files].filter(f => /\.(glb|gltf)$/i.test(f.name));
  if (!files.length) return;
  for (const f of files) {
    const cls = f.name.replace(/\.(glb|gltf)$/i, '');
    status(`Loading ${f.name} (${(f.size / 1e6).toFixed(1)} MB)…`);
    try {
      const g = await loadFile(f);
      const root = g.scene;
      const weaponMeshes = {};
      root.traverse(o => {
        if (o.isMesh) { o.castShadow = true; o.receiveShadow = true; o.frustumCulled = false; }
        const w = weaponOf(o.name);
        if (w) (weaponMeshes[w] ??= []).push(o);
      });
      const clips = {};
      for (const c of g.animations) {
        const m = /^TP_([A-Za-z]+)_([A-Za-z]+)$/.exec(c.name);
        if (!m || m[1] === 'Pistol') continue;
        (clips[m[1]] ??= {})[m[2]] = c;
      }
      const box = new THREE.Box3().setFromObject(root);
      chars[cls] = { root, mixer:new THREE.AnimationMixer(root), clips, weaponMeshes, height:box.max.y - box.min.y };
      status(`Loaded ${Object.keys(chars).length} character(s).`);
    } catch (e) { console.error(e); status(`Couldn't load ${f.name}: ${e.message || e}`); }
  }
  fillChars();
}
// drag-drop / picker live in the plain script in the page (they work even if this bundle fails); hand them the loader
window.__addFiles = addFiles;
// models baked into the page: <script type="application/octet-stream" data-name="Outlaw.glb">base64</script>
(async () => {
  const tags = [...document.querySelectorAll('script[data-name]')];
  if (!tags.length) return;
  const files = [];
  for (const t of tags) {
    status(`Unpacking ${t.dataset.name}…`);
    const blob = await (await fetch('data:model/gltf-binary;base64,' + t.textContent.trim())).blob();
    files.push(new File([blob], t.dataset.name)); t.textContent = '';
  }
  const order = ['Outlaw', 'MrShotgun', 'RocketGuy', 'Sniper', 'Mechanic', 'Greg'];
  files.sort((a, b) => order.indexOf(a.name.split('.')[0]) - order.indexOf(b.name.split('.')[0]));
  await addFiles(files);
  $('char').value = files[0].name.split('.')[0]; showChar($('char').value);
})();
if (window.__pending && window.__pending.length) { const p = window.__pending.splice(0); addFiles(p); }

// ---------------- UI
function fillChars() {
  const sel = $('char'), keep = sel.value;
  sel.innerHTML = '';
  for (const k of Object.keys(chars)) sel.add(new Option(CLASS_NAME[k] || k, k));
  sel.value = keep && chars[keep] ? keep : Object.keys(chars)[0];
  showChar(sel.value);
}
$('char').onchange = e => showChar(e.target.value);
$('weapon').onchange = e => showWeapon(e.target.value);

function showChar(name) {
  if (cur) scene.remove(cur.root);
  cur = chars[name]; if (!cur) return;
  scene.add(cur.root);
  if (skel) { scene.remove(skel); skel = null; }
  if ($('wire').checked) { skel = new THREE.SkeletonHelper(cur.root); scene.add(skel); }
  const wsel = $('weapon'); wsel.innerHTML = '';
  for (const w of Object.keys(cur.clips)) wsel.add(new Option(w.replace(/([a-z])([A-Z])/g, '$1 $2'), w));
  showWeapon(wsel.value);
  setCam('tp');
}
function showWeapon(w) {
  curWeapon = w;
  for (const [k, list] of Object.entries(cur.weaponMeshes)) for (const m of list) m.visible = (k === w);
  const box = $('acts'); box.innerHTML = '';
  const have = cur.clips[w] || {};
  ACTION_ORDER.forEach((a, i) => {
    if (!have[a]) return;
    const b = document.createElement('button'); b.className = 'act'; b.dataset.a = a;
    b.textContent = `${i + 1}. ${ACTION_LABEL[a]}`; b.onclick = () => playAction(a); box.appendChild(b);
  });
  playAction(have[curAction] ? curAction : 'Idle');
}
function playAction(a) {
  const clip = cur?.clips[curWeapon]?.[a]; if (!clip) return;
  curAction = a;
  cur.mixer.stopAllAction();
  action = cur.mixer.clipAction(clip);
  action.setLoop(THREE.LoopRepeat).reset().play();
  action.paused = !playing;
  document.querySelectorAll('.act').forEach(b => b.classList.toggle('on', b.dataset.a === a));
}
$('play').onclick = togglePlay;
function togglePlay() { playing = !playing; if (action) action.paused = !playing; $('play').textContent = playing ? '⏸ Pause' : '▶ Play'; }
function step(d) {
  if (!action) return;
  if (playing) togglePlay();
  const dur = action.getClip().duration;
  action.time = ((action.time + d / FPS) % dur + dur) % dur; cur.mixer.update(0);
}
$('prev').onclick = () => step(-1); $('next').onclick = () => step(1);
$('scrub').oninput = e => {
  if (!action) return;
  if (playing) togglePlay();
  action.time = e.target.value / 1000 * action.getClip().duration; cur.mixer.update(0);
};
$('speed').oninput = e => $('spdv').textContent = (+e.target.value).toFixed(2) + '×';
$('wire').onchange = () => cur && showChar($('char').value);
addEventListener('keydown', e => {
  if (e.target.tagName === 'SELECT') return;
  if (e.code === 'Space') { e.preventDefault(); togglePlay(); }
  else if (e.key === 'ArrowLeft') step(-1);
  else if (e.key === 'ArrowRight') step(1);
  else if (/^[1-7]$/.test(e.key)) playAction(ACTION_ORDER[+e.key - 1]);
});

// cameras (character faces +Z in glTF)
function setCam(kind) {
  const h = cur ? cur.height : 1;
  const t = new THREE.Vector3(0, h * 0.55, 0); let p;
  switch (kind) {
    case 'tp':    p = new THREE.Vector3(-0.55, h * 1.15, -1.9); t.set(-0.1, h * 0.65, 0.6); break;   // over the right shoulder
    case 'front': p = new THREE.Vector3(1.2, h * 0.9, 1.9); break;
    case 'side':  p = new THREE.Vector3(2.3, h * 0.55, 0); break;
    case 'back':  p = new THREE.Vector3(0, h * 0.8, -2.4); break;
    case 'top':   p = new THREE.Vector3(0.001, 3.2, 0); t.set(0, 0.4, 0); break;
    case 'close': p = new THREE.Vector3(0.45, h * 0.8, 1.05); t.set(-0.05, h * 0.6, 0.25); break;
  }
  camera.position.copy(p); controls.target.copy(t); controls.update();
}
document.querySelectorAll('[data-cam]').forEach(b => b.onclick = () => setCam(b.dataset.cam));

// ---------------- loop
function resize() {
  const w = innerWidth, h = innerHeight;
  renderer.setSize(w, h); camera.aspect = w / h; camera.updateProjectionMatrix();
}
addEventListener('resize', resize); resize(); setCam('front');
const clock = new THREE.Clock();
renderer.setAnimationLoop(() => {
  const dt = clock.getDelta() * +$('speed').value;
  if (cur) {
    cur.mixer.update(playing ? dt : 0);
    if (action) {
      const d = action.getClip().duration;
      $('scrub').value = Math.round((action.time % d) / d * 1000);
      $('time').textContent = `frame ${Math.floor((action.time % d) * FPS) + 1} / ${Math.round(d * FPS)}  ·  ${curAction}`;
    }
    const mv = MOVE[curAction];
    if (mv && playing && $('moving').checked) {           // floor slides opposite the walk so the feet look planted
      const s = SPEED[curAction] * (HEIGHT[$('char').value] || 1) * dt / (20 / 40);   // 1 texture tile = 0.5 m
      floorTex.offset.x += mv[0] * s;
      floorTex.offset.y -= mv[2] * s;
    }
  }
  controls.update();
  renderer.render(scene, camera);
});
if (!Object.keys(chars).length) status('Ready. Drop the .glb files from chez\\Viewer (or click the box).');
