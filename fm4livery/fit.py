#!/usr/bin/env python3
"""img2liv.py - approximate an image with FM4 vinyl layers (square 101 / circle 102 / triangle 103), Geometrize-style.
Calibration (measured in-game, Ford V8 Supercar, 2026-10-14):  pos units: +X right, +Y up (left panel: +X toward the rear).
  size 1.0 ~ K = 124 pos units across the shape's full width (mesh bbox).  Colour = ARGB, alpha FF.
Spin sign / unit (degrees) is an assumption (CCW degrees) pending in-game test - set SPIN_SIGN=-1 to flip.
"""
import numpy as np, struct, math, sys, random
from PIL import Image
K=124.0; SPIN_SIGN=1.0
SQ,CI,TR=101,102,103
def mask(kind,cx,cy,w,h,th,X,Y):
    """boolean mask over grids X,Y (pos units) for a shape centred cx,cy with full width w, height h, rotated th rad CCW"""
    dx=X-cx; dy=Y-cy; c,s=math.cos(th),math.sin(th)
    u=(dx*c+dy*s)/(w/2); v=(-dx*s+dy*c)/(h/2)
    if kind==CI: return u*u+v*v<=1
    if kind==SQ: return (abs(u)<=1)&(abs(v)<=1)
    return (abs(v)<=1)&(abs(u)<=(1-v)/2)
def extent(kind,w,h,th):
    c,s=abs(math.cos(th)),abs(math.sin(th)); return (w*c+h*s)/2,(w*s+h*c)/2
def fit(img,xmin,xmax,ymin,ymax,n_shapes=300,res=3.0,seed=1,minsz=6.0,log=None,allow_rot=True,weight=None):
    """img: PIL RGB. returns list of (kind,cx,cy,w,h,theta,(r,g,b)). First layer = full-canvas rect."""
    rng=random.Random(seed); np.random.seed(seed)
    W=int((xmax-xmin)/res); H=int((ymax-ymin)/res)
    T=np.asarray(img.convert('RGB').resize((W,H),Image.LANCZOS)).astype(np.float64)
    xs=xmin+(np.arange(W)+.5)*res; ys=ymax-(np.arange(H)+.5)*res
    X,Y=np.meshgrid(xs,ys)
    if weight is None: Wt=np.ones((H,W),bool)
    else: Wt=np.asarray(Image.fromarray((np.asarray(weight)>0).astype(np.uint8)*255).resize((W,H),Image.BILINEAR))>127
    bg=T[Wt].mean(0) if Wt.any() else T.reshape(-1,3).mean(0); C=np.ones_like(T)*bg
    layers=[(SQ,(xmin+xmax)/2,(ymin+ymax)/2,xmax-xmin,ymax-ymin,0.0,tuple(bg))]
    def evalc(c):
        kind,cx,cy,w,h,th=c
        ex,ey=extent(kind,w,h,th)
        if cx-ex<xmin or cx+ex>xmax or cy-ey<ymin or cy+ey>ymax: return None
        i0=max(0,int((cx-ex-xmin)/res)-1); i1=min(W,int((cx+ex-xmin)/res)+2)
        j0=max(0,int((ymax-cy-ey)/res)-1); j1=min(H,int((ymax-cy+ey)/res)+2)
        if i1<=i0 or j1<=j0: return None
        m=mask(kind,cx,cy,w,h,th,X[j0:j1,i0:i1],Y[j0:j1,i0:i1])
        m=m&Wt[j0:j1,i0:i1]
        if m.sum()<2: return None
        t=T[j0:j1,i0:i1]; cur=C[j0:j1,i0:i1]
        col=t[m].mean(0)
        d=((t[m]-col)**2).sum()-((t[m]-cur[m])**2).sum()
        return d,col,(j0,j1,i0,i1),m
    def rand_c(frac):
        kind=rng.choice((SQ,CI,TR,CI,SQ))
        big=(xmax-xmin)*0.5*(1-frac)**2+minsz*1.5
        w=rng.uniform(minsz,max(minsz+1,big)); h=w*rng.uniform(0.4,1.6)
        # bias position to high-error pixels
        err=(((T-C)**2).sum(2)*Wt).ravel(); p=err/err.sum() if err.sum()>0 else None
        k=np.random.choice(err.size,p=p); cy_i,cx_i=divmod(k,W)
        cx=xs[cx_i]; cy=ys[cy_i]
        th=rng.uniform(0,2*math.pi) if allow_rot else 0.0
        return [kind,cx,cy,w,h,th]
    for n in range(n_shapes):
        frac=n/n_shapes; best=None
        for _ in range(40):
            c=rand_c(frac); r=evalc(c)
            if r and (best is None or r[0]<best[1][0]): best=(c,r)
        if best is None: continue
        c,r=best
        step=0.25*(1-frac)+0.05
        for _ in range(30):
            c2=list(c); a=rng.choice((1,2,3,4,5)); 
            if a==1: c2[1]+=rng.gauss(0,res*3*step*4)
            elif a==2: c2[2]+=rng.gauss(0,res*3*step*4)
            elif a==3: c2[3]*=math.exp(rng.gauss(0,step)); 
            elif a==4: c2[4]*=math.exp(rng.gauss(0,step))
            else: c2[5]+=rng.gauss(0,step) if allow_rot else 0
            c2[3]=max(c2[3],minsz); c2[4]=max(c2[4],minsz)
            r2=evalc(c2)
            if r2 and r2[0]<r[0]: c,r=c2,r2
        d,col,(j0,j1,i0,i1),m=r
        if d>=0: continue
        C[j0:j1,i0:i1][m]=col
        layers.append((c[0],c[1],c[2],c[3],c[4],c[5],tuple(col)))
        if log and n%50==0: log(n,(((T-C)**2).sum(2)*Wt).sum()/max(Wt.sum(),1))
    return layers,C,T
