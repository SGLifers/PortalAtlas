// Groups store stable wall IDs, scoped to one map. Ignore stale or malformed
// browser data without allowing a group to affect another map's walls.
export function normalizeGroups(value, wallIds) {
  if (!Array.isArray(value)) return [];
  const valid=new Set(wallIds),seen=new Set();
  return value.flatMap(group=>{
    if (!group || typeof group.id!=='string' || !group.id || seen.has(group.id) || typeof group.name!=='string' || !Array.isArray(group.walls)) return [];
    const name=group.name.trim().slice(0,80);
    const walls=[...new Set(group.walls.filter(id=>valid.has(id)))];
    if (!name || !walls.length) return [];
    seen.add(group.id);
    return [{id:group.id,name,walls}];
  });
}

export function groupVisibility(wallIds, hidden, members, action) {
  const valid=new Set(wallIds),targets=new Set([...members].filter(id=>valid.has(id)));
  const result=new Set([...hidden].filter(id=>valid.has(id)));
  if (action==='only') return new Set(wallIds.filter(id=>!targets.has(id)));
  for (const id of targets) {
    if (action==='show') result.delete(id);
    else if (action==='hide') result.add(id);
  }
  return result;
}

// Shuffle the entire map before partitioning. Remainders go to the first groups,
// so every wall occurs once and group sizes differ by at most one.
export function randomClueGroups(wallIds, random=Math.random) {
  const shuffled=[...new Set(wallIds)];
  for(let i=shuffled.length-1;i>0;i--){
    const j=Math.floor(random()*(i+1));
    [shuffled[i],shuffled[j]]=[shuffled[j],shuffled[i]];
  }
  const size=Math.floor(shuffled.length/6),remainder=shuffled.length%6;
  let offset=0;
  return Array.from({length:6},(_,index)=>{
    const count=size+(index<remainder?1:0),group=shuffled.slice(offset,offset+count);
    offset+=count;return group;
  });
}

// A saved partition is usable only if it still covers this map exactly once.
// Reject the whole set instead of silently keeping missing/overlapping groups.
export function normalizeClueGroups(value, wallIds) {
  if(!Array.isArray(value)||value.length!==6||value.some(group=>!Array.isArray(group)))return [];
  const valid=new Set(wallIds),members=value.flat(),sizes=value.map(group=>group.length);
  if(members.length!==valid.size||new Set(members).size!==valid.size||members.some(id=>!valid.has(id))||Math.max(...sizes)-Math.min(...sizes)>1)return [];
  return value.map(group=>[...group]);
}

// Coordinates are viewport pixels. A drag in either direction selects visible
// wall centers; offscreen and behind-camera points are excluded by the caller.
export function wallsInBox(points, start, end) {
  const left=Math.min(start.x,end.x),right=Math.max(start.x,end.x);
  const top=Math.min(start.y,end.y),bottom=Math.max(start.y,end.y);
  return points.filter(p=>Number.isFinite(p.x)&&Number.isFinite(p.y)&&p.x>=left&&p.x<=right&&p.y>=top&&p.y<=bottom).map(p=>p.id);
}
