"""
Procedural PBR recipes for the Wash Junction kit (Blender 4.0 / Cycles).

Every recipe is a node graph that is *baked* into T_<Name>_BaseColor / _Normal / _ORM,
so nothing here ships to the engine as a shader -- it only has to look right once.

Inputs every recipe can read (see class G):
    g.P    part-local coordinates, metres. x = the part's longest axis (wood grain, streak
           direction, plank length).  Stored per vertex as the "lco" attribute by assetkit.
    g.W    object/world position, metres (Z up, ground at z=0).
    g.N    shading normal (world), g.up = N.z
    g.pid  random 0..1 per part (plank-to-plank / bolt-to-bolt variation)
    g.edge()   convex+concave edge mask   (baked once per asset, then read from a mask image)
    g.cav()    cavity / crevice amount     (0 open .. 1 deep)
    g.convex() worn convex edges only
Recipes return dict(color, rough, metal, height[mm], alpha?) -- height is in millimetres
and becomes the baked normal map together with a Bevel node (rounded hard edges for free).
"""
import bpy, math

DUST = "#b5a588"     # Mojave road dust, sun bleached
DIRT = "#6a5844"     # wet-then-dried mud splash
GRIME = (0.30, 0.27, 0.235)   # multiply colour for crevice grime


def lin1(c):
    return c / 12.92 if c <= 0.04045 else ((c + 0.055) / 1.055) ** 2.4


def rgb(h):
    """'#rrggbb' (sRGB) -> linear RGBA tuple."""
    if isinstance(h, (tuple, list)):
        return tuple(h) + ((1.0,) if len(h) == 3 else ())
    h = h.lstrip("#")
    return tuple(lin1(int(h[i:i + 2], 16) / 255.0) for i in (0, 2, 4)) + (1.0,)


