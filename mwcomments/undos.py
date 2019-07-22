# the first priority is on *.wikipedia.org/wiki/Mediawiki:Undo-summary
# then comes ./mediawiki-extensions-WikimediaMessages/
# finally comes ./mediawiki/languages/il8n/
import datetime
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
import dateutil.parser as date_parser
from . import EditSummary, EditSummaryEncoder


def patterns_to_regex(patterns, wikimedia_sites):
    for wiki, prop in patterns.items():
        for time, summary in prop.items():
            patterns[wiki][prop][time] = to_regex(summary, wikimedia_sites[wiki])
    return patterns

def to_regex(summary, site_info):
        
    dollar_replace = re.compile(re.escape("\$") + "\d")
    gender_replace = re.compile(re.escape("\{\{") + "GENDER.*" + re.escape("\}\}"))

    if summary[-1] == '.':
        summary = summary[0:-1]

    summary = apply_parser_functions(summary, site_info)

    summary = dollar_replace.sub('(.*)',summary)
    summary = gender_replace.sub("(.*)",summary)

    # remove final periods
    return re.compile(r"(?:.*{0}.*)".format(summary))

# TODO: specifically handle nested parser functions 
def apply_parser_functions(summary, site_info):

    import wikitextparser as wtp
    parsed = wtp.parse(summary)

    parser_functions = parsed.parser_functions

    def ifexpr(pf):
        cond, op1, op2 = pf.arguments
        return r'(?:{0}|{1})'.format(re.escape(op1.value), re.escape(op2.value))

    def invoke(pf):
        t, func, op = pf.arguments
        if t[0].parent().name == '#ifexpr':
            return ""

    def gender(pf):
        t, a, b, c = pf.arguments
        return r'(?:{0}|{1}|{2})'.format(re.escape(a), re.escape(b), re.escape(c))

    # special pages can probably be had from the siteinfo api too.
    # one problem might be that the siteinfo falls out of date.
    def special(pf):
        api = get_api(site_info['url'])
        result = api.get(action='query', meta='siteinfo', siprop = ['magicwords'])
        special_aliases = chain(* [x['aliases'] for x in result['query']['magicwords'] if  x['name'] == 'special'])
        regex = r'(?:{0})'.format('|'.join(special_aliases))
        return regex
    

    def extractLocalizedNamespaces(lang, date):
        def get_relevant_commits(lang, date):
            commits = repo.iter_commits("master",[msgs_php_fh])
            commits_prior_to_date = [c for c in commits if c.committed_datetime <= date]
            return commits_prior_to_date[-2:]

        def convert_php_dict(php_dict):
            elems = php_dict.split(',')
            return {a.strip():b.strip().replace("'","") for a,b in [e.split("=>")[0:2] for e in elems if '=>' in e]}
        
        def parse_localized_namespaces(filehandle):
            php_code = open(filehandle).read()
            
            namespace_regex = re.compile(r"\$namespaceNames\s*=\s*\[(.*?)\];", flags = re.S)
n
            php_dict = namespace_regex.findall(php_code)[0]
            
            namespace_dict = convert_php_dict(php_dict)
            return namespace_dict
            

        import git
        repo_path = "temp/mediawiki"
        repo = git.Repo(repo_path)
        lang = lang[0].upper() + lang[1:]
        msgs_php_fh = os.path.join("languages","Messages{0}.php".format(lang))


        commits = get_relevant_commits(lang, date)


        for commit in commits:
            repo.git.checkout('-f', commit)
            yield (parse_localized_namespaces(os.path.join(path,msgs_php_fh)))

    # TODO we need to handle localiztion templates using the api by passing in the url and the date.
    # NS can be got from the siteinfo api
    # we'll need to look up the namespace from git. 
    def ns(pf):
        # get langs from siteinfos
        # pass in the date in siteinfo

        namespace_dicts = extractLocalizedNamespaces(lang,date)
        namespace_name = pf.

    wikitemplate_patterns = {"#ifexpr": ifexpr, "#invoke": invoke, "ns":ns, 'gender':gender, "#special":special}

    if len(parser_functions) > 0:
        
        pf = parser_functions[0]
        span = pf.span
        if pf.name in wikitemplate_patterns:
            evaled_func = wikitemplate_patterns[pf.name.lower()](pf)
            summary = re.escape(summary[0:span[0]]) + evaled_func + re.escape(summary[span[1]:])
            return summary

    else:
        return re.escape(summary)


def get_fallback_langs(site_info):

    import mwapi
    api = get_api(site_info['url'])

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


def load_from_extensions(properties):
    git_path = clone_if_not_available("https://github.com/wikimedia/mediawiki-extensions-WikimediaMessages/")
    config_path = "/i18n/wikimediaoverrides"
    return load_from_git(git_path, config_path, properties)

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
        idx = sorted_list.bisect_right((timestamp,""))
        print(idx, len(sorted_list))
        if idx != len(sorted_list):
            regexes = [regex for timestamp, regex in [sorted_list[idx-1], sorted_list[idx]]]
        else:
            regexes = [sorted_list[idx-1][1]]

        for regex in regexes:
            if regex.match(comment):
                yield prop_name

    if huggle_pattern.match(comment):
        yield "huggle"

    if twinkle_pattern.match(comment):
        yield "twinkle"


huggle_pattern = re.compile(r".*\(HG\).*")
twinkle_pattern = re.compile(r".*\(TW\).*")
wiki_patterns = None

wiki_patterns = load_wiki_patterns()
