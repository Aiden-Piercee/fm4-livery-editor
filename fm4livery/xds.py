"""Read FM4 .xds textures (Xbox 360 GPU textures: big-endian D3DTexture header, Xenon-tiled DXT1/DXT5, 16-bit byte swap).
Only the base level is decoded. Layout verified on the car atlases (nodamage*.xds)."""
import io, struct
import numpy as np
from PIL import Image

def info(raw):
    """-> (format code, width, height); 53 = DXT5, 51 = DXT1"""
    f = struct.unpack('>13I', raw[:52])[7:13]
    return f[1] & 63, (f[2] & 0x1fff) + 1, ((f[2] >> 13) & 0x1fff) + 1

def decode(raw):
    fmt, w, h = info(raw)
    if fmt not in (51, 53): raise ValueError('unsupported xds format %d' % fmt)
    bs = 16 if fmt == 53 else 8; lb = 4 if bs == 16 else 3
    bw, bh = w // 4, h // 4
    data = raw[52:]
    a = np.frombuffer(data, dtype='>u2').astype('<u2').view(np.uint8)
    ys, xs = np.mgrid[0:bh, 0:bw]; X = xs.ravel().astype(np.int64); Y = ys.ravel().astype(np.int64)
    aw = (bw + 31) & ~31
    macro = ((X >> 5) + (Y >> 5) * (aw >> 5)) << (lb + 7)
    micro = ((X & 7) + ((Y & 6) << 2)) << lb
    off = macro + ((micro & ~15) << 1) + (micro & 15) + ((Y & 8) << (3 + lb)) + ((Y & 1) << 4)
    t = ((off & ~511) << 3) + ((off & 448) << 2) + (off & 63) + ((Y & 16) << 7) + (((((Y & 8) >> 2) + (X >> 3)) & 3) << 6)
    if int(t.max()) + bs > len(a): raise ValueError('xds data too short')
    lin = a[t[:, None] + np.arange(bs)[None, :]].reshape(bh, bw, bs).tobytes()
    dds = (b'DDS ' + struct.pack('<7I', 124, 0x81007, h, w, len(lin), 0, 0) + b'\0' * 44 +
           struct.pack('<2I4s5I', 32, 4, b'DXT5' if bs == 16 else b'DXT1', 0, 0, 0, 0, 0) + struct.pack('<5I', 0x1000, 0, 0, 0, 0))
    return Image.open(io.BytesIO(dds + lin)).convert('RGBA')
