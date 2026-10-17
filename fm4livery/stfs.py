"""STFS packaging for FM4 DLC packs (Xbox 360 container): repack an extracted package folder into an STFS file using an existing
retail package as the template (its header, thumbnails, title and content type are kept; file table, data blocks and the L0/L1/L2
hash tables are rebuilt). The console signature (LIVE RSA) CANNOT be re-created, so it is left stale: Xenia and the recomp do not
check it, a retail console does, and modded consoles need the package re-signed with their own tools. Hardware use is untested.
Layout notes: 43k blocks: L0#g at g*171 (+sg+1, +1 if sg>0), L1#0 at 171, L1#s at s*170*171+s+1, L2 at 170*171+1; file table = first data blocks."""
import hashlib, os, struct
BLK = 0x1000; PER = 170; SUPER = 0x70E4; HDR = 0xB000
def backing(b):
    r = ((b + 0xAA) // 0xAA) + b
    if b < 0xAA: return r
    if b < SUPER: return r + ((b + SUPER) // SUPER)
    return 1 + r + ((b + SUPER) // SUPER)
def l0pos(g):
    if g == 0: return 0
    sg = g // PER; return g * 171 + sg + 1 + (1 if sg > 0 else 0)
def l1pos(s): return 171 if s == 0 else s * PER * 171 + s + 1
L2POS = PER * 171 + 1
def is_template(path):
    """a LIVE marketplace package for the FM4 title (only its first 0xB000 bytes are used)"""
    try:
        with open(path, 'rb') as f: h = f.read(0x400)
        return len(h) >= 0x400 and h[:4] == b'LIVE' and struct.unpack('>I', h[0x360:0x364])[0] == 0x4D530910 and os.path.getsize(path) > HDR
    except OSError: return False
def find_template(roots, depth=6):
    """first retail FM4 DLC STFS file found under the given folders"""
    for root in roots:
        if not root or not os.path.isdir(root): continue
        base = root.rstrip(os.sep).count(os.sep)
        for d, dirs, files in os.walk(root):
            if d.count(os.sep) - base >= depth: dirs[:] = []
            for f in files:
                p = os.path.join(d, f)
                if not f.lower().endswith(('.py', '.json', '.xml', '.zip', '.header', '.xds', '.png')) and is_template(p): return p
    return None
def _collect(src):
    kids = {}
    for root, dirs, files in os.walk(src):
        rel = os.path.relpath(root, src).replace('\\', '/'); rel = '' if rel == '.' else rel
        kids[rel] = sorted([(d, True) for d in dirs] + [(f, False) for f in files], key=lambda x: x[0].lower())
    return kids
def build(template, src, out, name=None, desc=None):
    hdr = bytearray(open(template, 'rb').read(HDR))
    kids = _collect(src); ents = []; queue = [('', -1)]
    while queue:
        rel, pidx = queue.pop(0)
        for nm, isd in kids.get(rel, []):
            p = (rel + '/' + nm) if rel else nm; ents.append((nm, isd, pidx, p))
            if isd: queue.append((p, len(ents) - 1))
    nft = (len(ents) * 0x40 + BLK - 1) // BLK; blocks = [bytes(BLK)] * nft; start = {}
    for i, (nm, isd, pidx, p) in enumerate(ents):
        if isd: continue
        data = open(os.path.join(src, p), 'rb').read(); start[i] = (len(blocks), len(data))
        for k in range(0, len(data), BLK):
            c = data[k:k + BLK]; blocks.append(c + bytes(BLK - len(c)))
    tab = bytearray(nft * BLK)
    for i, (nm, isd, pidx, p) in enumerate(ents):
        nb = nm.encode('ascii'); assert len(nb) <= 0x28, nm
        e = bytearray(0x40); e[:len(nb)] = nb; e[0x28] = len(nb) | 0x40 | (0x80 if isd else 0)
        if not isd:
            s, sz = start[i]; n = (sz + BLK - 1) // BLK
            e[0x29:0x2C] = n.to_bytes(3, 'little'); e[0x2C:0x2F] = n.to_bytes(3, 'little'); e[0x2F:0x32] = s.to_bytes(3, 'little'); e[0x34:0x38] = struct.pack('>I', sz)
        e[0x32:0x34] = struct.pack('>H', 0xFFFF if pidx < 0 else pidx); e[0x38:0x3C] = bytes.fromhex('2d6f0020'); e[0x3C:0x40] = bytes.fromhex('2d6f0020')
        tab[i * 0x40:(i + 1) * 0x40] = e
    for k in range(nft): blocks[k] = bytes(tab[k * BLK:(k + 1) * BLK])
    n = len(blocks); nL0 = (n + PER - 1) // PER; nL1 = (nL0 + PER - 1) // PER if nL0 > 1 else 0; hasL2 = nL1 > 1
    phys = n + nL0 + nL1 + (1 if hasL2 else 0); img = bytearray(phys * BLK)
    for b, c in enumerate(blocks): o = backing(b) * BLK; img[o:o + BLK] = c
    sha = lambda o: hashlib.sha1(bytes(img[o * BLK:(o + 1) * BLK])).digest()
    for g in range(nL0):
        t = bytearray(BLK)
        for k in range(PER):
            b = g * PER + k
            if b >= n: break
            nxt = b + 1 if b + 1 < n else 0xFFFFFF
            t[k * 0x18:k * 0x18 + 0x18] = hashlib.sha1(blocks[b]).digest() + b'\x80' + nxt.to_bytes(3, 'big')
        o = l0pos(g) * BLK; img[o:o + BLK] = t
    for s in range(nL1):
        t = bytearray(BLK)
        for k in range(PER):
            g = s * PER + k
            if g >= nL0: break
            t[k * 0x18:k * 0x18 + 20] = sha(l0pos(g))
        o = l1pos(s) * BLK; img[o:o + BLK] = t
    if hasL2:
        t = bytearray(BLK)
        for s in range(nL1): t[s * 0x18:s * 0x18 + 20] = sha(l1pos(s))
        o = L2POS * BLK; img[o:o + BLK] = t; top = sha(L2POS)
    elif nL1: top = sha(l1pos(0))
    else: top = sha(0)
    vd = bytearray(hdr[0x379:0x379 + 0x24]); vd[3:5] = nft.to_bytes(2, 'little'); vd[5:8] = (0).to_bytes(3, 'little'); vd[8:28] = top
    vd[28:32] = struct.pack('>I', n); vd[32:36] = struct.pack('>I', 0); hdr[0x379:0x379 + 0x24] = vd
    hdr[0x34C:0x354] = struct.pack('>Q', len(img))
    if name: b_ = name.encode('utf-16-be')[:0x7E]; hdr[0x411:0x411 + 0x80] = b_ + bytes(0x80 - len(b_))
    if desc: b_ = desc.encode('utf-16-be')[:0x7E]; hdr[0xD11:0xD11 + 0x80] = b_ + bytes(0x80 - len(b_))
    cid = hashlib.sha1(bytes(hdr[0x344:HDR])).digest(); hdr[0x32C:0x340] = cid
    open(out, 'wb').write(bytes(hdr) + bytes(img))
    return dict(entries=len(ents), data_blocks=n, size=HDR + len(img), content_id=cid.hex().upper() + '4D')
class Reader:
    """minimal STFS reader used to verify what build() wrote"""
    def __init__(s, path):
        s.f = open(path, 'rb'); h = s.f.read(0x400); hs = struct.unpack('>I', h[0x340:0x344])[0]; s.first = (hs + 0xFFF) & ~0xFFF
        vd = h[0x379:0x379 + 0x24]; nft = vd[3] | vd[4] << 8; ftb = vd[5] | vd[6] << 8 | vd[7] << 16; s.ents = []
        raw = b''.join(s.block(ftb + k) for k in range(nft))
        for i in range(len(raw) // 0x40):
            e = raw[i * 0x40:(i + 1) * 0x40]; nl = e[0x28] & 0x3F
            if nl == 0: break
            s.ents.append(dict(name=e[:nl].decode('latin1'), isdir=bool(e[0x28] & 0x80), n=e[0x29] | e[0x2A] << 8 | e[0x2B] << 16,
                               start=e[0x2F] | e[0x30] << 8 | e[0x31] << 16, parent=struct.unpack('>H', e[0x32:0x34])[0], size=struct.unpack('>I', e[0x34:0x38])[0]))
        for e in s.ents:
            p = e['parent']; parts = [e['name']]
            while p != 0xFFFF: parts.append(s.ents[p]['name']); p = s.ents[p]['parent']
            e['path'] = '/'.join(reversed(parts))
    def block(s, b): s.f.seek(s.first + backing(b) * BLK); return s.f.read(BLK)
    def read(s, path):
        e = next(x for x in s.ents if x['path'].lower() == path.lower())
        return b''.join(s.block(e['start'] + k) for k in range(e['n']))[:e['size']]
    def files(s): return [e['path'] for e in s.ents if not e['isdir']]
    def close(s): s.f.close()
def verify(stfs_path, src):
    """every file under src must read back byte-identical from the STFS file; returns the number of files checked"""
    r = Reader(stfs_path); got = set(r.files()); n = 0
    try:
        for root, _, files in os.walk(src):
            for f in files:
                p = os.path.join(root, f); rel = os.path.relpath(p, src).replace('\\', '/')
                if rel.lower() not in {g.lower() for g in got}: raise ValueError('missing in STFS: ' + rel)
                if r.read(rel) != open(p, 'rb').read(): raise ValueError('content differs: ' + rel)
                n += 1
    finally: r.close()
    return n
