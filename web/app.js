import * as THREE from 'three';
import { OrbitControls } from './vendor/OrbitControls.js';
import { linearColor,coveragePercent,validSections,surfaceSlots } from './colors.js';
import { captureMapView,screenshotFilename,downloadScreenshot } from './screenshot.js';
import { normalizeGroups,groupVisibility,wallsInBox,randomClueGroups,normalizeClueGroups } from './portal-groups.js';
import {setupBatchCapture} from './batch-ui.js';

const $ = id => document.getElementById(id);
const esc = s => String(s ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const state = { maps:[], scene:null, selected:null, start:'',end:'', objective:'fastest', blocked:new Set(),route:null, generation:0,routeGeneration:0 };
state.hiddenPortals=new Set();
state.groupSelection=new Set();state.wallGroups=[];state.editingGroup=null;state.groupMode=false;
state.clueGroups=[];
let batchRunning=false,batchControlState=null;
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
const hemisphere=new THREE.HemisphereLight(0xd5e7df,0x293038,2.4);world.add(hemisphere);
const light=new THREE.DirectionalLight(0xd8ede5,2.7);light.position.set(50,100,30);world.add(light);
const fill=new THREE.DirectionalLight(0x92a5c8,.8);fill.position.set(-50,30,-60);world.add(fill);
let geometryGroup=new THREE.Group(),wallGroup=new THREE.Group(),edgeGroup=new THREE.Group(),routeGroup=new THREE.Group(),grid=null;
world.add(geometryGroup,wallGroup,edgeGroup,routeGroup);
const geometryMaterial=new THREE.MeshLambertMaterial({color:0x576f70,side:THREE.DoubleSide,transparent:true,opacity:.94});
const surfaceMaterials=new Map();
let appearance=null;
let preferredSurfaceMode='colors';
try{preferredSurfaceMode=localStorage.getItem('portal-atlas-surface-mode')==='neutral'?'neutral':'colors';}catch{}
const basis=new THREE.Matrix4().set(1,0,0,0,0,0,1,0,0,1,0,0,0,0,0,1);
const vec=p=>new THREE.Vector3(p[0],p[2],p[1]);
const matrix=rows=>basis.clone().multiply(new THREE.Matrix4().set(...rows.flat())).multiply(basis);
const wallMeshes=new Map(),labelElements=new Map(),meshCache=new Map();
let bounds=null,hover=null;
let cutoffHeight=null;
const raycaster=new THREE.Raycaster(),pointer=new THREE.Vector2();

function portalVisible(id){return $('show-portals').checked&&!state.hiddenPortals.has(id);}
function readHiddenPortals(){try{const value=JSON.parse(localStorage.getItem('portal-atlas-hidden-portals')||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{};}catch{return {};}}
function applyPortalVisibility(remember=false){
  for(const object of wallGroup.children)object.visible=portalVisible(object.userData.portalId);
  for(const [id,label] of labelElements)if(!portalVisible(id))label.style.display='none';
  edgeGroup.visible=routeGroup.visible=$('show-portals').checked&&$('show-lines').checked;
  $('visible-portal-count').textContent=`${state.scene?.nodes.filter(n=>portalVisible(n.id)).length||0} / ${state.scene?.nodes.length||0} shown`;
  $('capture-visible-count').textContent=$('visible-portal-count').textContent;
  $('only-selected-portal').disabled=!state.selected;
  for(const option of $('capture-portal-list').options)option.selected=!state.hiddenPortals.has(option.value);
  if(remember&&state.scene){try{const saved=readHiddenPortals();saved[state.scene.id]=[...state.hiddenPortals];localStorage.setItem('portal-atlas-hidden-portals',JSON.stringify(saved));}catch{}}
  drawEdges();drawRoute();
  renderWallGroups();
}
function setPortalVisibility(action){
  if(!state.scene)return;
  $('show-portals').checked=true;
  state.hiddenPortals=new Set(action==='all'?[]:state.scene.nodes.filter(n=>action!=='selected'||n.id!==state.selected).map(n=>n.id));
  applyPortalVisibility(true);renderWallList();
}

function readGroupStore(){
  try{const value=JSON.parse(localStorage.getItem('portal-atlas-wall-groups')||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{};}catch{return {};}
}
function saveGroups(groups){
  const saved=readGroupStore();saved[state.scene.id]=groups;
  try{localStorage.setItem('portal-atlas-wall-groups',JSON.stringify(saved));state.wallGroups=groups;return true;}
  catch{toast('Browser storage is unavailable. Groups could not be saved.');return false;}
}
function readClueGroupStore(){
  try{const value=JSON.parse(localStorage.getItem('portal-atlas-clue-groups')||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{};}catch{return {};}
}
function renderClueGroups(){
  const total=state.scene?.nodes.length||0,groups=state.clueGroups,shown=state.scene?.nodes.filter(n=>portalVisible(n.id)).length||0;
  $('randomize-clue-groups').disabled=!total;
  $('randomize-clue-groups').textContent=groups.length?'Reshuffle 6 groups':'Create 6 random groups';
  $('clue-groups-status').textContent=groups.length?`${total} walls assigned once · ${groups.map(group=>group.length).join(' / ')} · saved in this browser`:total?`${total} walls, including hidden walls. Preview starts with group 1.`:'Choose a map with portal walls.';
  $('clue-groups-list').innerHTML=groups.map((group,index)=>{
    const prefix=groups.slice(0,index+1).flat(),only=group.length>0&&shown===group.length&&group.every(portalVisible),through=prefix.length>0&&shown===prefix.length&&prefix.every(portalVisible);
    return `<div class="clue-group"><div class="groups-heading"><strong>Group ${index+1}</strong><small>${group.length} walls · ${group.filter(portalVisible).length} shown</small></div><div class="group-actions"><button type="button" class="secondary" data-clue-only="${index}" aria-label="Show only random group ${index+1}" aria-pressed="${only}" ${group.length?'':'disabled'}>Only this</button><button type="button" class="secondary" data-clue-through="${index}" aria-label="Show random groups 1 through ${index+1}" aria-pressed="${through}" ${prefix.length?'':'disabled'}>Through here · ${prefix.length}</button></div></div>`;
  }).join('');
  for(const mode of ['only','through'])$('clue-groups-list').querySelectorAll(`[data-clue-${mode}]`).forEach(button=>button.onclick=()=>{
    const index=Number(button.getAttribute(`data-clue-${mode}`)),members=mode==='only'?state.clueGroups[index]:state.clueGroups.slice(0,index+1).flat();
    setGroupMode(false);applyGroupVisibility(members,'only');
  });
}
function openGroups(open=true){$('groups-panel').classList.toggle('hidden',!open);$('toggle-groups').setAttribute('aria-expanded',String(open));}
function refreshGroupSelection(){
  const count=state.groupSelection.size;
  $('group-selection-count').textContent=`${count} wall${count===1?'':'s'} selected`;
  $('map-selection-count').textContent=`${count} selected`;
  $('group-selection-members').innerHTML=(state.scene?.nodes||[]).filter(n=>state.groupSelection.has(n.id)).map(n=>`<button type="button" class="group-member" data-unselect-wall="${n.id}" aria-label="Remove ${esc(n.label)} from selection">${esc(n.label)} ×</button>`).join('')||'No walls selected';
  $('group-selection-members').querySelectorAll('[data-unselect-wall]').forEach(button=>button.onclick=()=>{state.groupSelection.delete(button.dataset.unselectWall);refreshGroupSelection();});
  for(const id of ['show-group-selection','hide-group-selection','isolate-group-selection','save-wall-group'])$(id).disabled=!count;
  $('save-wall-group').textContent=state.editingGroup?'Update group':'Save group';
  $('new-wall-group').classList.toggle('hidden',!state.editingGroup);
  updateWallStyles();renderWallList();renderWallGroups();
}
function renderWallGroups(){
  $('group-count').textContent=state.wallGroups.length+state.clueGroups.length;
  renderClueGroups();
  $('wall-groups-list').innerHTML=state.wallGroups.map(group=>{
    const shown=group.walls.filter(portalVisible).length;
    return `<div class="wall-group ${group.id===state.editingGroup?'editing':''}"><div class="wall-group-heading"><button type="button" class="group-load" data-group-load="${esc(group.id)}" aria-label="Select group ${esc(group.name)}"><strong>${esc(group.name)}</strong><small>${group.walls.length} walls · ${shown} shown</small></button><button type="button" class="group-link group-delete" data-group-delete="${esc(group.id)}" aria-label="Delete group ${esc(group.name)}">×</button></div><div class="group-actions"><button type="button" class="secondary" data-group-show="${esc(group.id)}" aria-label="Show group ${esc(group.name)}">Show</button><button type="button" class="secondary" data-group-hide="${esc(group.id)}" aria-label="Hide group ${esc(group.name)}">Hide</button><button type="button" class="secondary" data-group-only="${esc(group.id)}" aria-label="Show only group ${esc(group.name)}">Only these</button></div></div>`;
  }).join('')||'<p class="group-empty">No saved groups yet.</p>';
  $('wall-groups-list').querySelectorAll('[data-group-load]').forEach(button=>button.onclick=()=>{
    const group=state.wallGroups.find(g=>g.id===button.dataset.groupLoad);
    state.editingGroup=group.id;state.groupSelection=new Set(group.walls);$('group-name').value=group.name;refreshGroupSelection();
  });
  $('wall-groups-list').querySelectorAll('[data-group-delete]').forEach(button=>button.onclick=()=>{
    if(!saveGroups(state.wallGroups.filter(g=>g.id!==button.dataset.groupDelete)))return;
    if(state.editingGroup===button.dataset.groupDelete){state.editingGroup=null;$('group-name').value='';}
    refreshGroupSelection();toast('Group deleted. Its walls and visibility are unchanged.');
  });
  for(const action of ['show','hide','only'])$('wall-groups-list').querySelectorAll(`[data-group-${action}]`).forEach(button=>button.onclick=()=>{
    const group=state.wallGroups.find(g=>g.id===button.getAttribute(`data-group-${action}`));applyGroupVisibility(group.walls,action);
  });
}
function applyGroupVisibility(members,action){
  if(!state.scene||!members.size&&!members.length)return;
  state.hiddenPortals=groupVisibility(state.scene.nodes.map(n=>n.id),state.hiddenPortals,members,action);
  if(action!=='hide')$('show-portals').checked=true;
  applyPortalVisibility(true);renderWallList();
}
function toggleGroupWall(id){
  state.groupSelection.has(id)?state.groupSelection.delete(id):state.groupSelection.add(id);refreshGroupSelection();
}
function setGroupMode(active,{openPanel=false}={}){
  cancelGroupDrag();state.groupMode=active;controls.enabled=!active;
  $('viewport').classList.toggle('selecting-walls',active);
  document.querySelector('.viewport-section').classList.toggle('selecting-walls',active);
  $('group-selection-bar').classList.toggle('hidden',!active);
  $('select-group-walls').textContent=active?'Continue selecting on map':'Select walls on map';
  for(const label of labelElements.values())label.tabIndex=active?0:-1;
  if(active){$('selection-card').classList.add('hidden');openGroups(false);}
  else if(openPanel)openGroups();
  updateWallStyles();renderWallList();
}

function readCutoffHeights(){
  try{const value=JSON.parse(localStorage.getItem('portal-atlas-cutoff-heights')||'{}');return value&&typeof value==='object'&&!Array.isArray(value)?value:{};}catch{return {};}
}
function applyCutaway(){
  const enabled=$('cutaway').checked&&Number.isFinite(cutoffHeight);
  $('cutaway-height-controls').disabled=!enabled;
  const planes=enabled?[new THREE.Plane(new THREE.Vector3(0,-1,0),cutoffHeight)]:[];
  for(const material of [geometryMaterial,...surfaceMaterials.values()])material.clippingPlanes=planes;
}
function applySurfaceMode(){
  const colored=$('surface-mode').value==='colors'&&appearance?.available;
  renderer.toneMapping=colored?THREE.ACESFilmicToneMapping:THREE.NoToneMapping;
  hemisphere.intensity=colored ? 0.85 : 2.4;light.intensity=colored ? 1.3 : 2.7;fill.intensity=colored ? 0.3 : 0.8;
  for(const mesh of geometryGroup.children)mesh.material=colored&&mesh.userData.surfaceMaterials?mesh.userData.surfaceMaterials:geometryMaterial;
  const coverage=coveragePercent(appearance);
  $('map-colors-status').textContent=!appearance?.available?(appearance?.reason||'Reading surface colors…'):colored?'Simplified asset colors'+(coverage===null?'':` · ${coverage}% of mesh triangles`)+' · unresolved stay neutral':'Neutral overview';
  $('map-colors-status').title=appearance?.description||$('map-colors-status').textContent;
}
function materialFor(id){
  const rgb=linearColor(appearance?.materials?.[id]);if(!rgb)return geometryMaterial;
  if(!surfaceMaterials.has(id)){
    const material=new THREE.MeshLambertMaterial({color:new THREE.Color().setRGB(...rgb),side:THREE.DoubleSide,transparent:true,opacity:.94});
    material.clippingPlanes=geometryMaterial.clippingPlanes;surfaceMaterials.set(id,material);
  }
  return surfaceMaterials.get(id);
}
function setCutoffHeight(value,{remember=false,updateNumber=true}={}){
  if(!state.scene||!bounds||!Number.isFinite(value))return;
  const rounded=Math.round(value*10)/10;if(!Number.isFinite(rounded))return;
  cutoffHeight=rounded;
  const low=Math.floor(state.scene.bounds.min[2]),high=Math.ceil(state.scene.bounds.max[2]);
  $('cutoff-slider').min=Math.min(low,cutoffHeight);$('cutoff-slider').max=Math.max(high,cutoffHeight);
  $('cutoff-slider').value=cutoffHeight;if(updateNumber)$('cutoff-height').value=cutoffHeight;
  applyCutaway();
  if(remember){
    try{const heights=readCutoffHeights();heights[state.scene.id]=cutoffHeight;localStorage.setItem('portal-atlas-cutoff-heights',JSON.stringify(heights));}catch{}
  }
}

function disposeGroup(group) {
  for(const o of [...group.children]) {group.remove(o);o.geometry?.dispose();for(const material of Array.isArray(o.material)?o.material:[o.material])if(material&&material!==geometryMaterial&&![...surfaceMaterials.values()].includes(material))material.dispose();}
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
function resize(){if(batchRunning)return;const r=$('viewport').getBoundingClientRect();renderer.setSize(r.width,r.height,false);camera.aspect=r.width/r.height;camera.updateProjectionMatrix();}
new ResizeObserver(resize).observe($('viewport'));
new ResizeObserver(()=>{
  const section=document.querySelector('.viewport-section'),tools=document.querySelector('.view-tools');
  section.style.setProperty('--group-top',`${tools.getBoundingClientRect().bottom-section.getBoundingClientRect().top+10}px`);
}).observe(document.querySelector('.view-tools'));

function loading(title, subtitle) {
  $('capture-view').disabled=true;$('open-batch-capture').disabled=true;
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
    const mesh=new THREE.Mesh(g,material);mesh.userData.node=n;mesh.userData.portalId=n.id;wallGroup.add(mesh);wallMeshes.set(n.id,mesh);
    const line=new THREE.LineLoop(new THREE.BufferGeometry().setFromPoints(outline),new THREE.LineBasicMaterial({color:0x91ffe8,transparent:true,opacity:.65}));line.userData.portalId=n.id;wallGroup.add(line);
    const label=document.createElement('span');label.className='node-label';label.textContent=n.label;label.tabIndex=-1;label.setAttribute('aria-label',`Select portal ${n.label}`);
    label.onclick=()=>{if(state.groupMode)toggleGroupWall(n.id);};
    label.onkeydown=event=>{if(state.groupMode&&['Enter',' '].includes(event.key)){event.preventDefault();event.stopPropagation();toggleGroupWall(n.id);}};
    $('node-labels').append(label);labelElements.set(n.id,label);
  }
}
function drawEdges() {
  disposeGroup(edgeGroup);if(!state.scene)return;
  const edges=$('show-edges').checked ? state.scene.edges : state.scene.edges.filter(e=>e.source===state.selected);
  for(const kind of ['portal','movement']) {
    const lines=[];
    for(const e of edges) {
      if(!portalVisible(e.source)||!portalVisible(e.target))continue;
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
    if(!portalVisible(e.source)||!portalVisible(e.target))continue;
    const pts=e.kind==='portal' ? [e.path[1],e.path[2]] : e.path;
    const line=new THREE.Line(new THREE.BufferGeometry().setFromPoints(pts.map(vec)),new THREE.LineDashedMaterial({color:e.kind==='portal'?0xd0bbff:0xffd394,dashSize:.7,gapSize:.3,transparent:true,opacity:1,depthTest:false}));line.computeLineDistances();routeGroup.add(line);
    const orb=new THREE.Mesh(new THREE.SphereGeometry(.2,12,8),new THREE.MeshBasicMaterial({color:e.kind==='portal'?0xd8caff:0xffd394,depthTest:false}));orb.position.copy(vec(e.path[e.path.length-1]));routeGroup.add(orb);
  }
}
function updateWallStyles(capture=false) {
  for(const [id,mesh] of wallMeshes) {
    const grouped=!capture&&state.groupMode&&state.groupSelection.has(id);
    mesh.material.color.setHex(grouped?0xffdd70:state.blocked.has(id)?0xb86e78:id===state.start?0xa7ffe8:id===state.end?0xffcb87:0x60cbbf);
    mesh.material.opacity=grouped||id===state.selected || id===state.start || id===state.end ? .85 : .46;
    const label=labelElements.get(id);label.classList.toggle('selected',id===state.selected || id===state.start || id===state.end);label.classList.toggle('blocked',state.blocked.has(id));
    label.classList.toggle('group-selected',grouped);
    if(state.groupMode){label.setAttribute('role','button');label.setAttribute('aria-pressed',String(state.groupSelection.has(id)));}
    else{label.removeAttribute('role');label.removeAttribute('aria-pressed');}
  }
}
function renderWallList(){
  const query=$('wall-search').value.toLowerCase();
  $('wall-list').innerHTML=(state.scene?.nodes || []).filter(n=>(n.label+' '+n.name).toLowerCase().includes(query)).map(n=>`<div class="wall-item"><input type="checkbox" data-portal-visible="${n.id}" aria-label="Show portal ${esc(n.label)}" ${!state.hiddenPortals.has(n.id)?'checked':''}><button class="wall-row ${n.id===state.selected?'selected':''}" data-wall="${n.id}"><span class="wall-id">${esc(n.label)}</span><span class="wall-name">${n.launch?'Launch wall':n.type.includes('Circular')?'Circular wall':'Portal wall'}<small>${n.width.toFixed(1)} × ${n.height.toFixed(1)} m · Z ${n.position[2].toFixed(1)}</small></span><span class="wall-state ${state.blocked.has(n.id)?'blocked':''}"></span></button></div>`).join('');
  $('wall-list').querySelectorAll('[data-wall]').forEach(b=>{b.classList.toggle('group-selected',state.groupMode&&state.groupSelection.has(b.dataset.wall));b.onclick=()=>state.groupMode?toggleGroupWall(b.dataset.wall):selectWall(b.dataset.wall);});
  $('wall-list').querySelectorAll('[data-portal-visible]').forEach(input=>input.onchange=()=>{input.checked?state.hiddenPortals.delete(input.dataset.portalVisible):state.hiddenPortals.add(input.dataset.portalVisible);applyPortalVisibility(true);});
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
  renderWallList();updateWallStyles();drawEdges();$('only-selected-portal').disabled=false;if(start||destination)findRoute();
}
let down=null;
let groupDrag=null;
function cancelGroupDrag(){
  if(groupDrag&&renderer.domElement.hasPointerCapture(groupDrag.id))renderer.domElement.releasePointerCapture(groupDrag.id);
  groupDrag=null;$('wall-selection-box').classList.add('hidden');
}
function mapPoint(event){const rect=renderer.domElement.getBoundingClientRect();return {x:Math.max(0,Math.min(rect.width,event.clientX-rect.left)),y:Math.max(0,Math.min(rect.height,event.clientY-rect.top))};}
function pickWall(event){
  const r=renderer.domElement.getBoundingClientRect();pointer.set((event.clientX-r.left)/r.width*2-1,-(event.clientY-r.top)/r.height*2+1);raycaster.setFromCamera(pointer,camera);
  return raycaster.intersectObjects([...wallMeshes.values()].filter(mesh=>portalVisible(mesh.userData.node.id)))[0]?.object.userData.node.id;
}
// Capture primary gestures before OrbitControls sees them. Navigation and route
// picking resume on Done; pointer cancellation never applies an unfinished box.
renderer.domElement.addEventListener('pointerdown',event=>{
  if(!state.groupMode||!state.scene||event.button!==0||!event.isPrimary)return;
  event.preventDefault();event.stopImmediatePropagation();down=null;
  groupDrag={id:event.pointerId,start:mapPoint(event),remove:event.shiftKey};renderer.domElement.setPointerCapture(event.pointerId);
},true);
renderer.domElement.addEventListener('pointermove',event=>{
  if(!groupDrag||event.pointerId!==groupDrag.id)return;
  event.preventDefault();event.stopImmediatePropagation();const end=mapPoint(event),start=groupDrag.start;
  const box=$('wall-selection-box');box.classList.toggle('hidden',Math.hypot(end.x-start.x,end.y-start.y)<=5);box.classList.toggle('removing',groupDrag.remove);
  box.style.left=Math.min(start.x,end.x)+'px';box.style.top=Math.min(start.y,end.y)+'px';box.style.width=Math.abs(end.x-start.x)+'px';box.style.height=Math.abs(end.y-start.y)+'px';
},true);
renderer.domElement.addEventListener('pointerup',event=>{
  if(!groupDrag||event.pointerId!==groupDrag.id)return;
  event.preventDefault();event.stopImmediatePropagation();const end=mapPoint(event),{start,remove}=groupDrag;
  if(Math.hypot(end.x-start.x,end.y-start.y)>5){
    const points=state.scene.nodes.filter(n=>portalVisible(n.id)).flatMap(n=>{
      const v=vec(n.position).project(camera);return v.z>=-1&&v.z<=1&&Math.abs(v.x)<=1&&Math.abs(v.y)<=1?[{id:n.id,x:(v.x+1)/2*renderer.domElement.clientWidth,y:(1-v.y)/2*renderer.domElement.clientHeight}]:[];
    });
    for(const id of wallsInBox(points,start,end))remove?state.groupSelection.delete(id):state.groupSelection.add(id);
    refreshGroupSelection();
  }else{const id=pickWall(event);if(id)toggleGroupWall(id);}
  cancelGroupDrag();
},true);
renderer.domElement.addEventListener('pointercancel',cancelGroupDrag);
renderer.domElement.addEventListener('lostpointercapture',()=>{groupDrag=null;$('wall-selection-box').classList.add('hidden');});
renderer.domElement.addEventListener('pointerdown',event=>{down=[event.clientX,event.clientY];});
renderer.domElement.addEventListener('pointerup',event=>{
  if(state.groupMode||!state.scene || !down || event.button!==0 || Math.hypot(event.clientX-down[0],event.clientY-down[1])>5)return;
  const id=pickWall(event);if(id)selectWall(id,{start:event.shiftKey,destination:!event.shiftKey});
});
function renderMaps(){
  const query=$('map-search').value.toLowerCase();const ready=state.maps.filter(m=>m.ready&&!m.library);$('map-count').textContent=ready.length;
  $('map-list').innerHTML=ready.filter(m=>[m.name,m.id].some(name=>name.toLowerCase().includes(query))).map(m=>`<button class="map-row ${m.id===state.scene?.id?'active':''}" data-map="${m.id}"><span class="map-glyph">${m.name==='Academy'?'⌘':m.name==='Abyss'?'◇':'⌁'}</span><span class="map-name">${esc(m.name)}<small>${m.nodes} WALLS · ${m.edges} EDGES</small></span><span class="map-arrow">›</span></button>`).join('') || '<p class="intro">No matching extracted arenas.</p>';
  $('map-list').querySelectorAll('[data-map]').forEach(b=>b.onclick=()=>loadScene(b.dataset.map));
  renderImports();
}
async function loadScene(mid,{batch=false}={}) {
  if(batchRunning&&!batch)return;
  const gen=++state.generation;state.routeGeneration++;loading('Reading arena','Loading extracted geometry and its portal graph.');$('find-route').disabled=false;$('find-route').innerHTML='Find route <span>↗</span>';
  try {
    const s=await api('/api/maps/'+mid);if(gen!==state.generation)return;
    state.scene=s;state.start='';state.end='';state.selected=null;state.blocked.clear();state.route=null;$('wall-search').value='';document.querySelector('.right-panel').scrollTop=0;
    const hidden=readHiddenPortals()[mid];state.hiddenPortals=new Set(Array.isArray(hidden)?hidden.filter(id=>s.nodes.some(n=>n.id===id)):[]);
    state.clueGroups=normalizeClueGroups(readClueGroupStore()[mid],s.nodes.map(n=>n.id));
    setGroupMode(false);state.groupSelection.clear();state.editingGroup=null;state.wallGroups=normalizeGroups(readGroupStore()[mid],s.nodes.map(n=>n.id));$('group-name').value='';refreshGroupSelection();
    if(!batch&&new URLSearchParams(location.hash.slice(1)).get('map')!==mid)history.replaceState(null,'','#'+new URLSearchParams({map:mid}));
    for(const g of [geometryGroup,wallGroup,edgeGroup,routeGroup])disposeGroup(g);
    for(const material of surfaceMaterials.values())material.dispose();surfaceMaterials.clear();appearance=null;
    $('surface-mode').disabled=true;$('map-colors-status').textContent='Reading surface colors…';
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
    $('capture-portal-list').innerHTML=s.nodes.map(n=>`<option value="${n.id}">${esc(n.label)}</option>`).join('');
    makeWalls();updateWallStyles();applyPortalVisibility();renderWallList();
    const savedHeight=readCutoffHeights()[mid];
    setCutoffHeight(Number.isFinite(savedHeight)?savedHeight:bounds.max.y+1);
    $('dataset-details').innerHTML=`<p>${s.source.coverage?.landscapeRead??0} terrain patches · ${s.instances.length.toLocaleString()} mesh instances · ${s.source.geometryTriangles.toLocaleString()} instanced proxy triangles.</p><p>Base walk ${s.model.walkSpeed} m/s${s.model.assetParameters?.walkSpeed?' from the character asset':''}. Gravity and jump behavior are estimated; active mode modifiers are not resolved.</p><p class="${s.issues.length?'issue-count':''}">${s.issues.length} extraction notes. <button class="secondary" id="show-source-notes">Inspect sources</button></p><code>${esc(s.rootPackage)}<br>Revision ${esc(s.revision)}</code>`;
    $('show-source-notes').onclick=showSources;
    $('export-graph').href='/api/export/graph?'+new URLSearchParams({map:s.id,revision:s.revision});
    let nextAppearance;
    try{nextAppearance=await api('/api/colors/'+mid);}catch{nextAppearance={available:false,reason:'Surface colors are unavailable; showing neutral geometry.'};}
    if(gen!==state.generation)return;
    appearance=nextAppearance;
    $('surface-mode').disabled=!appearance.available;$('surface-mode').value=appearance.available?preferredSurfaceMode:'neutral';applySurfaceMode();
    const groups=new Map();for(const instance of s.instances){if(!instance.visible)continue;const slots=surfaceSlots(appearance?.meshes?.[instance.mesh],appearance?.components?.[instance.name]);const key=JSON.stringify([instance.mesh,slots]);if(!groups.has(key))groups.set(key,[]);groups.get(key).push(instance);}
    const entries=[...groups.entries()];let complete=0,failed=0,cursor=0;
    await Promise.all(Array.from({length:Math.min(batch?2:10,entries.length)},async()=>{
      while(cursor<entries.length){if(gen!==state.generation)return;const [,instances]=entries[cursor++],id=instances[0].mesh;try{const proxy=s.meshes.find(m=>m.id===id)?.viewProxy,g=await fetchMesh(id,proxy,gen);if(gen!==state.generation)return;const mesh=new THREE.InstancedMesh(g,geometryMaterial,instances.length);const row=appearance?.meshes?.[id];if(validSections(row,g.index.count,g.attributes.position.count)){g.clearGroups();for(const section of row.sections)g.addGroup(section.start,section.count,section.slot);mesh.userData.surfaceMaterials=surfaceSlots(row,appearance?.components?.[instances[0].name]).map(materialFor);}instances.forEach((v,i)=>mesh.setMatrixAt(i,matrix(v.matrix)));mesh.computeBoundingSphere();geometryGroup.add(mesh);}catch(e){failed++;}complete++;if(gen===state.generation)loading('Loading '+s.name,`${complete} / ${entries.length} mesh assets${failed?' · '+failed+' unavailable':''}`);}
    }));
    if(gen!==state.generation)return;applySurfaceMode();$('loading').classList.add('hidden');geometryGroup.visible=$('show-geometry').checked;$('capture-view').disabled=false;$('open-batch-capture').disabled=false;
    if(!s.nodes.length)toast('This map has no resolved player portal walls. Check its extraction notes.');
    if(failed)toast(`${failed} mesh assets could not be displayed; the extraction notes remain available.`);
    const hash=new URLSearchParams(location.hash.slice(1));if(!batch&&hash.get('map')===mid){state.start=hash.get('from')||'';state.end=hash.get('to')||'';$('start-wall').value=state.start;$('end-wall').value=state.end;findRoute();}
    return {scene:s,failedMeshes:failed};
  } catch(error){if(batch)throw error;if(gen===state.generation){loading('Map could not be loaded',error.message);toast(error.message);}}
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
$('show-geometry').onchange=()=>geometryGroup.visible=$('show-geometry').checked;$('cutaway').onchange=applyCutaway;$('show-edges').onchange=drawEdges;
$('show-portals').onchange=()=>applyPortalVisibility();
$('show-lines').onchange=()=>applyPortalVisibility();
$('show-all-portals').onclick=()=>setPortalVisibility('all');$('hide-all-portals').onclick=()=>setPortalVisibility('none');$('only-selected-portal').onclick=()=>setPortalVisibility('selected');
$('capture-show-all').onclick=()=>setPortalVisibility('all');$('capture-hide-all').onclick=()=>setPortalVisibility('none');
$('capture-portal-list').onchange=()=>{const shown=new Set([...$('capture-portal-list').selectedOptions].map(option=>option.value));state.hiddenPortals=new Set(state.scene.nodes.filter(n=>!shown.has(n.id)).map(n=>n.id));$('show-portals').checked=true;applyPortalVisibility(true);renderWallList();};
$('toggle-groups').onclick=()=>openGroups($('groups-panel').classList.contains('hidden'));
$('close-groups').onclick=()=>openGroups(false);
$('randomize-clue-groups').onclick=()=>{
  if(!state.scene?.nodes.length)return;
  const groups=randomClueGroups(state.scene.nodes.map(n=>n.id)),saved=readClueGroupStore();saved[state.scene.id]=groups;
  try{localStorage.setItem('portal-atlas-clue-groups',JSON.stringify(saved));}
  catch{toast('Browser storage is unavailable. Random groups could not be saved.');return;}
  state.clueGroups=groups;setGroupMode(false);applyGroupVisibility(groups[0],'only');
  toast('Six balanced groups saved. Showing group 1; choose a group or build up the clues.');
};
$('select-group-walls').onclick=()=>{if(state.scene){setGroupMode(true);refreshGroupSelection();}};
$('selection-open-groups').onclick=()=>openGroups();
$('finish-group-selection').onclick=()=>setGroupMode(false,{openPanel:true});
$('clear-group-selection').onclick=()=>{state.groupSelection.clear();refreshGroupSelection();};
for(const [id,action] of [['show-group-selection','show'],['hide-group-selection','hide'],['isolate-group-selection','only']])$(id).onclick=()=>applyGroupVisibility(state.groupSelection,action);
$('new-wall-group').onclick=()=>{state.editingGroup=null;$('group-name').value='';refreshGroupSelection();$('group-name').focus();};
$('group-name').oninput=()=>$('group-name').setCustomValidity('');
$('group-form').onsubmit=event=>{
  event.preventDefault();if(!state.scene||!state.groupSelection.size)return;
  const name=$('group-name').value.trim();
  if(!name){$('group-name').setCustomValidity('Enter a group name.');$('group-name').reportValidity();return;}
  const group={id:state.editingGroup||crypto.randomUUID(),name,walls:[...state.groupSelection]};
  const groups=state.editingGroup?state.wallGroups.map(g=>g.id===group.id?group:g):[...state.wallGroups,group];
  if(!saveGroups(groups))return;
  state.editingGroup=group.id;refreshGroupSelection();toast(`Group “${name}” saved in this browser.`);
};
$('cutoff-slider').oninput=()=>setCutoffHeight($('cutoff-slider').valueAsNumber,{remember:true});
$('surface-mode').onchange=()=>{preferredSurfaceMode=$('surface-mode').value;try{localStorage.setItem('portal-atlas-surface-mode',preferredSurfaceMode);}catch{}applySurfaceMode();};
$('cutoff-height').oninput=()=>setCutoffHeight($('cutoff-height').valueAsNumber,{remember:true,updateNumber:false});
$('cutoff-height').onchange=()=>{if(Number.isFinite($('cutoff-height').valueAsNumber))setCutoffHeight($('cutoff-height').valueAsNumber,{remember:true});else $('cutoff-height').value=cutoffHeight;};
$('cutoff-auto').onclick=()=>{
  if(!state.scene||!bounds)return;
  try{const heights=readCutoffHeights();delete heights[state.scene.id];localStorage.setItem('portal-atlas-cutoff-heights',JSON.stringify(heights));}catch{}
  setCutoffHeight(bounds.max.y+1);
};
$('show-labels').onchange=()=>$('node-labels').classList.toggle('hidden',!$('show-labels').checked);
$('reset-view').onclick=()=>fitView();$('view-top').onclick=()=>fitView('top');$('view-orbit').onclick=()=>fitView();
$('capture-view').onclick=async()=>{
  if(!state.scene||!$('loading').classList.contains('hidden'))return;
  const button=$('capture-view');button.disabled=true;button.setAttribute('aria-busy','true');
  const filename=screenshotFilename(state.scene.name,$('view-top').classList.contains('active')?'top':'3d');
  try{
    let capture;
    try{updateWallStyles(true);capture=captureMapView({renderer,world,camera,labels:$('node-labels')});}
    finally{updateWallStyles();}
    const image=await capture;
    downloadScreenshot(image,filename);toast('Map screenshot downloaded as PNG.');
  }catch(error){toast('Screenshot failed: '+error.message);}
  finally{button.disabled=!state.scene||!$('loading').classList.contains('hidden');button.removeAttribute('aria-busy');}
};
$('choose-arena').onclick=()=>$('import-dialog').showModal();$('map-title').style.cursor='pointer';$('import-button').onclick=()=>$('import-dialog').showModal();$('help-button').onclick=()=>$('help-dialog').showModal();
for(const b of document.querySelectorAll('[data-close]'))b.onclick=()=>$(b.dataset.close).close();
for(const b of document.querySelectorAll('[data-objective]'))b.onclick=()=>{state.objective=b.dataset.objective;document.querySelectorAll('[data-objective]').forEach(x=>x.classList.toggle('active',x===b));findRoute();};
for(const c of document.querySelectorAll('.edge-filters input'))c.onchange=findRoute;
$('max-difficulty').oninput=()=>$('difficulty-value').textContent=$('max-difficulty').value;$('max-difficulty').onchange=findRoute;
window.addEventListener('keydown',e=>{if(batchRunning)return;if(['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName))return;if(e.key.toLowerCase()==='r')fitView();if(e.key==='Escape'){if(state.groupMode){setGroupMode(false,{openPanel:true});return;}if(!$('groups-panel').classList.contains('hidden')){openGroups(false);return;}$('selection-card').classList.add('hidden');state.selected=null;drawEdges();updateWallStyles();}});
const batchLayerIds=['show-geometry','show-portals','show-labels','show-lines','show-edges','cutaway'];
setupBatchCapture({
  maps:()=>state.maps,
  currentMap:()=>state.scene&&$('loading').classList.contains('hidden')?state.scene.id:null,
  setRunning:active=>{
    if(active)batchControlState={enabled:controls.enabled,damping:controls.enableDamping};
    batchRunning=active;
    if(!active&&batchControlState){controls.enabled=batchControlState.enabled;controls.enableDamping=batchControlState.damping;resize();}
  },
  cancelLoad:()=>{state.generation++;},
  snapshot:()=>({
    map:state.scene.id,hash:location.hash,position:camera.position.toArray(),up:camera.up.toArray(),target:controls.target.toArray(),far:camera.far,
    damping:controls.enableDamping,controlsEnabled:controls.enabled,pixelRatio:renderer.getPixelRatio(),cutoffHeight,surfaceMode:$('surface-mode').value,
    layers:Object.fromEntries(batchLayerIds.map(id=>[id,$(id).checked])),hidden:[...state.hiddenPortals],selected:state.selected,start:state.start,end:state.end,
    blocked:[...state.blocked],route:state.route,groupSelection:[...state.groupSelection],editingGroup:state.editingGroup,groupMode:state.groupMode,groupName:$('group-name').value,
    groupsOpen:!$('groups-panel').classList.contains('hidden'),top:$('view-top').classList.contains('active'),wallSearch:$('wall-search').value,
    gridVisible:grid?.visible,selectionCardVisible:!$('selection-card').classList.contains('hidden')
  }),
  load:async(mid,settings)=>{
    controls.enabled=false;controls.enableDamping=false;controls.update();
    renderer.setPixelRatio(1);renderer.setSize(settings.width,settings.height,false);camera.aspect=settings.width/settings.height;camera.updateProjectionMatrix();
    $('show-geometry').checked=true;$('show-portals').checked=true;$('show-labels').checked=false;$('show-lines').checked=false;$('show-edges').checked=false;
    $('node-labels').classList.add('hidden');
    const result=await loadScene(mid,{batch:true});
    if(!result)return null;
    if(result.failedMeshes)throw new Error(`${result.failedMeshes} mesh assets failed to load; this map was skipped.`);
    const scene=result.scene;if(!scene.nodes.length)throw new Error('No portal walls to capture.');
    // Frame full portal apertures rather than just centers, including wall height.
    const points=scene.nodes.flatMap(node=>{
      const center=vec(node.position),right=vec(node.right).multiplyScalar(node.width/2),up=vec(node.up).multiplyScalar(node.height/2);
      return [-1,1].flatMap(x=>[-1,1].map(y=>center.clone().addScaledVector(right,x).addScaledVector(up,y)));
    });
    const box=new THREE.Box3().setFromPoints(points);if(grid)grid.visible=false;
    return {id:scene.id,name:scene.name,revision:scene.revision,wallIds:scene.nodes.map(node=>node.id),box:{min:box.min.toArray(),max:box.max.toArray()},
      cutoffHeight:$('cutaway').checked?cutoffHeight:null,surfaceMode:$('surface-mode').value,colorCoverage:coveragePercent(appearance),geometryUsable:scene.source.geometryUsable,
      geometryNotes:scene.issues.length,overviewGeometry:scene.overviewGeometry||null};
  },
  capture:async(clue,settings)=>{
    state.hiddenPortals=new Set(state.scene.nodes.map(node=>node.id).filter(id=>!clue.walls.includes(id)));
    state.selected=null;state.route=null;setGroupMode(false);applyPortalVisibility(false);updateWallStyles(true);
    camera.up.set(0,1,0);camera.position.fromArray(clue.camera.position);controls.target.fromArray(clue.camera.target);
    camera.far=Math.max(5000,clue.camera.distance*4);camera.updateProjectionMatrix();controls.update();
    // Render after layout/controls settle. captureMapView renders once more before copying.
    await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
    return captureMapView({renderer,world,camera,labels:$('node-labels'),width:settings.width,height:settings.height});
  },
  restore:async saved=>{
    state.generation++;controls.enableDamping=false;
    for(const [id,checked] of Object.entries(saved.layers))$(id).checked=checked;
    $('node-labels').classList.toggle('hidden',!saved.layers['show-labels']);
    renderer.setPixelRatio(saved.pixelRatio);
    const rect=$('viewport').getBoundingClientRect();renderer.setSize(rect.width,rect.height,false);camera.aspect=rect.width/rect.height;camera.far=saved.far;camera.updateProjectionMatrix();
    const result=state.scene?.id===saved.map&&$('loading').classList.contains('hidden')?{scene:state.scene}:await loadScene(saved.map,{batch:true});if(!result)throw new Error('Original map did not reload.');
    state.hiddenPortals=new Set(saved.hidden);state.start=saved.start;state.end=saved.end;state.selected=saved.selected;state.blocked=new Set(saved.blocked);state.route=saved.route;
    state.groupSelection=new Set(saved.groupSelection);state.editingGroup=saved.editingGroup;$('group-name').value=saved.groupName;$('wall-search').value=saved.wallSearch;
    $('start-wall').value=saved.start;$('end-wall').value=saved.end;$('surface-mode').value=saved.surfaceMode;applySurfaceMode();setCutoffHeight(saved.cutoffHeight);
    if(grid)grid.visible=saved.gridVisible;
    camera.position.fromArray(saved.position);camera.up.fromArray(saved.up);controls.target.fromArray(saved.target);controls.update();
    $('view-top').classList.toggle('active',saved.top);$('view-orbit').classList.toggle('active',!saved.top);
    setGroupMode(saved.groupMode);openGroups(saved.groupsOpen);refreshGroupSelection();applyPortalVisibility(false);renderResult();
    if(saved.selected&&saved.selectionCardVisible){selectWall(saved.selected);state.start=saved.start;$('start-wall').value=saved.start;}
    else $('selection-card').classList.add('hidden');
    controls.enableDamping=saved.damping;controls.enabled=saved.controlsEnabled;history.replaceState(null,'',saved.hash||'#'+new URLSearchParams({map:saved.map}));
  }
});
function animate(){
  requestAnimationFrame(animate);controls.update();renderer.render(world,camera);
  const width=renderer.domElement.clientWidth,height=renderer.domElement.clientHeight;
  const priority=new Set([state.selected,state.start,state.end,...(state.route?.walls||[]),...(state.groupMode?state.groupSelection:[])]),cells=new Map();
  const labels=(state.scene?.nodes||[]).map(n=>({n,v:vec(n.position).add(vec(n.up).multiplyScalar(n.height/2+.3)).project(camera)}));
  labels.sort((a,b)=>Number(priority.has(b.n.id))-Number(priority.has(a.n.id))||a.v.z-b.v.z);
  for(const {n,v} of labels){
    const el=labelElements.get(n.id);if(!el)continue;
    const x=(v.x+1)/2*width,y=(1-v.y)/2*height,cx=Math.floor(x/40),cy=Math.floor(y/20);
    let hidden=!portalVisible(n.id)||v.z>1||v.z< -1||Math.abs(v.x)>1||Math.abs(v.y)>1;
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
