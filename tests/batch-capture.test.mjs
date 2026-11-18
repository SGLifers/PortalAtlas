import test from 'node:test';
import assert from 'node:assert/strict';
import {seededRandom,randomCameraPose,clueCapturePlan,progressiveGroupSizes,CaptureZip,crc32,safeCaptureName} from '../web/batch-capture.js';

const box={min:[-100,-10,-50],max:[90,30,70]},ids=Array.from({length:31},(_,i)=>`wall-${i}`);
const settings={seed:'repeatable',mapId:'MAP_Example',wallIds:ids,box,aspect:1.6};

test('seeded batches reproduce groups/poses regardless of map processing order',()=>{
  const first=clueCapturePlan(settings);
  clueCapturePlan({...settings,mapId:'MAP_Another'});
  assert.deepEqual(clueCapturePlan(settings),first);
  assert.notDeepEqual(clueCapturePlan({...settings,seed:'new distribution'}),first);
  assert.equal(new Set(first.groups.flat()).size,ids.length);
  assert.equal(first.clues[0].walls.length,4);
  assert.equal(first.clues[5].walls.length,31);
  assert.ok(first.clues.every((clue,i)=>i===0||first.clues[i-1].walls.every(id=>clue.walls.includes(id))));
});

test('growing groups match the requested example, remain exclusive and end with full coverage',()=>{
  assert.deepEqual(progressiveGroupSizes(50),[4,5,7,9,11,14]);
  for(let count=0;count<=1000;count++){
    const sizes=progressiveGroupSizes(count);
    assert.equal(sizes.length,6);assert.equal(sizes[0],Math.min(4,count));
    assert.equal(sizes.reduce((sum,size)=>sum+size,0),count);
    assert.ok(sizes.every(size=>Number.isSafeInteger(size)&&size>=0));
    if(count>=24)assert.ok(sizes.every((size,i)=>!i||size>=sizes[i-1]));
  }
  const wallIds=Array.from({length:50},(_,i)=>`id-${i}`),plan=clueCapturePlan({...settings,wallIds});
  assert.deepEqual(plan.clues.map(clue=>clue.walls.length),[4,9,16,25,36,50]);
  assert.equal(plan.groups.flat().length,50);assert.equal(new Set(plan.groups.flat()).size,50);
  assert.deepEqual(new Set(plan.groups.flat()),new Set(wallIds));
  assert.deepEqual(clueCapturePlan({...settings,distribution:'even'}).clues.map(clue=>clue.walls.length),[6,11,16,21,26,31]);
  assert.throws(()=>progressiveGroupSizes(-1));assert.throws(()=>progressiveGroupSizes(2.5));
  assert.throws(()=>clueCapturePlan({...settings,distribution:'bad'}));
});

test('fixed random angle and disjoint clue modes have the promised semantics',()=>{
  const plan=clueCapturePlan({...settings,fixedCamera:true,cumulative:false});
  assert.ok(plan.clues.every(clue=>JSON.stringify(clue.camera)===JSON.stringify(plan.clues[0].camera)));
  assert.deepEqual(plan.clues.map(clue=>clue.walls),plan.groups);
  assert.equal(new Set(plan.clues.flatMap(clue=>clue.walls)).size,ids.length);
});

test('random cameras keep all box corners in the frustum for landscape and portrait outputs',()=>{
  const random=seededRandom('frame checks');
  const dot=(a,b)=>a.reduce((sum,v,i)=>sum+v*b[i],0),unit=v=>v.map(x=>x/Math.hypot(...v));
  for(const aspect of [0.5,1,1.6,16/9,3])for(let index=0;index<60;index++){
    const pose=randomCameraPose(box,aspect,47,random);
    assert.ok(pose.elevation>=35*Math.PI/180&&pose.elevation<=65*Math.PI/180);
    const forward=unit(pose.target.map((v,i)=>v-pose.position[i]));
    const right=unit([-forward[2],0,forward[0]]);
    const up=[right[1]*forward[2]-right[2]*forward[1],right[2]*forward[0]-right[0]*forward[2],right[0]*forward[1]-right[1]*forward[0]];
    for(const x of [box.min[0],box.max[0]])for(const y of [box.min[1],box.max[1]])for(const z of [box.min[2],box.max[2]]){
      const offset=[x,y,z].map((v,i)=>v-pose.position[i]),depth=dot(offset,forward),vertical=Math.tan(47*Math.PI/360)*depth;
      assert.ok(depth>0);assert.ok(Math.abs(dot(offset,up))<vertical);assert.ok(Math.abs(dot(offset,right))<vertical*aspect);
    }
  }
  assert.throws(()=>randomCameraPose(box,0,47,random));
});

test('ZIP writer uses standard local/central headers, UTF-8 names and correct CRCs',async()=>{
  assert.equal(crc32(new TextEncoder().encode('123456789')),0xCBF43926);
  const zip=new CaptureZip();await zip.add('Dought/clue-01.png',new Blob(['image bytes']));await zip.add('manifest.json',new Blob(['{}']));
  const bytes=new Uint8Array(await zip.finish().arrayBuffer()),view=new DataView(bytes.buffer);
  assert.equal(view.getUint32(0,true),0x04034B50);assert.equal(view.getUint16(6,true),0x800);
  const end=bytes.length-22;assert.equal(view.getUint32(end,true),0x06054B50);assert.equal(view.getUint16(end+10,true),2);
  const directory=view.getUint32(end+16,true);assert.equal(view.getUint32(directory,true),0x02014B50);
  const size=view.getUint32(18,true),nameLength=view.getUint16(26,true),data=bytes.slice(30+nameLength,30+nameLength+size);
  assert.equal(new TextDecoder().decode(data),'image bytes');assert.equal(view.getUint32(14,true),crc32(data));
  assert.equal(safeCaptureName('../Dought / test'),'-Dought-test');
  await assert.rejects(()=>zip.add('../bad',new Blob(['x'])));
  await assert.rejects(()=>zip.add('manifest.json',new Blob(['x'])));
  await assert.rejects(()=>new CaptureZip(100).add('large',new Blob(['x'.repeat(101)])));
});
