"""Texture library: every texture edit the user keeps, per car, with one active edit per car. The game gets ONE combined pack built
from the active edits (see packs.build); older per-car packs are absorbed into the library and moved out of the game on the next apply."""
import hashlib, json, os, shutil, time
class Library:
    def __init__(self, root):
        self.dir = os.path.join(root, 'fm4livery_library'); self.ix = os.path.join(self.dir, 'library.json'); os.makedirs(self.dir, exist_ok=True)
        try: self.entries = json.load(open(self.ix))['entries']
        except Exception: self.entries = []
    def _save(self):
        tmp = self.ix + '.tmp'; json.dump(dict(entries=self.entries), open(tmp, 'w'), indent=1); os.replace(tmp, self.ix)
    def _dir(self, eid): return os.path.join(self.dir, 'entries', eid)
    def add(self, car, name, tex, originals=None, activate=True, source='editor', clone=None):
        eid = time.strftime('%Y%m%d-%H%M%S') + '-' + hashlib.sha1(os.urandom(8)).hexdigest()[:4]; d = self._dir(eid); os.makedirs(d)
        for n, b in tex.items(): open(os.path.join(d, n), 'wb').write(b)
        e = dict(id=eid, car=car, name=name or 'Edit ' + eid[:13], created=time.strftime('%Y-%m-%d %H:%M:%S'), active=False, source=source,
                 files={n: hashlib.sha256(b).hexdigest() for n, b in tex.items()}, original_sha256=originals or {}, clone=clone)
        self.entries.append(e)
        if activate: self.set_active(eid)
        else: self._save()
        return e
    def get(self, eid):
        for e in self.entries:
            if e['id'] == eid: return e
        raise KeyError('no such library entry')
    def set_active(self, eid):
        e = self.get(eid)
        for x in self.entries:
            if x['car'] == e['car']: x['active'] = (x['id'] == eid)
        self._save()
    def deactivate_car(self, car):
        for x in self.entries:
            if x['car'] == car: x['active'] = False
        self._save()
    def rename(self, eid, name): self.get(eid)['name'] = name; self._save()
    def remove(self, eid, parking):
        """moved into parking (never deleted)"""
        e = self.get(eid); os.makedirs(parking, exist_ok=True); shutil.move(self._dir(eid), os.path.join(parking, eid))
        self.entries = [x for x in self.entries if x['id'] != eid]; self._save()
    def tex(self, eid):
        d = self._dir(eid); return {f: open(os.path.join(d, f), 'rb').read() for f in sorted(os.listdir(d))}
    def active(self):
        """{car: {name: bytes}} + {car: original hashes}"""
        t = {}; o = {}
        for e in self.entries:
            if e['active']: t[e['car']] = self.tex(e['id']); o[e['car']] = e.get('original_sha256', {})
        return t, o
    def next_clone_id(self, used, first=9700):
        taken = set(used) | {e['clone']['car_id'] for e in self.entries if e.get('clone')}; i = first
        while i in taken: i += 1
        return i
    def active_split(self):
        """(overrides {car: tex}, originals {car: hashes}, clones [dict(media, car_id, donor, display, tex)])"""
        t = {}; o = {}; cl = []
        for e in self.entries:
            if not e['active']: continue
            if e.get('clone'): cl.append(dict(e['clone'], tex=self.tex(e['id'])))
            else: t[e['car']] = self.tex(e['id']); o[e['car']] = e.get('original_sha256', {})
        return t, o, cl
    def absorb(self, legacy):
        """import packs from older versions; they become the active edit for their car unless one is already active"""
        got = []
        for l in legacy:
            h = {n: hashlib.sha256(b).hexdigest() for n, b in l['tex'].items()}
            if any(e['car'] == l['car'] and e['files'] == h for e in self.entries): continue
            has = any(e['car'] == l['car'] and e['active'] for e in self.entries)
            got.append(self.add(l['car'], 'Imported ' + (l['created'] or 'earlier install'), l['tex'], activate=not has, source='imported'))
        return got
