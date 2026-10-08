---
name: "blender-modeling"
description: "How to do 3D work for this owner: procedural Blender Python, real-world mechanics, zero clipping, natural poses, real reload/fire animations, no slop, and careful handling of the owner's live Blender. Use before any 3D modelling, texturing, rigging, animation, game-map building or asset export/hand-off work."
---

# 3D work for this owner: how to do it

## 1. How the owner works

- **They judge what they see, not the code.** Never say something is done, fixed or clip-free unless a check you actually ran says so: a render, a viewport screenshot, or a clip or reach test.
- **No slop.** The owner rejects all of these:
  - plain recoloured cubes;
  - floating parts;
  - posts and braces that don't touch what they hold at both ends;
  - clipping;
  - spider-bent limbs;
  - animations that are just an object shaking.

  If you simplified something, say so.
- **Zero clipping tolerance.** All of these count: props in bodies, limbs through the torso or hats, stairs in walls, beams through stairwells.
- **Real mechanisms.** Things move the way the real thing moves:
  - A reload actually works the gun.
  - Spinning parts spin; they don't vibrate.
  - Projectiles actually leave the weapon.
  - Doors hinge where real hinges are.
- **Requests come as fast, casual voice notes with typos.** Work out the most sensible intent and act on it. Only ask when two readings lead to really different work.
- **Replies are short and plain.** Say what you did, what you checked, what's still open and where the output is. No walls of text, no internal jargon. A playful tone is fine if the owner's preferences ask for it, but on top of clear content, never instead of it.
- **Hard rules:**
  - Never mention "Jarvis".
  - Never share tunnel URLs or connection secrets.
  - Never open a pull request unless asked.
  - Do commit and push work to the branch you were given.

## 2. The owner's live Blender

- You drive the owner's real Blender through the Blender MCP. **Use only the Blender connection they tell you to use.** Other chats may own other Blender instances or ports. Never touch those.
- **"Give Blender a min."** Bakes, exports and long animation passes freeze Blender for 10–60 minutes. MCP calls time out after about 60 s, but the code keeps running and later calls **queue up behind it**. So:
  - Launch a long job **once** and have it write progress to a log file.
  - **Don't poll.** Schedule one check later (about 30–45 min) and read the log then.
  - Never stack retries. Queued checks pile up and Blender shows "Not Responding".
  - If Blender isn't connected, say so once and stop.
- **Do the heavy lifting in your cloud sandbox when you can.** It usually has Blender as a Python module (`bpy`), plus numpy and Pillow. Build, test, render previews and run checks there.
  - Use the owner's Blender for final bakes and exports into their folders, or when they want to watch something build.
  - If they say "build it in your sandbox", do exactly that.
- **Code lives in git, not in the scene.** Edit the Python modules, commit and push. The owner's Blender then pulls the files by commit SHA. Clear the modules from `sys.modules` before importing so stale code never runs.
- **Everything is procedural Python,** so every build is exact and can be repeated. Don't hand-edit the scene, because the next rebuild would wipe those edits.

## 3. Modelling standard

**Geometry**
- Build at real-world size, in metres. If an asset is shown at a different scale in-game, apply that as one documented scale factor; never model it at the wrong size.
- Build parts the way the real thing is made:
  - lathes for round parts;
  - extruded profiles for frames and plates;
  - real boolean cuts for ports, bores, slots and channels.

  If a mechanism needs an opening to work, cut the opening.
- Bevel hard edges with chamfers of a few mm. Each wall is one welded mesh with real reveals around its openings. Never stack boxes to fake a wall; you get grooves and z-fighting.
- Close lathe profiles onto the axis so the shells are solid. Open shells flip normals and break edge-wear masks: the part renders white or bare.
- **Every moving part is its own mesh** and shares the parent's origin, so it attaches the same way and the animation moves it. This covers cylinders, gates, mags, slides, bolts, levers, pumps, handles, rotors and doors. Split them off after the texture bake and export each one as its own file.
- Small consumables (rounds, casings, shells, projectiles) are real separate pieces at real size. Put the origin at the base, pointing forward.