class G:
    """Tiny node-graph builder. Every op accepts sockets or plain numbers/tuples."""

    def __init__(self, mat, ctx):
        self.mat, self.ctx = mat, ctx
        self.nt = mat.node_tree
        self.nt.nodes.clear()
        self.L = self.nt.links
        self._n = 0
        self._mask = None
        self._live = None
        a = self.node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="lco")
        self.P = a.outputs["Vector"]
        b = self.node("ShaderNodeAttribute", attribute_type="GEOMETRY", attribute_name="pid")
        self.pid = b.outputs["Fac"]
        tc = self.node("ShaderNodeTexCoord")
        self.W = tc.outputs["Object"]
        geo = self.node("ShaderNodeNewGeometry")
        self.N = geo.outputs["Normal"]
        self.Wx, self.Wy, self.Wz = self.sep(self.W)
        self.Nx, self.Ny, self.Nz = self.sep(self.N)
        self.up = self.Nz
        self.vert = self.sub(1.0, self.absv(self.Nz))      # 1 on walls, 0 on floors/roofs

    # ---------------------------------------------------------------- plumbing
    def node(self, t, **props):
        n = self.nt.nodes.new(t)
        for k, v in props.items():
            setattr(n, k, v)
        self._n += 1
        n.location = ((self._n % 30) * 220, -(self._n // 30) * 300)
        return n

    def _set(self, sock, v):
        if isinstance(v, bpy.types.NodeSocket):
            self.L.new(v, sock)
            return
        if sock.type == "RGBA":
            if isinstance(v, str):
                v = rgb(v)
            elif not isinstance(v, (tuple, list)):
                v = (v, v, v, 1.0)
            sock.default_value = tuple(v)[:3] + (1.0,)
        elif sock.type == "VECTOR":
            sock.default_value = (v, v, v) if not isinstance(v, (tuple, list)) else tuple(v)[:3]
        else:
            sock.default_value = v

    # ---------------------------------------------------------------- float math
    def m(self, op, a, b=0.0, c=0.0, clamp=False):
        n = self.node("ShaderNodeMath", operation=op, use_clamp=clamp)
        self._set(n.inputs[0], a); self._set(n.inputs[1], b); self._set(n.inputs[2], c)
        return n.outputs[0]

    def add(self, a, b): return self.m("ADD", a, b)
    def sub(self, a, b): return self.m("SUBTRACT", a, b)
    def mul(self, a, b): return self.m("MULTIPLY", a, b)
    def div(self, a, b): return self.m("DIVIDE", a, b)
    def mn(self, a, b): return self.m("MINIMUM", a, b)
    def mx(self, a, b): return self.m("MAXIMUM", a, b)
    def pw(self, a, b): return self.m("POWER", a, b)
    def absv(self, a): return self.m("ABSOLUTE", a)
    def fract(self, a): return self.m("FRACT", a)
    def floor(self, a): return self.m("FLOOR", a)
    def sin(self, a): return self.m("SINE", a)
    def clamp(self, a): return self.m("ADD", a, 0.0, clamp=True)
    def inv(self, a): return self.m("SUBTRACT", 1.0, a)
    def madd(self, a, b, c): return self.m("MULTIPLY_ADD", a, b, c)

    def sum(self, *terms):
        """sum((sock_or_val, weight), ...)"""
        out = 0.0
        for t, w in terms:
            out = self.madd(t, w, out)
        return out

    def lin(self, x, a, b, c=0.0, d=1.0):
        n = self.node("ShaderNodeMapRange", clamp=True, interpolation_type="LINEAR")
        for i, v in enumerate((x, a, b, c, d)):
            self._set(n.inputs[i], v)
        return n.outputs[0]

    def smooth(self, x, e0, e1):
        """smoothstep(e0, e1, x); e0 > e1 gives the inverted ramp."""
        if e0 > e1:
            return self.inv(self.smooth(x, e1, e0))
        n = self.node("ShaderNodeMapRange", clamp=True, interpolation_type="SMOOTHSTEP")
        for i, v in enumerate((x, e0, e1, 0.0, 1.0)):
            self._set(n.inputs[i], v)
        return n.outputs[0]

    # ---------------------------------------------------------------- vectors
    def vm(self, op, a, b=(0, 0, 0), scale=1.0):
        n = self.node("ShaderNodeVectorMath", operation=op)
        self._set(n.inputs[0], a); self._set(n.inputs[1], b)
        if op == "SCALE":
            self._set(n.inputs[3], scale)
        return n.outputs[1] if op in ("DOT_PRODUCT", "LENGTH", "DISTANCE") else n.outputs[0]

    def vs(self, v, s):
        """component-wise scale; s may be a number or (sx, sy, sz)"""
        return self.vm("MULTIPLY", v, s if isinstance(s, (tuple, list)) else (s, s, s))

    def vo(self, v, o):
        return self.vm("ADD", v, o if isinstance(o, (tuple, list, bpy.types.NodeSocket)) else (o, o, o))

    def sep(self, v):
        n = self.node("ShaderNodeSeparateXYZ")
        self._set(n.inputs[0], v)
        return n.outputs[0], n.outputs[1], n.outputs[2]

    def comb(self, x, y, z):
        n = self.node("ShaderNodeCombineXYZ")
        for i, v in enumerate((x, y, z)):
            self._set(n.inputs[i], v)
        return n.outputs[0]

    def rot(self, v, axis="Z", deg=0.0):
        n = self.node("ShaderNodeVectorRotate", rotation_type=axis + "_AXIS")
        self._set(n.inputs["Vector"], v)
        n.inputs["Angle"].default_value = math.radians(deg)
        return n.outputs[0]

    # ---------------------------------------------------------------- textures
    def noise(self, v, scale=1.0, detail=4.0, rough=0.5, dist=0.0, lac=2.0, color=False):
        n = self.node("ShaderNodeTexNoise", noise_dimensions="3D")
        self._set(n.inputs["Vector"], v); self._set(n.inputs["Scale"], scale)
        self._set(n.inputs["Detail"], detail); self._set(n.inputs["Roughness"], rough)
        self._set(n.inputs["Lacunarity"], lac); self._set(n.inputs["Distortion"], dist)
        return n.outputs["Color" if color else "Fac"]

    def vor(self, v, scale=1.0, feature="F1", out="Distance", rand=1.0, metric="EUCLIDEAN", detail=0.0):
        n = self.node("ShaderNodeTexVoronoi", voronoi_dimensions="3D", feature=feature, distance=metric)
        self._set(n.inputs["Vector"], v); self._set(n.inputs["Scale"], scale)
        self._set(n.inputs["Randomness"], rand)
        if detail:
            self._set(n.inputs["Detail"], detail)
        return n.outputs[out]

    def wave(self, v, scale=1.0, direction="X", dist=0.0, detail=0.0, profile="SIN", kind="BANDS", phase=0.0):
        n = self.node("ShaderNodeTexWave", wave_type=kind, bands_direction=direction, rings_direction=direction
                      if direction != "DIAGONAL" else "SPHERICAL", wave_profile=profile)
        self._set(n.inputs["Vector"], v); self._set(n.inputs["Scale"], scale)
        self._set(n.inputs["Distortion"], dist); self._set(n.inputs["Detail"], detail)
        self._set(n.inputs["Phase Offset"], phase)
        return n.outputs["Fac"]

    def white(self, v, color=False):
        n = self.node("ShaderNodeTexWhiteNoise", noise_dimensions="3D")
        self._set(n.inputs["Vector"], v)
        return n.outputs["Color" if color else "Value"]

    def image(self, img, vec=None, extension="REPEAT", interp="Linear", alpha=False):
        n = self.node("ShaderNodeTexImage", image=img, extension=extension, interpolation=interp)
        if vec is not None:
            self._set(n.inputs["Vector"], vec)
        return n.outputs["Alpha" if alpha else "Color"]

    # ---------------------------------------------------------------- colour
    def mixc(self, f, a, b, blend="MIX"):
        n = self.node("ShaderNodeMix", data_type="RGBA", blend_type=blend, clamp_result=False)
        self._set(n.inputs[0], f); self._set(n.inputs[6], a); self._set(n.inputs[7], b)
        return n.outputs[2]

    def mixf(self, f, a, b):
        n = self.node("ShaderNodeMix", data_type="FLOAT", clamp_factor=True)
        self._set(n.inputs[0], f); self._set(n.inputs[2], a); self._set(n.inputs[3], b)
        return n.outputs[0]

    def mulc(self, col, k):
        """col * k (k: float socket/number or colour)"""
        return self.mixc(1.0, col, k, "MULTIPLY")

    def hsv(self, col, h=0.5, s=1.0, v=1.0):
        n = self.node("ShaderNodeHueSaturation")
        self._set(n.inputs["Hue"], h); self._set(n.inputs["Saturation"], s)
        self._set(n.inputs["Value"], v); self._set(n.inputs["Fac"], 1.0); self._set(n.inputs["Color"], col)
        return n.outputs[0]

    def ramp(self, f, stops, interp="LINEAR"):
        n = self.node("ShaderNodeValToRGB")
        cr = n.color_ramp
        cr.interpolation = interp
        while len(cr.elements) < len(stops):
            cr.elements.new(0.5)
        for el, (pos, col) in zip(cr.elements, stops):
            el.position = pos
            el.color = rgb(col)
        self._set(n.inputs[0], f)
        return n.outputs[0]

    def const_c(self, col):
        n = self.node("ShaderNodeRGB")
        n.outputs[0].default_value = rgb(col)
        return n.outputs[0]

    def const_f(self, v):
        n = self.node("ShaderNodeValue")
        n.outputs[0].default_value = v
        return n.outputs[0]

    # ---------------------------------------------------------------- masks
    def live_masks(self):
        """edge / cavity / AO computed by ray tracing (used for the mask pre-bake and drafts)."""
        if self._live is None:
            c = self.ctx
            bev = self.node("ShaderNodeBevel", samples=8)
            bev.inputs["Radius"].default_value = c.get("edge_r", 0.012)
            d = self.vm("DOT_PRODUCT", bev.outputs[0], self.N)
            edge = self.pw(self.clamp(self.mul(self.sub(1.0, d), 5.0)), 0.7)
            ao_s = self.node("ShaderNodeAmbientOcclusion", only_local=True, samples=8)
            ao_s.inputs["Distance"].default_value = c.get("cav_d", 0.06)
            cav = self.clamp(self.mul(self.sub(1.0, ao_s.outputs["AO"]), 1.3))
            ao_l = self.node("ShaderNodeAmbientOcclusion", only_local=True, samples=8)
            ao_l.inputs["Distance"].default_value = c.get("ao_d", 0.5)
            self._live = (edge, cav, ao_l.outputs["AO"])
        return self._live

    def masks(self):
        if self._mask is None:
            img = self.ctx.get("mask_image")
            if img is None:
                self._mask = self.live_masks()
            else:
                n = self.node("ShaderNodeTexImage", image=img, interpolation="Linear")
                n.name = "MASK_READ"
                s = self.node("ShaderNodeSeparateColor")
                self.L.new(n.outputs[0], s.inputs[0])
                self._mask = (s.outputs[0], s.outputs[1], s.outputs[2])
        return self._mask

    def edge(self): return self.masks()[0]
    def cav(self): return self.masks()[1]
    def ao(self): return self.masks()[2]

    def convex(self):
        """edges that stick out (wear), not inside corners (dirt)."""
        e, c, _ = self.masks()
        return self.mul(e, self.pw(self.inv(c), 3.0))

    # ---------------------------------------------------------------- shared layers
    def jitter(self, col, amt=1.0):
        """per-part hue/sat/value variation"""
        j = self.sub(self.pid, 0.5)
        return self.hsv(col, self.add(0.5, self.mul(j, 0.016 * amt)), self.add(1.0, self.mul(j, 0.16 * amt)),
                        self.add(1.0, self.mul(j, 0.18 * amt)))

    def mottle(self, col, amt=0.12, scale=1.0):
        n = self.add(self.mul(self.noise(self.W, 1.1 * scale, 3, 0.5), 0.5),
                     self.mul(self.noise(self.vo(self.P, 7.3), 6.5 * scale, 5, 0.55), 0.5))
        return self.hsv(col, 0.5, 1.0, self.lin(n, 0.3, 0.7, 1.0 - amt, 1.0 + amt))

    def rust_layer(self, P=None, light=1.0):
        P = P if P is not None else self.P
        n1 = self.noise(P, 3.2, 8, 0.62)
        n2 = self.noise(self.vo(P, 3.1), 23.0, 6, 0.62, dist=0.35)
        v = self.add(self.mul(n1, 0.62), self.mul(n2, 0.38))
        col = self.ramp(v, [(0.28, "#231914"), (0.40, "#43241a"), (0.50, "#6b3519"), (0.60, "#8f4a1f"), (0.72, "#a8622b")])
        if light != 1.0:
            col = self.hsv(col, 0.5, 1.0, light)
        pits = self.smooth(self.vor(P, 75.0), 0.32, 0.08)
        rough = self.lin(n2, 0.3, 0.75, 0.70, 0.96)
        height = self.sub(self.mul(n2, 0.5), self.mul(pits, 0.25))
        return col, rough, height

    def steel_layer(self, tone="#6c6e70", rough=0.42):
        n = self.noise(self.vs(self.P, (0.6, 9, 9)), 6.0, 4, 0.5)     # rolling / grinding streaks
        col = self.hsv(rgb(tone), 0.5, 1.0, self.lin(n, 0.3, 0.7, 0.82, 1.15))
        r = self.lin(n, 0.3, 0.7, rough - 0.08, rough + 0.1)
        return col, r

    def scratches(self, density=1.0, P=None):
        P = P if P is not None else self.P
        out = 0.0
        for k, (ax, deg, sc) in enumerate((("Z", 23, 1.0), ("Y", -41, 1.3), ("X", 67, 0.8))):
            q = self.rot(self.vo(P, 11.1 * k), ax, deg)
            n = self.noise(self.vs(q, (0.9 * sc, 160.0 * sc, 160.0 * sc)), 1.0, 2, 0.5)
            gate = self.smooth(self.noise(self.vo(P, 5.7 * k), 3.0, 3, 0.5), 0.52, 0.66)
            out = self.mx(out, self.mul(self.smooth(n, 0.70 - 0.03 * density, 0.74 - 0.03 * density), gate))
        return self.mul(out, min(1.0, density))

    def weather(self, col, rough, metal, p):
        """cavity grime, ground splash, vertical streaks and desert dust."""
        grime, dust = p.get("grime", 0.6), p.get("dust", 0.45)
        streaks, splash = p.get("streaks", 0.35), p.get("splash", 0.5)
        if grime > 0:
            gm = self.mul(self.smooth(self.cav(), 0.06, 0.6), grime)
            gm = self.mul(gm, self.lin(self.noise(self.W, 2.5, 4, 0.6), 0.3, 0.7, 0.55, 1.0))
            col = self.mixc(gm, col, self.mulc(col, GRIME))
            rough = self.mixf(gm, rough, self.add(rough, 0.15))
        if streaks > 0:
            s = self.noise(self.vs(self.W, (9.0, 9.0, 0.45)), 1.0, 3, 0.5)
            sm = self.mul(self.mul(self.smooth(s, 0.56, 0.74), self.vert), streaks)
            col = self.mixc(sm, col, self.mulc(col, (0.62, 0.52, 0.43)))
            rough = self.mixf(sm, rough, self.add(rough, 0.08))
        if splash > 0:
            h = p.get("splash_h", 0.3)
            gz = self.inv(self.smooth(self.Wz, 0.0, h))
            sp = self.noise(self.vs(self.W, (5, 5, 9)), 1.0, 6, 0.65)
            speck = self.smooth(self.noise(self.W, 70.0, 2, 0.5), 0.62, 0.7)
            gn = self.clamp(self.sum((self.smooth(self.add(self.mul(gz, 0.9), self.mul(sp, 0.5)), 0.8, 1.05), 1.0),
                                     (self.mul(speck, gz), 0.8)))
            sm = self.mul(gn, splash * 0.6)
            col = self.mixc(sm, col, rgb(DIRT))
            rough = self.mixf(sm, rough, 0.93)
            if metal is not None:
                metal = self.mixf(sm, metal, 0.0)
        if dust > 0:
            facing = self.smooth(self.up, 0.35, 0.95)
            dn = self.smooth(self.noise(self.W, 2.4, 6, 0.62), 0.32, 0.72)
            dm = self.mul(self.add(self.mul(facing, dn), self.mul(self.cav(), 0.25)), dust)
            dm = self.add(dm, 0.06 * dust)
            col = self.mixc(self.clamp(dm), col, rgb(DUST))
            rough = self.mixf(self.clamp(dm), rough, 0.95)
            if metal is not None:
                metal = self.mixf(self.clamp(self.mul(dm, 1.4)), metal, 0.0)
        return col, rough, metal

    def rim(self, col, rough, height, p):
        """Coloured bands just inside the skin of a wheel-shaped solid (for cut faces of cheese wheels).
        p["rim"] = dict(R=outer radius, H=half height, bands=[(width_m, colour, rough), ...] outermost first)."""
        rim = p.get("rim")
        if not rim:
            return col, rough, height
        r = self.vm("LENGTH", self.comb(self.Wx, self.Wy, 0.0))
        d = self.mn(self.sub(rim["R"], r), self.sub(rim["H"], self.absv(self.Wz)))
        d = self.add(d, self.mul(self.sub(self.noise(self.W, 40.0, 3, 0.5), 0.5), 0.004))
        acc, edges = 0.0, []
        for w, c, ro in rim["bands"]:
            acc += w
            edges.append((acc, c, ro))
        for tot, c, ro in reversed(edges):
            m = self.smooth(d, tot + 0.001, tot - 0.0006)
            col = self.mixc(m, col, rgb(c))
            rough = self.mixf(m, rough, ro)
            height = self.add(height, self.mul(m, 0.15))
        return col, rough, height

    def decal(self, d):
        """projected 2D mask (stencils, emblems).  d = dict(img, axes='yz', center, size, facing, coords='W')"""
        src = self.W if d.get("coords", "W") == "W" else self.P
        x, y, z = self.sep(src)
        ax = {"x": x, "y": y, "z": z}
        a, b = d.get("axes", "yz")
        ca, cb = d["center"]; sa, sb = d["size"]
        u = self.add(self.div(self.sub(ax[a], ca), sa), 0.5)
        v = self.add(self.div(self.sub(ax[b], cb), sb), 0.5)
        if d.get("flip_u"):
            u = self.inv(u)
        mval = self.image(d["img"], self.comb(u, v, 0.0), extension="CLIP")
        mval = self.sep(mval)[0]
        f = d.get("facing")
        if f:
            mval = self.mul(mval, self.smooth(self.vm("DOT_PRODUCT", self.N, f), 0.55, 0.8))
        return mval


# ====================================================================== recipes
# Each returns dict(color, rough, metal, height_mm[, alpha])

def r_paint(g, p):
    """Sun-faded enamel over steel/wood: edge chips, primer rings, scratches, streaks, dust."""
    base = g.jitter(rgb(p.get("color", "#6d6f70")), p.get("jitter", 1.0))
    base = g.mottle(base, p.get("mottle", 0.10))
    fade = p.get("fade", 0.35)
    if fade > 0:
        fm = g.mul(g.lin(g.up, -0.4, 1.0, 0.5, 1.0), fade)
        fm = g.mul(fm, g.lin(g.noise(g.W, 1.8, 3, 0.5), 0.3, 0.7, 0.6, 1.25))
        base = g.mixc(g.clamp(fm), base, g.hsv(base, 0.5, 0.55, 1.28))
    chips, flake = p.get("chips", 0.6), p.get("flake", 0.15)
    e = g.convex()
    n = g.noise(g.P, p.get("chip_scale", 15.0), 10, 0.72, dist=0.25)
    field = g.add(g.mul(e, 1.9 * chips), g.mul(g.sub(n, 0.5), 1.25))
    if flake > 0:
        blot = g.smooth(g.noise(g.vo(g.P, 1.7), 2.6, 6, 0.62), 0.66 - 0.06 * flake, 0.71 - 0.06 * flake)
        field = g.add(field, g.mul(blot, 0.9))
    chip = g.smooth(field, 0.56, 0.585)
    ring = g.clamp(g.sub(g.smooth(field, 0.50, 0.53), chip))
    under = p.get("under", "rust")
    if under == "steel":
        uc, ur = g.steel_layer(p.get("steel", "#6a6c6e"), 0.4)
        um, uh = 1.0, 0.0
    elif under == "wood":
        uc, ur, uh = wood_layer(g, p)
        um = 0.0
    elif under == "galv":
        uc, ur = g.steel_layer("#8d9195", 0.38)
        um, uh = 1.0, 0.0
    else:   # rust (bare steel that has oxidised where the paint came off)
        uc, ur, uh = g.rust_layer()
        um = 0.0
        # tiny bright steel core in the middle of big chips
        core = g.mul(g.smooth(field, 0.74, 0.8), p.get("steel_core", 0.6))
        sc, sr = g.steel_layer("#5d5f61", 0.45)
        uc = g.mixc(core, uc, sc); ur = g.mixf(core, ur, sr); um = g.mixf(core, 0.0, 1.0)
    primer = rgb(p.get("primer", "#7b3b26" if under in ("rust", "steel") else "#b9b2a2"))
    col = g.mixc(g.mul(ring, 0.85), base, primer)
    col = g.mixc(chip, col, uc)
    pr = p.get("rough", 0.58)
    rough = g.add(pr, g.mul(g.sub(g.noise(g.P, 11, 4, 0.5), 0.5), 0.18))
    rough = g.mixf(chip, rough, ur)
    metal = g.mixf(chip, 0.0, um)
    sc = p.get("scratch", 0.5)
    height = g.sum((g.inv(chip), 0.55), (ring, -0.15), (g.noise(g.P, 140, 2, 0.5), 0.05))
    if under == "rust":
        height = g.add(height, g.mul(chip, uh))
    if sc > 0:
        s = g.scratches(sc)
        sc_col = rgb("#8c8f92") if under != "wood" else rgb("#a59a86")
        col = g.mixc(g.mul(s, 0.7), col, sc_col)
        rough = g.mixf(s, rough, 0.35)
        metal = g.mixf(g.mul(s, 0.8 if under != "wood" else 0.0), metal, 1.0)
        height = g.sub(height, g.mul(s, 0.12))
    # rust bleed below chips
    if under == "rust" and p.get("bleed", 0.5) > 0:
        bl = g.mul(g.clamp(g.sub(g.smooth(field, 0.38, 0.55), chip)), p.get("bleed", 0.5))
        col = g.mixc(g.mul(bl, 0.45), col, g.mulc(col, (0.78, 0.55, 0.38)))
    col, rough, metal, height = _decals(g, p, col, rough, metal, height)
    col, rough, metal = g.weather(col, rough, metal, p)
    return dict(color=col, rough=rough, metal=metal, height=height)


def _decals(g, p, col, rough, metal, height):
    ds = p.get("decal")
    if not ds:
        return col, rough, metal, height
    for d in (ds if isinstance(ds, (list, tuple)) else [ds]):
        m = g.decal(d)
        wear = g.smooth(g.noise(g.vo(g.W, 3.3), 18.0, 6, 0.6), 0.25, 0.45)    # sprayed stencil, partly worn
        m = g.mul(m, g.mul(wear, d.get("opacity", 0.9)))
        col = g.mixc(m, col, g.mottle(rgb(d.get("color", "#1d1d1b")), 0.1))
        rough = g.mixf(m, rough, d.get("rough", 0.7))
        if metal is not None:
            metal = g.mixf(m, metal, 0.0)
        height = g.add(height, g.mul(m, 0.05))
    return col, rough, metal, height


def r_team(g, p):
    """TeamPaint: neutral light-grey chipped enamel; the engine multiplies team colour in."""
    q = dict(color="#c9c9c5", fade=0.1, chips=0.45, flake=0.05, under="steel", dust=0.25, grime=0.45,
             streaks=0.2, splash=0.3, mottle=0.06, jitter=0.3)
    q.update(p)
    return r_paint(g, q)


def r_rust(g, p):
    """Heavy rust on old iron/tin, with ghosts of the original paint."""
    col, rough, height = g.rust_layer(light=p.get("light", 1.0))
    metal = 0.0
    pc = p.get("paint")
    if pc:
        left = p.get("paint_left", 0.35)
        n = g.noise(g.vo(g.P, 2.2), 4.0, 8, 0.7, dist=0.2)
        keep = g.smooth(g.add(n, g.sub(left, 0.5)), 0.5, 0.53)
        keep = g.mul(keep, g.inv(g.mul(g.convex(), 0.8)))
        pcol = g.mottle(g.hsv(g.jitter(rgb(pc)), 0.5, 0.6, 1.15), 0.15)
        col = g.mixc(keep, col, pcol)
        rough = g.mixf(keep, rough, 0.75)
        height = g.add(height, g.mul(keep, 0.3))
    col, rough, metal = g.weather(col, rough, metal, dict(p, streaks=p.get("streaks", 0.5)))
    return dict(color=col, rough=rough, metal=metal, height=height)


def r_galv(g, p):
    """Hot-dip galvanised steel: spangle, zinc-oxide bloom, a few rust spots."""
    base = rgb(p.get("color", "#8f9396"))
    sp = g.vor(g.P, p.get("spangle", 45.0), out="Color")
    spv = g.sep(sp)[0]
    col = g.hsv(base, 0.5, 1.0, g.lin(spv, 0, 1, 0.965, 1.035))
    col = g.mottle(col, 0.08)
    rough = g.lin(spv, 0, 1, 0.36, 0.46)
    ox = g.smooth(g.noise(g.vo(g.P, 4.4), 3.0, 7, 0.65), 0.56, 0.72)
    ox = g.mul(ox, p.get("oxide", 0.6))
    col = g.mixc(ox, col, rgb("#aeb0ab"))
    rough = g.mixf(ox, rough, 0.78)
    metal = g.mixf(ox, 1.0, 0.25)
    rs = p.get("rust", 0.15)
    if rs > 0:
        rm = g.smooth(g.add(g.mul(g.cav(), 0.8), g.mul(g.noise(g.P, 9.0, 6, 0.65), 0.7)), 0.95 - 0.25 * rs, 1.05 - 0.25 * rs)
        rc, rr, _ = g.rust_layer()
        col = g.mixc(rm, col, rc); rough = g.mixf(rm, rough, rr); metal = g.mixf(rm, metal, 0.0)
    height = g.add(g.mul(spv, 0.06), g.mul(ox, 0.08))
    s = g.scratches(p.get("scratch", 0.3))
    col = g.mixc(g.mul(s, 0.5), col, rgb("#b8bcbf")); rough = g.mixf(s, rough, 0.25)
    col, rough, metal = g.weather(col, rough, metal, dict(p, streaks=p.get("streaks", 0.25)))
    return dict(color=col, rough=rough, metal=metal, height=height)


def r_steel(g, p):
    """Raw / blackened structural steel: mill scale, bright worn edges, rust bloom in crevices."""
    col, rough = g.steel_layer(p.get("color", "#47494b"), p.get("rough", 0.5))
    ms = g.smooth(g.noise(g.vo(g.P, 8.8), 2.4, 5, 0.6), 0.45, 0.65)
    col = g.mixc(g.mul(ms, 0.6), col, rgb("#3b3f46"))
    wear = g.mul(g.convex(), p.get("worn", 0.8))
    col = g.mixc(wear, col, rgb("#9a9c9e")); rough = g.mixf(wear, rough, 0.28)
    metal = 1.0
    rs = p.get("rust", 0.35)
    height = g.mul(g.noise(g.P, 60, 3, 0.5), 0.06)
    if rs > 0:
        rm = g.smooth(g.add(g.mul(g.cav(), 1.0), g.mul(g.noise(g.vo(g.P, 1.3), 6.0, 7, 0.65), 0.8)), 1.1 - 0.4 * rs, 1.2 - 0.4 * rs)
        rc, rr, rh = g.rust_layer()
        col = g.mixc(rm, col, rc); rough = g.mixf(rm, rough, rr); metal = g.mixf(rm, 1.0, 0.0)
        height = g.add(height, g.mul(rm, rh))
    col, rough, metal = g.weather(col, rough, metal, p)
    return dict(color=col, rough=rough, metal=metal, height=height)


def r_diamond(g, p):
    """Diamond (tread) plate.  Pattern lives in the part's local XY (put the plate flat in local XY)."""
    x, y, z = g.sep(g.P)
    pitch = p.get("pitch", 0.032)
    u = g.div(g.add(x, y), pitch * 1.41421)
    v = g.div(g.sub(x, y), pitch * 1.41421)

    def lozenge(uu, vv, along_u):
        fu = g.sub(g.fract(uu), 0.5); fv = g.sub(g.fract(vv), 0.5)
        a, b = (fu, fv) if along_u else (fv, fu)
        d = g.vm("LENGTH", g.comb(g.div(a, 0.42), g.div(b, 0.09), 0.0))
        return g.smooth(d, 1.0, 0.75)

    h1 = lozenge(u, v, True)
    h2 = lozenge(g.add(u, 0.5), g.add(v, 0.5), False)
    bar = g.mx(h1, h2)
    col, rough = g.steel_layer(p.get("color", "#5f6163"), 0.5)
    rc, rr, rh = g.rust_layer()
    rm = g.mul(g.smooth(g.noise(g.vo(g.P, 2.0), 3.0, 6, 0.6), 0.5, 0.8), p.get("rust", 0.5))
    rm = g.mul(rm, g.inv(g.mul(bar, 0.8)))
    col = g.mixc(rm, col, rc); rough = g.mixf(rm, rough, rr)
    metal = g.mixf(rm, 1.0, 0.0)
    shine = g.mul(bar, p.get("worn", 0.8))
    col = g.mixc(shine, col, rgb("#a4a7aa")); rough = g.mixf(shine, rough, 0.26); metal = g.mixf(shine, metal, 1.0)
    pc = p.get("paint")
    if pc:   # painted plate worn back to steel on the diamonds
        keep = g.mul(g.inv(bar), g.smooth(g.noise(g.P, 6, 6, 0.6), 0.35, 0.5))
        col = g.mixc(keep, col, g.mottle(rgb(pc), 0.12)); rough = g.mixf(keep, rough, 0.6); metal = g.mixf(keep, metal, 0.0)
    col, rough, metal = g.weather(col, rough, metal, dict(p, streaks=0.1))
    height = g.add(g.mul(bar, 1.4), g.mul(rm, 0.15))
    return dict(color=col, rough=rough, metal=metal, height=height)


def wood_layer(g, p):
    """Weathered timber. Grain runs along local x."""
    x, y, z = g.sep(g.P)
    o = g.mul(g.pid, 13.0)
    warp = g.noise(g.vo(g.vs(g.P, (0.25, 2.5, 2.5)), o), 1.0, 3, 0.5)
    r = g.vm("LENGTH", g.comb(0.0, g.add(y, g.add(0.18, g.mul(g.pid, 0.25))), g.add(z, g.sub(g.mul(g.pid, 0.3), 0.15))))
    rings = g.fract(g.add(g.mul(r, p.get("rings", 34.0)), g.mul(warp, 6.0)))
    late = g.smooth(rings, 0.72, 0.92)
    fib = g.noise(g.vo(g.vs(g.P, (1.0, 70.0, 70.0)), o), 1.0, 4, 0.6)
    light, dark = rgb(p.get("wood", "#8c7f6b")), rgb(p.get("wood_dark", "#3a3029"))
    col = g.mixc(g.clamp(g.add(g.mul(late, 0.75), g.mul(g.sub(fib, 0.5), 0.9))), light, dark)
    col = g.jitter(col, 1.6)
    wthr = p.get("weather", 0.6)
    grey = g.mul(g.lin(g.up, -0.5, 1.0, 0.55, 1.0), wthr)
    col = g.mixc(grey, col, g.hsv(col, 0.5, 0.3, 1.05))
    crack = g.vor(g.vs(g.P, (1.3, 22.0, 22.0)), 1.0, "DISTANCE_TO_EDGE")
    cm = g.mul(g.smooth(crack, 0.05, 0.0), g.smooth(g.noise(g.vo(g.P, 3.3), 2.5, 3, 0.5), 0.4, 0.55))
    cm = g.mul(cm, p.get("cracks", 0.8))
    knot = g.vor(g.vo(g.vs(g.P, (1.0, 1.6, 1.6)), o), 2.4)
    km = g.mul(g.smooth(knot, 0.11, 0.05), p.get("knots", 0.7))
    col = g.mixc(km, col, g.mulc(col, 0.45))
    col = g.mixc(cm, col, rgb("#1d1915"))
    rough = g.lin(late, 0, 1, 0.82, 0.92)
    height = g.sum((late, 0.55), (fib, 0.25), (cm, -1.2), (km, 0.3))
    return col, rough, height


def r_wood(g, p):
    col, rough, height = wood_layer(g, p)
    col, rough, _, height = _decals(g, p, col, rough, None, height)
    col, rough, _ = g.weather(col, rough, None, dict(p, streaks=p.get("streaks", 0.25)))
    if p.get("nails"):
        # rusty nail heads + stains on a grid along the grain
        x, y, z = g.sep(g.P)
        sp = p.get("nails")
        cell = g.vm("LENGTH", g.comb(g.mul(g.sub(g.fract(g.div(x, sp)), 0.5), sp), y, 0.0))
        nm = g.smooth(cell, 0.006, 0.003)
        st = g.mul(g.smooth(cell, 0.03, 0.006), 0.5)
        col = g.mixc(st, col, g.mulc(col, (0.7, 0.55, 0.42)))
        col = g.mixc(nm, col, rgb("#3a2618"))
        height = g.add(height, g.mul(nm, 0.4))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def r_concrete(g, p):
    """Board-formed / cast concrete with pores, form lines, silt line and efflorescence."""
    base = rgb(p.get("color", "#9f998e"))
    col = g.mottle(base, 0.12, 0.8)
    n = g.noise(g.vo(g.W, 5.5), 3.5, 7, 0.65)
    col = g.hsv(col, 0.5, 1.0, g.lin(n, 0.3, 0.7, 0.8, 1.12))
    stain = g.smooth(g.noise(g.vo(g.W, 9.1), 1.4, 6, 0.6), 0.55, 0.75)
    col = g.mixc(g.mul(stain, 0.5), col, g.mulc(col, (0.72, 0.66, 0.58)))
    bh = p.get("board", 0.15)
    height = g.mul(g.noise(g.W, 40, 4, 0.6), 0.25)
    if bh:
        axis = p.get("board_axis", "z")
        coord = {"x": g.Wx, "y": g.Wy, "z": g.Wz}[axis]
        t = g.div(coord, bh)
        idx = g.floor(t)
        tone = g.white(g.comb(idx, 3.0, 7.0))
        col = g.hsv(col, 0.5, 1.0, g.lin(tone, 0, 1, 0.93, 1.06))
        f = g.fract(t)
        seam = g.smooth(g.absv(g.sub(f, 0.5)), 0.46, 0.495)
        col = g.mixc(g.mul(seam, 0.35), col, g.mulc(col, 0.7))
        gx, gy, gz = g.sep(g.W)
        imprint = g.noise(g.comb(g.mul(gx, 0.7), g.mul(gy, 0.7), g.mul(coord, 55.0)), 1.0, 3, 0.5)
        height = g.sum((height, 1.0), (seam, 0.9), (imprint, 0.35))
    agg = g.smooth(g.noise(g.W, 160.0, 2, 0.5), 0.6, 0.75)
    col = g.mixc(g.mul(agg, 0.25), col, g.mulc(col, 0.75))
    pores = g.smooth(g.vor(g.W, 90.0), 0.22, 0.1)
    pores = g.mul(pores, g.smooth(g.noise(g.W, 3.0, 3, 0.5), 0.35, 0.7))
    col = g.mixc(g.mul(pores, 0.75), col, g.mulc(col, 0.42))
    height = g.sub(height, g.mul(pores, 0.9))
    # broken / chipped arrises
    ch = g.mul(g.convex(), g.smooth(g.noise(g.W, 18, 6, 0.65), 0.45, 0.6))
    ch = g.mul(ch, p.get("chips", 0.6))
    col = g.mixc(ch, col, g.hsv(col, 0.5, 0.9, 1.12)); height = g.sub(height, g.mul(ch, 2.0))
    sh = p.get("silt_h")
    rough = g.lin(n, 0.3, 0.7, 0.86, 0.96)
    if sh:
        below = g.smooth(g.Wz, sh + 0.04, sh - 0.06)
        line = g.mul(g.smooth(g.absv(g.sub(g.Wz, sh)), 0.05, 0.0), 0.6)
        col = g.mixc(g.mul(below, 0.55), col, g.mulc(col, (0.78, 0.68, 0.55)))
        col = g.mixc(line, col, g.mulc(col, (0.55, 0.48, 0.40)))
    ef = p.get("efflor", 0.4)
    if ef > 0:
        e = g.smooth(g.noise(g.vs(g.W, (6.0, 6.0, 0.6)), 1.0, 4, 0.55), 0.62, 0.76)
        e = g.mul(g.mul(e, g.vert), ef)
        col = g.mixc(g.mul(e, 0.5), col, rgb("#d9d6cd"))
    col, rough, _ = g.weather(col, rough, None, dict(p, streaks=p.get("streaks", 0.45)))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def r_burlap(g, p):
    """Woven jute sacking (sandbags)."""
    x, y, z = g.sep(g.P)
    f = p.get("weave", 1000.0)
    jit = g.mul(g.noise(g.vs(g.P, (3, 3, 3)), 4.0, 3, 0.5), 9.0)
    wa = g.sin(g.add(g.mul(x, f), jit)); wb = g.sin(g.add(g.mul(y, f), jit))
    wz = g.sin(g.add(g.mul(z, f), jit))
    weave = g.mul(g.add(g.mul(wa, wb), g.mul(wb, wz)), 0.5)
    weave = g.add(g.mul(weave, 0.5), 0.5)
    fib = g.noise(g.vs(g.P, (3.0, 3.0, 3.0)), 25.0, 6, 0.7)
    col = g.mixc(g.clamp(g.add(g.mul(weave, 0.45), g.mul(fib, 0.4))), rgb(p.get("dark", "#5d4b33")), rgb(p.get("color", "#9a8460")))
    col = g.jitter(col, 1.4)
    col = g.mottle(col, 0.16, 1.5)
    rough = 0.97
    height = g.add(g.mul(weave, 0.6), g.mul(fib, 0.2))
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=p.get("dust", 0.6), streaks=0.2, splash=p.get("splash", 0.8)))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def r_wax(g, p):
    """Cheese wax: satin, smudged and scuffed, with drips and a little dust."""
    base = g.mottle(rgb(p.get("color", "#8e0f12")), 0.14, 2.0)
    smudge = g.noise(g.vo(g.P, 6.6), 5.0, 5, 0.6)
    rough = g.lin(smudge, 0.3, 0.7, 0.30, 0.42)
    drips = g.noise(g.vs(g.W, (14.0, 14.0, 1.6)), 1.0, 3, 0.55)
    dm = g.mul(g.smooth(drips, 0.58, 0.68), g.vert)
    bub = g.smooth(g.vor(g.P, 90.0), 0.12, 0.04)
    col = g.mixc(g.mul(dm, 0.35), base, g.hsv(base, 0.5, 1.1, 0.75))
    sc = g.scratches(p.get("scratch", 0.7))
    col = g.mixc(g.mul(sc, 0.35), col, g.hsv(col, 0.5, 0.8, 1.35))
    rough = g.mixf(sc, rough, 0.6)
    col = g.mixc(g.mul(g.cav(), 0.25), col, g.mulc(col, 0.6))
    height = g.sum((dm, 0.9), (bub, -0.25), (smudge, 0.12), (sc, -0.15))
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=p.get("dust", 0.2), streaks=0.0, splash=p.get("splash", 0.15), grime=0.3))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def _holes(g, scale, size):
    """eyes: round holes in cheese -> (mask, depth_mm)"""
    P = g.vo(g.P, 2.7)
    v = g.vor(P, scale, out="Distance")
    c = g.sep(g.vor(P, scale, out="Color"))[0]
    r = g.mul(g.lin(c, 0, 1, 0.25, 1.0), size)
    r = g.mul(r, g.smooth(c, 0.35, 0.45))        # only some cells have a hole
    m = g.smooth(g.sub(v, r), 0.02, -0.01)
    q = g.clamp(g.div(v, g.mx(r, 0.001)))
    depth = g.mul(g.pw(g.clamp(g.sub(1.0, g.mul(q, q))), 0.5), g.mul(r, 1000.0 / scale))   # hemisphere, mm
    return m, g.mul(depth, m)


