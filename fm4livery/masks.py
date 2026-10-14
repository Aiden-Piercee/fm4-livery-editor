"""Per-car livery placement maps: <car zip>/liverymasks/masks.xml + 1024x1024 RGBA silhouettes (left/right/front/back/top/wing .tga).
Returns, per valid panel, the box in livery 'pos units' and a 1-unit-per-pixel boolean silhouette (True = paintable)."""
import io, xml.etree.ElementTree as ET
import numpy as np
from PIL import Image
PANEL_OF = {'front': 'front', 'back': 'rear', 'top': 'roof', 'left': 'left', 'right': 'right', 'wing': 'wing'}
def load_masks(files):
    """files: {'liverymasks/masks.xml': bytes, 'liverymasks/left.tga': bytes, ...}"""
    out = {}
    for el in ET.fromstring(files['liverymasks/masks.xml']):
        if el.get('valid') != 'true': continue
        g = lambda k: float(el.get(k)); xo, yo = g('xorigin'), g('yorigin')
        box = (g('left') - xo, g('right') - xo, -(g('bottom') - yo), -(g('top') - yo))  # xmin, xmax, ymin, ymax (pos Y is up)
        tga = files.get('liverymasks/%s.tga' % el.tag.lower())
        if tga is None: continue
        a = np.asarray(Image.open(io.BytesIO(tga)).convert('RGBA'))[..., 3] > 128; ys, xs = np.where(a)
        if not len(ys): continue
        sil = a[ys.min():ys.max() + 1, xs.min():xs.max() + 1]; w = int(round(box[1] - box[0])); h = int(round(box[3] - box[2]))
        sil = np.asarray(Image.fromarray(sil.astype(np.uint8) * 255).resize((w, h), Image.NEAREST)) > 127
        if g('rotation') == 180: sil = sil[::-1, ::-1]
        out[PANEL_OF.get(el.tag.lower(), el.tag.lower())] = dict(box=box, sil=sil, rotation=g('rotation'), xaxis=el.get('xAxis'), yaxis=el.get('yAxis'))
    return out
def masks_from_zip(zip_path):
    from .fzip import read_files
    return load_masks(read_files(zip_path, lambda n: n.startswith('liverymasks/')))
