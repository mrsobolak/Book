# Whey Station -- Blender construction kit (derived from the Wash Junction kit: same API, same data format).
# All layout coordinates are in the game frame (three.js: X right, Y up, Z toward camera), metres.
# Vertices are converted to Blender (Z up) as (x, -z, y); the glTF exporter converts back exactly.
import bpy, bmesh, math, random, os
from mathutils import Matrix, Vector, Euler, noise

PI = math.pi


def T2B(v):
    return Vector((v[0], -v[2], v[1]))


# material table: name -> (poly haven texture id, metres per tile, sRGB colour, roughness, metalness)
# Colour = texture x (target colour / texture average), so every surface lands on its agreed colour.
TEAMCOL = {'C': '#c8601c', 'B': '#33669f'}
MATS = {
    # --- Wash Junction materials (same names, so the game viewer already knows them) ---
    'Conc': ('concrete_floor_worn_001', 3, '#8f8a82', 0.9, 0), 'ConcCrack': ('cracked_concrete', 6, '#8f8576', 0.92, 0),
    'Hangar': ('hangar_concrete_floor', 4, '#7b766e', 0.8, 0),
    'CMU': ('concrete_block_wall', 2.0, '#a0998d', 0.9, 0), 'Brick': ('red_brick_03', 1.6, '#93604a', 0.9, 0),
    'Stucco': ('white_stucco', 2.5, '#d7cdbb', 0.95, 0),
    'Paint_C': ('brushed_concrete', 2, TEAMCOL['C'], 0.85, 0), 'Paint_B': ('brushed_concrete', 2, TEAMCOL['B'], 0.85, 0),
    'Clad_C': ('box_profile_metal_sheet_g', 2.4, TEAMCOL['C'], 0.6, 0.25), 'Clad_B': ('box_profile_metal_sheet_g', 2.4, TEAMCOL['B'], 0.6, 0.25),
    'SteelT_C': ('rusty_painted_metal_g', 1.6, '#b85a1e', 0.55, 0.3), 'SteelT_B': ('rusty_painted_metal_g', 1.6, '#30609a', 0.55, 0.3),
    'Shutter_C': ('painted_metal_shutter_g', 2.0, TEAMCOL['C'], 0.55, 0.3), 'Shutter_B': ('painted_metal_shutter_g', 2.0, TEAMCOL['B'], 0.55, 0.3),
    'Steel': ('rusty_metal_02', 1.2, '#5d5a55', 0.6, 0.45), 'SteelO': ('rusty_metal_02', 1.6, '#76624c', 0.7, 0.35),
    'SteelW': ('rusty_metal_02', 1.2, '#cfcac0', 0.55, 0.25), 'SteelG': ('rusty_metal_02', 1.0, '#9ea2a3', 0.45, 0.6),
    'Plate': ('metal_plate', 1.0, '#7d7c78', 0.5, 0.55), 'Grate': ('metal_grate_rusty', 0.8, '#76604c', 0.7, 0.4),
    'Rust': ('rusty_metal_02', 1.2, '#7b4b2d', 0.8, 0.3), 'CorrWorn': ('worn_corrugated_iron', 2.0, '#918d87', 0.6, 0.4),
    'Precast': ('concrete_layers_02', 3.0, '#8c867d', 0.9, 0), 'Ribbed': ('ribbed_concrete_wall', 2.5, '#8c8478', 0.9, 0),
    'ConcLayers': ('concrete_layers_02', 3.0, '#9a948a', 0.9, 0), 'AntiSlip': ('anti_slip_concrete', 1.0, '#7f786e', 0.9, 0),
    'Brushed': ('brushed_concrete', 1.5, '#a59f95', 0.85, 0),
    'Panel': ('white_stucco', 4.0, '#c6cbc8', 0.6, 0.05), 'SafetyY': ('rusty_painted_metal_g', 1.6, '#c9a12a', 0.55, 0.3),
    'Plaster': ('yellow_plaster', 2.5, '#c9b48e', 0.95, 0), 'Planks': ('old_planks_02', 2.0, '#8a6f52', 0.85, 0),
    'Glass': (None, 1, '#33424a', 0.08, 0.6),
    # --- new for Whey Station (creamery interior); texture files are fetched by tools/fetch_textures.py ---
    'TileW': ('long_white_tiles', 1.27, '#d9d6cc', 0.35, 0), 'TileFloor': ('floor_tiles_08', 1.5, '#b8b0a2', 0.6, 0),
    'Epoxy': ('painted_concrete_02', 4.0, '#6f7472', 0.55, 0), 'EpoxyG': ('painted_concrete', 2.0, '#5f7464', 0.6, 0),
    'FloorDmg': ('concrete_floor_damaged_01', 5.0, '#77726a', 0.85, 0),
    'Stainless': ('metal_plate_02', 2.0, '#b9bcbc', 0.32, 0.85), 'SteelPlate': ('metal_plate_02', 2.0, '#6d6c69', 0.5, 0.6),
    'Grid': ('rusty_metal_grid', 1.8, '#6c7a78', 0.6, 0.4), 'RustCoarse': ('rust_coarse_01', 2.2, '#6f4a33', 0.85, 0.2),
}
# --- TF2-style ("illustrative") set: procedurally painted textures from tools/tf_textures.py (textures_tf/) ---
MATS.update({
    'TF_Wall': ('tf_wall_block', 4.0, '#d9d0bb', 0.85, 0), 'TF_Dado': ('tf_wall_dado', 2.0, '#7d8274', 0.8, 0),
    'TF_Floor': ('tf_floor_dark', 4.0, '#3f4042', 0.7, 0), 'TF_Tile': ('tf_tile_white', 2.0, '#ebe8e0', 0.35, 0),
    'TF_Steel': ('tf_steel_dark', 2.0, '#4d5154', 0.55, 0.3), 'TF_Conc': ('tf_concrete', 4.0, '#a9a69d', 0.9, 0),
    'TF_Brick': ('tf_brick', 2.0, '#8e4f3a', 0.9, 0), 'TF_Shutter': ('tf_shutter', 2.0, '#7f8287', 0.6, 0.2),
    'TF_Grate': ('tf_grate', 0.5, '#3a3c3f', 0.6, 0.4), 'TF_Wood': ('tf_wood', 1.2, '#ad8a56', 0.8, 0),
    'TF_Hazard': ('tf_hazard', 0.5, '#e0b52c', 0.6, 0), 'TF_Machine': ('tf_machine', 3.0, '#7d989b', 0.5, 0.2),
    'TF_Ceiling': ('tf_ceiling', 2.0, '#c9c5ba', 0.9, 0), 'TF_Arrow': ('tf_sign_arrow', 1.0, '#cfcdc6', 0.6, 0),
    'TF_Paint_C': ('tf_paint_metal', 2.4, '#b4561c', 0.55, 0.1), 'TF_Paint_B': ('tf_paint_metal', 2.4, '#2f5f94', 0.55, 0.1),
    'TF_Corr_C': ('tf_corr', 2.0, '#a85420', 0.6, 0.2), 'TF_Corr_B': ('tf_corr', 2.0, '#2c5888', 0.6, 0.2),
    'TF_Emblem_C': ('tf_emblem', 1.0, '#c8601c', 0.6, 0), 'TF_Emblem_B': ('tf_emblem', 1.0, '#33669f', 0.6, 0),
    'TF_Bulb': (None, 1, '#fff2c8', 0.3, 0),
})
SIGN_PREFIX = ('TF_Emblem', 'TF_Arrow')      # these get 0..1 UVs per face (one picture per sign face)
FLOORS = [0.0]          # walking levels used for floor-grime; the map module sets this


