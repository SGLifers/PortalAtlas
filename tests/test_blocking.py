import unittest
from tools.finalize_scene import blocks


class BlockingChannelsTests(unittest.TestCase):
    def test_invisible_wall_stops_pawn_but_not_portal_launcher(self):
        row={'collision':{'CollisionProfileName':'InvisibleWall'}}
        self.assertTrue(blocks(row,'Pawn'));self.assertFalse(blocks(row,'PortalLauncher'))
    def test_explicit_channel_response_overrides_profile_default(self):
        row={'collision':{'CollisionProfileName':'Custom','CollisionResponses':{'ResponseArray':[{'Channel':'Pawn','Response':'Unknown::0'},{'Channel':'PortalLauncher','Response':'Unknown::2'}]}}}
        self.assertFalse(blocks(row,'Pawn'));self.assertTrue(blocks(row,'PortalLauncher'))
    def test_physics_only_volume_does_not_block_query_trace(self):
        self.assertFalse(blocks({'collision':{'CollisionEnabled':'Unknown::2'}},'Pawn'))
    def test_disabled_actor_is_not_solid(self):
        self.assertFalse(blocks({'enabled':False},'Pawn'))
    def test_named_block_response_is_supported(self):
        row={'collision':{'CollisionResponses':{'ResponseArray':[{'Channel':'Pawn','Response':'ECR_Block'}]}}}
        self.assertTrue(blocks(row,'Pawn'))


if __name__=='__main__':unittest.main()
