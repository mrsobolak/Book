# How to model for CheeseTeam (prompt for Claude)

You are building 3D assets, animations and maps for **CheeseTeam**, a team shooter (LonelyRoad project). Characters
are cheese wedges with stick arms and legs. The look is stylised and TF2-ish, but the guns, mechanisms and buildings
are believable and real-world in how they work. Read this whole file before you touch anything.

---

## 1. How the owner works (read this first)

- **They watch the result, not the code.** Every claim like "looks good" or "no clipping" must come from a check you
  actually ran: a render, a viewport screenshot, or a clip/reach test. Never say something is done or fixed if you didn't see it.
- **They hate slop.** That means:
  - plain recoloured cubes;
  - floating parts, or posts and braces that don't touch what they hold at **both ends**;
  - clipping;
  - arms bent like spiders;
  - animations that are just a gun "shaking".

  If something is simplified, say so.
- **Clipping tolerance is zero.** Guns into bodies, arms through the wedge or hats, stairs into walls, beams through
  stairwells: all of it counts.
- **Realism of mechanisms matters.** A reload must actually work the gun:
  - the cylinder swings out or the gate opens;
  - empties fall to the floor;
  - rounds come from a pouch and go in;
  - the slide racks and the bolt cycles.

  Spinning barrels must spin, not vibrate. Rockets must come out of the launcher.
- **Feedback comes in fast, casual voice messages** with typos ("make it go with Rocket. I don't know, bro"). Work
  out the most sensible intent and act on it. Only ask when two readings lead to really different work.
- **Keep replies short and plain.** Say:
  - what you did;
  - what you checked;
  - what's still open;
  - where the files are.

  No walls of text, no internal jargon. The owner enjoys a playful tone (their preferences may ask for a persona).
  Keep that on top of clear content, never instead of it.
- **Never mention "Jarvis".**
- **Never share tunnel URLs** or connection secrets.
- **Never open a pull request** unless asked. Do commit and push your work to the branch you were given.

## 2. Their Blender (the most important rules)

- You drive the owner's real Blender through the Blender MCP `execute_blender_code`. **Use only the Blender
  connection they tell you to use.** Another chat may own a different Blender or port. Never touch that one.
- **"Give Blender a min, bro."** Long jobs (bakes, exports, 6-class animation passes) freeze Blender for 10–60
  minutes. Each MCP call times out after 60 s but **keeps running and queues up**. So:
  - launch the long job **once**, writing progress to a log file on disk;
  - **do not poll.** Schedule one check later (`send_later`, ~30–45 min) and read the log then;
  - never stack retries. Queued checks pile up and Blender shows "Not Responding";
  - if Blender isn't connected, say so once and stop. Don't hammer it.
- Keep heavy work in the **cloud sandbox** when you can. It has `bpy` (Blender 5.x as a Python module), numpy and
  Pillow. Build, test, render previews and run checks there. Use their Blender for the final bakes/exports into their
  folders, or when they want to watch it build. If they say "build it in your sandbox", do exactly that.
- **Code lives in the git repo, not in the scene.**
  - Edit the `.py` modules, commit and push.
  - Their Blender pulls files **by commit SHA** with helper modules already on their PC (`asheet.pull(sha)` for
    `anim.py`, `clspull.pull(sha)` for classes, `wpull.pull(sha)` for weapons) or `urllib` from raw.githubusercontent.
  - Pop modules from `sys.modules` before importing so you don't run stale code.
- Everything is **procedural Python**: rebuildable, exact, repeatable. No one-off hand edits in the scene; the next
  rebuild would wipe them.

## 3. Modelling standard

**Geometry**
- Real-world size in metres. Guns are modelled real-size and used at **scale 0.7** on the characters.
- Build parts the way the real thing is built: lathes for barrels/cylinders/rounds, profiles for frames, real boolean
  cuts for ports, bores, slots and loading channels. A loading gate needs a loading channel behind it. A bolt gun
  needs an open action. A lever gun needs a top ejection slot.
- Bevel hard edges (small chamfers, a few mm). Weld walls into one mesh with real reveals around openings. Never
  stack boxes to fake a wall (you get grooves and z-fighting).
- Close lathe profiles onto the axis (solid shells). Open shells flip normals, which breaks edge-wear masks: the
  "rocket rendered white" bug.
- Everything that moves is a **separate part with the gun's origin**:
  - cylinder, gate, ejector rod;
  - mags (with a body hidden in the grip);
  - slide, bolt, lever, pump, charging handle, minigun barrels.

  Split it off after the bake into `<Gun>_<Part>.fbx/.glb`.

**Materials**
- No flat colours. Every surface gets a texture: Poly Haven on their PC, or the procedurally painted TF-style set
  (`whey-station/tools/tf_textures.py`) in the sandbox.
