# Pure-Python LZX decoder (port of the libmspack lzxd logic) - used when the native helper is unavailable.
import struct
_EXTRA = []; _BASE = []
def _init_tables():
    j = 0
    for i in range(0, 37, 2):
        _EXTRA.append(j); _EXTRA.append(j)
        if i != 0 and j < 17: j += 1
    j = 0
    for e in _EXTRA:
        _BASE.append(j); j += 1 << e
_init_tables()

def _build(lens, n):
    """canonical Huffman -> (table, maxbits); table[peek] = (sym<<5)|len ; None entries = invalid"""
    mx = max(lens[:n]) if n else 0
    if mx == 0: return ([0] * 2, 1)
    table = [0] * (1 << mx)
    code = 0
    for ln in range(1, mx + 1):
        for s in range(n):
            if lens[s] == ln:
                lo = code << (mx - ln); cnt = 1 << (mx - ln)
                if lo + cnt > len(table): raise ValueError('lzx: bad huffman tree')
                table[lo:lo + cnt] = [(s << 5) | ln] * cnt
                code += 1
        code <<= 1
    return (table, mx)

def lzx(data, out_len, wbits=17):
    # strip XMemCompress chunk headers
    o = 0; pay = bytearray(); L = len(data)
    while o + 1 < L:
        if data[o] == 0xFF:
            if o + 4 >= L: break
            sz = (data[o + 3] << 8) | data[o + 4]; hdr = 5
        else:
            sz = (data[o] << 8) | data[o + 1]; hdr = 2
        if sz == 0 or o + hdr + sz > L: break
        pay += data[o + hdr:o + hdr + sz]; o += hdr + sz
    if len(pay) & 1: pay.append(0)
    pay += b'\0' * 8
    try:
        return _decode(bytes(pay), out_len, wbits)
    except (IndexError, struct.error) as e:
        raise ValueError('lzx: ' + repr(e))

