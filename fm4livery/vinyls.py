"""Vinyl shape meshes from the user's own Media/Livery.zip (+ Livery_VinylsDecals in gamedb.slt for the id -> file map).
Nothing is bundled: shapes are read at run time. Meshes are 2D triangle sets in the shape's own units (unit square = -0.25..0.25)."""
import os, re, sqlite3, struct
from . import fzip

_cache = {}


def _table(media):
    out = {}
    p = os.path.join(media, 'db', 'gamedb.slt')
    if os.path.exists(p):
        try:
            c = sqlite3.connect('file:%s?mode=ro' % p, uri=True)
            for i, path in c.execute('select ID, Path from Livery_VinylsDecals'):
                out[int(i)] = re.split(r'[\\/]', path)[-1].lower()
            c.close()
        except sqlite3.Error:
            pass
    return out


def _fallback_name(i):
    """a_01 = 101 ... t_40 = 2040, u_01..u_40 = 2101..2140, u_41..u_80 = 2201..2240"""
    n = i % 100
    k = i // 100
    if k <= 20:
        return '%s_%02d.carbin' % (chr(96 + k), n)
    return 'u_%02d.carbin' % (n if k == 21 else n + 40)


def _parse(d):
    for o in range(0, len(d) - 12):
        v, n, s = struct.unpack_from('>3I', d, o)
        if s in (0x24, 0x48) and v in (1, 2) and 3 <= n < 200000 and o + 12 + n * s <= len(d):
            vo = o + 12
            vs = [struct.unpack_from('>3f', d, vo + i * s) for i in range(n)]
            e = vo + n * s
            for p in range(e, len(d) - 16):
                a, m, b = struct.unpack_from('>3I', d, p)
                if a == 3 and b == 2 and 3 <= m < 60000 and p + 12 + m * 2 <= len(d):
                    idx = struct.unpack_from('>%dH' % m, d, p + 12)
                    if all(i == 0xFFFF or i < n for i in idx):
                        return vs, idx
            return vs, None
    return None, None


def _tris(idx):
    out = []
    cur = []
    for i in list(idx) + [0xFFFF]:
        if i == 0xFFFF:
            for k in range(len(cur) - 2):
                t = (cur[k], cur[k + 1], cur[k + 2])
                if len(set(t)) == 3:
                    out.append(t)
            cur = []
        else:
            cur.append(i)
    return out


def shapes(media, ids):
    """{id: dict(v=[x,y,...], t=[a,b,c,...])} for the ids that can be read; missing ids are left out."""
    key = os.path.abspath(media)
    st = _cache.setdefault(key, dict(table=None, shapes={}))
    if st['table'] is None:
        st['table'] = _table(media)
    zp = os.path.join(media, 'Livery.zip')
    need = [i for i in ids if i not in st['shapes']]
    if need and os.path.exists(zp):
        want = {i: (st['table'].get(i) or _fallback_name(i)) for i in need}
        names = set(want.values())
        files = fzip.read_files(zp, lambda n: os.path.basename(n).lower() in names)
        byname = {os.path.basename(n).lower(): d for n, d in files.items()}
        for i, nm in want.items():
            d = byname.get(nm)
            if not d:
                continue
            vs, idx = _parse(d)
            if not vs or not idx:
                continue
            st['shapes'][i] = dict(v=[round(c, 4) for v3 in vs for c in v3[:2]], t=[j for t in _tris(idx) for j in t])
    return {i: st['shapes'][i] for i in ids if i in st['shapes']}


def catalogue(media):
    """[{id, name, cat}] for every vinyl: from Livery_VinylsDecals when gamedb.slt is there, else the known id pattern (a_01..t_40, u_01..u_80)."""
    out = []
    p = os.path.join(media, 'db', 'gamedb.slt') if media else ''
    if p and os.path.exists(p):
        try:
            c = sqlite3.connect('file:%s?mode=ro' % p, uri=True)
            for i, cat, name in c.execute('select ID, Category, Name from Livery_VinylsDecals order by ID'):
                out.append(dict(id=int(i), name=name, cat=re.split(r'[\\ _]', name or '')[0].upper() or str(cat)))
            c.close()
        except sqlite3.Error:
            out = []
    if not out:
        for k in range(1, 21):
            for n in range(1, 41):
                out.append(dict(id=k * 100 + n, name='%s %02d' % (chr(64 + k), n), cat=chr(64 + k)))
        for i in list(range(2101, 2141)) + list(range(2201, 2241)):
            out.append(dict(id=i, name='U %02d' % ((i % 100) + (0 if i < 2200 else 40)), cat='U'))
    return out
