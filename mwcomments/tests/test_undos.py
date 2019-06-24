import unittest
from ..undos import match 

class TestUndos(unittest.TestCase):
    def test_huggle(self):
        message = "Message re. Dirty (disambiguation) (HG) (3.4.8)"
        self.assertSetEqual(set(match(message,'enwiki')),{"huggle"})

    def test_twinkle(self):
        message = "Reverted to revision 902745694 by Bmclaughlin9 (talk): Unsourced likely vandalism (TW)"
        self.assertSetEqual(set(match(message,'enwiki')),{"twinkle"})

    def test_undo(self):
        message = "Undid revision 902317645 by [[Special:Contributions/148.255.110.193|148.255.110.193]] ([[User talk:148.255.110.193|talk]]) Unsourced addition and ethnicities do not go in the lead"
        self.assertSetEqual(set(match(message,'enwiki')),{"undo"})

        message = 'Undid revision 862258093 by [[Special:Contributions/110.141.35.105|110.141.35.105]] ([[User talk:110.141.35.105|talk]])'

        self.assertSetEqual(set(match(message,'enwiki')),{'undo'})
        
    def test_rollback(self):
        message = "Reverted edits by [[Special:Contribs/Justthefacts98|Justthefacts98]] ([[User talk:Justthefacts98|talk]]) to last version by Someguy1221 (HG)"
        self.assertSetEqual(set(match(message,'enwiki')),{'huggle','rollback'})

    def test_fr_undo(self):
        message = "Annulation de la [[Special:Diff/$1|modification]] de [[Special:Contributions/$2|$2]] ([[User talk:$2|d]])"
        self.assertSetEqual(set(match(message,'frwiki')),{'undo'})
