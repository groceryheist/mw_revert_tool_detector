import unittest
from . import *

class TestUndos(unittest.TestCase):
    def test_huggle(self):
        message = "Message re. Dirty (disambiguation) (HG) (3.4.8)"
        self.assertSetEqual(set(match(message,'enwiki')),{"huggle"})

    def test_twinkle(self):
        message = "Reverted to revision 902745694 by Bmclaughlin9 (talk): Unsourced likely vandalism (TW)"
        self.assertSetEqual(set(match(message,'enwiki')),{"twinkle","rollback"})

    def test_undo(self):
        message = "Undid revision 902317645 by 148.255.110.193 (talk) Unsourced addition and ethnicities do not go in the lead"
        self.assertSetEqual(set(match(message,'enwiki')),{"undo"})

    def test_rollback(self):
        message = "Reverted edits by Justthefacts98 (talk) to last revision by Someguy1221"
        self.assertSetEqual(set(match(message,'enwiki')),{'huggle','rollback'})
