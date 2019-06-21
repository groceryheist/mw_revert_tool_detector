 # the first priority is on *.wikipedia.org/wiki/Mediawiki:Undo-summary
# then comes ./mediawiki-extensions-WikimediaMessages/
# finally comes ./mediawiki/languages/il8n/
from itertools import chain
from functools import reduce, partial
import mwapi
import os
import subprocess
import re
import glob
import json
from bs4 import BeautifulSoup as bs

wiki_patterns = load_wiki_patterns(refresh=False)

huggle_pattern = r".*\(HG\)"

def match(comment, wiki): 
    patterns = patterns[wiki]
    for k, pattern in patterns.items():
        if pattern.match(comment):
            return k
    if huggle_pattern.match(comment):
        return "huggle"

    return None

def load_wiki_patterns(refresh=False, wikis=None):

    if os.path.exists("resources/patterns.pickle"):
        return json.load(open("resources/wiki_patterns.json",'r'))

    properties = ['undo-summary','rollback-success']
    from_mediawiki = load_from_mediawiki(properties)
    if wikis is None:
        wikis = set(from_mediawiki.keys())

    from_extensions = load_from_extensions(properties)
    from_api = load_from_api(wikis)

    patterns = {}

    for wiki, props in from_api.items():
        patterns[wiki] = props

    for wiki, props in from_extensions.items():
        if wiki not in patterns:
            patterns[wiki] = props
        else:
            patterns[wiki] = {** props, **patterns[wiki]}

    for wiki, props in from_mediawiki.items():
        if wiki not in patterns:
            patterns[wiki] = props
        else:
            patterns[wiki] = {** props, **patterns[wiki]}

    json.dump(patterns, open("resources/wiki_patterns.json",'w'))
                    
def to_regex(summary):
    dollar_replace = re.compile("\\\\\\$\\d")
    gender_replace = re.compile("\\\\{\\\\{GENDER.*\\\\}\\\\}")
    special_replace = re.compile("Special\\\\\\:")
    usertalk_replace = re.compile("User\\\\ talk\\\\\\:")
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

def load_from_api(wikis):
    it = chain(_load_rollback_from_api(wikis), _load_undo_from_api(wikis))
    return reduce(agg_patterns, it, {})

def _load_rollback_from_api(wikis):
    it = _load_prefix_from_api(wikis, "rollback-success")
    return ((wiki, "rollback-success", pattern) for wiki, pattern in it)

def _load_undo_from_api(wikis):
    it = _load_prefix_from_api(wikis, "undo-summary")
    return ((wiki, "undo-summary", pattern) for wiki, pattern in it)

def _load_prefix_from_api(wikis, page_prefix):
    return chain(* map(partial(_load_from_api,page_prefix = page_prefix), wikis))

def _load_from_api(wiki_db, page_prefix):
    base_url = "https://{0}.wikipedia.org"
    wiki = re.findall(r'(.*)wiki', wiki_db)[0]
    
    # first we search for the page we're looking for
    api = mwapi.Session(base_url.format(wiki),user_agent="mw_revert_tool_detector, project by groceryheist (Nathan TeBlunthuis) <nathante@uw.edu>))")

    try:
        res = api.get(action="query", list="allpages", apprefix=page_prefix, aplimit="max", apnamespace=8)
#        res = api.get(action="query", list="prefixsearch", pssearch="undo", pslimit="max", psnamespace="8")
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
            html_parsed = bs(res2['parse']['text']['*'])
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
    variants = {}
    for f in languages_files:
        pre_lang = variant_regex.match(f).groups()[0]
        is_variant = pre_lang in languagesWithVariants
        lang = regex.match(f).groups()[0]
        translations = json.load(open(f,'r'))
        for prop in properties:
            if prop in translations:
                summary_regex = to_regex(translations[prop])
                if not is_variant:
                    yield ("{0}wiki".format(lang),prop,summary_regex)
                else: 
                    yield ("{0}wiki".format(pre_lang),prop,summary_regex)
