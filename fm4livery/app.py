"""Shared logic for the CLI and the GUI: find the game/profile, fit an image onto panels, build and write designs."""
import base64, io, os, shutil, time
import numpy as np
from PIL import Image
from . import crypto, design, detect, garage, masks, share
class AppError(Exception): pass
DEFAULT_PANELS = ('left', 'right')
def context(root=None, pe=None, profile=None, media=None):
    root = root or os.getcwd(); pe_path = pe or detect.find_pe(root); media = media or detect.find_media(root)
    if not pe_path: raise AppError('default.pe not found - choose the folder that contains your game / recomp files')
    profs = [profile] if profile else detect.find_profiles(root)
    if not profs: raise AppError('no profile with a PlayerDatabase found under that folder')
    if len(profs) > 1 and not profile: raise AppError('several profiles found: ' + ' | '.join(profs))
    names = detect.car_table(media, [root]) if media else {}
    return dict(root=root, pe=open(pe_path, 'rb').read(), pe_path=pe_path, media=media, profile=profs[0], profiles=profs,
                xuid=os.path.basename(profs[0].rstrip('/\\')), names=names)
def liv_path(c, slot): return os.path.join(c['profile'], 'Liveries', '%d.liv' % slot)
def load_garage(c): return garage.load(c['profile'], c['pe'])
def car_row(g, c, slot):
    for r in garage.rows(g, c['names']):
        if r['garage_id'] == slot: return r
    raise AppError('no garage car with Id %d' % slot)
def car_zip_for(c, row, carzip=None):
    zp = carzip or (detect.car_zip(c['media'], row['car']) if c['media'] and row['car'] != '?' else None)
    if not zp: raise AppError('cannot find the car zip for car %d - choose it from the list' % row['car_id'])
    return zp
def list_car_zips(c):
    out = []
    if c['media']:
        for d in ('cars', 'Cars'):
            p = os.path.join(c['media'], d)
            if os.path.isdir(p): out += sorted(os.path.join(p, f) for f in os.listdir(p) if f.lower().endswith('.zip'))
    return out
