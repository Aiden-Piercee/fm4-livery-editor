"""Decal tools: (1) Sheet tab = paint on the car's baked-livery texture atlas (flat); (2) 3D view locked to Left/Right/Top/Front/Rear
with drag-and-drop images / SVGs that are baked into the atlas through the car's UVs. HTML + CSS + JS fragments for the GUI page."""

CSS = r'''
#t_sheet{display:flex;flex-direction:column;gap:10px}
.shwrap{position:relative;height:min(66vh,700px);min-height:380px;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#0d0f13}
.shwrap canvas{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none}
.shwrap.drop,.vwrap.drop{outline:2px dashed var(--accent);outline-offset:-6px}
.dwrap{display:grid;grid-template-columns:minmax(180px,1fr) minmax(220px,1.3fr);gap:12px}
.dlist{max-height:170px;overflow:auto;border:1px solid var(--line);border-radius:7px;background:var(--bg);padding:4px}
.drow{display:flex;align-items:center;gap:6px;padding:3px 6px;border-radius:5px;cursor:pointer;font-size:12px}
.drow:hover{background:var(--panel2)}.drow.sel{background:#223a57}.drow .nm{flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap}
.drow img{width:22px;height:22px;object-fit:contain;background:#555;border-radius:3px}
.dprops button{padding:4px 9px;font-size:12px;margin:2px 4px 2px 0}
.dprops label{margin:6px 0 2px}
@media(max-width:900px){.dwrap{grid-template-columns:1fr}}
'''

HTML = r'''
   <div id="t_sheet" class="hide">
     <div class="vbar">
       <button class="sec" id="shAdd">Add image / SVG…</button><input type="file" id="shFile" accept="image/*,.svg" multiple style="display:none">
       <button class="sec" id="shFull" title="A texture you painted in another program (same layout as the sheet) - lays over the whole atlas">Add painted sheet…</button><input type="file" id="shFullFile" accept="image/*" style="display:none">
       <span class="sep"></span>
       <button class="sec on" id="shUV">UV outlines</button><button class="sec" id="shAlpha">Show alpha</button><button class="sec" id="shReset">Reset zoom</button>
       <span class="sep"></span>
       <button id="shExport" title="Builds the edited .xds files and a copy of the car zip in the output folder. Nothing is installed.">Build texture files</button>
       <input id="shName" placeholder="name this edit" style="width:140px">
       <label class="chk" title="Saves the edit as its OWN new car (new database row, name and media copy) so it can exist next to the original and other edits"><input type="checkbox" id="shClone">as new car</label>
       <button id="shSave" title="Keeps this edit in your texture library for the selected car. Nothing is installed until you press Apply in the Library tab.">Save to library</button>
       <button class="sec" id="shTemplate">Save atlas + UV template</button>
       <span class="note" id="shStatus" style="margin-left:auto"></span>
     </div>
     <div class="shwrap" id="shWrap"><canvas id="shCv"></canvas><div class="vhint">drop images / SVGs here &middot; wheel zoom &middot; drag empty space to pan &middot; drag a picture to move, corner = size, top knob = rotate</div></div>
     <div id="shPanel"></div>
     <p class="note">Everything you place here (and everything placed in the 3D view) is combined into the car's <b>baked-livery texture</b>. The 3D view shows it live. Use the UV outlines to see which part of the sheet is which panel. These changes go into texture files (<code>nodamage.xds</code>) in an output folder - they are not the garage <code>.liv</code> livery.</p>
   </div>

   <div id="t_lib" class="hide">
     <h2>Texture library</h2>
     <p class="note">Every texture edit you save is kept here, per car. Choose which edit is <b>active</b> for each car (or <b>original</b> for none), then <b>Apply</b>: the game gets ONE combined pack built from the active edits. Earlier per-car packs are absorbed here automatically. The original car files are never changed.</p>
     <div id="libList" class="note">...</div>
     <div class="row" style="margin-top:12px;align-items:end">
       <div style="flex:0 0 auto"><button id="libApply">Apply to game</button></div>
       <div style="flex:0 0 auto"><button class="sec" id="libRefresh">Refresh</button></div>
       <div><label>STFS template <span class="note">(a retail FM4 DLC package; blank = search)</span></label><input id="shTpl" placeholder="optional full path"></div>
       <div style="flex:0 0 auto"><button class="sec" id="libStfs" title="Wraps the combined pack as an STFS package for Xenia Install Content / modded consoles. The signature is NOT re-created.">Export STFS</button></div>
     </div>
     <p class="note" id="libNote"></p>
   </div>
'''

BAR3 = r'''<span class="note">Lock to:</span>'''

