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
    W, H = 1448, 2048
    bg = (22, 72, 150); ln = (225, 238, 255)
    im = Image.new('RGB', (W, H), bg); d = ImageDraw.Draw(im)
    for x in range(0, W, 40):
        d.line((x, 0, x, H), fill=(40, 92, 168), width=1)
    for y in range(0, H, 40):
        d.line((0, y, W, y), fill=(40, 92, 168), width=1)
    d.rectangle((50, 50, W - 50, H - 50), outline=ln, width=5)
    # ---- title block
    d.rectangle((W - 650, H - 330, W - 50, H - 50), outline=ln, width=4)
    for y in (H - 260, H - 190, H - 120):
        d.line((W - 650, y, W - 50, y), fill=ln, width=2)
    d.line((W - 350, H - 190, W - 350, H - 50), fill=ln, width=2)
    ctext(d, (W - 350, H - 295), 'CHEESE TURRET MK.II', C(46), ln)
    ctext(d, (W - 350, H - 225), '+ HELPER BOT "GOUDA BOY"', C(34), ln)
    d.text((W - 640, H - 180), 'DRAWN: MECHANIC', font=M(26), fill=ln)
    d.text((W - 340, H - 180), 'SCALE 1:BRIE', font=M(26), fill=ln)
    d.text((W - 640, H - 110), 'MATERIAL: CHEESE', font=M(26), fill=ln)
    d.text((W - 340, H - 110), 'SHEET 1 OF 3', font=M(26), fill=ln)

    def dim(x0, y0, x1, y1, txt, off=30, vertical=False):
        if vertical:
            d.line((x0 + off, y0, x0 + off, y1), fill=ln, width=2)
            for y in (y0, y1):
                d.line((x0 + 6, y, x0 + off + 14, y), fill=ln, width=2)
                d.polygon([(x0 + off, y), (x0 + off - 7, y + (12 if y == y0 else -12)), (x0 + off + 7, y + (12 if y == y0 else -12))], fill=ln)
            d.text((x0 + off + 10, (y0 + y1) / 2 - 12), txt, font=M(24), fill=ln)
        else:
            d.line((x0, y0 + off, x1, y0 + off), fill=ln, width=2)
            for x in (x0, x1):
                d.line((x, y0 + 6, x, y0 + off + 14), fill=ln, width=2)
                d.polygon([(x, y0 + off), (x + (12 if x == x0 else -12), y0 + off - 7), (x + (12 if x == x0 else -12), y0 + off + 7)], fill=ln)
            ctext(d, ((x0 + x1) / 2, y0 + off - 18), txt, M(24), ln)

    def wedge(x, y, w_, h_, holes=(), lw=5, flip=False):
        """cheese wedge in side view: thick end left (or right if flip), sloping top, holes"""
        if flip:
            pts = [(x, y + h_), (x + w_, y + h_), (x + w_, y)]
        else:
            pts = [(x, y), (x, y + h_), (x + w_, y + h_)]
        d.polygon(pts, outline=ln, width=lw)
        for (hx, hy, r) in holes:
            d.ellipse((x + hx - r, y + hy - r, x + hx + r, y + hy + r), outline=ln, width=max(2, lw - 2))

    def block(x, y, w_, h_, holes=(), lw=5, r=10):
        d.rounded_rectangle((x, y, x + w_, y + h_), radius=r, outline=ln, width=lw)
        for (hx, hy, rr) in holes:
            d.ellipse((x + hx - rr, y + hy - rr, x + hx + rr, y + hy + rr), outline=ln, width=max(2, lw - 2))

    # ---- turret: side elevation -- a cheese wedge on a breadstick tripod, firing cheese sticks
    ox, oy = 140, 260
    d.text((ox, oy - 90), 'A  SIDE ELEVATION', font=C(40), fill=ln)
    base_y = oy + 620
    for x1 in (ox + 60, ox + 470, ox + 260):
        d.line((ox + 260, oy + 380, x1, base_y), fill=ln, width=7)          # breadstick legs
        for k in range(1, 6):                                                # breadstick scoring
            t = k / 6
            xa = ox + 260 + (x1 - ox - 260) * t; ya = oy + 380 + (base_y - oy - 380) * t
            d.line((xa - 6, ya - 3, xa + 6, ya + 3), fill=ln, width=2)
    for x in (ox + 60, ox + 470):
        d.ellipse((x - 26, base_y - 14, x + 26, base_y + 10), outline=ln, width=3)   # cracker feet
        for k in (-1, 0, 1):
            d.ellipse((x + k * 10 - 2, base_y - 4, x + k * 10 + 2, base_y), fill=ln)
    block(ox + 225, oy + 290, 70, 100, holes=((20, 30, 8), (48, 70, 10)), lw=4, r=6)         # cheese-cube pivot
    wedge(ox + 110, oy + 120, 320, 175, holes=((70, 130, 22), (150, 150, 14), (210, 160, 10), (60, 75, 12)))   # body
    for yb in (oy + 215, oy + 262):                                                     # cheese-stick barrels
        xs = ox + 110 + 320 * (yb - oy - 120) / 175 - 4                                 # start at the wedge's slope
        d.rounded_rectangle((xs, yb - 12, ox + 740, yb + 12), radius=12, outline=ln, width=4)
        for k in range(7):
            d.ellipse((ox + 470 + k * 38, yb - 4, ox + 476 + k * 38, yb + 2), outline=ln, width=2)
    block(ox + 20, oy + 190, 90, 90, holes=((25, 30, 10), (60, 60, 14)), lw=4)          # ammo: cheese cube box
    d.text((ox + 24, oy + 290), 'CUBES', font=M(22), fill=ln)
    d.arc((ox + 90, oy + 120, ox + 230, oy + 220), 200, 330, fill=ln, width=3)
    d.ellipse((ox + 300, oy + 60, ox + 380, oy + 120), outline=ln, width=3)              # sensor: an olive
    d.ellipse((ox + 330, oy + 80, ox + 350, oy + 100), outline=ln, width=3)
    d.line((ox + 340, oy + 120, ox + 340, oy + 150), fill=ln, width=3)
    dim(ox + 20, oy + 640, ox + 740, oy + 640, '1 WHEEL', off=60)
    dim(ox + 760, oy + 120, ox + 760, base_y, '3 WEDGES', off=30, vertical=True)
    # ---- plan: a cheese wheel seen from above, one wedge missing
    tx, ty = 1060, 470
    d.text((tx - 80, ty - 330), 'B  PLAN', font=C(40), fill=ln)
    d.ellipse((tx - 150, ty - 150, tx + 150, ty + 150), outline=ln, width=5)
    d.ellipse((tx - 120, ty - 120, tx + 120, ty + 120), outline=ln, width=2)            # rind
    d.pieslice((tx - 150, ty - 150, tx + 150, ty + 150), -70, -20, fill=bg, outline=ln, width=5)
    for (hx, hy, r) in ((-60, -30, 18), (40, 50, 22), (-30, 70, 12), (70, -10, 10), (-80, 40, 9), (10, -80, 14)):
        d.ellipse((tx + hx - r, ty + hy - r, tx + hx + r, ty + hy + r), outline=ln, width=3)
    d.text((tx + 40, ty - 205), 'MISSING: 1/8', font=M(24), fill=ln)
    d.text((tx + 40, ty - 178), '(I ATE IT)', font=M(24), fill=ln)
    # ---- helper bot: a stack of cheese
    rx, ry = 160, 1150
    d.text((rx, ry - 70), 'C  HELPER BOT', font=C(40), fill=ln)
    block(rx + 120, ry + 140, 240, 240, holes=((50, 60, 20), (170, 90, 26), (90, 170, 16), (190, 200, 12)), r=20)   # body: cheese block
    wedge(rx + 150, ry + 10, 180, 120, holes=((60, 85, 12),), flip=False)                 # head: wedge
    for ex in (rx + 205, rx + 260):
        d.ellipse((ex - 14, ry + 75, ex + 14, ry + 103), outline=ln, width=4)            # googly eyes
        d.ellipse((ex - 4, ry + 87, ex + 4, ry + 95), fill=ln)
    d.line((rx + 165, ry + 10, rx + 165, ry - 18), fill=ln, width=3)
    d.ellipse((rx + 155, ry - 38, rx + 175, ry - 18), outline=ln, width=3)
    for sx, x0 in ((-1, rx + 120), (1, rx + 360)):                                         # string-cheese arms
        d.line((x0, ry + 190, x0 + sx * 90, ry + 260), fill=ln, width=7)
        d.line((x0 + sx * 90, ry + 260, x0 + sx * 110, ry + 330), fill=ln, width=7)
        d.polygon([(x0 + sx * 110, ry + 330), (x0 + sx * 140, ry + 370), (x0 + sx * 90, ry + 375)], outline=ln, width=3)
    for k in range(6):                                                                     # treads: cheese wheels
        cx_ = rx + 130 + k * 46
        d.ellipse((cx_ - 21, ry + 400, cx_ + 21, ry + 442), outline=ln, width=3)
        d.ellipse((cx_ - 6, ry + 415, cx_ + 6, ry + 427), outline=ln, width=2)
    d.rounded_rectangle((rx + 95, ry + 392, rx + 385, ry + 450), radius=29, outline=ln, width=4)
    dim(rx + 95, ry + 470, rx + 385, ry + 470, '1.5 BRIES', off=50)
    # notes
    nx, ny = 760, 1120
    notes = ['NOTES:', '1. ALL BOLTS: CHEDDAR', '2. GREASE PIVOT W/ BUTTER (!!)', '3. BARRELS: STRING CHEESE',
             '4. AMMO: CUBES, DICED 1cm', '5. DO NOT LEAVE IN SUN', '6. HOLES ARE STRUCTURAL', '   (DO NOT FILL)']
    for k, t in enumerate(notes):
        d.text((nx, ny + k * 46), t, font=MB(28) if k == 0 else M(28), fill=ln)
    d.line((nx, ny + 390, nx + 500, ny + 390), fill=ln, width=2)
    d.text((nx, ny + 410), 'REV C  -- CHECKED BY: TIM', font=M(26), fill=ln)
    d.ellipse((ox + 290, oy + 45, ox + 395, oy + 135), outline=(255, 250, 230), width=3)
    d.text((ox + 410, oy + 20), 'IT IS AN OLIVE', font=C(30), fill=(255, 250, 230))
    a = np.asarray(im).astype(float)
    rng = np.random.RandomState(7)
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    # paper: diazo fade + blotchy
    n = np.asarray(Image.fromarray((rng.rand(H // 64, W // 64) * 255).astype(np.uint8)).resize((W, H), Image.BICUBIC)) / 255.0
    a *= (0.86 + 0.18 * n)[..., None]
    # coffee rings
    for (cx, cy, r) in ((1080, 1650, 150), (420, 700, 120), (1180, 1000, 95)):
        dist = np.sqrt((xx - cx) ** 2 + (yy - cy) ** 2)
        ring = np.exp(-((dist - r) / 5.0) ** 2) * (0.55 + 0.45 * np.sin(np.arctan2(yy - cy, xx - cx) * 3 + cx) ** 2)
        fill = (dist < r) * 0.12
        m = np.clip(ring + fill, 0, 1)[..., None]
        a = a * (1 - m) + np.array([92, 64, 40]) * m
    # folds / creases + edge darkening
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
    ctext(d, (c, c), 'G', B(200), (120, 82, 22, 255))
    a = np.asarray(im).astype(float)
    rng = np.random.RandomState(21)
    n = np.asarray(Image.fromarray((rng.rand(S // 8, S // 8) * 255).astype(np.uint8)).resize((S, S), Image.BICUBIC)) / 255.0
    a[..., 3] *= np.clip((n - 0.12) * 3.0, 0, 1)
    a[..., :3] *= (0.85 + 0.15 * n)[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), 'RGBA').save(os.path.join(OUT, 'star_paint.png'))


if __name__ == '__main__':
    stickers(); stencil_backblast(); camo_tape(); blueprint(); star_paint()
    print(sorted(os.listdir(OUT)))
