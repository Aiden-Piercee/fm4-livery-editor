#!/usr/bin/env python3
"""FM4 livery DESIGN (.liv plaintext) editor - panels + layers.  Pairs with liv_tool.py (crypto).
Plaintext layout (all big-endian unless noted):
  0x00 'crlv' ver=3 ..  u32@0x10 = car ordinal   ...  'lvyg' @0x2d, u32 size @0x29 = 142 + 30*n_layers + (#non-empty panels)
  panels start @0x40, six records, order: 0 front, 1 rear, 2 roof/hood, 3 left, 4 right, 5 wing
  panel = [u32 n][u32 X (=1 if n>0)] + ( 00 pad + n*30-byte layers  if n>0 ) + 15-byte trailer
  the last panel's trailer + the 12 bytes after the panels hold 6 little-endian u32 per-panel layer counts
  (entry k at end-12+4k).
Layer (30 bytes) = shape u16 | spin f32 | posX f32 | posY f32 | sizeX f32 | sizeY f32 | skew f32 | ARGB 4 bytes
"""
import struct
PANELS=('front','rear','roof','left','right','wing')
def pack_layer(shape,x=0,y=0,sx=1,sy=1,spin=0,skew=0,argb=0xFFFFFFFF):
    return struct.pack('>H6fI',shape,spin,x,y,sx,sy,skew,argb)
def unpack_layer(b):
    s,spin,x,y,sx,sy,skew,argb=struct.unpack('>H6fI',b)
    return dict(shape=s,spin=spin,x=x,y=y,sx=sx,sy=sy,skew=skew,argb=argb)
def parse(p):
    o=0x40; panels=[]; trailers=[]
    for k in range(6):
        n,x=struct.unpack('>2I',p[o:o+8]); o+=8; lay=[]
        if n:
            o+=1
            for i in range(n): lay.append(p[o:o+30]); o+=30
        trailers.append(p[o:o+15]); o+=15; panels.append(lay)
    return dict(head=p[:0x40],panels=panels,trailers=trailers,tail=p[o:],end=o)
def build(d):
    panels=d['panels']; out=bytearray(d['head']); n_tot=sum(len(x) for x in panels); ne=sum(1 for x in panels if x)
    struct.pack_into('>I',out,0x29,142+30*n_tot+ne)
    for k in range(6):
        n=len(panels[k]); out+=struct.pack('>2I',n,1 if n else 0)
        if n: out+=b'\x00'+b''.join(panels[k])
        out+=d['trailers'][k]
    # counts table: 6 LE u32 ending 12 bytes after the panels
    end=len(out); out+=d['tail']
    for k in range(6): struct.pack_into('<I',out,end-12+4*k,len(panels[k]))
    return bytes(out)
def clear(d):
    d['panels']=[[] for _ in range(6)]; return d
if __name__=='__main__':
    import sys
    p=open(sys.argv[1],'rb').read(); d=parse(p); print([len(x) for x in d['panels']],'rebuild identical:',build(d)==p)

def new_design(car_id, layers_by_panel=None, xuid=None):
    """empty design for car_id (Data_Car.Id) with optional {panel_name: [packed 30-byte layers]}.
    xuid = creator profile id (16 hex chars); the game ties a design to its creator, so pass the profile's id."""
    from ._template import EMPTY, CREATOR_OFFSET
    raw = bytearray(EMPTY)
    if xuid: raw[CREATOR_OFFSET:CREATOR_OFFSET + 8] = bytes.fromhex(xuid)
    d = parse(bytes(raw)); d['head'] = d['head'][:0x10] + struct.pack('>I', car_id) + d['head'][0x14:]
    for name, lay in (layers_by_panel or {}).items(): d['panels'][PANELS.index(name)] = list(lay)
    return build(d)
def car_id_of(plain): return struct.unpack('>I', plain[0x10:0x14])[0]