def r_cheddar(g, p):
    """Cut cheddar paste: pale orange, eyes (holes), knife marks, slight sweat."""
    base = g.mottle(rgb(p.get("color", "#eaa04a")), 0.07, 3.0)
    m, d = _holes(g, p.get("hole_scale", 11.0), p.get("hole_size", 0.42))
    hole_col = g.hsv(base, 0.5, 1.12, 0.8)
    col = g.mixc(m, base, hole_col)
    x, y, z = g.sep(g.P)
    knife = g.wave(g.P, p.get("knife", 55.0), "X", dist=2.0, detail=2.0, profile="SAW")
    km = g.mul(g.smooth(knife, 0.8, 1.0), 0.6)
    crumb = g.noise(g.P, 120, 4, 0.6)
    rough = g.sum((g.lin(crumb, 0.3, 0.7, 0.5, 0.7), 1.0), (km, -0.15), (m, 0.15))
    height = g.sum((d, -1.0), (km, 0.25), (crumb, 0.15))
    col, rough, height = g.rim(col, rough, height, p)
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=0.1, streaks=0.0, splash=0.0, grime=0.25))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def r_bleu_paste(g, p):
    base = g.mottle(rgb(p.get("color", "#e8dfc3")), 0.05, 3.0)
    w = g.noise(g.P, 6.0, 8, 0.7, dist=0.8)
    vein = g.smooth(g.absv(g.sub(w, 0.5)), 0.06, 0.015)
    vein = g.mul(vein, g.smooth(g.noise(g.vo(g.P, 4.2), 4.0, 3, 0.5), 0.35, 0.55))
    pock = g.smooth(g.add(g.noise(g.vo(g.P, 1.1), 14.0, 6, 0.75, dist=0.4), g.mul(g.noise(g.P, 4.0, 2, 0.5), 0.35)), 0.74, 0.82)
    vein = g.mx(vein, pock)
    vc = g.mixc(g.noise(g.P, 40.0, 3, 0.5), rgb("#33505a"), rgb("#5e7f84"))
    m, d = _holes(g, 22.0, 0.30)
    col = g.mixc(vein, base, vc)
    col = g.mixc(g.mul(m, 0.6), col, g.mulc(vc, 0.8))
    rough = g.lin(g.noise(g.P, 90, 3, 0.5), 0.3, 0.7, 0.62, 0.8)
    height = g.sum((d, -1.0), (vein, -0.3), (g.noise(g.P, 140, 4, 0.6), 0.2))
    col, rough, height = g.rim(col, rough, height, p)
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=0.08, streaks=0.0, splash=0.0, grime=0.25))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def r_bleu_rind(g, p):
    """Grey-blue bloomy rind: chalky grey, blue-grey mould patches, fine white bloom, a few brown spots."""
    base = g.mottle(rgb(p.get("color", "#a3a49c")), 0.10, 3.0)
    blue = g.smooth(g.noise(g.vo(g.P, 3.0), 5.0, 7, 0.68, dist=0.3), 0.47, 0.64)
    col = g.mixc(g.mul(blue, 0.8), base, g.mottle(rgb(p.get("blue", "#667b8b")), 0.15, 6.0))
    bloom = g.smooth(g.noise(g.P, 40.0, 6, 0.7), 0.52, 0.72)
    col = g.mixc(g.mul(bloom, 0.55), col, rgb("#dcdeda"))
    spots = g.smooth(g.vor(g.P, 60.0), 0.16, 0.07)
    spots = g.mul(spots, g.smooth(g.noise(g.vo(g.P, 4.0), 6, 3, 0.5), 0.5, 0.62))
    col = g.mixc(spots, col, rgb("#3e5260"))
    brown = g.mul(g.smooth(g.noise(g.vo(g.P, 7.7), 9.0, 5, 0.6), 0.62, 0.75), 0.6)
    col = g.mixc(brown, col, rgb("#8b7658"))
    fuzz = g.noise(g.P, 220, 3, 0.7)
    lump = g.noise(g.P, 12, 4, 0.6)
    rough = 0.96
    height = g.sum((bloom, 0.35), (fuzz, 0.3), (spots, -0.2), (lump, 0.8))
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=0.12, streaks=0.0, splash=0.0, grime=0.35))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def r_natural_rind(g, p):
    """Cloth-bound natural rind: tan-brown, cheesecloth imprint, darker mould spots."""
    base = g.mottle(rgb(p.get("color", "#b0813f")), 0.15, 2.5)
    x, y, z = g.sep(g.P)
    f = 420.0
    weave = g.add(g.mul(g.mul(g.sin(g.mul(x, f)), g.sin(g.mul(g.add(y, z), f))), 0.5), 0.5)
    spots = g.mul(g.smooth(g.noise(g.vo(g.P, 9.0), 14.0, 6, 0.65), 0.6, 0.72), 0.8)
    col = g.mixc(spots, base, rgb("#5b3e1d"))
    col = g.mixc(g.mul(weave, 0.25), col, g.mulc(col, 0.8))
    rough = 0.86
    height = g.sum((weave, 0.3), (spots, 0.25), (g.noise(g.P, 30, 6, 0.6), 0.35))
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=0.15, streaks=0.0, splash=0.0, grime=0.4))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def r_brass(g, p):
    base = rgb(p.get("color", "#b48a3c"))
    n = g.noise(g.P, 30, 4, 0.5)
    col = g.hsv(base, 0.5, 1.0, g.lin(n, 0.3, 0.7, 0.9, 1.1))
    tarn = g.mul(g.smooth(g.add(g.cav(), g.mul(g.noise(g.vo(g.P, 2.0), 12, 5, 0.6), 0.6)), 0.55, 0.9), p.get("tarnish", 0.6))
    col = g.mixc(tarn, col, rgb("#4e3d22"))
    rough = g.mixf(tarn, g.lin(n, 0.3, 0.7, 0.22, 0.34), 0.6)
    metal = g.mixf(tarn, 1.0, 0.6)
    col, rough, metal = g.weather(col, rough, metal, dict(p, dust=0.15, streaks=0.0, splash=0.0))
    return dict(color=col, rough=rough, metal=metal, height=g.mul(n, 0.05))


