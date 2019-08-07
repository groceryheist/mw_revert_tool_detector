import unittest
from functools import partial
from itertools import islice
import mwcomments.util 
mwcomments.util.iterate_commits = partial(mwcomments.util.iterate_commits, max_count=2)
import mwcomments.util as util
from mwcomments.wikiToolMap import WikiToolMap, WikiToolMapEncoder
from mwcomments.siteInfo import SiteInfo
import json

class TestFromAllSources(unittest.TestCase):

    def test_ltwiki(self):
        test_siteInfos = {'ltwiki':SiteInfo("https://lt.wikipedia.org")}
        result = WikiToolMap.from_all_sources(siteInfos = test_siteInfos)
        result = result.convert_to_regex(test_siteInfos)
        test_comment = "Anuliuotas naudotojo [[Special:Contributions/12]] ([[User talk:123]]) darytas keitimas 123 (TW)"
        test_date = "2006-12-07T12:13:06+00:00"
        test_wiki='ltwiki'
        self.assertSetEqual(set(result.match(test_comment, test_wiki, test_date)), {'undo','twinkle'})

    def test_kkwiki(self):
        test_siteInfos = {'kkwiki':SiteInfo("https://kk.wikipedia.org"),'enwiki':SiteInfo("https://en.wikipedia.org")}
        
        result = WikiToolMap.from_all_sources(siteInfos = test_siteInfos)
#        print(result)
        result = result.convert_to_regex(test_siteInfos)
        print(result['kkwiki']._toolMap['undo'])

        test_comment = "Reverted edits by [[Special:Contributions/name|name]] ([[User talk:name|talk]]) to last revision by [[User:name2|name]]"
        test_date = "2019-06-25T12:13:14+00:00"
        test_wiki='kkwiki'
        match = result.match(test_comment,test_wiki,test_date)
        self.assertSetEqual(set(match),{'rollback'})
        print(result['kkwiki']._toolMap['undo'])
        

        ## aawiki fallsback to enwiki
    def test_aawiki(self):
        test_siteInfos = {'enwiki':SiteInfo("https://en.wikipedia.org"),'aawiki':SiteInfo("https://aa.wikipedia.org")}
        wtm = WikiToolMap.load_WikiToolMap(_siteInfos=test_siteInfos)
        print(wtm)

class TestLoadAndMatch(unittest.TestCase):

    def setUp(self):
        self.wtm = WikiToolMap.load_WikiToolMap()

    def test_enwiki(self):
        test_str = "Reverted edits by [[Special:Contribs/name|name]] ([[User talk:name|talk]]) to last version by [[User:name2|name]]"
        test_date = "2019-06-25T12:13:14+00:00"
        test_wiki='enwiki'
        match = self.wtm.match(test_str, test_wiki, test_date)
        self.assertSetEqual(set(match),{'rollback'})
