import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = { maps:[], scene:null, selected:null, start:'',end:'', objective:'fastest', blocked:new Set(),route:null, generation:0,routeGeneration:0 };
let toastTimer;
function toast(text) { $('toast').textContent=text;$('toast').classList.remove('hidden');clearTimeout(toastTimer);toastTimer=setTimeout(()=>$('toast').classList.add('hidden'),4300); }
async function api(path, payload) {
  const res=await fetch(path,payload ? {method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(payload)} : {});
  const body=await res.json();if(!res.ok)throw new Error(body.error || 'Request failed');return body;
}

const renderer=new THREE.WebGLRenderer({canvas:$('canvas'),antialias:true,alpha:true});
renderer.setPixelRatio(Math.min(window.devicePixelRatio,1.7));
renderer.setClearColor(0x111a20,0);
renderer.outputColorSpace=THREE.SRGBColorSpace;
renderer.localClippingEnabled=true;
const world=new THREE.Scene();
const camera=new THREE.PerspectiveCamera(47,1,.1,5000);
const controls=new OrbitControls(camera,renderer.domElement);controls.enableDamping=true;controls.dampingFactor=.08;controls.maxPolarAngle=Math.PI*.88;
world.add(new THREE.HemisphereLight(0xd5e7df,0x293038,2.4));
const light=new THREE.DirectionalLight(0xd8ede5,2.7);light.position.set(50,100,30);world.add(light);
const fill=new THREE.DirectionalLight(0x92a5c8,.8);fill.position.set(-50,30,-60);world.add(fill);
let geometryGroup=new THREE.Group(),wallGroup=new THREE.Group(),edgeGroup=new THREE.Group(),routeGroup=new THREE.Group(),grid=null;
world.add(geometryGroup,wallGroup,edgeGroup,routeGroup);
const geometryMaterial=new THREE.MeshLambertMaterial({color:0x576f70,side:THREE.DoubleSide,transparent:true,opacity:.94});
const basis=new THREE.Matrix4().set(1,0,0,0,0,0,1,0,0,1,0,0,0,0,0,1);
const vec=p=>new THREE.Vector3(p[0],p[2],p[1]);
const matrix=rows=>basis.clone().multiply(new THREE.Matrix4().set(...rows.flat())).multiply(basis);
const wallMeshes=new Map(),labelElements=new Map(),meshCache=new Map();
let bounds=null,hover=null;
const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();

