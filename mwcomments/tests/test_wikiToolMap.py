import unittest
from WikiToolMap import WikiToolMap, WikiToolMapEncoder
from siteInfo import SiteInfo
import json
import util
from functools import partial

class TestFromAllSources(unittest.TestCase):

    def setUp(self):
        util.iterate_commits = partial(util.iterate_commits, max_count=2)

    def test_ltwiki(self):
        test_siteInfos = {'ltwiki':SiteInfo("https://lt.wikipedia.org")}
        result = WikiToolMap.from_all_sources(siteInfos = test_siteInfos)
        print(result)
        print(json.dumps(result, cls=WikiToolMapEncoder))
        result = result.convert_to_regex(test_siteInfos)
        print(json.dumps(result, cls=WikiToolMapEncoder))

    def test_kkwiki(self):
        test_siteInfos = {'kkwiki':SiteInfo("https://kk.wikipedia.org")}
        result = WikiToolMap.from_all_sources(siteInfos = test_siteInfos)
        print(result)
        print(json.dumps(result, cls=WikiToolMapEncoder))
        result = result.convert_to_regex(test_siteInfos)
        print(json.dumps(result, cls=WikiToolMapEncoder))

        from_json = WikiToolMap._load_from_json(json.dumps(result, cls=WikiToolMapEncoder))
