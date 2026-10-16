"""Read renderable geometry from an FM4 .carbin (read-only; grammar from the project's carbin.py).

parse(data) -> list of parts. Each part:
  name, lod, prim (4 list / 6 strip), mat, unpack (12 floats), index (np.uint32 array),
  verts (np.float32 N x 3 positions, car space metres), uv (N x 2), normal (N x 3)
"""
import struct
import numpy as np


class Fmt(Exception):
    pass


class _R:
    def __init__(s, d):
        s.d = d
        s.o = 0

    def u32(s):
        v = struct.unpack_from('>I', s.d, s.o)[0]
        s.o += 4
        return v

    def raw(s, n):
        if s.o + n > len(s.d):
            raise Fmt('read past EOF')
        b = s.d[s.o:s.o + n]
        s.o += n
        return b

    def string(s):
        n = s.u32()
        if n > 4096:
            raise Fmt('bad string')
        return bytes(s.raw(n)).decode('latin1')

    def ver(s, ok, what=''):
        v = s.u32()
        if v not in ok:
            raise Fmt('%s: version %d' % (what, v))
        return v

    def strlist(s, what):
        s.ver((1,), what)
        for _ in range(s.u32()):
            s.string()

    def counted(s, what, elem):
        s.ver((1,), what)
        n = s.u32()
        s.raw(n * elem)


def _vb(r, what):
    v = r.ver((2, 3), what)
    cnt = r.u32()
    size = r.u32()
    if v == 3:
        fl = r.u32()
        if fl & 1:
            r.u32()
        if fl & 2:
            return cnt, size, b''
    return cnt, size, r.raw(cnt * size)


def _ib(r):
    v = r.ver((3, 4), 'IB')
    if v >= 4:
        fl = r.u32()
        if fl & 1:
            r.u32()
    cnt = r.u32()
    fmt = r.u32()
    if fmt not in (2, 4):
        raise Fmt('IB format')
    raw = r.raw(cnt * fmt)
    return np.frombuffer(raw, dtype='>u2' if fmt == 2 else '>u4').astype(np.uint32)


def _skip_front(r):
    first = struct.unpack_from('>I', r.d, 0)[0]
    if first == 1:
        r.ver((1,), 'Model')
    elif first == 3:
        r.ver((3,), 'Wheel')
        r.raw(68)
    elif first in (2, 5):
        v = r.ver((2, 3, 4, 5), 'Car')
        r.raw(256)
        r.raw(80)
        if v >= 3:
            n = r.u32()
            r.raw(n * {3: 27, 4: 30, 5: 32}[v])
    else:
        raise Fmt('root version %d' % first)
    r.ver((16, 17), 'Model16')
    r.u32()
    r.ver((1,), 'Emitters')
    for _ in range(r.u32()):
        r.ver((2,), 'Emitter')
        r.raw(136)
    r.ver((3,), 'DriverControls')
    r.raw(256 + 8 + 15 * 36 + 12)
    r.strlist('BoneMappingTable')


def parse(data):
    r = _R(data)
    _skip_front(r)
    r.ver((4,), 'Model4')
    r.ver((4,), 'OrderedSubModels')
    for _ in range(r.u32()):
        for _ in range(2):
            n = r.u32()
            r.raw(n * 4)
    r.ver((1,), 'SubModel_Container')
    subs = []
    for _ in range(r.u32()):
        v = r.ver((4, 5), 'SubModel5')
        hdr = r.raw(56)
        r.ver((1,), 'GlassParticles')
        r.counted('gv', 16)
        r.counted('gi', 2)
        r.raw(1)
        if v >= 3:
            r.raw(4)
        r.ver((1,), 'SubModel1')
        name = r.string()
        cnt, size, vb = _vb(r, 'VB')
        r.ver((1,), 'Mesh_Container')
        meshes = []
        for _ in range(r.u32()):
            mv = r.ver((1, 2, 3), 'Mesh3')
            if mv >= 2:
                r.raw(1)
            if mv >= 3:
                r.raw(64)
            v2 = r.ver((1, 2), 'Mesh2')
            mname = r.string()
            lod, prim, mat = struct.unpack('>III', r.raw(12))
            r.ver((1,), 'Unpack')
            unpack = struct.unpack('>12f', r.raw(48))
            idx = _ib(r)
            if v2 >= 2:
                r.raw(4)
            meshes.append(dict(name=mname, lod=lod, prim=prim, mat=mat, unpack=unpack, index=idx))
        if v > 1:
            _vb(r, 'VB_LOD0')
        if v >= 5:
            r.ver((1,), 'Morph')
            r.raw(1)
            _vb(r, 'M')
            _vb(r, 'M0')
        subs.append(dict(hdr=bytes(hdr), name=name, count=cnt, stride=size, vb=vb, meshes=meshes))
    return subs


# ---------------------------------------------------------------------------------------------
# Renderable model for the 3D viewer
# ---------------------------------------------------------------------------------------------
import base64
import re
import xml.etree.ElementTree as ET

