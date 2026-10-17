"""Texture override packs: the original car zip is never touched. A small DLC-style package is added that mounts
loose nodamage*.xds files over game:\\Media\\Cars\\<CAR>\\ at a higher priority. Restore = move that one package away.
Layout copied from the installed Widebody / Damage Plus packs. In-game acceptance of texture overrides is UNTESTED."""
import hashlib, json, os, shutil, struct, tempfile, time, zipfile
from . import clone as CL
PRIO = 27300            # above widebody carbins (27200); brake-options strings use 27250
TAG = 'fm4livery.json'
def _sha(b): return hashlib.sha256(b).hexdigest()
def folder_name(car): return (hashlib.sha1(('fm4livery-tex-' + car).encode()).hexdigest().upper() + '4D')
def find_pack_root(root, depth=8, fast=False):
    """.../4D530910/00000002 (the folder holding extracted DLC packages). fast: only the usual recomp location (no tree walk)."""
    root = os.path.abspath(root); base = root.count(os.sep)
    usual = os.path.join(root, '.local', 'user', '0000000000000000', '4D530910', '00000002')
    if os.path.isdir(usual): return usual
    if fast: return None
    for d, dirs, _ in os.walk(root):
        if d.count(os.sep) - base > depth: dirs[:] = []; continue
        if os.path.basename(d) == '00000002' and os.path.basename(os.path.dirname(d)).upper() == '4D530910' and 'Headers' not in d.split(os.sep): return d
    return None
def header_dir(pack_root): return os.path.join(os.path.dirname(pack_root), 'Headers', '00000002')
def make_header(pack_root, folder, title):
    """clone an installed pack's header when one exists (keeps its licence/flags), else synthesise the 0x148-byte layout"""
    hd = header_dir(pack_root); tpl = None
    if os.path.isdir(hd):
        for f in sorted(os.listdir(hd)):
            if f.endswith('.header'):
                b = open(os.path.join(hd, f), 'rb').read()
                if len(b) >= 0x148: tpl = bytearray(b); break
    if tpl is None: tpl = bytearray(0x148); tpl[0:8] = struct.pack('>II', 1, 2)
    for a, b_ in ((0x8, 0x108), (0x108, 0x148)): tpl[a:b_] = b'\0' * (b_ - a)
    t = title.encode('utf-16-be')[:0xF0]; tpl[0x8:0x8 + len(t)] = t
    n = folder.encode('ascii'); tpl[0x108:0x108 + len(n)] = n
    return bytes(tpl)
def _zip_stored(path, files):
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_STORED) as z:
        for n, b in files.items():
            zi = zipfile.ZipInfo(n, (1980, 1, 1, 0, 0, 0)); zi.compress_type = zipfile.ZIP_STORED; z.writestr(zi, b)
def offer_for(folder):
    """stable offer number + 16-hex OfferId for a package folder name"""
    offer = 3000 + int(folder[:6], 16) % 900; return offer, '4D530910F4FF%04X' % offer
