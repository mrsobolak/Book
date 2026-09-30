# Tim Cheese v2 (TF2-style character)

An original Team Fortress 2-style character: a lean mercenary built somewhere between the Scout and the
Demoman, with a Swiss-cheese wedge for a head, two googly eyes, a cocky smirk cut into the cheese, a flat cap
perched on the slope of the wedge, and real articulated hands (palm, four three-segment fingers and a thumb
per hand). Loadout: The Grate Equalizer (box grater), The Brie-dolier (wax-dipped cheese wheels), Fists of Gouda.

![Grid](preview_grid.png)

**View it:** open `index.html` in a browser. Drag to orbit, switch RED/BLU, jump, shake his head. The googly
pupils are simulated: they feel gravity and the head's motion and rattle around their housings.

| File | What it is |
| --- | --- |
| `build_cheeseman.py` | Builds the whole character procedurally (`blender -b --python build_cheeseman.py -- . [--nobake]`) |
| `build_viewer.py` | Packs the GLB (meshopt) and embeds it with `rig.json` into `index.html` |
| `viewer_template.html` | three.js viewer with the TF2-style half-Lambert toon shader, ink lines and googly physics |
| `cheeseman.packed.glb`, `rig.json` | The model the page uses, and the eye rig (pupil centres, radii) |
| `preview_*.png` | Renders straight out of the viewer |

Built on the shared toolkit in `cod/armory/lib.py`: elliptical lofts + Catmull-Clark smoothing for the body,
limbs, palms and fingers; exact booleans for the cheese holes, mouth, buckle and grater; a Cycles
ambient-occlusion bake into vertex colours. This is v2: v1 was a Heavy-sized metaball blob with no hands.
