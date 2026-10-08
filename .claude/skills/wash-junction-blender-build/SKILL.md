---
name: "wash-junction-blender-build"
description: "Rebuild, edit or extend the Wash Junction CTF map in the user's Blender exactly as it was originally built (code-built kit, Poly Haven textures, fence + straight slopes). Use for any work on the cheese-team CTF map in Blender."
---

# Wash Junction — how the map is built in Blender

The map is not hand-modelled. It is produced by a small Python construction kit that runs inside the user's Blender through the Blender MCP (`execute_blender_code`). Every wall, stair, rail and slab comes from code, so a rebuild is exact and repeatable. Follow this file and you get the same result.

## 0. Which Blender to drive

- There are two Blender connections on this PC. **blender** (port 9876) belongs to the main map chat. **blender2** (port 9877) is the second Blender for another chat. Use the one the user tells you to use. If you are the second chat, use only the `blender2` tools and never touch `blender`.
- Before working: `get_addon_status` and `get_scene_info`. If the target Blender has no `COL-WashJunction` collection, open `WashJunction.blend` (see §1) or run a full rebuild (§3).

## 1. Files (on the user's PC)

`C:\Users\mrsobo\Documents\LonelyRoad\WashJunction_Blender\` (the same instructions are also there as README.md)

| File | What it does |
|---|---|
| `build.py` | Step runner: `step('start'|'C'|'B'|'M'|'E'|'F', texdir)`, `sky()`, `finish(outdir)` (writes `wj_data.json` + GLB) |
| `wjkit.py` | The kit: transform stack, `box/obox/cyl/quad/wall/rect_minus`, colliders, `MATS` material table, bevel + UV + grime finishing, Blender material builder |
| `wjparts.py` | Architecture parts: `rail, stairs, opening, window, cmu_wall, ibeam, hbeam, downpipe` |
| `wjbase.py` | One team base (spawn hall, courtyard, catwalk, stair house, service corridor, **Cold Store** flag room, storm drain, pump room, depot, balcony, fire escape) |
| `wjmiddle.py` | Middle: field, highway, culvert junction under the road, the two washes with wing walls and end walls |
| `wjenv.py` | Surroundings: straight-slope terrain ring and the perimeter chain-link fence (placements + colliders) |
| `texman.json` | Average colour of every texture (used for colour normalisation) |
| `textures\*.webp` | 86 Poly Haven textures at 1k (`<id>_d.webp` diffuse, `<id>_n.webp` normal; `_g_` = greyscale variant for team tinting) |
| `WashJunction.blend` | The saved scene |

## 2. Coordinates and layout (do not change unless the user asks)

- The kit works in **game coordinates**: X right, **Y up**, Z toward the camera, metres. A vertex goes into Blender as `(x, -z, y)` (`T2B`). glTF export converts back exactly.
- Each base is built in a base-local frame: `d` along X (0 = back wall of spawn, 38 = depot front), Z lateral (±16). Cheddar (C) is `at(-74, 0, 0, 0)`; Bleu (B) is `at(74, 0, 0, π)`. The bases are identical and point-symmetric.
- Base-local layout: spawn hall d0–12 (brick, 6.8 m tall); courtyard d12–26 with the north catwalk at y5 and the stair house (d14–20, z −15.6…−9.5) going down to y −5; service corridor; **Cold Store** flag room d12.7–25.3, z −2.3…14.3, y −5…−1 (flag spot = steel floor scale at d19, z6); storm drain d25.3–65.6, z9–13, y −5 (it runs into the culvert junction under the road); pump room d42–50; depot d26–38, two storeys (CMU ground floor, team-clad upper floor, slab at 4.7–5.0, roof at 10.3); balcony d38–40.8 at y5; fire escape down at z −17…−10.
- Middle: field |x|<36, |z|<34; road z ±6; culvert chamber x ±8, z ±14, y −5; washes ramp down from z ±14.4 to ±24, then a bed at y −1.6 to an end wall at z ±31.6–32.2.
- Flags: C (−55, −5, 6), B (55, −5, −6). Spawns: C (−68, 0, 0), B (68, 0, 0).
- Fence loop (game x,z): middle rims at z ±31.9 (sitting on the wash end walls at y 1.1); x ±36 between z ±20.3 and ±31.9; base flanks z ±20.3 for |x| 36–82.3; behind the spawns x ±82.3.

## 3. Full rebuild (exact recipe)

```python
import bpy, sys
SRC = r"C:\Users\mrsobo\Documents\LonelyRoad\WashJunction_Blender"
if SRC not in sys.path: sys.path.insert(0, SRC)
for m in ('build','wjkit','wjparts','wjbase','wjmiddle','wjenv'): sys.modules.pop(m, None)   # always reload
import build
T = SRC + r"\textures"
for s in ('start','C','B','M','E','F'):   # start clears COL-WashJunction only; user objects are untouched
    print(build.step(s, T))
