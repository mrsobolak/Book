# CheeseTeam classes -- looks

Six classes on the unchanged base body (`src/cheese/CheesePlayer.blend`, SK_CheeseTP + Armature):
accessories only, plus a uniform height scale. Accessories are built by code (`acc.py` toolkit,
`classes.py` designs), skinned rigidly to the bone they sit on, and exported with the rig and animations.

| class | height | accessories |
|---|---|---|
| Outlaw | 1.00 | low flat-brim black hat tilted forward over the left eye, pencil moustache, toothpick, red paisley bandana on the right upper arm |
| Mr. Shotgun | 1.00 | backwards trucker cap, mutton-chop sideburns, angry brows, shotgun shells pushed into the cheese holes |
| Rocket Guy | 1.00 | open-face motorcycle helmet with scratched goggles on top, big band-aid, spiked leather wristbands |
| Sniper | 1.07 | blaze-orange hunting cap with ear flaps down, two camo face-paint stripes, a stalk of dry grass |
| Mechanic | 1.00 | short-brim patterned welder's cap, grease smudges, red shop rag in a hole, big wrench clipped to the side |
| Greg (was Heavy) | 1.16 | handlebar moustache, gold sheriff star (no hat) |

Build one class: `blender -b -P build_class.py -- <Class> <outdir> [preview|full]`

## Final looks (as shipped)
| Class | Accessories | Height |
|---|---|---|
| Outlaw | low black flat-brim hat, pencil moustache, toothpick, red paisley bandana (right arm) | 1.00 |
| Mr. Shotgun | backwards trucker cap, angry brows, mutton chops, shotgun shells in the holes | 1.00 |
| Rocket Guy | open-face helmet + goggles, band-aid, spiked wristbands | 1.00 |
| Sniper | camo face paint (no hat) | 1.07 |
| Mechanic | grease smears, big wrench strapped to the side (no hat) | 1.00 |
| Greg (was Heavy) | handlebar moustache, sheriff star (no hat) | 1.16 |

## Export
`finish.finish(cls, export_root)` (run inside Blender) builds the class, bakes the accessories to one PBR set
(BaseColor / Roughness / Metallic / Normal + packed ORM, 2048), skins them rigidly to their bones, applies the class
height (object + the actions' object-level keys) and writes `<cls>.fbx`, `<cls>.glb`, `<cls>.blend`, `textures/` and a
preview. `finish.lineup(export_root, png)` renders all six side by side.
