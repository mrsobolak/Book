# Wash Junction asset kit — how to build a model

Everything is Python run headless in Blender 4.0. Each model has a build script in `src/`.
`kit/assetkit.py` handles UVs, baking, export, collision, LOD, preview render and reports.

```bash
cd /home/user/Book/cheese-team/wash-junction
blender -b -P src/my_script.py -- --draft                  # seconds: assemble + UV + stats report only (no bake, no render)
blender -b -P src/my_script.py -- --draft --only Name      # only one asset of a multi-asset script
blender -b -P src/my_script.py                             # FINAL: bake textures + FBX/GLB/LOD1/UCX + report
# add --render to either to also write a preview JPG (slow; off by default -- the user asked for no rendering)
```

Drafts write `export/<Name>/_draft_<Name>.jpg` and `_draft.report.json` (tris, dims vs target, texel density).
The final build writes:
- `SM_<Name>.fbx` (+ UCX)
- `SM_<Name>_LOD1.fbx`
- `SM_<Name>.glb`
- `T_<Name>_BaseColor.png`, `T_<Name>_Normal.png` (DirectX) and `T_<Name>_ORM.png`
- `SM_<Name>_preview.jpg`
- `SM_<Name>.report.json`

Always read the draft JPG with the Read tool. Look at it critically and iterate until it looks like a real,
used object, then run the final build and look at `SM_<Name>_preview.jpg`.

