import os

import dateutil.parser as date_parser

fromisoformat = date_parser.isoparse

def get_api(url):
    import mwapi
    # first we search for the page we're looking for
    user_agent = "mw_revert_tool_detector, project by groceryheist (Nathan TeBlunthuis) <nathante@uw.edu>))"
    api = mwapi.Session(url, user_agent=user_agent)
    return api

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
