---
name: "cheeseteam-modeling"
description: "How to model, animate and build maps for CheeseTeam the way the owner wants: procedural Blender Python, real-world mechanics, zero clipping, natural arms, real reloads, no slop, careful handling of the owner's live Blender. Use before any CheeseTeam 3D work: guns, ammo, characters, animations, maps, exports or hand-off folders."
---

# CheeseTeam modelling: how to work

CheeseTeam is a team shooter. The characters are cheese wedges with stick arms and legs. The look is stylised and TF2-ish. Guns, mechanisms and buildings must still be believable and work the way the real thing does.

## 1. How the owner works

- **They judge what they see, not the code.** Only call something done, fixed or clip-free after a check you actually ran: a render, a viewport screenshot, or a clip/reach test.
- **No slop.** The owner rejects all of these:
  - plain recoloured cubes
  - floating parts
  - posts and braces that don't touch what they hold at both ends
  - clipping
  - spider-bent arms
  - animations where a gun just "shakes"

  If you simplified something, say so.
- **Zero clipping tolerance.** Guns in bodies, arms through the body or hats, stairs in walls, and beams through stairwells all count.
- **Real mechanisms.** A reload actually works the gun. Spinning parts really spin (they don't vibrate). Projectiles really leave the weapon.
- **Requests arrive as fast, casual voice notes with typos.** Work out the most sensible intent and act on it. Ask only when two readings lead to really different work.
- **Replies are short and plain:** what you did, what you checked, what's still open, and where the output is. Skip the walls of text and the internal jargon. Playful is welcome if the owner's preferences ask for it, but on top of clear content, never instead of it.
- **Hard rules:** never mention "Jarvis". Never share tunnel URLs or connection secrets. Never open a pull request unless asked. Do commit and push your work to the branch you were given.

## 2. The owner's live Blender

- You drive their real Blender through the Blender MCP. **Use only the Blender connection they tell you to use.** Other chats may own other Blender instances or ports; never touch those.
- **"Give Blender a min."** Bakes, exports and full animation passes freeze Blender for 10–60 minutes. MCP calls time out after about 60 s, but the code keeps running and later calls **queue up behind it**. So:
  - Launch a long job **once**, and have it write its progress to a log file.
  - **Don't poll.** Schedule one check later (about 30–45 min) and read the log then.
  - Never stack retries. Queued checks pile up and Blender shows "Not Responding".
  - If Blender isn't connected, say so once and stop.
- **Use your cloud sandbox for heavy lifting.** It usually has Blender as a Python module (`bpy`), plus numpy and Pillow. Build, test, render previews and run checks there. Use the owner's Blender for final bakes and exports into their folders, or when they want to watch something build. If they say "build it in your sandbox", do exactly that.
- **Code lives in git, not in the scene.** Edit the Python modules, commit and push. The owner's Blender then pulls the files by commit SHA. Clear the modules from `sys.modules` before importing, so stale code never runs.
- **Everything is procedural Python,** so it is exact and can be rebuilt. Don't hand-edit the scene; the next rebuild would wipe it.

## 3. Modelling standard

**Geometry**
- Model at real-world size in metres. Guns are built real-size and used at **0.7 scale** on the characters.
- Build parts the way the real thing is built:
  - lathes for barrels, cylinders and rounds
  - extruded profiles for frames
  - real boolean cuts for ports, bores, slots and loading channels
- A part needs whatever lets it work. A loading gate needs a channel behind it, a bolt gun needs an open action, and a lever gun needs an ejection slot.
- Bevel hard edges with chamfers of a few mm.
- Weld each wall into one mesh with real reveals around its openings. Never stack boxes to fake a wall; you get grooves and z-fighting.
- Close lathe profiles onto the axis so the shells are solid. Open shells flip normals, which breaks edge-wear masks: a part suddenly renders white or bare.
- Every moving part is a separate mesh that shares the gun's origin, so it attaches the same way and the animation moves it. Moving parts include:
  - cylinder, loading gate, ejector rod
  - magazine (with its body hidden inside the grip)
  - slide, bolt, lever, pump, charging handle
  - spinning barrels

  Split them off after the texture bake and export each one as its own file.

**Materials**
- No flat colours: every surface gets a real texture. Use Poly Haven textures where you can get them, or a procedurally painted TF-style set otherwise.
- Colour = texture × (target colour ÷ texture average). Every surface then lands on the agreed palette and keeps its detail.
- Team colours: Cheddar `#C8601C`, Bleu `#33669F`. The visual bible skill has the rest.
- Export with baked PBR maps: BaseColor, Roughness, Metallic, Normal and ORM.

**Ammo**
- Model real calibres: case, bullet, primer and rim.
- Each calibre has three pieces: the *bullet* (what flies), the *round* (live) and the *casing* (fired).
- Origin at the base, nose pointing forward.

## 4. Animation standard (third person)

**Rig**
- Bones: a `weapon` socket plus spare socket bones.
- A second gun, every moving part and every ammo piece each get their own spare socket.
- Scaling a socket bone to about 0 means "this piece isn't there right now".

**Actions per weapon**
- Idle, WalkF, WalkB, StrafeL, StrafeR, Fire and Reload.
- Rifles also get Aim and AimFire. Weapons that never reload skip Reload.

**Method**
- Keyframes are procedural.
- Arms use two-bone IK. Search the elbow pole for a pose that clears the real meshes: body, pelvis, hats and the held gun.
- Prefer last frame's elbow (hysteresis) so it never twitches.
- Feet plant during the gait.
- Each channel interpolates between its own keys.

**Natural arms.** This was the biggest complaint.
- Keep every hand target at **60–95 % of the arm's reach**, with the elbow hanging **down and slightly out**.
- A hand jammed close to the shoulder of a long arm folds the arm and pokes the elbow out sideways. It looks terrible.
- Check reach ratios with a quick offline solver before baking.

**Holds**
- Face forward: the head looks where the gun points, never at the gun.
- Pistols are held out in front at shoulder height.
- On long guns the support hand really grips the forend, with no gap.
- Aiming puts the stock at the face and the sights at the eye.

**Fire works the gun**
- Cylinders index and slides cycle.
- Bolt and lever guns are worked by hand after each shot, and the empty case flies out.
- Recoil rocks the whole body.
- Spinning barrels loop seamlessly.

**Reload follows the real procedure**
- The parts move and the hands hold real ammo: empties drop, fresh rounds come from a pouch, then the mag is seated and the slide racks.
- A dropped piece falls to the floor. Pieces that aren't there are hidden by bone scale, never left floating.

**Walk speed.** Snappy cycles of about 12–13 frames read natural. Slower ones look sluggish.

**Clip check on every frame**
- Weapon vs body, weapon vs accessories, arms vs body and hats, leg vs leg.
- Also log IK misses and reach misses.
- Export only at **0 everywhere**.

## 5. Maps

- Use a code kit:
  - a transform stack
  - welded walls with openings
  - stair and rail parts
  - slabs with holes
  - AABB colliders
  - a material table
- Opposing team bases are identical: one function, rotated (point-symmetric).
- Check walkability with a flood fill using the player rules (radius 0.36 m, step 0.5 m, height 1.8 m). Terrain slopes stay walkable everywhere except deliberate cliffs.
- Check stairs, beams and rails for clipping. Every column and brace touches what it holds at both ends.
- Follow whatever rules the owner set for that map, for example the boundary style, or "no props unless asked".

## 6. Delivery

- **The hand-off folder stays simple.**
  - At the top level: only a `READ ME.txt` that explains everything, and the animation viewer.
  - In the main folders: only what goes into the game (FBX + textures).
  - Everything else goes into an `_Extras` folder: Blender files, GLBs, previews, pivot data, review sheets.
  - Move files, never delete them.
  - Regenerate the README after every update.
- **The viewer** is a single HTML file. three.js is bundled inline (no CDN), the models are baked in as base64, and it works on a double-click. If WebGL is off it shows a clear error, plus a hint to use Chrome/Edge or turn on hardware acceleration.
- **Verify before handing over:** render check sheets or screenshots of the new work, from the angles that matter.

## 7. Working loop

1. Understand the ask. Restate it in one line only if it's ambiguous.
2. Design with numbers first: reach ratios, hinge points, timings, layout. Use offline solvers or stub tests in the sandbox.
3. Write or edit the modules, then smoke-test the logic in the sandbox.
4. Commit and push.
5. Run in Blender as one logged job. Schedule a single check; don't poll.
6. Read the log and fix every nonzero clip, reach or IK miss. Look at the renders.
7. Export, update the hand-off folder and regenerate its README.
8. Report briefly: what changed, what you verified, what's left.