def r_chrome(g, p):
    base = rgb(p.get("color", "#d9d9d6"))
    spots = g.smooth(g.vor(g.P, 55.0), 0.16, 0.06)
    spots = g.mul(spots, g.smooth(g.noise(g.P, 6, 3, 0.5), 0.4, 0.6))
    col = g.mixc(g.mul(spots, 0.8), base, rgb("#6b5644"))
    rough = g.add(g.lin(g.noise(g.P, 20, 3, 0.5), 0.3, 0.7, 0.05, 0.14), g.mul(spots, 0.5))
    metal = g.mixf(spots, 1.0, 0.3)
    col, rough, metal = g.weather(col, rough, metal, dict(p, dust=p.get("dust", 0.3), streaks=0.15, grime=0.5))
    return dict(color=col, rough=rough, metal=metal, height=g.mul(spots, -0.2))


def r_rubber(g, p):
    base = rgb(p.get("color", "#1d1d1d"))
    n = g.noise(g.P, 25, 5, 0.6)
    col = g.hsv(base, 0.5, 1.0, g.lin(n, 0.3, 0.7, 0.85, 1.25))
    wear = g.mul(g.convex(), 0.5)
    col = g.mixc(wear, col, rgb("#3b3a38"))
    rough = g.lin(n, 0.3, 0.7, 0.72, 0.9)
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=p.get("dust", 0.5)))
    return dict(color=col, rough=rough, metal=0.0, height=g.mul(g.noise(g.P, 150, 3, 0.6), 0.2))