JS = r'''
const D=(()=>{
const VIEWS={left:{f:[1,0,0],r:[0,0,1],u:[0,1,0]},right:{f:[-1,0,0],r:[0,0,-1],u:[0,1,0]},front:{f:[0,0,1],r:[-1,0,0],u:[0,1,0]},rear:{f:[0,0,-1],r:[1,0,0],u:[0,1,0]},top:{f:[0,-1,0],r:[1,0,0],u:[0,0,-1]}};
const VPANEL={left:'left',right:'right',front:'front',rear:'rear',top:'roof'};
const A={base:null,baseA:null,dec3:[],sheet:[],sel3:null,selS:null,ver3:0,bk:null,pending3:false,showUV:true,showAlpha:false,wire:null,hasAtlas:false};
let nextId=1;
const cvs=(w,h)=>{const c=document.createElement('canvas');c.width=w;c.height=h||w;return c};
const el=(t,c,x)=>{const e=document.createElement(t);if(c)e.className=c;if(x!=null)e.textContent=x;return e};
const clamp=(v,a,b)=>Math.max(a,Math.min(b,v));
const asp=L=>L.canvas.height/L.canvas.width;
function mkLayer(o){return Object.assign({id:nextId++,x:0,y:0,w:.25,rot:0,fx:false,fy:false,op:1,name:'',view:null},o)}
function toCanvas(img,max){const w0=img.naturalWidth||img.width,h0=img.naturalHeight||img.height;const s=Math.min(1,max/Math.max(w0,h0));const c=cvs(Math.max(1,Math.round(w0*s)),Math.max(1,Math.round(h0*s)));c.getContext('2d').drawImage(img,0,0,c.width,c.height);return c}
function loadFile(file){return new Promise((res,rej)=>{const name=file.name||'image';
 if(/svg/i.test(file.type)||/\.svg$/i.test(name)){file.text().then(t=>{const m=t.match(/<svg[^>]*>/i);
   if(m){const tag=m[0];const vb=tag.match(/viewBox\s*=\s*["']([^"']+)["']/i);const noSize=!/\swidth\s*=\s*["'][0-9.]+(px)?["']/i.test(tag)||!/\sheight\s*=\s*["'][0-9.]+(px)?["']/i.test(tag);
    let t2=tag;if(vb&&noSize){const p=vb[1].trim().split(/[\s,]+/).map(Number);if(p.length===4&&p[2]>0&&p[3]>0){const k=1024/Math.max(p[2],p[3]);t2=t2.replace(/\s(width|height)\s*=\s*["'][^"']*["']/gi,'').replace(/<svg/i,'<svg width="'+Math.round(p[2]*k)+'" height="'+Math.round(p[3]*k)+'"')}}
    if(!/xmlns\s*=/.test(t2))t2=t2.replace(/<svg/i,'<svg xmlns="http://www.w3.org/2000/svg"');t=t.replace(tag,t2)}
   const img=new Image();img.onload=()=>res({name,canvas:toCanvas(img,1024)});img.onerror=()=>rej(new Error('could not read the SVG '+name));img.src='data:image/svg+xml;charset=utf-8,'+encodeURIComponent(t)}).catch(rej);return}
 const u=URL.createObjectURL(file);const img=new Image();img.onload=()=>{res({name,canvas:toCanvas(img,2048)});URL.revokeObjectURL(u)};img.onerror=()=>rej(new Error('could not read '+name));img.src=u})}
function pixels(L){if(!L._px)L._px=L.canvas.getContext('2d').getImageData(0,0,L.canvas.width,L.canvas.height);return L._px}
const SM=new Float32Array(4);
function sample(L,u,v){const P=pixels(L),W=P.width,H=P.height,d=P.data;const fx=u*W-.5,fy=v*H-.5;const x0=Math.floor(fx),y0=Math.floor(fy),tx=fx-x0,ty=fy-y0;let r=0,g=0,b=0,a=0;
 for(let j=0;j<2;j++)for(let i=0;i<2;i++){const xx=clamp(x0+i,0,W-1),yy=clamp(y0+j,0,H-1),w=(i?tx:1-tx)*(j?ty:1-ty),k=(yy*W+xx)*4,al=d[k+3]/255*w;r+=d[k]*al;g+=d[k+1]*al;b+=d[k+2]*al;a+=al}
 if(a<1e-4){SM[3]=0;return SM}SM[0]=r/a;SM[1]=g/a;SM[2]=b/a;SM[3]=a;return SM}
function prep(L){const t=L.rot*Math.PI/180;L._c=Math.cos(t);L._s=Math.sin(t);L._h=L.w*asp(L)}
function localUV(L,X,Y,out){const dx=X-L.x,dy=Y-L.y;let lx=dx*L._c+dy*L._s,ly=-dx*L._s+dy*L._c;if(L.fx)lx=-lx;if(L.fy)ly=-ly;const u=lx/L.w+.5,v=ly/L._h+.5;if(u<0||u>1||v<0||v>1)return false;out[0]=u;out[1]=v;return true}
function drawLayer(ctx,L,toS,k,alpha){const [sx,sy]=toS(L.x,L.y);ctx.save();ctx.globalAlpha=L.op*(alpha==null?1:alpha);ctx.translate(sx,sy);ctx.rotate(L.rot*Math.PI/180);ctx.scale(L.fx?-1:1,L.fy?-1:1);const w=L.w*k,h=w*asp(L);ctx.imageSmoothingQuality='high';ctx.drawImage(L.canvas,-w/2,-h/2,w,h);ctx.restore()}
function frame(ctx,L,toS,k,strong){const [sx,sy]=toS(L.x,L.y);const w=L.w*k,h=w*asp(L);ctx.save();ctx.translate(sx,sy);ctx.rotate(L.rot*Math.PI/180);ctx.lineWidth=strong?1.6:1;ctx.strokeStyle=strong?'#4aa3ff':'rgba(255,255,255,.35)';ctx.strokeRect(-w/2,-h/2,w,h);
 if(strong){ctx.fillStyle='#4aa3ff';ctx.fillRect(w/2-5,h/2-5,10,10);ctx.beginPath();ctx.moveTo(0,-h/2);ctx.lineTo(0,-h/2-24);ctx.stroke();ctx.beginPath();ctx.arc(0,-h/2-24,5,0,7);ctx.fill()}ctx.restore()}
function rot2(x,y,deg){const t=deg*Math.PI/180,c=Math.cos(t),s=Math.sin(t);return[x*c-y*s,x*s+y*c]}
function handles(L,toS,k){const [sx,sy]=toS(L.x,L.y);const w=L.w*k,h=w*asp(L);const b=rot2(w/2,h/2,L.rot),r=rot2(0,-h/2-24,L.rot);return{sc:[sx+b[0],sy+b[1]],ro:[sx+r[0],sy+r[1]],c:[sx,sy]}}
function hit(L,toS,k,px,py){const [sx,sy]=toS(L.x,L.y);const w=L.w*k,h=w*asp(L);const t=-L.rot*Math.PI/180,c=Math.cos(t),s=Math.sin(t),dx=px-sx,dy=py-sy;const lx=dx*c-dy*s,ly=dx*s+dy*c;return Math.abs(lx)<=w/2&&Math.abs(ly)<=h/2}

// ---------- interaction on one surface (3D view or sheet) ----------
function Surface(cfg){let mode=null,off=[0,0];
 return{get mode(){return mode},
  down(px,py){const {list,toS,k,toW}=cfg.ctx();const sel=list.find(l=>l.id===cfg.getSel());
   if(sel){const h=handles(sel,toS,k);if(Math.hypot(px-h.ro[0],py-h.ro[1])<10){mode='rot';return true}if(Math.hypot(px-h.sc[0],py-h.sc[1])<10){mode='scale';return true}}
   for(let i=list.length-1;i>=0;i--){const L=list[i];if(hit(L,toS,k,px,py)){cfg.setSel(L.id);const w=toW(px,py);off=[w[0]-L.x,w[1]-L.y];mode='move';cfg.changed(L,false);return true}}
   if(sel){cfg.setSel(null);cfg.changed(null,false)}return false},
  move(px,py){if(!mode)return false;const {list,toS,k,toW}=cfg.ctx();const L=list.find(l=>l.id===cfg.getSel());if(!L)return false;
   if(mode==='move'){const w=toW(px,py);L.x=w[0]-off[0];L.y=w[1]-off[1]}
   else if(mode==='scale'){const c=toS(L.x,L.y);L.w=clamp(2*Math.hypot(px-c[0],py-c[1])/(k*Math.hypot(1,asp(L))),cfg.lim[0],cfg.lim[1])}
   else{const c=toS(L.x,L.y);L.rot=Math.round((Math.atan2(py-c[1],px-c[0])*180/Math.PI+90)*2)/2;if(L.rot>180)L.rot-=360}
   cfg.changed(L,false);return true},
  up(){if(!mode)return false;mode=null;cfg.changed(cfg.get(),true);return true}}}

// ---------- layer panel ----------
function mkPanel(host,o){host.innerHTML='';const wrap=el('div','dwrap'),list=el('div','dlist'),props=el('div','dprops');wrap.append(list,props);host.append(wrap);
 const lim=o.lim,lg=Math.log(lim[1]/lim[0]);
 const mk=(lab,id,min,max,step)=>{const l=el('label');const b=el('b','',' ');l.append(lab+' ',b);const r=document.createElement('input');r.type='range';r.min=min;r.max=max;r.step=step;props.append(l,r);return{r,b}};
 const sS=mk('Size','sz',0,1000,1),sR=mk('Rotate','ro',-180,180,0.5),sO=mk('Opacity','op',0,100,1);
 const bt=(t,f)=>{const b=el('button','sec',t);b.onclick=()=>{const L=o.get();if(L)f(L)};props.append(b);return b};
 bt('Flip H',L=>{L.fx=!L.fx;o.changed(L,true)});bt('Flip V',L=>{L.fy=!L.fy;o.changed(L,true)});
 bt('Duplicate',L=>{const n=mkLayer(Object.assign({},L,{id:nextId++,x:L.x+L.w*.1,y:L.y+L.w*.1,_px:L._px}));o.list().push(n);o.setSel(n.id);o.changed(n,true);o.structure()});
 bt('Up',L=>{const a=o.list(),i=a.indexOf(L);if(i<a.length-1){a.splice(i,1);a.splice(i+1,0,L);o.changed(L,true);o.structure()}});
 bt('Down',L=>{const a=o.list(),i=a.indexOf(L);if(i>0){a.splice(i,1);a.splice(i-1,0,L);o.changed(L,true);o.structure()}});
 bt('Delete',L=>{const a=o.list();const i=a.indexOf(L);a.splice(i,1);o.setSel(a.length?a[Math.min(i,a.length-1)].id:null);o.changed(null,true);o.structure()});
 sS.r.oninput=()=>{const L=o.get();if(!L)return;L.w=lim[0]*Math.exp(lg*sS.r.value/1000);o.changed(L,false);o.debounce()};
 sR.r.oninput=()=>{const L=o.get();if(!L)return;L.rot=+sR.r.value;o.changed(L,false);o.debounce()};
 sO.r.oninput=()=>{const L=o.get();if(!L)return;L.op=sO.r.value/100;o.changed(L,false);o.debounce()};
 function R(){const a=o.shown?o.shown():o.list();list.innerHTML='';if(!a.length){list.append(Object.assign(el('div','note','Nothing placed yet - drop an image or SVG, or use the Add button.'),{}))}
  a.slice().reverse().forEach(L=>{const r=el('div','drow'+(L.id===o.sel()?' sel':''));const im=document.createElement('img');im.src=L.canvas.toDataURL();r.append(im,Object.assign(el('span','nm',L.name+(L.view?' ('+L.view+')':''))));r.onclick=()=>{o.setSel(L.id);o.changed(L,false);R()};list.append(r)});
  const L=o.get();[sS.r,sR.r,sO.r].forEach(r=>r.disabled=!L);if(L){sS.r.value=clamp(Math.log(L.w/lim[0])/lg*1000,0,1000);sR.r.value=L.rot;sO.r.value=Math.round(L.op*100);sS.b.textContent=(o.fmt?o.fmt(L.w):L.w.toFixed(3));sR.b.textContent=L.rot.toFixed(1)+'°';sO.b.textContent=Math.round(L.op*100)+'%'}}
 return{R}}

// ---------- baking 3D decals into the atlas through the car's UVs ----------
function bakeView(G,Vw,decs,S,px){const {pos,uv,idx,parts}=G,nv=pos.length/3;const [rx,ry,rz]=Vw.r,[ux,uy,uz]=Vw.u,[fx,fy,fz]=Vw.f;
 const pa=new Float32Array(nv),pb=new Float32Array(nv),pd=new Float32Array(nv);let amin=1e9,amax=-1e9,bmin=1e9,bmax=-1e9;
 for(let i=0;i<nv;i++){const x=pos[3*i],y=pos[3*i+1],z=pos[3*i+2];const a=x*rx+y*ry+z*rz,b=x*ux+y*uy+z*uz;pa[i]=a;pb[i]=b;pd[i]=x*fx+y*fy+z*fz;if(a<amin)amin=a;if(a>amax)amax=a;if(b<bmin)bmin=b;if(b>bmax)bmax=b}
 const R=1536,ds=(R-2)/Math.max(amax-amin,bmax-bmin,1e-6),Dm=new Float32Array(R*R).fill(1e9);
 for(const p of parts){if(p.hidden||p.cat==='glass')continue;for(let t=p.i0;t<p.i0+p.n;t+=3){const i0=idx[t],i1=idx[t+1],i2=idx[t+2];
   const x0=(pa[i0]-amin)*ds,y0=(bmax-pb[i0])*ds,x1=(pa[i1]-amin)*ds,y1=(bmax-pb[i1])*ds,x2=(pa[i2]-amin)*ds,y2=(bmax-pb[i2])*ds;
   const det=(y1-y2)*(x0-x2)+(x2-x1)*(y0-y2);if(Math.abs(det)<1e-9)continue;
   const xa=Math.max(0,Math.floor(Math.min(x0,x1,x2))),xb=Math.min(R-1,Math.ceil(Math.max(x0,x1,x2))),ya=Math.max(0,Math.floor(Math.min(y0,y1,y2))),yb=Math.min(R-1,Math.ceil(Math.max(y0,y1,y2)));
   const d0=pd[i0],d1=pd[i1],d2=pd[i2];
   for(let y=ya;y<=yb;y++)for(let x=xa;x<=xb;x++){const X=x+.5,Y=y+.5;const l0=((y1-y2)*(X-x2)+(x2-x1)*(Y-y2))/det,l1=((y2-y0)*(X-x2)+(x0-x2)*(Y-y2))/det,l2=1-l0-l1;if(l0<-.02||l1<-.02||l2<-.02)continue;const d=l0*d0+l1*d1+l2*d2,k=y*R+x;if(d<Dm[k])Dm[k]=d}}}
 // plane bbox of the decals
 let ba=1e9,bA=-1e9,bb=1e9,bB=-1e9;decs.forEach(L=>{prep(L);const hw=L.w/2,hh=L._h/2,c=Math.abs(L._c),s=Math.abs(L._s),ex=c*hw+s*hh,ey=s*hw+c*hh;ba=Math.min(ba,L.x-ex);bA=Math.max(bA,L.x+ex);bb=Math.min(bb,-L.y-ey);bB=Math.max(bB,-L.y+ey)});
 const uvo=[0,0];
 for(const p of parts){if(p.hidden||!p.atlas)continue;for(let t=p.i0;t<p.i0+p.n;t+=3){const i0=idx[t],i1=idx[t+1],i2=idx[t+2];
   if(Math.max(pa[i0],pa[i1],pa[i2])<ba||Math.min(pa[i0],pa[i1],pa[i2])>bA||Math.max(pb[i0],pb[i1],pb[i2])<bb||Math.min(pb[i0],pb[i1],pb[i2])>bB)continue;
   const e1x=pos[3*i1]-pos[3*i0],e1y=pos[3*i1+1]-pos[3*i0+1],e1z=pos[3*i1+2]-pos[3*i0+2],e2x=pos[3*i2]-pos[3*i0],e2y=pos[3*i2+1]-pos[3*i0+1],e2z=pos[3*i2+2]-pos[3*i0+2];
   const nx=e1y*e2z-e1z*e2y,ny=e1z*e2x-e1x*e2z,nz=e1x*e2y-e1y*e2x,nl=Math.hypot(nx,ny,nz);if(nl<1e-12||Math.abs(nx*fx+ny*fy+nz*fz)/nl<.06)continue;
   const u0=uv[2*i0]*S,v0=uv[2*i0+1]*S,u1=uv[2*i1]*S,v1=uv[2*i1+1]*S,u2=uv[2*i2]*S,v2=uv[2*i2+1]*S;
   const det=(v1-v2)*(u0-u2)+(u2-u1)*(v0-v2);if(Math.abs(det)<1e-9)continue;
   const tol=-Math.min(.35,.8/Math.sqrt(Math.abs(det)+1e-9));
   const xa=Math.max(0,Math.floor(Math.min(u0,u1,u2))-1),xb=Math.min(S-1,Math.ceil(Math.max(u0,u1,u2))+1),ya=Math.max(0,Math.floor(Math.min(v0,v1,v2))-1),yb=Math.min(S-1,Math.ceil(Math.max(v0,v1,v2))+1);
   for(let y=ya;y<=yb;y++)for(let x=xa;x<=xb;x++){const X=x+.5,Y=y+.5;let l0=((v1-v2)*(X-u2)+(u2-u1)*(Y-v2))/det,l1=((v2-v0)*(X-u2)+(u0-u2)*(Y-v2))/det,l2=1-l0-l1;
    if(l0<tol||l1<tol||l2<tol)continue;l0=Math.max(0,l0);l1=Math.max(0,l1);l2=Math.max(0,l2);const sn=l0+l1+l2;l0/=sn;l1/=sn;l2/=sn;
    const Aa=l0*pa[i0]+l1*pa[i1]+l2*pa[i2],Bb=l0*pb[i0]+l1*pb[i1]+l2*pb[i2],Dd=l0*pd[i0]+l1*pd[i1]+l2*pd[i2];
    const ix=((Aa-amin)*ds)|0,iy=((bmax-Bb)*ds)|0;if(ix<0||iy<0||ix>=R||iy>=R)continue;if(Dd>Dm[iy*R+ix]+.03)continue;
    const o=(y*S+x)*4;
    for(const L of decs){if(!localUV(L,Aa,-Bb,uvo))continue;const c=sample(L,uvo[0],uvo[1]);const as=c[3]*L.op;if(as<=0)continue;const ad=px[o+3]/255,ao=as+ad*(1-as);
     px[o]=(c[0]*as+px[o]*ad*(1-as))/ao;px[o+1]=(c[1]*as+px[o+1]*ad*(1-as))/ao;px[o+2]=(c[2]*as+px[o+2]*ad*(1-as))/ao;px[o+3]=ao*255}}}}}
function bake(S){if(A.bk&&A.bk.S===S&&A.bk.ver===A.ver3)return A.bk.c;const G=V.getGeo(),out=cvs(S);
 if(G&&G.uv&&A.dec3.length){const img=new ImageData(S,S),by={};A.dec3.forEach(L=>{(by[L.view]=by[L.view]||[]).push(L)});for(const v in by)bakeView(G,VIEWS[v],by[v],S,img.data);out.getContext('2d').putImageData(img,0,0)}
 A.bk={S,ver:A.ver3,c:out};return out}

// ---------- compose the atlas ----------
function compose(S){const ov=cvs(S),g=ov.getContext('2d');if(A.dec3.length)g.drawImage(bake(S),0,0);A.sheet.forEach(L=>drawLayer(g,L,(x,y)=>[x*S,y*S],S));
 const rgb=cvs(S),gr=rgb.getContext('2d');gr.fillStyle='#000';gr.fillRect(0,0,S,S);if(A.base)gr.drawImage(A.base,0,0,S,S);gr.drawImage(ov,0,0);
 const al=cvs(S),ga=al.getContext('2d');ga.fillStyle='#000';ga.fillRect(0,0,S,S);if(A.baseA)ga.drawImage(A.baseA,0,0,S,S);
 const wh=cvs(S),gw=wh.getContext('2d');gw.drawImage(ov,0,0);gw.globalCompositeOperation='source-in';gw.fillStyle='#fff';gw.fillRect(0,0,S,S);ga.drawImage(wh,0,0);
 return{rgb,alpha:al,overlay:ov}}
function wire(S,color,lw){const c=cvs(S),g=c.getContext('2d'),G=V.getGeo();if(!G||!G.uv)return c;g.strokeStyle=color;g.lineWidth=lw;g.beginPath();
 for(const p of G.parts){if(p.hidden||!p.atlas)continue;for(let t=p.i0;t<p.i0+p.n;t+=3){const a=G.idx[t],b=G.idx[t+1],d=G.idx[t+2];g.moveTo(G.uv[2*a]*S,G.uv[2*a+1]*S);g.lineTo(G.uv[2*b]*S,G.uv[2*b+1]*S);g.lineTo(G.uv[2*d]*S,G.uv[2*d+1]*S);g.closePath()}}
 g.stroke();return c}

// ---------- refresh / live push to the 3D viewer ----------
let rq=false,pushT=0,last=null;
function refresh(){if(rq)return;rq=true;requestAnimationFrame(()=>{rq=false;if(!A.hasAtlas)return;last=compose(1024);drawSheet();const now=performance.now();if(now-pushT>90){pushT=now;V.setAtlasCanvases(last.rgb,last.alpha)}else{clearTimeout(refresh.t);refresh.t=setTimeout(()=>{if(last)V.setAtlasCanvases(last.rgb,last.alpha)},100)}})}
let dbT=0;function debounceBake(){clearTimeout(dbT);dbT=setTimeout(()=>{A.ver3++;A.pending3=false;refresh()},160)}

// ---------- sheet tab ----------
const sh={cv:null,z:1,ox:0,oy:0,drag:null};
function shGeo(){const W=sh.cv.clientWidth,H=sh.cv.clientHeight,s=Math.min(W,H)-16;return{W,H,s,x0:(W-s)/2+sh.ox,y0:(H-s)/2+sh.oy}}
const shToS=(x,y)=>{const g=shGeo();return[g.x0+x*g.s*sh.z,g.y0+y*g.s*sh.z]};
const shToW=(px,py)=>{const g=shGeo();return[(px-g.x0)/(g.s*sh.z),(py-g.y0)/(g.s*sh.z)]};
function drawSheet(){if(!sh.cv||$('#t_sheet').classList.contains('hide'))return;const dpr=window.devicePixelRatio||1,W=sh.cv.clientWidth,H=sh.cv.clientHeight;if(sh.cv.width!==Math.round(W*dpr)){sh.cv.width=Math.round(W*dpr);sh.cv.height=Math.round(H*dpr)}
 const c=sh.cv.getContext('2d');c.setTransform(dpr,0,0,dpr,0,0);c.fillStyle='#0d0f13';c.clearRect(0,0,W,H);c.fillRect(0,0,W,H);const g=shGeo(),S=g.s*sh.z;
 if(last){c.imageSmoothingEnabled=sh.z<3;c.drawImage(A.showAlpha?last.alpha:last.rgb,g.x0,g.y0,S,S);if(A.showUV&&A.wire)c.drawImage(A.wire,g.x0,g.y0,S,S)}
 c.strokeStyle='#323844';c.strokeRect(g.x0,g.y0,S,S);
 A.sheet.forEach(L=>frame(c,L,shToS,S,L.id===A.selS&&true));}
const shSurf=Surface({lim:[.004,3],ctx:()=>({list:A.sheet,toS:shToS,toW:shToW,k:shGeo().s*sh.z}),getSel:()=>A.selS,get:()=>A.sheet.find(l=>l.id===A.selS),setSel:id=>{A.selS=id},changed:(L,commit)=>{if(commit)shPanel.R();refresh()}});
const shPanel=mkPanel($('#shPanel'),{list:()=>A.sheet,sel:()=>A.selS,setSel:id=>{A.selS=id},get:()=>A.sheet.find(l=>l.id===A.selS),lim:[.004,3],fmt:w=>Math.round(w*100)+'% of sheet width',changed:(L,c)=>{refresh()},debounce:()=>{},structure:()=>shPanel.R()});
function addSheet(r,at,full){const L=mkLayer({canvas:r.canvas,name:r.name,w:full?1:clamp(.25,.004,3),x:.5,y:.5,view:null});if(full){L.w=1;L.name=r.name+' (sheet)'}else if(at){L.x=at[0];L.y=at[1]}A.sheet.push(L);A.selS=L.id;shPanel.R();refresh()}
sh.cv=$('#shCv');
sh.cv.addEventListener('pointerdown',e=>{sh.cv.setPointerCapture(e.pointerId);const r=sh.cv.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top;if(e.button===0&&shSurf.down(px,py)){shPanel.R();return}sh.drag={x:e.clientX,y:e.clientY}});
sh.cv.addEventListener('pointermove',e=>{const r=sh.cv.getBoundingClientRect();if(shSurf.mode){shSurf.move(e.clientX-r.left,e.clientY-r.top);shPanel.R();return}if(sh.drag){sh.ox+=e.clientX-sh.drag.x;sh.oy+=e.clientY-sh.drag.y;sh.drag={x:e.clientX,y:e.clientY};drawSheet()}});
sh.cv.addEventListener('pointerup',e=>{shSurf.up();sh.drag=null});
sh.cv.addEventListener('wheel',e=>{e.preventDefault();const r=sh.cv.getBoundingClientRect(),px=e.clientX-r.left,py=e.clientY-r.top,w=shToW(px,py);sh.z=clamp(sh.z*Math.exp(-e.deltaY*.0015),.5,16);const g=shGeo(),s=g.s*sh.z;sh.ox+=px-(g.x0+w[0]*s);sh.oy+=py-(g.y0+w[1]*s);drawSheet()},{passive:false});
$('#shReset').onclick=()=>{sh.z=1;sh.ox=sh.oy=0;drawSheet()};
$('#shUV').onclick=e=>{A.showUV=!A.showUV;e.target.classList.toggle('on',A.showUV);drawSheet()};
$('#shAlpha').onclick=e=>{A.showAlpha=!A.showAlpha;e.target.classList.toggle('on',A.showAlpha);drawSheet()};
async function addFiles(files,surface,at){let n=0;for(const f of files){try{const r=await loadFile(f);if(surface==='sheet')addSheet(r,at||null,false);else add3(r,at);n++}catch(e){log(e.message,'bad')}}return n}
$('#shAdd').onclick=()=>$('#shFile').click();$('#shFile').onchange=async e=>{if(!A.hasAtlas)return log('open a car with a baked livery texture first','warn');await addFiles([...e.target.files],'sheet');e.target.value=''};
$('#shFull').onclick=()=>$('#shFullFile').click();$('#shFullFile').onchange=async e=>{const f=e.target.files[0];e.target.value='';if(!f||!A.hasAtlas)return;try{addSheet(await loadFile(f),null,true)}catch(er){log(er.message,'bad')}};
const dz=(node,fn)=>{['dragenter','dragover'].forEach(t=>node.addEventListener(t,e=>{e.preventDefault();node.classList.add('drop')}));['dragleave','drop'].forEach(t=>node.addEventListener(t,e=>{e.preventDefault();node.classList.remove('drop')}));node.addEventListener('drop',e=>{const fs=[...e.dataTransfer.files];if(fs.length)fn(fs,e)})};
dz($('#shWrap'),(fs,e)=>{if(!A.hasAtlas)return log('open a car with a baked livery texture first','warn');const r=sh.cv.getBoundingClientRect();addFiles(fs,'sheet',shToW(e.clientX-r.left,e.clientY-r.top))});

// ---------- 3D locked-view decals ----------
let panel3=null,s3=null;
const ctx3=()=>{const v=V.view2d();return{list:A.dec3.filter(l=>l.view===v.name),toS:(x,y)=>v.toS(x,-y),toW:(px,py)=>{const w=v.toW(px,py);return[w[0],-w[1]]},k:v.k}};
function add3(r,at){const v=V.view2d();if(!v){log('lock the 3D view to Left / Right / Top / Front / Rear first, then drop the image','warn');return}
 const L=mkLayer({canvas:r.canvas,name:r.name,view:v.name,w:Math.min(v.W/v.k*.3,1.5)});const w=at||[v.W/2,v.H/2];const p=ctx3().toW(w[0],w[1]);L.x=p[0];L.y=p[1];A.dec3.push(L);A.sel3=L.id;A.pending3=true;panel3.R();debounceBake()}
function mkBar(){const bar=$('#dLockBar');bar.innerHTML='';bar.append(el('span','note','Decals - lock to:'));
 ['left','right','front','rear','top'].forEach(n=>{const b=el('button','sec',n[0].toUpperCase()+n.slice(1));b.dataset.lock=n;b.onclick=()=>{if(!A.hasAtlas)log('this car has no baked-livery texture, so decals cannot be placed','warn');V.lock(n);syncBar();panel3.R()};bar.append(b)});
 const b=el('button','sec','Free orbit');b.onclick=()=>{V.unlock();syncBar()};bar.append(b);
 const add=el('button','sec','Add image / SVG…');const fi=document.createElement('input');fi.type='file';fi.accept='image/*,.svg';fi.multiple=true;fi.style.display='none';add.onclick=()=>{if(!V.view2d())return log('lock a view first (Left / Right / Top / Front / Rear)','warn');fi.click()};fi.onchange=async()=>{await addFiles([...fi.files],'3d');fi.value=''};bar.append(add,fi);
 bar.append(Object.assign(el('span','note','or drag a file onto the car.'),{style:'margin-left:4px'}));}
function syncBar(){document.querySelectorAll('#dLockBar [data-lock]').forEach(b=>b.classList.toggle('on',V.st.lock===b.dataset.lock))}
function mk3(){const host=$('#dBox3');host.innerHTML='';const top=el('div','note');top.style.margin='6px 0';top.textContent='Decals are placed flat on the locked view and baked onto every visible panel of the car texture through its UV map (hidden-surface aware). Click a picture to select; drag to move; corner = size; knob = rotate.';host.append(top);
 const ph=el('div');host.append(ph);
 panel3=mkPanel(ph,{list:()=>A.dec3,shown:()=>A.dec3.filter(l=>!V.view2d()||l.view===V.view2d().name),sel:()=>A.sel3,setSel:id=>{A.sel3=id},get:()=>A.dec3.find(l=>l.id===A.sel3),lim:[.02,6],fmt:w=>w.toFixed(2)+' m wide',
  changed:(L,commit)=>{A.pending3=true;if(commit)debounceBake()},debounce:debounceBake,structure:()=>{A.ver3++;panel3.R();refresh()}});
 s3=Surface({lim:[.02,6],ctx:ctx3,getSel:()=>A.sel3,get:()=>A.dec3.find(l=>l.id===A.sel3),setSel:id=>{A.sel3=id},changed:(L,commit)=>{A.pending3=true;if(commit){debounceBake()}panel3.R()}});
 const row=el('div');row.style.cssText='margin:8px 0;display:flex;gap:8px;flex-wrap:wrap;align-items:center';
 const b1=el('button','',' Send 3D decals to the editor (.liv layers)');const rs=document.createElement('input');rs.type='range';rs.min=60;rs.max=950;rs.step=10;rs.value=400;rs.style.width='140px';const rl=el('span','note','shapes: 400');rs.oninput=()=>rl.textContent='shapes: '+rs.value;
 b1.onclick=()=>sendToEditor(+rs.value,b1);const b2=el('button','sec','Clear all decals');b2.onclick=()=>{A.dec3=[];A.sel3=null;A.ver3++;A.pending3=false;panel3.R();refresh()};
 row.append(b1,rs,rl,b2,Object.assign(el('span','note','The .liv route is approximate (flat shapes on the garage panels); the texture route is exact.'),{}));host.append(row);panel3.R()}
V.hooks.down=e=>{if(!V.st.lock||e.button!==0||!A.hasAtlas)return false;const r=V.cv.getBoundingClientRect();return s3.down(e.clientX-r.left,e.clientY-r.top)};
V.hooks.move=e=>{if(!s3||!s3.mode)return false;const r=V.cv.getBoundingClientRect();return s3.move(e.clientX-r.left,e.clientY-r.top)};
V.hooks.up=e=>{if(s3&&s3.mode){s3.up();return true}};
V.hooks.overlay=c=>{const v=V.view2d();if(!v)return;const list=A.dec3.filter(l=>l.view===v.name),t=(x,y)=>v.toS(x,-y);
 if(A.pending3||(s3&&s3.mode))list.forEach(L=>drawLayer(c,L,t,v.k,.75));list.forEach(L=>frame(c,L,t,v.k,L.id===A.sel3));
 c.fillStyle='rgba(74,163,255,.9)';c.font='11px sans-serif';c.fillText('LOCKED: '+v.name.toUpperCase()+' (orthographic) - drop images here',10,16)};
dz($('#vWrap'),(fs,e)=>{const r=V.cv.getBoundingClientRect();if(!V.view2d())return log('lock the view first (Left / Right / Top / Front / Rear), then drop the image','warn');if(!A.hasAtlas)return log('this car has no baked-livery texture','warn');addFiles(fs,'3d',[e.clientX-r.left,e.clientY-r.top])});

// ---------- .liv route ----------
async function sendToEditor(shapes,btn){
 if(!sel)return log('pick a garage slot first','warn');const views=[...new Set(A.dec3.map(l=>l.view))];if(!views.length)return log('place a decal in the 3D view first','warn');
 const out={};
 for(const vn of views){const pn=VPANEL[vn],P=V.getProj(pn);if(!P){log('this car has no '+pn+' livery panel (skipped '+vn+')','warn');continue}
  const decs=A.dec3.filter(l=>l.view===vn);decs.forEach(prep);const [x0,x1,y0,y1]=P.box,W=Math.min(1600,Math.max(8,Math.round(x1-x0))),H=Math.max(8,Math.round((y1-y0)*W/(x1-x0)));
  const img=new ImageData(W,H),px=img.data,Vw=VIEWS[vn],uvo=[0,0];
  for(let j=0;j<H;j++)for(let i=0;i<W;i++){const pxu=x0+(i+.5)/W*(x1-x0),pyu=y0+(1-(j+.5)/H)*(y1-y0);const w=[0,0,0];w[P.ax]=(pxu-P.cx)/(P.sx*P.s);w[P.ay]=(pyu-P.cy)/(P.sy*P.s);
   const Aa=w[0]*Vw.r[0]+w[1]*Vw.r[1]+w[2]*Vw.r[2],Bb=w[0]*Vw.u[0]+w[1]*Vw.u[1]+w[2]*Vw.u[2],o=(j*W+i)*4;
   for(const L of decs){if(!localUV(L,Aa,-Bb,uvo))continue;const c=sample(L,uvo[0],uvo[1]),as=c[3]*L.op;if(as<=0)continue;const ad=px[o+3]/255,ao=as+ad*(1-as);px[o]=(c[0]*as+px[o]*ad*(1-as))/ao;px[o+1]=(c[1]*as+px[o+1]*ad*(1-as))/ao;px[o+2]=(c[2]*as+px[o+2]*ad*(1-as))/ao;px[o+3]=ao*255}}
  const c=cvs(W,H);c.getContext('2d').putImageData(img,0,0);out[pn]=await b64(await new Promise(r=>c.toBlob(r,'image/png')))}
 if(!Object.keys(out).length)return;setBusy(true,btn,'Fitting shapes…');
 try{const r=await api('decalfit',{slot:sel,carzip:$('#zipSel').value,panels:out,shapes});const lay=await api('fitlayers',{id:r.id});prevId=r.id;prevSlot=sel;goTab('edit');await E.importLayers(lay.panels,$('#openHow').value);log('decals sent to the editor as '+r.total_layers+' layers','ok')}
 catch(e){log('decals to editor: '+e.message,'bad')}finally{setBusy(false,btn)}}

// ---------- export ----------
const blobOf=c=>new Promise(r=>c.toBlob(r,'image/png'));
async function exportXds(){if(!sel)return log('pick a garage slot first','warn');if(!A.hasAtlas)return log('this car has no baked-livery texture','warn');
 if(!A.dec3.length&&!A.sheet.length)return log('nothing placed yet','warn');const btn=$('#shExport');setBusy(true,btn,'Building…');
 try{const S=2048;const c=compose(S);const r=await api('bake',{slot:sel,carzip:$('#zipSel').value,overlay:await b64(await blobOf(c.overlay)),zip:true});
  log('texture files written to '+r.dir,'ok');r.files.forEach(f=>log('  '+f));if(r.zip)log('  car zip copy: '+r.zip+' (stored/uncompressed entries - not installed anywhere)');log('round-trip check: mean error '+r.err.toFixed(2)+' (levels of 255)');$('#shStatus').textContent='built - '+r.dir}
 catch(e){log('build: '+e.message,'bad')}finally{setBusy(false,btn)}}
$('#shExport').onclick=exportXds;

async function libShow(){try{const l=await api('liblist',sel?{slot:sel,carzip:$('#zipSel').value}:{});const box=$('#libList');box.innerHTML='';
  const by={};l.entries.forEach(e=>(by[e.car]=by[e.car]||[]).push(e));const cars=Object.keys(by).sort();if(!cars.length)box.textContent='Nothing saved yet - make an edit in the Texture sheet or 3D view and press "Save to library".';
  cars.forEach(car=>{const h=el('div',null);h.style.cssText='margin:10px 0 4px;font-weight:600;color:var(--text)';const cl=by[car][0].clone;h.textContent=(cl?cl.display+'  (new car, copy of '+cl.donor+', id '+cl.car_id+')':car)+(car===l.car?'  (selected car)':'')+(l.installed_cars.includes(car)||l.installed_clones.includes(car)?'   - in game':'');box.appendChild(h);
   const none=el('label','chk');none.innerHTML='<input type="radio" name="lib_'+car+'" '+(by[car].some(e=>e.active)?'':'checked')+'> '+(by[car][0].clone?'not in game':'original (no texture edit)');none.firstChild.onchange=async()=>{if(by[car][0].clone&&!await askYes('Take this new car out of the game? Garage cars of this model would stop working.')){libShow();return}await api('libset',{deactivate_car:car});libShow()};box.appendChild(none);
   by[car].forEach(e=>{const row=el('div',null);row.style.cssText='display:flex;gap:8px;align-items:center';const lb=el('label','chk');lb.style.flex='1';lb.innerHTML='<input type="radio" name="lib_'+car+'" '+(e.active?'checked':'')+'> ';lb.appendChild(document.createTextNode(e.name+'  '));const sm=el('span','note',e.created+(e.source==='imported'?' · imported':''));lb.appendChild(sm);
    lb.firstChild.onchange=async()=>{await api('libset',{activate:e.id});libShow()};row.appendChild(lb);const rm=el('button','sec','Remove');rm.style.padding='3px 8px';rm.onclick=async()=>{if(!await askYes('Remove "'+e.name+'" from the library? (it is moved to the backups folder, not deleted)'+(e.clone?' A garage car using this new car would lose its model - remove those first.':'')))return;await api('libset',{remove:e.id});libShow()};row.appendChild(rm);box.appendChild(row)})});
  $('#libNote').textContent=l.legacy.length?l.legacy.length+' pack(s) from an earlier version are installed; Apply will absorb them into the library and move them out of the game.':''}
 catch(e){$('#libList').textContent='';log('library: '+e.message,'bad')}}
$('#libRefresh').onclick=libShow;
$('#shSave').onclick=async()=>{if(!sel)return log('pick a garage slot first','warn');if(!A.hasAtlas)return log('this car has no baked-livery texture','warn');
 if(!A.dec3.length&&!A.sheet.length)return log('nothing placed yet','warn');const btn=$('#shSave');setBusy(true,btn,'Saving…');
 try{const c=compose(2048);const r=await api('libsave',{slot:sel,carzip:$('#zipSel').value,overlay:await b64(await blobOf(c.overlay)),name:$('#shName').value,activate:true,clone:$('#shClone').checked});
  log('saved "'+r.entry.name+'" '+(r.entry.clone?'as a NEW car (id '+r.entry.clone.car_id+', copy of '+r.entry.clone.donor+')':'for '+r.entry.car)+' to the library (active). Open the Library tab and press Apply to put it in the game.','ok');$('#shStatus').textContent='saved to library';$('#shName').value=''}
 catch(e){log('save: '+e.message,'bad')}finally{setBusy(false,btn)}};
$('#libApply').onclick=async()=>{if(!await askYes('Is the game fully closed? This rebuilds one texture pack from the active library edits and installs it (earlier packs are moved to the backups folder; original car files are not changed).'))return;
 const btn=$('#libApply');setBusy(true,btn,'Applying…');
 try{const r=await api('libapply',{confirm:true,gameClosed:true});log((r.cars.length||r.clones.length)?('installed one pack: '+r.cars.length+' texture override(s)'+(r.clones.length?', '+r.clones.length+' new car(s): '+r.clones.join(', '):'')):'no active edits - the texture pack was removed from the game','ok');
  r.absorbed.forEach(n=>log('  absorbed into the library: '+n));r.moved_out.forEach(f=>log('  moved out to '+f));log('backups: '+r.backups+'. Untested in game until you look at the car - Apply with "original" selected undoes it.');libShow()}
 catch(e){log('apply: '+e.message,'bad')}finally{setBusy(false,btn)}};
$('#libStfs').onclick=async()=>{const btn=$('#libStfs');setBusy(true,btn,'Packaging…');
 try{const r=await api('stfs',{template:$('#shTpl').value.trim()});
  log('STFS package written: '+r.path+' ('+r.verified_files+' files read back OK, '+r.cars.length+' car(s), template '+r.template+')','ok');log('The signature is stale (cannot be re-created). Xenia/recomp do not check it; a retail console does - hardware users must re-sign it. Untested on hardware.','warn')}
 catch(e){log('STFS: '+e.message,'bad')}finally{setBusy(false,btn)}};
$('#shTemplate').onclick=async()=>{if(!sel||!A.hasAtlas)return log('open a car with a baked livery texture first','warn');try{const S=2048;const w=wire(S,'rgba(0,255,255,0.9)',1.2),base=cvs(S),g=base.getContext('2d');g.drawImage(A.base,0,0,S,S);const al=cvs(S);al.getContext('2d').drawImage(A.baseA,0,0,S,S);
  const mix=cvs(S),gm=mix.getContext('2d');gm.drawImage(base,0,0);gm.drawImage(w,0,0);let dir='';
  for(const [n,c] of [['atlas_colour.png',base],['atlas_alpha.png',al],['uv_outlines.png',w],['atlas_with_uv.png',mix]]){const r=await api('savefile',{slot:sel,carzip:$('#zipSel').value,name:n,data:await b64(await blobOf(c))});dir=r.dir}
  log('template saved in '+dir+' (atlas_colour / atlas_alpha / uv_outlines / atlas_with_uv). Paint on atlas_colour.png, then load it with "Add painted sheet…"','ok')}catch(e){log('template: '+e.message,'bad')}};

// ---------- model hook ----------
function loadImg(b64){return new Promise(r=>{const i=new Image();i.onload=()=>r(i);i.onerror=()=>r(null);i.src='data:image/png;base64,'+b64})}
V.hooks.model=async m=>{A.dec3=[];A.sheet=[];A.sel3=A.selS=null;A.ver3++;A.bk=null;A.wire=null;A.base=A.baseA=null;A.hasAtlas=false;last=null;V.unlock();syncBar();
 if(!panel3){mkBar();mk3()}else{panel3.R();shPanel.R()}
 if(!m.atlas||!m.atlas_a){$('#shStatus').textContent='this car has no baked-livery texture';return}
 const [b,a]=await Promise.all([loadImg(m.atlas),loadImg(m.atlas_a)]);if(!b||!a)return;A.base=b;A.baseA=a;A.hasAtlas=true;A.wire=wire(1024,'rgba(0,255,255,0.4)',.6);$('#shStatus').textContent='';refresh()};
mkBar();mk3();
return{libShow,sheetShow(){drawSheet();if(!A.hasAtlas&&V.getGeo()==null)$('#shStatus').textContent='pick a garage slot first'; else refresh()},A,compose,bake}})();
'''
