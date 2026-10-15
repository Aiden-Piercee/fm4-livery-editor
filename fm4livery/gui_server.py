"""Local GUI backend: a tiny HTTP server on 127.0.0.1 (random port, per-run token) serving the page and a JSON API."""
import base64, io, json, os, secrets, threading, uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from PIL import Image
from . import app, crypto, design, detect, garage, masks, share, __version__
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
        return dict(signature=g['ok'], rows=[dict(r, zip=bool(c['media'] and r['car'] != '?' and detect.car_zip(c['media'], r['car'])), file=os.path.exists(app.liv_path(c, r['garage_id']))) for r in garage.rows(g, c['names'])], carzips=zips)
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
ROUTES = {'setup': lambda a, d: a.setup(d.get('root') or '', d.get('profile'), pe=d.get('pe'), media=d.get('media')), 'state': lambda a, d: a.state(), 'garage': lambda a, d: a.garage(), 'preview': lambda a, d: a.preview(d), 'model': lambda a, d: a.model(d),
          'apply': lambda a, d: a.apply(d), 'export': lambda a, d: a.export(d), 'import': lambda a, d: a.import_(d), 'backups': lambda a, d: a.backups(), 'restore': lambda a, d: a.restore(d)}
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
