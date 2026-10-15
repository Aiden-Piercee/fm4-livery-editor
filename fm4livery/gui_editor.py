"""Editor tab: shows the livery that is in the selected slot (layers per panel, real vinyl shapes). Fragments spliced into the GUI page."""

CSS = r'''
#t_edit{display:flex;flex-direction:column;gap:10px}
.ewrap{height:560px;max-height:72vh;overflow:auto;border:1px solid var(--line);border-radius:8px;background:#0d0f13;min-width:0}
.ewrap canvas{display:block}
.etools{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.etools .note{margin-left:6px}
.elist{max-height:300px;overflow:auto;border:1px solid var(--line);border-radius:7px;background:var(--bg);font-size:12px}
.elist div{display:flex;gap:8px;align-items:center;padding:3px 8px;border-bottom:1px solid var(--line);cursor:pointer}
.elist div:hover{background:var(--panel2)}.elist div.sel{background:#223a57}
.sw{width:14px;height:14px;border-radius:3px;border:1px solid #fff3;flex:0 0 auto}
.egrid{display:grid;grid-template-columns:1fr 280px;gap:12px}
@media(max-width:900px){.egrid{grid-template-columns:1fr}}
.eform{display:grid;grid-template-columns:1fr 1fr;gap:8px 10px;margin-top:6px}
.eform label{display:flex;flex-direction:column;gap:3px;margin:0;font-size:12px;color:var(--mute)}
.eform input{width:100%;background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:7px;padding:5px 7px;font:inherit}
.eform input[type=color]{height:30px;padding:2px}
.eform input:disabled{opacity:.45}
'''

HTML = r'''
   <div id="t_edit" class="hide">
     <div class="row"><div style="flex:0 0 180px"><label>Panel</label><select id="ePanel"></select></div>
       <div style="flex:0 0 auto;align-self:flex-end"><button class="sec" id="eReload">Reload from slot</button></div>
       <div style="flex:0 0 auto;align-self:flex-end"><button id="eSave" disabled>Save to slot</button></div>
       <label class="chk hide" id="eClosedBox" style="flex:0 0 auto;align-self:flex-end;margin:0 0 6px"><input type="checkbox" id="eClosed"> The game is closed</label>
       <div class="note" id="eCount" style="flex:0 0 auto;align-self:flex-end"></div></div>
     <div class="note" id="eInfo"></div>
     <div class="etools">
       <button class="sec" id="eUndo" title="Ctrl+Z">Undo</button><button class="sec" id="eRedo" title="Ctrl+Y or Ctrl+Shift+Z">Redo</button>
       <button class="sec" id="eDup">Duplicate</button><button class="sec" id="eFwd">Bring forward</button><button class="sec" id="eBack">Send back</button><button class="sec" id="eDel" title="Delete key">Delete</button>
       <span class="note">Drag to move - handles resize - top handle rotates - wheel zooms - right/middle drag or Space+drag pans - arrows nudge (Shift = 10)</span>
     </div>
     <div class="egrid"><div class="ewrap" id="eWrap"><canvas id="eCv"></canvas></div>
       <div><label>Layers (bottom to top)</label><div class="elist" id="eList"></div>
         <label>Selected layer</label>
         <div class="eform" id="eForm">
           <label>x <input type="number" step="any" data-k="x"></label>
           <label>y <input type="number" step="any" data-k="y"></label>
           <label>Width (sx) <input type="number" step="any" data-k="sx"></label>
           <label>Height (sy) <input type="number" step="any" data-k="sy"></label>
           <label>Spin (deg) <input type="number" step="any" data-k="spin"></label>
           <label>Skew <input type="number" step="any" data-k="skew"></label>
           <label>Colour <input type="color" data-k="col"></label>
           <label>Opacity 0-255 <input type="number" min="0" max="255" step="1" data-k="op"></label>
         </div></div></div>
   </div>
'''