def r_glass(g, p):
    base = rgb(p.get("color", "#0f1416"))
    dirt = g.smooth(g.noise(g.W, 4, 6, 0.6), 0.45, 0.75)
    col = g.mixc(g.mul(dirt, 0.4), base, rgb("#6c6457"))
    rough = g.add(0.04, g.mul(dirt, 0.4))
    cr = p.get("cracks", 0.0)
    height = 0.0
    if cr:
        c = g.vor(g.P, 5.0, "DISTANCE_TO_EDGE")
        cm = g.mul(g.smooth(c, 0.012, 0.0), cr)
        col = g.mixc(cm, col, rgb("#d4d4cc")); rough = g.mixf(cm, rough, 0.5)
        height = g.mul(cm, -0.6)
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=p.get("dust", 0.5), streaks=0.3, grime=0.6))
    return dict(color=col, rough=rough, metal=0.0, height=height)


def r_milkglass(g, p):
    base = rgb(p.get("color", "#e6dfcf"))
    c = g.vor(g.vo(g.P, 1.5), p.get("crack_scale", 7.0), "DISTANCE_TO_EDGE")
    gate = g.smooth(g.noise(g.P, 2.0, 3, 0.5), 0.45 - 0.2 * p.get("cracks", 0.6), 0.6 - 0.2 * p.get("cracks", 0.6))
    cm = g.mul(g.smooth(c, 0.010, 0.0), g.mul(gate, g.smooth(g.noise(g.vo(g.P, 6.0), 3.0, 2, 0.5), 0.5, 0.62)))
    col = g.mixc(cm, g.mottle(base, 0.05), rgb("#5a554c"))
    rough = g.mixf(cm, 0.16, 0.6)
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=0.4, streaks=0.2, grime=0.5))
    return dict(color=col, rough=rough, metal=0.0, height=g.mul(cm, -0.8))


