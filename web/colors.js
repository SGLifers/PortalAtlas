// Appearance data is optional. Invalid or mismatched sections keep neutral geometry.
export function linearColor(record){
  const rgb=record?.colorLinear;
  return Array.isArray(rgb)&&rgb.length===3&&rgb.every(v=>Number.isFinite(v)&&v>=0&&v<=1)?rgb:null;
}

export function validSections(row,indexCount,vertexCount){
  if(!row||row.indexCount!==indexCount||row.vertices!==vertexCount||!Array.isArray(row.slots)||row.slots.length>256||!Array.isArray(row.sections)||!row.sections.length)return false;
  let end=0;
  for(const s of row.sections){
    if(!s||typeof s!=='object')return false;
    if(!Number.isInteger(s.start)||!Number.isInteger(s.count)||!Number.isInteger(s.slot)||s.start!==end||s.count<0||s.count%3||s.slot<0||s.slot>255)return false;
    end+=s.count;if(end>indexCount)return false;
  }
  return end===indexCount;
}

export function surfaceSlots(row,overrides){
  if(!row||!Array.isArray(row.slots)||row.slots.length>256||!Array.isArray(row.sections)||!row.sections.every(s=>s&&Number.isInteger(s.slot)&&s.slot>=0&&s.slot<=255))return [];
  const length=Math.max(row.slots.length,...row.sections.map(s=>s.slot+1));
  if(length>256)return [];
  return Array.from({length},(_,i)=>(Array.isArray(overrides)?overrides[i]:null)??row.slots[i]??null);
}
