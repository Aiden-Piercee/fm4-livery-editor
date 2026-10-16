"""FM4 string tables (.str, 'LSB2'): hash16 -> text. The game database stores text as '_&<u32>'; the low 16 bits are the hash16 inside that
table's .str file (Data_Car.str for Data_Car columns, List_CarMake.str for makes ...). Only the text section is decoded."""
import struct
def parse(raw):
    if raw[:4] != b'LSB2': raise ValueError('not an LSB2 string table')
    h = struct.unpack('>9I', raw[:36]); off = h[5]
    size, count = struct.unpack('>II', raw[off:off + 8]); p = off + 8
    ent = [struct.unpack('>HI', raw[p + 6 * i:p + 6 * i + 6]) for i in range(count + 1)]   # last = 0xFFFF terminator carrying the end offset
    base = p + 6 * (count + 1); out = {}
    for i in range(count):
        a = base + ent[i][1] * 2; b = a
        while b + 1 < len(raw) and raw[b:b + 2] != b'\0\0': b += 2          # offsets count UTF-16 characters; read to the terminator
        out[ent[i][0]] = raw[a:b].decode('utf-16-be', 'replace')
    return out
def resolve(table, ref):
    """'_&3444137817' -> text (or None)"""
    if not isinstance(ref, str) or not ref.startswith('_&'): return None
    try: return table.get(int(ref[2:]) & 0xFFFF)
    except ValueError: return None
