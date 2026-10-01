"""Turn the raw float bakes (npy, written by assetkit inside Blender) into the delivered 8-bit PNGs.
Runs under system python (needs numpy + Pillow):  python3 pack.py <tmpdir> <out_base>
    <out_base>_BaseColor.png  sRGB (RGBA when an alpha bake exists)
    <out_base>_ORM.png        R = AO, G = roughness, B = metallic (linear)
    <out_base>_Normal.png     tangent space, DirectX / Unreal convention (green = -Y)
    <out_base>_Normal.gl.png  OpenGL convention, only used to build the GLB, deleted afterwards
"""
import os, sys
import numpy as np
from PIL import Image

tmp, base = sys.argv[1], sys.argv[2]
L = lambda n: np.load(os.path.join(tmp, n + ".npy"))


def srgb(x):
    x = np.clip(x, 0.0, 1.0)
    return np.where(x <= 0.0031308, x * 12.92, 1.055 * np.power(x, 1 / 2.4) - 0.055)


def u8(x, dither=True):
    x = np.clip(x, 0.0, 1.0) * 255.0
    if dither:
        x = x + (np.random.default_rng(7).random(x.shape) - 0.5)
    return np.clip(np.round(x), 0, 255).astype(np.uint8)


col = srgb(L("col"))
if os.path.exists(os.path.join(tmp, "alpha.npy")):
    a = L("alpha")[..., None]
    Image.fromarray(u8(np.concatenate([col, a], -1)), "RGBA").save(base + "_BaseColor.png", optimize=True)
else:
    Image.fromarray(u8(col), "RGB").save(base + "_BaseColor.png", optimize=True)
rm = L("rm"); ao = L("ao")
orm = np.dstack([ao, rm[..., 0], rm[..., 1]])
Image.fromarray(u8(orm), "RGB").save(base + "_ORM.png", optimize=True)
n = np.clip(L("nrm"), 0, 1)
# renormalise (bake margins / filtering can shorten vectors)
v = n * 2 - 1
v /= np.maximum(np.linalg.norm(v, axis=-1, keepdims=True), 1e-6)
n = v * 0.5 + 0.5
Image.fromarray(u8(n, False), "RGB").save(base + "_Normal.gl.png", compress_level=6)
dx = n.copy(); dx[..., 1] = 1.0 - dx[..., 1]
Image.fromarray(u8(dx, False), "RGB").save(base + "_Normal.png", optimize=True)
print("[pack] wrote", base + "_{BaseColor,ORM,Normal}.png")