def r_cloth(g, p):
    """Canvas / banner cloth."""
    x, y, z = g.sep(g.P)
    f = p.get("weave", 600.0)
    weave = g.add(g.mul(g.mul(g.sin(g.mul(x, f)), g.sin(g.mul(g.add(y, z), f))), 0.5), 0.5)
    base = g.mottle(rgb(p.get("color", "#c8c6bf")), 0.08, 2.0)
    col = g.mixc(g.mul(weave, 0.15), base, g.mulc(base, 0.8))
    fade = p.get("fade", 0.3)
    col = g.mixc(g.mul(g.noise(g.W, 1.5, 3, 0.5), fade), col, g.hsv(col, 0.5, 0.7, 1.12))
    rough = 0.92
    col, rough, _ = g.weather(col, rough, None, dict(p, dust=p.get("dust", 0.3), streaks=p.get("streaks", 0.4), splash=0.2))
    return dict(color=col, rough=rough, metal=0.0, height=g.mul(weave, 0.25))


def r_team_cloth(g, p):
    q = dict(color="#cbcbc7", fade=0.15, dust=0.2, streaks=0.3)
    q.update(p)
    return r_cloth(g, q)


def r_plastic(g, p):
    base = g.jitter(g.mottle(rgb(p.get("color", "#2a2a2a")), 0.06, 2.0), 0.6)
    s = g.scratches(0.6)
    col = g.mixc(g.mul(s, 0.3), base, g.hsv(base, 0.5, 0.6, 1.4))
    rough = g.add(p.get("rough", 0.45), g.mul(s, 0.2))
    col, rough, _ = g.weather(col, rough, None, p)
    return dict(color=col, rough=rough, metal=0.0, height=g.mul(s, -0.08))


