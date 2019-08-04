import unittest
from wikitextToRegex import *
from siteInfo import * 
import re

class TestFr(unittest.TestCase):

    def setUp(self):
        self.siteInfo = SiteInfo("https://fr.wikipedia.org")
        self.maxDiff = None

    # test that we can convert {{ifexpr}}.. templates into reasonable regular expressions
    def test_ifexpr(self):
        test_str = "Undid revision $1 by {{#ifexpr:{{#invoke:String|len|$2}}>25|[[User:$2]]|[[Special:Contributions/$2|$2]] ([[User talk:$2|talk]])}}"

        goal_str = r"(?:.*Undid\ revision\ (.*)\ by\ (?:\[\[User:(.*)\]\]|\[\[Special:Contributions/(.*)\|(.*)\]\]\ \(\[\[User\ talk:(.*)\|talk\]\]\)).*)"
        
        result = convert(test_str,self.siteInfo)
        self.assertEqual(result.pattern, goal_str)


    def test_ns(self):
        test_str = "{{ns:-1}}:RecentChanges"
        result = convert(test_str, self.siteInfo)
        goal_regex = re.compile('(?:.*(?:Spécial):RecentChanges.*)')
        self.assertEqual(result.pattern,goal_regex.pattern)
        
    def test_ifexists(self):
        test_str = 'Révocation des modifications de [[Spécial:Contributions/$2|$2]] (retour à la dernière version de {{#ifexist: Utilisateur:$1 | [[User:$1{{!}}$1]] | [[Spécial:Contributions/$1{{!}}$1]]}})'
        
        goal_str = r'(?:.*Révocation\ des\ modifications\ de\ \[\[Spécial:Contributions/(.*)\|(.*)\]\]\ \(retour\ à\ la\ dernière\ version\ de\ (?:\ \[\[User:(.*)\|(.*)\]\]\ |\ \[\[Spécial:Contributions/(.*)\|(.*)\]\])\).*)'

        result = convert(test_str, self.siteInfo)

        self.assertEqual(result.pattern, goal_str)


class TestKK(unittest.TestCase):

    def setUp(self):
        self.siteInfo = SiteInfo("https://kk.wikipedia.org")
        self.maxDiff = None

    def test_special(self):
        test_str = "reverted edit by [[{{#special:Contributions}}/name|name]]"
        result = convert(test_str, self.siteInfo)

        goal_regex = re.compile('(?:.*reverted\ edit\ by\ \[\[(?:Arnaýı:Үлесі|Arnaýı:Contributions|Arnaýı:Contribs|Special:Үлесі|Special:Contributions|Special:Contribs|special:Үлесі|special:Contributions|special:Contribs|Арнайы:Үлесі|Арнайы:Contributions|Арнайы:Contribs|арнайы:Үлесі|арнайы:Contributions|арнайы:Contribs|ارنايى:Үлесі|ارنايى:Contributions|ارنايى:Contribs)/name\|name\]\].*)')


        self.assertEqual(goal_regex.pattern, result.pattern)

        self.assertTrue(result.match("reverted edit by [[Special:Contributions/name|name]]"))
        self.assertTrue(result.match("reverted edit by [[арнайы:Үлесі/name|name]]"))

    

class TestEn(unittest.TestCase):

    def setUp(self):
        self.siteInfo = SiteInfo("https://en.wikipedia.org")
        self.maxDiff=None

    def test_nested(self):

        test_str = "{{#ifexpr:{{#invoke:String|len|$2}}>25|[[{{ns:user}}:$2]]|[[{{#special:Contributions}}/$2|$2]]}}"

        goal_str = r"(?:.*(?:\[\[(?:User):(.*)\]\]|\[\[(?:Special:Contributions|Special:Contribs|special:Contributions|special:Contribs)/(.*)\|(.*)\]\]).*)"

        result = convert(test_str,self.siteInfo)

        self.assertEqual(result.pattern,goal_str)

        self.assertTrue(result.match("[[User:123]]"))

        self.assertTrue(result.match("[[Special:Contribs/123|123]]"))
        self.assertFalse(result.match("[[User:123Special:Contribs/123|123"))
        

class TestEnWiktionary(unittest.TestCase):
    def setUp(self):
        self.siteInfo = SiteInfo("https://en.wiktionary.org")
        self.maxDiff = None

    def test_fullurl(self):
        test_str = "Reverted edits by [[Special:Contributions/$2|$2]] ([{{fullurl:Special:Log|type=block&page=User:$2}} Block log]); changed back to last version by [[User:$1|$1]]"

        goal_str = r"(?:.*Reverted\ edits\ by\ \[\[Special:Contributions/(.*)\|(.*)\]\]\ \(\[(?:.*)\ Block\ log\]\);\ changed\ back\ to\ last\ version\ by\ \[\[User:(.*)\|(.*)\]\].*)"

        result = convert(test_str, self.siteInfo)
        self.assertEqual(result.pattern, goal_str)

    def test_urlencode(self):
        test_str = "([{{fullurl:Special:Log|type=block&page=User:{{urlencode:$2}}}} Block log])"
        goal_str = r"(?:.*\(\[(?:.*)\ Block\ log\]\).*)"
        
        result = convert(test_str, self.siteInfo)
        self.assertEqual(result.pattern, goal_str)
