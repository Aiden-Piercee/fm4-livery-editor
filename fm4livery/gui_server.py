"""Local GUI backend: a tiny HTTP server on 127.0.0.1 (random port, per-run token) serving the page and a JSON API."""
import base64, io, json, os, re, secrets, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PIL import Image
from . import app, crypto, design, detect, garage, masks, packs, share, vinyls, __version__
from .gui_page import PAGE
class Api:
    def __init__(self, root=None):
        self.c = None; self.err = None; self.fits = {}; self.lock = threading.Lock(); self.exports = os.path.join(os.getcwd(), 'fm4livery_exports')
        self.setup(root or '', None, quiet=True)
    SETTINGS = 'fm4livery_settings.json'
    def _load_settings(self):
        try: return json.load(open(self.SETTINGS))
        except Exception: return {}
    def _save_settings(self, **kw):
        st = self._load_settings(); st.update(kw)
        try: json.dump(st, open(self.SETTINGS, 'w'))
        except OSError: pass
    def prefs(self, d=None):
        d = d or {}
        if 'hide_intro' in d: self._save_settings(hide_intro=bool(d['hide_intro']))
        return dict(hide_intro=bool(self._load_settings().get('hide_intro')))
    def cars(self, d=None):
        c = self.need()
        if not c['media']: raise app.AppError('no Media folder set - the car list needs the folder with cars\\*.zip')
        return dict(rows=app.list_cars(c), names=bool(c['names']))
    def prereqs(self, d=None):
        c = self.c; out = []
        def add(key, label, ok, detail, need): out.append(dict(key=key, label=label, ok=bool(ok), detail=detail, need=need))
        m = c['media'] if c else None; nz = len(app.list_car_zips(c)) if c else 0
        add('media', 'Media folder with car zips', m and nz, (m + ' (%d cars)' % nz) if m and nz else 'not found', 'Texture studio and the 3D view (extracted game files: the Media folder that contains cars\\)')
        add('gamedb', 'Game database', m and os.path.isfile(os.path.join(m, 'db', 'gamedb.slt')), 'Media\\db\\gamedb.slt', 'Real car names and ids (optional - without it cars show their file name)')
        add('strings', 'String tables', m and os.path.isfile(os.path.join(m, 'StringTables', 'EN.zip')), 'Media\\StringTables\\EN.zip', 'Car names in English (optional)')
        add('profile', 'Profile + default.pe', c and c['profile'] and c['pe_path'], (c['profile'] if c and c['profile'] else 'not found'), 'In-game livery section only (garage list, saving liveries to a slot)')
        pr = packs.find_pack_root(c['root'], fast=True) if c else None
        add('packroot', 'Package folder (4D530910\\00000002)', pr, pr or 'not found under the chosen folder', 'Apply to game (install the texture pack) - your recomp folder has it')
        add('template', 'Retail FM4 DLC package', None, 'any official FM4 DLC STFS file; searched when you press Export STFS', 'Export STFS only (header/thumbnail template)')
        return dict(items=out, hide=self.prefs()['hide_intro'])
    def setup(self, root, profile, quiet=False, pe=None, media=None):
        st = self._load_settings()
        if root is None or root == '':
            root = st.get('root') or os.getcwd()
            pe = pe if pe is not None else st.get('pe'); media = media if media is not None else st.get('media')
        pe = (pe or '').strip().strip('"') or None; media = (media or '').strip().strip('"') or None
        try:
            if pe and not os.path.isfile(pe): raise app.AppError('that default.pe path does not exist: ' + pe)
            if media and not os.path.isdir(media): raise app.AppError('that Media folder does not exist: ' + media)
            self.c = app.context(root, pe, profile or None, media); self.err = None
            self._save_settings(root=root, pe=pe or '', media=media or '')
        except Exception as e:
            self.c = None; self.err = str(e)
            if not quiet: raise
        return self.state()
    def state(self):
        c = self.c
        if not c: return dict(ok=False, error=self.err, version=__version__)
        return dict(ok=True, version=__version__, cars_only=not (c['profile'] and c['pe']), root=c['root'], profile=c['profile'], xuid=c['xuid'], profiles=c['profiles'], media=c['media'], pe=c['pe_path'], cars_known=len(c['names']))
    def need(self):
        if not self.c: raise app.AppError(self.err or 'game folder not set')
        return self.c
    def garage(self):
        c = self.need(); g = app.load_garage(c); zips = app.list_car_zips(c)
        return dict(signature=g['ok'], rows=[dict(r, zip=bool(c['media'] and r['car'] != '?' and detect.car_zip(c['media'], r['car'])), file=os.path.exists(app.liv_path(c, r['garage_id']))) for r in garage.rows(g, c['names'], c.get('titles'))], carzips=zips)
    def preview(self, d):
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        zp = app.car_zip_for(c, row, d.get('carzip') or None); mk = masks.masks_from_zip(zp)
        img = Image.open(io.BytesIO(base64.b64decode(d['image']))).convert('RGB'); panels = d.get('panels') or list(app.DEFAULT_PANELS)
        fits = app.fit_panels(img, mk, panels, int(d.get('shapes', 450)), float(d.get('res', 2.0)), d.get('fill', 'contain'))
        pid = uuid.uuid4().hex; self.fits[pid] = dict(slot=slot, car_id=row['car_id'], fits=fits)
        for k in list(self.fits)[:-6]: self.fits.pop(k)
        return dict(id=pid, total_layers=sum(len(f['layers']) for f in fits.values()),
                    panels={p: dict(png=base64.b64encode(app.render_preview(f, mk[p]['sil'])).decode(), tex=base64.b64encode(app.render_rgba(f, mk[p]['sil'])).decode(), layers=len(f['layers'])) for p, f in fits.items()})
    def model(self, d):
        c = self.need(); return app.model_for_zip(self._car(c, d)[0])
    def bake(self, d):
        c = self.need(); zp = self._car(c, d)[0]
        return app.bake_atlas(zp, base64.b64decode(d['overlay']), os.path.join(self.exports, 'textures'), bool(d.get('zip', True)))
    def _pk(self, c):
        pr = packs.find_pack_root(c['root'])
        if not pr: raise app.AppError('no 4D530910\\00000002 package folder found under the chosen folder')
        return pr, os.path.join(c['root'], 'fm4livery_backups')
    def _lib(self, c):
        from . import library
        return library.Library(c['root'])
    def _car(self, c, d):
        zp, car, _ = app.resolve(c, d['slot'], d.get('carzip') or None); return zp, car
    def lib_list(self, d=None):
        c = self.need(); lib = self._lib(c); d = d or {}; car = None
        if d.get('slot') is not None: car = self._car(c, d)[1]
        pr = packs.find_pack_root(c['root']); inst = packs.installed(pr) if pr else []
        legacy = [dict(folder=p['folder'], car=p['car']) for p in inst if p.get('car') and p.get('kind') != 'library']
        live = {}
        for p in inst:
            for k, v in (p.get('cars') or {}).items(): live[k] = v.get('files', {})
        return dict(car=car, entries=lib.entries, legacy=legacy, installed_cars=sorted(live), installed_clones=sorted({k for p in inst for k in (p.get('clones') or {})}), pack_root=pr)
    def lib_save(self, d):
        """bake the overlay for the selected car and keep it in the library (not installed)"""
        c = self.need(); zp, car = self._car(c, d); lib = self._lib(c)
        r = app.bake_atlas(zp, base64.b64decode(d['overlay']), os.path.join(self.exports, 'textures'), False)
        tex = {os.path.basename(f): open(f, 'rb').read() for f in r['files']}
        orig = packs.save_originals(car, zp, set(tex), os.path.join(c['root'], 'fm4livery_backups'))
        name = (d.get('name') or '').strip(); clone = None; ecar = car
        if d.get('clone'):
            if not name: raise app.AppError('give the new car a name first (the name box)')
            if not c['media'] or not os.path.isfile(os.path.join(c['media'], 'db', 'gamedb.slt')): raise app.AppError('cloning needs the game database (Media\\db\\gamedb.slt)')
            from . import clone as CL
            db = CL.open_db(os.path.join(c['media'], 'db', 'gamedb.slt'))
            if CL.donor_id(db, car) is None: raise app.AppError('only base-game cars can be cloned for now (%s is not in the base database)' % car)
            used = CL.used_car_ids(db); db.close()
            try: used |= set(CL.installed_car_ids([self._pk(c)[0]], exclude_dir=os.path.join(self._pk(c)[0], packs.folder_name('library'))))
            except app.AppError: pass
            cid = lib.next_clone_id(used); ecar = '%s_X%d' % (car, cid)
            clone = dict(media=ecar, car_id=cid, donor=car, display=name)
        e = lib.add(ecar, name, tex, orig, activate=bool(d.get('activate', True)), clone=clone); return dict(entry=e, err=r['err'])
    def lib_set(self, d):
        c = self._need_c(); lib = self._lib(c)
        if d.get('deactivate_car'): lib.deactivate_car(d['deactivate_car'])
        if d.get('activate'): lib.set_active(d['activate'])
        if d.get('rename'): lib.rename(d['rename']['id'], d['rename']['name'])
        if d.get('remove'): lib.remove(d['remove'], os.path.join(c['root'], 'fm4livery_backups', '_to_delete'))
        return dict(entries=lib.entries)
    def _need_c(self): return self.need()
    def lib_apply(self, d):
        """rebuild the ONE combined pack from the active library entries and install it (older per-car packs are absorbed and moved out)"""
        if not (d.get('confirm') and d.get('gameClosed')): raise app.AppError('installing needs confirmation and the game closed')
        c = self.need(); pr, bk = self._pk(c); lib = self._lib(c)
        legacy = packs.legacy_entries(pr); absorbed = lib.absorb(legacy); moved = []
        tex, orig, cl = lib.active_split(); folder = packs.folder_name('library'); res = dict(absorbed=[e['name'] for e in absorbed], cars=sorted(tex), clones=[x['display'] for x in cl], backups=bk)
        if tex or cl:
            b = packs.build(os.path.join(self.exports, 'packs'), tex, pr, originals=orig, clones=self._clones(c, cl), media=c['media'], roots=[c['root']], installed_dir=os.path.join(pr, folder)); i = packs.install(pr, b, bk)
            res.update(folder=b['folder'], dest=i['dest'], parked=i['parked'])
        elif folder in [p['folder'] for p in packs.installed(pr)]:
            moved += packs.uninstall(pr, folder, bk)
        for l in legacy:
            if l['folder'] != folder: moved += packs.uninstall(pr, l['folder'], bk)
        res['moved_out'] = moved; return res
    def stfs_export(self, d):
        from . import stfs
        c = self.need(); lib = self._lib(c); pr = packs.find_pack_root(c['root'])
        tpl = d.get('template') or stfs.find_template([c['root'], os.path.dirname(c['media'] or ''), self.exports])
        if not tpl or not stfs.is_template(tpl): raise app.AppError('no retail FM4 DLC package (STFS LIVE file) found to use as the template - type its full path in the template box')
        tex, orig, cl = lib.active_split()
        if pr:
            lg = lib.absorb(packs.legacy_entries(pr))
            if lg: tex, orig, cl = lib.active_split()
        if not tex and not cl: raise app.AppError('the library has no active texture edits - save one and make it active first')
        b = packs.build(os.path.join(self.exports, 'packs'), tex, pr, originals=orig, clones=self._clones(c, cl), media=c['media'], roots=[c['root']], installed_dir=os.path.join(pr, packs.folder_name('library')) if pr else None)
        info = packs.export_stfs(b, tpl, os.path.join(self.exports, 'stfs')); info['template'] = tpl; info['cars'] = sorted(tex) + [x['display'] for x in cl]; return info
    def _clones(self, c, cl):
        out = []
        for x in cl:
            zp = detect.car_zip(c['media'], x['donor']) if c['media'] else None
            if not zp: raise app.AppError('cannot find the donor car zip for ' + x['donor'])
            out.append(dict(x, donor_zip=zp))
        return out
    def savefile(self, d):
        c = self.need(); zp = self._car(c, d)[0]; dd = os.path.join(self.exports, 'templates', os.path.splitext(os.path.basename(zp))[0]); os.makedirs(dd, exist_ok=True)
        name = re.sub(r'[^A-Za-z0-9_.-]', '_', d['name'])[:60]; open(os.path.join(dd, name), 'wb').write(base64.b64decode(d['data'])); return dict(dir=dd)
    def decalfit(self, d):
        c = self.need(); app.need_profile(c); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        zp = app.car_zip_for(c, row, d.get('carzip') or None); mk = masks.masks_from_zip(zp)
        imgs = {p: Image.open(io.BytesIO(base64.b64decode(b))).convert('RGBA') for p, b in d['panels'].items()}
        fits = app.fit_decal_panels(imgs, mk, int(d.get('shapes', 400)), float(d.get('res', 2.0)))
        pid = uuid.uuid4().hex; self.fits[pid] = dict(slot=slot, car_id=row['car_id'], fits=fits)
        return dict(id=pid, total_layers=sum(len(f['layers']) for f in fits.values()))
    def slot(self, d):
        """the livery currently in a slot, decoded to layers per panel (+ shape meshes and mask silhouettes)"""
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        zp = app.car_zip_for(c, row, d.get('carzip') or None); mk = masks.masks_from_zip(zp)
        p = app.liv_path(c, slot); layers = {n: [] for n in design.PANELS}; have = os.path.exists(p)
        if have:
            _, ok, plain = crypto.decrypt_liv(open(p, 'rb').read(), c['pe'], c['xuid'])
            if not ok: raise app.AppError('the livery file did not verify (wrong default.pe or a different profile)')
            dd = design.parse(plain)
            for n, lay in zip(design.PANELS, dd['panels']): layers[n] = [design.unpack_layer(b) for b in lay]
        ids = sorted({l['shape'] for v in layers.values() for l in v})
        shp = vinyls.shapes(c['media'], ids) if c['media'] else {}
        pan = {}
        for n, m in mk.items():
            buf = io.BytesIO(); Image.fromarray(m['sil'].astype('uint8') * 255).save(buf, 'PNG')
            pan[n] = dict(box=list(m['box']), sil=base64.b64encode(buf.getvalue()).decode(), layers=layers.get(n, []))
        return dict(car_id=row['car_id'], have_file=have, panels=pan, shapes={str(k): v for k, v in shp.items()}, missing=[i for i in ids if i not in shp])
    def savelayers(self, d):
        """write edited layers (dicts as returned by 'slot') for the slot: backup, sign, assign. Re-reads the file to verify."""
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        if not row['livery'] and not d.get('game_closed'): return dict(needs_confirm=True, message='This slot has no livery yet. Saving will edit your PlayerDatabase (a backup is made first). Close the game, tick the box, and save again.')
        pan = {n: [design.pack_layer(int(l['shape']), x=float(l['x']), y=float(l['y']), sx=float(l['sx']), sy=float(l['sy']), spin=float(l['spin']), skew=float(l['skew']), argb=int(l['argb']) & 0xFFFFFFFF) for l in lay]
               for n, lay in (d.get('panels') or {}).items() if n in design.PANELS}
        if not any(pan.values()) and not os.path.exists(app.liv_path(c, slot)): raise app.AppError('nothing to save - this slot has no livery and no layers yet')
        if sum(len(v) for v in pan.values()) > 1000: raise app.AppError('more than 1000 layers - the in-game editor will not open it')
        plain = design.new_design(row['car_id'], pan, c['xuid']); msgs = app.write_liv(c, g, slot, plain)
        _, ok, back = crypto.decrypt_liv(open(app.liv_path(c, slot), 'rb').read(), c['pe'], c['xuid'])
        if not ok or [len(x) for x in design.parse(back)['panels']] != [len(pan.get(n, [])) for n in design.PANELS]: raise app.AppError('saved file failed the re-read check - restore from Backups')
        return dict(messages=msgs + ['re-read check passed'])
    def vinylcat(self, d):
        c = self.need()
        if not c['media'] or not os.path.exists(os.path.join(c['media'], 'Livery.zip')): raise app.AppError('Livery.zip not found - set the Media folder in the setup box')
        return dict(items=vinyls.catalogue(c['media']))
    def vinylshapes(self, d):
        c = self.need(); ids = [int(i) for i in d.get('ids', [])][:120]
        return dict(shapes={str(k): v for k, v in vinyls.shapes(c['media'], ids).items()} if c['media'] else {})
    def fitlayers(self, d):
        """the layers of a finished preview as editor layer dicts (nothing is written)"""
        from . import fit
        f = self.fits.get(d['id'])
        if not f: raise app.AppError('preview expired - run Preview again')
        return dict(panels={p: [design.unpack_layer(b) for b in fit.to_liv_layers(fp['layers'], design)] for p, fp in f['fits'].items()})
    def apply(self, d):
        c = self.need(); f = self.fits.get(d['id'])
        if not f: raise app.AppError('preview expired - run Preview again')
        g = app.load_garage(c); row = app.car_row(g, c, f['slot'])
        if not row['livery'] and not d.get('game_closed'): return dict(needs_confirm=True, message='This slot has no livery yet. Applying will edit your PlayerDatabase (a backup is made first). Close the game, tick the box, and apply again.')
        return dict(messages=app.write_liv(c, g, f['slot'], app.to_plain(f['car_id'], c['xuid'], f['fits'])))
    def export(self, d):
        c = self.need(); p = app.liv_path(c, int(d['slot']))
        if not os.path.exists(p): raise app.AppError('that slot has no livery file')
        _, ok, plain = crypto.decrypt_liv(open(p, 'rb').read(), c['pe'], c['xuid']); os.makedirs(self.exports, exist_ok=True)
        out = os.path.join(self.exports, 'slot%s.fm4livery' % d['slot']); share.export(plain, out); return dict(path=out)
    def import_(self, d):
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        if not row['livery'] and not d.get('game_closed'): return dict(needs_confirm=True, message='This slot has no livery yet. Importing will edit your PlayerDatabase (a backup is made first). Close the game, tick the box, and import again.')
        tmp = os.path.join(os.path.dirname(app.liv_path(c, slot)), '_import.tmp'); os.makedirs(os.path.dirname(tmp), exist_ok=True); open(tmp, 'wb').write(base64.b64decode(d['file']))
        try: m = share.load(tmp)
        finally: os.remove(tmp)
        warn = [] if m['car_id'] == row['car_id'] else ['This livery was made for car %d but this slot is car %d.' % (m['car_id'], row['car_id'])]
        return dict(messages=warn + app.write_liv(c, g, slot, share.to_plain(m, row['car_id'], c['xuid'])))
    def backups(self): c = self.need(); return dict(files=[os.path.relpath(p, c['profile']) for p in app.backups(c)])
    def restore(self, d): c = self.need(); return dict(restored=os.path.relpath(app.restore(c, os.path.join(c['profile'], d['file'])), c['profile']))
