"""Garage access: read the profile PlayerDatabase, list cars, assign livery slots. Writes always make a backup first."""
import os, shutil, sqlite3, time
from . import crypto
def load(profile_dir, pe):
    xuid = os.path.basename(profile_dir.rstrip('/\\')); raw = open(os.path.join(profile_dir, 'PlayerDatabase'), 'rb').read()
    db, ok = crypto.read_db(raw, pe, xuid); con = sqlite3.connect(':memory:'); con.deserialize(db)
    return dict(con=con, raw=raw, ok=ok, xuid=xuid, path=os.path.join(profile_dir, 'PlayerDatabase'), pe=pe)
def rows(g, names=None):
    names = names or {}
    return [dict(garage_id=i, car_id=c, car=names.get(c, '?'), livery=l or '') for i, c, l in g['con'].execute('select Id,CarId,LiveryFileName from Career_Garage order by Id')]
def livery_path(garage_id): return 'Liveries\\%d.liv' % garage_id
def assign(g, garage_id):
    """point the garage car at Liveries\\<id>.liv (no-op if already set). Returns the path."""
    p = livery_path(garage_id)
    n = g['con'].execute('update Career_Garage set LiveryFileName=? where Id=?', (p, garage_id)).rowcount
    if not n: raise KeyError('no garage car with Id %d' % garage_id)
    g['con'].commit(); g['dirty'] = True; return p
def backup(path):
    b = '%s.bak_%s' % (path, time.strftime('%Y%m%d_%H%M%S')); shutil.copy2(path, b); return b
def save(g):
    """re-encrypt and write PlayerDatabase (backup first, verify after). Game must be closed."""
    new = crypto.write_db(g['raw'], g['con'].serialize(), g['pe'], g['xuid'])
    chk, ok = crypto.read_db(new, g['pe'], g['xuid'])
    if not ok or chk != g['con'].serialize(): raise RuntimeError('verification failed; nothing written')
    b = backup(g['path']); tmp = g['path'] + '.new'; open(tmp, 'wb').write(new); os.replace(tmp, g['path'])
    g['raw'] = new; g['dirty'] = False; return b