def r_glow(g, p):
    """Emitter strip (Glow slot): frosted diffuser, slightly dirty.  The engine drives the emission."""
    base = rgb(p.get("color", "#eef0ee"))
    col = g.mixc(g.mul(g.smooth(g.noise(g.W, 6, 4, 0.5), 0.5, 0.8), 0.3), base, rgb("#b9b5a8"))
    rough = 0.3
    return dict(color=col, rough=rough, metal=0.0, height=g.mul(g.noise(g.P, 200, 2, 0.5), 0.03))


def r_iron(g, p):
    """Cast / wrought iron: pitted, black-brown, rust bloom (hitching posts, valve wheels, trough rivets)."""
    q = dict(color="#2f2e2c", rough=0.62, worn=0.5, rust=0.55)
    q.update(p)
    out = r_steel(g, q)
    out["height"] = g.add(out["height"], g.mul(g.smooth(g.vor(g.P, 40.0), 0.25, 0.05), -0.35))
    return out


def r_emissive_bulb(g, p):
    base = rgb(p.get("color", "#f3e2b0"))
    return dict(color=g.mottle(base, 0.05, 4.0), rough=0.12, metal=0.0, height=0.0)


def r_flat(g, p):
    """Plain colour with roughness/metal -- for hidden faces or debug."""
    return dict(color=g.const_c(p.get("color", "#808080")), rough=p.get("rough", 0.8), metal=p.get("metal", 0.0), height=0.0)