ROUTES = {'setup': lambda a, d: a.setup(d.get('root') or '', d.get('profile'), pe=d.get('pe'), media=d.get('media')), 'state': lambda a, d: a.state(), 'garage': lambda a, d: a.garage(), 'preview': lambda a, d: a.preview(d), 'model': lambda a, d: a.model(d), 'slot': lambda a, d: a.slot(d), 'savelayers': lambda a, d: a.savelayers(d), 'vinylcat': lambda a, d: a.vinylcat(d), 'fitlayers': lambda a, d: a.fitlayers(d), 'vinylshapes': lambda a, d: a.vinylshapes(d),
          'apply': lambda a, d: a.apply(d), 'bake': lambda a, d: a.bake(d), 'savefile': lambda a, d: a.savefile(d), 'stfs': lambda a, d: a.stfs_export(d), 'liblist': lambda a, d: a.lib_list(d), 'cars': lambda a, d: a.cars(d), 'prereqs': lambda a, d: a.prereqs(d), 'prefs': lambda a, d: a.prefs(d), 'libsave': lambda a, d: a.lib_save(d), 'libset': lambda a, d: a.lib_set(d), 'libapply': lambda a, d: a.lib_apply(d), 'decalfit': lambda a, d: a.decalfit(d), 'export': lambda a, d: a.export(d), 'import': lambda a, d: a.import_(d), 'backups': lambda a, d: a.backups(), 'restore': lambda a, d: a.restore(d)}
