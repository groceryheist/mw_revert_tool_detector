from .siteMatrix import SiteMatrix
from functools import reduce, partial
from .toolMap import ToolMap, ToolMapEncoder
from .util import get_api, clone_if_not_available, get_fallback_langs
from .patternIndex import TimedPattern
from collections import defaultdict
import re
from pkg_resources import resource_exists, resource_string
import json


class WikiToolMap(object):
    __slots__ = ['wikiToolMap']

    EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    resource_path = 'resources/wiki_patterns.json' 

    def __init__(self, wikiToolMap):
        self.wikiToolMap = wikiToolMap

    def match(editSummary):
        toolMap = self.wikiToolMap[editSummary.wiki]
        return toolMap.match(editSummary)

    @staticmethod
    def from_all_sources(properties = [('undo-summary', 'undo'), ('revertpage', 'rollback')]):
        #    we could make this steaming potentially
        if resource_exists(__name__, WikiToolMap.resource_path):
            wiki_patterns_str = resource_string(__name__, WikiToolMap.resource_path)
            return WikiToolMap._load_from_resource(wiki_patterns_str.decode())

        from_mediawiki = WikiToolMap._load_from_mediawiki(properties)
 
        from_extensions = WikiToolMap._load_from_extensions(properties)

        wikimedia_sites = SiteMatrix()

        from_api = WikiToolMap._load_from_api(wikimedia_sites)

        wtm = WikiToolMap._merge([from_api, from_mediawiki, from_extensions], wikimedia_sites)

        wtm.save()

        return wtm

    @staticmethod
    def _load_from_api(wikimedia_sites):
        it = chain(WikiToolMap._load_rollback_from_api(wikimedia_sites),
                   WikiToolMap._load_undo_from_api(wikimedia_sites))
        wtm = WikiToolMap._agg_patterns(it)
        return wtm

    @staticmethod
    def _load_rollback_from_api(wikimedia_sites):
        it = WikiToolMap._load_prefix_from_api(wikimedia_sites, "revertpage")
        return map(lambda wiki_db, timedPattern, page_title:
                   (wiki_db, "rollback_nouser" if page_title.endswith("-nouser") else "rollback", timedPattern),
                   it)

    @staticmethod
    def _load_undo_from_api(wikimedia_sites):
        it = WikiToolMap._load_prefix_from_api(wikimedia_sites, "undo-summary")
        return map(lambda wiki_db, timedPattern, page_title:
                   (wiki_db, "undo_nouser" if page_title.endswith("-nouser") else "undo", timedPattern),
                   it)

    @staticmethod
    def _load_prefix_from_api(wikimedia_sites, page_prefix):
        with ThreadPoolExecutor() as executor:
            return chain(* executor.map(partial(WikiToolMap._scrape_api, page_prefix = page_prefix), wikimedia_sites.items()))

    @staticmethod
    def _scrape_api(wikimedia_site, page_prefix):
        from bs4 import BeautifulSoup as bs
        import mwapi

        wiki_db, site_info = wikimedia_site

        # first we search for the page we're looking for
        api = get_api(site_info['url'])

        try:
            res = api.get(action="query", list="allpages", apprefix=page_prefix, aplimit="max", apnamespace=8)
        except mwapi.errors.ConnectionError as e:
            print(e)
            return

        except ValueError as e:
            print(e)
            return

        except mwapi.errors.APIError as e:
            print(e)
            return

        allpages = res['query']['allpages']

        for page in allpages:
            print("found api settings for {0}".format(wiki_db))
            # then we get the text of that page
            res2 = api.get(action="query",titles=[page['title']],prop="revisions",rvprop=['content','timestamp'], rvlimit='max')
            res_page = res2['query']['pages'][str(page['pageid'])]
            for revision in res_page['revisions']:
                wiki_text = revision['*']
                timestamp = revision['timestamp']
                timestamp = datetime.datetime.strptime(timestamp,"%Y-%m-%dT%H:%M:%SZ")
                timestamp = timestamp.replace(tzinfo = datetime.timezone.utc)
                msg = [line for line in wiki_text.split('\n') if len(line) > 0][0]

                timedPattern = TimedPattern(time=timestamp, pattern=msg.strip())

                yield (wiki_db, timedPattern, page['title'])


    @staticmethod
    def _merge(wikiToolMaps, wikimedia_sites):
        reduce(lambda left, right: left.merge(right, wikimedia_sites), wikiToolMaps[1:], wikiToolMaps[0])
    
    # OLD COMMENT: need to make this slightly fancier to account for time
    def merge(self, other, wikimedia_sites):
        not_found = []
        for wiki_db, site_info in wikimedia_sites.items():
            lang = site_info['lang']
            self_toolMap = self.wikiToolMap[wiki_db]
            other_toolMap = other[wiki_db]

            merged_toolmap = self_toolMap.merge(left_toolMap)

            # language fallbacks
            if len(merged_toolmap) == 0:
                get_fallback_langs(site_info)

                merged_toolMap = ToolMap()

                # could be a problem here. should we be checking all the fallback langs?
                for lang in fall_back_langs:
                    self_toolMap = self.wikiToolMap[lang]
                    merged_toolmap.add_fallback(self_toolMap)
                    other_toolMap = other.wikiToolMap[lang]
                    merged_toolMap.add_fallback(other_toolMap)

                self.wikiToolMap[wiki_db] = merged_toolmap

    @staticmethod
    def _load_from_resource(path):
        wikiToolMap = json.loads(resource_string(path))
        wikiToolMap.update({k:ToolMap.from_json_dict(v) for k,v in wikiToolMap.items()})
        return WikiToolMap(wikiToolMap)

    @staticmethod
    def _load_from_mediawiki(properties):
        git_path = clone_if_not_available("https://github.com/wikimedia/mediawiki/")
        config_path = "languages/i18n/"
        return WikiToolMap._load_from_git(git_path, config_path, properties)

    @staticmethod
    def load_from_extensions(properties):
        git_path = clone_if_not_available("https://github.com/wikimedia/mediawiki-extensions-WikimediaMessages/")
        config_path = "/i18n/wikimediaoverrides"
        return WikiToolMap._load_from_git(git_path, config_path, properties)

    @staticmethod    
    def _load_from_git(git_path, config_path, properties):
        it = chain(* WikiToolMap._load_json(git_path, config_path, properties))
        
        wikiToolMap = WikiToolMap._agg_patterns(it)
        return WikiToolMap(wikiToolMap)

    @staticmethod
    def _agg_patterns(it):
        d = defaultdict(ToolMap)

        for k, v, in it.items():
            d[k].add(v)

        return d

    # warning! this is super not thread-safe
    @staticmethod
    def _load_json(git_path, config_path, properties):
        # config_path = 'languages/il18n'
        # git_path = 'temp/mediawiki'

        import git
        # first find the language files
        glob_str = "{0}/*.json".format(os.path.join(git_path, config_path))
        languages_files = set(glob.glob(glob_str))

        ## TODO: use global variants instead of this.
        def parse_file(f, timestamp):
            regex = re.compile(r".*/(.*)\.json")
            variant_regex = re.compile(r".*/([^-]*).*\.json")
            languagesWithVariants = ['en','crh','gan','iu','kk','ku','shi','sr','tg','uz','zh']

            pre_lang = variant_regex.match(f).groups()[0]
            is_variant = pre_lang in languagesWithVariants
            lang = regex.match(f).groups()[0]

            if not os.path.exists(f):
                return

            translations = json.load(open(f,'r'))
            for prop, label in properties:
                if prop in translations:
                    summary = translations[prop]
                    timedPattern = TimedPattern(time=timestamp, pattern=summary)
            
                    if not is_variant:
                        yield (lang, label, timedPattern)
                    else: 
                        yield (pre_lang, label, timedPattern)

        def find_diffs(path, languages_files):
            repo = git.Repo(path)
            language_files = [f.replace(path+'/',"") for f in languages_files]
            commits = repo.iter_commits('master', language_files)
            for commit in commits:
                print(commit.committed_datetime)
                parent = commit.parents[0] if commit.parents else WikiToolMap.EMPTY_TREE_SHA
                diffs  = {
                    diff.a_path: diff for diff in commit.diff(parent)
                }

                repo.git.checkout('-f', commit.hexsha)

                # probably want to check if the file is created or if it's missing for some other bad reason
                for objpath, stats in commit.stats.files.items():
                    if objpath in language_files:
                        diff = diffs.get(objpath)
                        if not diff:
                            for diff in diffs.values():
                                if diff.b_path == path and diff.renamed:
                                    break

                        yield list(parse_file(os.path.join(path, objpath), commit.committed_datetime))

        return find_diffs(git_path, languages_files)


    def save(self):
        jsonstr = json.dumps(self, ToolMapEncoder)
        of = open(WikiToolMap, 'w')
        of.write(jsonstr)

    def match(self, editSummary):
        toolMap = self.wikiToolMap[editSummary.wiki]
        return toolMap.match(editSummary)
