"""Find the user's game files without asking them to hunt: default.pe, Media folder, profiles, car table."""
import os, re, sqlite3, zipfile, tempfile
HEX16 = re.compile(r'^[0-9A-Fa-f]{16}$')
def _walk(root, depth, skip=('.git', 'node_modules', '__pycache__', 'trash', '_to_delete')):
    root = os.path.abspath(root); base = root.count(os.sep)
    for d, dirs, files in os.walk(root):
        if d.count(os.sep) - base >= depth: dirs[:] = []
        dirs[:] = [x for x in dirs if x not in skip]
        yield d, dirs, files
def find_pe(root, depth=4):
    for d, _, files in _walk(root, depth):
        if 'default.pe' in files: return os.path.join(d, 'default.pe')
def find_media(root, depth=4):
    for d, dirs, _ in _walk(root, depth):
        if os.path.basename(d).lower() == 'media' and 'cars' in [x.lower() for x in dirs]: return d
def find_profiles(root, depth=7):
    out = []
    for d, _, files in _walk(root, depth):
        if HEX16.match(os.path.basename(d)) and 'PlayerDatabase' in files: out.append(d)
    return out
def car_table(media_dir, extra_roots=()):
    """{CarId: MediaName} from Media/db/gamedb.slt plus any DLC merge databases found under extra_roots"""
    names = {}
    def grab(path):
        try:
            c = sqlite3.connect('file:%s?mode=ro' % path, uri=True)
            for i, m in c.execute('select Id,MediaName from Data_Car'): names.setdefault(i, m)
            c.close()
        except sqlite3.Error: pass
    for p in (os.path.join(media_dir, 'db', 'gamedb.slt'),):
        if os.path.exists(p): grab(p)
    for r in extra_roots:
        for d, _, files in _walk(r, 8):
            for f in files:
                if f.endswith('_pri_65.zip'):
                    try:
                        z = zipfile.ZipFile(os.path.join(d, f))
                        for n in z.namelist():
                            if n.endswith('_merge.slt'):
                                t = tempfile.NamedTemporaryFile(suffix='.slt', delete=False); t.write(z.read(n)); t.close(); grab(t.name); os.unlink(t.name)
                    except Exception: pass
    return names
def car_zip(media_dir, media_name):
    for d in ('cars', 'Cars'):
        p = os.path.join(media_dir, d, media_name + '.zip')
        if os.path.exists(p): return p
def _prio(name):
    m = re.search(r'_pri_(\d+)', name); return int(m.group(1)) if m else 0
def string_tables(media_dir, extra_roots=(), lang='EN', tables=('Data_Car', 'List_CarMake')):
    """{table: {hash16: text}} - the base StringTables/<lang>.zip, then every pack StringTables_pri_N.zip in priority order (higher wins)"""
    from . import fzip, strings
    srcs = []
    base = os.path.join(media_dir, 'StringTables', lang + '.zip') if media_dir else None
    if base and os.path.exists(base): srcs.append((0, base, ''))
    for r in extra_roots:
        for d, _, files in _walk(r, 9):
            for f in files:
                if f.lower().startswith('stringtables') and f.lower().endswith('.zip') and '_pri_' in f: srcs.append((_prio(f), os.path.join(d, f), lang + '/'))
    out = {t: {} for t in tables}
    for _, path, pre in sorted(srcs):
        try: got = fzip.read_files(path, lambda n: n in {pre + t + '.str' for t in tables})
        except Exception: continue
        for t in tables:
            raw = got.get(pre + t + '.str')
            if raw:
                try: out[t].update(strings.parse(raw))
                except Exception: pass
    return out
def car_titles(media_dir, extra_roots=()):
    """{CarId: 'Year Make Model'} using Data_Car / List_CarMake rows (base + pack merges) and the string tables"""
    from . import strings
    tabs = string_tables(media_dir, extra_roots)
    rows = {}; makes = {}
    def grab(path):
        try:
            c = sqlite3.connect('file:%s?mode=ro' % path, uri=True)
            try:
                for i, y, mk, dn in c.execute('select Id,Year,MakeID,DisplayName from Data_Car'): rows.setdefault(i, (y, mk, dn))
            except sqlite3.Error: pass
            try:
                for i, dn in c.execute('select ID,DisplayName from List_CarMake'): makes.setdefault(i, dn)
            except sqlite3.Error: pass
            c.close()
        except sqlite3.Error: pass
    p = os.path.join(media_dir, 'db', 'gamedb.slt') if media_dir else None
    if p and os.path.exists(p): grab(p)
    for r in extra_roots:
        for d, _, files in _walk(r, 8):
            for f in files:
                if f.endswith('_pri_65.zip'):
                    try:
                        z = zipfile.ZipFile(os.path.join(d, f))
                        for n in z.namelist():
                            if n.endswith('_merge.slt'):
                                t = tempfile.NamedTemporaryFile(suffix='.slt', delete=False); t.write(z.read(n)); t.close(); grab(t.name); os.unlink(t.name)
                    except Exception: pass
    out = {}
    for i, (y, mk, dn) in rows.items():
        model = strings.resolve(tabs['Data_Car'], dn); make = strings.resolve(tabs['List_CarMake'], makes.get(mk))
        if not model: continue
        if make and make.lower() not in model.lower(): model = make + ' ' + model
        out[i] = ('%s %s' % (y, model)) if y else model
    return out