SKIP_SUBS = ('bumperFrace', 'wingrace', 'bumperFb', 'winga', 'cagerace')
HIDDEN_SUBS = ('interior', 'seatL', 'seatR', 'steering_wheel', 'undercarriagea')
PAINT_MATS = ('body', 'body_2')
GLASS_MATS = ('window', 'glass', 'black_glass', 'detail_glass_clear', 'detail_glass_red', 'detail_glass_amber')
LIGHT_MATS = ('textured_reflector', 'tail_light', 'reverse_light', 'head_light', 'reflector')
# viewer colours (r, g, b, a)
CAT_COLOR = {
    'paint': (0.80, 0.82, 0.86, 1.0), 'glass': (0.35, 0.45, 0.55, 0.45), 'light': (0.95, 0.80, 0.55, 1.0),
    'chrome': (0.78, 0.80, 0.82, 1.0), 'trim': (0.10, 0.10, 0.11, 1.0), 'tire': (0.06, 0.06, 0.06, 1.0),
    'rim': (0.62, 0.63, 0.66, 1.0), 'interior': (0.25, 0.22, 0.20, 1.0), 'under': (0.12, 0.12, 0.12, 1.0),
}


def _category(sub, mat):
    if sub == 'wheel':
        return 'tire' if mat in ('tire', 'blur_rim') else 'rim'
    if sub == 'undercarriagea':
        return 'under'
    if sub in HIDDEN_SUBS:
        return 'interior'
    if mat in PAINT_MATS:
        return 'paint'
    if mat in GLASS_MATS:
        return 'glass'
    if mat in LIGHT_MATS:
        return 'light'
    if mat in ('chrome', 'chrome_2'):
        return 'chrome'
    return 'trim'


def _positions(sub):
    """Positions in car space (metres). Verified against face normals (dot 0.99)."""
    f = struct.unpack('>14f', sub['hdr'])
    off = np.array(f[0:3])
    mn = np.array(f[3:6])
    mx = np.array(f[6:9])
    w = np.frombuffer(sub['vb'], dtype='>i2').reshape(-1, 16).astype(np.float64)
    dec = w[:, 0:3] / 32767.0 * (w[:, 3:4] / 32767.0)
    lo, hi = dec.min(0), dec.max(0)
    span = np.where(hi - lo > 1e-12, hi - lo, 1.0)
    pos = off + mn + (dec - lo) / span * (mx - mn)
    q = w[:, 8:12] / 32767.0
    x, y, z, qw = q.T
    nrm = np.stack([1 - 2 * (y * y + z * z), 2 * (x * y + z * qw), 2 * (x * z - y * qw)], 1)
    nrm /= np.maximum(np.linalg.norm(nrm, axis=1, keepdims=True), 1e-9)
    return pos, nrm


def _uv0(sub):
    """Per-vertex UV set 1 = the car's own texture atlas (nodamage.xds): vertex words 4,5 as u16 / 65535
    (verified by rendering the Falcon V8 Supercar's baked livery onto its body)."""
    w = np.frombuffer(sub['vb'], dtype='>u2').reshape(-1, 16).astype(np.float32)
    return w[:, 4:6] / 65535.0


def _strip_to_tris(idx):
    out = []
    cur = []
    for i in idx.tolist():
        if i == 0xFFFF or i == 0xFFFFFFFF:
            cur = []
            continue
        cur.append(i)
        if len(cur) >= 3:
            a, b, c = (cur[-3], cur[-2], cur[-1]) if len(cur) % 2 else (cur[-2], cur[-3], cur[-1])
            if a != b and b != c and a != c:
                out.append((a, b, c))
    return np.array(out, dtype=np.uint32).reshape(-1, 3)


def _wheel_layout(phys_xml):
    wb, ft, rt, zc = 2.5, 1.6, 1.6, 0.0
    try:
        root = ET.fromstring(phys_xml)
        m = root.find('Misc')
        wb = float(m.get('Wheelbase'))
        ft = float(m.get('FrontTrackOuter'))
        rt = float(m.get('RearTrackOuter'))
        b = root.find('.//BottomCenterWheelbasePos')      # wheelbase centre is not always at the model origin
        if b is not None: zc = float(b.get('z'))
    except Exception:
        pass
    return wb, ft, rt, zc