build.sky()
for o in bpy.context.selected_objects: o.select_set(False)
bpy.ops.wm.save_mainfile()
```

- Step `F` (fence) instances the Poly Haven fence from hidden source objects `SRC-fence_panel` and `SRC-fence_post` in collection `COL-Sources`. If they are missing: run `download_polyhaven_asset('modular_chainlink_fence', 'models', '1k')`, then keep `modular_chainlink_fence_double` → rename to `SRC-fence_panel` and `modular_chainlink_fence_post` → `SRC-fence_post`. Move both into `COL-Sources` at location (0,0,0), delete the other imported pieces, and hide the collection. The panel's local X runs from −1.952 to −0.038 (one 2 m bay that ends at its origin).
- Expected counts: C ≈ 24 objects / 32.1k faces, B ≈ 24 / 32.2k, M ≈ 14 / 2.6k, E ≈ 25.2k faces, F = 472 fence pieces, about 715 colliders.
- Building in steps (C, then B, then M…) lets the user watch the map appear. Set the viewport to Material Preview once. After that, leave the user's viewport alone unless you need a check view.

## 4. How the kit makes things look built, not "recoloured shapes"

- **Walls are one welded mesh per call.** `wall(mat, axis, s0, s1, c, t, y0, y1, holes)` builds a grid around the openings. The openings get real reveal faces and the wall gets real colliders. Extra edge loops at 0.6 m and 0.25 m below the top carry floor grime. Never stack separate boxes to make a wall; you get grooves and z-fighting.
- **Bevel:** in `finish_bmesh` every edge whose face angle is over 0.6 rad gets a 12 mm chamfer (`bmesh.ops.bevel`, clamp on). Call `normal_update()` before bevelling and before UVs, or nothing bevels and every UV is wrong. Big floor slabs use `box(..., bevel=False)` (they land in a `~flat` part) so their seams don't show.
- **UVs:** world-metre box projection per face (top: x,y; sides: y,z or x,z). Each material's texture tiles at its own size via a Mapping node set to `1/tile`.
- **Colour:** every material is `texture × (target colour ÷ texture average)` from `texman.json`, so each surface lands on its agreed colour but keeps all the texture detail. Team materials have `_C` / `_B` variants (Paint, Clad, SteelT, Shutter) and use the greyscale `_g` textures.
- **Grime:** a per-corner colour attribute `Col` (noise variation, darkening near each floor level, ceilings 15% darker) is multiplied into the base colour.
- **Material table** (`MATS` in wjkit): name → (texture id, metres per tile, sRGB colour, roughness, metallic). Add new materials there, never inline.

## 5. Kit cheat-sheet

- `K.at(x,y,z,ry)` / `K.pop()` push and pop transforms. `K.group` picks the target collection (`BaseC`, `BaseB`, `Middle`, `Env`).
- `box(mat, x0,y0,z0, x1,y1,z1, col=False, bevel=True)` · `obox(mat, cx,cy,cz, w,h,d, (rx,ry,rz))` (three.js XYZ euler) · `cyl(mat, x,y,z, r, h, axis='y'|'x'|'z', seg)` · `quad(mat, A,B,C,D)` (counter-clockwise seen from the visible side) · `rect_minus(x0,z0,x1,z1, holes, fn)` · `col(...)` adds a collision box · `light/area/label` write gameplay data.
- Parts: `P.rail(x0,z0,x1,z1,y, panel=…)`, `P.stairs(x,z,ry,w,y0,y1, kind='steel'|'conc', rail_sides=…)` (ascends along local +x), `P.opening(...)` (frame + reveal liners), `P.window(...)`, `P.cmu_wall(...)`, `P.ibeam(...)` (column), `P.hbeam(x0,x1,z,ytop)` (ceiling beam), `P.downpipe(...)`.
- For any brace or rod, compute both end points first, then use `obox` with length = distance and angle = `atan2`. Check that both ends land on something.

## 6. The user's rules for this map

1. **Keep the layout** (§2). The old "vault" theme is gone. The flag room is a practical **Cold Store** (insulated panel walls, kick curbs + yellow bump rails, column grid with yellow corner guards, beam ceiling, floor scale).
2. **Nothing may be a plain recoloured shape.** Everything gets a real Poly Haven texture through `MATS`.
3. **Zero clipping.** Stairs, stringers, beams and rails must clear walls and each other. Every column, post, brace and rod must touch what it holds up at **both ends** (the user checks this).
4. The bases stay **identical** (built from one function and rotated).
5. Boundary: a **chain-link fence** all round. Outside it: flat for 12 m, then **one straight, steady slope** to a 60 m ridge. **No rocks, no lumpy or curvy hills.**
6. Props, doors, signs and words were removed on purpose. Add gameplay or "life" pieces only when the user asks, and build them the same way (kit or real Poly Haven/Sketchfab models, never untextured shapes).
7. The user watches in Blender. Show progress there; an HTML preview is no longer needed. Renders aren't required. Viewport screenshots are fine for checking.

## 7. Editing workflow

- Edit the `.py` modules, never one-off geometry in the scene; the next rebuild would wipe it.
- If you have a cloud sandbox with `pip install bpy` (Blender 5.x module), test there first: `python3 build.py <texdir> <outdir>`, which runs headless and prints the counts. Then copy to the PC.
- Copying files to the PC with `device_commit_files`: **use a new staged path (a new folder) every time**; re-using a staged path can write a stale copy. **Never run the commit and the Blender exec in the same parallel batch.** Afterwards, check the MD5 on the PC (PowerShell `Get-FileHash`) before rebuilding.
- If you have no sandbox, edit the files on the PC directly and rebuild.
- After editing, always pop the modules from `sys.modules` before importing (§3), or Blender keeps running the old code.

## 8. Checks before saying it's done

- Counts match §3 (or changed only where you meant them to).
- **Walkability:** `finish(outdir)` writes `wj_data.json` (colliders are AABBs `[x0,y0,z0,x1,y1,z1]` in game coords). Flood-fill with the player rules (radius 0.36, step 0.5, height 1.8) from spawn C. Every room must be reachable, enemy flag about 21 s at sprint, **0 nodes outside the fence**.
- **Clipping:** for each new part, compare its bounding box with nearby wall and slab colliders. Check stairs against side walls and ceiling beams over stair holes.
- One or two `get_viewport_screenshot` check views of what you changed, then `bpy.ops.wm.save_mainfile()`.

## 9. Known gotchas

- In Blender 5.x Mix nodes, use input indices for RGBA (`inputs[6]`/`[7]`, `outputs[2]`), not names.
- The glTF exporter writes a dummy white `COLOR_0` and the real grime as `COLOR_1`. Swap them if you export for another engine. Don't run gltf-transform `dedup()` (it merges materials that only differ by name) or `meshopt()` (it squashes the metre-scale UVs).
- Poly Haven model downloads land at the scene origin as `<asset>_LOD0` or similar names. Rename them to `SRC-…`, hide them, and place linked duplicates (`obj.copy()`).
- Game yaw `ry` equals Blender Z rotation `ry` under `T2B`.