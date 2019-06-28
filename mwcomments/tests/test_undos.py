import unittest
import datetime
from datetime import datetime
from ..undos import match
from ..undos import load_json
from ..undos import _load_from_api
from ..undos import load_from_extensions
from ..undos import agg_patterns
from ..undos import clone_if_not_available
from ..undos import SortedPairList
from ..undos import _merge_prop_dicts
import json
from functools import partial, reduce
from itertools import islice, chain

fromisoformat = datetime.fromisoformat
class TestMatch(unittest.TestCase):
    def setUp(self):
        self.test_datetime = fromisoformat("2019-06-25")
        self.test_match = partial(match, datetime = test_datetime)

    def test_huggle(self):
        message = "Message re. Dirty (disambiguation) (HG) (3.4.8)"
        self.assertSetEqual(set(self.test_match(message,'enwiki')),{"huggle"})

    def test_twinkle(self):
        message = "Reverted to revision 902745694 by Bmclaughlin9 (talk): Unsourced likely vandalism (TW)"
        self.assertSetEqual(set(self.test_match(message,'enwiki')),{"twinkle"})

    def test_undo(self):
        message = "Undid revision 902317645 by [[Special:Contributions/148.255.110.193|148.255.110.193]] ([[User talk:148.255.110.193|talk]]) Unsourced addition and ethnicities do not go in the lead"
        self.assertSetEqual(set(self.test_match(message,'enwiki')),{"undo"})

        message = 'Undid revision 862258093 by [[Special:Contributions/110.141.35.105|110.141.35.105]] ([[User talk:110.141.35.105|talk]])'

        self.assertSetEqual(set(self.test_match(message,'enwiki')),{'undo'})
        
    def test_rollback(self):
        message = "Reverted edits by [[Special:Contribs/Justthefacts98|Justthefacts98]] ([[User talk:Justthefacts98|talk]]) to last version by Someguy1221 (HG)"
        self.assertSetEqual(set(self.test_match(message,'enwiki')),{'huggle','rollback'})

    def test_fr_undo(self):
        message = "Annulation de la [[Special:Diff/$1|modification]] de [[Special:Contributions/$2|$2]] ([[User talk:$2|d]])"
        self.assertSetEqual(set(self.test_match(message,'frwiki')),{'undo'})


class Test_Load_From_API(unittest.TestCase):

    def test_enwiki_undos(self):
        results = _load_from_api(("enwiki",{"url":"https://en.wikipedia.org"}),"undo-summary")

        known_value_1 = '["enwiki", "(?:.*Undid\\\\ revision\\\\ (.*)\\\\ by\\\\ \\\\[\\\\[Special:Contributions/(.*)\\\\|(.*)\\\\]\\\\]\\\\ \\\\(\\\\[\\\\[User\\\\ talk:(.*)\\\\|talk\\\\]\\\\]\\\\).*)", "2018-04-24T11:39:29"]'

        match_1 = False
        for result in results:
            result = (result[0],result[1],result[2],result[3].isoformat())
            if json.dumps(result) == known_value_1:
                match_1 = True
                break
        self.assertTrue(match_1)


class Test_Load_From_Git(unittest.TestCase):

    def test_enwiki_undos(self):
        results = load_json("temp/mediawiki","languages/i18n",[("undo-summary","undo")])
        
        known_value_1 = ("en", "undo", "(?:.*Undo\\ revision\\ (.*)\\ by\\ \\[\\[Special:Contributions/(.*)\\|(.*)\\]\\]\\ \\(\\[\\[User\\ talk:(.*)\\|talk\\]\\]\\).*)", "2019-06-14T18:12:51+00:00")
        
        match_1 = False
        for result in results:
            for prop in result:
                prop = (prop[0],prop[1],prop[2],prop[3].isoformat())
                if prop == known_value_1:
                    match_1 = True
                    break
            if match_1 is True:
                break

        self.assertTrue(match_1)

    def test_agg_patterns(self):
        d = {}
        date0=fromisoformat("2015-01-01")
        date0_1=fromisoformat("2015-01-02")
        date1=fromisoformat("2016-01-01")
        t0 = ('testwiki','testprop','testpattern0',date0)
        t0_1 = ('testwiki','testprop','testpattern0',date0_1)
        t1 = ('testwiki','testprop','testpattern1',date1)

        r0 = agg_patterns(d,t0)

        # test that we don't store duplicates
        r0 = agg_patterns(r0, t0_1)
        r1 = agg_patterns(r0, t1)

        self.assertTrue('testwiki' in r1)
        self.assertTrue(len(r1) == 1)

        self.assertTrue('testprop' in r1['testwiki'])
        self.assertTrue(len(r1['testwiki']) == 1)

        print(r1)
        self.assertTrue(r1['testwiki']['testprop'][0] == (date0, 'testpattern0'))
        self.assertTrue(r1['testwiki']['testprop'][1] == (date1, 'testpattern1'))


    def test_merge_prop_dicts(self):
        old_pair = (fromisoformat("2017-01-01"), "undo_old")
        new_pair = (fromisoformat("2016-01-01"), "undo_new")
        old = {'undo':
                 SortedPairList([old_pair])}

        new = {'undo':
                 SortedPairList([new_pair])}

        self.assertEqual(_merge_prop_dicts(old,new), new)

        old['rollback'] = SortedPairList([(fromisoformat("2016-01-01"),'rollback_old')])

        merged = _merge_prop_dicts(old,new)
        self.assertEqual(merged['rollback'], old['rollback'])
        
        really_old_pair = (fromisoformat("2015-01-01"), "undo_really_old")
        old['undo'].add(really_old_pair)
        merged = _merge_prop_dicts(old,new)
        self.assertEqual(merged['undo'],SortedPairList([really_old_pair, new_pair]))


    def test_load_json(self):
        git_path = clone_if_not_available("https://github.com/wikimedia/mediawiki/")
        config_path = "languages/i18n/"
        it = load_json(git_path, config_path, [('undo','undo-summary')])
        test_set = islice(it,10)
        it = chain(* test_set)

        reduced = reduce(agg_patterns, it, {})

        print(reduced)

