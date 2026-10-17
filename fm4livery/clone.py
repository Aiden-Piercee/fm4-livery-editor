"""Clone a base-game car as a NEW car (own Data_Car row, own media folder, own name) so several texture variants of the same car can
coexist. Builds the pieces of a normal FM4 DLC car pack: database rows as execute.sql statements (INSERT OR IGNORE, like the retail
and ported packs), a media copy of the donor's files (raw-copied, textures replaced), and string-table entries for the new name.
Shared with the donor (not copied): engine, drivetrain, wheels, physics payload rows, audio, thumbnail. NOT verified in game."""
import glob, os, re, sqlite3, struct, zipfile, zlib
from . import strtab
XTRA = 0x1123
SKIP_PREFIX = ('Event', 'Arcade', 'Demo', 'IE', 'Kinect', 'HasCar', 'NewProfile', 'Rewards')
SKIP_TABLES = {'List_AntiSwayPhysics', 'List_SpringDamperPhysics', 'ContentOffers'}   # physics payload rows stay shared with the donor
REF_HI = 0xCD49                                                                    # high 16 bits of Data_Car text references
FIRST_CLONE_ID = 9700
def _q(v):
    if v is None: return 'NULL'
    if isinstance(v, bytes): return "X'" + v.hex() + "'"
    if isinstance(v, (int, float)): return repr(v)
    return "'" + str(v).replace("'", "''") + "'"
def open_db(path): return sqlite3.connect('file:%s?mode=ro' % path, uri=True)
def donor_id(db, media_name):
    r = db.execute('select Id from Data_Car where MediaName=?', (media_name,)).fetchone()
    return r[0] if r else None
def used_car_ids(db, merges=()):
    ids = {r[0] for r in db.execute('select Id from Data_Car')}
    for p in merges:
        try:
            c = open_db(p); ids |= {r[0] for r in c.execute('select Id from Data_Car')}; c.close()
        except sqlite3.Error: pass
    return ids
def installed_car_ids(roots, exclude_dir=None):
    """car ids defined by installed packs (Data_Car rows in their *merge.slt) -> {id: package folder}; a clone must not reuse one"""
    import tempfile
    from . import fzip
    out = {}
    for r in roots:
        if not r or not os.path.isdir(r): continue
        for d in sorted(os.listdir(r)):
            dz = os.path.join(r, d, 'Media', 'DLCZips')
            if not os.path.isdir(dz) or (exclude_dir and os.path.abspath(os.path.join(r, d)) == os.path.abspath(exclude_dir)): continue
            for z in sorted(os.listdir(dz)):
                if not z.lower().endswith('_pri_65.zip'): continue
                try: g = fzip.read_files(os.path.join(dz, z), lambda n: n.lower().endswith('merge.slt'))
                except Exception: continue
                for b in g.values():
                    with tempfile.NamedTemporaryFile(suffix='.slt', delete=False) as f: f.write(b); p = f.name
                    try:
                        c = sqlite3.connect(p)
                        for (i,) in c.execute('select Id from Data_Car'): out.setdefault(i, d)
                        c.close()
                    except sqlite3.Error: pass
                    finally: os.remove(p)
    return out
def make_sql(db, donor, new_id, new_media, disp_ref, short_ref, offer_int):
    """-> (statements, report {table: rows}). Row ids in car-owned tables follow the base convention (car*1000+n); others get 90000000+new*1000+k."""
    out = []; rep = {}
    for (t,) in db.execute("select name from sqlite_master where type='table' order by 1").fetchall():
        if t in SKIP_TABLES or t.startswith(SKIP_PREFIX): continue
        cols = [r[1] for r in db.execute('pragma table_info("%s")' % t)]; lc = [c.lower() for c in cols]
        carc = [i for i, c in enumerate(lc) if c in ('ordinal', 'carid')]; bodyc = [i for i, c in enumerate(lc) if c == 'carbodyid']
        idc = 0 if lc and lc[0] == 'id' else None
        if t == 'Data_Car': sel = 'Id=?'; args = (donor,)
        elif t == 'Data_CarBody': sel = 'Id/1000=?'; args = (donor,)
        elif carc or bodyc:
            sel = ' or '.join(['"%s"=?' % cols[i] for i in carc] + ['"%s"/1000=?' % cols[i] for i in bodyc]); args = (donor,) * (len(carc) + len(bodyc))
        else: continue
        k = 0
        for row in db.execute('select * from "%s" where %s' % (t, sel), args).fetchall():
            r = list(row)
            for i in carc:
                if r[i] == donor: r[i] = new_id
            for i in bodyc:
                if isinstance(r[i], int) and r[i] // 1000 == donor: r[i] = new_id * 1000 + r[i] % 1000
            if t == 'Data_CarBody' and lc[0] == 'id': r[0] = new_id * 1000 + row[0] % 1000
            elif t == 'Data_Car':
                r[0] = new_id
                for i, c in enumerate(lc):
                    if c == 'medianame': r[i] = new_media
                    elif c == 'displayname': r[i] = disp_ref
                    elif c == 'modelshort': r[i] = short_ref
            elif idc is not None and t != 'Data_CarBody':
                if isinstance(row[0], int) and row[0] // 1000 == donor: r[0] = new_id * 1000 + row[0] % 1000
                else: r[0] = 90000000 + new_id * 1000 + k
            k += 1
            out.append('INSERT OR IGNORE INTO "%s" (%s) VALUES (%s);' % (t, ','.join('"%s"' % c for c in cols), ','.join(_q(v) for v in r)))
        if k: rep[t] = k
    # make the car appear in the offer
    out.append('INSERT OR IGNORE INTO ContentOffersMapping (Id,OfferId,ContentId,ContentType) VALUES (%d,%d,%d,1);' % (8000000 + new_id, offer_int, new_id)); rep['ContentOffersMapping'] = 1
    return out, rep