def build(out_dir, cars, pack_root=None, prio=PRIO, originals=None, label='library', clones=None, media=None, roots=(), installed_dir=None):
    """cars {CAR: {entry name: bytes}} -> one override zip per car mounted over game:\\Media\\Cars\\<CAR>\\ .
    clones [{media, car_id, donor, donor_zip, display, tex}] -> a main zip with new cars (+ database execute.sql, merge.slt, string tables).
    Writes <out_dir>/<folder>/ and <out_dir>/<folder>.header; returns dict(folder, dir, header, zips, manifest)."""
    folder = folder_name(label); d = os.path.join(out_dir, folder); mdir = os.path.join(d, 'Media'); dz = os.path.join(mdir, 'DLCZips')
    if os.path.isdir(d): shutil.rmtree(d)
    os.makedirs(dz); offer, offer_hex = offer_for(folder)
    open(os.path.join(mdir, '%d.puboffer' % offer), 'wb').write(b'\x20\x0d\x0a')
    zips = []; mounts = []; tables = []; report = {}
    for car, tex in sorted(cars.items()):
        zn = 'Tex%s_pri_%d.zip' % (car.replace('_', ''), prio); CL.write_zip(os.path.join(dz, zn), [CL.stored(n, b) for n, b in tex.items()]); zips.append(zn)
        mounts.append('   <zip Name="%s" Mount="game:\\Media\\Cars\\%s\\" AltRootPath="game:\\Media\\Cars\\%s\\" ShouldCache="0" />' % (zn, car, car))
    if clones:
        if not media: raise ValueError('cloning needs the Media folder')
        gdb = os.path.join(media, 'db', 'gamedb.slt'); db = CL.open_db(gdb)
        strs, refs, maxpri = CL.string_pack(media, roots, installed_dir, clones, CL.reader)
        d_installed = installed_dir; stmts = []; entries = []
        for cl in clones:
            did = CL.donor_id(db, cl['donor'])
            if did is None: raise ValueError('donor car %s is not in the base game database' % cl['donor'])
            taken = CL.installed_car_ids([pack_root], exclude_dir=d_installed) if (pack_root and os.path.isdir(pack_root)) else {}
            if cl['car_id'] in taken: raise ValueError('car id %d is already used by installed package %s' % (cl['car_id'], taken[cl['car_id']]))
            dref, sref = refs[cl['media']]; st, rep = CL.make_sql(db, did, cl['car_id'], cl['media'], dref, sref, int(offer_hex, 16)); stmts += st; report[cl['media']] = rep
            entries += CL.car_entries(cl['donor_zip'], cl['media'], cl['tex'])
        entries.append(CL.stored('media/db/patch/%d000_merge.slt' % offer, CL.merge_slt(gdb, os.path.join(tempfile.gettempdir(), 'fm4livery_merge_tmp.slt'), offer, offer_hex)))
        for i, ch in enumerate(CL.chunk_sql(stmts), 1): entries.append(CL.stored('media/db/patch/%d%03d_execute.sql' % (offer, i), ch.encode('ascii')))
        CL.write_zip(os.path.join(dz, '%d_pri_65.zip' % offer), entries); db.close(); os.remove(os.path.join(tempfile.gettempdir(), 'fm4livery_merge_tmp.slt'))
        sp = max(26000, maxpri + 1); sn = 'StringTables_pri_%d.zip' % sp
        CL.write_zip(os.path.join(dz, sn), [CL.stored('%s/Data_Car.str' % l, b) for l, b in sorted(strs.items())]); zips.append(sn)
        mounts.append('   <zip Name="%s" Mount="game:\\Media\\StringTables\\"  />' % sn); tables.append('Data_Car')
    open(os.path.join(dz, 'zipmount.xml'), 'w').write('<?xml version="1.0" ?> \r\n<zipmount> \r\n' + '\r\n'.join(mounts) + ('\r\n' if mounts else '') + '</zipmount> \r\n')
    open(os.path.join(dz, 'stringtables.xml'), 'w').write('<?xml version="1.0" ?> \r\n<stringtables> \r\n' + ''.join('   <table Name="%s" /> \r\n' % t for t in tables) + '</stringtables> \r\n')
    man = dict(tool='fm4livery', kind='library', priority=prio, created=time.strftime('%Y-%m-%d %H:%M:%S'), offer=offer,
               cars={c: dict(files={n: _sha(b) for n, b in t.items()}, original_sha256=(originals or {}).get(c, {})) for c, t in cars.items()},
               clones={cl['media']: dict(car_id=cl['car_id'], donor=cl['donor'], display=cl['display'], rows=report.get(cl['media'], {}),
                                          files={n: _sha(b) for n, b in cl['tex'].items()}) for cl in (clones or [])})
    open(os.path.join(mdir, TAG), 'w').write(json.dumps(man, indent=1))
    hp = os.path.join(out_dir, folder + '.header'); open(hp, 'wb').write(make_header(pack_root or '', folder, 'FM4 Livery Textures'))
    return dict(folder=folder, dir=d, header=hp, zips=zips, manifest=man)