def set_floors(levels):
    FLOORS[:] = sorted(levels)


class Kit:
    def __init__(self, seed=7):
        self.M = [Matrix.Identity(4)]
        self.parts = {}            # (group, mat) -> bmesh
        self.group = 'misc'
        self.cols, self.openings, self.lights, self.areas, self.labels, self.props = [], [], [], [], [], []
        self.rng = random.Random(seed)
        self.nobevel = set(['Glass', 'Grate'])

    # ---------- transform stack ----------
    def at(self, x, y, z, ry=0.0):
        self.M.append(self.M[-1] @ Matrix.Translation((x, y, z)) @ Matrix.Rotation(ry, 4, 'Y'))

    def pop(self):
        self.M.pop()

    def rr(self, a, b):
        return self.rng.uniform(a, b)

    def bm(self, mat):
        k = (self.group, mat)
        b = self.parts.get(k)
        if b is None:
            b = bmesh.new(); self.parts[k] = b
        return b

    def W(self, x, y, z):
        """local point -> game-world point under the current transform"""
        return self.M[-1] @ Vector((x, y, z))

    # ---------- collision ----------
    def colw(self, pts):
        xs = [p[0] for p in pts]; ys = [p[1] for p in pts]; zs = [p[2] for p in pts]
        self.cols.append([round(min(xs), 3), round(min(ys), 3), round(min(zs), 3), round(max(xs), 3), round(max(ys), 3), round(max(zs), 3)])

    def col(self, x0, y0, z0, x1, y1, z1, m=None):
        M = m or self.M[-1]
        self.colw([M @ Vector((x, y, z)) for x in (x0, x1) for y in (y0, y1) for z in (z0, z1)])

    # ---------- primitives ----------
    def box(self, mat, x0, y0, z0, x1, y1, z1, col=False, m=None, bevel=True):
        x0, x1 = min(x0, x1), max(x0, x1); y0, y1 = min(y0, y1), max(y0, y1); z0, z1 = min(z0, z1), max(z0, z1)
        if x1 - x0 < 1e-4 or y1 - y0 < 1e-4 or z1 - z0 < 1e-4:
            return
        M = m or self.M[-1]
        b = self.bm(mat if bevel else mat + '~flat')
        V = []
        for i in range(8):
            p = Vector((x1 if i & 1 else x0, y1 if i & 2 else y0, z1 if i & 4 else z0))
            V.append(b.verts.new(T2B(M @ p)))
        for f in ((0, 4, 6, 2), (1, 3, 7, 5), (0, 1, 5, 4), (2, 6, 7, 3), (0, 2, 3, 1), (4, 5, 7, 6)):
            b.faces.new([V[j] for j in f])
        if col:
            self.col(x0, y0, z0, x1, y1, z1, M)

    def obox(self, mat, cx, cy, cz, w, h, d, rot=(0, 0, 0), col=False):
        m = self.M[-1] @ Matrix.Translation((cx, cy, cz)) @ Euler(rot, 'ZYX').to_matrix().to_4x4()
        self.box(mat, -w / 2, -h / 2, -d / 2, w / 2, h / 2, d / 2, col=col, m=m)

    def cyl(self, mat, cx, cy, cz, r, h, axis='y', seg=12, col=False, r2=None):
        """cylinder from (cx,cy,cz) along +axis for length h"""
        r2 = r if r2 is None else r2
        rot = {'y': Matrix.Identity(4), 'x': Matrix.Rotation(-PI / 2, 4, 'Z'), 'z': Matrix.Rotation(PI / 2, 4, 'X')}[axis]
        M = self.M[-1] @ Matrix.Translation((cx, cy, cz)) @ rot
        b = self.bm(mat)
        bot, top = [], []
        for i in range(seg):
            a = 2 * PI * i / seg
            bot.append(b.verts.new(T2B(M @ Vector((math.cos(a) * r, 0, -math.sin(a) * r)))))
            top.append(b.verts.new(T2B(M @ Vector((math.cos(a) * r2, h, -math.sin(a) * r2)))))
        for i in range(seg):
            j = (i + 1) % seg
            b.faces.new([bot[i], bot[j], top[j], top[i]])
        b.faces.new(list(reversed(bot))); b.faces.new(top)
        if col:
            rr = max(r, r2)
            pts = [M @ Vector((sx * rr, y, sz * rr)) for sx in (-1, 1) for sz in (-1, 1) for y in (0, h)]
            self.colw(pts)

    def quad(self, mat, A, B, C, D):
        """one-sided quad in local game coords (A,B,C,D counter-clockwise seen from the visible side)"""
        M = self.M[-1]; b = self.bm(mat)
        b.faces.new([b.verts.new(T2B(M @ Vector(p))) for p in (A, B, C, D)])

    def slab_poly(self, mat, pts_xz, y0, y1, col=False):
        """vertical prism from a polygon given in local x,z (counter-clockwise from above)"""
        M = self.M[-1]; b = self.bm(mat)
        lo = [b.verts.new(T2B(M @ Vector((x, y0, z)))) for x, z in pts_xz]
        hi = [b.verts.new(T2B(M @ Vector((x, y1, z)))) for x, z in pts_xz]
        n = len(pts_xz)
        b.faces.new(hi[::-1]); b.faces.new(lo)
        for i in range(n):
            j = (i + 1) % n
            b.faces.new([lo[i], lo[j], hi[j], hi[i]])
        if col:
            xs = [p[0] for p in pts_xz]; zs = [p[1] for p in pts_xz]
            self.col(min(xs), y0, min(zs), max(xs), y1, max(zs))

    # ---------- walls with openings (single welded mesh, real reveals) ----------
    def wall(self, mat, axis, s0, s1, c, t, y0, y1, holes=(), col=True, band=True):
        """axis 'x': wall runs along x from s0..s1 at z=c (thickness t); axis 'z': along z at x=c.
        holes: [(s0, s1, y0, y1), ...] -- doorways/windows get real reveal faces."""
        holes = [h for h in holes if h[1] > s0 and h[0] < s1 and h[3] > y0 and h[2] < y1]
        S = {s0, s1}; Y = {y0, y1}
        for h in holes:
            S.add(max(s0, min(s1, h[0]))); S.add(max(s0, min(s1, h[1])))
            Y.add(max(y0, min(y1, h[2]))); Y.add(max(y0, min(y1, h[3])))
        if band:
            for f in FLOORS:
                for yy in (f + 0.6,):
                    if y0 < yy < y1:
                        Y.add(yy)
            if y0 < y1 - 0.25:
                Y.add(y1 - 0.25)
        S = sorted(S); Y = sorted(Y)
        S = [v for i, v in enumerate(S) if i == 0 or v - S[i - 1] > 1e-4]
        Y = [v for i, v in enumerate(Y) if i == 0 or v - Y[i - 1] > 1e-4]
        ni, nj = len(S) - 1, len(Y) - 1

        def solid(i, j):
            if i < 0 or j < 0 or i >= ni or j >= nj:
                return False
            ms, my = (S[i] + S[i + 1]) / 2, (Y[j] + Y[j + 1]) / 2
            return not any(h[0] < ms < h[1] and h[2] < my < h[3] for h in holes)

        M = self.M[-1]; b = self.bm(mat)
        cache = {}

        def P(i, j, side):
            k = (i, j, side)
            v = cache.get(k)
            if v is None:
                s, y = S[i], Y[j]; cc = c - t / 2 if side == 0 else c + t / 2
                p = Vector((s, y, cc)) if axis == 'x' else Vector((cc, y, s))
                v = b.verts.new(T2B(M @ p)); cache[k] = v
            return v
        flip = axis == 'z'

        def F(vs):
            b.faces.new(vs[::-1] if flip else vs)
        for i in range(ni):
            for j in range(nj):
                if not solid(i, j):
                    continue
                F([P(i, j, 0), P(i, j + 1, 0), P(i + 1, j + 1, 0), P(i + 1, j, 0)])
                F([P(i, j, 1), P(i + 1, j, 1), P(i + 1, j + 1, 1), P(i, j + 1, 1)])
                if not solid(i - 1, j):
                    F([P(i, j, 0), P(i, j, 1), P(i, j + 1, 1), P(i, j + 1, 0)])
                if not solid(i + 1, j):
                    F([P(i + 1, j, 0), P(i + 1, j + 1, 0), P(i + 1, j + 1, 1), P(i + 1, j, 1)])
                if not solid(i, j - 1):
                    F([P(i, j, 0), P(i + 1, j, 0), P(i + 1, j, 1), P(i, j, 1)])
                if not solid(i, j + 1):
                    F([P(i, j + 1, 0), P(i, j + 1, 1), P(i + 1, j + 1, 1), P(i + 1, j + 1, 0)])
        if col:
            for i in range(ni):
                run = None
                for j in range(nj + 1):
                    if j < nj and solid(i, j):
                        if run is None:
                            run = Y[j]
                    elif run is not None:
                        ya, yb = run, Y[j]
                        if axis == 'x':
                            self.col(S[i], ya, c - t / 2, S[i + 1], yb, c + t / 2)
                        else:
                            self.col(c - t / 2, ya, S[i], c + t / 2, yb, S[i + 1])
                        run = None

    def wall2(self, axis, s0, s1, c, t, y0, y1, holes=(), lower='TF_Dado', upper='TF_Wall', band=1.2, trim='TF_Steel', col=True):
        """TF2-style wall: darker painted lower band, cream block upper part, thin steel trim line between"""
        yb = y0 + band
        if y1 <= yb + 0.05:
            self.wall(lower, axis, s0, s1, c, t, y0, y1, holes, col=col, band=False); return
        self.wall(lower, axis, s0, s1, c, t, y0, yb, holes, col=col, band=False)
        self.wall(upper, axis, s0, s1, c, t, yb, y1, holes, col=col, band=False)
        # trim strip on both faces, skipping holes that cross the band
        cuts = sorted([(h[0], h[1]) for h in holes if h[2] < yb + 0.06 and h[3] > yb - 0.06])
        segs, a = [], s0
        for h0, h1 in cuts:
            if h0 > a: segs.append((a, min(h0, s1)))
            a = max(a, h1)
        if a < s1: segs.append((a, s1))
        for a0, a1 in segs:
            for f in (-1, 1):
                cc0, cc1 = c + f * t / 2, c + f * (t / 2 + 0.035)
                if axis == 'x':
                    self.box(trim, a0, yb - 0.05, min(cc0, cc1), a1, yb + 0.05, max(cc0, cc1))
                else:
                    self.box(trim, min(cc0, cc1), yb - 0.05, a0, max(cc0, cc1), yb + 0.05, a1)

    def lamp(self, x, yc, z, drop=2.0, light=True, color='#ffe7c2', intensity=1.4, dist=16):
        """hanging industrial lamp: cable from ceiling yc, shade, bulb"""
        yl = yc - drop
        self.cyl('TF_Steel', x, yl + 0.35, z, 0.012, drop - 0.35, seg=6)
        self.cyl('TF_Steel', x, yl, z, 0.42, 0.35, seg=16, r2=0.08)
        self.cyl('TF_Bulb', x, yl - 0.06, z, 0.14, 0.08, seg=10)
        if light:
            self.light(x, yl - 0.3, z, color, intensity, dist)

    # ---------- helpers ----------
    @staticmethod
    def rect_minus(x0, z0, x1, z1, holes, fn):
        """call fn(x0,z0,x1,z1) for rectangles covering [x0,x1]x[z0,z1] minus the hole rectangles (x0,z0,x1,z1)"""
        xs = {x0, x1}; zs = {z0, z1}
        for h in holes:
            for x in (h[0], h[2]):
                if x0 < x < x1: xs.add(x)
            for z in (h[1], h[3]):
                if z0 < z < z1: zs.add(z)
        X = sorted(xs); Z = sorted(zs)
        for i in range(len(X) - 1):
            run = None
            for j in range(len(Z) - 1):
                mx, mz = (X[i] + X[i + 1]) / 2, (Z[j] + Z[j + 1]) / 2
                inhole = any(h[0] < mx < h[2] and h[1] < mz < h[3] for h in holes)
                if not inhole and run is None:
                    run = Z[j]
                if inhole or j == len(Z) - 2:
                    end = Z[j] if inhole else Z[j + 1]
                    if run is not None and end > run:
                        fn(X[i], run, X[i + 1], end)
                    run = None

    def slab(self, mat, x0, z0, x1, z1, y0, y1, holes=(), col=True, under=None):
        """floor/ceiling slab with rectangular holes (stair wells, drops). Top face uses `mat` (flat, no bevel seams);
        `under` (optional) is a second material for a thin soffit under the slab."""
        def f(a0, b0, a1, b1):
            self.box(mat, a0, y0, b0, a1, y1, b1, col=col, bevel=False)
        self.rect_minus(x0, z0, x1, z1, holes, f)

    def light(self, x, y, z, color, intensity, dist, flicker=False):
        p = self.M[-1] @ Vector((x, y, z))
        self.lights.append({'p': [round(p.x, 3), round(p.y, 3), round(p.z, 3)], 'color': color, 'intensity': intensity, 'dist': dist, 'flicker': flicker})

    def area(self, name, x0, z0, x1, z1, level, **o):
        pts = [self.M[-1] @ Vector((x, 0, z)) for x in (x0, x1) for z in (z0, z1)]
        xs = [p.x for p in pts]; zs = [p.z for p in pts]
        d = {'name': name, 'x0': round(min(xs), 2), 'z0': round(min(zs), 2), 'x1': round(max(xs), 2), 'z1': round(max(zs), 2), 'level': level, 'team': None, 'kind': 'room'}
        d.update(o); self.areas.append(d)

    def label(self, text, x, y, z, **o):
        p = self.M[-1] @ Vector((x, y, z))
        d = {'text': text, 'p': [round(p.x, 2), round(p.y, 2), round(p.z, 2)], 'team': None, 'kind': 'room'}; d.update(o); self.labels.append(d)

    def prop(self, src, x, y, z, ry=0.0, scale=1.0, col=None):
        """place a library model (Poly Haven / Sketchfab source object name) -- instanced in Blender by build.py;
        col: optional local AABB (x0,y0,z0,x1,y1,z1) added as a collider"""
        p = self.M[-1] @ Vector((x, y, z))
        yaw = math.atan2(self.M[-1][0][2], self.M[-1][0][0])   # rotation of the current frame about Y
        self.props.append({'src': src, 'p': [round(p.x, 3), round(p.y, 3), round(p.z, 3)], 'ry': round(ry - yaw, 4), 'scale': scale})
        if col:
            self.at(x, y, z, ry); self.col(*col); self.pop()

    def opening_rec(self, axis, s0, s1, c, t, y0, y1):
        a0, a1, b0, b1, c0, c1 = s0 + 0.15, s1 - 0.15, y0 + 0.12, y1 - 0.12, c - t / 2 - 0.25, c + t / 2 + 0.25
        pts = []
        for a in (a0, a1):
            for bb in (b0, b1):
                for cc in (c0, c1):
                    pts.append(self.M[-1] @ (Vector((a, bb, cc)) if axis == 'x' else Vector((cc, bb, a))))
        xs = [p.x for p in pts]; ys = [p.y for p in pts]; zs = [p.z for p in pts]
        self.openings.append([min(xs), min(ys), min(zs), max(xs), max(ys), max(zs)])