def chunk_sql(stmts, limit=3800):
    chunks = []; cur = []; n = 0
    for s in stmts:
        if cur and n + len(s) + 2 > limit: chunks.append('\r\n'.join(cur)); cur = []; n = 0
        cur.append(s); n += len(s) + 2
    if cur: chunks.append('\r\n'.join(cur))
    return chunks
def merge_slt(base_db_path, out_path, offer, offer_hex):
    """an otherwise-empty copy of the base schema (page size 1024) holding only this pack's ContentOffers row"""
    if os.path.exists(out_path): os.remove(out_path)
    src = open_db(base_db_path); dst = sqlite3.connect(out_path); dst.execute('pragma page_size=1024')
    for (sql,) in src.execute("select sql from sqlite_master where type='table' and sql is not null").fetchall(): dst.execute(sql)
    dst.execute("insert into ContentOffers values (?,?,?,?,?,1,1,1,'','',0,0,0,0,0,0)", (offer_hex, int(offer_hex, 16), '', '', offer))
    dst.commit(); dst.execute('vacuum'); dst.close(); src.close()
    return open(out_path, 'rb').read()
# ---------------------------------------------------------------- zips
def write_zip(path, entries):
    """entries: [(name, method, crc, usize, raw bytes)] with the central-directory extra 0x1123 (absolute data offset) like game zips"""
    cd = bytearray(); off = 0
    with open(path, 'wb') as f:
        for name, meth, crc, usize, raw in entries:
            n = name.encode('ascii'); lh = struct.pack('<IHHHHHIIIHH', 0x04034b50, 10, 0, meth, 0, 0x21, crc, len(raw), usize, len(n), 0)
            data_off = off + len(lh) + len(n); f.write(lh); f.write(n); f.write(raw)
            ex = struct.pack('<HHI', XTRA, 4, data_off)
            cd += struct.pack('<IHHHHHHIIIHHHHHII', 0x02014b50, 10, 10, 0, meth, 0, 0x21, crc, len(raw), usize, len(n), len(ex), 0, 0, 0, 0, off) + n + ex
            off = data_off + len(raw)
        f.write(cd); f.write(struct.pack('<IHHHHIIH', 0x06054b50, 0, 0, len(entries), len(entries), len(cd), off, 0))
def stored(name, data): return (name, 0, zlib.crc32(data) & 0xffffffff, len(data), data)
def raw_entries(zip_path):
    zf = zipfile.ZipFile(zip_path)
    with open(zip_path, 'rb') as f:
        for i in zf.infolist():
            if i.filename.endswith('/'): continue
            f.seek(i.header_offset); h = f.read(30); nl, el = struct.unpack('<HH', h[26:30]); f.seek(i.header_offset + 30 + nl + el)
            yield i.filename, i.compress_type, i.CRC, i.file_size, f.read(i.compress_size)
def damage_attribs(roots, donor, exclude_dir=None):
    """carattribs.xml for `donor` from an installed per-car override zip (Damage Plus 'DmgCars_pri_*.zip', entries '<MEDIA>/carattribs.xml'),
    highest priority wins; None when no installed pack overrides it. A clone has a new media name, so such overrides never reach it by themselves."""
    from . import fzip
    best = None; want = (donor + '/carattribs.xml').lower()
    for root in roots:
        for z in glob.glob(os.path.join(root, '*', 'Media', 'DLCZips', 'Dmg*_pri_*.zip')):
            if exclude_dir and os.path.normcase(os.path.abspath(z)).startswith(os.path.normcase(os.path.abspath(exclude_dir))): continue
            try: names = [n for n in fzip.names(z) if n.lower() == want]
            except Exception: continue
            if not names: continue
            pr = _prio(os.path.basename(z))
            if best is None or pr > best[0]: best = (pr, z, names[0])
    if not best: return None
    return fzip.read_files(best[1], lambda n: n == best[2])[best[2]]
