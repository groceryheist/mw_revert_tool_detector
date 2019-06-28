# the first priority is on *.wikipedia.org/wiki/Mediawiki:Undo-summary
# then comes ./mediawiki-extensions-WikimediaMessages/
# finally comes ./mediawiki/languages/il8n/
import datetime
import git
import tempfile
from itertools import chain
from functools import reduce, partial
import os
import subprocess
import re
import glob
import json
from concurrent.futures import ThreadPoolExecutor
from pkg_resources import resource_string, resource_exists
import sortedcontainers
from sortedcontainers import SortedList
user_agent = "mw_revert_tool_detector, project by groceryheist (Nathan TeBlunthuis) <nathante@uw.edu>))"
EMPTY_TREE_SHA = "4b825dc642cb6eb9a060e54bf8d69288fbee4904"

SortedPairList = partial(SortedList,key = lambda pair: pair[0])

# we want, dbname -> (url, lang)
def load_sitematrix():

    if resource_exists(__name__, 'resources/wikimedia_sites.json'):
        wikimedia_sites = resource_string(__name__, 'resources/wikimedia_sites.json')
        return json.loads(wikimedia_sites.decode())

    import mwapi
    api = mwapi.Session("https://en.wikipedia.org", user_agent = user_agent)
    site_matrix = api.get(action='sitematrix')['sitematrix']

    def gen_sitematrix(site_matrix):
        for i, data in site_matrix.items():
            if type(data) is not dict:
                continue

            lang = data['code']

            for site_data in data['site']:
                yield (site_data['dbname'],{'url':site_data['url'], 'lang':lang})

        for site_data in site_matrix['specials']:
            lang = site_data['lang']
            yield (site_data['dbname'],{'url':site_data['url'], 'lang':lang})

    # add wikidata manually
    wikimedia_sites = dict(gen_sitematrix(site_matrix))
    
    if os.path.exists("resources"):
        if not os.path.exists("resources/wikimedia_sites.json"):
            json.dump(wikimedia_sites, open("resources/wikimedia_sites.json",'w'))

    return wikimedia_sites

def _load_wiki_patterns_from_json(jsonobj):
    return {wiki:
            {
                prop: SortedPairList(((datetime.datetime.fromisoformat(t),
                                   re.compile(regex))
                                  for t, regex in values))
                for prop, values in props.items()
            }
            for wiki, props in jsonobj.items()}


def _merge_time_lists(old, new):
    # take all the olds that come before the first new
    if old is None or len(old) == 0:
        return new

    if new is None or len(new) == 0:
        return old

    min_new = new[0]
    kept_old = old.irange(None, min_new, inclusive=(True, False))
    new.update(kept_old)
    return new
    

def _merge_prop_dicts(old, new):
    return {k: _merge_time_lists(old.get(k), new.get(k)) for k in set(chain(old.keys(), new.keys()))}
            
    
# need to make this slightly fancier to account for time
def _merge_patterns(from_api, from_mediawiki, from_extensions):
    patterns = {}

    not_found = []
    for wiki_db, site_info in wikimedia_sites.items():
        props1 = from_api.get(wiki_db, SortedPairList([]))
        lang = site_info['lang']
        props2 = from_extensions.get(lang, SortedPairList([]))
        props3 = from_mediawiki.get(lang, SortedPairList([]))
        patterns[wiki_db] = _merge_prop_dicts(props3,
                                              _merge_prop_dicts(props2, props1))
        if len(patterns[wiki_db]) == 0:
            not_found.append(wiki_db)

    # for the ones still missing get siteinfo from the api
    for wiki_db in not_found:
        site_info = wikimedia_sites[wiki_db]
        fall_back_langs = get_fallback_langs(site_info)
        props = {}
        for lang in fall_back_langs:
            props1 = from_extensions.get(lang, SortedPairList([]))
            props2 = from_mediawiki.get(lang, SortedPairList([]))
            props = _merge_prop_dicts(props2,
                                      _merge_prop_dicts(props1, props))

        patterns[wiki_db] = props

    return patterns

