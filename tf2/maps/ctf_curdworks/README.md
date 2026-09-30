# ctf_curdworks (TF2-style Capture the Flag map)

A symmetric two-base CTF map set in the Curdworks cheese factory. Team Fortress 2 illustrative rendering
(saturated team buildings, dark stripes, cheese silos, a water tower, plank catwalks, oversized signs, a
cartoon intel briefcase) mixed with a Call of Duty edge (sandbag nests, olive military crates, a stranded troop
truck by each base, barbed wire on the perimeter, floodlight towers). Built to an Xbox One budget: about 70k
triangles, one draw call per material, ambient occlusion baked into vertices so no shadow maps are needed.

![Overview](preview_grid.png)

**View it:** open `index.html` in a browser. Views: overview, top-down, each base, the bridge, the RED intel
room, and player height in the RED courtyard. Drag to orbit, scroll to zoom, right-drag to pan.

## Layout (104 × 56 m)

- **Bases** at each end: a two-storey factory building with a big front door toward mid, side doors north and
  south, a first-floor sniper deck over the front door, stairs inside, a chimney, team stripe and signs.
- **Intel room** at the back of each base: raised pedestal, glowing briefcase, INTEL sign. **Spawn** behind it:
  lockers and a resupply cabinet facing the door.
- **Three routes** between the bases: the plank bridge (fast, exposed to both sniper decks), the dry canal under
  it (slow, blind corners, safe from snipers), and the north catwalk deck. The conveyor yard (north) and the mid
  shed with a firing slit (south) break sightlines.
- **Cover** in each courtyard: three sandbag nests, crates, barrels. Health kits and ammo boxes on both side routes.

## Files

| File | What it is |
| --- | --- |
| `build_map.py` | Builds the whole map procedurally; the RED half is mirrored for BLU with team materials swapped |
| `build_viewer.py`, `viewer_template.html` | Pack the model and embed it in the page with the TF2 toon shader |
| `curdworks.packed.glb` | The model the page uses |

Rebuild: `blender -b --python build_map.py -- .` then `python3 build_viewer.py`.
