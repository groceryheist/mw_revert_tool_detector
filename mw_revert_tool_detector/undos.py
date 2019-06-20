 # the first priority is on *.wikipedia.org/wiki/Mediawiki:Undo-summary
# then comes ./mediawiki-extensions-WikimediaMessages/
# finally comes ./mediawiki/languages/il8n/
from itertools import chain, groupby
import mwapi
import os
import subprocess
import re
import glob
import json
from bs4 import BeautifulSoup as bs

class RevertCommentMatcher(object):
    def __init__(self):
        self.undo_regexes = load_undo_regexes()

    def match_comment(self, wiki, comment):
        if self.is_undo(wiki,comment):
            return 'mw-undo'
        else:
            return None

    def is_undo(self, wiki, comment):
        if self.undo_regexes[wiki].match(comment):
            return True
        return False

def load_undo_regexes():
    undo_regexes = {}
    from_mediawiki = list(load_undos_from_mediawiki())
    wikis = {k for k, _ in from_mediawiki}
    from_extensions = list(load_undos_from_extensions())
    from_api = {k:set(v) for k,v in load_undos_from_api(wikis)}
    for wiki in wikis:
        if wiki in from_api:
            if from_api[wiki] is not None:
                undo_regexes[wiki] = from_api[wiki]
                continue

        if wiki in from_extensions:
            if from_extensions[wiki] is not None:
                undo_regexes[wiki] = from_extensions[wiki]
                continue

        undo_regexes[wiki] = from_api[wiki]

    return undo_regexes

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
    return r"(?:{0})".format(re4)

def clone_if_not_available(repo_url):
    repo_name = repo_url.split('/')[-2]
    if not os.path.exists("temp/{0}".format(repo_name)):
        if not os.path.exists("temp"):
            os.mkdir("temp")
        os.chdir("temp")
        subprocess.call(["git","clone",repo_url])
        os.chdir("..")

def load_undos_from_api(wikis):
    return groupby(chain(* map(_load_undo_from_api, wikis)), lambda t: t[0])

def _load_undo_from_api(wiki_db):
    base_url = "https://{0}.wikipedia.org"
    wiki = re.findall(r'(.*)wiki',wiki_db)[0]
    
    # first we search for the page we're looking for
    api = mwapi.Session(base_url.format(wiki),user_agent="mw_revert_tool_detector, project by groceryheist (Nathan TeBlunthuis) <nathante@uw.edu>))")

    try:
        res = api.get(action="query",list="allpages",apprefix="undo-success",aplimit="max",apn amespace=8)
    except mwapi.errors.ConnectionError as e:
        print(e)
        return

    allpages = res['query']['allpages']
    if len(allpages) > 0:
        for page in allpages:
            # then we get the text of that page
            res2 = api.get(action="parse",page=page['title'],prop="text")
            html_parsed = bs(res2['parse']['text']['*'])
            yield (wiki_db, to_regex(html_parsed.getText().strip()))

def load_undos_from_extensions():
    clone_if_not_available("https://github.com/wikimedia/mediawiki-extensions-WikimediaMessages/")
    path_to_overrides = "temp/mediawiki-extensions-WikimediaMessages/i18n/wikimediaoverrides"
    return load_json_undos(path_to_overrides)
    
def load_undos_from_mediawiki():
    clone_if_not_available("https://github.com/wikimedia/mediawiki/")
    return load_json_undos("temp/mediawiki/languages/i18n/")

def load_json_undos(path):
    regex = re.compile(r".*/(.*)\.json")
    variant_regex = re.compile(r".*/([^-]*).*\.json")
    languagesWithVariants = ['en','crh','gan','iu','kk','ku','shi','sr','tg','uz','zh']
    glob_str = "{0}/*.json".format(path)
    languages_files = glob.glob(glob_str)

    variants = {}
    for f in languages_files:
        pre_lang = variant_regex.match(f).groups()[0]
        is_variant =  pre_lang in languagesWithVariants
        lang = regex.match(f).groups()[0]
        translations = json.load(open(f,'r'))
        if 'undo-summary' in translations:
            summary_regex = to_regex(translations['undo-summary'])
            if not is_variant:
                yield ("{0}wiki".format(lang),summary_regex)
            else: 
                if pre_lang in variants:
                    variants[pre_lang].append(summary_regex)
                else:
                    variants[pre_lang] = [summary_regex]
    for lang, summaries in variants.items():
        yield ("{0}wiki".format(lang), summaries)