def _save_patterns(patterns):
    patterns_to_json = {wiki:
                        {
                            prop:[(t.isoformat(), regex.pattern)
                                  for t, regex in values]
                            for prop, values in props.items()
                        }
                        for wiki, props in patterns
    }

    json.dump(patterns_to_json, open("resources/wiki_patterns.json", 'w'))


def load_wiki_patterns():

    # we could make this steaming potentially
    # if resource_exists(__name__, 'resources/wiki_patterns.json'):
    #     wiki_patterns_str = resource_string(__name__, 'resources/wiki_patterns.json')
    #     jsonobj = json.loads(wiki_patterns_str.decode())

    #     # conver the datastructure
    #     return _load_wiki_patterns_from_json(jsonobj) 

    properties = [('undo-summary', 'undo'), ('revertpage', 'rollback')]

    from_mediawiki = load_from_mediawiki(properties)

    from_extensions = load_from_extensions(properties)

    wikimedia_sites = load_sitematrix()

    from_api = load_from_api(wikimedia_sites)

    patterns = _merge_patterns(from_api, from_mediawiki, from_extensions)

    _save_patterns(patterns)
    
    # we need to sort the patterns in reverse chronological order
    return patterns

def get_fallback_langs(site_info):
    import mwapi
    api = mwapi.Session(site_info['url'], user_agent)
    try:
        res = api.get(action='query', meta='siteinfo')

    except mwapi.errors.APIError as e:
        print(e)
        return

    except ValueError as e:
        print(e)
        return

    try:
        fall_backlangs = res['query']['general']['fallback']
    except KeyError as e:
        return

    try:
        lang = res['query']['general']['lang']
        yield lang

    except KeyError as e:
        pass

    for lang in fall_backlangs:
        yield lang['code']

def to_regex(summary, ):
    dollar_replace = re.compile(re.escape("\$") + "\d")
    gender_replace = re.compile(re.escape("\{\{") + "GENDER.*" + re.escape("\}\}"))

    # remove final periods
    if summary[-1] == '.':
        summary = summary[0:-1]

    summary = re.escape(summary)
    summary = dollar_replace.sub('(.*)',summary)
    summary = gender_replace.sub("(.*)",summary)
    return re.compile(r"(?:.*{0}.*)".format(summary))

def clone_if_not_available(repo_url):
    repo_name = repo_url.split('/')[-2]
    dest_path = os.path.join("temp",repo_name)
    if not os.path.exists(dest_path):
        if not os.path.exists("temp"):
            os.mkdir("temp")
        os.chdir("temp")
        subprocess.call(["git","clone",repo_url])
        os.chdir("..")

    return dest_path

def load_from_api(wikimedia_sites):
    it = chain(_load_rollback_from_api(wikimedia_sites), _load_undo_from_api(wikimedia_sites))
    return reduce(agg_patterns, it, {})

def _load_rollback_from_api(wikimedia_sites):
    it = _load_prefix_from_api(wikimedia_sites, "revertpage")
    return ((wiki_db, "rollback", pattern, timestamp) for wiki_db, pattern, timstamp in it)

def _load_undo_from_api(wikimedia_sites):
    it = _load_prefix_from_api(wikimedia_sites, "undo-summary")
    return ((wiki_db, "undo", pattern, timestamp) for wiki_db, pattern, timestamp in it)

def _load_prefix_from_api(wikimedia_sites, page_prefix):
    with ThreadPoolExecutor() as executor:
        return chain(* executor.map(partial(_load_from_api,page_prefix = page_prefix), wikimedia_sites.items()))

def _load_from_api(wikimedia_site, page_prefix):
    from bs4 import BeautifulSoup as bs
    import mwapi
    
    wiki_db, site_info = wikimedia_site

    # first we search for the page we're looking for
    api = mwapi.Session(site_info['url'], user_agent=user_agent)

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

            msg = [line for line in wiki_text.split('\n') if len(line) > 0][0]

            yield (wiki_db, to_regex(msg.strip()), timestamp)