def make_server(root=None, port=0):
    api = Api(root); token = secrets.token_urlsafe(16); page = PAGE.replace('__TOKEN__', token).encode('utf-8')
    class H(BaseHTTPRequestHandler):
        def log_message(self, *a): pass
        def _send(self, code, body, ctype='application/json'):
            self.send_response(code); self.send_header('Content-Type', ctype); self.send_header('Content-Length', str(len(body))); self.send_header('Cache-Control', 'no-store'); self.end_headers(); self.wfile.write(body)
        def do_GET(self):
            if self.path.split('?')[0] in ('/', '/index.html'): self._send(200, page, 'text/html; charset=utf-8')
            else: self._send(404, b'{}')
        def do_POST(self):
            if self.headers.get('X-Token') != token or not self.path.startswith('/api/'): return self._send(403, b'{"error":"forbidden"}')
            name = self.path[5:]
            try:
                d = json.loads(self.rfile.read(int(self.headers.get('Content-Length', 0))) or b'{}')
                with api.lock: res = ROUTES[name](api, d)
                self._send(200, json.dumps(res).encode())
            except app.AppError as e: self._send(200, json.dumps(dict(error=str(e))).encode())
            except KeyError as e: self._send(200, json.dumps(dict(error='bad request: missing %s' % e)).encode())
            except Exception as e: self._send(200, json.dumps(dict(error='%s: %s' % (type(e).__name__, e))).encode())
    srv = ThreadingHTTPServer(('127.0.0.1', port), H); return srv, api, token
def run(root=None, no_window=False):
    srv, api, token = make_server(root); url = 'http://127.0.0.1:%d/' % srv.server_address[1]
    threading.Thread(target=srv.serve_forever, daemon=True).start(); print('fm4livery GUI at', url)
    if not no_window:
        try:
            import webview
            class JsApi:
                def pick_file(self):
                    try:
                        r = webview.windows[0].create_file_dialog(getattr(getattr(webview, 'FileDialog', webview), 'OPEN', None) or webview.OPEN_DIALOG)
                        return r[0] if r else None
                    except Exception: return None
                def pick_folder(self):
                    try:
                        r = webview.windows[0].create_file_dialog(getattr(getattr(webview, 'FileDialog', webview), 'FOLDER', None) or webview.FOLDER_DIALOG)
                        return r[0] if r else None
                    except Exception: return None
            webview.create_window('FM4 Livery Tool', url, js_api=JsApi(), width=1280, height=820, min_size=(980, 640)); webview.start(); srv.shutdown(); return
        except Exception as e: print('window not available (%s) - opening your browser instead' % e)
        import webbrowser; webbrowser.open(url)
    try:
        while True: threading.Event().wait(3600)
    except KeyboardInterrupt: srv.shutdown()
