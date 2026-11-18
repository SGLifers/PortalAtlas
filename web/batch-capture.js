// Seeded planning and a small ZIP writer. Captures stay in the browser until download.
import {randomClueGroups} from './portal-groups.js';

export function seededRandom(seed){
  let value=2166136261;
  for(const character of String(seed))value=Math.imul(value^character.codePointAt(0),16777619)>>>0;
  return ()=>{value=(value+0x6D2B79F5)>>>0;let t=value;t=Math.imul(t^(t>>>15),t|1);t^=t+Math.imul(t^(t>>>7),t|61);return ((t^(t>>>14))>>>0)/4294967296;};
}

export function randomCameraPose(box,aspect,fov,random){
  if(!Number.isFinite(aspect)||aspect<=0||!Number.isFinite(fov)||fov<=0||fov>=180)throw new Error('Invalid capture camera.');
  if(!box.min.every(Number.isFinite)||!box.max.every(Number.isFinite)||box.min.some((v,i)=>v>box.max[i]))throw new Error('Invalid map bounds.');
  const target=box.min.map((v,i)=>(v+box.max[i])/2);
  const radius=Math.max(1,Math.hypot(...box.min.map((v,i)=>(box.max[i]-v)/2)));
  const azimuth=random()*2*Math.PI,elevation=(35+random()*30)*Math.PI/180;
  const vertical=fov*Math.PI/180,horizontal=2*Math.atan(Math.tan(vertical/2)*aspect);
  const distance=radius/Math.sin(Math.min(vertical,horizontal)/2)*1.08;
  const direction=[Math.cos(elevation)*Math.sin(azimuth),Math.sin(elevation),Math.cos(elevation)*Math.cos(azimuth)];
  return {target,position:target.map((v,i)=>v+direction[i]*distance),azimuth,elevation,distance};
}

// Four walls first; progressively larger additions thereafter. Largest-remainder
// allocation preserves every wall exactly once and matches 4,5,7,9,11,14 at 50.
export function progressiveGroupSizes(total){
  if(!Number.isSafeInteger(total)||total<0)throw new Error('Invalid portal count.');
  const first=Math.min(4,total),remaining=total-first;
  // Tiny maps cannot have six nondecreasing groups starting at four. Allocate
  // their remaining walls evenly; supported Portle maps all have at least 24.
  if(total<24)return [first,...Array.from({length:5},(_,i)=>Math.floor(remaining/5)+(i>=5-remaining%5?1:0))];
  const weights=[1,3,5,7,10],extra=total-24;
  const quotas=weights.map(weight=>extra*weight/26),counts=quotas.map(Math.floor);
  const order=quotas.map((quota,i)=>({i,fraction:quota-counts[i]})).sort((a,b)=>b.fraction-a.fraction||b.i-a.i);
  for(let i=0,left=extra-counts.reduce((sum,count)=>sum+count,0);i<left;i++)counts[order[i].i]++;
  return [4,...counts.map(count=>count+4)];
}

export function clueCapturePlan({seed,mapId,wallIds,box,aspect,fov=47,fixedCamera=false,cumulative=true,distribution='progressive'}){
  if(!['progressive','even'].includes(distribution))throw new Error('Invalid portal distribution.');
  const evenGroups=randomClueGroups(wallIds,seededRandom(`${seed}:${mapId}:groups`)),shuffled=evenGroups.flat();
  let offset=0;
  const groups=distribution==='even'?evenGroups:
    progressiveGroupSizes(shuffled.length).map(size=>{const group=shuffled.slice(offset,offset+size);offset+=size;return group;});
  const random=seededRandom(`${seed}:${mapId}:camera`),first=randomCameraPose(box,aspect,fov,random);
  return {groups,clues:groups.map((group,index)=>({stage:index+1,walls:cumulative?groups.slice(0,index+1).flat():[...group],camera:fixedCamera||index===0?first:randomCameraPose(box,aspect,fov,random)}))};
}

export function safeCaptureName(value){return String(value).replace(/[^A-Za-z0-9_-]+/g,'-').slice(0,90)||'map';}

const crcTable=Uint32Array.from({length:256},(_,i)=>{for(let bit=0;bit<8;bit++)i=i&1?0xEDB88320^(i>>>1):i>>>1;return i>>>0;});
export function crc32(bytes){let value=0xFFFFFFFF;for(const byte of bytes)value=crcTable[(value^byte)&255]^(value>>>8);return (value^0xFFFFFFFF)>>>0;}
function header(size){const data=new Uint8Array(size);return {data,view:new DataView(data.buffer)};}

// PNGs are already compressed; stored ZIP entries avoid another large compression pass.
export class CaptureZip{
  constructor(maxBytes=384*1024*1024){this.maxBytes=maxBytes;this.parts=[];this.entries=[];this.offset=0;this.names=new Set();}
  canAdd(bytes,count=1){return this.offset+bytes+count*256<this.maxBytes;}
  async add(name,blob){
    if(!name||name.startsWith('/')||name.includes('..')||name.includes('\\')||this.names.has(name))throw new Error('Invalid or duplicate archive path.');
    if(!this.canAdd(blob.size))throw new Error('Capture archive reached its memory limit. Select fewer maps or a smaller resolution.');
    const filename=new TextEncoder().encode(name),crc=crc32(new Uint8Array(await blob.arrayBuffer()));
    const {data,view}=header(30);view.setUint32(0,0x04034B50,true);view.setUint16(4,20,true);view.setUint16(6,0x800,true);view.setUint16(12,33,true);
    view.setUint32(14,crc,true);view.setUint32(18,blob.size,true);view.setUint32(22,blob.size,true);view.setUint16(26,filename.length,true);
    this.entries.push({filename,crc,size:blob.size,offset:this.offset});this.parts.push(data,filename,blob);this.offset+=30+filename.length+blob.size;this.names.add(name);
  }
  finish(){
    const directory=[];let length=0;
    for(const entry of this.entries){
      const {data,view}=header(46);view.setUint32(0,0x02014B50,true);view.setUint16(4,20,true);view.setUint16(6,20,true);view.setUint16(8,0x800,true);view.setUint16(14,33,true);
      view.setUint32(16,entry.crc,true);view.setUint32(20,entry.size,true);view.setUint32(24,entry.size,true);view.setUint16(28,entry.filename.length,true);view.setUint32(42,entry.offset,true);
      directory.push(data,entry.filename);length+=46+entry.filename.length;
    }
    const {data,view}=header(22);view.setUint32(0,0x06054B50,true);view.setUint16(8,this.entries.length,true);view.setUint16(10,this.entries.length,true);view.setUint32(12,length,true);view.setUint32(16,this.offset,true);
    return new Blob([...this.parts,...directory,data],{type:'application/zip'});
  }
}