def agg_patterns(d, t):
    wiki, prop, pattern, time = t
    if wiki in d:
        prop_patterns = d[wiki]
        if prop in prop_patterns:
            l = d[wiki][prop]
            previous_time = l.bisect_right((time,pattern)) - 1
            if d[wiki][prop][previous_time][1] != pattern:
                d[wiki][prop].add( (time, pattern) )
        else:
            d[wiki][prop] = SortedPairList([(time, pattern)])
    else:
        d[wiki] = {prop: SortedPairList([(time, pattern)])}

    return d


def load_from_git(git_path, config_path, properties):
    it = chain(* load_json(git_path, config_path, properties))
    return reduce(agg_patterns, it, {})

def load_from_extensions(properties):
    git_path = clone_if_not_available("https://github.com/wikimedia/mediawiki-extensions-WikimediaMessages/")
    config_path = "/i18n/wikimediaoverrides"
    return load_from_git(git_path, config_path, properties)
    
def load_from_mediawiki(properties):
    git_path = clone_if_not_available("https://github.com/wikimedia/mediawiki/")
    config_path = "languages/i18n/"
    return load_from_git(git_path, config_path, properties)

# config_path = 'languages/il18n'
# git_path = 'temp/mediawiki'
# this is super not thread-safe
def load_json(git_path, config_path, properties):
    # first find the language files
    glob_str = "{0}/*.json".format(os.path.join(git_path, config_path))
    languages_files = set(glob.glob(glob_str))

    def parse_file(f, timestamp):
        print(f, timestamp)
        regex = re.compile(r".*/(.*)\.json")
        variant_regex = re.compile(r".*/([^-]*).*\.json")
        languagesWithVariants = ['en','crh','gan','iu','kk','ku','shi','sr','tg','uz','zh']

        pre_lang = variant_regex.match(f).groups()[0]
        is_variant = pre_lang in languagesWithVariants
        lang = regex.match(f).groups()[0]
        translations = json.load(open(f,'r'))
        for prop, label in properties:
            if prop in translations:
                summary_regex = to_regex(translations[prop])
                if not is_variant:
                    yield (lang, label, summary_regex, timestamp)
                else: 
                    yield (pre_lang, label, summary_regex, timestamp)

    def find_diffs(path, languages_files):
        repo = git.Repo(path)
        language_files = [f.replace(path+'/',"") for f in languages_files]
        commits = repo.iter_commits('master', language_files)
        for commit in commits:
            print(commit.committed_datetime)
            parent = commit.parents[0] if commit.parents else EMPTY_TREE_SHA
            diffs  = {
                diff.a_path: diff for diff in commit.diff(parent)
            }

            repo.git.checkout('-f', commit.hexsha)

            
            
            for objpath, stats in commit.stats.files.items():
                if objpath in language_files:
                    diff = diffs.get(objpath)
                    if not diff:
                        for diff in diffs.values():
                            if diff.b_path == path and diff.renamed:
                                break

                    yield list(parse_file(os.path.join(path, objpath), commit.committed_datetime))

    return find_diffs(git_path, languages_files)
                    

def match(comment, wiki, timestamp):

    global wiki_patterns
    if wiki_patterns is None:
        wiki_patterns = load_wiki_patterns()

    try:
        props = wiki_patterns[wiki]
    except KeyError as e:
        raise KeyError(str(e)) from e
    # iterating in reverse chronological order.
    # use the first pattern that matches that is not from the future
    for prop_name, sorted_list in props.items():
        for prop in properties:
            idx = sorted_list.bisect_left(timestamp)
            regexes = chain(sorted_list[idx], sorted_list[idx+1])

            for regex in regexes:
                if regex.matrch(comment):
                    yield prop_name

    if huggle_pattern.match(comment):
        yield "huggle"

    if twinkle_pattern.match(comment):
        yield "twinkle"


huggle_pattern = re.compile(r".*\(HG\).*")
twinkle_pattern = re.compile(r".*\(TW\).*")
wiki_patterns = None

if __name__ == "__main__":
    wiki_patterns = load_wiki_patterns()