def installed(pack_root):
    out = []
    if pack_root and os.path.isdir(pack_root):
        for f in sorted(os.listdir(pack_root)):
            t = os.path.join(pack_root, f, 'Media', TAG)
            if os.path.isfile(t):
                try: out.append(dict(folder=f, **json.load(open(t))))
                except Exception: out.append(dict(folder=f, car='?'))
    return out
def _park(path, backup_root, label):
    dst = os.path.join(backup_root, time.strftime('%Y%m%d-%H%M%S'), label); os.makedirs(os.path.dirname(dst), exist_ok=True)
    shutil.move(path, dst); return dst
def install(pack_root, built, backup_root):
    """Copy a built pack into the game. An existing copy of the same pack is moved (not deleted) into backup_root first."""
    f = built['folder']; dest = os.path.join(pack_root, f); hd = header_dir(pack_root); os.makedirs(hd, exist_ok=True)
    hdest = os.path.join(hd, f + '.header'); parked = []
    if os.path.isdir(dest): parked.append(_park(dest, backup_root, f))
    if os.path.isfile(hdest): parked.append(_park(hdest, backup_root, f + '.header'))
    shutil.copytree(built['dir'], dest); shutil.copyfile(built['header'], hdest)
    # verify
    for zn in built['zips']: assert zipfile.ZipFile(os.path.join(dest, 'Media', 'DLCZips', zn)).testzip() is None
    assert os.path.getsize(hdest) >= 0x148
    return dict(dest=dest, header=hdest, parked=parked)
def uninstall(pack_root, folder, backup_root):
    """Restore = move the package + header out of the game (kept in backup_root, never deleted)."""
    if folder not in [p['folder'] for p in installed(pack_root)]: raise ValueError('not a fm4livery texture pack')
    out = [_park(os.path.join(pack_root, folder), backup_root, folder)]
    h = os.path.join(header_dir(pack_root), folder + '.header')
    if os.path.isfile(h): out.append(_park(h, backup_root, folder + '.header'))
    return out
def save_originals(car, zip_path, names, backup_root):
    """Pristine copy of the files being overridden, kept once and never overwritten (rename-able, for manual restore)."""
    from . import fzip
    d = os.path.join(backup_root, 'originals', car); os.makedirs(d, exist_ok=True); hashes = {}
    files = fzip.read_files(zip_path, lambda n: n in names)
    for n, b in files.items():
        p = os.path.join(d, n + '.orig'); hashes[n] = _sha(b)
        if not os.path.exists(p): open(p, 'wb').write(b)
    return hashes
def export_stfs(built, template, out_dir, car='library'):
    """Wrap a built pack as an STFS package (stale signature, see stfs.py). Verified by reading every file back."""
    from . import stfs
    os.makedirs(out_dir, exist_ok=True); out = os.path.join(out_dir, built['folder'])
    info = stfs.build(template, built['dir'], out, name='FM4 Livery Textures', desc='Baked livery texture overrides')
    n = stfs.verify(out, built['dir']); info.update(path=out, verified_files=n); return info
def legacy_entries(pack_root):
    """packs written by older versions: one package per car (manifest has 'car', files in its single zip)"""
    out = []
    for p in installed(pack_root):
        if p.get('car') and p.get('kind') != 'library':
            dz = os.path.join(pack_root, p['folder'], 'Media', 'DLCZips'); tex = {}
            for f in os.listdir(dz) if os.path.isdir(dz) else []:
                if f.lower().endswith('.zip'):
                    with zipfile.ZipFile(os.path.join(dz, f)) as z:
                        for n in z.namelist(): tex[n] = z.read(n)
            out.append(dict(folder=p['folder'], car=p['car'], created=p.get('created', ''), tex=tex))
    return out
