# Cheese Team — Model Generation List (Wash Junction CTF + shared gameplay props)

Brief handed to the generation pipeline (condensed copy; the original came in chat). Work top to bottom:
**P1** blocks gameplay, **P2** are the landmarks that make the map memorable, **P3** is set dressing.
Guns and characters are excluded.

## Rules for every model
- **Style:** modern industrial with a little Old West (desert highway depot, rusted steel, sun-faded paint, old brick,
  weathered wood). Realistic PBR, worn and dirty. NOT cartoon, NOT clean. It must sit next to Poly Haven scans.
- **No "recoloured primitives":** every surface needs a real material (rust, paint chips, grime, wood grain, scratches).
- **Scale:** real-world metres. FBX so 1 unit = 1 cm in Unreal; GLB in metres. Sizes are target bounding boxes, W × H × D (m).
- **Orientation:** Z up, front faces +X, pivot at bottom centre unless noted.
- **Formats:** FBX (Unreal) + GLB (web preview). Meshes `SM_<Name>`. Textures `T_<Name>_BaseColor / _Normal / _ORM`
  (Occlusion, Roughness, Metallic packed). 2048² for hero/large props, 1024² for small. No baked lighting in BaseColor.
- **[TEAM] parts:** separate material slot `TeamPaint` (neutral light-grey chipped paint; the engine tints it Cheddar
  orange #C8601C or Bleu blue #33669F).
- **Text:** none baked unless stated (sign faces blank).
- **Collision:** `UCX_` convex collision for large props. Nothing walkable may have holes.
- **Budgets:** at or under the triangle budgets. LOD1 at ~50% for anything over 5k tris.
- **Deliverables per model:** FBX, GLB, textures, one preview render (front three-quarter view).

## P1 — Gameplay-critical
| ID | Model | Size (m) | Tris | Notes |
|---|---|---|---|---|
| SM_FlagCheese_Cheddar | Giant cheddar wheel in red wax | Ø1.2 × 0.42 | 3k | ~45° wedge cut showing pale-orange paste with holes, wax drips, knife marks. Pivot at **centre**. |
| SM_FlagCheese_Bleu | Giant blue-cheese wheel | Ø1.2 × 0.42 | 3k | Same shape; grey-blue bloomy rind, blue veins in the cut. |
| SM_FlagPedestal | Flag stand | Ø2.9 × 0.95 | 4k | Hex steel plinth, diamond-plate top, bolted base, emissive ring channel (`Glow` slot). [TEAM] trim. |
| SM_VaultDoor_Open | Round vault door, open | Ø3.7 × 0.7 thick | 8k | 16 edge locking bolts, 3-spoke handwheel, hinge blocks. Plus SM_VaultDoorFrame: ring Ø4.7 outer / Ø4.0 inner, 0.5 deep. |
| SM_HealthPack_S/_M/_L | Health pickups | 0.3 / 0.45 / 0.6 wide | 1k each | Metal first-aid tins with a moulded cheese-wedge emblem (no text). |
| SM_AmmoPack_S/_M/_L | Ammo pickups | 0.3 / 0.45 / 0.6 | 1k each | Olive steel ammo cans; crate for L; brass casings visible in M and L. |
| SM_ResupplyCabinet | Spawn resupply locker | 1.7 × 2.3 × 0.6 | 5k | Open front, 3 shelves, emissive frame strip (`Glow`). [TEAM] body. |
| SM_Lockers_1 / _Open | Single steel locker module | 0.42 × 1.95 × 0.5 | 600 | Louvred door, handle, blank number plate, tiles side by side. [TEAM]. |
| SM_SpawnDoorFrame | Spawn exit frame | 3.2 × 3.4 × 0.5 | 1.5k | Heavy steel frame with an emitter strip down each side. [TEAM]. |

## P2 — Landmarks
| ID | Model | Size (m) | Tris | Notes |
|---|---|---|---|---|
| SM_WaterTower_Wood | Wooden water tower on a roof | 6 × 13 × 6 | 12k | Stave tank Ø5.4 × 4.2 with steel hoops, conical rusted tin roof, four I-beam legs 5.2 tall with bracing, ladder, railed walkway, blank flat area facing +X. |
| SM_Windmill_Pump | Pumping windmill | 4 × 13 × 4 | 10k | Tapered lattice tower; 18-blade wheel Ø4.6 as separate SM_Windmill_Wheel with pivot at the hub; tail vane; pump rod. Plus SM_StockTank Ø3.9 × 0.76 galvanised. |
| SM_Billboard_2Post | Roadside billboard | 13.5 × 12 × 1.6 | 6k | Two I-beam posts, wooden back framing, catwalk with railing, 5 lamp arms, blank 13 × 4.6 face, weathered and peeling. |
| SM_SignGantry | Highway sign gantry | 2 × 7.8 × 17 | 8k | Galvanised box-truss posts and span truss with catwalk. Plus SM_HighwaySign 6 × 2.4 blank green. |
| SM_SemiTrailer_DryVan | 48′ box trailer | 2.6 × 4.1 × 14.6 | 10k | Corrugated white panels, logistic posts, rear swing doors with lock rods, landing gear, tandem axles, mud flaps, underride guard. Pivot under the king-pin. |
| SM_SemiCab_American | Long-nose cab | 2.6 × 4.2 × 6.6 | 15k | Chrome grille and stacks, sleeper, fuel tanks, dual rear axles, sun-faded red. |
| SM_RoofSignFrame | Rooftop sign structure | 14.5 × 3.6 × 1.5 | 3k | Truss holding a 14 × 2.2 sign box with bulb sockets, blank face. [TEAM] box. |
| SM_GarageRollUp_Half | Roll-up dock door, half open | 8.6 × 4.7 × 0.7 | 3k | Coil housing, guide channels, curtain lowered ~0.6 m from the top. [TEAM] curtain. |

## P3 — Set-dressing kits
- SM_CheeseRack: 2.6 × 2.9 × 0.85, 8k. Timber, 5 slatted shelves, ~16 wheels with mixed rinds. Plus an empty variant.
- SM_CheeseWheel_S/_M (+ _Wedge): Ø0.3 / Ø0.55, 300/500 tris. Three rinds (red wax, blue mould, natural); the wedge has holes.
- SM_CheeseCrate: 0.8 × 0.5 × 0.6, 400. Stencilled cheese wedge, no text, stackable.
- SM_Container_20ft / _40ft / _40ft_Open: 2.44 × 2.59 × 6.06 / 12.19, 3k/4k/6k. Corner castings, corrugation, lock rods.
  The Open variant has doors swung out, a walkable wooden floor, a hollow interior with collision, and a TeamPaint-style tint slot.
- SM_Sandbags_Straight/_Corner: 1.8 × 0.75 × 0.6, 2k. 5 rows, slumped burlap.
- SM_Dumpster: 2 × 1.45 × 1.7, 2k. Green, rusted, one lid open, wheels.
- SM_CableReel: Ø1.8 × 0.9, 1k. Rubber cable wrap.
- SM_Pump_Industrial: 3.2 × 2.3 × 1.8, 6k. Pump and motor on a concrete plinth, [TEAM] casing. Plus SM_Valve_Wheel.
- SM_StairSteel_Run: 2.2 × 5 × 7, 4k. Diamond-plate treads, channel stringers, handrails both sides, [TEAM] nosing. Plus SM_Catwalk_2m grating module with railings.
- SM_Railing_2m: 2 × 1.07 × 0.1, 300. Posts, rails, toe board. Plus a [TEAM] corrugated-panel variant.
- SM_BoxCulvert_2m: 4.6 × 3.8 × 2.44, 500. Board-formed concrete, joint lip, silt stain. Plus SM_CulvertHeadwall 16.8 × 5.6 with an 8 × 3.8 opening.
- SM_FilingCabinet: 0.5 × 1.32 × 0.6, 600. Dented, one drawer ajar.
- SM_Bollard: Ø0.26 × 1.2, 200. Yellow.
- SM_DrainGrate: 1 × 0.05 × 0.5, 200.
- SM_RazorWire_3m: 3 × 0.7 × 0.6, 2k. Alpha-tested strip, not modelled barbs.
- SM_TeamBanner: 3 × 1.6, 300. Fringed bottom edge, folds, [TEAM] cloth, blank centre.
- SM_HitchingPost / SM_WaterTrough: 3 × 1 × 0.3 / 2.4 × 0.6 × 0.7, 500 each. Weathered timber and riveted iron.
- SM_RetroGasPump: 0.7 × 2 × 0.5, 2k. 1950s, faded paint, cracked glass globe.

## Already covered (do NOT generate)
Vehicles (pickup, forklift, tanker rig, MAN cab), concrete barriers, pallets and barrels, oil drums, crates, cardboard
boxes, cement bags, jerrycans, propane tanks, AC units, security and hanging lamps, power poles, chain-link fence,
hydrant, tool cart, hand truck, office desk and stool, extinguisher, trash bags, rocks, cliffs, boulders, desert plants,
dead tree, bull skull.
