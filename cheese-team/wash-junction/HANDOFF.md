# Handoff — continue Wash Junction on your own PC

This file carries the state of the cloud session (`session_01YB5yxjfvq1qMjyRkuhq9NW`) so a local Claude Code
session on your PC can pick up the work and use your local MCP servers (blender / blender2 / unreal / unity).

## Move the session to your PC with its full chat history (teleport)
1. Install the Claude Code CLI. Sign in with the **same claude.ai account** (`claude`, then `/login`).
2. Get a clean checkout of `mrsobolak/Book`:
   ```powershell
   git clone https://github.com/mrsobolak/Book.git
   cd Book
   ```
3. Pull this session down. Teleport checks out the branch and loads the whole conversation:
   ```powershell
   claude --teleport session_01YB5yxjfvq1qMjyRkuhq9NW
   ```
   Alternatively, run `claude --teleport` with no ID and pick from the list, or use **Open in > Terminal** in the session menu on claude.ai/code.
4. Give that local Claude Code your Blender MCP server. Claude Code doesn't read the Desktop app's server list on
   native Windows, so add it once. Copy the command from Claude Desktop → Local MCP servers → blender2 → Edit config.
   ```powershell
   claude mcp add blender2 --scope user -- "C:\path\from\desktop\config\blender-mcp.exe"
   claude mcp list
   ```
   Do the same for `unreal` or `unity` if you want them. In Blender, enable the BlenderMCP addon and click **Connect**.
5. Optionally, keep steering it from your phone: run `/remote-control` inside that local session.

The cloud session stays as it is, and the local one becomes its own copy.

## Where the work stands
Finished meshes, each with FBX + LOD1 (when over 5k tris) + GLB + BaseColor/Normal(DirectX)/ORM + report:
- SM_FlagCheese_Cheddar and SM_FlagCheese_Bleu (`src/flag_cheese.py`), with previews
- SM_VaultDoor_Open (with preview) and SM_VaultDoorFrame (`src/vault_door.py`)

In progress:
- `src/flag_pedestal.py`: script written, not baked yet. Run `blender -b -P src/flag_pedestal.py -- --gpu`.

Not started (the spec text for each is in SPEC.md):
- **P1:** health_packs, ammo_packs, resupply_cabinet, lockers (+Open variant), spawn_door_frame
- **P2:** water_tower, windmill (+wheel, stock tank), billboard, sign_gantry (+highway sign), semi_trailer, semi_cab,
  roof_sign, garage_rollup
- **P3:** cheese_rack (+Empty), cheese_wheels (3 rind skins), cheese_crate, containers (20/40 ft), container_open,
  sandbags, dumpster, cable_reel, pump_industrial (+valve wheel), stairs_catwalk, railings (+panel), culvert
  (+headwall), filing_cabinet, bollard_grate, razor_wire, team_banner, western (hitching post + trough), gas_pump

The detailed per-script briefs that were given to the builder agents (sizes → bbox, budgets, construction notes,
the gantry and roll-up interpretations) are in `kit/agent_briefs.js`.

## User preferences that came up in the chat
- Speed over everything: **no rendering** unless asked (the kit renders nothing by default; `--render` opts in).
- Banter persona: crazy guy, "TIM CHEESE", "Backrooms", 🫪, plus Doom references.
- Never bring up "Jarvis".
- Commit and push to branch `claude/adoring-pascal-ehr8wx`. Don't open a new PR (PR #1 already exists).

## Fast local build
```powershell
pip install numpy pillow
python cheese-team\wash-junction\kit\build_all.py --blender "C:\...\blender.exe" --jobs 4 --gpu
```
See `README.md` → *Running it on your own PC* and `kit/KIT.md` for the kit API.
