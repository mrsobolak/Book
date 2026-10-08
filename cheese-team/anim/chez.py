# Keeps the hand-off folder (Downloads\chez) simple: the top level holds only what goes into the game plus the viewer,
# everything else (Blender files, GLBs, previews, review sheets, the drag-drop viewer) lives in _Extras, and READ ME.txt
# says what everything is. tidy() reorganises in place; it moves files, it never deletes them.
import os, shutil

CH = r"C:\Users\mrsobo\Downloads\chez"
EXTRA_EXT = ('.blend', '.blend1', '.glb', '.json', '.png')          # in the main folders only .fbx + textures\ stay
CLASS_NAMES = {'Outlaw': 'Outlaw', 'MrShotgun': 'Mr. Shotgun', 'RocketGuy': 'Boom Boom', 'Sniper': 'Mr. Faraway',
               'Mechanic': 'Mechanic', 'Greg': 'Greg'}
CLASS_WEAPONS = {'Outlaw': ('Revolver', 'Derringer'), 'MrShotgun': ('SawedOff', 'MachinePistol'),
                 'RocketGuy': ('RocketLauncher', 'SemiAuto'), 'Sniper': ('BoltRifle', 'LeverRifle'),
                 'Mechanic': ('SMG', 'Blueprint'), 'Greg': ('Minigun', 'SnubNose')}


def _move(src, dst):
    os.makedirs(os.path.dirname(dst), exist_ok=True)
    if os.path.exists(dst):
        os.remove(dst)
    shutil.move(src, dst)


def tidy(ch=CH):
    ex = os.path.join(ch, '_Extras')
    for top in ('Characters', 'Weapons', 'Ammo'):
        root = os.path.join(ch, top)
        if not os.path.isdir(root):
            continue
        for r, ds, fs in os.walk(root):
            if os.path.basename(r) == 'textures':
                continue                                               # textures stay next to their FBX
            for f in fs:
                if f.lower().endswith(EXTRA_EXT):
                    rel = os.path.relpath(os.path.join(r, f), ch)
                    kind = 'Blender files' if f.endswith(('.blend', '.blend1')) else \
                           'GLB (web, Godot)' if f.endswith('.glb') else 'Previews' if f.endswith('.png') else 'Pivot data'
                    _move(os.path.join(r, f), os.path.join(ex, kind, rel))
    for top, dst in (('Review', 'Review sheets'), ('Viewer', 'Drag-drop viewer')):
        p = os.path.join(ch, top)
        if os.path.isdir(p):
            for f in os.listdir(p):
                _move(os.path.join(p, f), os.path.join(ex, dst, f))
            os.rmdir(p)
    open(os.path.join(ch, 'READ ME.txt'), 'w', encoding='utf-8').write(readme(ch))
    return tree(ch)


def tree(ch=CH, depth=2):
    out = []
    for r, ds, fs in os.walk(ch):
        lvl = os.path.relpath(r, ch).count(os.sep) + (0 if r == ch else 1)
        if lvl > depth:
            continue
        mb = sum(os.path.getsize(os.path.join(r, f)) for f in fs) / 1e6
        out.append('%s%s\\  (%d files, %.0f MB)' % ('  ' * lvl, os.path.basename(r) or r, len(fs), mb))
    return '\n'.join(out)


def _list(ch, top):
    p = os.path.join(ch, top)
    return sorted(d for d in os.listdir(p)) if os.path.isdir(p) else []


def readme(ch=CH):
    chars = '\n'.join('    %-18s %-12s guns: %s' % (c + '_TP.fbx', CLASS_NAMES[c], ' + '.join(CLASS_WEAPONS[c]))
                      for c in CLASS_WEAPONS)
    weapons = ', '.join(_list(ch, 'Weapons'))
    ammo = ', '.join(_list(ch, 'Ammo'))
    return '''CHEESE TEAM - what's in this folder
====================================

CheeseTeam_Animations.html
    Double-click it to watch every animation in your browser (Chrome or Edge).
    Pick a character and a gun, then press 1-9 for the actions.

Characters\\
    One FBX per character: the mesh, the skeleton and ALL of its third-person animations.
%s
    Animations are named TP_<Gun>_<Action>:
        Idle, WalkF, WalkB, StrafeL, StrafeR, Fire, Reload
        (+ Aim, AimFire on the two rifles; the minigun has no Reload)

Weapons\\<Gun>\\
    <Gun>.fbx + textures\\. Guns: %s
    Extra FBXs next to a gun (e.g. Revolver_Cylinder.fbx, SMG_Mag.fbx, Minigun_Barrels.fbx) are its MOVING
    PARTS. The gun is only complete with them attached.

Ammo\\<Piece>\\
    <Piece>.fbx + textures\\. Bullets, live rounds, empty casings, shotgun shells, the rocket, the speedloader.
    Pieces: %s

HOW TO PUT A GUN IN A HAND (game engine)
    * Attach the gun to the character's  weapon  bone at scale 0.7. Its origin is already the grip.
    * Attach each moving part / ammo piece to its wp_## bone the same way (scale 0.7, same origin as the gun).
      The animations move those bones; a bone scaled to ~0 means "that piece isn't there right now".
    * Mr. Shotgun's second sawed-off goes on wp_01.
    * Which piece goes on which wp_## bone, per gun: see the table in
      https://github.com/mrsobolak/Book/blob/claude/adoring-pascal-ehr8wx/cheese-team/anim/README.md

_Extras\\  (you don't need these to use the models)
    Blender files     - the .blend source of everything
    GLB (web, Godot)  - the same models as .glb
    Previews          - render of each gun / piece, ammo line-up
    Pivot data        - grip offsets the animation tool uses
    Review sheets     - the frame-by-frame check sheets
    Drag-drop viewer  - the viewer without the models baked in (drop GLBs onto it)
''' % (chars, weapons, ammo)
