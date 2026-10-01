"""Generate the TF2-style ("illustrative", hand-painted look) texture set for Whey Station.
Every texture is seamless; <id>_d.webp (colour) + <id>_n.webp (OpenGL normal from a height field).
    python3 tools/tf_textures.py   -> textures_tf/*.webp + textures_tf/texman.json"""
import numpy as np, json, os, math
from PIL import Image, ImageFilter, ImageDraw
OUT = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), 'textures_tf')
os.makedirs(OUT, exist_ok=True)
S = 1024
rng = np.random.default_rng(7)


def tnoise(cells, seed, size=S):
    """seamless value noise in [0,1] (bicubic upsampling of a wrapped random grid)"""
    r = np.random.default_rng(seed).random((cells, cells))
    big = np.tile(r, (3, 3))
    im = Image.fromarray((big * 255).astype(np.uint8)).resize((size * 3, size * 3), Image.BICUBIC)
    a = np.asarray(im, np.float32)[size:2 * size, size:2 * size] / 255.0
    return a


def fbm(seed, octaves=((4, .5), (8, .25), (16, .15), (64, .1))):
    a = sum(w * tnoise(c, seed + i) for i, (c, w) in enumerate(octaves))
    return a / sum(w for _, w in octaves)


def brush(seed, horizontal=True, amt=1.0):
    """painterly streaks: directional blur of noise"""
    n = tnoise(128, seed)
    im = Image.fromarray((n * 255).astype(np.uint8))
    k = 21
    big = Image.fromarray(np.tile(np.asarray(im), (3, 3)))
    big = big.filter(ImageFilter.BoxBlur(0)) if False else big
    arr = np.asarray(big, np.float32)
    # 1-D box blur along one axis (wrap-safe via tiling)
    ker = np.ones(k) / k
    if horizontal:
        arr = np.apply_along_axis(lambda r: np.convolve(r, ker, 'same'), 1, arr)
    else:
        arr = np.apply_along_axis(lambda r: np.convolve(r, ker, 'same'), 0, arr)
    return (arr[S:2 * S, S:2 * S] / 255.0 - 0.5) * amt


def col(h):
    h = h.lstrip('#'); return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], np.float32) / 255.0


