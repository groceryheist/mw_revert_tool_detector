import unittest
from mwcomments.twinkle_patterns import find_summary_ad

class TestFr(unittest.TestCase):

    def setUp(self):
        self.url = "https://fr.wikipedia.org"

    def test(self):
        self.assertEqual(find_summary_ad(self.url),'using [[WP:TW|TW]]')

class TestEn(unittest.TestCase):
    def setUp(self):
        self.url = "https://en.wikipedia.org"

    def test(self):
        self.assertEqual(find_summary_ad(self.url),'([[WP:TW|TW]])')
        