**Materials**
- No flat colours. Every surface gets a real texture: Poly Haven where it's available, or a procedurally painted texture set when you work offline.
- Colour = texture × (target colour ÷ texture average). Every surface lands on the agreed palette and keeps its detail. Use the project's own palette and style guide when there is one.
- Export with baked PBR maps: BaseColor, Roughness, Metallic, Normal and ORM.

## 4. Animation standard

**Rig.** Held items go on a socket bone. Extra items (a second weapon, moving parts, ammo pieces) each get their own spare socket bone. Scaling a socket bone to about 0 means the piece isn't there right now.

**Method:**
- Keyframes are procedural.
- Limbs use two-bone IK. Search the elbow and knee pole for a pose that clears the real meshes: body, hats and accessories, the held item.
- Prefer last frame's pole (hysteresis) so elbows don't twitch.
- Feet stay planted during the gait.
- Each channel interpolates between its own keys.

**Natural limbs.** This was the biggest complaint.
- Keep hand targets at **60–95% of the arm's reach**, with elbows hanging **down and slightly out**.
- A hand jammed close to the shoulder of a long arm folds the arm and pokes the elbow out sideways. It looks terrible.
- Check reach ratios with a quick offline solver before baking.

**Holds:**
- The head looks where the item points, never at the item.
- One-handed items are held out in front.
- On two-handed items the support hand really grips, with no gap.
- Aiming puts the stock at the face and the sights at the eye.

**Using an item works it.** Cylinders index, slides cycle, bolts and levers get worked by hand, empties fly out and recoil rocks the whole body. Looping motions (spinning barrels, wheels) loop seamlessly.

**Reloads and other procedures follow the real steps.** The parts move and the hands hold real pieces:
- Empties drop and fresh rounds come from a pouch.
- The mag gets seated and the slide gets racked.
- Dropped pieces fall to the floor.
- Pieces that aren't there are hidden by bone scale, never left floating.

**Pace.** Snappy cycles read natural. A walk cycle of about 12–13 frames at 30 fps is a good start; sluggish cycles look wrong.

**Clip-check every frame:**
- held item vs body;
- held item vs accessories;
- limbs vs body and hats;
- leg vs leg.

Also log IK misses and reach misses. Export only at **0 everywhere**.

## 5. Game maps

- Use a code kit with:
  - a transform stack;
  - welded walls with openings;
  - stair and rail parts;
  - slabs with holes;
  - AABB colliders;
  - a material table.
- Bases for opposing teams are identical: one function, rotated (point-symmetric).
- Check walkability with a flood fill using the player rules (for example radius 0.36 m, step 0.5 m, height 1.8 m). Terrain slopes stay walkable except at deliberate cliffs.
- Clip-check stairs, beams and rails. Every column and brace touches what it holds at both ends.
- Follow whatever rules the owner set for that map, for example the boundary style or "no props unless asked".

## 6. Delivery

- **Keep the hand-off folder simple:**
  - The top level holds only a `READ ME.txt` that explains everything, plus any viewer.
  - The main folders hold only what goes into the game (FBX + textures).
  - Everything else goes into an `_Extras` folder: source .blend files, GLBs, previews, pivot data, review sheets.
  - Move files, never delete them. Regenerate the README on every update.
- **A viewer is one HTML file:**
  - three.js bundled inline (no CDN), with the models baked in as base64, so it works on a double-click.
  - If WebGL is off, it shows a clear error and suggests Chrome/Edge or turning on hardware acceleration.
- **Verify before handing over.** Render check sheets or screenshots of the new work, from the angles that matter.

## 7. Working loop

1. Understand the ask. Restate it in one line only if it's ambiguous.
2. Design with numbers first: reach ratios, hinge points, timings, layout. Use offline solvers or stub tests in the sandbox.
3. Write or edit the modules, then smoke-test the logic in the sandbox.
4. Commit and push.
5. Run in Blender as one logged job. Schedule a single check instead of polling.
6. Read the log and fix every nonzero clip, reach or IK miss. Look at the renders.
7. Export, update the hand-off folder and regenerate its README.
8. Report briefly: what changed, what you verified, what's left.
