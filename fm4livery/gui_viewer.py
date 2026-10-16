"""3D viewer tab (WebGL2, no external libraries): HTML + CSS + JS fragments spliced into the GUI page."""

CSS = r'''
#t_view{display:flex;flex-direction:column;gap:10px}
.vwrap{position:relative;height:min(62vh,640px);min-height:380px;border:1px solid var(--line);border-radius:8px;overflow:hidden;background:#0d0f13}
.vwrap canvas{position:absolute;inset:0;width:100%;height:100%;display:block;touch-action:none}
#vOverlay{pointer-events:none}
.vbar{display:flex;flex-wrap:wrap;gap:6px;align-items:center}
.vbar button{padding:5px 10px;font-size:12px;font-weight:600}
.vbar button.on{background:var(--accent2);color:#fff;border-color:var(--accent2)}
.vbar .sep{width:1px;height:20px;background:var(--line);margin:0 4px}
.vside{display:grid;grid-template-columns:1fr 1fr;gap:12px}
.plist{max-height:190px;overflow:auto;border:1px solid var(--line);border-radius:7px;padding:6px 8px;background:var(--bg);font-size:12px}
.plist label{display:flex;align-items:center;gap:6px;margin:2px 0;color:var(--text);font-size:12px}
.vhint{position:absolute;left:10px;bottom:8px;color:#6d7686;font-size:11px;pointer-events:none}
.vdim{position:absolute;right:10px;bottom:8px;color:#8d97a8;font:11px Consolas,monospace;pointer-events:none;text-align:right}
@media(max-width:900px){.vside{grid-template-columns:1fr}}
'''

HTML = r'''
   <div id="t_view" class="hide">
     <div class="vbar">
       <button class="sec" data-v="iso">Iso</button><button class="sec" data-v="front">Front</button><button class="sec" data-v="rear">Rear</button>
       <button class="sec" data-v="left">Left</button><button class="sec" data-v="right">Right</button><button class="sec" data-v="top">Top</button>
       <span class="sep"></span>
       <button class="sec on" id="vPersp">Perspective</button>
       <span class="sep"></span>
       <button class="sec on" data-m="shaded">Shaded</button><button class="sec" data-m="edges">Shaded + edges</button><button class="sec" data-m="wire">Wireframe</button>
       <span class="sep"></span>
       <button class="sec on" id="vGrid">Grid</button><button class="sec on" id="vLiv">Livery</button><select id="vTex" title="The car's own painted texture (UV set 1 of the car model)" style="width:auto;margin:0;padding:4px 6px;font-size:12px"><option value="0">Car texture: off</option><option value="1" selected>Car texture: baked colour</option><option value="2">Car texture: paint + decals</option></select><button class="sec" id="vFit">Fit view</button>
       <span class="note" id="vStatus" style="margin-left:auto"></span>
     </div>
     <div class="vbar" id="dLockBar"></div>
     <div class="vwrap" id="vWrap"><canvas id="vGL"></canvas><canvas id="vOverlay"></canvas>
       <div class="vhint">left-drag orbit &middot; right/middle-drag pan &middot; wheel zoom &middot; double-click fit</div><div class="vdim" id="vDim"></div></div>
     <div id="dBox3"></div>
     <div class="vside">
       <div><label>Parts</label><div class="plist" id="vParts"></div>
         <div class="row" style="margin-top:8px"><div><label>Paint colour</label><input type="color" id="vPaint" value="#cfd3da" style="width:100%;height:32px;padding:2px;background:var(--bg);border:1px solid var(--line);border-radius:7px"></div></div></div>
       <div><label>Livery placement <span class="note">(the 3D fit is automatic and approximate)</span></label>
         <select id="vCalPanel"></select>
         <label>Scale <b id="vScV">0%</b></label><input type="range" id="vSc" min="-25" max="25" step="0.5" value="0">
         <label>Move across <b id="vDxV">0</b></label><input type="range" id="vDx" min="-80" max="80" step="1" value="0">
         <label>Move up <b id="vDyV">0</b></label><input type="range" id="vDy" min="-80" max="80" step="1" value="0">
         <p class="note" id="vFitNote">Run a preview on the Image to livery tab and it appears here.</p></div>
     </div>
   </div>
'''