JS = r'''
const E=(()=>{
const K=124,SC=248,ELEM=['x','y','sx','sy','spin','skew'];
let data=null,shapes={},panel=null,sel=-1,sils={},key=null,zoom=1,rtok=0;
let U=[],R=[],cur=null,saved=null,dirty=false,nt=null,drag=null,pan=null,spaceDown=false;
const argb=v=>{const a=(v>>>24)&255,r=(v>>>16)&255,g=(v>>>8)&255,b=v&255;return[r,g,b,a]};
function paintLayers(ctx,P,x0,y1,s,upto){
 for(let i=0;i<P.layers.length&&i<(upto??1e9);i++){const L=P.layers[i],S=shapes[L.shape];const [r,g,b,a]=argb(L.argb);
  ctx.fillStyle='rgba('+r+','+g+','+b+','+(a/255)+')';
  if(!S){ctx.fillRect((L.x-x0-K*L.sx/2)*s,(y1-L.y-K*L.sy/2)*s,K*L.sx*s,K*L.sy*s);continue}
  const c=Math.cos(L.spin*Math.PI/180),sn=Math.sin(L.spin*Math.PI/180);const V=S.v,T=S.t;ctx.beginPath();
  const pt=j=>{const mx=V[j*2]*SC*L.sx,my=V[j*2+1]*SC*L.sy;const px=L.x+mx*c-my*sn,py=L.y+mx*sn+my*c;return[(px-x0)*s,(y1-py)*s]};
  for(let k=0;k<T.length;k+=3){let A=pt(T[k]),B=pt(T[k+1]),C=pt(T[k+2]);const ar=(B[0]-A[0])*(C[1]-A[1])-(B[1]-A[1])*(C[0]-A[0]);if(ar<0){const t=B;B=C;C=t}
   ctx.moveTo(A[0],A[1]);ctx.lineTo(B[0],B[1]);ctx.lineTo(C[0],C[1]);ctx.closePath()}
  ctx.fill()}}
function silImg(n){return new Promise(res=>{if(sils[n])return res(sils[n]);const im=new Image();im.onload=()=>{sils[n]=im;res(im)};im.src='data:image/png;base64,'+data.panels[n].sil})}
async function renderTex(n,res){const P=data.panels[n],[x0,x1,y0,y1]=P.box,W=Math.max(8,Math.round((x1-x0)*res)),H=Math.max(8,Math.round((y1-y0)*res));
 const cv=document.createElement('canvas');cv.width=W;cv.height=H;const ctx=cv.getContext('2d');paintLayers(ctx,P,x0,y1,res);
 ctx.globalCompositeOperation='destination-in';ctx.drawImage(await silImg(n),0,0,W,H);return cv}

// ---- view and geometry (canvas px; pos units are Y-up, canvas is Y-down) ----
function view(){const P=data.panels[panel],[x0,x1,y0,y1]=P.box;return{P,x0,x1,y0,y1,s:Math.min(1.6,Math.max(0.5,960/(x1-x0)))*zoom}}
function toC(V,px,py){return[(px-V.x0)*V.s,(V.y1-py)*V.s]}
function toP(V,cx,cy){return[V.x0+cx/V.s,V.y1-cy/V.s]}
function geom(V,L){const r=L.spin*Math.PI/180,c=Math.cos(r),sn=Math.sin(r),p=toC(V,L.x,L.y);
 return{cx:p[0],cy:p[1],w:K*L.sx*V.s,h:K*L.sy*V.s,u:[c,-sn],v:[-sn,-c]}}
function corner(g,hx,hy){return[g.cx+hx*g.w/2*g.u[0]+hy*g.h/2*g.v[0],g.cy+hx*g.w/2*g.u[1]+hy*g.h/2*g.v[1]]}
function rotPt(g){const d=g.h/2+26;return[g.cx+d*g.v[0],g.cy+d*g.v[1]]}
const HANDLES=[[-1,-1],[0,-1],[1,-1],[1,0],[1,1],[0,1],[-1,1],[-1,0]];
const dist=(a,b)=>Math.hypot(a[0]-b[0],a[1]-b[1]);
function hit(V,mx,my){const Ls=V.P.layers;
 if(sel>0&&Ls[sel]){const g=geom(V,Ls[sel]);if(dist(rotPt(g),[mx,my])<=9)return{t:'rot',g};
  for(const [hx,hy] of HANDLES){if(dist(corner(g,hx,hy),[mx,my])<=8)return{t:'h',hx,hy,g}}}
 for(let i=Ls.length-1;i>=0;i--){const g=geom(V,Ls[i]),dx=mx-g.cx,dy=my-g.cy;
  if(Math.abs(dx*g.u[0]+dy*g.u[1])<=g.w/2&&Math.abs(dx*g.v[0]+dy*g.v[1])<=g.h/2)return{t:'body',i}}
 return null}
function overlay(ctx,V){const L=V.P.layers[sel];if(!L)return;const g=geom(V,L);
 ctx.save();ctx.strokeStyle='#4aa3ff';ctx.lineWidth=2;ctx.beginPath();
 [[-1,-1],[1,-1],[1,1],[-1,1]].forEach(([hx,hy],k)=>{const p=corner(g,hx,hy);k?ctx.lineTo(p[0],p[1]):ctx.moveTo(p[0],p[1])});
 ctx.closePath();ctx.stroke();
 if(sel>0){const top=corner(g,0,1),rp=rotPt(g);ctx.beginPath();ctx.moveTo(top[0],top[1]);ctx.lineTo(rp[0],rp[1]);ctx.stroke();
  ctx.beginPath();ctx.arc(rp[0],rp[1],5,0,Math.PI*2);ctx.fillStyle='#fff';ctx.fill();ctx.stroke();
  for(const [hx,hy] of HANDLES){const p=corner(g,hx,hy);ctx.fillStyle='#fff';ctx.fillRect(p[0]-4,p[1]-4,8,8);ctx.strokeRect(p[0]-4,p[1]-4,8,8)}}
 ctx.restore()}

async function draw(){if(!data||!panel)return;const my=++rtok,V=view(),[x0,x1,y0,y1]=V.P.box;
 const sil=await silImg(panel);const t=await renderTex(panel,V.s);if(my!==rtok)return;
 const cv=$('#eCv');cv.width=Math.round((x1-x0)*V.s);cv.height=Math.round((y1-y0)*V.s);
 const ctx=cv.getContext('2d');ctx.fillStyle='#14161a';ctx.fillRect(0,0,cv.width,cv.height);
 const bg=document.createElement('canvas');bg.width=cv.width;bg.height=cv.height;const b=bg.getContext('2d');b.drawImage(sil,0,0,cv.width,cv.height);b.globalCompositeOperation='source-in';b.fillStyle='#2b2f38';b.fillRect(0,0,cv.width,cv.height);
 ctx.drawImage(bg,0,0);ctx.drawImage(t,0,0);
 if(sel>=0&&V.P.layers[sel])overlay(ctx,V);
 const list=$('#eList');list.innerHTML='';V.P.layers.forEach((L,i)=>{const d=document.createElement('div');if(i===sel)d.className='sel';const [r,g,bb,a]=argb(L.argb);
  d.innerHTML='<span class="sw" style="background:rgba('+r+','+g+','+bb+','+(a/255)+')"></span><span>#'+(i+1)+'</span><span class="note">shape '+L.shape+'</span><span class="note" style="margin-left:auto">'+Math.round(L.x)+', '+Math.round(L.y)+'</span>';
  d.onclick=()=>{sel=i;draw()};list.appendChild(d)});
 updForm();updBtns();updCount();info()}

function info(){if(!data||!panel)return;const P=data.panels[panel];
 $('#eInfo').textContent=(dirty?'* unsaved changes - ':'')+P.layers.length+' layers on '+panel+(data.missing.length?' - '+data.missing.length+' shape(s) not readable (drawn as boxes)':'')+(data.have_file?'':' - this slot has no livery file yet')}
function updCount(){if(!data)return;let t=0;for(const n of Object.keys(data.panels))t+=data.panels[n].layers.length;
 const c=$('#eCount');c.textContent=t+' layers in total (limit 1000)';c.className='note'+(t>1000?' warn':'');
 for(const o of $('#ePanel').options){if(data.panels[o.value])o.textContent=o.value+' ('+data.panels[o.value].layers.length+')'}}
function updBtns(){const n=(data&&panel)?data.panels[panel].layers.length:0,has=!!data&&sel>0;
 $('#eDel').disabled=!has;$('#eDup').disabled=!has;$('#eFwd').disabled=!(has&&sel<n-1);$('#eBack').disabled=!(sel>1);
 $('#eUndo').disabled=!U.length;$('#eRedo').disabled=!R.length;$('#eSave').disabled=!data}
function updForm(){const L=(data&&panel&&sel>=0)?data.panels[panel].layers[sel]:null;
 document.querySelectorAll('#eForm [data-k]').forEach(el=>{const k=el.dataset.k;
  el.disabled=!L||(sel===0&&ELEM.includes(k));
  if(el===document.activeElement)return;
  if(!L){el.value=(k==='col'?'#000000':'');return}
  if(k==='col'){const [r,g,b]=argb(L.argb);el.value='#'+[r,g,b].map(v=>v.toString(16).padStart(2,'0')).join('')}
  else if(k==='op')el.value=argb(L.argb)[3];
  else el.value=Math.round(L[k]*1000)/1000})}
function formIn(el){if(!data||sel<0)return;const L=data.panels[panel].layers[sel],k=el.dataset.k;
 if(k==='col'||k==='op'){const hex=document.querySelector('#eForm [data-k=col]').value;
  const r=parseInt(hex.slice(1,3),16),g=parseInt(hex.slice(3,5),16),b=parseInt(hex.slice(5,7),16);
  let op=Math.round(parseFloat(document.querySelector('#eForm [data-k=op]').value));if(!isFinite(op))return;op=Math.min(255,Math.max(0,op));
  L.argb=((op<<24)|(r<<16)|(g<<8)|b)>>>0}
 else{if(sel===0&&ELEM.includes(k))return;const v=parseFloat(el.value);if(!isFinite(v))return;L[k]=v}
 touch();draw()}

// ---- undo / dirty state (snapshot based, per slot load, max 100 steps) ----
function touch(){dirty=true}
function snap(){const o={};for(const n in data.panels)o[n]=data.panels[n].layers;return JSON.stringify(o)}
function restore(s){const o=JSON.parse(s);for(const n in o)data.panels[n].layers=o[n];if(sel>=data.panels[panel].layers.length)sel=-1}
function commit(){if(!data)return;clearTimeout(nt);nt=null;const s=snap();
 if(s!==cur){if(cur!==null){U.push(cur);if(U.length>100)U.shift()}cur=s;R=[]}dirty=s!==saved}
function nudgeLater(){clearTimeout(nt);nt=setTimeout(()=>{nt=null;commit();draw()},500)}
function undo(){if(!data)return;commit();if(!U.length)return;R.push(cur);cur=U.pop();restore(cur);dirty=cur!==saved;draw()}
function redo(){if(!data)return;commit();if(!R.length)return;U.push(cur);cur=R.pop();restore(cur);dirty=cur!==saved;draw()}

// ---- layer operations (layer 0 is the panel background: never deleted or moved) ----
function del(){if(!data||sel<=0)return;data.panels[panel].layers.splice(sel,1);sel=-1;commit();draw()}
function dup(){if(!data||sel<=0)return;const Ls=data.panels[panel].layers,L=Ls[sel];Ls.splice(sel+1,0,Object.assign({},L,{x:L.x+10,y:L.y+10}));sel++;commit();draw()}
function swapSel(j){const Ls=data.panels[panel].layers;[Ls[sel],Ls[j]]=[Ls[j],Ls[sel]];sel=j}
function fwd(){if(!data||sel<=0||sel>=data.panels[panel].layers.length-1)return;swapSel(sel+1);commit();draw()}
function back(){if(!data||sel<=1)return;swapSel(sel-1);commit();draw()}
function nudge(dx,dy){if(!data||sel<=0)return;const L=data.panels[panel].layers[sel];L.x+=dx;L.y+=dy;touch();nudgeLater();draw()}

// ---- canvas: select, move, resize, rotate, zoom, pan ----
const cv=$('#eCv'),wrap=$('#eWrap');
function cvPt(ev){const r=cv.getBoundingClientRect();return[(ev.clientX-r.left)*cv.width/r.width,(ev.clientY-r.top)*cv.height/r.height]}
cv.addEventListener('mousedown',ev=>{if(!data||!panel)return;
 if(ev.button===1||ev.button===2||(ev.button===0&&spaceDown)){ev.preventDefault();pan={x:ev.clientX,y:ev.clientY,l:wrap.scrollLeft,t:wrap.scrollTop};cv.style.cursor='grabbing';return}
 if(ev.button!==0)return;ev.preventDefault();
 if(document.activeElement&&document.activeElement.blur)document.activeElement.blur();
 const V=view(),[mx,my]=cvPt(ev),h=hit(V,mx,my);drag=null;
 if(!h)sel=-1;
 else if(h.t==='body'){sel=h.i;if(sel>0){const L=V.P.layers[sel];drag={k:'move',L,V,ox:L.x,oy:L.y,mx0:mx,my0:my}}}
 else if(h.t==='rot')drag={k:'rot',L:V.P.layers[sel],V,cc:[h.g.cx,h.g.cy]};
 else drag={k:'size',L:V.P.layers[sel],V,g:h.g,hx:h.hx,hy:h.hy,A:corner(h.g,-h.hx,-h.hy)};
 draw()});
cv.addEventListener('mousemove',ev=>{if(!data||drag||pan)return;const V=view(),[mx,my]=cvPt(ev),h=hit(V,mx,my);
 cv.style.cursor=spaceDown?'grab':h?(h.t==='body'?'move':h.t==='rot'?'crosshair':'pointer'):'default'});
cv.addEventListener('contextmenu',e=>e.preventDefault());
cv.addEventListener('wheel',ev=>{if(!data||!ev.deltaY)return;ev.preventDefault();
 const r=wrap.getBoundingClientRect(),mx=ev.clientX-r.left,my=ev.clientY-r.top,old=zoom;
 zoom=Math.min(4,Math.max(0.25,zoom*(ev.deltaY<0?1.15:1/1.15)));const k=zoom/old,cx=wrap.scrollLeft+mx,cy=wrap.scrollTop+my;
 const V=view();cv.width=Math.round((V.x1-V.x0)*V.s);cv.height=Math.round((V.y1-V.y0)*V.s);
 wrap.scrollLeft=cx*k-mx;wrap.scrollTop=cy*k-my;draw()},{passive:false});
window.addEventListener('mousemove',ev=>{
 if(pan){wrap.scrollLeft=pan.l-(ev.clientX-pan.x);wrap.scrollTop=pan.t-(ev.clientY-pan.y);return}
 if(!drag||!data)return;const M=cvPt(ev),D=drag,L=D.L,V=D.V;
 if(D.k==='move'){L.x=D.ox+(M[0]-D.mx0)/V.s;L.y=D.oy-(M[1]-D.my0)/V.s}
 else if(D.k==='rot'){let th=Math.atan2(-(M[0]-D.cc[0]),-(M[1]-D.cc[1]))*180/Math.PI;if(ev.shiftKey)th=Math.round(th/15)*15;L.spin=th}
 else{const g=D.g,dx=M[0]-D.A[0],dy=M[1]-D.A[1];
  const lu=dx*g.u[0]+dy*g.u[1],lv=dx*g.v[0]+dy*g.v[1];
  const Wn=D.hx?Math.max(4,D.hx*lu):g.w,Hn=D.hy?Math.max(4,D.hy*lv):g.h;
  const c=[D.A[0]+D.hx*Wn/2*g.u[0]+D.hy*Hn/2*g.v[0],D.A[1]+D.hx*Wn/2*g.u[1]+D.hy*Hn/2*g.v[1]];
  const p=toP(V,c[0],c[1]);L.x=p[0];L.y=p[1];
  if(D.hx)L.sx=Wn/(K*V.s);if(D.hy)L.sy=Hn/(K*V.s)}
 draw()});
window.addEventListener('mouseup',()=>{if(pan){pan=null;cv.style.cursor='';return}if(drag){drag=null;commit();draw()}});

// ---- keyboard (only while the Editor tab is open and no form field has focus) ----
const isOpen=()=>{const t=$('#t_edit');return !!data&&!!t&&!t.classList.contains('hide')};
document.addEventListener('keydown',ev=>{if(!isOpen())return;const tag=ev.target&&ev.target.tagName;
 if(tag==='INPUT'||tag==='SELECT'||tag==='TEXTAREA')return;
 const ctrl=ev.ctrlKey||ev.metaKey,k=ev.key.toLowerCase();
 if(ev.key===' '){spaceDown=true;ev.preventDefault();return}
 if(ctrl&&k==='z'){ev.preventDefault();ev.shiftKey?redo():undo();return}
 if(ctrl&&k==='y'){ev.preventDefault();redo();return}
 if(ctrl)return;
 if(ev.key==='Delete'){ev.preventDefault();del();return}
 const st=ev.shiftKey?10:1,m={ArrowLeft:[-st,0],ArrowRight:[st,0],ArrowUp:[0,st],ArrowDown:[0,-st]}[ev.key];
 if(m&&sel>0){ev.preventDefault();nudge(m[0],m[1])}});
document.addEventListener('keyup',ev=>{if(ev.key===' ')spaceDown=false});

// ---- slot load and save ----
const sel_slot=()=>window.__slot&&window.__slot();
async function load(force){if(!sel_slot())return false;const k=sel_slot()+'|'+$('#zipSel').value;if(!force&&k===key)return true;
 if(dirty&&!window.confirm('Discard the unsaved layer changes?'))return true;
 $('#eInfo').textContent='reading the livery...';data=await api('slot',{slot:sel_slot(),carzip:$('#zipSel').value});shapes=data.shapes;sils={};key=k;sel=-1;
 dirty=false;U=[];R=[];cur=snap();saved=cur;
 const names=Object.keys(data.panels);const ps=$('#ePanel');const old=ps.value;ps.innerHTML='';names.forEach(n=>{const o=document.createElement('option');o.value=n;o.textContent=n+' ('+data.panels[n].layers.length+')';ps.appendChild(o)});
 panel=names.includes(old)?old:(names.find(n=>data.panels[n].layers.length)||names[0]);ps.value=panel;
 $('#eClosedBox').classList.toggle('hide',!!data.have_file);
 await draw();
 // textures for the 3D view
 const tp={};for(const n of names){if(data.panels[n].layers.length){const c=await renderTex(n,1.5);tp[n]={tex:c.toDataURL('image/png').split(',')[1]}}}return tp}
async function save(){if(!data)return;commit();const btn=$('#eSave');const panels={};for(const n of Object.keys(data.panels))panels[n]=data.panels[n].layers;
 setBusy(true,btn,'Saving...');
 try{const r=await api('savelayers',{slot:sel_slot(),panels:panels,game_closed:$('#eClosed').checked});
  if(r.needs_confirm){log(r.message,'warn');return}
  (r.messages||[]).forEach(m=>log(m,'ok'));
  dirty=false;saved=snap();
  const tp=await load(true);if(tp&&tp!==true&&window.__setSlotTex)window.__setSlotTex(tp);
  log('editor: saved and 3D view refreshed','ok')}
 catch(e){log('save: '+e.message,'bad')}
 finally{setBusy(false,btn);updBtns()}}

$('#ePanel').onchange=e=>{panel=e.target.value;sel=-1;draw()};
$('#eReload').onclick=()=>load(true).then(tp=>{if(tp&&tp!==true&&window.__setSlotTex)window.__setSlotTex(tp)}).catch(e=>log('editor: '+e.message,'bad'));
$('#eSave').onclick=save;
$('#eUndo').onclick=undo;$('#eRedo').onclick=redo;$('#eDup').onclick=dup;$('#eFwd').onclick=fwd;$('#eBack').onclick=back;$('#eDel').onclick=del;
document.querySelectorAll('#eForm [data-k]').forEach(el=>{el.addEventListener('input',()=>formIn(el));el.addEventListener('change',()=>{commit();draw()})});
updBtns();
return{load}})();
'''
