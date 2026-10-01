# Pattern textures for the class accessories (tileable, painted look matching the cheese body).
import numpy as np, math, os, random
from PIL import Image, ImageDraw, ImageFilter
OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'tex')
os.makedirs(OUT, exist_ok=True)
S = 1024


def soften(im, r=1.2):
    return im.filter(ImageFilter.GaussianBlur(r))


def paisley(base=(176, 28, 30), ink=(245, 236, 220), dark=(40, 18, 18), name='bandana_paisley'):
    """classic bandana: red field, white/black paisley teardrops, dot borders"""
    rng = random.Random(3)
    im = Image.new('RGB', (S, S), base); d = ImageDraw.Draw(im)
    def bez(p0, p1, p2, n=20):
        return [((1 - t) ** 2 * p0[0] + 2 * (1 - t) * t * p1[0] + t * t * p2[0], (1 - t) ** 2 * p0[1] + 2 * (1 - t) * t * p1[1] + t * t * p2[1]) for t in [i / n for i in range(n + 1)]]

    def tear(cx, cy, r, ang, col, w):
        """paisley boteh: round body with a tail that curls back"""
        tip = (-1.9 * r, -1.15 * r)
        outer = bez(tip, (-1.7 * r, 0.9 * r), (0, r))                     # tip -> top of body
        body = [(r * math.cos(a), r * math.sin(a)) for a in [math.pi / 2 - i / 40 * 1.65 * math.pi for i in range(41)]]
        inner = bez(body[-1], (-0.9 * r, -0.95 * r), tip)
        pts = outer + body + inner
        ca, sa = math.cos(ang), math.sin(ang)
        P = [(cx + x * ca - y * sa, cy + x * sa + y * ca) for x, y in pts]
        d.line(P + [P[0]], fill=col, width=w, joint='curve')
        return P
    for gy in range(4):
        for gx in range(4):
            for k in (0, 1):
                cx = (gx + 0.5 * k + 0.25) * S / 4; cy = (gy + 0.5 * k + 0.25) * S / 4
                ang = (gx + gy + k) * 1.1
                for (r, col, w) in ((44, ink, 7), (32, dark, 5), (20, ink, 4)):
                    for ox in (-S, 0, S):
                        for oy in (-S, 0, S):
                            tear(cx + ox, cy + oy, r, ang, col, w)
                for ox in (-S, 0, S):
                    for oy in (-S, 0, S):
                        d.ellipse((cx + ox - 9, cy + oy - 9, cx + ox + 9, cy + oy + 9), fill=ink)
                for i in range(14):
                    a = i / 14 * 2 * math.pi
                    x = cx + 92 * math.cos(a); y = cy + 92 * math.sin(a) * 0.7
                    for ox in (-S, 0, S):
                        for oy in (-S, 0, S):
                            d.ellipse((x + ox - 5, y + oy - 5, x + ox + 5, y + oy + 5), fill=ink)
    im = soften(im, 1.0)
    a = np.asarray(im).astype(float)
    a *= (0.92 + 0.08 * np.random.RandomState(1).rand(S, S))[..., None]          # cloth mottling
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name + '.png'))


def southwest(name='welder_pattern'):
    """welder's cap fabric: bold southwest/aztec bands -- turquoise, rust, cream, black"""
    cols = [(32, 120, 128), (233, 222, 196), (178, 70, 32), (30, 26, 24), (233, 222, 196), (214, 150, 44)]
    im = Image.new('RGB', (S, S), cols[1]); d = ImageDraw.Draw(im)
    band = S // 8
    for b in range(8):
        y0 = b * band
        c = cols[b % len(cols)]
        if b % 2 == 0:
            d.rectangle((0, y0, S, y0 + band), fill=c)
            # stepped diamonds
            for i in range(9):
                cx = i * S / 8
                for ox in (-S, 0, S):
                    pts = [(cx + ox, y0 + 8), (cx + ox + band / 2 - 8, y0 + band / 2), (cx + ox, y0 + band - 8), (cx + ox - band / 2 + 8, y0 + band / 2)]
                    d.polygon(pts, fill=cols[(b + 2) % len(cols)])
                    pts2 = [(cx + ox, y0 + 26), (cx + ox + band / 2 - 30, y0 + band / 2), (cx + ox, y0 + band - 26), (cx + ox - band / 2 + 30, y0 + band / 2)]
                    d.polygon(pts2, fill=cols[(b + 3) % len(cols)])
        else:
            d.rectangle((0, y0, S, y0 + band), fill=cols[1])
            for i in range(32):
                x = i * S / 32
                d.polygon([(x, y0 + band - 10), (x + S / 64, y0 + 10), (x + S / 32, y0 + band - 10)], fill=cols[(b + 1) % len(cols)])
    im = soften(im, 1.0)
    a = np.asarray(im).astype(float)
    a *= (0.9 + 0.1 * np.random.RandomState(2).rand(S, S))[..., None]
    Image.fromarray(np.clip(a, 0, 255).astype(np.uint8)).save(os.path.join(OUT, name + '.png'))


