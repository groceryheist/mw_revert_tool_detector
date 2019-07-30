import unittest
from wikitextToRegex import *
from siteInfo import * 
import re

class TestFr(unittest.TestCase):

    def setUp(self):
        self.siteInfo = SiteInfo("https://fr.wikipedia.org")

        
    # test that we can convert {{ifexpr}}.. templates into reasonable regular expressions
    def test_ifexpr(self):
        test_str = "Undid revision $1 by {{#ifexpr:{{#invoke:String|len|$2}}>25|[[User:$2]]|[[Special:Contributions/$2|$2]] ([[User talk:$2|talk]])}}"

        goal_str = r"(?:.*Undid\ revision\ (.*)\ by\ (?:\[\[User:(.*)\]\]|\[\[Special:Contributions/(.*)\|(.*)\]\]\ \(\[\[User\ talk:(.*)\|talk\]\]\)).*)"
        
        result = convert(test_str,self.siteInfo)
        self.assertEqual(result.pattern, goal_str)


    def test_ns(self):
        test_str = "{{ns:-1}}:RecentChanges"
        result = convert(test_str,self.siteInfo)
        goal_regex = re.compile('(?:.*(?:Spécial):RecentChanges.*)')
        self.assertEqual(result.pattern,goal_regex.pattern)
        

class TestKK(unittest.TestCase):

    def setUp(self):
        self.siteInfo = SiteInfo("https://kk.wikipedia.org")
        self.maxDiff = None

    def test_special(self):
        test_str = "{{#special:Contributions}}"
        result = convert(test_str, self.siteInfo)

        goal_regex = re.compile('(?:.*(?:Arnaýı:Үлесі|Arnaýı:Contributions|Arnaýı:Contribs|Special:Үлесі|Special:Contributions|Special:Contribs|special:Үлесі|special:Contributions|special:Contribs|Арнайы:Үлесі|Арнайы:Contributions|Арнайы:Contribs|арнайы:Үлесі|арнайы:Contributions|арнайы:Contribs|ارنايى:Үлесі|ارنايى:Contributions|ارنايى:Contribs).*)')


        self.assertEqual(goal_regex.pattern, result.pattern)

        self.assertTrue(result.match("Special:Contributions"))
        self.assertTrue(result.match("арнайы:Үлесі"))


    