def to_liv_layers(layers,D):
    out=[]
    for kind,cx,cy,w,h,th,col in layers:
        r,g,b=[int(round(max(0,min(255,v)))) for v in col]
        out.append(D.pack_layer(kind,x=cx,y=cy,sx=w/K,sy=h/K,spin=SPIN_SIGN*math.degrees(th),skew=0,argb=0xFF000000|(r<<16)|(g<<8)|b))
    return out
def render(layers,xmin,xmax,ymin,ymax,res=1.5):
    W=int((xmax-xmin)/res); H=int((ymax-ymin)/res)
    xs=xmin+(np.arange(W)+.5)*res; ys=ymax-(np.arange(H)+.5)*res; X,Y=np.meshgrid(xs,ys)
    C=np.zeros((H,W,3))
    for kind,cx,cy,w,h,th,col in layers: C[mask(kind,cx,cy,w,h,th,X,Y)]=col
    return Image.fromarray(C.clip(0,255).astype(np.uint8))

import xml.etree.ElementTree as ET
def load_masks(xml_path,tga_dir):
    """per-car livery projection: returns {panel: dict(box=(xmin,xmax,ymin,ymax) in pos units, sil=bool array in pos-unit resolution of 1 unit/px, flipY)}"""
    out={}
    for el in ET.parse(xml_path).getroot():
        if el.get('valid')!='true': continue
        g=lambda k: float(el.get(k)); xo,yo=g('xorigin'),g('yorigin')
        box=(g('left')-xo,g('right')-xo,-(g('bottom')-yo),-(g('top')-yo))   # pos Y up: texture rows grow downward
        a=np.asarray(Image.open('%s/%s.tga'%(tga_dir,el.tag.lower())).convert('RGBA'))[...,3]>128
        ys,xs=np.where(a); 
        sil=a[ys.min():ys.max()+1, xs.min():xs.max()+1]      # bbox of the silhouette == the box (row0 = highest pos Y)
        w=int(round(box[1]-box[0])); h=int(round(box[3]-box[2]))
        sil=np.asarray(Image.fromarray(sil.astype(np.uint8)*255).resize((w,h),Image.NEAREST))>127
        if g('rotation')==180: sil=sil[::-1,::-1]
        out[el.tag.lower()]=dict(box=box,sil=sil,rotation=g('rotation'),xaxis=el.get('xAxis'),yaxis=el.get('yAxis'))
    return out