def _decode(inp, out_len, wbits):
    if wbits < 15 or wbits > 21: raise ValueError('lzx: window bits')
    wsize = 1 << wbits
    nslots = 50 if wbits == 21 else 42 if wbits == 20 else wbits << 1
    main_n = 256 + (nslots << 3)
    out = bytearray(out_len); pos = 0
    ip = 0; bb = 0; bl = 0
    R0 = R1 = R2 = 1
    main_lens = [0] * main_n; len_lens = [0] * 249
    header_read = 0; intel = 0; intel_size = 0
    btype = 0; bremain = 0; frame = 0
    overrun = 0; overrun_off = 0
    mtab = ltab = atab = None

    def ensure(n):
        nonlocal bb, bl, ip
        while bl < n:
            bb = (bb << 16) | (inp[ip] | (inp[ip + 1] << 8)); ip += 2; bl += 16
    def bits(n):
        nonlocal bb, bl
        if n == 0: return 0
        ensure(n)
        bl -= n; v = bb >> bl; bb &= (1 << bl) - 1
        return v
    def sym(t):
        nonlocal bb, bl
        table, mx = t
        ensure(mx)
        e = table[(bb >> (bl - mx)) & ((1 << mx) - 1)]
        ln = e & 31
        if ln == 0: raise ValueError('lzx: bad code')
        bl -= ln; bb &= (1 << bl) - 1
        return e >> 5
    def read_lens(lens, first, last):
        pl = [bits(4) for _ in range(20)]
        pt = _build(pl, 20)
        x = first
        while x < last:
            z = sym(pt)
            if z == 17:
                y = bits(4) + 4
                for _ in range(y): lens[x] = 0; x += 1
            elif z == 18:
                y = bits(5) + 20
                for _ in range(y): lens[x] = 0; x += 1
            elif z == 19:
                y = bits(1) + 4
                z = sym(pt); z = lens[x] - z
                if z < 0: z += 17
                for _ in range(y): lens[x] = z; x += 1
            else:
                z = lens[x] - z
                if z < 0: z += 17
                lens[x] = z; x += 1
            if x > last: raise ValueError('lzx: lens overrun')

    while pos < out_len:
        fsize = min(32768, out_len - pos)
        fstart = pos; fend = pos + fsize
        # carry-over of a match that crossed the previous frame boundary
        while overrun and pos < fend:
            n = min(overrun, fend - pos)
            for _ in range(n):
                out[pos] = out[pos - overrun_off]; pos += 1
            overrun -= n; bremain -= n
        while pos < fend:
            if bremain == 0:
                if btype == 3 and (blen_total & 1): ip += 1
                if not header_read:
                    if bits(1):
                        intel_size = (bits(16) << 16) | bits(16)
                    header_read = 1
                btype = bits(3)
                blen_total = (bits(16) << 8) | bits(8); bremain = blen_total
                if btype in (1, 2):
                    if btype == 2:
                        al = [bits(3) for _ in range(8)]; atab = _build(al, 8)
                    read_lens(main_lens, 0, 256); read_lens(main_lens, 256, main_n)
                    mtab = _build(main_lens, main_n)
                    if main_lens[0xE8]: intel = 1
                    read_lens(len_lens, 0, 249); ltab = _build(len_lens, 249)
                elif btype == 3:
                    intel = 1
                    if bl == 0: ip += 2
                    else:
                        d = (bl & 15) or 16; ip -= ((bl - d) // 16) * 2
                    bl = 0; bb = 0
                    R0, R1, R2 = struct.unpack_from('<III', inp, ip); ip += 12
                else:
                    raise ValueError('lzx: bad block type')
            run = min(bremain, fend - pos)
            if btype == 3:
                out[pos:pos + run] = inp[ip:ip + run]; ip += run; pos += run; bremain -= run
                continue
            target = pos + run
            while pos < target:
                m = sym(mtab)
                if m < 256:
                    out[pos] = m; pos += 1; bremain -= 1; continue
                m -= 256
                ml = m & 7
                if ml == 7: ml += sym(ltab)
                ml += 2
                mo = m >> 3
                if mo > 2:
                    ex = _EXTRA[mo]; off = _BASE[mo] - 2
                    if btype == 2 and ex >= 3:
                        if ex > 3: off += bits(ex - 3) << 3
                        off += sym(atab)
                    elif ex > 0: off += bits(ex)
                    else: off = 1
                    R2 = R1; R1 = R0; R0 = off
                elif mo == 0: off = R0
                elif mo == 1: off = R1; R1 = R0; R0 = off
                else: off = R2; R2 = R0; R0 = off
                if off > pos or off > wsize: raise ValueError('lzx: bad offset')
                n = min(ml, target - pos) if False else min(ml, fend - pos)
                src = pos - off
                if off >= n: out[pos:pos + n] = out[src:src + n]
                else:
                    for k in range(n): out[pos + k] = out[src + k]
                pos += n; bremain -= n
                if n < ml: overrun = ml - n; overrun_off = off; target = pos  # crossed frame end
                if pos >= fend: break
            if pos >= fend: break
        # frame end: realign bit stream
        if bl > 0:
            ensure(16)
            d = bl & 15
            if d: bl -= d; bb &= (1 << bl) - 1
        if intel and intel_size and frame < 32768 and fsize > 10:
            _e8(out, fstart, fsize, frame * 32768, intel_size)
        frame += 1
    return bytes(out)

def _e8(buf, start, size, cur, fsize):
    i = 0; end = size - 10
    while i < end:
        if buf[start + i] != 0xE8: i += 1; continue
        a = struct.unpack_from('<i', buf, start + i + 1)[0]
        cp = cur + i
        if -cp <= a < fsize:
            v = a - cp if a >= 0 else a + fsize
            struct.pack_into('<i', buf, start + i + 1, v)
        i += 5