def r_debug_mask(g, p):
    e, c, a = g.masks()
    cc = g.node("ShaderNodeCombineColor")
    g._set(cc.inputs[0], e); g._set(cc.inputs[1], c); g._set(cc.inputs[2], a)
    return dict(color=cc.outputs[0], rough=0.9, metal=0.0, height=0.0)


RECIPES = {"debug_mask": r_debug_mask, 
    "paint": r_paint, "team": r_team, "rust": r_rust, "galv": r_galv, "steel": r_steel,
    "diamond": r_diamond, "wood": r_wood, "concrete": r_concrete, "burlap": r_burlap,
    "wax": r_wax, "cheddar": r_cheddar, "bleu_paste": r_bleu_paste, "bleu_rind": r_bleu_rind,
    "natural_rind": r_natural_rind, "brass": r_brass, "chrome": r_chrome, "rubber": r_rubber,
    "glass": r_glass, "milkglass": r_milkglass, "cloth": r_cloth, "team_cloth": r_team_cloth,
    "plastic": r_plastic, "glow": r_glow, "iron": r_iron, "bulb": r_emissive_bulb, "flat": r_flat,
}

# which export slot each recipe lands in
SLOT = {"team": "TeamPaint", "team_cloth": "TeamPaint", "glow": "Glow"}
