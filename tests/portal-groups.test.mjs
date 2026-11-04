import assert from 'node:assert/strict';
import test from 'node:test';
import {normalizeGroups,groupVisibility,wallsInBox} from '../web/portal-groups.js';

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