def save(name, rgb, height, strength=2.0):
    rgb = np.clip(rgb, 0, 1)
    Image.fromarray((rgb * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(OUT, name + '_d.webp'), quality=88)
    h = height.astype(np.float32)
    gx = (np.roll(h, -1, 1) - np.roll(h, 1, 1)) * strength
    gy = (np.roll(h, -1, 0) - np.roll(h, 1, 0)) * strength
    n = np.dstack([-gx, gy, np.ones_like(h)])
    n /= np.linalg.norm(n, axis=2, keepdims=True)
    Image.fromarray(((n * 0.5 + 0.5) * 255 + 0.5).astype(np.uint8), 'RGB').save(os.path.join(OUT, name + '_n.webp'), quality=92)
    MAN[name] = {'avg': [round(float(v), 4) for v in rgb.reshape(-1, 3).mean(0)]}


def grid_mask(nx, ny, line_px, offset_rows=False, soft=1.5):
    """returns (mortar mask 0..1, block id map, local u/v in block) for an nx x ny grid of blocks"""
    yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
    bw, bh = S / nx, S / ny
    row = np.floor(yy / bh)
    xo = xx + (bw / 2) * (row % 2) * offset_rows
    colm = np.floor(xo / bw) % nx
    u = (xo % bw); v = (yy % bh)
    d = np.minimum(np.minimum(u, bw - u), np.minimum(v, bh - v))
    mortar = np.clip(1 - (d - line_px / 2) / soft, 0, 1)
    bid = (row * 131 + colm * 17) % 997
    return mortar, bid, u / bw, v / bh, d


def per_block(bid, seed, amt):
    r = np.random.default_rng(seed).random(1000)
    return (r[bid.astype(int)] - 0.5) * amt


MAN = {}
# 1) cream painted block wall (4 m tile: 4 x 8 blocks of 1.0 x 0.5 m)
mort, bid, u, v, d = grid_mask(4, 8, 7, offset_rows=True)
base = col('#d9d0bb')[None, None] * (1 + per_block(bid, 1, 0.07)[..., None])
paint = fbm(10) - 0.5
rgb = base * (1 + paint[..., None] * 0.10 + brush(11, True, 0.10)[..., None])
rgb = rgb * (1 - mort[..., None] * 0.22) + mort[..., None] * col('#a99f8b') * 0.0
edge = np.clip(1 - d / 10, 0, 1) * (1 - mort)
rgb = rgb * (1 - edge[..., None] * 0.05)
save('tf_wall_block', rgb, (1 - mort) * 1.0 + edge * -0.3 + paint * 0.05, 3.0)
# 2) lower wall paint band (muted green-grey, smooth with brush strokes)
rgb = col('#7d8274')[None, None] * (1 + (fbm(20) - 0.5)[..., None] * 0.12 + brush(21, True, 0.12)[..., None])
save('tf_wall_dado', rgb, fbm(22) * 0.2, 1.0)
# 3) dark concrete floor with panel seams every 2 m (4 m tile)
mort, bid, u, v, d = grid_mask(2, 2, 5)
rgb = col('#3f4042')[None, None] * (1 + (fbm(30) - 0.5)[..., None] * 0.22 + per_block(bid, 31, 0.06)[..., None])
sc = (tnoise(256, 32) > 0.985).astype(np.float32)
rgb = rgb * (1 - mort[..., None] * 0.35) + sc[..., None] * 0.03
save('tf_floor_dark', rgb, (1 - mort) + (fbm(33) - .5) * 0.2, 2.0)
# 4) white square tiles 0.25 m (2 m tile -> 8 x 8)
mort, bid, u, v, d = grid_mask(8, 8, 6)
rgb = col('#ebe8e0')[None, None] * (1 + per_block(bid, 41, 0.05)[..., None] + (fbm(42) - .5)[..., None] * 0.05)
rgb = rgb * (1 - mort[..., None]) + mort[..., None] * col('#8f8c86')
save('tf_tile_white', rgb, (1 - mort) * 1.0 - np.clip(1 - d / 6, 0, 1) * 0.2, 3.0)
# 5) team paint metal (greyscale; tinted per team) -- 1.2 m panels with seams + rivets + soft wear
mort, bid, u, v, d = grid_mask(2, 2, 4)
g = 0.62 * (1 + (fbm(50) - .5) * 0.14 + per_block(bid, 51, 0.05) + brush(52, False, 0.08))
yy, xx = np.mgrid[0:S, 0:S]
riv = np.zeros((S, S), np.float32)
for cx in np.arange(16, S, 64):
    for cy in (12, S // 2 - 12, S // 2 + 12, S - 12):
        riv += np.exp(-(((xx - cx) ** 2 + (yy - cy) ** 2) / 14.0))
wear = np.clip((fbm(53) - 0.62) * 6, 0, 1) * 0.35
g = g * (1 - mort * 0.3) + wear * 0.25 + riv * 0.12
save('tf_paint_metal', np.dstack([g, g, g]), (1 - mort) + riv * 0.6, 2.0)
# 6) dark painted steel (beams, trims, railings)
rgb = col('#4d5154')[None, None] * (1 + (fbm(60) - .5)[..., None] * 0.18 + brush(61, True, 0.15)[..., None])
save('tf_steel_dark', rgb, fbm(62) * 0.3, 1.0)
# 7) light concrete (ceilings, beams, plinths) with formwork lines every 1 m
mort, bid, u, v, d = grid_mask(1, 4, 3)
rgb = col('#a9a69d')[None, None] * (1 + (fbm(70) - .5)[..., None] * 0.16 + per_block(bid, 71, 0.04)[..., None])
rgb = rgb * (1 - mort[..., None] * 0.15)
save('tf_concrete', rgb, (1 - mort) * 0.6 + fbm(72) * 0.15, 1.5)
# 8) stylised brick (2 m tile: 8 x 24 bricks)
mort, bid, u, v, d = grid_mask(8, 24, 6, offset_rows=True)
rgb = col('#8e4f3a')[None, None] * (1 + per_block(bid, 81, 0.16)[..., None] + (fbm(82) - .5)[..., None] * 0.12)
rgb = rgb * (1 - mort[..., None]) + mort[..., None] * col('#a39a8a')
save('tf_brick', rgb, (1 - mort) - np.clip(1 - d / 8, 0, 1) * 0.25, 3.0)
# 9) roll shutter slats (2 m tile, 0.1 m slats)
yy = np.mgrid[0:S, 0:S][0].astype(np.float32)
ph = (yy % (S / 20)) / (S / 20)
prof = np.sin(ph * math.pi)
g = 0.5 + 0.18 * prof + (fbm(90) - .5) * 0.1
save('tf_shutter', np.dstack([g, g * 1.01, g * 1.03]), prof, 3.0)
# 10) floor grating (0.5 m tile, 10 x 10 holes)
mort, bid, u, v, d = grid_mask(10, 10, 22, soft=2)
g = 0.16 + mort * 0.18 + (fbm(100) - .5) * 0.05
save('tf_grate', np.dstack([g, g, g * 1.05]), mort, 4.0)
# 11) painted crate wood (vertical planks 0.15 m on a 1.2 m tile)
mort, bid, u, v, d = grid_mask(8, 1, 6)
grain = brush(111, False, 0.6) + (tnoise(32, 112) - .5) * 0.1
rgb = col('#ad8a56')[None, None] * (1 + per_block(bid, 113, 0.1)[..., None] + grain[..., None] * 0.35)
rgb = rgb * (1 - mort[..., None] * 0.55)
save('tf_wood', rgb, (1 - mort) + grain * 0.2, 2.0)
# 12) corrugated metal (greyscale for team tint), vertical ribs every 0.25 m on 2 m tile
xx = np.mgrid[0:S, 0:S][1].astype(np.float32)
ph = (xx % (S / 8)) / (S / 8)
prof = np.clip(np.abs(ph - 0.5) * 4 - 0.5, 0, 1)
g = 0.55 + 0.12 * prof + (fbm(120) - .5) * 0.12 + brush(121, False, 0.08)
save('tf_corr', np.dstack([g, g, g]), prof, 3.0)
# 13) hazard stripes (yellow / near black, 45 deg, 0.5 m tile)
yy, xx = np.mgrid[0:S, 0:S].astype(np.float32)
st = ((xx + yy) % (S / 2)) < (S / 4)
rgb = np.where(st[..., None], col('#e0b52c'), col('#2a2a2a'))[...] * (1 + (fbm(130) - .5)[..., None] * 0.1)
save('tf_hazard', rgb, st.astype(np.float32) * 0.2, 1.0)
# 14) machine paint (teal-grey, Turbine-like industrial machinery colour, smooth with soft gradients)
rgb = col('#7d989b')[None, None] * (1 + (fbm(140) - .5)[..., None] * 0.14 + brush(141, False, 0.1)[..., None])
save('tf_machine', rgb, fbm(142) * 0.2, 1.0)
# 15) ceiling panels (light, 2 m tile with recessed seams)
mort, bid, u, v, d = grid_mask(2, 2, 8)
rgb = col('#c9c5ba')[None, None] * (1 + (fbm(150) - .5)[..., None] * 0.1) * (1 - mort[..., None] * 0.3)
save('tf_ceiling', rgb, 1 - mort, 2.0)
# 16) team emblems (greyscale panel + white cheese-wedge emblem in a ring; tinted by team colour)
im = Image.new('RGB', (S, S), (150, 150, 150)); dr = ImageDraw.Draw(im)
dr.ellipse((112, 112, 912, 912), fill=(235, 235, 230)); dr.ellipse((172, 172, 852, 852), fill=(150, 150, 150))
dr.polygon([(300, 640), (740, 640), (740, 380)], fill=(235, 235, 230))
for (cx, cy, r) in ((640, 560, 40), (560, 600, 22), (690, 470, 26)):
    dr.ellipse((cx - r, cy - r, cx + r, cy + r), fill=(150, 150, 150))
a = np.asarray(im, np.float32) / 255.0
a = a * (1 + (fbm(160) - .5)[..., None] * 0.08)
save('tf_emblem', a, a[..., 0] * 0.3, 1.0)
# 17) direction sign (white arrow on dark panel)
im = Image.new('RGB', (S, S), (52, 54, 56)); dr = ImageDraw.Draw(im)
dr.rectangle((40, 40, S - 40, S - 40), outline=(220, 218, 210), width=24)
dr.polygon([(220, 430), (600, 430), (600, 280), (840, 512), (600, 744), (600, 594), (220, 594)], fill=(225, 222, 214))
a = np.asarray(im, np.float32) / 255.0 * (1 + (fbm(170) - .5)[..., None] * 0.06)
save('tf_sign_arrow', a, a[..., 0] * 0.2, 1.0)
json.dump(MAN, open(os.path.join(OUT, 'texman.json'), 'w'), separators=(',', ':'))
print(len(MAN), 'textures ->', OUT)
