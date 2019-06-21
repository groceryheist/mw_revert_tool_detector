 # the first priority is on *.wikipedia.org/wiki/Mediawiki:Undo-summary
# then comes ./mediawiki-extensions-WikimediaMessages/
# finally comes ./mediawiki/languages/il8n/
from itertools import chain
from functools import reduce, partial
import os
import subprocess
import re
import glob
import json
from concurrent.futures import ThreadPoolExecutor
from pkg_resources import resource_string, resource_exists
user_agent = "mw_revert_tool_detector, project by groceryheist (Nathan TeBlunthuis) <nathante@uw.edu>))"

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

    wikimedia_sites = dict(gen_sitematrix(site_matrix))
    
    if os.path.exists("resources"):
        if not os.path.exists("resources/wikimedia_sites.json"):
            json.dump(wikimedia_sites, open("resources/wikimedia_sites.json",'w'))

    return wikimedia_sites

def load_wiki_patterns():

    if resource_exists(__name__, 'resources/wiki_patterns.json'):
        wiki_patterns_str = resource_string(__name__, 'resources/wiki_patterns.json')
        return json.loads(wiki_patterns_str.decode())

    properties = ['undo-summary','rollback-success']
    from_mediawiki = load_from_mediawiki(properties)

    from_extensions = load_from_extensions(properties)

    wikimedia_sites = load_sitematrix()

    from_api = load_from_api(wikimedia_sites)

    patterns = {}

    for wiki_db, site_info in wikimedia_sites.items():
        props1 = from_api.get(wiki_db,{})
        lang = site_info['lang']
        props2 = from_extensions.get(lang,{})
        props3 = from_mediawiki.get(lang,{})

        patterns[wiki_db] = {**props3, **{**props2, **props1}}

    json.dump(patterns, open("resources/wiki_patterns.json",'w'))
    return patterns
                    
def to_regex(summary):
    dollar_replace = re.compile("\\\\\\$\\d")
    gender_replace = re.compile("\\\\{\\\\{GENDER.*\\\\}\\\\}")
    special_replace = re.compile("Special\\\\\\:")
    usertalk_replace = re.compile("User\\\\ talk\\\\\\:")
    
    # remove final periods
    if summary[-1] == '.':
        summary = summary[0:-1]

    summary = re.escape(summary)

    re1 = dollar_replace.sub('(.*)',summary)
    re2 = gender_replace.sub("(.*)",re1)
    re3 = special_replace.sub('(.*)',re2)
    re4 = usertalk_replace.sub('(.*)',re3)
    return r"(?:.*{0}.*)".format(re4)

def clone_if_not_available(repo_url):
    repo_name = repo_url.split('/')[-2]
    if not os.path.exists("temp/{0}".format(repo_name)):
        if not os.path.exists("temp"):
            os.mkdir("temp")
        os.chdir("temp")
        subprocess.call(["git","clone",repo_url])
        os.chdir("..")

def load_from_api(wikimedia_sites):
    it = chain(_load_rollback_from_api(wikimedia_sites), _load_undo_from_api(wikimedia_sites))

    return reduce(agg_patterns, it, {})

def _load_rollback_from_api(wikimedia_sites):
    it = _load_prefix_from_api(wikimedia_sites, "rollback-success")
    return ((wiki_db, "rollback", pattern) for wiki_db, pattern in it)

def _load_undo_from_api(wikimedia_sites):
    it = _load_prefix_from_api(wikimedia_sites, "undo-summary")
    return ((wiki_db, "undo", pattern) for wiki_db, pattern in it)

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

    allpages = res['query']['allpages']
    if len(allpages) > 0:
        for page in allpages:
            # then we get the text of that page
            res2 = api.get(action="parse",page=page['title'],prop="text")
            html_parsed = bs(res2['parse']['text']['*'], features="lxml")
            print("found api settings for {0}".format(wiki_db))
            yield (wiki_db, to_regex(html_parsed.getText().strip()))


def agg_patterns(d, t):
    wiki, prop, pattern = t
    if wiki in d:
        prop_patterns = d[wiki]
        if prop in prop_patterns:
            d[wiki][prop].append(pattern)
        else:
            d[wiki][prop] = [pattern]
    else:
        d[wiki] = {prop:[pattern]}

    return d

def load_from_extensions(properties):
    clone_if_not_available("https://github.com/wikimedia/mediawiki-extensions-WikimediaMessages/")
    path_to_overrides = "temp/mediawiki-extensions-WikimediaMessages/i18n/wikimediaoverrides"
    it = load_json(path_to_overrides, properties)
    return reduce(agg_patterns, it, {})
    
def load_from_mediawiki(properties):
    clone_if_not_available("https://github.com/wikimedia/mediawiki/")
    it = load_json("temp/mediawiki/languages/i18n/", properties)
    return reduce(agg_patterns, it, {})

def load_json(path, properties):
    regex = re.compile(r".*/(.*)\.json")
    variant_regex = re.compile(r".*/([^-]*).*\.json")
    languagesWithVariants = ['en','crh','gan','iu','kk','ku','shi','sr','tg','uz','zh']
    glob_str = "{0}/*.json".format(path)
    languages_files = glob.glob(glob_str)
    for f in languages_files:
        pre_lang = variant_regex.match(f).groups()[0]
        is_variant = pre_lang in languagesWithVariants
        lang = regex.match(f).groups()[0]
        translations = json.load(open(f,'r'))
        for prop in properties:
            if prop in translations:
                summary_regex = to_regex(translations[prop])
                if not is_variant:
                    yield (lang, prop.split('-')[0],summary_regex)
                else: 
                    yield (pre_lang, prop.split('-')[0],summary_regex)

wiki_patterns = load_wiki_patterns()

def match(comment, wiki): 

    props = wiki_patterns[wiki]
    for k, properties in props.items():
        for prop in properties: 
            if re.match(prop, comment):
                yield k

    if re.match(huggle_pattern, comment):
        yield "huggle"

    if re.match(twinkle_pattern, comment):
        yield "twinkle"


huggle_pattern = r".*\(HG\).*"
twinkle_pattern = r".*\(TW\).*"