## Axes, size, pivot
- Units are metres. **Z up. FRONT faces +X.** The spec size is **W × H × D**, so the bbox is X = D, Y = W, Z = H.
- `K.Asset(name, size=(W, H, D), tris=budget, tex=1024|2048, pivot="bottom"|"center"|"none")`.
  - `"bottom"` (the default) recentres the bbox in XY and puts min Z at 0 after assembly.
  - `"none"` keeps your modelling origin (e.g. the trailer's king-pin).
- Model at the real size. The report's `dims_dev` is the per-axis deviation from the target. Aim for within ±5%.
- `tris` is a hard budget. Count against it and spend triangles on the silhouette, not on hidden faces.
  Use `drop=("-z",)` to delete faces that sit on the ground or are buried in another part.

## Parts
Every part is a bmesh built in its own local frame. Add it with `A.add(bm, material, at=(x,y,z), rot=(rx,ry,rz) deg)`
or with a full matrix `M=`. Useful options:
- `smooth=35`: edges with a dihedral angle below this shade smooth. Use about 60 for round organic parts and 20 for crisp machined ones.
- `group="door"`: names a vertex group, so variants can move or delete it.
- `grain="x"|"y"|"z"`: the local axis that wood grain, streaks and brushing follow. Defaults to the part's longest axis.
- `drop=("-z", "+x", ...)`: delete axis-aligned faces in local space.

Builders (all local, mostly centred on the origin):

| function | what |
|---|---|
| `K.box(sx, sy, sz, chamfer=0, drop=())` | box (chamfer adds one bevel segment; costs tris) |
| `K.cyl(r, h, seg=16, axis="z", r2=None, caps=True)` | cylinder / frustum (`r2` = top radius) |
| `K.tube(ro, ri, h, seg, axis, a0=0, a1=360)` | thick ring / pipe / arc segment |
| `K.lathe([(r, z), ...], seg, axis="z")` | revolve a profile; r=0 closes the end |
| `K.prism([(u, v), ...], thick, plane="xz"\|"xy"\|"yz")` | extrude a 2D polygon (centred thickness) |
| `K.sweep(path3d, profile2d, closed=False, cap=True, up=(0,0,1), scale=None)` | sweep a profile along a polyline (hoops, cables, drips, rails) |
| `K.torus(R, r, seg, rseg, axis)`, `K.sphere(r, seg, rings)` | |
| `K.grid(sx, sy, nx, ny)` | flat XY grid to deform (cloth, sheet metal) |
| `K.ibeam(L, h, w, tw, tf)`, `K.channel(L, h, w, t)`, `K.angle(L, a, t)`, `K.rtube(L, w, h, t=None)`, `K.pipe(L, r, seg)` | structural sections along +X, 0..L |
| `K.corrugated(L, H, pitch, depth, kind="sine"\|"trap", thick=0)` | corrugated sheet in XZ (waves along X) |
| `K.hexbolt(r, h)` | 6-sided bolt head |
| `K.deform(bm, fn)` | `fn(Vector) -> Vector` per vertex (sag, dents, bulges, irregularity) |
| `K.merge(bm1, bm2, ...)`, `K.transform(bm, at, rot)` | combine / place bmeshes before adding |
| `K.align_x(p0, p1, roll=0, up=(0,0,1))` | matrix mapping local +X onto p0→p1 |

Shortcuts:
- `A.rod(p0, p1, r, mat, seg=8)`: a round bar between two points.
- `A.beam(lambda L: K.ibeam(L, .3, .15, .01, .015), p0, p1, mat, roll=0)`: any section between two points.
- `A.cut(target_part, A.cutter(bm, mat, at=..., smooth=30))`: exact boolean difference. The cut faces take the
  cutter's material and smoothing angle, e.g. a wedge cutter with cheese paste makes the paste show.
  Use cutters sparingly and keep them low-poly. Booleans add triangles.

## Materials (procedural, baked)
`K.mat(recipe, **params)`. All recipes accept these weathering params:
- `grime` (0..1, crevice dirt)
- `dust` (desert dust on up-facing surfaces)
- `streaks` (rain and rust streaks on walls)
- `splash` (mud near the ground, `splash_h` in metres)

| recipe | look | key params |
|---|---|---|
| `paint` | sun-faded enamel with edge chips, primer rings, scratches, rust bleed | `color` hex, `under` = rust/steel/galv/wood/primer, `chips` 0..1, `flake` (big peeling patches), `fade`, `rough`, `scratch` |
| `team` | **TeamPaint slot**: neutral light-grey chipped paint (the engine tints it) | same as paint |
| `rust` | heavy rust, optionally with ghost paint | `paint` hex, `paint_left` 0..1, `light` |
| `galv` | galvanised steel with zinc bloom | `oxide`, `rust` |
| `steel` | raw/blackened structural steel, bright worn edges, crevice rust | `color`, `worn`, `rust` |
| `iron` | cast iron, pitted | `rust` |
| `diamond` | tread plate (pattern in the part's local XY, so lay the plate flat in local XY) | `paint` hex, `rust`, `worn` |
| `wood` | weathered timber; grain follows the part's long axis | `wood`, `wood_dark` hex, `weather`, `cracks`, `knots`, `nails` (spacing m) |
| `concrete` | board-formed concrete | `board` (m, 0 = smooth cast), `board_axis`, `silt_h` (m), `efflor`, `chips` |
| `burlap` | sacking | `color`, `dark` |
| `wax` | cheese wax | `color` |
| `cheddar`, `bleu_paste` | cut cheese | `rim=dict(R, H, bands=[(w, hex, rough)...])` for wax/rind bands on wheel cut faces |
| `bleu_rind`, `natural_rind` | cheese rinds | `color` |
| `brass`, `chrome`, `rubber`, `glass` (`cracks`), `milkglass` (`cracks`), `plastic` (`color`, `rough`), `cloth` (`color`, `fade`) | |
| `team_cloth` | **TeamPaint slot** cloth | |
| `glow` (`K.GLOW`) | **Glow slot**: frosted emitter strip | |
| `bulb` | bulb glass | |

- `K.TEAM` is the default TeamPaint material and `K.GLOW` the Glow material.
- Anything built from `team`/`team_cloth` lands in the `TeamPaint` slot, and `glow` lands in the `Glow` slot. Everything else bakes into `M_<Name>`.
- Stencils (create AFTER `K.Asset(...)`, which resets the scene): `img = K.stencil_image("wedge_stencil", "wedge")` gives a cheese-wedge stencil mask.
  Pass `decal=dict(img=img, axes="yz", center=(y, z), size=(sy, sz), facing=(1, 0, 0), color="#hex")` to `paint` or `wood`.
  See the materials.py decal helper.
- Alpha cards (razor wire etc.): `A = K.Asset(..., alpha=True)`. Draw the pattern with numpy and wrap it with
  `img = K.image_from_array("wire", arr)` (after `K.Asset(...)`). Then `K.mat("card", img=img, size=(Lx, Ly), centre=(cx, cy), look="galv")`
  maps the image over the card's local x/y (its two longest axes). BaseColor becomes RGBA and the GLB material is alpha-clipped.
- Colours are sRGB hex. Keep albedo realistic: no pure black or white, paint about 0.15–0.75 value, rust dark.
- Desert setting: sun-faded, dusty and dry. Never clean.

## Collision (UCX_)
- `A.ucx_box(center, size, rot)`
- `A.ucx_cyl(center, r, h, seg=8, axis="z")`
- `A.ucx_hull(points)`
- `A.ucx_parts(part1, part2...)`: convex hull of those parts.

Several convex pieces are fine, and walkable surfaces must be solid boxes (no holes). Coordinates are in modelling space;
the kit applies the pivot shift. Large props need UCX. Small pickups get one simple hull.

## Variants and skins
```python
A.build(variants={"Lockers_1_Open": lambda A, ob: K.rotate_group(ob, "door", pivot, "Z", -100)})
A.build(skins={"BlueMould": {WAX.name: K.mat("bleu_rind")}})   # extra texture sets on the same mesh
```
- Variants share the base texture set and land in the same folder.
- `K.delete_group(ob, "wheels")` removes tagged geometry (an "empty" variant).
- A variant fn may return a list of point lists to replace the UCX hulls. Points are in modelling space.

## Quality bar
Realistic PBR, worn and dirty, Old-West-industrial desert depot. It must sit next to Poly Haven scans.
- **Silhouette first.** Real objects have chamfers, lips, rolled edges, bolts, welds, hinges, seams and dents.
  No perfect boxes: add irregularity (sag, lean, bent sheet) with `K.deform`.
- **No recoloured primitives.** Use the right recipe per part (bolts `steel`, hinges `iron`, gaskets `rubber`) and
  vary each part's tint (pid does that automatically).
- Spend tris where the silhouette reads. Hide nothing inside closed volumes. Remove ground-contact faces.
- Check the draft from the front three-quarter view the preview uses (camera at azimuth -36°, elevation 17°).