function disposeGroup(group) {
  for(const o of [...group.children]) {group.remove(o);o.geometry?.dispose();if(o.material && o.material!==geometryMaterial) o.material.dispose();}
}
function fitView(mode='orbit') {
  if(!bounds)return;
  const center=bounds.getCenter(new THREE.Vector3()),size=bounds.getSize(new THREE.Vector3()),r=Math.max(size.x,size.z,size.y*1.7,25)*.85;
  camera.up.set(0,1,0);
  const distance=r / Math.tan(THREE.MathUtils.degToRad(camera.fov/2)) * Math.max(1,1/camera.aspect) * .64;
  if(mode==='top') {camera.up.set(0,0,-1);camera.position.copy(center).add(new THREE.Vector3(0,distance,.001));}
  else camera.position.copy(center).add(new THREE.Vector3(.92,.85,1.06).normalize().multiplyScalar(distance));
  controls.target.copy(center);controls.maxDistance=r*8;controls.minDistance=2;controls.update();
  $('view-top').classList.toggle('active',mode==='top');$('view-orbit').classList.toggle('active',mode!=='top');
}
function resize(){const r=$('viewport').getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe($('viewport'));

function loading(title, subtitle) {
  $('loading').classList.remove('hidden');$('loading').querySelector('strong').textContent=title;$('loading').querySelector('span').textContent=subtitle;
}
async function fetchMesh(id,viewProxy,generation) {
  const cacheKey=(viewProxy?'proxy:':'mesh:')+id;
  if(meshCache.has(cacheKey))return meshCache.get(cacheKey);
  const response=await fetch(`/assets/${viewProxy?'proxies':'meshes'}/${id}.bin`);if(!response.ok)throw new Error('Mesh file unavailable');
  const data=await response.arrayBuffer(),header=new DataView(data),n=header.getUint32(0,true),ni=header.getUint32(4,true);
  if(data.byteLength!==8+n*12+ni*4)throw new Error('Invalid mesh buffer');
  const raw=new Float32Array(data,8,n*3),positions=new Float32Array(n*3);
  for(let i=0;i<n;i++){positions[i*3]=raw[i*3]/100;positions[i*3+1]=raw[i*3+2]/100;positions[i*3+2]=raw[i*3+1]/100;}
  const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(positions,3));g.setIndex(new THREE.BufferAttribute(new Uint32Array(data,8+n*12,ni),1));g.computeVertexNormals();g.computeBoundingSphere();if(generation!==state.generation){g.dispose();throw new Error('Arena changed');}meshCache.set(cacheKey,g);return g;
}
function makeWalls() {
  for(const n of state.scene.nodes) {
    const center=vec(n.position),right=vec(n.right).multiplyScalar(n.width/2),up=vec(n.up).multiplyScalar(n.height/2);
    const corners=[center.clone().sub(right).sub(up),center.clone().add(right).sub(up),center.clone().add(right).add(up),center.clone().sub(right).add(up)];
    let outline=corners;const positions=new Float32Array(corners.flatMap(v=>v.toArray()));
    let g;
    if(n.shape==='circle') {
      outline=Array.from({length:48},(_,i)=>center.clone().addScaledVector(right,Math.cos(i/48*Math.PI*2)).addScaledVector(up,Math.sin(i/48*Math.PI*2)));
      const verts=[...center.toArray(),...outline.flatMap(v=>v.toArray())],indices=[];
      for(let i=0;i<48;i++)indices.push(0,i+1,(i+1)%48+1);
      g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(verts,3));g.setIndex(indices);
    } else { g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.BufferAttribute(positions,3));g.setIndex([0,1,2,0,2,3]); }
    g.computeVertexNormals();
    const material=new THREE.MeshBasicMaterial({color:0x70e7d6,side:THREE.DoubleSide,transparent:true,opacity:.53,depthWrite:false,polygonOffset:true,polygonOffsetFactor:-3});
    const mesh=new THREE.Mesh(g,material);mesh.userData.node=n;wallGroup.add(mesh);wallMeshes.set(n.id,mesh);
    const line=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(outline),new THREE.LineBasicMaterial({color:0x91ffe8,transparent:true,opacity:.65}));wallGroup.add(line);
    const label=document.createElement('span');label.className='node-label';label.textContent=n.label;$('node-labels').append(label);labelElements.set(n.id,label);
  }
}
function drawEdges() {
  disposeGroup(edgeGroup);if(!state.scene)return;
  const edges=$('show-edges').checked ? state.scene.edges : state.scene.edges.filter(e=>e.source===state.selected);
  for(const kind of ['portal','movement']) {
    const lines=[];
    for(const e of edges) {
      if((e.kind==='portal')!==(kind==='portal'))continue;
      const pts=e.kind==='portal' ? [e.path[1],e.path[2]] : e.path;
      for(let i=1;i<pts.length;i++)lines.push(...vec(pts[i-1]).toArray(),...vec(pts[i]).toArray());
    }
    if(!lines.length)continue;
    const g=new THREE.BufferGeometry();g.setAttribute('position',new THREE.Float32BufferAttribute(lines,3));
    edgeGroup.add(new THREE.LineSegments(g,new THREE.LineBasicMaterial({color:kind==='portal'?0xac9ee9:0xdcb775,transparent:true,opacity:$('show-edges').checked ? .18 : .45,depthTest:false})));
  }
}
function drawRoute() {
  disposeGroup(routeGroup);
  for(const e of state.route?.edges || []) {
    const pts=e.kind==='portal' ? [e.path[1],e.path[2]] : e.path;
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts.map(vec)),new THREE.LineDashedMaterial({color:e.kind==='portal'?0xd0bbff:0xffd394,dashSize:.7,gapSize:.3,transparent:true,opacity:1,depthTest:false}));line.computeLineDistances();routeGroup.add(line);
    const orb=new THREE.Mesh(new THREE.SphereGeometry(.2,12,8),new THREE.MeshBasicMaterial({color:e.kind==='portal'?0xd8caff:0xffd394,depthTest:false}));orb.position.copy(vec(e.path[e.path.length-1]));routeGroup.add(orb);
  }
}
function updateWallStyles() {
  for(const [id,mesh] of wallMeshes) {
    mesh.material.color.setHex(state.blocked.has(id)?0xb86e78:id===state.start?0xa7ffe8:id===state.end?0xffcb87:0x60cbbf);
    mesh.material.opacity=id===state.selected || id===state.start || id===state.end ? .85 : .46;
    const label=labelElements.get(id);label.classList.toggle('selected',id===state.selected || id===state.start || id===state.end);label.classList.toggle('blocked',state.blocked.has(id));
  }
}
function renderWallList(){
  const query=$('wall-search').value.toLowerCase();
  $('wall-list').innerHTML=(state.scene?.nodes || []).filter(n=>(n.label+' '+n.name).toLowerCase().includes(query)).map(n=>`<button class="wall-row ${n.id===state.selected?'selected':''}" data-wall="${n.id}"><span class="wall-id">${esc(n.label)}</span><span class="wall-name">${n.launch?'Launch wall':n.type.includes('Circular')?'Circular wall':'Portal wall'}<small>${n.width.toFixed(1)} × ${n.height.toFixed(1)} m · Z ${n.position[2].toFixed(1)}</small></span><span class="wall-state ${state.blocked.has(n.id)?'blocked':''}"></span></button>`).join('');
  $('wall-list').querySelectorAll('[data-wall]').forEach(b=>b.onclick=()=>selectWall(b.dataset.wall));
}
function selectWall(id,{start=false,destination=false}={}){
  const n=state.scene.nodes.find(n=>n.id===id);if(!n)return;state.selected=id;
  if(start || !state.start){state.start=id;$('start-wall').value=id;}
  else if(destination){state.end=id;$('end-wall').value=id;}
  const outgoing=state.scene.edges.filter(e=>e.source===id);
  $('selection-card').innerHTML=`<span class="eyebrow">${esc(n.label)} · ${n.launch?'LAUNCH WALL':'PORTAL WALL'}</span><strong>${n.width.toFixed(1)} × ${n.height.toFixed(1)} metres</strong><p>${outgoing.filter(e=>e.kind==='portal').length} placement angles · ${outgoing.filter(e=>e.kind!=='portal').length} movement paths<br>${n.sides.length===2?'Double-sided':'Front face modeled'} · World Z ${n.position[2].toFixed(1)} m${n.launchSpeed?'<br>Launch speed '+n.launchSpeed.toFixed(1)+' m/s from asset':''}</p><div class="card-actions"><button class="secondary" id="card-start">Set start</button><button class="secondary" id="card-end">Set destination</button><button class="secondary" id="card-block">${state.blocked.has(id)?'Restore':'Avoid'}</button></div>`;
  $('selection-card').classList.remove('hidden');
  $('card-start').onclick=()=>{state.start=id;$('start-wall').value=id;updateWallStyles();findRoute();};
  $('card-end').onclick=()=>{state.end=id;$('end-wall').value=id;updateWallStyles();findRoute();};
  $('card-block').onclick=()=>{state.blocked.has(id)?state.blocked.delete(id):state.blocked.add(id);selectWall(id);findRoute();};
  renderWallList();updateWallStyles();drawEdges();if(start||destination)findRoute();
}
let down=null;
renderer.domElement.addEventListener('pointerdown',event=>{down=[event.clientX,event.clientY];});
renderer.domElement.addEventListener('pointerup',event=>{
  if(!state.scene || !down || event.button!==0 || Math.hypot(event.clientX-down[0],event.clientY-down[1])>5)return;
  const r=renderer.domElement.getBoundingClientRect();pointer.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);raycaster.setFromCamera(pointer,camera);
  const hits=raycaster.intersectObjects([...wallMeshes.values()]);if(hits.length)selectWall(hits[0].object.userData.node.id,{start:event.shiftKey,destination:!event.shiftKey});
});
function renderMaps(){
  const query=$('map-search').value.toLowerCase();const ready=state.maps.filter(m=>m.ready&&!m.library);$('map-count').textContent=ready.length;
  $('map-list').innerHTML=ready.filter(m=>m.name.toLowerCase().includes(query)).map(m=>`<button class="map-row ${m.id===state.scene?.id?'active':''}" data-map="${m.id}"><span class="map-glyph">${m.name==='Academy'?'⌘':m.name==='Abyss'?'◇':'⌁'}</span><span class="map-name">${esc(m.name)}<small>${m.nodes} WALLS · ${m.edges} EDGES</small></span><span class="map-arrow">›</span></button>`).join('') || '<p class="intro">No matching extracted arenas.</p>';
  $('map-list').querySelectorAll('[data-map]').forEach(b=>b.onclick=()=>loadScene(b.dataset.map));
  renderImports();
}
async function loadScene(mid) {
  const gen=++state.generation;state.routeGeneration++;loading('Reading arena','Loading extracted geometry and its portal graph.');$('find-route').disabled=false;$('find-route').innerHTML='Find route <span>↗</span>';
  try {
    const s=await api('/api/maps/'+mid);if(gen!==state.generation)return;
    state.scene=s;state.start='';state.end='';state.selected=null;state.blocked.clear();state.route=null;$('wall-search').value='';document.querySelector('.right-panel').scrollTop=0;
    if(new URLSearchParams(location.hash.slice(1)).get('map')!==mid)history.replaceState(null,'','#'+new URLSearchParams({map:mid}));
    for(const g of [geometryGroup,wallGroup,edgeGroup,routeGroup])disposeGroup(g);
    for(const g of meshCache.values())g.dispose();meshCache.clear();wallMeshes.clear();labelElements.clear();$('node-labels').replaceChildren();$('selection-card').classList.add('hidden');
    if(grid){world.remove(grid);grid.geometry.dispose();grid.material.dispose();}
    $('map-title').textContent=s.name;$('map-title').onclick=()=>$('import-dialog').showModal();$('map-title').title='Choose another arena';
    $('map-subtitle').textContent=`${s.nodes.length} portal walls   /   ${s.edges.length} directed edges   /   ${s.source.levels.length} loaded levels${s.overviewGeometry?.startsWith('collision')?'   /   collision overview':''}`;
    $('map-badge').textContent=s.source.geometryUsable===false?'PARTIAL GEOMETRY':'ASSET DATA';
    $('wall-count').textContent=s.nodes.length;$('build-note').textContent=`Build ${s.source.executableSha256.slice(0,8)} · Unreal assets`;
    const options='<option value="">Select a wall…</option>'+s.nodes.map(n=>`<option value="${n.id}">${esc(n.label)} — ${n.launch?'Launch wall':'Portal wall'} · ${n.position[2].toFixed(1)} m</option>`).join('');
    $('start-wall').innerHTML=options;$('end-wall').innerHTML=options;renderWallList();renderMaps();renderResult();
    const vs=s.nodes.map(n=>vec(n.position));bounds=new THREE.Box3().setFromPoints(vs.length?vs:[new THREE.Vector3(-10,0,-10),new THREE.Vector3(10,0,10)]);fitView();
    const center=bounds.getCenter(new THREE.Vector3());grid=new THREE.GridHelper(300,120,0x344d4d,0x23383e);grid.position.set(center.x,bounds.min.y-1.5,center.z);grid.material.transparent=true;grid.material.opacity=.32;world.add(grid);
    makeWalls();updateWallStyles();
    geometryMaterial.clippingPlanes=$('cutaway').checked ? [new THREE.Plane(new THREE.Vector3(0,-1,0),bounds.max.y+1)] : [];
    $('dataset-details').innerHTML=`<p>${s.source.coverage?.landscapeRead??0} terrain patches · ${s.instances.length.toLocaleString()} mesh instances · ${s.source.geometryTriangles.toLocaleString()} instanced proxy triangles.</p><p>Base walk ${s.model.walkSpeed} m/s${s.model.assetParameters?.walkSpeed?' from the character asset':''}. Gravity and jump behavior are estimated; active mode modifiers are not resolved.</p><p class="${s.issues.length?'issue-count':''}">${s.issues.length} extraction notes. <button class="secondary" id="show-source-notes">Inspect sources</button></p><code>${esc(s.rootPackage)}<br>Revision ${esc(s.revision)}</code>`;
    $('show-source-notes').onclick=showSources;
    $('export-graph').href='/api/export/graph?'+new URLSearchParams({map:s.id,revision:s.revision});
    const groups=new Map();for(const instance of s.instances){if(!instance.visible)continue;if(!groups.has(instance.mesh))groups.set(instance.mesh,[]);groups.get(instance.mesh).push(instance);}
    const entries=[...groups.entries()];let complete=0,failed=0,cursor=0;
    await Promise.all(Array.from({length:Math.min(10,entries.length)},async()=>{
      while(cursor<entries.length){const [id,instances]=entries[cursor++];try{const g=await fetchMesh(id,s.meshes.find(m=>m.id===id)?.viewProxy,gen);if(gen!==state.generation)return;const mesh=new THREE.InstancedMesh(g,geometryMaterial,instances.length);instances.forEach((v,i)=>mesh.setMatrixAt(i,matrix(v.matrix)));mesh.computeBoundingSphere();geometryGroup.add(mesh);}catch(e){failed++;}complete++;if(gen===state.generation)loading('Loading '+s.name,`${complete} / ${entries.length} mesh assets${failed?' · '+failed+' unavailable':''}`);}
    }));
    if(gen!==state.generation)return;$('loading').classList.add('hidden');geometryGroup.visible=$('show-geometry').checked;
    if(!s.nodes.length)toast('This map has no resolved player portal walls. Check its extraction notes.');
    if(failed)toast(`${failed} mesh assets could not be displayed; the extraction notes remain available.`);
    const hash=new URLSearchParams(location.hash.slice(1));if(hash.get('map')===mid){state.start=hash.get('from')||'';state.end=hash.get('to')||'';$('start-wall').value=state.start;$('end-wall').value=state.end;findRoute();}
  } catch(error){if(gen===state.generation){loading('Map could not be loaded',error.message);toast(error.message);}}
}
function showSources(){
  let d=$('source-dialog');if(!d){d=document.createElement('dialog');d.id='source-dialog';document.body.append(d);}
  const s=state.scene;
  d.innerHTML=`<div class="dialog-heading"><h2>${esc(s.name)} asset sources</h2><button class="icon-button" id="close-source">×</button></div><p>Map geometry and wall transforms come from the installed game. Terrain uses heightmaps at the serialized collision mip and visibility holes. Primitive bounds and render fallbacks remain approximations.</p><p><strong>${s.source.geometryUsable===false?'Routes withheld: incomplete geometry':'Geometry extraction checks passed'}</strong><br>Selected root: ${esc(s.rootPackage)}. Other cooked variants are kept separate.</p><p><strong>${s.source.levels.length} active levels</strong><br>${s.source.levels.map(esc).join('<br>')}</p><p><strong>${s.issues.length} extraction notes</strong></p><div style="max-height:35vh;overflow:auto;font:9px monospace;line-height:1.8;overflow-wrap:anywhere">${s.issues.map(i=>`<p>${esc(i.path||i.wall||i.scope||'Asset')}<br>${esc(i.error||i.message)}</p>`).join('')||'No recorded extraction exceptions.'}</div>`;
  $('close-source').onclick=()=>d.close();d.showModal();
}
async function findRoute(){
  if(!state.scene)return;
  state.start=$('start-wall').value;state.end=$('end-wall').value;updateWallStyles();
  if(!state.start||!state.end){state.route=null;drawRoute();renderResult();return;}
  const gen=++state.routeGeneration;
  $('find-route').disabled=true;$('find-route').textContent='Finding route…';
  const kinds=[...document.querySelectorAll('.edge-filters input:checked')].flatMap(e=>e.value==='jump'?['jump','drop']:[e.value]);
  try {
    const r=await api('/api/route',{map:state.scene.id,revision:state.scene.revision,start:state.start,end:state.end,objective:state.objective,kinds,blocked:[...state.blocked],maxDifficulty:Number($('max-difficulty').value)});
    if(gen!==state.routeGeneration)return;state.route=r;renderResult();drawRoute();
    history.replaceState(null,'',`#${new URLSearchParams({map:state.scene.id,from:state.start,to:state.end})}`);
  }catch(e){if(gen===state.routeGeneration){state.route=null;toast(e.message);renderResult();}}
  finally{if(gen===state.routeGeneration){$('find-route').disabled=false;$('find-route').innerHTML='Find route <span>↗</span>';}}
}
function renderResult(){
  const r=state.route;$('route-actions').classList.toggle('hidden',!r?.found);
  if(!r){$('route-result').innerHTML='<div class="empty-route"><span>⌁</span><strong>A different way across.</strong><p>Select two walls on the map or use the menus above.</p></div>';return;}
  if(!r.found){$('route-result').innerHTML=`<div class="empty-route"><span>⌁</span><strong>No matching route</strong><p>${esc(r.reason)} Try a higher difficulty limit or another wall.</p></div>`;return;}
  const nodes=new Map(state.scene.nodes.map(n=>[n.id,n]));
  const kinds=[...document.querySelectorAll('.edge-filters input:checked')].flatMap(e=>e.value==='jump'?['jump','drop']:[e.value]);
  $('export-route').href='/api/export/route?'+new URLSearchParams({map:state.scene.id,revision:state.scene.revision,start:state.start,end:state.end,objective:state.objective,kinds:kinds.join(','),blocked:[...state.blocked].join(','),maxDifficulty:$('max-difficulty').value});
  $('route-result').innerHTML=`<div class="route-metrics"><div><strong>${r.seconds.toFixed(1)}<span> s</span></strong><small>EST. SETUP + TRAVEL</small></div><div><strong>${r.difficulty.toFixed(0)}<span> /100</span></strong><small>PEAK DIFFICULTY</small></div><div><strong>${r.placements}</strong><small>PLACEMENTS</small></div></div><div class="route-title"><span>${r.edges.length?`${r.edges.length} steps · ${r.objective}`:'Already at destination'}</span><span>${r.distance.toFixed(0)} m linked</span></div>${r.edges.map((e,i)=>`<div class="route-step ${e.kind==='portal'?'':'movement'}" data-step="${i}"><span class="step-dot"></span><strong>${esc(nodes.get(e.source)?.label)} → ${esc(nodes.get(e.target)?.label)} <span style="color:#81929f">${e.kind==='portal'?'Place + portal':e.kind}</span></strong><small>${e.kind==='portal'?`${e.angle}° incidence · ${e.distance.toFixed(1)} m · ${e.angularSize}° target`:`${e.distance.toFixed(1)} m · direct ${e.kind}`}<br>${e.kind==='portal'?`Aim yaw ${e.yaw}° · pitch ${e.pitch}° · turn ${e.turn}°<br>`:''}${e.seconds.toFixed(2)} s estimated · difficulty ${e.difficulty.toFixed(0)}</small></div>`).join('')}<p class="route-note">Geometry checked. Timing and difficulty are estimates. Start with a portal active on ${esc(nodes.get(state.start)?.label)}.</p>`;
  $('route-result').querySelectorAll('[data-step]').forEach(b=>b.onclick=()=>selectWall(r.edges[Number(b.dataset.step)].target));
}
function readSaved(){try{return JSON.parse(localStorage.getItem('portal-atlas-routes')||'[]');}catch{return [];}}
function renderSaved(){const saved=readSaved();$('saved-count').textContent=saved.length;$('saved-list').innerHTML=saved.map((r,i)=>`<div class="saved-item"><button data-saved="${i}">${esc(r.name)}</button><button data-delete="${i}" aria-label="Delete saved route">×</button></div>`).join('')||'<p>No saved routes yet.</p>';$('saved-list').querySelectorAll('[data-delete]').forEach(b=>b.onclick=()=>{saved.splice(Number(b.dataset.delete),1);localStorage.setItem('portal-atlas-routes',JSON.stringify(saved));renderSaved();});$('saved-list').querySelectorAll('[data-saved]').forEach(b=>b.onclick=async()=>{const r=saved[Number(b.dataset.saved)];if(state.scene?.id!==r.map)await loadScene(r.map);if(state.scene?.id!==r.map)return;state.start=r.start;state.end=r.end;state.blocked=new Set(r.blocked);state.objective=r.objective;$('max-difficulty').value=r.maxDifficulty??100;$('difficulty-value').textContent=$('max-difficulty').value;document.querySelectorAll('.edge-filters input').forEach(c=>c.checked=!r.kinds||r.kinds.includes(c.value));$('start-wall').value=r.start;$('end-wall').value=r.end;document.querySelectorAll('[data-objective]').forEach(x=>x.classList.toggle('active',x.dataset.objective===r.objective));await findRoute();toast(r.revision===state.scene.revision?'Saved route loaded.':'Map data changed; the saved route was recalculated.');});}
$('save-route').onclick=()=>{if(!state.route?.found)return;const nodes=new Map(state.scene.nodes.map(n=>[n.id,n]));const saved=readSaved();saved.unshift({name:`${state.scene.name} · ${nodes.get(state.start).label} → ${nodes.get(state.end).label}`,map:state.scene.id,revision:state.scene.revision,start:state.start,end:state.end,blocked:[...state.blocked],objective:state.objective,maxDifficulty:Number($('max-difficulty').value),kinds:[...document.querySelectorAll('.edge-filters input:checked')].map(c=>c.value)});try{localStorage.setItem('portal-atlas-routes',JSON.stringify(saved.slice(0,50)));renderSaved();toast('Route saved in this browser.');}catch{toast('Browser storage is unavailable. Use Export JSON to save the route.');}};
function renderImports(){
  $('import-list').innerHTML=state.maps.map(m=>`<div class="import-row"><span>${esc(m.name)}<small>${m.ready?(m.library?'Shared asset library · no standalone arena':`${m.nodes} walls · ${m.edges} edges`):m.job?.status==='running'?esc(m.job.phase):m.job?.status==='failed'?'Import failed · see local log':'Available in installed archives'}</small></span><button class="secondary" data-import="${m.id}" ${!m.ready&&m.job?.status==='running'?'disabled':''}>${m.ready?(m.library?'Inspect':'Open'):m.job?.status==='running'?'Reading…':'Import'}</button></div>`).join('');
  $('import-list').querySelectorAll('[data-import]').forEach(b=>b.onclick=async()=>{const m=state.maps.find(m=>m.id===b.dataset.import);if(m.ready){$('import-dialog').close();loadScene(m.id);return;}try{await api('/api/import',{map:m.id});toast('Reading '+m.name+' from installed assets.');await refreshMaps();}catch(e){toast(e.message);}});
}
async function refreshMaps(){const result=await api('/api/maps');state.maps=result.maps;renderMaps();}
$('map-search').oninput=renderMaps;$('wall-search').oninput=renderWallList;
$('start-wall').onchange=findRoute;$('end-wall').onchange=findRoute;$('find-route').onclick=findRoute;
$('swap-walls').onclick=()=>{const a=$('start-wall').value;$('start-wall').value=$('end-wall').value;$('end-wall').value=a;findRoute();};
$('show-geometry').onchange=()=>geometryGroup.visible=$('show-geometry').checked;$('cutaway').onchange=()=>{geometryMaterial.clippingPlanes=$('cutaway').checked && bounds ? [new THREE.Plane(new THREE.Vector3(0,-1,0),bounds.max.y+1)] : [];};$('show-edges').onchange=drawEdges;
$('show-labels').onchange=()=>$('node-labels').classList.toggle('hidden',!$('show-labels').checked);
$('reset-view').onclick=()=>fitView();$('view-top').onclick=()=>fitView('top');$('view-orbit').onclick=()=>fitView();
$('choose-arena').onclick=()=>$('import-dialog').showModal();$('map-title').style.cursor='pointer';$('import-button').onclick=()=>$('import-dialog').showModal();$('help-button').onclick=()=>$('help-dialog').showModal();
for(const b of document.querySelectorAll('[data-close]'))b.onclick=()=>$(b.dataset.close).close();
for(const b of document.querySelectorAll('[data-objective]'))b.onclick=()=>{state.objective=b.dataset.objective;document.querySelectorAll('[data-objective]').forEach(x=>x.classList.toggle('active',x===b));findRoute();};
for(const c of document.querySelectorAll('.edge-filters input'))c.onchange=findRoute;
$('max-difficulty').oninput=()=>$('difficulty-value').textContent=$('max-difficulty').value;$('max-difficulty').onchange=findRoute;
window.addEventListener('keydown',e=>{if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName))return;if(e.key.toLowerCase()==='r')fitView();if(e.key==='Escape'){$('selection-card').classList.add('hidden');state.selected=null;drawEdges();updateWallStyles();}});
function animate(){
  requestAnimationFrame(animate);controls.update();renderer.render(world,camera);
  const width=renderer.domElement.clientWidth,height=renderer.domElement.clientHeight;
  const priority=new Set([state.selected,state.start,state.end,...(state.route?.walls||[])]),cells=new Map();
  const labels=(state.scene?.nodes||[]).map(n=>({n,v:vec(n.position).add(vec(n.up).multiplyScalar(n.height/2+.3)).project(camera)}));
  labels.sort((a,b)=>Number(priority.has(b.n.id))-Number(priority.has(a.n.id))||a.v.z-b.v.z);
  for(const {n,v} of labels){
    const el=labelElements.get(n.id);if(!el)continue;
    const x=(v.x+1)/2*width,y=(1-v.y)/2*height,cx=Math.floor(x/40),cy=Math.floor(y/20);
    let hidden=v.z>1||v.z< -1||Math.abs(v.x)>1||Math.abs(v.y)>1;
    if(!hidden&&!priority.has(n.id))for(let dx=-1;dx<=1;dx++)for(let dy=-1;dy<=1;dy++){
      if((cells.get(`${cx+dx},${cy+dy}`)||[]).some(p=>Math.abs(p[0]-x)<37&&Math.abs(p[1]-y)<19))hidden=true;
    }
    el.style.display=hidden?'none':'';el.style.left=x+'px';el.style.top=y+'px';
    if(!hidden){const key=`${cx},${cy}`;if(!cells.has(key))cells.set(key,[]);cells.get(key).push([x,y]);}
  }
}
resize();animate();renderSaved();
try{
  await refreshMaps();const status=await api('/api/status');$('source-status').textContent=`${status.mapPackages.toLocaleString()} map packages indexed`;
  const hash=new URLSearchParams(location.hash.slice(1));const initial=state.maps.find(m=>m.id===hash.get('map')&&m.ready)||state.maps.find(m=>m.id==='MAP_Academy'&&m.ready)||state.maps.find(m=>m.ready);
  if(initial)await loadScene(initial.id);else loading('Import your first arena','Choose Import installed map to build its portal network.');
}catch(e){loading('Local assets are not ready',e.message);}
setInterval(async()=>{try{await refreshMaps();}catch{}},7000);