def trucker_mesh(name='trucker_mesh'):
    """trucker cap back panels: cream mesh -- grey-cream with dark hex holes (as colour; bump from the same)"""
    im = Image.new('L', (S, S), 225); d = ImageDraw.Draw(im)
    step = 16
    for j in range(int(S / (step * 0.87)) + 3):
        for i in range(S // step + 2):
            x = i * step + (step / 2 if j % 2 else 0); y = j * step * 0.87
            d.ellipse((x - 5, y - 5, x + 5, y + 5), fill=70)
    im = soften(im, 0.8)
    im.save(os.path.join(OUT, name + '.png'))


def bandaid(name='bandaid'):
    """band-aid: skin-tan plastic, perforation dots, pale gauze pad in the middle (U across the strip)"""
    W, H = 1024, 256
    im = Image.new('RGB', (W, H), (214, 170, 128)); d = ImageDraw.Draw(im)
    d.rounded_rectangle((W * 0.36, H * 0.12, W * 0.64, H * 0.88), radius=18, fill=(238, 226, 214))
    for y in range(18, H, 34):
        for x in range(18, W, 34):
            if W * 0.35 < x < W * 0.65: continue
            d.ellipse((x - 4, y - 4 * 4, x + 4, y + 4 * 4) if False else (x - 4, y - 4, x + 4, y + 4), fill=(188, 142, 100))
    for y in range(int(H * 0.16), int(H * 0.86), 9):
        d.line((W * 0.37, y, W * 0.63, y), fill=(226, 214, 200), width=2)
    im = soften(im, 0.7)
    im.save(os.path.join(OUT, name + '.png'))


def grease(name='grease_smear'):
    """RGBA finger-swipe grease smear (u along the swipe): 3-4 soft streaks, thick at the start, dragging out"""
    W, H = 1024, 384
    rng = np.random.RandomState(5)
    alpha = np.zeros((H, W)); dark = np.zeros((H, W))
    yy, xx = np.mgrid[0:H, 0:W].astype(float)
    t = xx / W
    lanes = [0.30, 0.47, 0.63, 0.78]
    for k, c in enumerate(lanes):
        c += 0.02 * rng.randn()
        wd = (0.115 - 0.012 * k) * (1.0 - 0.5 * t) * (0.6 + 0.4 * np.clip(t * 6, 0, 1))
        cy = (c + 0.04 * np.sin(t * 5 + k) + 0.05 * t * (k - 1.5) * 0.4) * H
        d = np.abs(yy - cy) / (wd * H + 1e-6)
        streak = np.clip(1.0 - d ** 2.6, 0, 1)
        fade = np.clip(1.2 - t * (0.95 + 0.25 * rng.rand()), 0, 1) ** 0.9 * np.clip((t - 0.03) / 0.10, 0, 1)
        alpha = np.maximum(alpha, streak * fade * (0.97 - 0.06 * k))
    # thick blob where the finger first pressed + speckle + streak texture
    blob = np.exp(-(((xx - 0.12 * W) / (0.075 * W)) ** 2 + ((yy - 0.54 * H) / (0.33 * H)) ** 2) ** 1.5)
    alpha = np.maximum(alpha, blob * 0.97)
    grain = np.asarray(Image.fromarray((rng.rand(H, W) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.2))) / 255.0
    streaks = np.asarray(Image.fromarray((rng.rand(H, W // 16) * 255).astype(np.uint8)).resize((W, H), Image.BILINEAR).filter(ImageFilter.GaussianBlur(0.8))) / 255.0
    alpha = alpha * (0.82 + 0.18 * streaks) * (0.9 + 0.2 * grain)
    alpha = alpha * np.clip((1 - t) / 0.1, 0, 1) * np.clip(t / 0.03, 0, 1) * np.clip(np.minimum(yy, H - yy) / (0.06 * H), 0, 1)
    for _ in range(140):
        x0, y0 = rng.rand() * W * 0.95, rng.rand() * H
        r = rng.rand() * 3 + 1
        alpha = np.maximum(alpha, np.exp(-(((xx - x0) ** 2 + (yy - y0) ** 2) / (r * r))) * 0.55 * (alpha > 0.05))
    a = np.asarray(Image.fromarray((np.clip(alpha, 0, 1) * 255).astype(np.uint8)).filter(ImageFilter.GaussianBlur(1.6))) / 255.0
    col = np.zeros((H, W, 3))
    lo = np.array([16, 13, 10]); hi = np.array([62, 50, 38])
    m = np.clip(1.0 - a, 0, 1)[..., None]
    col = lo + (hi - lo) * m * (0.7 + 0.3 * grain[..., None])
    rgba = np.dstack([col, a * 255]).astype(np.uint8)
    Image.fromarray(rgba, 'RGBA').save(os.path.join(OUT, name + '.png'))


if __name__ == '__main__':
    paisley(); southwest(); trucker_mesh(); bandaid(); grease()
    print(sorted(os.listdir(OUT)))
