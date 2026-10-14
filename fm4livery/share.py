""".fm4livery - shareable livery: a zip with livery.json (car + layers per panel) and optional thumbnail.png. Not encrypted, not profile-bound;
the importing user's tool encrypts it for their own profile."""
import json, zipfile, io
from . import design
def export(plain, path, name='', thumb=None):
    d = design.parse(plain)
    meta = dict(format=1, name=name, car_id=design.car_id_of(plain), panels={design.PANELS[k]: [design.unpack_layer(l) for l in lay] for k, lay in enumerate(d['panels']) if lay})
    with zipfile.ZipFile(path, 'w', zipfile.ZIP_DEFLATED) as z:
        z.writestr('livery.json', json.dumps(meta))
        if thumb: z.writestr('thumbnail.png', thumb)
def load(path):
    m = json.loads(zipfile.ZipFile(path).read('livery.json'))
    if m.get('format') != 1: raise ValueError('unsupported .fm4livery version')
    return m
def to_plain(meta, car_id=None, xuid=None):
    lay = {p: [design.pack_layer(l['shape'], l['x'], l['y'], l['sx'], l['sy'], l['spin'], l['skew'], l['argb']) for l in ls] for p, ls in meta['panels'].items()}
    return design.new_design(car_id if car_id is not None else meta['car_id'], lay, xuid)