def fit_panels(img, mk, panels, shapes=450, res=2.0, fill='contain', progress=None):
    """-> {panel: dict(box, layers)}; layers = [(kind, cx, cy, w, h, theta, (r,g,b))] drawn in order, first = panel background"""
    from . import fit
    arr = np.asarray(img).astype(float); e = max(2, min(img.width, img.height) // 25)
    edge = tuple(np.concatenate([arr[:e].reshape(-1, 3), arr[-e:].reshape(-1, 3), arr[:, :e].reshape(-1, 3), arr[:, -e:].reshape(-1, 3)]).mean(0))
    per = max(1, shapes // len(panels)); out = {}
    for n, pn in enumerate(panels):
        if pn not in mk: raise AppError('this car has no %s panel (it has: %s)' % (pn, ', '.join(mk)))
        x0, x1, y0, y1 = mk[pn]['box']; bw, bh = x1 - x0, y1 - y0
        s = min(bw / img.width, bh / img.height) if fill == 'contain' else max(bw / img.width, bh / img.height)
        w, h = img.width * s, img.height * s; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        L, *_ = fit.fit(img, cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2, n_shapes=per, res=res, seed=1, minsz=3.0)
        out[pn] = dict(box=(x0, x1, y0, y1), layers=[(101, cx, cy, bw, bh, 0.0, edge)] + list(L[1:]))
        if progress: progress(n + 1, len(panels))
    return out
def to_plain(car_id, xuid, fits):
    from . import fit
    lay = {p: fit.to_liv_layers(f['layers'], design) for p, f in fits.items()}
    return design.new_design(car_id, lay, xuid)
def render_preview(fitp, sil, res=1.5):
    from . import fit
    x0, x1, y0, y1 = fitp['box']; im = fit.render(fitp['layers'], x0, x1, y0, y1, res=res); W, H = im.size
    m = np.asarray(Image.fromarray(sil.astype(np.uint8) * 255).resize((W, H), Image.NEAREST)) > 127
    a = np.asarray(im).copy(); bgc = np.array([34, 36, 42], dtype=np.uint8); a[~m] = bgc
    buf = io.BytesIO(); Image.fromarray(a).save(buf, 'PNG'); return buf.getvalue()
def render_rgba(fitp, sil, res=1.5):
    """RGBA panel texture (transparent where nothing is painted or outside the silhouette) for the 3D viewer"""
    from . import fit
    x0, x1, y0, y1 = fitp['box']; im = fit.render_rgba(fitp['layers'], x0, x1, y0, y1, res=res); W, H = im.size
    m = np.asarray(Image.fromarray(sil.astype(np.uint8) * 255).resize((W, H), Image.NEAREST)) > 127
    a = np.asarray(im).copy(); a[~m, 3] = 0
    buf = io.BytesIO(); Image.fromarray(a, 'RGBA').save(buf, 'PNG'); return buf.getvalue()
_MODEL_CACHE = {}
def model_for_zip(zip_path):
    """3D model + panel projection for a car zip (cached by path+mtime)."""
    key = (zip_path, os.path.getmtime(zip_path))
    if key in _MODEL_CACHE: return _MODEL_CACHE[key]
    from . import carbin_mesh, fzip
    cands = [n for n in fzip.names(zip_path) if n.lower().endswith('.carbin') and not any(k in n.lower() for k in ('lod0', 'cockpit', 'caliper', 'rotor'))]
    if not cands: raise AppError('no body model in that car zip')
    body = min(cands, key=len)
    want = {body, 'physics/maxdata.xml'}
    atl = [n for n in ('nodamage_lod0.xds', 'nodamage.xds') if n in set(fzip.names(zip_path))]
    f = fzip.read_files(zip_path, lambda n: n in want or n.startswith('liverymasks/') or (atl and n == atl[0]))
    mk = masks.load_masks(f)
    model, pos, idx = carbin_mesh.build_model(f[body], f.get('physics/maxdata.xml', b''))
    model['proj'] = carbin_mesh.fit_projection(pos, idx, model['parts'], mk)
    if atl and atl[0] in f:
        try:
            from . import xds
            im = xds.decode(f[atl[0]])
            rgb, alpha = im.convert('RGB'), im.getchannel('A')      # resize separately: RGBA resampling premultiplies and wipes RGB under alpha 0
            if im.width > 1024: rgb, alpha = rgb.resize((1024, 1024), Image.LANCZOS), alpha.resize((1024, 1024), Image.LANCZOS)
            enc = lambda i: base64.b64encode((lambda b: (i.save(b, 'PNG'), b.getvalue())[1])(io.BytesIO())).decode()
            model['atlas'] = enc(rgb); model['atlas_a'] = enc(alpha)   # separate: browsers drop RGB under alpha 0
        except Exception as e:
            model['atlas_error'] = str(e)
    _MODEL_CACHE.clear(); _MODEL_CACHE[key] = model; return model
def write_liv(c, g, slot, plain, assign=True):
    """returns list of human-readable lines"""
    msgs = []; p = liv_path(c, slot); os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p):
        b = p + '.bak_' + time.strftime('%Y%m%d_%H%M%S'); shutil.copy2(p, b); msgs.append('backed up old livery: ' + os.path.basename(b))
    open(p, 'wb').write(crypto.encrypt_liv(plain, c['pe'], c['xuid'], 'design'))
    row = car_row(g, c, slot)
    if assign and not row['livery']:
        garage.assign(g, slot); b = garage.save(g); msgs.append('slot had no livery: assigned %s; PlayerDatabase backup: %s' % (garage.livery_path(slot), os.path.basename(b)))
    msgs.append('wrote ' + p); return msgs
def backups(c):
    out = []
    ld = os.path.join(c['profile'], 'Liveries')
    if os.path.isdir(ld): out += [os.path.join(ld, f) for f in sorted(os.listdir(ld)) if '.bak_' in f]
    out += [os.path.join(c['profile'], f) for f in sorted(os.listdir(c['profile'])) if f.startswith('PlayerDatabase.bak_')]
    return out
def restore(c, path):
    path = os.path.abspath(path); prof = os.path.abspath(c['profile'])
    if not path.startswith(prof) or '.bak_' not in os.path.basename(path): raise AppError('not a backup of this profile')
    target = path.split('.bak_')[0]; keep = target + '.bak_' + time.strftime('%Y%m%d_%H%M%S') + '_before_restore'
    if os.path.exists(target): shutil.copy2(target, keep)
    shutil.copy2(path, target); return target
