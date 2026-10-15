"""Editor tab: shows the livery that is in the selected slot (layers per panel, real vinyl shapes). Fragments spliced into the GUI page."""

CSS = r'''
#t_edit{display:flex;flex-direction:column;gap:10px}
.ecanvas{background:#0d0f13;border:1px solid var(--line);border-radius:8px;display:block;max-width:100%}
.elist{max-height:360px;overflow:auto;border:1px solid var(--line);border-radius:7px;background:var(--bg);font-size:12px}
.elist div{display:flex;gap:8px;align-items:center;padding:3px 8px;border-bottom:1px solid var(--line);cursor:pointer}
.elist div:hover{background:var(--panel2)}.elist div.sel{background:#223a57}
.sw{width:14px;height:14px;border-radius:3px;border:1px solid #fff3;flex:0 0 auto}
.egrid{display:grid;grid-template-columns:1fr 280px;gap:12px}
@media(max-width:900px){.egrid{grid-template-columns:1fr}}
'''

HTML = r'''
   <div id="t_edit" class="hide">
     <div class="row"><div style="flex:0 0 180px"><label>Panel</label><select id="ePanel"></select></div>
       <div style="flex:0 0 auto;align-self:flex-end"><button class="sec" id="eReload">Reload from slot</button></div>
       <div class="note" id="eInfo" style="align-self:flex-end"></div></div>
     <div class="egrid"><div><canvas id="eCv" class="ecanvas"></canvas></div>
       <div><label>Layers (bottom to top)</label><div class="elist" id="eList"></div></div></div>
   </div>
'''

JS = r'''
const E=(()=>{
const K=124,SC=248;let data=null,shapes={},panel=null,sel=-1,sils={},key=null;
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
async function draw(){if(!data||!panel)return;const P=data.panels[panel],[x0,x1,y0,y1]=P.box;const cv=$('#eCv');const s=Math.min(1.6,Math.max(0.5,960/(x1-x0)));
 cv.width=Math.round((x1-x0)*s);cv.height=Math.round((y1-y0)*s);const ctx=cv.getContext('2d');
 ctx.fillStyle='#14161a';ctx.fillRect(0,0,cv.width,cv.height);const sil=await silImg(panel);
 const t=await renderTex(panel,s);const bg=document.createElement('canvas');bg.width=cv.width;bg.height=cv.height;const b=bg.getContext('2d');b.drawImage(sil,0,0,cv.width,cv.height);b.globalCompositeOperation='source-in';b.fillStyle='#2b2f38';b.fillRect(0,0,cv.width,cv.height);
 ctx.drawImage(bg,0,0);ctx.drawImage(t,0,0);
 if(sel>=0&&P.layers[sel]){const L=P.layers[sel];ctx.strokeStyle='#4aa3ff';ctx.lineWidth=2;ctx.strokeRect((L.x-x0-K*L.sx/2)*s,(y1-L.y-K*L.sy/2)*s,K*L.sx*s,K*L.sy*s)}
 const list=$('#eList');list.innerHTML='';P.layers.forEach((L,i)=>{const d=document.createElement('div');if(i===sel)d.className='sel';const [r,g,bb,a]=argb(L.argb);
  d.innerHTML='<span class="sw" style="background:rgba('+r+','+g+','+bb+','+(a/255)+')"></span><span>#'+(i+1)+'</span><span class="note">shape '+L.shape+'</span><span class="note" style="margin-left:auto">'+Math.round(L.x)+', '+Math.round(L.y)+'</span>';
  d.onclick=()=>{sel=i;draw()};list.appendChild(d)});
 $('#eInfo').textContent=P.layers.length+' layers on '+panel+(data.missing.length?' - '+data.missing.length+' shape(s) not readable (drawn as boxes)':'')}
async function load(force){if(!sel_slot())return false;const k=sel_slot()+'|'+$('#zipSel').value;if(!force&&k===key)return true;
 $('#eInfo').textContent='reading the livery...';data=await api('slot',{slot:sel_slot(),carzip:$('#zipSel').value});shapes=data.shapes;sils={};key=k;sel=-1;
 const names=Object.keys(data.panels);const ps=$('#ePanel');const old=ps.value;ps.innerHTML='';names.forEach(n=>{const o=document.createElement('option');o.value=n;o.textContent=n+' ('+data.panels[n].layers.length+')';ps.appendChild(o)});
 panel=names.includes(old)?old:(names.find(n=>data.panels[n].layers.length)||names[0]);ps.value=panel;
 if(!data.have_file)$('#eInfo').textContent='this slot has no livery file yet';
 await draw();
 // textures for the 3D view
 const tp={};for(const n of names){if(data.panels[n].layers.length){const c=await renderTex(n,1.5);tp[n]={tex:c.toDataURL('image/png').split(',')[1]}}}return tp}
const sel_slot=()=>window.__slot&&window.__slot();
$('#ePanel').onchange=e=>{panel=e.target.value;sel=-1;draw()};
$('#eReload').onclick=()=>load(true).then(tp=>{if(tp&&window.__setSlotTex)window.__setSlotTex(tp)}).catch(e=>log('editor: '+e.message,'bad'));
$('#eCv').onclick=ev=>{if(!data)return;const P=data.panels[panel],[x0,x1,y0,y1]=P.box,r=ev.target.getBoundingClientRect(),s=ev.target.width/(x1-x0);
 const px=x0+(ev.clientX-r.left)*(ev.target.width/r.width)/s,py=y1-(ev.clientY-r.top)*(ev.target.height/r.height)/s;
 for(let i=P.layers.length-1;i>=0;i--){const L=P.layers[i];if(Math.abs(px-L.x)<=K*L.sx/2&&Math.abs(py-L.y)<=K*L.sy/2&&i>0){sel=i;draw();return}}sel=-1;draw()};
return{load}})();
'''