# ---------------- finishing: bevel, UVs, grime, objects, materials ----------------
def hex_lin(h):
    h = h.lstrip('#'); c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    return [v / 12.92 if v <= 0.04045 else ((v + 0.055) / 1.055) ** 2.4 for v in c]


def floor_below(y):
    best = -99
    for f in FLOORS:
        if f <= y + 0.02 and f > best:
            best = f
    return best


def finish_bmesh(b, mat, bevel=0.012):
    if mat.endswith('~flat'):
        bevel = 0
    b.normal_update()
    if mat not in ('Glass', 'Grate') and bevel > 0:
        edges = []
        for e in b.edges:
            if len(e.link_faces) == 2:
                try:
                    ang = e.calc_face_angle()
                except ValueError:
                    continue
                if ang > 0.6 and e.calc_length() > 0.03:
                    edges.append(e)
        if edges:
            bmesh.ops.bevel(b, geom=edges, offset=bevel, offset_type='OFFSET', segments=1, profile=0.5, affect='EDGES', clamp_overlap=True)
    b.normal_update()
    uv = b.loops.layers.uv.new('UVMap')
    colr = b.loops.layers.float_color.new('Col')
    sign = mat.startswith(SIGN_PREFIX)
    tf = mat.startswith('TF_')
    for f in b.faces:
        n = f.normal
        ax, ay, az = abs(n.x), abs(n.y), abs(n.z)
        horiz = az >= ax and az >= ay
        if sign:
            if horiz:
                pa = [(l.vert.co.x, l.vert.co.y) for l in f.loops]
            elif ax >= ay:
                pa = [(-l.vert.co.y if n.x > 0 else l.vert.co.y, l.vert.co.z) for l in f.loops]
            else:
                pa = [(l.vert.co.x if n.y < 0 else -l.vert.co.x, l.vert.co.z) for l in f.loops]
            us = [a for a, _ in pa]; vs = [b_ for _, b_ in pa]
            u0, u1, v0, v1 = min(us), max(us), min(vs), max(vs)
        for li, l in enumerate(f.loops):
            co = l.vert.co
            if sign:
                l[uv].uv = ((pa[li][0] - u0) / max(1e-6, u1 - u0), (pa[li][1] - v0) / max(1e-6, v1 - v0))
            elif horiz:
                l[uv].uv = (co.x, co.y)
            elif ax >= ay:
                l[uv].uv = (co.y, co.z)
            else:
                l[uv].uv = (co.x, co.z)
            if tf:
                g = 1.0 + 0.04 * noise.noise(co * 0.15)
            else:
                g = 1.0 + 0.10 * noise.noise(co * 0.21) + 0.05 * noise.noise(co * 1.3)
            if not horiz:
                h = co.z - floor_below(co.z)
                g *= 1.0 - 0.28 * max(0.0, 1.0 - h / 0.65)
            elif n.z < 0:
                g *= 0.85
            g = max(0.45, min(1.12, g))
            l[colr] = (g, g * 0.985, g * 0.965, 1.0)


