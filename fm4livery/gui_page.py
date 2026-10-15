PAGE = r'''<!doctype html>
<html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width, initial-scale=1">
<title>FM4 Livery Tool</title>
<style>
:root{--bg:#14161a;--panel:#1c1f25;--panel2:#242830;--line:#323844;--text:#e8eaee;--mute:#99a1b0;--accent:#4aa3ff;--accent2:#2f7fd6;--ok:#4cc38a;--warn:#f0b34a;--bad:#ff6b6b}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--text);font:14px/1.45 "Segoe UI",system-ui,sans-serif}
header{display:flex;align-items:center;gap:14px;padding:12px 18px;border-bottom:1px solid var(--line);background:var(--panel)}
header h1{font-size:16px;margin:0;font-weight:650}header .sp{flex:1}
.chip{padding:3px 10px;border-radius:99px;background:var(--panel2);border:1px solid var(--line);color:var(--mute);font-size:12px}
.chip.ok{color:var(--ok);border-color:#2c5a46}.chip.bad{color:var(--bad);border-color:#6a3434}
main{display:grid;grid-template-columns:340px 1fr;gap:16px;padding:16px 18px;height:calc(100vh - 56px)}
.card{background:var(--panel);border:1px solid var(--line);border-radius:10px;padding:14px;min-height:0}
.col{display:flex;flex-direction:column;gap:14px;min-height:0;overflow:auto}.col>.card{flex:0 0 auto}
h2{font-size:13px;letter-spacing:.04em;text-transform:uppercase;color:var(--mute);margin:0 0 10px;font-weight:600}
table{width:100%;border-collapse:collapse}th,td{text-align:left;padding:6px 8px;border-bottom:1px solid var(--line);font-size:13px}
tbody tr{cursor:pointer}tbody tr:hover{background:var(--panel2)}tbody tr.sel{background:#223a57}
th{color:var(--mute);font-weight:600;font-size:12px}
.tag{font-size:11px;padding:1px 7px;border-radius:99px;background:var(--panel2);color:var(--mute)}.tag.has{color:var(--ok)}
button,.btn{background:var(--accent2);color:#fff;border:0;border-radius:7px;padding:8px 14px;font:inherit;font-weight:600;cursor:pointer}
button:hover{background:var(--accent)}button.sec{background:var(--panel2);border:1px solid var(--line);color:var(--text)}button:disabled{opacity:.45;cursor:default}
input[type=text],select{background:var(--bg);color:var(--text);border:1px solid var(--line);border-radius:7px;padding:7px 9px;font:inherit;width:100%}
input[type=range]{width:100%}label{display:block;color:var(--mute);font-size:12px;margin:10px 0 4px}
.row{display:flex;gap:12px;flex-wrap:wrap;align-items:flex-end}.row>*{flex:1;min-width:150px}
.tabs{display:flex;gap:6px;margin-bottom:12px}.tabs button{background:var(--panel2);color:var(--mute);border:1px solid var(--line)}.tabs button.on{background:var(--accent2);color:#fff;border-color:var(--accent2)}
.panels{display:grid;grid-template-columns:repeat(auto-fill,minmax(300px,1fr));gap:12px;margin-top:12px}
.pv{background:var(--panel2);border:1px solid var(--line);border-radius:8px;padding:8px}.pv img{width:100%;display:block;border-radius:5px;image-rendering:auto}
.pv b{font-size:12px;color:var(--mute)}.chk{display:inline-flex;align-items:center;gap:6px;margin-right:14px;color:var(--text);font-size:13px}
.note{color:var(--mute);font-size:12px}.warn{color:var(--warn)}.bad{color:var(--bad)}.ok{color:var(--ok)}
#log{max-height:150px;overflow:auto;font:12px/1.5 Consolas,monospace;color:var(--mute);white-space:pre-wrap}
.spin{display:inline-block;width:14px;height:14px;border:2px solid #fff4;border-top-color:#fff;border-radius:50%;animation:s 0.8s linear infinite;vertical-align:-2px;margin-right:6px}@keyframes s{to{transform:rotate(360deg)}}
.hide{display:none!important}
__EDITOR_CSS__
__VIEWER_CSS__
@media(max-width:900px){main{grid-template-columns:1fr;height:auto}}
</style></head><body>
<header><h1>FM4 Livery Tool</h1><span id="chipProfile" class="chip">looking for your game...</span><span class="sp"></span><span class="note" id="ver"></span><button class="sec" id="btnFolder">Change folder</button></header>
<main>
 <div class="col">
  <div class="card hide" id="setupCard">
   <h2>Game folder</h2>
   <p class="note" id="setupMsg">Choose the folder that contains your game or recomp files (the one with <code>default.pe</code> and your profile).</p>
   <div class="row"><div><input type="text" id="rootIn" placeholder="C:\path\to\your\recomp"></div><div style="flex:0 0 auto"><button class="sec hide" id="btnPick">Browse…</button> <button id="btnFind">Find</button></div></div>
   <details style="margin-top:10px" id="advBox"><summary class="note" style="cursor:pointer">Files in different places? (optional)</summary>
    <label>default.pe <span class="note">(your own game file; leave blank to search the folder above)</span></label>
    <div class="row"><div><input type="text" id="peIn" placeholder="C:\path\to\default.pe"></div><div style="flex:0 0 auto"><button class="sec hide" id="btnPickPe">Browse…</button></div></div>
    <label>Media folder <span class="note">(has the cars folder and db/gamedb.slt; gives car names and finds car zips)</span></label>
    <div class="row"><div><input type="text" id="mediaIn" placeholder="C:\path\to\Media"></div><div style="flex:0 0 auto"><button class="sec hide" id="btnPickMedia">Browse…</button></div></div>
   </details>
   <div id="profPick" class="hide"><label>Profile</label><select id="profSel"></select></div>
  </div>
  <div class="card"><h2>Garage</h2>
   <table><thead><tr><th>Slot</th><th>Car</th><th>Livery</th></tr></thead><tbody id="garage"><tr><td colspan="3" class="note">no profile loaded</td></tr></tbody></table>
   <p class="note" id="garNote"></p></div>
 </div>
 <div class="col">
  <div class="card">
   <div class="tabs"><button data-t="make" class="on">Image to livery</button><button data-t="share" >Import / export</button><button data-t="edit">Editor</button><button data-t="view">3D view</button><button data-t="bak">Backups</button></div>
   <div id="t_make">
     <div class="note" id="selInfo">Pick a garage slot on the left.</div>
     <div class="row"><div><label>Image</label><input type="file" id="img" accept="image/*"></div>
       <div><label>Car zip <span class="note">(only if the car isn't found automatically)</span></label><select id="zipSel"><option value="">automatic</option></select></div></div>
     <label>Panels</label><div id="panelBoxes">
       <label class="chk"><input type="checkbox" value="left" checked>left</label><label class="chk"><input type="checkbox" value="right" checked>right</label>
       <label class="chk"><input type="checkbox" value="front">front</label><label class="chk"><input type="checkbox" value="rear">rear</label>
       <label class="chk"><input type="checkbox" value="roof">roof / hood</label><label class="chk" title="Only paints about 60% of the blade"><input type="checkbox" value="wing">wing (experimental)</label></div>
     <div class="row"><div><label>Shapes in total: <b id="shV">450</b> <span class="note">(editor limit 1000)</span></label><input type="range" id="shapes" min="60" max="950" step="10" value="450"></div>
       <div><label>Fit</label><select id="fill"><option value="contain">Whole image (contain)</option><option value="cover">Fill the panel (crop)</option></select></div></div>
     <p><button id="btnPrev">Preview</button> <span class="note" id="prevNote"></span></p>
     <div class="panels" id="prevGrid"></div>
     <div id="applyBox" class="hide"><p id="totalNote" class="note"></p>
       <label class="chk hide" id="closedBox"><input type="checkbox" id="closed"> The game is closed</label>
       <p><button id="btnApply">Write to slot</button></p></div>
   </div>
   <div id="t_share" class="hide">
     <h2>Export the selected slot</h2><p class="note">Saves a shareable <code>.fm4livery</code> file (not tied to your profile).</p><button id="btnExp">Export</button> <span id="expOut" class="note"></span>
     <h2 style="margin-top:22px">Import into the selected slot</h2><input type="file" id="impFile" accept=".fm4livery,.zip"><p><label class="chk hide" id="closedBox2"><input type="checkbox" id="closed2"> The game is closed</label></p><button id="btnImp">Import</button>
   </div>
__EDITOR_HTML__
__VIEWER_HTML__
   <div id="t_bak" class="hide"><h2>Backups</h2><p class="note">Made automatically before every write. Restoring keeps a copy of what it replaces.</p><div id="bakList" class="note">…</div></div>
  </div>
  <div class="card"><h2>Log</h2><div id="log"></div></div>
 </div>
</main>
<script>
const TOKEN="__TOKEN__";let sel=null,rows=[],prevId=null,busy=false,lastPanels=null,viewKey=null;
const $=s=>document.querySelector(s);
function log(m,c){const e=$('#log');const d=document.createElement('div');d.textContent=m;if(c)d.className=c;e.appendChild(d);e.scrollTop=e.scrollHeight}
async function api(n,d){const r=await fetch('/api/'+n,{method:'POST',headers:{'X-Token':TOKEN,'Content-Type':'application/json'},body:JSON.stringify(d||{})});const j=await r.json();if(j.error)throw new Error(j.error);return j}
function setBusy(b,btn,txt){busy=b;if(btn){btn.disabled=b;if(b){btn.dataset.t=btn.innerHTML;btn.innerHTML='<span class="spin"></span>'+txt}else if(btn.dataset.t)btn.innerHTML=btn.dataset.t}}
function b64(file){return new Promise((res,rej)=>{const f=new FileReader();f.onload=()=>res(f.result.split(',')[1]);f.onerror=rej;f.readAsDataURL(file)})}
function showState(s){const ch=$('#chipProfile');$('#ver').textContent='v'+(s.version||'');
 if(s.ok){if(s.root&&!$('#rootIn').value)$('#rootIn').value=s.root;$('#peIn').value=s.pe||'';$('#mediaIn').value=s.media||'';ch.textContent='profile '+s.xuid;ch.className='chip ok';$('#setupCard').classList.add('hide');const p=$('#profSel');p.innerHTML='';(s.profiles||[]).forEach(x=>{const o=document.createElement('option');o.value=x;o.textContent=x;if(x===s.profile)o.selected=true;p.appendChild(o)});$('#profPick').classList.toggle('hide',(s.profiles||[]).length<2);
  $('#garNote').textContent=s.cars_known?'':'Car names unavailable (game database not found) - cars show their ID.';loadGarage()}
 else{ch.textContent='game files not found';ch.className='chip bad';$('#setupCard').classList.remove('hide');$('#advBox').open=true;$('#setupMsg').textContent=(s.error||'')+' - if your files are in different places, fill in the boxes below.';}}
async function loadGarage(){try{const g=await api('garage');rows=g.rows;const z=$('#zipSel');z.innerHTML='<option value="">automatic</option>';g.carzips.forEach(p=>{const o=document.createElement('option');o.value=p;o.textContent=p.split(/[\\/]/).pop();z.appendChild(o)});
 const tb=$('#garage');tb.innerHTML='';rows.forEach(r=>{const tr=document.createElement('tr');tr.innerHTML='<td>'+r.garage_id+'</td><td>'+(r.car!=='?'?r.car:'car '+r.car_id)+'</td><td><span class="tag '+(r.livery?'has':'')+'">'+(r.livery?(r.file?'livery':'assigned'):'none')+'</span></td>';tr.onclick=()=>pick(r.garage_id);tr.dataset.id=r.garage_id;tb.appendChild(tr)});
 if(!g.signature)log('warning: PlayerDatabase signature did not verify','warn');if(sel)pick(sel)}catch(e){log('garage: '+e.message,'bad')}}
function pick(id){sel=id;document.querySelectorAll('#garage tr').forEach(t=>t.classList.toggle('sel',t.dataset.id==id));const r=rows.find(x=>x.garage_id==id);if(!r)return;
 $('#selInfo').innerHTML='Slot <b>'+r.garage_id+'</b> - '+(r.car!=='?'?r.car:'car '+r.car_id)+(r.livery?'':' <span class="warn">(no livery yet - the garage database will be updated)</span>');
 const need=!r.livery;$('#closedBox').classList.toggle('hide',!need);$('#closedBox2').classList.toggle('hide',!need);}
document.querySelectorAll('.tabs button').forEach(b=>b.onclick=()=>{document.querySelectorAll('.tabs button').forEach(x=>x.classList.toggle('on',x===b));['make','share','edit','view','bak'].forEach(t=>$('#t_'+t).classList.toggle('hide',t!==b.dataset.t));if(b.dataset.t==='bak')loadBak();if(b.dataset.t==='view')loadView();if(b.dataset.t==='edit')loadEdit()});
$('#shapes').oninput=e=>$('#shV').textContent=e.target.value;
$('#btnFolder').onclick=()=>{$('#setupCard').classList.toggle('hide')};
$('#btnFind').onclick=async()=>{try{showState(await api('setup',{root:$('#rootIn').value.trim(),pe:$('#peIn').value,media:$('#mediaIn').value,profile:$('#profSel').value||''}))}catch(e){showState({ok:false,error:e.message});log(e.message,'bad')}};
$('#profSel').onchange=async()=>{try{showState(await api('setup',{root:$('#rootIn').value.trim()||undefined,pe:$('#peIn').value,media:$('#mediaIn').value,profile:$('#profSel').value}))}catch(e){log(e.message,'bad')}};
$('#btnPrev').onclick=async()=>{const f=$('#img').files[0];if(!sel)return log('pick a garage slot first','warn');if(!f)return log('choose an image first','warn');
 const panels=[...document.querySelectorAll('#panelBoxes input:checked')].map(x=>x.value);if(!panels.length)return log('tick at least one panel','warn');
 if(panels.includes('wing'))log('note: the wing only paints about 60% of the blade','warn');
 const btn=$('#btnPrev');setBusy(true,btn,'Fitting shapes…');$('#prevNote').textContent='this can take up to a minute';
 try{const r=await api('preview',{slot:sel,image:await b64(f),panels,shapes:+$('#shapes').value,fill:$('#fill').value,carzip:$('#zipSel').value});prevId=r.id;lastPanels=r.panels;if(window.V)V.setLivery(r.panels);const g=$('#prevGrid');g.innerHTML='';
  Object.entries(r.panels).forEach(([n,p])=>{const d=document.createElement('div');d.className='pv';d.innerHTML='<b>'+n+' - '+p.layers+' layers</b><img src="data:image/png;base64,'+p.png+'">';g.appendChild(d)});
  $('#applyBox').classList.remove('hide');$('#totalNote').innerHTML=r.total_layers+' layers in total'+(r.total_layers>1000?' <span class="bad">- over the editor limit of 1000</span>':'');log('preview ready ('+r.total_layers+' layers)','ok')}
 catch(e){log('preview: '+e.message,'bad')}finally{setBusy(false,btn);$('#prevNote').textContent=''}};
$('#btnApply').onclick=async()=>{const btn=$('#btnApply');setBusy(true,btn,'Writing…');try{const r=await api('apply',{id:prevId,game_closed:$('#closed').checked});if(r.needs_confirm){log(r.message,'warn')}else{r.messages.forEach(m=>log(m,'ok'));log('Done. In the game, switch to another car and back (or restart) to see the change.','ok');loadGarage()}}catch(e){log('apply: '+e.message,'bad')}finally{setBusy(false,btn)}};
$('#btnExp').onclick=async()=>{if(!sel)return log('pick a garage slot first','warn');try{const r=await api('export',{slot:sel});$('#expOut').textContent=r.path;log('exported to '+r.path,'ok')}catch(e){log('export: '+e.message,'bad')}};
$('#btnImp').onclick=async()=>{const f=$('#impFile').files[0];if(!sel)return log('pick a garage slot first','warn');if(!f)return log('choose a .fm4livery file','warn');try{const r=await api('import',{slot:sel,file:await b64(f),game_closed:$('#closed2').checked});if(r.needs_confirm)log(r.message,'warn');else{r.messages.forEach(m=>log(m,'ok'));loadGarage()}}catch(e){log('import: '+e.message,'bad')}};
async function loadBak(){try{const r=await api('backups');const L=$('#bakList');L.innerHTML='';if(!r.files.length)L.textContent='No backups yet.';r.files.forEach(f=>{const d=document.createElement('div');d.style.cssText='display:flex;gap:10px;align-items:center;padding:4px 0;border-bottom:1px solid var(--line)';d.innerHTML='<span style="flex:1;word-break:break-all">'+f+'</span>';const b=document.createElement('button');b.className='sec';b.textContent='Restore';b.onclick=async()=>{try{const x=await api('restore',{file:f});log('restored '+x.restored,'ok');loadGarage()}catch(e){log('restore: '+e.message,'bad')}};d.appendChild(b);L.appendChild(d)})}catch(e){log('backups: '+e.message,'bad')}}
__EDITOR_JS__
__VIEWER_JS__
window.__slot=()=>sel;window.__setSlotTex=tp=>{lastPanels=tp;if(window.V)V.setLivery(tp)};
async function loadEdit(){if(!sel){$('#eInfo').textContent='Pick a garage slot first';return}try{const tp=await E.load(false);if(tp&&tp!==true){window.__setSlotTex(tp)}}catch(e){$('#eInfo').textContent='';log('editor: '+e.message,'bad')}}
async function loadView(){if(!V.init())return;if(!sel){$('#vStatus').textContent='Pick a garage slot first';return}
 const key=sel+'|'+$('#zipSel').value;if(viewKey===key)return;$('#vStatus').textContent='loading the car model...';$('#vStatus').className='note';
 try{const m=await api('model',{slot:sel,carzip:$('#zipSel').value});V.setModel(m);viewKey=key;if(lastPanels)V.setLivery(lastPanels)}catch(e){$('#vStatus').textContent='';log('3D view: '+e.message,'bad')}}
window.addEventListener('pywebviewready',()=>{if(window.pywebview&&window.pywebview.api&&window.pywebview.api.pick_folder)$('#btnPick').classList.remove('hide');$('#btnPickPe').classList.remove('hide');$('#btnPickMedia').classList.remove('hide')});
$('#btnPickPe').onclick=async()=>{const p=await window.pywebview.api.pick_file();if(p)$('#peIn').value=p};
$('#btnPickMedia').onclick=async()=>{const p=await window.pywebview.api.pick_folder();if(p)$('#mediaIn').value=p};
$('#btnPick').onclick=async()=>{const p=await window.pywebview.api.pick_folder();if(p){$('#rootIn').value=p;$('#btnFind').click()}};
(async()=>{try{showState(await api('state'))}catch(e){log(e.message,'bad')}})();
</script></body></html>'''

from . import gui_viewer as _v, gui_editor as _e
PAGE = PAGE.replace('__VIEWER_HTML__', _v.HTML).replace('__VIEWER_CSS__', _v.CSS).replace('__VIEWER_JS__', _v.JS).replace('__EDITOR_HTML__', _e.HTML).replace('__EDITOR_CSS__', _e.CSS).replace('__EDITOR_JS__', _e.JS)
