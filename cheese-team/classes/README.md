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
| Heavy | 1.16 | ten-gallon hat, handlebar moustache, gold sheriff star |

Build one class: `blender -b -P build_class.py -- <Class> <outdir> [preview|full]`
