"""Wall-node routing with directed, side-aware angle/movement edges."""
import heapq
import math


def edge_cost(edge, objective='fastest'):
    seconds=max(.001,float(edge['seconds']))
    difficulty=max(0.,min(100.,float(edge['difficulty'])))
    if objective=='easiest':return seconds*.1+difficulty*.2+.5
    if objective=='balanced':return seconds+difficulty*.04
    return seconds


def route(scene, start, end, objective='fastest', kinds=None, blocked=(), max_difficulty=100):
    nodes={x['id']:x for x in scene['nodes']}
    if start not in nodes or end not in nodes:raise ValueError('Select two walls from this map')
    if start in blocked or end in blocked:raise ValueError('The selected wall is marked unavailable')
    if objective not in ('fastest','easiest','balanced'):raise ValueError('Unknown route objective')
    allowed=set(kinds if kinds is not None else ['portal','walk','jump','drop'])
    adjacency={}
    for edge in scene['edges']:
        if edge['kind'] not in allowed or edge['source'] in blocked or edge['target'] in blocked or edge['difficulty']>max_difficulty:continue
        adjacency.setdefault((edge['source'],edge.get('sourceSide',1)),[]).append(edge)
    # Side is state on one physical wall node. A route cannot silently switch to
    # the other face of a double-sided wall between two placements.
    queue=[];dist={};prev={}
    for side in nodes[start].get('sides',[1]):
        state=(start,side);dist[state]=0.;heapq.heappush(queue,(0.,state))
    goal=None
    while queue:
        cost,state=heapq.heappop(queue)
        if cost!=dist[state]:continue
        if state[0]==end:goal=state;break
        for edge in adjacency.get(state,[]):
            nxt=(edge['target'],edge.get('targetSide',1));candidate=cost+edge_cost(edge,objective)
            if candidate<dist.get(nxt,math.inf):
                dist[nxt]=candidate;prev[nxt]=(state,edge);heapq.heappush(queue,(candidate,nxt))
    if goal is None:return {'found':False,'reason':'No route satisfies these filters in the extracted graph.','edges':[]}
    result=[];s=goal
    while s in prev:
        s,edge=prev[s];result.append(edge)
    result.reverse()
    return {'found':True,'edges':result,'walls':[start]+[e['target'] for e in result],
            'seconds':round(sum(e['seconds'] for e in result),2),
            'difficulty':round(max((e['difficulty'] for e in result),default=0.),1),
            'placements':sum(e['kind']=='portal' for e in result),
            'distance':round(sum(e.get('distance',0) for e in result),1),
            'objective':objective,'cost':round(dist[goal],3),
            'assumptions':['Start at the selected wall with an active portal; replace the opposite portal at each placement.',
                           'Timing and jump physics use the editable model; the game has not been run to measure execution.']}
