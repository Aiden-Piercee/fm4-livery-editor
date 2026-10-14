"""Livery (.liv/.lvg) and PlayerDatabase containers. Base keys are read from the user's own default.pe at runtime;
nothing from the game is bundled. key[i] = base[i] ^ creator[(i+idx)&7], creator = 8-byte profile XUID."""
import struct, hmac, hashlib, zlib
from cryptography.hazmat.primitives.ciphers import Cipher, algorithms, modes
# kind -> (aes_offset, aes_idx, sha_offset, sha_idx) in default.pe
KINDS = {'design': (0xEC80, 5, 0xEC60, 1), 'group': (0x1D0C4, 2, 0x1D0A4, 7), 'db': (0xEC50, 3, 0xEC30, 2)}
def keys(pe, xuid, kind):
    ao, ai, so, si = KINDS[kind]; cr = bytes.fromhex(xuid)
    sk = lambda b, i: bytes(b[j] ^ cr[(j + i) & 7] for j in range(len(b)))
    return sk(pe[ao:ao + 16], ai), sk(pe[so:so + 32], si)
def _hdr(L): return struct.pack('>5I', L, 0xBBBBBBBB, 0xBBBBBBBB, 0xBBBBBBBB, 0xBBBBBBBB)
def decrypt_liv(raw, pe, xuid):
    """-> (kind, signature_ok, plaintext). Tries the design key, then the group key."""
    hdr = raw[0x20:0x34]; u = struct.unpack('>5I', hdr); L = u[0] ^ u[1] ^ u[2] ^ u[3] ^ u[4]
    for kind in ('design', 'group'):
        a, s = keys(pe, xuid, kind)
        p = (Cipher(algorithms.AES(a), modes.CBC(raw[0x24:0x34])).decryptor().update(raw[0x34:]))[:L]
        if p[:4] == (b'crlv' if kind == 'design' else b'lvyg'):
            return kind, hmac.new(s, hdr + raw[0x34:], hashlib.sha256).digest() == raw[:0x20], p
    raise ValueError('cannot decrypt: wrong profile ID, or not a livery file')
def encrypt_liv(plain, pe, xuid, kind='design'):
    L = len(plain); data = plain + b'\xbb' * ((-L) % 16); a, s = keys(pe, xuid, kind); hdr = _hdr(L)
    e = Cipher(algorithms.AES(a), modes.CBC(hdr[4:20])).encryptor(); ct = e.update(data) + e.finalize()
    return hmac.new(s, hdr + ct, hashlib.sha256).digest() + hdr + ct
def read_db(raw, pe, xuid):
    """PlayerDatabase ('cmss') -> (sqlite bytes, signature_ok)"""
    if raw[:4] != b'cmss': raise ValueError('not a PlayerDatabase')
    n = struct.unpack('>I', raw[4:8])[0]; aes, sha = keys(pe, xuid, 'db')
    stored, hdr, ct = raw[8:0x28], raw[0x28:0x3c], raw[0x3c:8 + n]
    ok = hmac.new(sha, raw[0x28:8 + n], hashlib.sha256).digest() == stored
    u = struct.unpack('>5I', hdr); real = u[0] ^ u[1] ^ u[2] ^ u[3] ^ u[4]
    pl = Cipher(algorithms.AES(aes), modes.CBC(hdr[4:20])).decryptor().update(ct)[:real]
    tot = struct.unpack('>I', pl[:4])[0]; o = 4; out = b''
    while len(out) < tot:
        c, r = struct.unpack('>2I', pl[o:o + 8]); o += 8; out += zlib.decompress(pl[o:o + c], -15); o += c
    return out, ok
def write_db(raw_old, sqlite_bytes, pe, xuid):
    """new PlayerDatabase bytes, same length as raw_old (the block must fit the preallocated file)"""
    aes, sha = keys(pe, xuid, 'db'); body = struct.pack('>I', len(sqlite_bytes)); pos = 0
    while pos < len(sqlite_bytes):
        ch = sqlite_bytes[pos:pos + 0x200000]; co = zlib.compressobj(9, zlib.DEFLATED, -15); comp = co.compress(ch) + co.flush()
        body += struct.pack('>2I', len(comp), len(ch)) + comp; pos += len(ch)
    L = len(body); data = body + b'\xbb' * ((-L) % 16); hdr = _hdr(L)
    e = Cipher(algorithms.AES(aes), modes.CBC(hdr[4:20])).encryptor(); ct = e.update(data) + e.finalize()
    blk = hmac.new(sha, hdr + ct, hashlib.sha256).digest() + hdr + ct
    out = b'cmss' + struct.pack('>I', len(blk)) + blk
    if len(out) > len(raw_old): raise ValueError('new database does not fit the preallocated file')
    return out + raw_old[len(out):]
