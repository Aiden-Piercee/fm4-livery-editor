"""Texture override packs: the original car zip is never touched. A small DLC-style package is added that mounts
loose nodamage*.xds files over game:\\Media\\Cars\\<CAR>\\ at a higher priority. Restore = move that one package away.
Layout copied from the installed Widebody / Damage Plus packs. In-game acceptance of texture overrides is UNTESTED."""
import hashlib, json, os, shutil, struct, time, zipfile
PRIO = 27300            # above widebody carbins (27200); brake-options strings use 27250
TAG = 'fm4livery.json'
def _sha(b): return hashlib.sha256(b).hexdigest()
def folder_name(car): return (hashlib.sha1(('fm4livery-tex-' + car).encode()).hexdigest().upper() + '4D')
def find_pack_root(root, depth=8):
    """.../4D530910/00000002 (the folder holding extracted DLC packages)"""
    root = os.path.abspath(root); base = root.count(os.sep)
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
def build(out_dir, car, tex, pack_root=None, prio=PRIO, originals=None):
    """tex {entry name: bytes}. Writes <out_dir>/<folder>/ and <out_dir>/<folder>.header; returns dict(folder, dir, header)."""
    folder = folder_name(car); d = os.path.join(out_dir, folder); media = os.path.join(d, 'Media'); dz = os.path.join(media, 'DLCZips')
    if os.path.isdir(d): shutil.rmtree(d)
    os.makedirs(dz); offer = '9%04d' % (int(folder[:6], 16) % 10000)
    open(os.path.join(media, offer + '.puboffer'), 'wb').write(b'\x20\x0d\x0a')
    open(os.path.join(dz, 'stringtables.xml'), 'w').write('<stringtables>\r\n</stringtables>\r\n')
    zn = 'Tex%s_pri_%d.zip' % (car.replace('_', ''), prio); _zip_stored(os.path.join(dz, zn), tex)
    open(os.path.join(dz, 'zipmount.xml'), 'w').write('<zipmounts>\r\n\t<zip Name="%s" Mount="game:\\Media\\Cars\\%s\\" AltRootPath="game:\\Media\\Cars\\%s\\" ShouldCache="0" />\r\n</zipmounts>\r\n' % (zn, car, car))
    man = dict(tool='fm4livery', car=car, priority=prio, created=time.strftime('%Y-%m-%d %H:%M:%S'),
               files={n: _sha(b) for n, b in tex.items()}, original_sha256=originals or {})
    open(os.path.join(media, TAG), 'w').write(json.dumps(man, indent=1))
    hp = os.path.join(out_dir, folder + '.header'); open(hp, 'wb').write(make_header(pack_root or '', folder, 'FM4 Livery Texture - ' + car))
    return dict(folder=folder, dir=d, header=hp, zip=zn, manifest=man)
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
    z = zipfile.ZipFile(os.path.join(dest, 'Media', 'DLCZips', built['zip']))
    assert z.testzip() is None and os.path.getsize(hdest) >= 0x148
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
def export_stfs(built, template, out_dir, car):
    """Wrap a built pack as an STFS package (stale signature, see stfs.py). Verified by reading every file back."""
    from . import stfs
    os.makedirs(out_dir, exist_ok=True); out = os.path.join(out_dir, built['folder'])
    info = stfs.build(template, built['dir'], out, name='FM4 Livery Texture - ' + car, desc='Baked livery texture override for ' + car)
    n = stfs.verify(out, built['dir']); info.update(path=out, verified_files=n); return info
