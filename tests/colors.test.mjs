import assert from 'node:assert/strict';
import test from 'node:test';
import {linearColor,validSections,surfaceSlots} from '../web/colors.js';

const row={vertices:4,indexCount:6,slots:['base','trim'],sections:[{start:0,count:3,slot:0},{start:3,count:3,slot:1}]};
test('section coverage must match the actual buffer',()=>{
  assert.equal(validSections(row,6,4),true);
  assert.equal(validSections(row,9,4),false);assert.equal(validSections(row,6,5),false);
  assert.equal(validSections({...row,sections:[{start:0,count:3,slot:0}]},6,4),false);
});
test('gaps, overlap, fractional triangles and unsafe slots fall back to neutral',()=>{
  for(const section of [{start:2,count:4,slot:1},{start:0,count:3,slot:1},{start:3,count:3,slot:256},{start:3,count:3,slot:-1}]){
    assert.equal(validSections({...row,sections:[row.sections[0],section]},6,4),false);
  }
});
test('component overrides retain null slots and leave other instances independent',()=>{
  assert.deepEqual(surfaceSlots(row,[null,'paint']),['base','paint']);
  assert.deepEqual(surfaceSlots(row,['different']),['different','trim']);
  assert.deepEqual(surfaceSlots(row),['base','trim']);
  assert.deepEqual(row.slots,['base','trim']);
});
test('unresolved slots are explicit neutral fallbacks',()=>{
  assert.deepEqual(surfaceSlots({...row,slots:[]}),[null,null]);
  assert.deepEqual(surfaceSlots({slots:[]}),[]);
  for(const invalid of [{...row,sections:[null]},{...row,slots:Array(257).fill(null)}]){
    assert.equal(validSections(invalid,6,4),false);assert.deepEqual(surfaceSlots(invalid),[]);
  }
});
test('only finite linear RGB triples can become colors',()=>{
  assert.deepEqual(linearColor({colorLinear:[1,.766,.336]}),[1,.766,.336]);
  for(const value of [null,{},[1,0],[1,-.1,0],[1,NaN,0],[2,0,0],['1',0,0]])assert.equal(linearColor({colorLinear:value}),null);
});
