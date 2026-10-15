"""Read Forza zips (store / deflate / method 21 = Xbox LZX). LZX needs the small native helper
(libfzlzx.so on Linux, fzlzx.dll on Windows) if present; otherwise a built-in pure-Python decoder (lzxpy.py, same algorithm) is used.
The helper wraps libmspack's lzxd (LGPL-2.1) - dynamic linking only, source: https://github.com/kyz/libmspack"""
import ctypes, os, struct, sys, zipfile, zlib
_lib = None; _tried = False
def _load():
    """Native helper if one matches this OS, else None (pure-Python decoder is used instead)."""
    global _lib, _tried
    if _tried: return _lib
    _tried = True
    here = os.path.dirname(os.path.abspath(__file__))
    names = ('fzlzx.dll',) if os.name == 'nt' else ('libfzlzx.so',)
    cands = [os.environ.get('FZLZX', '')] + [os.path.join(d, n) for d in (here, os.path.join(here, 'lib'), os.path.dirname(here)) for n in names]
    for c in cands:
        if c and os.path.exists(c):
            try:
                lib = ctypes.CDLL(c)
                lib.fz_lzx_decompress.argtypes = [ctypes.c_char_p, ctypes.c_long, ctypes.c_char_p, ctypes.c_long, ctypes.c_int]
                _lib = lib; break
            except (OSError, AttributeError): continue
    return _lib
def lzx(data, out_len, wbits=17):
    lib = _load()
    if lib is None:
        from . import lzxpy
        return lzxpy.lzx(data, out_len, wbits)
    out = ctypes.create_string_buffer(out_len)
    if lib.fz_lzx_decompress(data, len(data), out, out_len, wbits) != 0: raise ValueError('lzx failed')
    return out.raw
def read_entry(f, info):
    f.seek(info.header_offset); h = f.read(30); nl, el = struct.unpack('<HH', h[26:30])
    f.seek(info.header_offset + 30 + nl + el); d = f.read(info.compress_size); m = info.compress_type
    if m == 0: return d
    if m == 8: return zlib.decompress(d, -15)
    if m == 21:
        last = None
        for wb in (17, 16, 15, 18, 19, 20, 21):
            try: return lzx(d, info.file_size, wb)
            except ValueError as e: last = e
        raise last
    raise ValueError('unsupported zip method %d' % m)
def read_files(zip_path, wanted=None):
    """{name: bytes} for entries whose name passes wanted(name) (default: all)"""
    out = {}
    with open(zip_path, 'rb') as f:
        for i in zipfile.ZipFile(f).infolist():
            if not i.filename.endswith('/') and (wanted is None or wanted(i.filename)): out[i.filename] = read_entry(f, i)
    return out
def names(zip_path): return [i.filename for i in zipfile.ZipFile(zip_path).infolist()]
