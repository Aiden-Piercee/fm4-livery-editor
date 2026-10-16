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
            try: json.dump(dict(root=root, pe=pe or '', media=media or ''), open(self.SETTINGS, 'w'))
            except OSError: pass
        except Exception as e:
            self.c = None; self.err = str(e)
            if not quiet: raise
        return self.state()
    def state(self):
        c = self.c
        if not c: return dict(ok=False, error=self.err, version=__version__)
        return dict(ok=True, version=__version__, root=c['root'], profile=c['profile'], xuid=c['xuid'], profiles=c['profiles'], media=c['media'], pe=c['pe_path'], cars_known=len(c['names']))
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
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        return app.model_for_zip(app.car_zip_for(c, row, d.get('carzip') or None))
    def bake(self, d):
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        zp = app.car_zip_for(c, row, d.get('carzip') or None)
        return app.bake_atlas(zp, base64.b64decode(d['overlay']), os.path.join(self.exports, 'textures'), bool(d.get('zip', True)))
    def _pk(self, c):
        pr = packs.find_pack_root(c['root'])
        if not pr: raise app.AppError('no 4D530910\\00000002 package folder found under the chosen folder')
        return pr, os.path.join(c['root'], 'fm4livery_backups')
    def install(self, d):
        if not (d.get('confirm') and d.get('gameClosed')): raise app.AppError('installing needs confirmation and the game closed')
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        zp = app.car_zip_for(c, row, d.get('carzip') or None); pr, bk = self._pk(c); car = os.path.splitext(os.path.basename(zp))[0]
        r = app.bake_atlas(zp, base64.b64decode(d['overlay']), os.path.join(self.exports, 'textures'), False)
        tex = {os.path.basename(f): open(f, 'rb').read() for f in r['files']}
        orig = packs.save_originals(car, zp, set(tex), bk)
        b = packs.build(os.path.join(self.exports, 'packs'), car, tex, pr, originals=orig)
        i = packs.install(pr, b, bk); return dict(car=car, folder=b['folder'], dest=i['dest'], parked=i['parked'], backups=bk, files=sorted(tex))
    def uninstall(self, d):
        c = self.need(); pr, bk = self._pk(c); return dict(moved=packs.uninstall(pr, d['folder'], bk), backups=bk)
    def packs_list(self, d=None):
        c = self.need(); pr, bk = self._pk(c); car = None; d = d or {}
        if d.get('slot') is not None:
            g = app.load_garage(c); row = app.car_row(g, c, int(d['slot'])); car = os.path.splitext(os.path.basename(app.car_zip_for(c, row, d.get('carzip') or None)))[0]
        return dict(root=pr, car=car, packs=packs.installed(pr))
    def savefile(self, d):
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
        zp = app.car_zip_for(c, row, d.get('carzip') or None); dd = os.path.join(self.exports, 'templates', os.path.splitext(os.path.basename(zp))[0]); os.makedirs(dd, exist_ok=True)
        name = re.sub(r'[^A-Za-z0-9_.-]', '_', d['name'])[:60]; open(os.path.join(dd, name), 'wb').write(base64.b64decode(d['data'])); return dict(dir=dd)
    def decalfit(self, d):
        c = self.need(); slot = int(d['slot']); g = app.load_garage(c); row = app.car_row(g, c, slot)
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
          'apply': lambda a, d: a.apply(d), 'bake': lambda a, d: a.bake(d), 'savefile': lambda a, d: a.savefile(d), 'install': lambda a, d: a.install(d), 'uninstall': lambda a, d: a.uninstall(d), 'packs': lambda a, d: a.packs_list(d), 'decalfit': lambda a, d: a.decalfit(d), 'export': lambda a, d: a.export(d), 'import': lambda a, d: a.import_(d), 'backups': lambda a, d: a.backups(), 'restore': lambda a, d: a.restore(d)}
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