JS = r'''
const V=(()=>{
const m4={
 id:()=>new Float32Array([1,0,0,0,0,1,0,0,0,0,1,0,0,0,0,1]),
 mul(a,b){const o=new Float32Array(16);for(let i=0;i<4;i++)for(let j=0;j<4;j++){let s=0;for(let k=0;k<4;k++)s+=a[k*4+j]*b[i*4+k];o[i*4+j]=s}return o},
 persp(f,a,n,fa){const t=1/Math.tan(f/2),o=new Float32Array(16);o[0]=t/a;o[5]=t;o[10]=(fa+n)/(n-fa);o[11]=-1;o[14]=2*fa*n/(n-fa);return o},
 ortho(h,a,n,fa){const o=new Float32Array(16);o[0]=1/(h*a);o[5]=1/h;o[10]=-2/(fa-n);o[14]=-(fa+n)/(fa-n);o[15]=1;return o},
 look(e,c,u){let z=[e[0]-c[0],e[1]-c[1],e[2]-c[2]];let l=Math.hypot(...z);z=z.map(v=>v/l);
  let x=[u[1]*z[2]-u[2]*z[1],u[2]*z[0]-u[0]*z[2],u[0]*z[1]-u[1]*z[0]];l=Math.hypot(...x);x=x.map(v=>v/l);
  const y=[z[1]*x[2]-z[2]*x[1],z[2]*x[0]-z[0]*x[2],z[0]*x[1]-z[1]*x[0]];
  return new Float32Array([x[0],y[0],z[0],0,x[1],y[1],z[1],0,x[2],y[2],z[2],0,-(x[0]*e[0]+x[1]*e[1]+x[2]*e[2]),-(y[0]*e[0]+y[1]*e[1]+y[2]*e[2]),-(z[0]*e[0]+z[1]*e[1]+z[2]*e[2]),1])}
};
const cv=$('#vGL'),ov=$('#vOverlay');let gl=null,ok=false;let geo=null;const hooks={};
const VIEWS={left:{f:[1,0,0],r:[0,0,1],u:[0,1,0],az:-Math.PI/2,el:0},right:{f:[-1,0,0],r:[0,0,-1],u:[0,1,0],az:Math.PI/2,el:0},front:{f:[0,0,1],r:[-1,0,0],u:[0,1,0],az:Math.PI,el:0},rear:{f:[0,0,-1],r:[1,0,0],u:[0,1,0],az:0,el:0},top:{f:[0,-1,0],r:[1,0,0],u:[0,0,-1],az:Math.PI,el:1.57}};
let atlasTex=null,atlasTexA=null,atlasOn=false;let vaoL=null,axB=null,model=null,parts=[],bufs=null,progM=null,progL=null,texs={},texOn=[0,0,0,0,0],proj=null,cal={},slotKey=null;
const PAN=['left','right','front','rear','roof'];
const st={lock:null,atl:1,az:3.9,el:0.35,dist:6,tx:0,ty:0.7,tz:0,ortho:false,mode:'shaded',grid:true,liv:true,paint:[0.81,0.83,0.855]};
const VS=`#version 300 es
layout(location=0) in vec3 aP;layout(location=1) in vec3 aN;layout(location=2) in vec2 aUV;uniform mat4 uVP;out vec3 vP;out vec3 vN;out vec2 vUV;
void main(){vP=aP;vN=aN;vUV=aUV;gl_Position=uVP*vec4(aP,1.0);}`;
const FS=`#version 300 es
precision highp float;in vec3 vP;in vec3 vN;in vec2 vUV;uniform sampler2D uAtlas;uniform sampler2D uAtlasA;uniform float uAtl;uniform vec4 uCol;uniform float uPaint;uniform float uLiv;uniform vec3 uEye;uniform float uFlat;
uniform sampler2D uT0;uniform sampler2D uT1;uniform sampler2D uT2;uniform sampler2D uT3;uniform sampler2D uT4;
uniform vec4 uHas;uniform float uHas4;uniform vec3 uAX[5];uniform vec3 uAY[5];uniform vec4 uPR[5];uniform vec4 uBX[5];out vec4 o;
vec4 smp(int i,vec2 uv){if(i==0)return texture(uT0,uv);if(i==1)return texture(uT1,uv);if(i==2)return texture(uT2,uv);if(i==3)return texture(uT3,uv);return texture(uT4,uv);}
void main(){vec3 n=normalize(vN);vec3 V=normalize(uEye-vP);if(dot(n,V)<0.0&&uCol.a>0.99)n=-n;
 vec3 base=uCol.rgb;float a=uCol.a;
 if(uFlat<0.5&&uAtl>0.5){vec3 tx=texture(uAtlas,vUV).rgb;float ta=texture(uAtlasA,vUV).r;base=(uAtl<1.5)?tx:mix(base,tx,ta);}
 if(uFlat<0.5&&uPaint>0.5&&uLiv>0.5){
  float d[5];d[0]=-n.x;d[1]=n.x;d[2]=-n.z;d[3]=n.z;d[4]=n.y*1.15;int b=0;float bd=d[0];for(int i=1;i<5;i++){if(d[i]>bd){bd=d[i];b=i;}}
  bool has=(b==0&&uHas.x>0.5)||(b==1&&uHas.y>0.5)||(b==2&&uHas.z>0.5)||(b==3&&uHas.w>0.5)||(b==4&&uHas4>0.5);
  if(has){float px=dot(vP,uAX[b])*uPR[b].x+uPR[b].y;float py=dot(vP,uAY[b])*uPR[b].x+uPR[b].z;
   vec2 uv=vec2((px-uBX[b].x)/(uBX[b].y-uBX[b].x),(py-uBX[b].z)/(uBX[b].w-uBX[b].z));
   if(uv.x>0.0&&uv.x<1.0&&uv.y>0.0&&uv.y<1.0){vec4 t=smp(b,uv);base=base*(1.0-t.a)+t.rgb;}}}
 if(uFlat>0.5){o=vec4(uCol.rgb,1.0);return;}
 vec3 L=normalize(vec3(-0.45,0.85,-0.35));vec3 L2=normalize(vec3(0.6,0.3,0.7));
 float dif=max(dot(n,L),0.0)*0.8+max(dot(n,L2),0.0)*0.25;float hemi=0.35+0.25*n.y;
 vec3 H=normalize(L+V);float sp=pow(max(dot(n,H),0.0),48.0)*(uPaint>0.5?0.55:0.25);
 vec3 c=base*(hemi+dif)+vec3(sp);
 float rim=pow(1.0-max(dot(n,V),0.0),3.0)*0.18;c+=vec3(rim)*vec3(0.6,0.7,0.9);
 o=vec4(c,a);}`;
const VSL=`#version 300 es
layout(location=0) in vec3 aP;uniform mat4 uVP;void main(){gl_Position=uVP*vec4(aP,1.0);}`;
const FSL=`#version 300 es
precision mediump float;uniform vec4 uC;out vec4 o;void main(){o=uC;}`;
function sh(t,s){const x=gl.createShader(t);gl.shaderSource(x,s);gl.compileShader(x);if(!gl.getShaderParameter(x,gl.COMPILE_STATUS))throw new Error(gl.getShaderInfoLog(x));return x}
function prog(v,f){const p=gl.createProgram();gl.attachShader(p,sh(gl.VERTEX_SHADER,v));gl.attachShader(p,sh(gl.FRAGMENT_SHADER,f));gl.linkProgram(p);if(!gl.getProgramParameter(p,gl.LINK_STATUS))throw new Error(gl.getProgramInfoLog(p));return p}
function init(){if(gl||ok===null)return ok;try{gl=cv.getContext('webgl2',{antialias:true,alpha:false});if(!gl)throw new Error('WebGL2 is not available in this browser');
 progM=prog(VS,FS);progL=prog(VSL,FSL);vaoL=gl.createVertexArray();axB=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,axB);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array([0,0,0,1,0,0,0,0,0,0,1,0,0,0,0,0,0,1]),gl.STATIC_DRAW);ok=true;}catch(e){ok=null;$('#vStatus').textContent='3D view unavailable: '+e.message;$('#vStatus').className='note bad'}return ok}
function f32(b){const s=atob(b);const u=new Uint8Array(s.length);for(let i=0;i<s.length;i++)u[i]=s.charCodeAt(i);return u.buffer}
function setModel(m){model=m;parts=m.parts;proj=m.proj||{};
 const pos=new Float32Array(f32(m.pos)),nrm=new Float32Array(f32(m.nrm)),idx=new Uint32Array(f32(m.idx));
 if(bufs){gl.deleteBuffer(bufs.p);gl.deleteBuffer(bufs.n);gl.deleteBuffer(bufs.i);gl.deleteBuffer(bufs.e);gl.deleteBuffer(bufs.u);gl.deleteVertexArray(bufs.vao)}
 const vao=gl.createVertexArray();gl.bindVertexArray(vao);
 const p=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,p);gl.bufferData(gl.ARRAY_BUFFER,pos,gl.STATIC_DRAW);
 const lp=0;gl.enableVertexAttribArray(lp);gl.vertexAttribPointer(lp,3,gl.FLOAT,false,0,0);
 const n=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,n);gl.bufferData(gl.ARRAY_BUFFER,nrm,gl.STATIC_DRAW);
 const ln=1;gl.enableVertexAttribArray(ln);gl.vertexAttribPointer(ln,3,gl.FLOAT,false,0,0);
 const u=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,u);gl.bufferData(gl.ARRAY_BUFFER,m.uv?new Float32Array(f32(m.uv)):new Float32Array(pos.length/3*2),gl.STATIC_DRAW);gl.enableVertexAttribArray(2);gl.vertexAttribPointer(2,2,gl.FLOAT,false,0,0);
 const i=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,i);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,idx,gl.STATIC_DRAW);
 const ed=new Uint32Array(idx.length*2);for(let t=0;t<idx.length;t+=3){const o=t*2;ed[o]=idx[t];ed[o+1]=idx[t+1];ed[o+2]=idx[t+1];ed[o+3]=idx[t+2];ed[o+4]=idx[t+2];ed[o+5]=idx[t]}
 const e=gl.createBuffer();gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,e);gl.bufferData(gl.ELEMENT_ARRAY_BUFFER,ed,gl.STATIC_DRAW);
 gl.bindVertexArray(null);bufs={p,n,u,i,e,vao,nIdx:idx.length};geo={pos,nrm,uv:m.uv?new Float32Array(f32(m.uv)):null,idx,parts:m.parts,model:m};loadAtlas(m.atlas,m.atlas_a);if(hooks.model)hooks.model(m);
 // grid + axes
 const bb=m.bbox,L=Math.max(bb[1][0]-bb[0][0],bb[1][2]-bb[0][2]);
 const step=0.5,ext=Math.ceil(L*0.9/step)*step,ln_=[];
 for(let x=-ext;x<=ext+1e-6;x+=step){ln_.push(x,0,-ext,x,0,ext,-ext,0,x,ext,0,x)}
 const gb=gl.createBuffer();gl.bindBuffer(gl.ARRAY_BUFFER,gb);gl.bufferData(gl.ARRAY_BUFFER,new Float32Array(ln_),gl.STATIC_DRAW);bufs.grid=gb;bufs.nGrid=ln_.length/3;bufs.ext=ext;
 // part list
 const names={};parts.forEach(p=>{const k=p.name==='wheel'?'wheels':p.name;(names[k]=names[k]||[]).push(p)});
 const box=$('#vParts');box.innerHTML='';Object.keys(names).sort().forEach(k=>{const lb=document.createElement('label');const c=document.createElement('input');c.type='checkbox';c.checked=!names[k][0].hidden;
  c.onchange=()=>{names[k].forEach(p=>p.hidden=!c.checked)};lb.appendChild(c);lb.appendChild(document.createTextNode(k));box.appendChild(lb)});
 const sel=$('#vCalPanel');sel.innerHTML='';PAN.forEach(p=>{if(proj[p]){const o=document.createElement('option');o.value=p;o.textContent=p;sel.appendChild(o);cal[p]=cal[p]||{sc:0,dx:0,dy:0}}});
 syncCal();fit();
 const d=[bb[1][0]-bb[0][0],bb[1][1]-bb[0][1],bb[1][2]-bb[0][2]];$('#vDim').innerHTML='L '+d[2].toFixed(2)+' m &nbsp; W '+d[0].toFixed(2)+' m &nbsp; H '+d[1].toFixed(2)+' m<br>wheelbase '+m.wheelbase.toFixed(2)+' m';
 $('#vStatus').textContent=parts.length+' meshes, '+Math.round(idx.length/3000)+'k triangles';$('#vStatus').className='note ok'}
function fit(){if(!model)return;const bb=model.bbox;st.tx=(bb[0][0]+bb[1][0])/2;st.ty=(bb[0][1]+bb[1][1])/2;st.tz=(bb[0][2]+bb[1][2])/2;
 const r=Math.hypot(bb[1][0]-bb[0][0],bb[1][1]-bb[0][1],bb[1][2]-bb[0][2])/2;st.dist=r/Math.tan(0.4)*0.8;}
function setView(n){st.lock=null;const t={iso:[3.9,0.35],front:[Math.PI,0],rear:[0,0],left:[-Math.PI/2,0],right:[Math.PI/2,0],top:[Math.PI,1.5533]}[n];st.az=t[0];st.el=t[1];fit();}
// camera: azimuth 0 = camera on +z looking -z (rear view); pi = front view (car faces -z)
function camPos(){const c=Math.cos(st.el);return[st.tx+st.dist*c*Math.sin(st.az),st.ty+st.dist*Math.sin(st.el),st.tz+st.dist*c*Math.cos(st.az)]}
function vp(){const w=cv.width,h=cv.height,a=w/h,e=camPos();const up=[0,1,0];const view=m4.look(e,[st.tx,st.ty,st.tz],up);
 const r=model?Math.hypot(model.bbox[1][0]-model.bbox[0][0],model.bbox[1][2]-model.bbox[0][2]):5;
 const pr=st.ortho?m4.ortho(st.dist*0.42,a,-r*6,r*6):m4.persp(0.8,a,Math.max(st.dist*0.02,0.01),st.dist+r*6);return{m:m4.mul(pr,view),e}}
function mkTex(b64,cb){const img=new Image();img.onload=()=>{const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
  gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);gl.generateMipmap(gl.TEXTURE_2D);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);cb(t)};img.src='data:image/png;base64,'+b64}
function loadAtlas(b64,a64){atlasOn=false;$('#vTex').style.display=b64?'':'none';if(!b64||!a64||!gl)return;let n=0;const done=()=>{if(++n===2)atlasOn=true};
 mkTex(b64,t=>{if(atlasTex)gl.deleteTexture(atlasTex);atlasTex=t;done()});mkTex(a64,t=>{if(atlasTexA)gl.deleteTexture(atlasTexA);atlasTexA=t;done()})}
function loadTex(i,url){const img=new Image();img.onload=()=>{if(!gl)return;if(texs[i])gl.deleteTexture(texs[i]);const t=gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);
  gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,true);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,true);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,img);
  gl.generateMipmap(gl.TEXTURE_2D);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);
  gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);
  texs[i]=t;texOn[i]=1};img.src=url}
function setLivery(panels){PAN.forEach((p,i)=>{texOn[i]=0;if(panels&&panels[p]&&panels[p].tex&&gl)loadTex(i,'data:image/png;base64,'+panels[p].tex)});
 const n=panels?Object.keys(panels).filter(k=>PAN.includes(k)).length:0;$('#vFitNote').textContent=n?('Showing the last preview on '+n+' panel(s). '+fitInfo()):'Run a preview on the Image to livery tab and it appears here.'}
function fitInfo(){const q=PAN.filter(p=>proj[p]).map(p=>p+' '+Math.round(proj[p].iou*100)+'%');return q.length?'Auto-fit match: '+q.join(', ')+'.':''}
function syncCal(){const p=$('#vCalPanel').value;if(!p||!cal[p])return;const c=cal[p];$('#vSc').value=c.sc;$('#vDx').value=c.dx;$('#vDy').value=c.dy;$('#vScV').textContent=c.sc+'%';$('#vDxV').textContent=c.dx;$('#vDyV').textContent=c.dy}
['vSc','vDx','vDy'].forEach(id=>$('#'+id).oninput=()=>{const p=$('#vCalPanel').value;if(!cal[p])return;cal[p]={sc:+$('#vSc').value,dx:+$('#vDx').value,dy:+$('#vDy').value};syncCal()});
$('#vCalPanel').onchange=syncCal;
function lock(n){const v=VIEWS[n];if(!v)return;st.lock=n;st.ortho=true;st.az=v.az;st.el=v.el;fit();$('#vPersp').textContent='Orthographic'}
function unlock(){st.lock=null}
function view2d(){const v=VIEWS[st.lock];if(!v)return null;const W=cv.clientWidth,H=cv.clientHeight,h=st.dist*0.42,k=H/(2*h);const c=[st.tx,st.ty,st.tz];const dot=(p,q)=>p[0]*q[0]+p[1]*q[1]+p[2]*q[2];const ca=dot(c,v.r),cb=dot(c,v.u);
 return{W,H,h,k,ca,cb,view:v,name:st.lock,toS:(A,B)=>[W/2+(A-ca)*k,H/2-(B-cb)*k],toW:(x,y)=>[(x-W/2)/k+ca,-((y-H/2)/k)+cb]}}
function getProj(p){const q=proj&&proj[p];if(!q)return null;const c=cal[p]||{sc:0,dx:0,dy:0};return{ax:q.ax,sx:q.sx,ay:q.ay,sy:q.sy,s:q.s*(1+c.sc/100),cx:q.cx+c.dx,cy:q.cy+c.dy,box:q.box}}
function upTex(c,old){const t=old||gl.createTexture();gl.bindTexture(gl.TEXTURE_2D,t);gl.pixelStorei(gl.UNPACK_PREMULTIPLY_ALPHA_WEBGL,false);gl.pixelStorei(gl.UNPACK_FLIP_Y_WEBGL,false);gl.texImage2D(gl.TEXTURE_2D,0,gl.RGBA,gl.RGBA,gl.UNSIGNED_BYTE,c);gl.generateMipmap(gl.TEXTURE_2D);
 gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MIN_FILTER,gl.LINEAR_MIPMAP_LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_MAG_FILTER,gl.LINEAR);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_S,gl.CLAMP_TO_EDGE);gl.texParameteri(gl.TEXTURE_2D,gl.TEXTURE_WRAP_T,gl.CLAMP_TO_EDGE);return t}
function setAtlasCanvases(rgb,alpha){if(!gl||!model)return;atlasTex=upTex(rgb,atlasTex);atlasTexA=upTex(alpha,atlasTexA);atlasOn=true;$('#vTex').style.display=''}
function draw(){requestAnimationFrame(draw);if(!ok||!model||!bufs||$('#t_view').classList.contains('hide'))return;
 const W=cv.clientWidth,H=cv.clientHeight,dpr=window.devicePixelRatio||1;if(cv.width!==Math.round(W*dpr)){cv.width=ov.width=Math.round(W*dpr);cv.height=ov.height=Math.round(H*dpr)}
 gl.viewport(0,0,cv.width,cv.height);gl.clearColor(0.055,0.06,0.075,1);gl.clear(gl.COLOR_BUFFER_BIT|gl.DEPTH_BUFFER_BIT);gl.enable(gl.DEPTH_TEST);
 const {m,e}=vp();
 if(st.grid){gl.useProgram(progL);gl.bindVertexArray(vaoL);gl.enableVertexAttribArray(0);gl.uniformMatrix4fv(gl.getUniformLocation(progL,'uVP'),false,m);gl.bindBuffer(gl.ARRAY_BUFFER,bufs.grid);gl.vertexAttribPointer(0,3,gl.FLOAT,false,0,0);
  gl.uniform4f(gl.getUniformLocation(progL,'uC'),0.22,0.25,0.31,1);gl.drawArrays(gl.LINES,0,bufs.nGrid);
  gl.bindBuffer(gl.ARRAY_BUFFER,axB);gl.vertexAttribPointer(0,3,gl.FLOAT,false,0,0);
  [[0,[0.9,0.25,0.25]],[2,[0.3,0.85,0.4]],[4,[0.3,0.55,1]]].forEach(([o,c])=>{gl.uniform4f(gl.getUniformLocation(progL,'uC'),c[0],c[1],c[2],1);gl.drawArrays(gl.LINES,o,2)});gl.bindVertexArray(null)}
 gl.useProgram(progM);const U=n=>gl.getUniformLocation(progM,n);gl.uniformMatrix4fv(U('uVP'),false,m);gl.uniform3f(U('uEye'),e[0],e[1],e[2]);
 const ax=[],ay=[],pr=[],bx=[];PAN.forEach((p,i)=>{const q=proj[p];if(!q){ax.push(0,0,0);ay.push(0,0,0);pr.push(1,0,0,0);bx.push(0,1,0,1);return}
  const c=cal[p]||{sc:0,dx:0,dy:0};const X=[0,0,0],Y=[0,0,0];X[q.ax]=q.sx;Y[q.ay]=q.sy;ax.push(...X);ay.push(...Y);
  const k=1+c.sc/100;const s=q.s*k;pr.push(s,q.cx+c.dx,q.cy+c.dy,0);bx.push(...q.box)});
 gl.uniform3fv(U('uAX[0]'),ax);gl.uniform3fv(U('uAY[0]'),ay);gl.uniform4fv(U('uPR[0]'),pr);gl.uniform4fv(U('uBX[0]'),bx);
 for(let i=0;i<5;i++){gl.activeTexture(gl.TEXTURE0+i);gl.bindTexture(gl.TEXTURE_2D,texs[i]||null);gl.uniform1i(U('uT'+i),i)}
 gl.activeTexture(gl.TEXTURE0+5);gl.bindTexture(gl.TEXTURE_2D,atlasTex||null);gl.uniform1i(U('uAtlas'),5);gl.activeTexture(gl.TEXTURE0+6);gl.bindTexture(gl.TEXTURE_2D,atlasTexA||null);gl.uniform1i(U('uAtlasA'),6);
 gl.uniform4f(U('uHas'),texOn[0],texOn[1],texOn[2],texOn[3]);gl.uniform1f(U('uHas4'),texOn[4]);gl.uniform1f(U('uLiv'),st.liv?1:0);
 gl.bindVertexArray(bufs.vao);const wire=st.mode==='wire';
 const passes=[false,true];
 for(const glassPass of passes){
  if(glassPass){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA);gl.depthMask(false)}else{gl.disable(gl.BLEND);gl.depthMask(true)}
  if(!wire){gl.enable(gl.POLYGON_OFFSET_FILL);gl.polygonOffset(1,1);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,bufs.i);
   for(const p of parts){if(p.hidden)continue;const isG=p.cat==='glass';if(isG!==glassPass)continue;let c=model.colors[p.cat];
    const col=p.cat==='paint'?[st.paint[0],st.paint[1],st.paint[2],1]:c;gl.uniform4f(U('uCol'),col[0],col[1],col[2],col[3]);gl.uniform1f(U('uPaint'),p.cat==='paint'?1:0);gl.uniform1f(U('uFlat'),0);gl.uniform1f(U('uAtl'),(atlasOn&&p.atlas)?st.atl:0);
    gl.drawElements(gl.TRIANGLES,p.n,gl.UNSIGNED_INT,p.i0*4)}
   gl.disable(gl.POLYGON_OFFSET_FILL)}
 }
 gl.depthMask(true);gl.disable(gl.BLEND);
 if(st.mode!=='shaded'){gl.useProgram(progL);gl.bindVertexArray(vaoL);gl.enableVertexAttribArray(0);gl.bindBuffer(gl.ARRAY_BUFFER,bufs.p);gl.vertexAttribPointer(0,3,gl.FLOAT,false,0,0);
  gl.uniformMatrix4fv(gl.getUniformLocation(progL,'uVP'),false,m);gl.bindBuffer(gl.ELEMENT_ARRAY_BUFFER,bufs.e);
  gl.uniform4f(gl.getUniformLocation(progL,'uC'),wire?0.55:0.0,wire?0.8:0.0,wire?1:0.0,wire?0.9:0.55);if(!wire){gl.enable(gl.BLEND);gl.blendFunc(gl.SRC_ALPHA,gl.ONE_MINUS_SRC_ALPHA)}
  for(const p of parts){if(p.hidden)continue;gl.drawElements(gl.LINES,p.n*2,gl.UNSIGNED_INT,p.i0*8)}
  gl.disable(gl.BLEND);gl.bindVertexArray(null)}
 // axis gizmo
 const c2=ov.getContext('2d');c2.clearRect(0,0,ov.width,ov.height);const g=44*dpr,ox=g*1.5,oy=ov.height-g*2.3;
 const view=m4.look([0,0,0].map((_,i)=>camPos()[i]-[st.tx,st.ty,st.tz][i]),[0,0,0],[0,1,0]);
 [['X',[1,0,0],'#e64545'],['Y',[0,1,0],'#4cc38a'],['Z',[0,0,1],'#4aa3ff']].forEach(([n,v,col])=>{
  const x=view[0]*v[0]+view[4]*v[1]+view[8]*v[2],y=view[1]*v[0]+view[5]*v[1]+view[9]*v[2];
  c2.strokeStyle=col;c2.fillStyle=col;c2.lineWidth=2*dpr;c2.beginPath();c2.moveTo(ox,oy);c2.lineTo(ox+x*g,oy-y*g);c2.stroke();c2.font=(11*dpr)+'px sans-serif';c2.fillText(n,ox+x*g*1.18-3*dpr,oy-y*g*1.18+4*dpr)});
 c2.fillStyle='#8d97a8';c2.font=(10*dpr)+'px sans-serif';c2.fillText('car front = -Z',ox-g*0.9,oy+g*1.15);if(hooks.overlay){c2.save();c2.scale(dpr,dpr);hooks.overlay(c2);c2.restore()}
}
// interaction
let drag=null;
cv.addEventListener('contextmenu',e=>e.preventDefault());
cv.addEventListener('pointerdown',e=>{if(hooks.down&&hooks.down(e)){cv.setPointerCapture(e.pointerId);return}cv.setPointerCapture(e.pointerId);drag={x:e.clientX,y:e.clientY,b:e.button,shift:e.shiftKey}});
cv.addEventListener('pointerup',e=>{if(hooks.up)hooks.up(e);drag=null});
cv.addEventListener('pointermove',e=>{if(hooks.move&&hooks.move(e))return;if(!drag)return;const dx=e.clientX-drag.x,dy=e.clientY-drag.y;drag.x=e.clientX;drag.y=e.clientY;
 if(drag.b===0&&!drag.shift&&!st.lock){st.az-=dx*0.007;st.el=Math.max(-1.5,Math.min(1.5533,st.el+dy*0.007))}
 else{const s=st.ortho?2*st.dist*0.42/cv.clientHeight:st.dist*0.0016;const az=st.az,el=st.el;
  const rx=[Math.cos(az),0,-Math.sin(az)],uy=[-Math.sin(el)*Math.sin(az),Math.cos(el),-Math.sin(el)*Math.cos(az)];
  st.tx+=(-dx*rx[0]+dy*uy[0])*s;st.ty+=(dy*uy[1])*s;st.tz+=(-dx*rx[2]+dy*uy[2])*s}});
cv.addEventListener('wheel',e=>{e.preventDefault();st.dist*=Math.exp(e.deltaY*0.0012);st.dist=Math.max(0.3,Math.min(60,st.dist))},{passive:false});
cv.addEventListener('dblclick',fit);
document.querySelectorAll('#t_view [data-v]').forEach(b=>b.onclick=()=>setView(b.dataset.v));
document.querySelectorAll('#t_view [data-m]').forEach(b=>b.onclick=()=>{st.mode=b.dataset.m;document.querySelectorAll('#t_view [data-m]').forEach(x=>x.classList.toggle('on',x===b))});
$('#vPersp').onclick=e=>{st.ortho=!st.ortho;e.target.textContent=st.ortho?'Orthographic':'Perspective'};
$('#vGrid').onclick=e=>{st.grid=!st.grid;e.target.classList.toggle('on',st.grid)};
$('#vLiv').onclick=e=>{st.liv=!st.liv;e.target.classList.toggle('on',st.liv)};
$('#vFit').onclick=fit;$('#vTex').onchange=e=>{st.atl=+e.target.value};
$('#vPaint').oninput=e=>{const h=e.target.value;st.paint=[1,3,5].map(i=>parseInt(h.substr(i,2),16)/255)};
requestAnimationFrame(draw);
return{init,setModel,setLivery,hooks,lock,unlock,view2d,getProj,setAtlasCanvases,st,cv,getGeo:()=>geo,keyFor:k=>{if(slotKey===k)return false;slotKey=k;return true}}})();
'''