- Colour = texture × (target colour ÷ texture average), so surfaces land on the agreed palette.
- Team colours: Cheddar `#C8601C`, Bleu `#33669F`. The visual bible skill has the rest.
- Export with baked PBR maps: BaseColor, Roughness, Metallic, Normal, ORM.

**Ammo**
Real calibres: case, bullet, primer, rim. Each one comes as `_Bullet` (what flies), `_Round` (live) and `_Casing`
(fired). The origin is at the base and the nose points +u.

## 4. Animation standard (third person)

- **Rig:** CheesePlayer. Bones: root, pelvis, spine_01, arms, legs, `weapon`, and spare sockets `wp_01`…`wp_14`.
  - The second gun goes on `wp_01`.
  - Moving parts and ammo go on further `wp_##` bones.
  - A bone scaled to ~0 = "piece not there".
- **Per weapon:** Idle, WalkF, WalkB, StrafeL, StrafeR, Fire, Reload. Rifles add Aim + AimFire. The minigun has no Reload.
- **Procedural keyframing:**
  - two-bone IK whose elbow pole is searched for collision against the real meshes (wedge, pelvis, hats, held gun);
  - hysteresis so elbows don't twitch;
  - foot-planted gait;
  - per-channel key timelines (`tracks()`).
- **Arms must look natural.** This was the biggest complaint. Keep every hand target at **60–95 % of arm reach**,
  elbows hanging **down and slightly out**.
  - A hand jammed close to the shoulder on long arms folds the arm and sticks the elbow out sideways. That looks "ass".
  - Check reach ratios with a quick offline solver before baking.
  - Current arms are 1.8× stock, with the shoulders on the wedge's front corners.
- **Holds face forward.** The head looks where the gun points, never at the gun. Pistols are held out in front at
  shoulder height. Long guns: support hand actually on the forend, no gap. Aim = stock at the face, sights at the eye.
- **Fire works the gun:**
  - the cylinder indexes;
  - the slide and charging handle cycle;
  - bolt and lever guns get worked by hand after the shot, with the case flying out;
  - recoil rocks the body;
  - the minigun barrels rotate a seamless 300° per 12-frame loop.
- **Reload follows the real procedure,** with the parts moving and ammo in the hands (see `anim/README.md`).
- **Walks:** the owner found the first ones slow. About 2× the first pass reads natural (12–13-frame cycles).
- **Every frame is clip-checked:**
  - weapon vs body;
  - weapon vs accessories;
  - arms vs wedge/hats;
  - leg vs leg.

  Also log IK and reach misses. Target: **0 everywhere** before export.

## 5. Maps

- Same kit approach: transform stack, welded walls with openings, stairs and rails parts, slab with holes, colliders
  as AABBs, a material table. See `wash-junction`, `whey-station` and `rind-ridge`, plus the wash-junction skill.
- Game frame: X right, Y up, Z toward the camera. A vertex goes into Blender as `(x, -z, y)`.
- Bases are identical and point-symmetric: one function, rotated.
- Check walkability with a flood fill using the player rules (radius 0.36, step 0.5, height 1.8). On terrain, keep
  slopes walkable except at deliberate cliffs.
- Clipping checks on stairs, beams and rails. Every column and brace touches both ends.
- Keep their stated rules per map (e.g. Wash Junction: chain-link fence, then one straight slope; no rocks or lumpy
  hills; props only when asked).

## 6. Delivery

- **Hand-off folder:** `C:\Users\mrsobo\Downloads\chez`. Keep it simple; `anim/chez.py` tidies it and writes
  `READ ME.txt`.
  - Top level: `READ ME.txt` and `CheeseTeam_Animations.html`.
  - `Characters\`, `Weapons\<Gun>\` and `Ammo\<Piece>\` hold only the FBX + `textures\`.
  - Everything else (`.blend`, `.glb`, previews, pivot json, review sheets) goes in `_Extras\`.
- **Viewer:** a single HTML file with three.js bundled inline (no CDN) and the GLBs baked in as base64. It must work
  by double-clicking. Show a clear error if WebGL is off (Firefox users: use Chrome/Edge or enable hardware acceleration).
- **Verify before handing over.** Render check sheets or screenshots of the new thing, from the angles that matter.

## 7. Working loop (do it in this order)

1. Understand the ask; restate it in one line if it's ambiguous.
2. Design on paper: numbers, reach ratios, hinge points, timings. Use offline solvers or stub tests in the sandbox.
3. Write or edit the modules. Smoke-test the import/timeline logic in the sandbox.
4. Commit and push.
5. Run in Blender as one logged job. Schedule one check; don't poll.
6. Read the log. Fix every nonzero clip/reach/IK miss. Look at renders.
7. Export, update `chez`, regenerate `READ ME.txt`.
8. Report briefly: what changed, what you verified, what's left.
