# if I run into more problems with json, just cut it out and use pickle
import git
from concurrent.futures import ThreadPoolExecutor
from .editSummary import EditSummary
from .siteList import SiteList, SiteListItem
from .siteInfo import SiteInfo
from functools import partial
from itertools import chain
from .toolMap import ToolMap
from .util import get_api, clone_if_not_available, fromisoformat
from .patternIndex import TimedPattern, PatternIndex
from sortedcontainers import SortedList
import re
from pkg_resources import resource_exists, resource_string
import json
import os
import datetime
from collections import namedtuple, defaultdict
import pickle

# Rename classes so relationship between wikiToolMap and toolMap is
# more obvious

class WikiToolMap(object):
    __slots__ = ('wikiToolMap')

    EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"
    resource_path = 'resources/wiki_patterns.pickle'

    def __init__(self, wikiToolMap):
        self.wikiToolMap = wikiToolMap

    def match(self, comment, wiki_db, date):
        """ 
        Look for an editing tool that matches the message for the given wiki 
        and time. This is the main api for end-users of the library)

        Keyword Arguments:
        comment -- the text of the edit summary.
        wiki_db -- the wiki_db code identifying where the edit was made.
        date -- an iso-formatted string or a python datetime object
        identifying the timestamp of the edit.
        """

        return self._match(EditSummary(date, comment, wiki_db))

    def _match(self, editSummary):
        """ 
        Look for an editing tool that matches the editSummary and 
        return the name of the tool.

        Keyword Arguments:
        editSummary -- An object with date, message, and wiki slots.
        """

        toolMap = self.wikiToolMap[editSummary.wiki]

        huggle_pattern = re.compile(
            r".*(:?(\(HG\)|\(\[\[.*\|HG\]\]\)|\(\[\[.*\|Huggle\]\]\))).*")
        twinkle_pattern = re.compile(
            r".*(:?\(TW\)|\(\[\[.*\|TW\]\]\)\)|\(\[\[.*\|Twinkle\]\]\)\)).*")
        stiki_pattern = re.compile(r".*(:?using\ \[\[WP:STiki\|STiki\]\]).*")

        tool_patterns = zip(["huggle", "twinkle", "stiki"], [
                            huggle_pattern, twinkle_pattern, stiki_pattern])
        tools = []
        for name, pattern in tool_patterns:
            if pattern.match(editSummary.message):
                tools.append(name)

        tools.extend(toolMap.match(editSummary))

        return tools

    @staticmethod
    def load_WikiToolMap(properties=[('undo-summary', 'undo'),
                                     ('revertpage', 'rollback')],
                         _siteInfos=None):
        if _siteInfos is None:
            if resource_exists(__name__, WikiToolMap.resource_path):
                wiki_patterns_str = resource_string(
                    __name__, WikiToolMap.resource_path)
                return WikiToolMap._load_from_resource(wiki_patterns_str)

            print("looking up siteinfos from the api")
            wikimedia_sites = SiteList()
            siteInfos = {}
            for site in wikimedia_sites:
                si = SiteInfo(site.url)
                if si.have_info:
                    siteInfos[site.dbname] = si

        else:
            siteInfos = _siteInfos

        print("loading toolmaps from all sources")
        wtm = WikiToolMap.from_all_sources(properties, siteInfos)

        wtm = wtm.convert_to_regex(siteInfos)

        return wtm

    # think about promoting SiteInfos to an object property
    @staticmethod
    def from_all_sources(properties=[('undo-summary', 'undo'),
                                     ('revertpage', 'rollback')],
                         siteInfos=None):
        #    we could make this steaming potentially

        # ok so we have a problem:
        # github is organized by language, but the API is wiki-specific
        from_api = WikiToolMap._load_from_api(siteInfos)

        from_mediawiki = WikiToolMap._load_from_mediawiki(
            properties, siteInfos)

        from_extensions = WikiToolMap._load_from_extensions(
            properties, siteInfos)

        from_git = from_mediawiki.merge(from_extensions)

        wtm = WikiToolMap._merge_api_git(from_api, from_git, siteInfos)

        return wtm

    @staticmethod
    def _load_from_api(siteInfos):
        it = chain(WikiToolMap._load_rollback_from_api(siteInfos),
                   WikiToolMap._load_undo_from_api(siteInfos))
        wtm = WikiToolMap._agg_patterns(it)
        return wtm

    @staticmethod
    def _load_rollback_from_api(siteInfos):
        it = WikiToolMap._load_prefix_from_api(siteInfos, "revertpage")
        return map(lambda t:
                   (t.wiki_db, "rollback_nouser" if t.page_title.endswith(
                       "-nouser") else "rollback", t.timedPattern),
                   it)

    def convert_to_regex(self, siteInfos):
        for wiki_db in siteInfos.keys():
            self.wikiToolMap[wiki_db].convert_to_regex(siteInfos[wiki_db])
        return self

    @staticmethod
    def _load_undo_from_api(siteInfos):
        it = WikiToolMap._load_prefix_from_api(siteInfos, "undo-summary")
        return map(lambda t:
                   (t.wiki_db, "undo_nouser" if t.page_title.endswith(
                       "-nouser") else "undo", t.timedPattern),
                   it)

    @staticmethod
    def _load_prefix_from_api(siteInfos, page_prefix):
        with ThreadPoolExecutor() as executor:
            return chain(*
                         executor.map(
                             partial(WikiToolMap._scrape_api,
                                     page_prefix=page_prefix),
                             siteInfos.items()))

    @staticmethod
    def _scrape_api(siteInfo, page_prefix):
        ApiTuple = namedtuple(
            "ApiTuple", ['wiki_db', 'page_title', 'timedPattern'])

        import mwapi
        wiki_db, siteInfo = siteInfo
        url = siteInfo.url

        # first we search for the page we're looking for
        api = get_api(url)

        try:
            res = api.get(action="query", list="allpages",
                          apprefix=page_prefix, aplimit="max", apnamespace=8)
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
            res2 = api.get(action="query",
                           titles=[page['title']],
                           prop="revisions",
                           rvprop=['content', 'timestamp'],
                           rvlimit='max')

            res_page = res2['query']['pages'][str(page['pageid'])]
            for revision in res_page['revisions']:
                wiki_text = revision['*']
                timestamp = revision['timestamp']
                timestamp = datetime.datetime.strptime(
                    timestamp, "%Y-%m-%dT%H:%M:%SZ")
                timestamp = timestamp.replace(tzinfo=datetime.timezone.utc)
                msg = [line for line in wiki_text.split(
                    '\n') if len(line) > 0][0]

                timedPattern = TimedPattern(
                    time=timestamp, pattern=msg.strip())

                yield ApiTuple(wiki_db=wiki_db,
                               page_title=page['title'],
                               timedPattern=timedPattern)

    @staticmethod
    def _merge_api_git(from_api, from_git, siteInfos):

        result = {}
        for wiki_db in siteInfos.keys():
            siteInfo = siteInfos[wiki_db]
            api_toolMap = from_api[wiki_db]
            git_toolMap = from_git[siteInfo.langcode]
            primary_toolMap = api_toolMap.merge(git_toolMap)

            # we may need fallback langs in the past
            # merge will use right-hand patterns if
            # there are no left-hand patterns before the time period
            # we assume that nobody every deletes a configuration
            # once it is created
            for lang in siteInfo.fallback_langs:
                git_toolMap = from_git[lang]
                if not git_toolMap.empty():
                    primary_toolMap = primary_toolMap.merge(git_toolMap)
            result[wiki_db] = primary_toolMap
        return WikiToolMap(result)

    # OLD COMMENT: need to make this slightly fancier to account for time
    def merge(self, other):
        for key in set(chain(self.wikiToolMap.keys(),
                             other.wikiToolMap.keys())):

            self_toolMap = self.wikiToolMap[key]
            other_toolMap = other[key]
            merged_toolmap = self_toolMap.merge(other_toolMap)
            self.wikiToolMap[key] = merged_toolmap

        return self

    @staticmethod
    def _load_from_json(s):
        jsonobj = json.loads(s)
        jsonobj.update({k: ToolMap.from_json_dict(v)
                        for k, v in jsonobj.items()})
        return WikiToolMap(jsonobj)


    @staticmethod
    def _load_from_mediawiki(properties, siteInfos):
        git_path = clone_if_not_available(
            "https://github.com/wikimedia/mediawiki/")
        config_path = "languages/i18n/"
        return WikiToolMap._load_from_git(git_path,
                                          config_path,
                                          properties,
                                          siteInfos)

    @staticmethod
    def _load_from_extensions(properties, siteInfos):
        git_path = clone_if_not_available(
            "https://github.com/wikimedia/mediawiki-extensions-WikimediaMessages/")

        config_path = "/i18n/wikimediaoverrides"
        return WikiToolMap._load_from_git(git_path,
                                          config_path,
                                          properties,
                                          siteInfos)

    @staticmethod
    def _load_from_git(git_path, config_path, properties, siteInfos):
        it = chain(* WikiToolMap._load_json(git_path,
                                            config_path,
                                            properties,
                                            siteInfos))

        wikiToolMap = WikiToolMap._agg_patterns(it)
        return WikiToolMap(wikiToolMap)

    @staticmethod
    def _agg_patterns(it):
        d = defaultdict(ToolMap)
        for key, label, timedPattern in it:
            d[key].add(label, timedPattern=timedPattern)

        return d

    # warning! this is super not thread-safe
    @staticmethod
    def _load_json(git_path, config_path, properties, siteInfos):
        from .util import iterate_commits
        import glob
        GitTuple = namedtuple("GitTuple", ['lang', 'label', 'timedPattern'])
        # config_path = 'languages/il18n'
        # git_path = 'temp/mediawiki'
        # first find the language files
        glob_str = "{0}/*.json".format(os.path.join(git_path, config_path))

        languages_files = set(glob.glob(glob_str))

        # we want to make it easy to operate on a subset of sites
        if siteInfos is not None:
            def extract_langcode(langfile):
                regex = re.compile(r".*/(.*).json")
                return regex.findall(langfile)[0]

            siteLangCodes = {si.langcode for _, si in siteInfos.items()}

            languages_files = {lf for lf in
                               languages_files
                               if extract_langcode(lf) in siteLangCodes}

        # TODO: use global variants instead of this.
        def parse_file(f, timestamp):

            regex = re.compile(r".*/(.*)\.json")
            lang = regex.match(f).groups()[0]

            if not os.path.exists(f):
                return

            translations = json.load(open(f, 'r'))
            for prop, label in properties:
                if prop in translations:
                    summary = translations[prop]
                    # the timestamps from git have special offset that we want to strip
                    
                    timestamp2 = fromisoformat(timestamp.isoformat())
                    timedPattern = TimedPattern(
                        time=timestamp2, pattern=summary)

                    yield GitTuple(lang=lang,
                                   label=label,
                                   timedPattern=timedPattern)

        def find_diffs(path, languages_files):

            language_files = [f.replace(path+'/', "") for f in languages_files]
            repo = git.Repo(path)
            # start at the head
            repo.git.checkout('-f', "master")

            for commit in iterate_commits(repo, language_files):
                print(commit.committed_datetime)
                parent = commit.parents[0] if commit.parents else WikiToolMap.EMPTY_TREE_SHA

                diffs = {
                    diff.a_path: diff for
                    diff in
                    commit.diff(parent)
                }

                repo.git.checkout('-f', commit)

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
        of = open(WikiToolMap.resource_path, 'wb')
        out_obj = {k:v.as_dict() for k, v in self.wikiToolMap.items()}
        pickle.dump(out_obj, of)

    def __getitem__(self, wiki_db):
        return self.wikiToolMap[wiki_db]

    def __repr__(self):
        return self.wikiToolMap.__repr__()

    @staticmethod
    def _load_from_resource(s):
        in_d = pickle.loads(s)

        loaded = {k:ToolMap.from_dict(v) for k, v in in_d.items()}
        loaded = WikiToolMap(loaded)
        
        if isinstance(list(loaded.wikiToolMap.keys())[0], SiteListItem):
            loaded.wikiToolMap = {k.dbname:v for k,v in loaded.wikiToolMap.items()}

        return loaded
#    return pickle.load(open('resources/wiki_patterns.pickle','rb'))


class WikiToolMapEncoder(json.JSONEncoder):
    def default(self, obj):

        # cases to handle
        if isinstance(obj, WikiToolMap):
            return obj.wikiToolMap

        if isinstance(obj, ToolMap):
            return obj._toolMap

        if isinstance(obj, PatternIndex):
            return obj.index

        if isinstance(obj, SiteInfo):
            return obj._asdict()

        if isinstance(obj, TimedPattern):
            import pdb
            pdb.set_trace()
            print("TimedPattern")

            return {'time': obj.time,
                    'pattern': obj.pattern}

        if isinstance(obj, re.Pattern):
            return obj.pattern

        if isinstance(obj, datetime.datetime):
            return obj.isoformat()

        if isinstance(obj, SortedList):
            res = list(obj)
            print("SortedList")
            print(res)

            return list(obj)

        return json.JSONEncoder().default(obj)

    def _iterencode(self, obj, markers=None):

        if isinstance(obj, tuple) and hasattr(obj, '_asdict'):
            gen = self._iterencode_dict(obj._asdict(), markers)
        else:
            gen = json.JSONEncoder._iterencode(self, obj, markers)
        for chunk in gen:
            yield chunk
