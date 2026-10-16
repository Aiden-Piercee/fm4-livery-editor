"""Write FM4 .xds textures: inverse of xds.decode. DXT5/DXT1 encoder (numpy), Xenon tiling, mip chain.
Keeps the original header + tail tile. Mips: 2x2 box (RGB averaged in gamma 2.0, alpha linear), levels > 16 texels."""
import struct
import numpy as np
from PIL import Image
from . import xds as _x

def _tile_index(bw, bh, lb):
    aw = (bw + 31) & ~31; ah = (bh + 31) & ~31
    ys, xs = np.mgrid[0:ah, 0:aw]; X = xs.ravel().astype(np.int64); Y = ys.ravel().astype(np.int64)
    macro = ((X >> 5) + (Y >> 5) * (aw >> 5)) << (lb + 7)
    micro = ((X & 7) + ((Y & 6) << 2)) << lb
    off = macro + ((micro & ~15) << 1) + (micro & 15) + ((Y & 8) << (3 + lb)) + ((Y & 1) << 4)
    t = ((off & ~511) << 3) + ((off & 448) << 2) + (off & 63) + ((Y & 16) << 7) + (((((Y & 8) >> 2) + (X >> 3)) & 3) << 6)
    return t, aw, ah

def _565(c):
    c = np.clip(c, 0, 255).astype(np.int32)
    return ((c[..., 0] * 31 + 127) // 255 << 11) | ((c[..., 1] * 63 + 127) // 255 << 5) | ((c[..., 2] * 31 + 127) // 255)

def _un565(v):
    r = (v >> 11) & 31; g = (v >> 5) & 63; b = v & 31
    return np.stack([(r * 255 + 15) // 31, (g * 255 + 31) // 63, (b * 255 + 15) // 63 * 0 + (b * 255 + 15) // 31], -1).astype(np.float32)

def _color_blocks(px):
    """px (N,16,3) float -> (N,8) bytes DXT1 colour block (4-colour mode)"""
    lo = px.min(1); hi = px.max(1)
    inset = (hi - lo) / 16.0
    lo = lo + inset; hi = hi - inset
    c0 = _565(hi); c1 = _565(lo)
    swap = c0 < c1; c0, c1 = np.where(swap, c1, c0), np.where(swap, c0, c1)
    eq = c0 == c1
    p0 = _un565(c0); p1 = _un565(c1)
    pal = np.stack([p0, p1, (2 * p0 + p1) / 3, (p0 + 2 * p1) / 3], 1)  # (N,4,3)
    d = ((px[:, :, None, :] - pal[:, None, :, :]) ** 2).sum(-1)       # (N,16,4)
    idx = d.argmin(-1).astype(np.uint32)
    idx = np.where(eq[:, None], 0, idx)
    bits = np.zeros(len(px), np.uint32)
    for i in range(16): bits |= idx[:, i] << (2 * i)
    out = np.zeros((len(px), 8), np.uint8)
    out[:, 0] = c0 & 255; out[:, 1] = c0 >> 8; out[:, 2] = c1 & 255; out[:, 3] = c1 >> 8
    for k in range(4): out[:, 4 + k] = (bits >> (8 * k)) & 255
    return out

def _alpha_blocks(a):
    """a (N,16) float 0..255 -> (N,8) DXT5 alpha block"""
    a = np.round(a).astype(np.int32)
    a0 = a.max(1); a1 = a.min(1)
    flat = a0 == a1
    pal = np.stack([a0, a1] + [((7 - i) * a0 + i * a1) // 7 for i in range(1, 7)], 1)  # (N,8)
    d = np.abs(a[:, :, None] - pal[:, None, :])
    idx = d.argmin(-1).astype(np.uint64)
    idx = np.where(flat[:, None], 0, idx)
    bits = np.zeros(len(a), np.uint64)
    for i in range(16): bits |= idx[:, i] << np.uint64(3 * i)
    out = np.zeros((len(a), 8), np.uint8)
    out[:, 0] = a0; out[:, 1] = a1
    for k in range(6): out[:, 2 + k] = (bits >> np.uint64(8 * k)) & np.uint64(255)
    return out

def encode_blocks(rgba, bs):
    """rgba uint8 (h,w,4) -> blocks (bh,bw,bs)"""
    h, w = rgba.shape[:2]; bh, bw = h // 4, w // 4
    b = rgba.reshape(bh, 4, bw, 4, 4).transpose(0, 2, 1, 3, 4).reshape(bh * bw, 16, 4).astype(np.float32)
    out = np.empty((bh * bw, bs), np.uint8); CH = 20000
    for s in range(0, len(b), CH):
        c = b[s:s + CH]
        if bs == 16:
            out[s:s + CH, :8] = _alpha_blocks(c[:, :, 3]); out[s:s + CH, 8:] = _color_blocks(c[:, :, :3])
        else:
            out[s:s + CH] = _color_blocks(c[:, :, :3])
    return out.reshape(bh, bw, bs)

def tile_level(blocks):
    bh, bw, bs = blocks.shape; lb = 4 if bs == 16 else 3
    t, aw, ah = _tile_index(bw, bh, lb)
    buf = np.zeros(int(t.max()) + bs, np.uint8)
    ys, xs = np.mgrid[0:ah, 0:aw]
    ok = ((ys < bh) & (xs < bw)).ravel()
    src = np.zeros((ah, aw, bs), np.uint8); src[:bh, :bw] = blocks
    src = src.reshape(-1, bs)
    idx = t[:, None] + np.arange(bs)[None, :]
    buf[idx.ravel()] = src.ravel()
    return buf

def _swap(buf):
    n = len(buf) & ~1
    out = buf.copy(); out[0:n:2] = buf[1:n:2]; out[1:n:2] = buf[0:n:2]
    return out

def _down(rgba):
    f = rgba.astype(np.float32); h, w = f.shape[:2]
    f = f.reshape(h // 2, 2, w // 2, 2, 4)
    rgb = ((f[..., :3] / 255.0) ** 2.0).mean((1, 3)) ** 0.5 * 255.0
    a = f[..., 3].mean((1, 3))
    return np.concatenate([rgb, a[..., None]], -1).round().astype(np.uint8)

def build(orig, rgba):
    """orig: original .xds bytes (header, format, size and tail are reused); rgba: PIL image or (h,w,4) uint8 array.
    Returns the new .xds bytes. Image is resized to the texture size if different."""
    fmt, w, h = _x.info(orig)
    if fmt not in (51, 53): raise ValueError('unsupported xds format %d' % fmt)
    bs = 16 if fmt == 53 else 8
    if isinstance(rgba, Image.Image): rgba = np.asarray(rgba.convert('RGBA'))
    if rgba.shape[:2] != (h, w):
        raise ValueError('image must be %dx%d (got %dx%d)' % (w, h, rgba.shape[1], rgba.shape[0]))
    data = orig[52:]
    out = bytearray(data)
    lv = rgba; cw, ch = w, h; pos = 0; level = 0
    while True:
        blocks = encode_blocks(lv, bs)
        buf = _swap(tile_level(blocks))
        if pos + len(buf) > len(out): break
        out[pos:pos + len(buf)] = buf.tobytes()
        pos += len(buf)
        if level == 0: pos = (pos + 4095) & ~4095
        cw //= 2; ch //= 2; level += 1
        if cw <= 16 or ch <= 16 or pos >= len(out): break
        lv = _down(lv)
    return orig[:52] + bytes(out)
