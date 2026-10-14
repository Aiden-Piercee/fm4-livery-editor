"""fm4livery command line.   python -m fm4livery <command> [options]
  info                          find game files and profiles
  garage                        list garage cars and their livery slots
  make --slot N --image FILE    fit an image onto garage car N (writes Liveries\\N.liv, assigns the slot if empty)
  export --slot N --out F       save slot N as a shareable .fm4livery      import --slot N --file F
Common options: --root DIR (where the game / recomp lives; default: current folder)  --profile DIR  --pe FILE  --media DIR"""
import argparse, math, os, shutil, sys, time
from . import crypto, design, detect, garage, masks, share, __version__
def ctx(a):
    root = a.root or os.getcwd(); pe_path = a.pe or detect.find_pe(root); media = a.media or detect.find_media(root)
    if not pe_path: sys.exit('default.pe not found - pass --pe FILE or --root DIR')
    profs = [a.profile] if a.profile else detect.find_profiles(root)
    if not profs: sys.exit('no profile with a PlayerDatabase found - pass --profile DIR')
    if len(profs) > 1 and not a.profile: sys.exit('several profiles found, pass --profile DIR:\n  ' + '\n  '.join(profs))
    pe = open(pe_path, 'rb').read(); names = detect.car_table(media, [root]) if media else {}
    return dict(pe=pe, pe_path=pe_path, media=media, profile=profs[0], xuid=os.path.basename(profs[0].rstrip('/\\')), names=names)
def liv_path(c, slot): return os.path.join(c['profile'], 'Liveries', '%d.liv' % slot)
def car_row(g, c, slot):
    for r in garage.rows(g, c['names']):
        if r['garage_id'] == slot: return r
    sys.exit('no garage car with Id %d (see: garage)' % slot)
def write_liv(c, g, slot, plain, assign=True):
    p = liv_path(c, slot); os.makedirs(os.path.dirname(p), exist_ok=True)
    if os.path.exists(p): shutil.copy2(p, p + '.bak_' + time.strftime('%Y%m%d_%H%M%S'))
    open(p, 'wb').write(crypto.encrypt_liv(plain, c['pe'], c['xuid'], 'design'))
    row = car_row(g, c, slot)
    if assign and not row['livery']:
        garage.assign(g, slot); print('slot had no livery: assigned %s - saving garage (game must be closed)' % garage.livery_path(slot)); print('backup:', garage.save(g))
    print('wrote', p)
def main(argv=None):
    ap = argparse.ArgumentParser(prog='fm4livery', description='FM4 livery tool ' + __version__)
    ap.add_argument('cmd', choices=['info', 'garage', 'make', 'export', 'import', 'show'])
    for o in ('--root', '--profile', '--pe', '--media', '--image', '--out', '--file', '--panels', '--fill', '--carzip'): ap.add_argument(o)
    ap.add_argument('--slot', type=int); ap.add_argument('--shapes', type=int, default=450); ap.add_argument('--res', type=float, default=2.0)
    a = ap.parse_args(argv); c = ctx(a)
    print('profile %s   default.pe %s   media %s' % (c['xuid'], c['pe_path'], c['media']))
    g = garage.load(c['profile'], c['pe']); print('PlayerDatabase signature', 'OK' if g['ok'] else 'BAD')
    if a.cmd == 'info': return
    if a.cmd == 'garage':
        for r in garage.rows(g, c['names']): print('%3d  car %5d  %-26s %s' % (r['garage_id'], r['car_id'], r['car'], r['livery'] or '-'))
        return
    if a.slot is None: sys.exit('--slot required')
    row = car_row(g, c, a.slot)
    if a.cmd == 'show':
        _, ok, p = crypto.decrypt_liv(open(liv_path(c, a.slot), 'rb').read(), c['pe'], c['xuid']); print('signature', ok, 'car', design.car_id_of(p), [len(x) for x in design.parse(p)['panels']]); return
    if a.cmd == 'export':
        _, ok, p = crypto.decrypt_liv(open(liv_path(c, a.slot), 'rb').read(), c['pe'], c['xuid']); share.export(p, a.out or 'slot%d.fm4livery' % a.slot); print('saved', a.out or 'slot%d.fm4livery' % a.slot); return
    if a.cmd == 'import':
        m = share.load(a.file)
        if m['car_id'] != row['car_id']: print('warning: livery was made for car %d, slot %d is car %d' % (m['car_id'], a.slot, row['car_id']))
        write_liv(c, g, a.slot, share.to_plain(m, row['car_id'], c['xuid'])); return
    # make
    from PIL import Image
    from . import fit
    zp = a.carzip or (detect.car_zip(c['media'], row['car']) if row['car'] != '?' else None)
    if not zp: sys.exit('cannot find the car zip for car %d (%s) - car table missing it' % (row['car_id'], row['car']))
    mk = masks.masks_from_zip(zp); img = Image.open(a.image).convert('RGB')
    import numpy as np
    arr = np.asarray(img).astype(float); e = max(2, min(img.width, img.height) // 25)   # border colour = what surrounds the picture on the car
    edge = np.concatenate([arr[:e].reshape(-1, 3), arr[-e:].reshape(-1, 3), arr[:, :e].reshape(-1, 3), arr[:, -e:].reshape(-1, 3)]).mean(0)
    panels = (a.panels or 'left,right').split(','); lay = {}
    per = max(1, a.shapes // len(panels))
    if 'wing' in panels: print('warning: the wing panel only paints about 60% of the blade (from the car-left end); treat it as experimental')
    for pn in panels:
        if pn not in mk: sys.exit('car has no %s panel (has: %s)' % (pn, ', '.join(mk)))
        x0, x1, y0, y1 = mk[pn]['box']; bw, bh = x1 - x0, y1 - y0; s = min(bw / img.width, bh / img.height) if (a.fill or 'contain') == 'contain' else max(bw / img.width, bh / img.height)
        w, h = img.width * s, img.height * s; cx, cy = (x0 + x1) / 2, (y0 + y1) / 2
        L, *_ = fit.fit(img, cx - w / 2, cx + w / 2, cy - h / 2, cy + h / 2, n_shapes=per, res=a.res, seed=1, minsz=3.0)
        r_, g_, b_ = [int(round(v)) for v in edge]  # panel background = the image's border colour
        lay[pn] = [design.pack_layer(101, x=cx, y=cy, sx=bw / fit.K, sy=bh / fit.K, argb=0xFF000000 | (r_ << 16) | (g_ << 8) | b_)] + fit.to_liv_layers(L[1:], design)
        print(pn, len(lay[pn]), 'layers')
    write_liv(c, g, a.slot, design.new_design(row['car_id'], lay, c['xuid']))
if __name__ == '__main__': main()