def _tex(texdir, tid, kind):
    for ext in ('.webp', '.jpg', '.png'):
        p = os.path.join(texdir, '%s_%s%s' % (tid, kind, ext))
        if os.path.exists(p):
            return p
    return None


def make_material(name, texdir):
    key = name
    m = bpy.data.materials.get('MAT-' + key) or bpy.data.materials.new('MAT-' + key)
    m.use_nodes = True
    nt = m.node_tree; nt.nodes.clear()
    out = nt.nodes.new('ShaderNodeOutputMaterial'); bsdf = nt.nodes.new('ShaderNodeBsdfPrincipled')
    nt.links.new(bsdf.outputs[0], out.inputs[0])
    d = MATS.get(key, ('concrete_floor_worn_001', 3, '#ff00ff', 0.9, 0))
    tid, tile, col, rough, metal = d
    bsdf.inputs['Roughness'].default_value = rough
    bsdf.inputs['Metallic'].default_value = metal
    lin = hex_lin(col)
    if key == 'TF_Bulb':
        bsdf.inputs['Base Color'].default_value = (*lin, 1)
        bsdf.inputs['Emission Color'].default_value = (*lin, 1)
        bsdf.inputs['Emission Strength'].default_value = 6.0
        return m
    if key == 'Glass':
        bsdf.inputs['Base Color'].default_value = (*lin, 1)
        bsdf.inputs['Alpha'].default_value = 0.45
        try:
            m.surface_render_method = 'BLENDED'
        except Exception:
            pass
        return m
    dpath = _tex(texdir, tid, 'd'); npath = _tex(texdir, tid, 'n')
    tc = nt.nodes.new('ShaderNodeTexCoord'); mp = nt.nodes.new('ShaderNodeMapping')
    mp.inputs['Scale'].default_value = (1 / tile, 1 / tile, 1)
    nt.links.new(tc.outputs['UV'], mp.inputs['Vector'])
    vc = nt.nodes.new('ShaderNodeVertexColor'); vc.layer_name = 'Col'
    mix = nt.nodes.new('ShaderNodeMix'); mix.data_type = 'RGBA'; mix.blend_type = 'MULTIPLY'; mix.inputs[0].default_value = 1.0
    if dpath:
        img = bpy.data.images.get(os.path.basename(dpath)) or bpy.data.images.load(dpath, check_existing=True)
        tx = nt.nodes.new('ShaderNodeTexImage'); tx.image = img
        nt.links.new(mp.outputs[0], tx.inputs[0])
        avg = TEXAVG.get(tid, (0.5, 0.5, 0.5))
        k = [min(10, lin[i] / max(1e-3, avg[i])) for i in range(3)]
        tint = nt.nodes.new('ShaderNodeMix'); tint.data_type = 'RGBA'; tint.blend_type = 'MULTIPLY'; tint.inputs[0].default_value = 1.0
        nt.links.new(tx.outputs['Color'], tint.inputs[6]); tint.inputs[7].default_value = (*k, 1)
        nt.links.new(tint.outputs[2], mix.inputs[6])
    else:
        mix.inputs[6].default_value = (*lin, 1)
    nt.links.new(vc.outputs['Color'], mix.inputs[7])
    nt.links.new(mix.outputs[2], bsdf.inputs['Base Color'])
    if npath:
        nimg = bpy.data.images.get(os.path.basename(npath)) or bpy.data.images.load(npath, check_existing=True)
        nimg.colorspace_settings.name = 'Non-Color'
        ntx = nt.nodes.new('ShaderNodeTexImage'); ntx.image = nimg
        nt.links.new(mp.outputs[0], ntx.inputs[0])
        nm = nt.nodes.new('ShaderNodeNormalMap'); nm.inputs['Strength'].default_value = 0.9
        nt.links.new(ntx.outputs['Color'], nm.inputs['Color']); nt.links.new(nm.outputs['Normal'], bsdf.inputs['Normal'])
    return m


TEXAVG = {}


def build_objects(kit, texdir, collection_for_group):
    mats = {}
    objs = []
    for (group, mat), b in kit.parts.items():
        if not b.faces:
            continue
        finish_bmesh(b, mat)
        flat = mat.endswith('~flat'); mat = mat.replace('~flat', '')
        me = bpy.data.meshes.new('ME-%s__%s%s' % (group, mat, '_flat' if flat else ''))
        b.to_mesh(me); b.free()
        me.shade_flat() if hasattr(me, 'shade_flat') else None
        if mat not in mats:
            mats[mat] = make_material(mat, texdir)
        me.materials.append(mats[mat])
        ob = bpy.data.objects.new('GEO-%s__%s%s' % (group, mat, '_flat' if flat else ''), me)
        collection_for_group(group).objects.link(ob)
        objs.append(ob)
    kit.parts = {}
    return objs
