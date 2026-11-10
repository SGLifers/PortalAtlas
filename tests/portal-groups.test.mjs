import assert from 'node:assert/strict';
import test from 'node:test';
import {normalizeGroups,groupVisibility,wallsInBox,randomClueGroups,normalizeClueGroups} from '../web/portal-groups.js';

test('saved groups reject corrupt data and resolve only walls in the current map',()=>{
  const raw=[null,{id:'a',name:' Courtyard ',walls:['p1','p1','other-map','stale']},{id:'a',name:'Duplicate',walls:['p2']},{id:'b',name:'Gone',walls:['stale']},{id:'c',name:' ',walls:['p2']},{id:'d',name:'Valid',walls:['p2']}];
  assert.deepEqual(normalizeGroups(raw,['p1','p2']),[{id:'a',name:'Courtyard',walls:['p1']},{id:'d',name:'Valid',walls:['p2']}]);
  for(const value of [null,{},'broken',42])assert.deepEqual(normalizeGroups(value,['p1']),[]);
  assert.equal(raw[1].name,' Courtyard ');
});
test('overlapping groups change only their members; isolate replaces visibility',()=>{
  const ids=['a','b','c','d'],hidden=new Set(['c','d']);
  const afterHide=groupVisibility(ids,hidden,['a','c','wrong-map'],'hide');
  assert.deepEqual([...afterHide].sort(),['a','c','d']);
  const afterShow=groupVisibility(ids,afterHide,['b','c'],'show');
  assert.deepEqual([...afterShow].sort(),['a','d']);
  assert.deepEqual([...groupVisibility(ids,afterShow,['b','c'],'only')].sort(),['a','d']);
  assert.deepEqual([...hidden],['c','d']);
  assert.deepEqual([...groupVisibility(ids,new Set(),['a','b','c','d'],'only')],[]);
});
test('box selection is direction independent and includes boundary centers',()=>{
  const points=[{id:'a',x:10,y:20},{id:'b',x:15,y:30},{id:'c',x:20,y:40},{id:'outside',x:21,y:30},{id:'bad',x:NaN,y:25}];
  assert.deepEqual(wallsInBox(points,{x:10,y:20},{x:20,y:40}),['a','b','c']);
  assert.deepEqual(wallsInBox(points,{x:20,y:40},{x:10,y:20}),['a','b','c']);
  assert.deepEqual(wallsInBox(points,{x:0,y:0},{x:1,y:1}),[]);
});

test('random clue partitions cover every wall once and stay balanced for all remainders',()=>{
  let seed=42;
  const random=()=>{seed=(Math.imul(seed,1664525)+1013904223)>>>0;return seed/4294967296;};
  for(let count=0;count<=401;count++){
    const ids=Array.from({length:count},(_,i)=>`wall-${i}`),original=[...ids];
    const groups=randomClueGroups(ids,random),sizes=groups.map(group=>group.length);
    assert.equal(groups.length,6);
    assert.deepEqual([...groups.flat()].sort(),[...ids].sort());
    assert.equal(new Set(groups.flat()).size,count);
    assert.ok(Math.max(...sizes)-Math.min(...sizes)<=1);
    if(count%6===0)assert.ok(sizes.every(size=>size===count/6));
    assert.deepEqual(ids,original);
  }
  assert.equal(randomClueGroups(['a','a','b']).flat().length,2);
});

test('reshuffling can change assignments without changing coverage or manual groups',()=>{
  const ids=Array.from({length:24},(_,i)=>`wall-${i}`);
  const first=randomClueGroups(ids,()=>0),saved=structuredClone(first);
  const next=randomClueGroups(ids,()=>0.999);
  assert.notDeepEqual(first,next);
  assert.deepEqual(first,saved);
  assert.deepEqual([...next.flat()].sort(),[...ids].sort());
});

test('saved clue groups require the complete current map, unique membership and balanced sizes',()=>{
  const ids=Array.from({length:13},(_,i)=>`wall-${i}`),groups=randomClueGroups(ids,()=>0.5);
  assert.deepEqual(normalizeClueGroups(JSON.parse(JSON.stringify(groups)),ids),groups);
  const restored=normalizeClueGroups(groups,ids);restored[0].pop();
  assert.equal(groups.flat().length,ids.length);
  const overlap=structuredClone(groups);overlap[1][0]=overlap[0][0];
  const unbalanced=structuredClone(groups);unbalanced[0].push(unbalanced[1].pop());
  const stale=structuredClone(groups);stale[0][0]='another-map';
  for(const value of [null,{},'broken',[],groups.slice(1),[null,...groups.slice(1)],overlap,unbalanced,stale]){
    assert.deepEqual(normalizeClueGroups(value,ids),[]);
  }
  assert.deepEqual(normalizeClueGroups(groups,[...ids,'new-wall']),[]);
  assert.deepEqual(normalizeClueGroups(groups,ids.slice(1)),[]);
});

test('each clue can isolate a disjoint group or reveal all groups through that stage',()=>{
  const ids=Array.from({length:20},(_,i)=>`wall-${i}`),groups=randomClueGroups(ids,()=>0.5);
  let previouslyShown=new Set();
  for(let index=0;index<6;index++){
    const only=groupVisibility(ids,new Set(ids),groups[index],'only');
    assert.deepEqual(ids.filter(id=>!only.has(id)).sort(),[...groups[index]].sort());
    const prefix=groups.slice(0,index+1).flat(),hidden=groupVisibility(ids,new Set(ids),prefix,'only');
    assert.equal(ids.filter(id=>!hidden.has(id)).length,prefix.length);
    assert.ok([...previouslyShown].every(id=>!hidden.has(id)));
    previouslyShown=new Set(prefix);
  }
  assert.equal(previouslyShown.size,ids.length);
});