def car_entries(donor_zip, new_media, tex):
    """donor zip raw-copied under media/cars/<new_media>/ ; texture files in tex replaced by stored copies.
    The game finds a car's model by its media name (<media>.carbin, <media>_lod0.carbin, <media>_cockpit.carbin, brake parts,
    digitalgauge/dash_<media>.*), so files that carry the donor's media name are renamed to the new one; a file another file
    may refer to by its old name (the odometer xds) is kept under both names."""
    donor = os.path.splitext(os.path.basename(donor_zip))[0].lower(); nm = new_media.lower(); out = []; seen = set()
    def ren(name):
        d, _, b = name.rpartition('/'); lb = b.lower()
        if lb.startswith(donor) or lb.startswith('dash_' + donor): return (d + '/' if d else '') + lb.replace(donor, nm, 1)
        return None
    for name, meth, crc, usize, raw in raw_entries(donor_zip):
        r = ren(name); keep_old = r is None or name.lower().endswith('.xds')
        if name in tex: out.append(stored('media/cars/%s/%s' % (new_media, name), tex[name])); seen.add(name); continue
        if r: out.append(('media/cars/%s/%s' % (new_media, r), meth, crc, usize, raw))
        if keep_old: out.append(('media/cars/%s/%s' % (new_media, name), meth, crc, usize, raw))
    for n in tex:
        if n not in seen: out.append(stored('media/cars/%s/%s' % (new_media, n), tex[n]))
    return out
# ---------------------------------------------------------------- strings
def _prio(name):
    m = re.search(r'_pri_(\d+)', name); return int(m.group(1)) if m else 0
def languages(media):
    d = os.path.join(media, 'StringTables') if media else ''
    return sorted(os.path.splitext(f)[0] for f in os.listdir(d) if f.lower().endswith('.zip')) if os.path.isdir(d) else []
def installed_string_zips(roots, exclude_dir=None):
    out = []
    for r in roots:
        for d, _, files in os.walk(r):
            if d.count(os.sep) - r.rstrip(os.sep).count(os.sep) > 9: continue
            if exclude_dir and os.path.abspath(d).startswith(os.path.abspath(exclude_dir)): continue
            for f in files:
                if f.lower().startswith('stringtables') and f.lower().endswith('.zip') and '_pri_' in f: out.append((_prio(f), os.path.join(d, f)))
    return sorted(out)
def latest_table(media, lang, table, szips, read):
    """raw bytes of the highest-priority copy of table for lang (base zip, then pack zips ascending)"""
    raw = None; base = os.path.join(media, 'StringTables', lang + '.zip')
    if os.path.exists(base): raw = read(base).get(table + '.str', raw)
    for _, p in szips:
        try: g = read(p, prefix=lang + '/')
        except Exception: continue
        if table + '.str' in g: raw = g[table + '.str']
    return raw
def string_pack(media, roots, exclude_dir, clones, read):
    """{lang: new Data_Car.str bytes}, {media_name: (display_ref, short_ref)}, max installed priority. One shared hash per new string across languages."""
    langs = languages(media); szips = installed_string_zips(roots, exclude_dir)
    tabs = {l: latest_table(media, l, 'Data_Car', szips, read) for l in langs}
    tabs = {l: strtab.parse(b) for l, b in tabs.items() if b}
    taken = set()
    for t in tabs.values(): taken |= strtab.hashes(t)
    refs = {}; adds = []; h = 0xF4A0
    for cl in clones:
        hs = []
        for _ in range(2):
            while h in taken or h == 0xFFFF: h = (h + 1) & 0xFFFF
            taken.add(h); hs.append(h)
        refs[cl['media']] = ('_&%d' % ((REF_HI << 16) | hs[0]), '_&%d' % ((REF_HI << 16) | hs[1]))
        adds.append(('IDS_DisplayName_%d' % cl['car_id'], hs[0], cl['display'])); adds.append(('IDS_ModelShort_%d' % cl['car_id'], hs[1], cl['display'][:40]))
    out = {l: strtab.rebuild(t, adds) for l, t in tabs.items()}
    return out, refs, (szips[-1][0] if szips else 0)
def reader(path, prefix=''):
    """{name without prefix: bytes} for the Data_Car.str entry of a (base or pack) string zip"""
    from . import fzip
    g = fzip.read_files(path, lambda n: n.startswith(prefix) and n[len(prefix):] == 'Data_Car.str')
    return {n[len(prefix):]: b for n, b in g.items()}
