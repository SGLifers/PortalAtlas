import unittest
from server.routing import route


def edge(a,b,seconds,difficulty=10,kind='portal',**kw):
    return {'id':a+b,'source':a,'target':b,'sourceSide':1,'targetSide':1,'seconds':seconds,'difficulty':difficulty,'kind':kind,**kw}


def graph(edges,nodes=None):return {'nodes':nodes or [{'id':x,'sides':[1]} for x in 'ABCD'],'edges':edges}


class RoutingTests(unittest.TestCase):
    def test_objectives_choose_different_paths(self):
        s=graph([edge('A','D',1,95),edge('A','B',2,10),edge('B','D',2,10)])
        self.assertEqual(route(s,'A','D')['walls'],['A','D'])
        self.assertEqual(route(s,'A','D','easiest')['walls'],['A','B','D'])
    def test_blocked_wall_cannot_be_used_as_intermediate(self):
        s=graph([edge('A','B',1),edge('B','D',1)])
        self.assertFalse(route(s,'A','D',blocked=['B'])['found'])
    def test_no_silent_switch_between_faces_of_one_wall(self):
        s=graph([edge('A','B',1,targetSide=-1),edge('B','D',1)],nodes=[{'id':'A','sides':[1]},{'id':'B','sides':[1,-1]},{'id':'D','sides':[1]}])
        self.assertFalse(route(s,'A','D')['found'])
    def test_forced_launch_arrival_is_not_a_standing_player(self):
        s=graph([edge('A','B',1),edge('B','D',1)],nodes=[{'id':'A'},{'id':'B','launch':True},{'id':'D'}])
        self.assertTrue(route(s,'A','B')['found']);self.assertFalse(route(s,'A','D')['found'])
        self.assertTrue(route(s,'B','D')['found'])
    def test_filters_and_maximum_difficulty(self):
        s=graph([edge('A','D',1,80),edge('A','B',1,10,'walk'),edge('B','D',1,10,'walk')])
        self.assertFalse(route(s,'A','D',kinds=['portal'],max_difficulty=50)['found'])
        self.assertEqual(route(s,'A','D',max_difficulty=50)['walls'],['A','B','D'])
    def test_directed_edges_are_not_reversed(self):self.assertFalse(route(graph([edge('A','D',1)]),'D','A')['found'])
    def test_same_wall_has_zero_cost(self):
        r=route(graph([]),'A','A');self.assertTrue(r['found']);self.assertEqual(r['seconds'],0)
    def test_movement_includes_entry_portal_setup(self):
        r=route(graph([edge('A','B',1,kind='walk'),edge('B','D',1)]),'A','D');self.assertEqual(r['placements'],2)
    def test_invalid_inputs_are_rejected(self):
        for objective,difficulty in [('unknown',100),('fastest',float('nan')),('fastest',101)]:
            with self.assertRaises(ValueError):route(graph([]),'A','D',objective,max_difficulty=difficulty)
        with self.assertRaises(ValueError):route(graph([]),'missing','D')


if __name__=='__main__':unittest.main()
