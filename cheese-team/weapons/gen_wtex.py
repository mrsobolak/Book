# Printed / painted graphics for the weapons: stickers (die-cut), skull sticker, camo tape, the Mechanic's blueprint.
# All names and logos are invented for CheeseTeam.
import os, math, random
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
os.makedirs(OUT, exist_ok=True)
FD = '/usr/share/fonts/truetype/dejavu/'


def font(name, size):
    return ImageFont.truetype(FD + name, size)


B = lambda s: font('DejaVuSans-Bold.ttf', s)
C = lambda s: font('DejaVuSansCondensed-Bold.ttf', s)
M = lambda s: font('DejaVuSansMono.ttf', s)
MB = lambda s: font('DejaVuSansMono-Bold.ttf', s)


def ctext(d, xy, txt, f, fill, anchor='mm', **kw):
    d.text(xy, txt, font=f, fill=fill, anchor=anchor, **kw)


def wear(im, seed, amount=1.0, edge=True):
    """scuffs, light scratches, dirt + darker grimy edge -- stickers that have been knocked around"""
    rng = np.random.RandomState(seed)
    a = np.asarray(im.convert('RGB')).astype(float)
    H, W = a.shape[:2]
    # dirt mottling
    n = Image.fromarray((rng.rand(H // 16, W // 16) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)
    n = np.asarray(n.filter(ImageFilter.GaussianBlur(6))) / 255.0
    a *= (0.88 + 0.12 * n)[..., None]
    # scratches: thin pale lines
    sc = Image.new('L', (W, H), 0); d = ImageDraw.Draw(sc)
    for _ in range(int(40 * amount)):
        x0, y0 = rng.rand() * W, rng.rand() * H
        ang = rng.rand() * math.pi; L = rng.rand() * W * 0.25 + 10
        d.line((x0, y0, x0 + math.cos(ang) * L, y0 + math.sin(ang) * L), fill=int(120 + rng.rand() * 135), width=1 + int(rng.rand() * 2))
    for _ in range(int(6 * amount)):                         # scraped patches
        x0, y0 = rng.rand() * W, rng.rand() * H; r = rng.rand() * W * 0.05 + 4
        d.ellipse((x0 - r, y0 - r * 0.4, x0 + r, y0 + r * 0.4), fill=200)
    s = np.asarray(sc.filter(ImageFilter.GaussianBlur(0.7))) / 255.0
    a = a * (1 - 0.55 * s[..., None]) + 235 * 0.55 * s[..., None]
    if edge:
        yy, xx = np.mgrid[0:H, 0:W]
        e = np.minimum(np.minimum(xx, W - 1 - xx), np.minimum(yy, H - 1 - yy)) / (0.06 * min(W, H))
        a *= (0.75 + 0.25 * np.clip(e, 0, 1))[..., None]
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8))


def circle_sticker(name, draw_fn, bg, border=(240, 236, 226), S=512, seed=1):
    im = Image.new('RGB', (S, S), border); d = ImageDraw.Draw(im)
    d.ellipse((14, 14, S - 14, S - 14), fill=bg)
    draw_fn(d, S)
    wear(im, seed).save(os.path.join(OUT, name + '.png'))


def rect_sticker(name, draw_fn, bg, size=(1024, 512), border=(240, 236, 226), seed=1, r=40):
    W, H = size
    im = Image.new('RGB', size, border); d = ImageDraw.Draw(im)
    d.rounded_rectangle((14, 14, W - 14, H - 14), radius=r, fill=bg)
    draw_fn(d, W, H)
    wear(im, seed).save(os.path.join(OUT, name + '.png'))


def skull(d, cx, cy, s, fill, eye):
    """simple skull: dome + jaw + eye sockets + nose + teeth"""
    d.ellipse((cx - s, cy - s * 1.05, cx + s, cy + s * 0.75), fill=fill)
    d.rounded_rectangle((cx - s * 0.55, cy + s * 0.3, cx + s * 0.55, cy + s * 1.05), radius=int(s * 0.18), fill=fill)
    for sx in (-1, 1):
        d.ellipse((cx + sx * s * 0.42 - s * 0.27, cy - s * 0.2, cx + sx * s * 0.42 + s * 0.27, cy + s * 0.3), fill=eye)
    d.polygon([(cx, cy + s * 0.32), (cx - s * 0.12, cy + s * 0.55), (cx + s * 0.12, cy + s * 0.55)], fill=eye)
    for k in range(-2, 3):
        d.line((cx + k * s * 0.17, cy + s * 0.72, cx + k * s * 0.17, cy + s * 1.02), fill=eye, width=max(2, int(s * 0.05)))


def stickers():
    # 1. motorcycle club round: winged wheel
    def choppers(d, S):
        c = S / 2
        d.ellipse((40, 40, S - 40, S - 40), outline=(232, 140, 30), width=14)
        for sx in (-1, 1):                                      # wings
            for k in range(5):
                y = c - 40 + k * 22
                d.polygon([(c + sx * 60, y), (c + sx * (190 - k * 22), y - 26 + k * 4), (c + sx * (175 - k * 22), y + 10)], fill=(240, 236, 226))
        d.ellipse((c - 62, c - 62, c + 62, c + 62), outline=(240, 236, 226), width=12)
        for k in range(8):
            a = k * math.pi / 4
            d.line((c, c, c + math.cos(a) * 56, c + math.sin(a) * 56), fill=(240, 236, 226), width=6)
        ctext(d, (c, 112), 'CHEDDAR', B(44), (232, 140, 30))
        ctext(d, (c, S - 114), 'CHOPPERS M.C.', B(32), (232, 140, 30))
    circle_sticker('st_choppers', choppers, (22, 20, 20), seed=11)

    def brie(d, W, H):
        d.rectangle((40, 40, W - 40, H - 40), outline=(240, 236, 226), width=8)
        skull(d, 190, H / 2 - 10, 110, (240, 236, 226), (176, 28, 30))
        ctext(d, (630, 190), 'BRIE', C(150), (240, 236, 226))
        ctext(d, (630, 345), 'OR DIE', C(130), (255, 214, 64))
    rect_sticker('st_brie', brie, (176, 28, 30), seed=12)

    def gouda(d, W, H):
        ctext(d, (W / 2, 190), 'GOUDA ROCK', C(118), (255, 214, 64))
        d.polygon([(470, 255), (560, 255), (520, 320), (590, 320), (440, 470), (490, 350), (430, 350)], fill=(255, 214, 64))
        ctext(d, (W / 2 - 230, 400), 'WORLD', B(60), (210, 120, 255))
        ctext(d, (W / 2 + 230, 400), "TOUR '84", B(60), (210, 120, 255))
    rect_sticker('st_gouda', gouda, (18, 14, 26), seed=13)

    def throttle(d, W, H):
        sq = 48
        for i in range(0, 6):
            for j in range(0, 8):
                if (i + j) % 2 == 0:
                    d.rectangle((40 + i * sq, 64 + j * sq * 0.94, 40 + (i + 1) * sq, 64 + (j + 1) * sq * 0.94), fill=(20, 20, 20))
        ctext(d, (665, 195), 'FULL', C(140), (20, 20, 20))
        ctext(d, (665, 345), 'THROTTLE', C(96), (210, 30, 30))
    rect_sticker('st_throttle', throttle, (238, 234, 222), seed=14, border=(20, 20, 20))

    def flames(d, W, H):
        rng = random.Random(3)
        for k in range(14):                                     # flame tongues from the left
            y = 70 + k * 28
            L = 380 + rng.random() * 260
            col = [(255, 210, 40), (250, 140, 20), (220, 50, 20)][k % 3]
            d.polygon([(30, y - 22), (30 + L * 0.6, y - 30), (30 + L, y - 4), (30 + L * 0.55, y + 20), (30, y + 24)], fill=col)
        ctext(d, (W - 330, H / 2), 'LOUD PIPES', C(92), (240, 236, 226), stroke_width=6, stroke_fill=(20, 20, 20))
    rect_sticker('st_flames', flames, (20, 20, 22), size=(1024, 512), seed=15)

    def eightyeight(d, S):
        c = S / 2
        d.ellipse((60, 60, S - 60, S - 60), fill=(240, 236, 226))
        ctext(d, (c, c + 10), '88', C(260), (200, 30, 30))
    circle_sticker('st_88', eightyeight, (200, 30, 30), seed=16)

    def skullst(d, S):
        c = S / 2
        skull(d, c, c - 10, 150, (240, 236, 226), (18, 18, 18))
        for sx in (-1, 1):                                      # crossbones
            d.line((c - 190, c + 150 * sx * -1 + 20, c + 190, c - 150 * sx * -1 + 20), fill=(240, 236, 226), width=34)
        skull(d, c, c - 10, 150, (240, 236, 226), (18, 18, 18))
    circle_sticker('st_skull', skullst, (18, 18, 18), seed=17)


def stencil_backblast():
    W, H = 1024, 256
    im = Image.new('RGBA', (W, H), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ctext(d, (W / 2, H / 2), 'DANGER  BACKBLAST  AREA', C(92), (230, 230, 220, 235))
    a = np.asarray(im).astype(float)
    rng = np.random.RandomState(9)
    n = np.asarray(Image.fromarray((rng.rand(H // 4, W // 4) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    a[..., 3] *= np.clip((n - 0.25) * 2.2, 0, 1)                 # worn spray paint
    Image.fromarray(a.astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'stencil_backblast.png'))


def camo_tape():
    S = 1024
    rng = np.random.RandomState(4)
    cols = [(92, 98, 58), (58, 64, 36), (110, 84, 52), (36, 32, 24), (140, 128, 92)]
    a = np.zeros((S, S, 3)); a[:] = cols[0]
    yy, xx = np.mgrid[0:S, 0:S].astype(float)
    for layer, col in enumerate(cols[1:]):
        f = np.zeros((S, S))
        for _ in range(26):
            cx, cy = rng.rand() * S, rng.rand() * S
            rx, ry = 40 + rng.rand() * 130, 20 + rng.rand() * 60
            ang = rng.rand() * math.pi
            for ox in (-S, 0, S):
                for oy in (-S, 0, S):
                    dx = xx - cx - ox; dy = yy - cy - oy
                    u = dx * math.cos(ang) + dy * math.sin(ang); v = -dx * math.sin(ang) + dy * math.cos(ang)
                    f = np.maximum(f, 1 - (u / rx) ** 2 - (v / ry) ** 2)
        nz = np.asarray(Image.fromarray((rng.rand(S // 32, S // 32) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC)) / 255.0
        m = (f + 0.35 * (nz - 0.5)) > 0.15 + 0.12 * layer
        a[m] = col
    # cloth tape weave + wear
    weave = (np.sin(xx * 1.6) * np.sin(yy * 1.6)) * 6
    a += weave[..., None]
    a *= (0.92 + 0.08 * rng.rand(S, S))[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(OUT, 'camo_tape.png'))


def blueprint():
    """the Mechanic's 'blueprint': it's just a drawing of cheese"""
    W, H = 1448, 2048
    bg = (22, 72, 150); ln = (225, 238, 255)
    im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im)
    for x in range(0, W, 40):
        d.line((x, 0, x, H), fill=(40, 92, 168), width=1)
    for y in range(0, H, 40):
        d.line((0, y, W, y), fill=(40, 92, 168), width=1)
    d.rectangle((50, 50, W - 50, H - 50), outline=ln, width=5)
    # one big cheese wedge, 3/4 view: thick back face on the left, sloping top down to the point on the right
    A = (250, 1000)      # back-bottom-left
    B = (250, 560)       # back-top-left
    Cp = (560, 420)      # back-top-right (depth)
    Dp = (560, 860)      # back-bottom-right (depth)
    T = (1230, 1290)     # tip bottom (front)
    Tb = (1260, 1150)    # tip bottom (depth)
    lw = 7
    d.polygon([A, B, T], outline=ln, width=lw)                      # front face (triangle)
    d.line((B[0], B[1], Cp[0], Cp[1]), fill=ln, width=lw)           # top back edge
    d.line((Cp[0], Cp[1], Tb[0], Tb[1]), fill=ln, width=lw)         # top far edge
    d.line((Tb[0], Tb[1], T[0], T[1]), fill=ln, width=lw)
    d.line((A[0], A[1], T[0], T[1]), fill=ln, width=lw)
    d.line((B[0], B[1], T[0], T[1]), fill=ln, width=lw)
    # holes on the front face (ellipses) + a few on the top
    for (cx, cy, rx, ry) in ((360, 860, 50, 46), (480, 930, 34, 30), (330, 700, 28, 26), (600, 1040, 42, 38), (760, 1120, 24, 22),
                             (430, 760, 20, 18), (880, 1200, 18, 16), (540, 820, 16, 14)):
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=ln, width=5)
        d.arc((cx - rx + 6, cy - ry + 6, cx + rx - 6, cy + ry - 6), 200, 330, fill=ln, width=2)
    for (cx, cy, rx, ry) in ((520, 560, 40, 18), (760, 760, 30, 13), (930, 930, 22, 10), (400, 520, 18, 8)):
        d.ellipse((cx - rx, cy - ry, cx + rx, cy + ry), outline=ln, width=4)
    # hole cut on the back edge
    d.arc((222, 620, 278, 690), 270, 90, fill=ln, width=5)
    # title
    ctext(d, (W / 2, 1560), 'CHEESE', C(170), ln)
    ctext(d, (W / 2, 1700), 'FIG. 1', M(44), ln)
    a = np.asarray(im).astype(float)
    rng = np.random.RandomState(7)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    n = np.asarray(Image.fromarray((rng.rand(H // 64, W // 64) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    a *= (0.86 + 0.18 * n)[..., None]
    for (cx, cy, r) in ((1150, 1820, 150), (300, 1650, 110), (1180, 380, 95)):
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        ring = np.exp(-((dist - r) / 5.0) ** 2) * (0.55 + 0.45 * np.sin(np.arctan2(yy - cy, xx - cx) * 3 + cx) ** 2)
        m = np.clip(ring + (dist < r) * 0.12, 0, 1)[..., None]
        a = a * (1 - m) + np.array([92, 64, 40]) * m
    for y in (H / 3, 2 * H / 3):
        a *= (1 - 0.18 * np.exp(-((yy - y) / 6) ** 2))[..., None]
    e = np.minimum(np.minimum(xx, W - xx), np.minimum(yy, H - yy)) / 60.0
    a *= (0.8 + 0.2 * np.clip(e, 0, 1))[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(OUT, 'blueprint.png'))


def star_paint():
    """gold sheriff star painted (stencil spray) -- RGBA, worn"""
    S = 1024
    im = Image.new('RGBA', (S, S), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    c = S / 2; R = 440
    pts = []
    for i in range(12):
        a = -math.pi / 2 + i * math.pi / 6
        r = R if i % 2 == 0 else R * 0.55
        pts.append((c + r * math.cos(a), c + r * math.sin(a)))
    d.polygon(pts, fill=(214, 168, 62, 255))
    for i in range(6):
        a = -math.pi / 2 + i * math.pi / 3
        x, y = c + R * math.cos(a), c + R * math.sin(a)
        d.ellipse((x - 46, y - 46, x + 46, y + 46), fill=(214, 168, 62, 255))
    d.ellipse((c - 150, c - 150, c + 150, c + 150), outline=(120, 82, 22, 255), width=18)
    a = np.asarray(im).astype(float)
    rng = np.random.RandomState(21)
    n = np.asarray(Image.fromarray((rng.rand(S // 8, S // 8) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC)) / 255.0
    a[..., 3] *= np.clip((n - 0.12) * 3.0, 0, 1)
    a[..., :3] *= (0.85 + 0.15 * n)[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'star_paint.png'))


if __name__ == '__main__':
    stickers(); stencil_backblast(); camo_tape(); blueprint(); star_paint()
    print(sorted(os.listdir(OUT)))
