import unittest
import os
from util import parse_localized_namespaces

class TestPhpFuncs(unittest.TestCase):

    def test_convert_php_dict(self):
        
        test_str = """
        $namespaceNames = array(
                NS_MEDIA            => 'Taspa',
                NS_SPECIAL          => 'Arnaýı',
                NS_TALK             => 'Talqılaw',
                NS_USER             => 'Qatıswşı',
                NS_USER_TALK        => 'Qatıswşı_talqılawı',
                NS_PROJECT_TALK     => '$1_talqılawı',
                NS_FILE             => 'Swret',
                NS_FILE_TALK        => 'Swret_talqılawı',
                NS_MEDIAWIKI        => 'MedïaWïkï',
                NS_MEDIAWIKI_TALK   => 'MedïaWïkï_talqılawı',
                NS_TEMPLATE         => 'Ülgi',
                NS_TEMPLATE_TALK    => 'Ülgi_talqılawı',
                NS_HELP             => 'Anıqtama',
                NS_HELP_TALK        => 'Anıqtama_talqılawı',
                NS_CATEGORY         => 'Sanat',
                NS_CATEGORY_TALK    => 'Sanat_talqılawı',
        );
        """

        tmpfile = open('.temp', 'w')
        tmpfile.write(test_str)
        tmpfile.flush()
        result = parse_localized_namespaces('.temp')

        goal = {-2: 'Taspa',
                -1: 'Arnaýı',
                1: 'Talqılaw',
                2: 'Qatıswşı',
                3: 'Qatıswşı_talqılawı',
                5: '$1_talqılawı',
                6: 'Swret',
                7: 'Swret_talqılawı',
                8: 'MedïaWïkï',
                9: 'MedïaWïkï_talqılawı',
                10: 'Ülgi',
                11: 'Ülgi_talqılawı',
                12: 'Anıqtama',
                13: 'Anıqtama_talqılawı',
                14: 'Sanat',
                15: 'Sanat_talqılawı'}
        self.assertEqual(result, goal)
        os.remove('.temp')
