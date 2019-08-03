from timedPattern import TimedPattern
import os
import re
import dateutil.parser as date_parser
fromisoformat = date_parser.isoparse


# we only support namespaces with these constants
namespace_constants = {
    'NS_MAIN': 0,
    'NS_TALK': 1,
    'NS_USER': 2,
    'NS_USER_TALK': 3,
    'NS_PROJECT': 4,
    'NS_PROJECT_TALK': 5,
    'NS_FILE': 6,
    'NS_FILE_TALK': 7,
    'NS_MEDIAWIKI': 8,
    'NS_MEDIAWIKI_TALK': 9,
    'NS_TEMPLATE': 10,
    'NS_TEMPLATE_TALK': 11,
    'NS_HELP': 12,
    'NS_HELP_TALK': 13,
    'NS_CATEGORY': 14,
    'NS_CATEGORY_TALK': 15,
    'NS_SPECIAL': -1,
    'NS_MEDIA': -2
}


def get_api(url):
    import mwapi
    # first we search for the page we're looking for
    user_agent = "mw_revert_tool_detector, project by groceryheist (Nathan TeBlunthuis) <nathante@uw.edu>))"
    api = mwapi.Session(url, user_agent=user_agent)
    return api


def clone_if_not_available(repo_url):
    repo_name = repo_url.split('/')[-2]
    dest_path = os.path.join("temp", repo_name)
    if not os.path.exists(dest_path):
        if not os.path.exists("temp"):
            os.mkdir("temp")
        os.chdir("temp")
        os.subprocess.call(["git", "clone", repo_url])
        os.chdir("..")

    return dest_path


def convert_php_dict(php_dict):
    elems = php_dict.split(',')
    return {a.strip(): b.strip().replace("'", "")
            for a, b in [e.split("=>")[0:2]
                         for e in elems if '=>' in e]}


def parse_localized_namespaces(filehandle):
    php_code = open(filehandle).read()

    namespace_regex = re.compile(
        r"\$namespaceNames\s*=\s*(?:\[|array\()(.*?)(?:\]|\));", flags=re.S)

    matches = namespace_regex.findall(php_code)
    if len(matches) > 0:
        php_dict = matches[0]
        namespace_dict = convert_php_dict(php_dict)
        namespace_dict = {k: v for k, v in
                          [(namespace_constants.get(k, None), v)
                           for k, v in namespace_dict.items()]
                          if k is not None}

        return namespace_dict


def get_previous_time_from_index(index, time):
    return index.bisect_right(TimedPattern(time, None)) - 1


def iterate_commits(repo, fileset, max_count=-1):
    return repo.iter_commits('master', fileset, max_count=max_count)
