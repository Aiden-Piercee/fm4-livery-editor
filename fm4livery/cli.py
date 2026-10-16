"""fm4livery command line.   python -m fm4livery <command> [options]
  gui                           open the graphical tool (also what run_livery.py does with no arguments)
  info                          find game files and profiles
  garage                        list garage cars and their livery slots
  make --slot N --image FILE    fit an image onto garage car N (writes Liveries\\N.liv, assigns the slot if empty)
  export --slot N --out F       save slot N as a shareable .fm4livery      import --slot N --file F
Common options: --root DIR (where the game / recomp lives; default: current folder)  --profile DIR  --pe FILE  --media DIR"""
import argparse, math, os, shutil, sys, time
from . import app, crypto, design, detect, garage, masks, share, __version__
def ctx(a):
    try: return app.context(a.root, a.pe, a.profile, a.media)
    except app.AppError as e: sys.exit(str(e))
def liv_path(c, slot): return os.path.join(c['profile'], 'Liveries', '%d.liv' % slot)
def car_row(g, c, slot):
    for r in garage.rows(g, c['names'], c.get('titles')):
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
    ap.add_argument('cmd', choices=['gui', 'info', 'garage', 'make', 'export', 'import', 'show'])
    for o in ('--root', '--profile', '--pe', '--media', '--image', '--out', '--file', '--panels', '--fill', '--carzip'): ap.add_argument(o)
    ap.add_argument('--no-window', action='store_true'); ap.add_argument('--slot', type=int); ap.add_argument('--shapes', type=int, default=450); ap.add_argument('--res', type=float, default=2.0)
    a = ap.parse_args(argv)
    if a.cmd == 'gui':
        from . import gui_server; gui_server.run(a.root, no_window=a.no_window); return
    c = ctx(a)
    print('profile %s   default.pe %s   media %s' % (c['xuid'], c['pe_path'], c['media']))
    g = garage.load(c['profile'], c['pe']); print('PlayerDatabase signature', 'OK' if g['ok'] else 'BAD')
    if a.cmd == 'info': return
    if a.cmd == 'garage':
        for r in garage.rows(g, c['names'], c.get('titles')): print('%3d  car %5d  %-26s %s' % (r['garage_id'], r['car_id'], r['car'], r['livery'] or '-'))
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
    zp = a.carzip or (detect.car_zip(c['media'], row['car']) if row['car'] != '?' else None)
    if not zp: sys.exit('cannot find the car zip for car %d (%s) - pass --carzip' % (row['car_id'], row['car']))
    mk = masks.masks_from_zip(zp); img = Image.open(a.image).convert('RGB'); panels = (a.panels or 'left,right').split(',')
    if 'wing' in panels: print('warning: the wing panel only paints about 60% of the blade (from the car-left end); treat it as experimental')
    try: fits = app.fit_panels(img, mk, panels, a.shapes, a.res, a.fill or 'contain')
    except app.AppError as e: sys.exit(str(e))
    for pn, f in fits.items(): print(pn, len(f['layers']), 'layers')
    write_liv(c, g, a.slot, app.to_plain(row['car_id'], c['xuid'], fits))
if __name__ == '__main__': main()
