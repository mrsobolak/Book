# CheeseTeam third-person animations

`anim.py` runs inside Blender (pulled by SHA from this branch) and procedurally authors every class + weapon set on the
CheesePlayer rig. The arms are lengthened 1.8x and the shoulders sit on the wedge's front corners (`classes/arms.py`).

| class | weapons | actions per weapon |
|---|---|---|
| Outlaw | Revolver, Derringer | Idle, WalkF, WalkB, StrafeL, StrafeR, Fire, Reload |
| Mr. Shotgun | Sawed-off (dual, 2nd gun on `wp_01`), Machine pistol | same |
| Boom Boom (RocketGuy) | Rocket launcher, Semi-auto | same |
| Mr. Faraway (Sniper) | Bolt rifle, Lever rifle | same + Aim, AimFire |
| Mechanic | SMG, Blueprint | same |
| Greg | Minigun (no reload), Snub-nose | same (Minigun: no Reload) |

Actions are named `TP_<Weapon>_<Action>`. `export_class(cls)` bakes both weapons on one rig, re-runs the clip check and
writes `CheeseAnim/export/<cls>_TP.blend` + `.fbx`.

## Attaching in engine
Every gun and every moving part / ammo piece goes on a socket bone at scale 0.7 (weapons are modelled real size). The
gun's origin is its grip (`<Weapon>_pivot.json`); split parts keep the gun's origin, so attach them exactly like the gun.
The animation moves the bones. A bone scaled to ~0 means "that piece isn't there right now": a round still in the pouch,
a case that has hit the floor. Keep the socket's scale inheritance on.

| weapon | wp_01 | wp_02 | wp_03 | wp_04 | wp_05 | wp_06 | wp_07 | wp_08 |
|---|---|---|---|---|---|---|---|---|
| Revolver | | Revolver_Gate | Revolver_Rod | Revolver_Cylinder | Ammo45_Casing | Ammo45_Casing | Ammo45_Round | Ammo45_Round |
| Derringer | | Derringer_Barrels | Derringer_Lever | Ammo38_Casing | Ammo38_Casing | Ammo38_Round | Ammo38_Round | |
| SnubNose | | SnubNose_Cylinder | Casings38 | Speedloader38 | Speedloader38_Rounds | | | |
| SemiAuto | | SemiAuto_Mag | SemiAuto_Slide | SemiAuto_Mag (fresh one) | | | | |
| MachinePistol | | MachinePistol_Mag | MachinePistol_Charger | MachinePistol_Mag (fresh one) | | | | |
| SawedOff | SawedOff (2nd gun) | SawedOff_Pump | SawedOff_Bolt | SawedOff_Pump (gun 2) | SawedOff_Bolt (gun 2) | Shotgun12_Shell | | |
| BoltRifle | | BoltRifle_Bolt | Ammo3006_Casing | Ammo3006_Round | Ammo3006_Round | | | |
| LeverRifle | | LeverRifle_Lever | Ammo3030_Casing | Ammo3030_Round | Ammo3030_Round | | | |
| SMG | | SMG_Mag | SMG_Cock | SMG_Mag (fresh one) | | | | |
| RocketLauncher | | | Rocket | | | | | |
| Minigun | | Minigun_Barrels | | | | | | |

Gun parts are in `weapons/export/<Weapon>/`, ammo in `weapons/export_ammo/<Piece>/`. A gun mesh no longer contains its
split parts: the gun is only complete with its parts attached.

## How the reloads work
Each reload follows the real mechanism, with the parts moving and ammo in the hands:
* **Revolver** (single action): flick the loading gate open, half-cock, the ejector rod punches out two empties, the cylinder
  turns a chamber at a time, two rounds come from the left pouch and get thumbed in, the gate shuts, then a spin.
* **Derringer**: thumb the lever, tip the barrels up, pull both empties, two rounds in, snap shut.
* **Snub-nose**: the cylinder swings out, muzzle up, slap the ejector (five empties fall), speedloader in, twist, pull it, flick shut.
* **Semi-auto / machine pistol**: slide locked back / mag drops to the floor, a fresh mag comes from the pouch and gets seated,
  then slide release / rack the top charging knob.
* **SMG**: roll the side mag down, strip it and toss it, seat a fresh one, rack the cocking handle.
* **Dual sawed-offs** (pump): one gun tucked in the waistband while the free hand feeds a shell up the loading port and
  racks the pump, then the other gun.
* **Bolt rifle**: bolt up and back, two rounds pressed down into the open action from the right pouch, bolt home.
* **Lever rifle**: rifle rolled so the side gate faces up, two rounds pushed in through the gate, then a lever cycle.
* **Rocket launcher**: down across the belly, a rocket comes from the pouch and gets slid into the tube.

Firing also works the gun: the cylinders index, the semi-auto slide and the SMG / machine-pistol handles cycle, and the
bolt and lever guns are worked by hand after every shot with the empty case flying out.

## How it stays clip-free
* **Reach.** Holds come from an offline reach solver. Both hands sit at 60-95 % of the arm's reach, with the elbows
  hanging down / out, and the gun body clears the wedge.
* **Elbows.** `arm_ik` is a two-bone IK. Its elbow swings around the shoulder-hand axis, starting nearest the wanted
  pole, until both sticks clear the wedge mesh, the pelvis, hats / face accessories, the held gun (parts and ammo
  included) and forearm cuffs. Last frame's elbow is preferred, so it doesn't twitch.
* **Check.** `check()` counts triangle overlaps every frame: gun vs body, gun vs accessories, arms vs wedge / hats, and
  leg vs leg. Contacts hidden inside a hand ball or at the shoulder root, and pieces scaled to ~0, don't count.

## Authoring
`tracks([...])` turns a key list into a modifier. Each channel interpolates between its own keys:
* `dg` / `dr`: grip offset and yaw-pitch-roll in body space. `dg2` / `dr2` do the same for the second gun.
* `lh` / `rh`: hand targets. These can be `'grip'`, `'rest'`, `('w', u, v, x)` (a point on the gun in design mm),
  `('p', bone, u, v, x)` (a point on a moving part) or a char-space `Vector`.
* `lel` / `rel`: elbow poles.
* `pt={bone: spec}`: part specs, built with `G`, `AT`, `ON`, `HAND`, `FREE`, `DROP` and `HID` (see `part_xf`).
* `ease`: the easing for each key.

`kick()` makes recoil and `shake()` makes looping auto fire. `WDEF` ties each weapon to its hold, fire, reload and parts.
