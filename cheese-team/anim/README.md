# CheeseTeam third-person animations

`anim.py` runs inside Blender (pulled by SHA from this branch) and procedurally authors every class + weapon set on the
CheesePlayer rig (arms lengthened 1.65x by `classes/arms.py`):

| class | weapons | actions per weapon |
|---|---|---|
| Outlaw | Revolver, Derringer | Idle, WalkF, WalkB, StrafeL, StrafeR, Fire, Reload |
| Mr. Shotgun | Sawed-off (dual, 2nd gun on `wp_01`), Machine pistol | same |
| Boom Boom (RocketGuy) | Rocket launcher, Semi-auto | same |
| Mr. Faraway (Sniper) | Bolt rifle, Lever rifle | same |
| Mechanic | SMG, Blueprint | same |
| Greg | Minigun (no reload), Snub-nose | same (Minigun: no Reload) |

Actions are named `TP_<Weapon>_<Action>`. `export_class(cls)` bakes both weapons on one rig, re-runs the clip check and
writes `CheeseAnim/export/<cls>_TP.blend` + `.fbx` (armature, body, accessories, all actions). Guns are the separate
`weapons/` exports; in engine attach them to the `weapon` bone (and `wp_01` for the second sawed-off) at scale 0.7
with their `<name>_pivot.json` grip offset, the same way `Rig.attach` does here.

## How it stays clip-free
* **Reach.** The stick arms hang off the sides of a 0.40 m wedge, so in front of it the two hands can't get closer than
  ~0.14 m (~0.08 m just under the wedge). Everything is laid out from that reach map:
  * one-handed guns hold out front-right, reloads that need both hands happen low in front of the hips and work the
    muzzle end of the gun (or the hip pouch for magazine pistols);
  * long guns use a bladed stance (`twist`: wedge turned right, left shoulder forward; 65 deg rifles / SMG, 55 deg
    launcher / minigun) so the gun lies across the body and still points straight ahead; the hold points come from an
    offline solver (both hands reachable, gun body clear of the wedge).
* **Elbows.** `arm_ik` is a two-bone IK whose elbow swings around the shoulder-hand axis until both sticks clear the
  real wedge mesh, the pelvis, hats / face accessories, the held gun (and the forearm cuff, e.g. Boom Boom's spiked
  wristbands). `IK_MISSES` logs any frame where no clean elbow exists.
* **Check.** `check()` counts triangle overlaps every frame: gun vs body, gun vs accessories, arms vs wedge / hats,
  leg vs leg (contacts hidden inside a hand ball or at the shoulder root are ignored). `probe()` breaks one frame down
  by body part.

## Authoring
`keyed([...])` turns a key-pose list into a modifier: `dg` / `dr` (grip offset / yaw-pitch-roll in body space),
`dg2` / `dr2` (second gun), `tw` (extra twist), `lh` / `rh` hand targets (`'grip'`, `'rest'`, `None` = hold default,
`('w', u, v, x)` a point on the gun in its design mm, or a char-space `Vector`), `lel` / `rel` elbow poles, `ease`.
`kick()` / `shake()` make one-shot recoil and looping auto-fire. `WDEF` ties each weapon to its hold, fire and reload.