def build_model(carbin_bytes, phys_xml=b''):
    """-> dict(parts=[...], pos=b64 f32, nrm=b64 f32, idx=b64 u32, bbox=[min,max])"""
    subs = parse(carbin_bytes)
    P, N, UV, I, parts = [], [], [], [], []
    nv = 0
    ni = 0
    wb, ft, rt, zc = _wheel_layout(phys_xml)

    def add(name, mat, cat, pos, nrm, tris, hidden, uv=None):
        nonlocal nv, ni
        used = np.unique(tris)
        remap = np.zeros(int(used.max()) + 1, dtype=np.uint32)
        remap[used] = np.arange(len(used), dtype=np.uint32)
        P.append(pos[used].astype(np.float32))
        N.append(nrm[used].astype(np.float32))
        UV.append((uv[used] if uv is not None else np.zeros((len(used), 2))).astype(np.float32))
        I.append((remap[tris] + nv).astype(np.uint32).ravel())
        parts.append(dict(name=name, mat=mat, cat=cat, hidden=hidden, i0=ni, n=int(tris.size), atlas=uv is not None and cat in ('paint', 'trim', 'chrome')))
        nv += len(used)
        ni += int(tris.size)

    for s in subs:
        if s['name'] in SKIP_SUBS or 'frame' in s['name'].lower():
            continue
        meshes = [m for m in s['meshes'] if m['lod'] == 1]
        if not meshes:
            continue
        pos, nrm = _positions(s)
        uv0 = _uv0(s)
        for m in meshes:
            tris = _strip_to_tris(m['index']) if m['prim'] == 6 else m['index'][:len(m['index']) // 3 * 3].reshape(-1, 3)
            if not len(tris):
                continue
            cat = _category(s['name'], m['name'])
            if s['name'] == 'wheel':
                cy = float(pos[:, 1].max())          # wheel radius: sits on the ground
                ox = -float(pos[:, 0].min())         # outer tyre face sits at TrackOuter/2
                for fz, tr, side in ((-1, ft, -1), (-1, ft, 1), (1, rt, -1), (1, rt, 1)):
                    p = pos.copy()
                    p[:, 1] += cy
                    p[:, 2] += zc + fz * wb / 2.0
                    n2 = nrm.copy()
                    t2 = tris
                    if side == -1:
                        p[:, 0] += -tr / 2.0 + ox
                    else:
                        p[:, 0] = -p[:, 0] + tr / 2.0 - ox
                        n2[:, 0] = -n2[:, 0]
                        t2 = tris[:, ::-1]
                    add('wheel', m['name'], cat, p, n2, t2, False)
            else:
                add(s['name'], m['name'], cat, pos, nrm, tris, s['name'] in HIDDEN_SUBS, uv0)
    pos = np.concatenate(P)
    b64 = lambda a: base64.b64encode(np.ascontiguousarray(a).tobytes()).decode()
    return dict(parts=parts, pos=b64(pos), nrm=b64(np.concatenate(N)), uv=b64(np.concatenate(UV)), idx=b64(np.concatenate(I)),
                bbox=[pos.min(0).tolist(), pos.max(0).tolist()], colors=CAT_COLOR,
                wheelbase=wb), pos, np.concatenate(I)


# Panel projection (in model axes: x = car left(-)/right(+), y up, z = front(-)/rear(+)).
# panel -> (axis for pos X, sign, axis for pos Y, sign). Orientations were confirmed in game.
PANEL_AXES = {
    'left': (2, 1, 1, 1), 'right': (2, -1, 1, 1),
    'front': (0, -1, 1, 1), 'rear': (0, 1, 1, 1),
    'roof': (2, 1, 0, 1),
}


def fit_projection(pos, idx, parts, masks):
    """Fit scale/offset (pos units per metre) of each panel so the paintable body lines up with the
    car's silhouette mask. Returns {panel: dict(ax, sx, ay, sy, s, cx, cy, box, iou)}."""
    from PIL import Image, ImageDraw
    tris = []
    for p in parts:
        if p['cat'] == 'paint' and not p['hidden']:
            tris.append(idx[p['i0']:p['i0'] + p['n']].reshape(-1, 3))
    if not tris:
        return {}
    T = np.concatenate(tris)
    out = {}
    for panel, (ax, sx, ay, sy) in PANEL_AXES.items():
        mk = masks.get(panel)
        if mk is None:
            continue
        x0, x1, y0, y1 = mk['box']
        sil = mk['sil']
        H, W = sil.shape
        D = 2
        tgt = np.asarray(Image.fromarray(sil.astype(np.uint8) * 255).resize((max(W // D, 1), max(H // D, 1)), Image.NEAREST)) > 127
        h, w = tgt.shape
        u0 = pos[:, ax] * sx
        v0 = pos[:, ay] * sy
        s_init = (x1 - x0) / max(np.ptp(u0[T.ravel()]), 1e-6)
        ty, tx = np.where(tgt)

        def raster(s, cx, cy):
            im = Image.new('L', (w, h), 0)
            d = ImageDraw.Draw(im)
            u = (u0 * s + cx - x0) / D
            v = (y1 - (v0 * s + cy)) / D
            for t in T:
                d.polygon([(u[t[0]], v[t[0]]), (u[t[1]], v[t[1]]), (u[t[2]], v[t[2]])], fill=255)
            return np.asarray(im) > 127

        best = (-1.0, s_init, 0.0, 0.0)
        for s in np.linspace(s_init * 0.8, s_init * 1.25, 14):
            r = raster(s, 0.0, 0.0)
            ys, xs = np.where(r)
            if not len(ys):
                continue
            cx = (tx.mean() - xs.mean()) * D
            cy = -(ty.mean() - ys.mean()) * D
            r = raster(s, cx, cy)
            iou = (r & tgt).sum() / max((r | tgt).sum(), 1)
            if iou > best[0]:
                best = (iou, s, cx, cy)
        out[panel] = dict(ax=ax, sx=sx, ay=ay, sy=sy, s=float(best[1]), cx=float(best[2]), cy=float(best[3]),
                          box=[float(v) for v in mk['box']], iou=float(best[0]))
    return out
