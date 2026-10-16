"""Shared logic for the CLI and the GUI: find the game/profile, fit an image onto panels, build and write designs."""
import base64, io, os, re, shutil, time, zipfile
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
    try: titles = detect.car_titles(media, [root]) if media else {}
    except Exception: titles = {}
    return dict(root=root, pe=open(pe_path, 'rb').read(), pe_path=pe_path, media=media, profile=profs[0], profiles=profs,
                xuid=os.path.basename(profs[0].rstrip('/\\')), names=names, titles=titles)
def liv_path(c, slot): return os.path.join(c['profile'], 'Liveries', '%d.liv' % slot)
def load_garage(c): return garage.load(c['profile'], c['pe'])
def car_row(g, c, slot):
    for r in garage.rows(g, c['names'], c.get('titles')):
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

def bake_atlas(zip_path, overlay_png, out_dir, make_zip=True):
    """Composite an RGBA overlay onto the car's baked-livery atlases and write new .xds files (+ a stored-entry copy of the car zip).
    BUILD ONLY: writes into out_dir, never into the game. Overlay alpha a: rgb = base*(1-a)+overlay*a, atlas alpha = base*(1-a)+255*a (255 = texture overrides paint)."""
    from . import fzip, xds, xdswrite
    names = fzip.names(zip_path); targets = [n for n in ('nodamage.xds', 'nodamage_lod0.xds') if n in set(names)]
    if not targets: raise AppError('this car has no baked-livery texture (nodamage.xds)')
    ov = Image.open(io.BytesIO(overlay_png)).convert('RGBA')
    files = fzip.read_files(zip_path) if make_zip else fzip.read_files(zip_path, lambda n: n in targets)
    d = os.path.join(out_dir, os.path.splitext(os.path.basename(zip_path))[0]); os.makedirs(d, exist_ok=True)
    new = {}; written = []; worst = 0.0
    for n in targets:
        raw = files[n]; base = np.asarray(xds.decode(raw)).astype(np.float32); h, w = base.shape[:2]
        o = np.asarray(ov if ov.size == (w, h) else ov.resize((w, h), Image.LANCZOS)).astype(np.float32); a = o[..., 3:4] / 255.0
        out = np.empty_like(base); out[..., :3] = base[..., :3] * (1 - a) + o[..., :3] * a; out[..., 3:4] = base[..., 3:4] * (1 - a) + 255.0 * a
        out = np.clip(out + 0.5, 0, 255).astype(np.uint8); data = xdswrite.build(raw, out)
        back = np.asarray(xds.decode(data)).astype(np.float32); err = float(np.abs(back[..., :3] - out[..., :3]).mean()); worst = max(worst, err)
        if err > 6 or len(data) != len(raw): raise AppError('internal check failed for %s (error %.1f)' % (n, err))
        new[n] = data; p = os.path.join(d, n); open(p, 'wb').write(data); written.append(p)
    zp = None
    if make_zip:
        zp = os.path.join(d, os.path.basename(zip_path))
        with zipfile.ZipFile(zp, 'w', zipfile.ZIP_STORED) as z:
            for n in names:
                if n.endswith('/'): continue
                z.writestr(n, new.get(n, files[n]))
    return dict(dir=d, files=written, zip=zp, err=worst)
def fit_decal_panels(imgs, mk, shapes=400, res=2.0):
    """imgs {panel: RGBA PIL image covering exactly the panel box}. Only opaque pixels are fitted; no background layer is added."""
    from . import fit
    per = max(1, shapes // max(1, len(imgs))); out = {}
    for pn, im in imgs.items():
        if pn not in mk: raise AppError('this car has no %s panel' % pn)
        a = np.asarray(im.convert('RGBA'))[..., 3]
        if int((a > 127).sum()) < 20: continue
        x0, x1, y0, y1 = mk[pn]['box']
        L, *_ = fit.fit(im.convert('RGB'), x0, x1, y0, y1, n_shapes=per, res=res, seed=1, minsz=3.0, weight=a)
        out[pn] = dict(box=(x0, x1, y0, y1), layers=list(L[1:]))
    if not out: raise AppError('no decals landed on a livery panel')
    return out
